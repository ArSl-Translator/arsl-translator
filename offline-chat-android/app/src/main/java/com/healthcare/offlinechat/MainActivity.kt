package com.healthcare.offlinechat

import android.Manifest
import android.annotation.SuppressLint
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothManager
import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.core.view.WindowCompat
import androidx.lifecycle.viewmodel.compose.viewModel
import com.healthcare.offlinechat.ui.screens.AiAssistantScreen
import com.healthcare.offlinechat.ui.screens.ChatScreen
import com.healthcare.offlinechat.ui.screens.ConversationListScreen
import com.healthcare.offlinechat.ui.screens.DeviceListScreen
import com.healthcare.offlinechat.ui.screens.HomeScreen
import com.healthcare.offlinechat.ui.theme.OfflineChatTheme
import com.healthcare.offlinechat.viewmodel.ChatViewModel
import com.healthcare.offlinechat.viewmodel.UserRole

class MainActivity : ComponentActivity() {

    private val bluetoothManager by lazy {
        getSystemService(BluetoothManager::class.java)
    }

    private val bluetoothAdapter by lazy {
        bluetoothManager?.adapter
    }

    private val isBluetoothEnabled: Boolean
        get() = bluetoothAdapter?.isEnabled == true

    private val enableBluetoothLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { /* Result handled */ }

    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        val allGranted = permissions.values.all { it }
        if (!allGranted) {
            Toast.makeText(
                this,
                getString(R.string.errorbluetoothrequired),
                Toast.LENGTH_LONG
            ).show()
        }
    }

    @SuppressLint("MissingPermission")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        WindowCompat.setDecorFitsSystemWindows(window, false)

        requestPermissions()

        setContent {
            OfflineChatTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    val viewModel: ChatViewModel = viewModel()

                    val userRole by viewModel.userRole.collectAsState()
                    val isConnected by viewModel.isConnected.collectAsState()
                    val connectionStatus by viewModel.connectionStatus.collectAsState()
                    val messages by viewModel.messages.collectAsState()
                    val conversations by viewModel.conversations.collectAsState()
                    val pairedDevices by viewModel.pairedDevices.collectAsState()
                    val scannedDevices by viewModel.scannedDevices.collectAsState()
                    val currentConversationId by viewModel.currentConversationId.collectAsState()
                    val connectedDevice by viewModel.connectedDevice.collectAsState()
                    var showAiAssistant by remember { mutableStateOf(false) }

                    when {
                        showAiAssistant -> {
                            AiAssistantScreen(
                                onBack = { showAiAssistant = false }
                            )
                        }

                        userRole == null -> {
                            HomeScreen(
                                onRoleSelected = { role ->
                                    if (!isBluetoothEnabled) {
                                        enableBluetoothLauncher.launch(
                                            Intent(BluetoothAdapter.ACTION_REQUEST_ENABLE)
                                        )
                                    }
                                    viewModel.setRole(role)
                                },
                                onOpenAssistant = { showAiAssistant = true }
                            )
                        }

                        userRole == UserRole.ASSISTED && currentConversationId == null -> {
                            ConversationListScreen(
                                conversations = conversations,
                                connectionStatus = connectionStatus,
                                onConversationClick = { conversation ->
                                    viewModel.setCurrentConversation(
                                        conversation.deviceAddress,
                                        conversation.deviceName
                                    )
                                },
                                onBack = { viewModel.goBackToHome() }
                            )
                        }

                        userRole == UserRole.ASSISTED && currentConversationId != null -> {
                            val conversationName = conversations
                                .find { it.deviceAddress == currentConversationId }
                                ?.deviceName ?: connectedDevice?.name ?: "Chat"

                            ChatScreen(
                                messages = messages,
                                connectionStatus = connectionStatus,
                                isConnected = isConnected,
                                conversationName = conversationName,
                                onSendMessage = { viewModel.sendMessage(it) },
                                onSendMedia = { viewModel.sendMedia(it) },
                                onBack = { viewModel.clearCurrentConversation() }
                            )
                        }

                        userRole == UserRole.ASSISTANT && !isConnected -> {
                            DeviceListScreen(
                                pairedDevices = pairedDevices,
                                scannedDevices = scannedDevices,
                                onDeviceClick = { device ->
                                    viewModel.connectToDevice(device)
                                },
                                onStartScan = { viewModel.startDiscovery() },
                                onStopScan = { viewModel.stopDiscovery() },
                                onBack = { viewModel.goBackToHome() }
                            )
                        }

                        userRole == UserRole.ASSISTANT && isConnected -> {
                            val conversationName = connectedDevice?.name ?: "Chat"

                            ChatScreen(
                                messages = messages,
                                connectionStatus = connectionStatus,
                                isConnected = isConnected,
                                conversationName = conversationName,
                                onSendMessage = { viewModel.sendMessage(it) },
                                onSendMedia = { viewModel.sendMedia(it) },
                                onBack = { viewModel.disconnect() }
                            )
                        }
                    }
                }
            }
        }
    }

    private fun requestPermissions() {
        val permissions = mutableListOf<String>()

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            permissions.add(Manifest.permission.BLUETOOTH_CONNECT)
            permissions.add(Manifest.permission.BLUETOOTH_SCAN)
            permissions.add(Manifest.permission.BLUETOOTH_ADVERTISE)
        }

        permissions.add(Manifest.permission.ACCESS_FINE_LOCATION)
        permissions.add(Manifest.permission.CAMERA)
        permissions.add(Manifest.permission.RECORD_AUDIO)

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            permissions.add(Manifest.permission.READ_MEDIA_IMAGES)
            permissions.add(Manifest.permission.READ_MEDIA_VIDEO)
            permissions.add(Manifest.permission.READ_MEDIA_AUDIO)
        } else {
            permissions.add(Manifest.permission.READ_EXTERNAL_STORAGE)
        }

        permissionLauncher.launch(permissions.toTypedArray())
    }
}
