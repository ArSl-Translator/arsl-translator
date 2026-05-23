package com.arsl.offlinechat

import android.Manifest
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothManager
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.lifecycle.viewmodel.compose.viewModel
import com.arsl.offlinechat.ui.screens.ChatScreen
import com.arsl.offlinechat.ui.screens.ConversationListScreen
import com.arsl.offlinechat.ui.screens.DeviceListScreen
import com.arsl.offlinechat.ui.screens.HomeScreen
import com.arsl.offlinechat.ui.theme.AccessibleChatTheme
import com.arsl.offlinechat.viewmodel.ChatViewModel
import com.arsl.offlinechat.viewmodel.UserRole

class MainActivity : ComponentActivity() {
    private val bluetoothAdapter: BluetoothAdapter? by lazy {
        getSystemService(BluetoothManager::class.java)?.adapter
    }

    private val enableBluetooth = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) {}

    private val permissions = registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { result ->
        if (result.values.any { !it }) {
            Toast.makeText(this, getString(R.string.permissions_required), Toast.LENGTH_LONG).show()
        }
    }

    override fun attachBaseContext(newBase: Context) {
        super.attachBaseContext(LocaleHelper.arabicContext(newBase))
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        requestNeededPermissions()

        setContent {
            AccessibleChatTheme {
                Surface(Modifier.fillMaxSize()) {
                    val vm: ChatViewModel = viewModel()
                    val role by vm.role.collectAsState()
                    val conversations by vm.conversations.collectAsState()
                    val currentId by vm.currentConversationId.collectAsState()
                    val messages by vm.currentMessages.collectAsState()
                    val paired by vm.pairedDevices.collectAsState()
                    val scanned by vm.scannedDevices.collectAsState()
                    val connected by vm.isConnected.collectAsState()
                    val connectedDevice by vm.connectedDevice.collectAsState()
                    val status by vm.connectionStatus.collectAsState()

                    when {
                        role == null -> HomeScreen { selected ->
                            if (bluetoothAdapter?.isEnabled != true) {
                                enableBluetooth.launch(Intent(BluetoothAdapter.ACTION_REQUEST_ENABLE))
                            }
                            vm.chooseRole(selected)
                        }

                        role == UserRole.ASSISTED && currentId == null -> ConversationListScreen(
                            conversations = conversations,
                            connectionStatus = status,
                            onConversationClick = { vm.openConversation(it.deviceAddress, it.deviceName) },
                            onBack = { vm.goHome() }
                        )

                        role == UserRole.ASSISTED && currentId != null -> {
                            val name = conversations.find { it.deviceAddress == currentId }?.deviceName
                                ?: connectedDevice?.name
                                ?: "Chat"
                            ChatScreen(
                                messages = messages,
                                connectionStatus = status,
                                isConnected = connected,
                                conversationName = name,
                                onSendText = vm::sendText,
                                onSendMedia = vm::sendMedia,
                                onBack = { vm.closeConversation() }
                            )
                        }

                        role == UserRole.HELPER && !connected -> DeviceListScreen(
                            pairedDevices = paired,
                            scannedDevices = scanned,
                            onDeviceClick = vm::connectTo,
                            onStartScan = vm::startDiscovery,
                            onStopScan = vm::stopDiscovery,
                            onBack = { vm.goHome() }
                        )

                        else -> ChatScreen(
                            messages = messages,
                            connectionStatus = status,
                            isConnected = connected,
                            conversationName = connectedDevice?.name ?: "Chat",
                            onSendText = vm::sendText,
                            onSendMedia = vm::sendMedia,
                            onBack = { vm.disconnect() }
                        )
                    }
                }
            }
        }
    }

    private fun requestNeededPermissions() {
        val list = mutableListOf(Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.CAMERA, Manifest.permission.RECORD_AUDIO)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            list += Manifest.permission.BLUETOOTH_CONNECT
            list += Manifest.permission.BLUETOOTH_SCAN
            list += Manifest.permission.BLUETOOTH_ADVERTISE
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            list += Manifest.permission.READ_MEDIA_IMAGES
            list += Manifest.permission.READ_MEDIA_VIDEO
            list += Manifest.permission.READ_MEDIA_AUDIO
        } else {
            list += Manifest.permission.READ_EXTERNAL_STORAGE
        }
        permissions.launch(list.toTypedArray())
    }
}
