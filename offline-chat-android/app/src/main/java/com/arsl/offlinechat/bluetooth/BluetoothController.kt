package com.arsl.offlinechat.bluetooth

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

@SuppressLint("MissingPermission")
class BluetoothController(private val context: Context) {
    private val manager = context.getSystemService(BluetoothManager::class.java)
    private val adapter = manager?.adapter

    private val _scannedDevices = MutableStateFlow<List<BluetoothDevice>>(emptyList())
    val scannedDevices: StateFlow<List<BluetoothDevice>> = _scannedDevices.asStateFlow()

    private val _pairedDevices = MutableStateFlow<List<BluetoothDevice>>(emptyList())
    val pairedDevices: StateFlow<List<BluetoothDevice>> = _pairedDevices.asStateFlow()

    private val _connectedDevice = MutableStateFlow<BluetoothDevice?>(null)
    val connectedDevice: StateFlow<BluetoothDevice?> = _connectedDevice.asStateFlow()

    private val _isConnected = MutableStateFlow(false)
    val isConnected: StateFlow<Boolean> = _isConnected.asStateFlow()

    private val _connectionStatus = MutableStateFlow("Disconnected")
    val connectionStatus: StateFlow<String> = _connectionStatus.asStateFlow()

    private val _incomingText = MutableStateFlow<IncomingText?>(null)
    val incomingText: StateFlow<IncomingText?> = _incomingText.asStateFlow()

    private val _incomingMedia = MutableStateFlow<IncomingMedia?>(null)
    val incomingMedia: StateFlow<IncomingMedia?> = _incomingMedia.asStateFlow()

    private var server: BluetoothServer? = null
    private var client: BluetoothClient? = null
    private var transfer: BluetoothDataTransfer? = null
    private var receiverRegistered = false

    private val receiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context?, intent: Intent?) {
            if (intent?.action != BluetoothDevice.ACTION_FOUND) return
            val device = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                intent.getParcelableExtra(BluetoothDevice.EXTRA_DEVICE, BluetoothDevice::class.java)
            } else {
                @Suppress("DEPRECATION")
                intent.getParcelableExtra(BluetoothDevice.EXTRA_DEVICE)
            } ?: return

            _scannedDevices.update { current ->
                if (current.any { it.address == device.address }) current else current + device
            }
        }
    }

    companion object {
        const val SERVICE_NAME = "ArSLAccessibleOfflineChat"
        val SERVICE_UUID: UUID = UUID.fromString("2f7023de-4c6d-45c9-b65d-3b8ef8b6c101")
    }

    fun hasPermissions(): Boolean {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            has(Manifest.permission.BLUETOOTH_CONNECT) && has(Manifest.permission.BLUETOOTH_SCAN)
        } else {
            has(Manifest.permission.ACCESS_FINE_LOCATION)
        }
    }

    fun isBluetoothEnabled(): Boolean = adapter?.isEnabled == true

    fun updatePairedDevices() {
        if (!hasPermissions()) return
        _pairedDevices.value = adapter?.bondedDevices?.toList().orEmpty()
    }

    fun startDiscovery() {
        if (!hasPermissions()) return
        stopDiscovery()
        _scannedDevices.value = emptyList()
        context.registerReceiver(receiver, IntentFilter(BluetoothDevice.ACTION_FOUND))
        receiverRegistered = true
        adapter?.startDiscovery()
    }

    fun stopDiscovery() {
        if (hasPermissions()) adapter?.cancelDiscovery()
        if (receiverRegistered) {
            try {
                context.unregisterReceiver(receiver)
            } catch (_: IllegalArgumentException) {
            }
            receiverRegistered = false
        }
    }

    fun startServer() {
        if (!hasPermissions() || adapter == null) return
        _connectionStatus.value = "Waiting for connection..."
        server?.cancel()
        server = BluetoothServer(
            adapter = adapter,
            onConnected = { socket -> setupConnectedSocket(socket.remoteDevice, socketTransfer = socket) },
            onError = { _connectionStatus.value = it }
        ).also { it.start() }
    }

    fun connectToDevice(device: BluetoothDevice) {
        if (!hasPermissions()) return
        stopDiscovery()
        _connectionStatus.value = "Connecting to ${device.name ?: device.address}..."
        client?.cancel()
        client = BluetoothClient(
            device = device,
            onConnected = { socket -> setupConnectedSocket(device, socket) },
            onError = { _connectionStatus.value = it }
        ).also { it.start() }
    }

    fun sendText(message: String): Boolean = transfer?.sendText(message) ?: false
    fun sendMedia(bytes: ByteArray, metadata: JSONObject): Boolean = transfer?.sendMedia(bytes, metadata) ?: false
    fun clearIncomingText() { _incomingText.value = null }
    fun clearIncomingMedia() { _incomingMedia.value = null }

    fun disconnect() {
        transfer?.close()
        server?.cancel()
        client?.cancel()
        transfer = null
        server = null
        client = null
        _connectedDevice.value = null
        _isConnected.value = false
        _connectionStatus.value = "Disconnected"
    }

    fun release() {
        disconnect()
        stopDiscovery()
    }

    private fun setupConnectedSocket(device: BluetoothDevice, socketTransfer: android.bluetooth.BluetoothSocket) {
        _connectedDevice.value = device
        _isConnected.value = true
        _connectionStatus.value = "Connected to ${device.name ?: device.address}"
        transfer = BluetoothDataTransfer(
            socket = socketTransfer,
            onTextReceived = {
                _incomingText.value = IncomingText(it, device.address, device.name ?: device.address)
            },
            onMediaReceived = { bytes, metadata ->
                _incomingMedia.value = IncomingMedia(bytes, metadata, device.address, device.name ?: device.address)
            },
            onConnectionLost = {
                _isConnected.value = false
                _connectedDevice.value = null
                _connectionStatus.value = "Connection lost"
            }
        ).also { it.startListening() }
    }

    private fun has(permission: String): Boolean {
        return ContextCompat.checkSelfPermission(context, permission) == PackageManager.PERMISSION_GRANTED
    }
}
