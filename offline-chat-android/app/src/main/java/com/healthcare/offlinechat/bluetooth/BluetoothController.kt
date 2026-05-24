package com.healthcare.offlinechat.bluetooth

import android.Manifest
import android.annotation.SuppressLint
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothManager
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.content.ContextCompat
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import org.json.JSONObject
import java.util.UUID

data class IncomingMessage(
    val content: String,
    val senderAddress: String,
    val senderName: String
)

data class IncomingMedia(
    val bytes: ByteArray,
    val metadata: JSONObject,
    val senderAddress: String,
    val senderName: String
) {
    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (javaClass != other?.javaClass) return false
        other as IncomingMedia
        return bytes.contentEquals(other.bytes) &&
            metadata.toString() == other.metadata.toString() &&
            senderAddress == other.senderAddress
    }

    override fun hashCode(): Int {
        var result = bytes.contentHashCode()
        result = 31 * result + metadata.toString().hashCode()
        result = 31 * result + senderAddress.hashCode()
        return result
    }
}

@SuppressLint("MissingPermission")
class BluetoothController(
    private val context: Context
) {
    private val bluetoothManager = context.getSystemService(BluetoothManager::class.java)
    private val bluetoothAdapter = bluetoothManager?.adapter

    private val _scannedDevices = MutableStateFlow<List<BluetoothDevice>>(emptyList())
    val scannedDevices: StateFlow<List<BluetoothDevice>> = _scannedDevices.asStateFlow()

    private val _pairedDevices = MutableStateFlow<List<BluetoothDevice>>(emptyList())
    val pairedDevices: StateFlow<List<BluetoothDevice>> = _pairedDevices.asStateFlow()

    private val _isConnected = MutableStateFlow(false)
    val isConnected: StateFlow<Boolean> = _isConnected.asStateFlow()

    private val _connectionStatus = MutableStateFlow("Disconnected")
    val connectionStatus: StateFlow<String> = _connectionStatus.asStateFlow()

    private val _incomingMessages = MutableStateFlow<IncomingMessage?>(null)
    val incomingMessages: StateFlow<IncomingMessage?> = _incomingMessages.asStateFlow()

    private val _incomingMedia = MutableStateFlow<IncomingMedia?>(null)
    val incomingMedia: StateFlow<IncomingMedia?> = _incomingMedia.asStateFlow()

    private val _connectedDevice = MutableStateFlow<BluetoothDevice?>(null)
    val connectedDevice: StateFlow<BluetoothDevice?> = _connectedDevice.asStateFlow()

    private var bluetoothServer: BluetoothServer? = null
    private var bluetoothClient: BluetoothClient? = null
    private var dataTransfer: BluetoothDataTransfer? = null

    private val foundDeviceReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            when (intent?.action) {
                BluetoothDevice.ACTION_FOUND -> {
                    val device = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                        intent.getParcelableExtra(
                            BluetoothDevice.EXTRA_DEVICE,
                            BluetoothDevice::class.java
                        )
                    } else {
                        @Suppress("DEPRECATION")
                        intent.getParcelableExtra(BluetoothDevice.EXTRA_DEVICE)
                    }

                    device?.let { newDevice ->
                        _scannedDevices.update { devices ->
                            if (devices.any { it.address == newDevice.address }) {
                                devices
                            } else {
                                devices + newDevice
                            }
                        }
                    }
                }
            }
        }
    }

    companion object {
        val SERVICE_UUID: UUID = UUID.fromString("00001101-0000-1000-8000-00805F9B34FB")
        const val SERVICE_NAME = "OfflineChatService"
    }

    fun hasPermissions(): Boolean {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            ContextCompat.checkSelfPermission(
                context, Manifest.permission.BLUETOOTH_CONNECT
            ) == PackageManager.PERMISSION_GRANTED &&
                ContextCompat.checkSelfPermission(
                    context, Manifest.permission.BLUETOOTH_SCAN
                ) == PackageManager.PERMISSION_GRANTED
        } else {
            ContextCompat.checkSelfPermission(
                context, Manifest.permission.ACCESS_FINE_LOCATION
            ) == PackageManager.PERMISSION_GRANTED
        }
    }

    fun isBluetoothEnabled(): Boolean {
        return bluetoothAdapter?.isEnabled == true
    }

    fun getDeviceName(): String {
        return if (hasPermissions()) {
            bluetoothAdapter?.name ?: "Unknown"
        } else {
            "Unknown"
        }
    }

    fun updatePairedDevices() {
        if (!hasPermissions()) return

        bluetoothAdapter?.bondedDevices?.let { devices ->
            _pairedDevices.value = devices.toList()
        }
    }

    fun startDiscovery() {
        if (!hasPermissions()) return

        context.registerReceiver(
            foundDeviceReceiver,
            IntentFilter(BluetoothDevice.ACTION_FOUND)
        )

        _scannedDevices.value = emptyList()
        bluetoothAdapter?.startDiscovery()
    }

    fun stopDiscovery() {
        if (!hasPermissions()) return

        bluetoothAdapter?.cancelDiscovery()
        try {
            context.unregisterReceiver(foundDeviceReceiver)
        } catch (e: IllegalArgumentException) {
            // Receiver not registered
        }
    }

    fun startServer() {
        if (!hasPermissions() || bluetoothAdapter == null) return

        _connectionStatus.value = "Waiting for connection..."

        bluetoothServer = BluetoothServer(
            bluetoothAdapter = bluetoothAdapter,
            onConnectionEstablished = { socket ->
                val remoteDevice = socket.remoteDevice
                _connectedDevice.value = remoteDevice
                _isConnected.value = true
                _connectionStatus.value = "Connected to ${remoteDevice.name ?: "Unknown"}"

                dataTransfer = BluetoothDataTransfer(
                    socket = socket,
                    onMessageReceived = { message ->
                        _incomingMessages.value = IncomingMessage(
                            content = message,
                            senderAddress = remoteDevice.address,
                            senderName = remoteDevice.name ?: "Unknown"
                        )
                    },
                    onMediaReceived = { bytes, metadataJson ->
                        _incomingMedia.value = IncomingMedia(
                            bytes = bytes,
                            metadata = JSONObject(metadataJson),
                            senderAddress = remoteDevice.address,
                            senderName = remoteDevice.name ?: "Unknown"
                        )
                    },
                    onConnectionLost = {
                        _isConnected.value = false
                        _connectedDevice.value = null
                        _connectionStatus.value = "Connection lost"
                        dataTransfer = null
                        startServer()
                    }
                )
                dataTransfer?.startListening()
            },
            onError = { error ->
                _connectionStatus.value = "Error: $error"
            }
        )
        bluetoothServer?.start()
    }

    fun connectToDevice(device: BluetoothDevice) {
        if (!hasPermissions()) return

        stopDiscovery()
        _connectionStatus.value = "Connecting to ${device.name ?: "Unknown"}..."

        bluetoothClient = BluetoothClient(
            device = device,
            onConnectionEstablished = { socket ->
                _connectedDevice.value = device
                _isConnected.value = true
                _connectionStatus.value = "Connected to ${device.name ?: "Unknown"}"

                dataTransfer = BluetoothDataTransfer(
                    socket = socket,
                    onMessageReceived = { message ->
                        _incomingMessages.value = IncomingMessage(
                            content = message,
                            senderAddress = device.address,
                            senderName = device.name ?: "Unknown"
                        )
                    },
                    onMediaReceived = { bytes, metadataJson ->
                        _incomingMedia.value = IncomingMedia(
                            bytes = bytes,
                            metadata = JSONObject(metadataJson),
                            senderAddress = device.address,
                            senderName = device.name ?: "Unknown"
                        )
                    },
                    onConnectionLost = {
                        _isConnected.value = false
                        _connectedDevice.value = null
                        _connectionStatus.value = "Connection lost"
                        dataTransfer = null
                    }
                )
                dataTransfer?.startListening()
            },
            onError = { error ->
                _connectionStatus.value = "Error: $error"
            }
        )
        bluetoothClient?.start()
    }

    fun sendMessage(message: String): Boolean {
        return dataTransfer?.sendMessage(message) ?: false
    }

    fun sendMedia(mediaBytes: ByteArray, metadata: JSONObject): Boolean {
        return dataTransfer?.sendMedia(mediaBytes, metadata) ?: false
    }

    fun clearIncomingMessage() {
        _incomingMessages.value = null
    }

    fun clearIncomingMedia() {
        _incomingMedia.value = null
    }

    fun disconnect() {
        dataTransfer?.close()
        bluetoothServer?.cancel()
        bluetoothClient?.cancel()

        dataTransfer = null
        bluetoothServer = null
        bluetoothClient = null

        _isConnected.value = false
        _connectedDevice.value = null
        _connectionStatus.value = "Disconnected"
    }

    fun release() {
        disconnect()
        stopDiscovery()
    }
}
