package com.arsl.offlinechat.viewmodel

import android.annotation.SuppressLint
import android.app.Application
import android.bluetooth.BluetoothDevice
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.arsl.offlinechat.AccessibleChatApplication
import com.arsl.offlinechat.bluetooth.BluetoothController
import com.arsl.offlinechat.bluetooth.IncomingMedia
import com.arsl.offlinechat.data.ChatMessage
import com.arsl.offlinechat.data.Conversation
import com.arsl.offlinechat.data.MessageType
import com.arsl.offlinechat.media.FileUtils
import com.arsl.offlinechat.media.MediaInfo
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.File

enum class UserRole {
    ASSISTED,
    HELPER
}

@SuppressLint("MissingPermission")
class ChatViewModel(application: Application) : AndroidViewModel(application) {
    private val app = application as AccessibleChatApplication
    private val context = app.applicationContext
    private val messagesDao = app.database.chatMessageDao()
    private val conversationsDao = app.database.conversationDao()

    val bluetooth = BluetoothController(context)

    private val _role = MutableStateFlow<UserRole?>(null)
    val role: StateFlow<UserRole?> = _role.asStateFlow()

    private val _currentConversationId = MutableStateFlow<String?>(null)
    val currentConversationId: StateFlow<String?> = _currentConversationId.asStateFlow()

    val conversations = conversationsDao.getAllConversations().stateIn(
        viewModelScope,
        SharingStarted.WhileSubscribed(5000),
        emptyList()
    )

    @OptIn(ExperimentalCoroutinesApi::class)
    val currentMessages = _currentConversationId.flatMapLatest { id ->
        if (id == null) flowOf(emptyList()) else messagesDao.getMessagesForConversation(id)
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val scannedDevices = bluetooth.scannedDevices
    val pairedDevices = bluetooth.pairedDevices
    val connectedDevice = bluetooth.connectedDevice
    val isConnected = bluetooth.isConnected
    val connectionStatus = bluetooth.connectionStatus

    init {
        viewModelScope.launch {
            bluetooth.incomingText.collect { incoming ->
                if (incoming != null) {
                    saveIncomingText(incoming.senderAddress, incoming.senderName, incoming.content)
                    bluetooth.clearIncomingText()
                }
            }
        }

        viewModelScope.launch {
            bluetooth.incomingMedia.collect { incoming ->
                if (incoming != null) {
                    saveIncomingMedia(incoming)
                    bluetooth.clearIncomingMedia()
                }
            }
        }

        viewModelScope.launch {
            bluetooth.connectedDevice.collect { device ->
                if (device != null) openConversation(device.address, device.name ?: device.address)
            }
        }
    }

    fun chooseRole(role: UserRole) {
        _role.value = role
        if (role == UserRole.ASSISTED) {
            bluetooth.startServer()
        } else {
            bluetooth.updatePairedDevices()
        }
    }

    fun goHome() {
        bluetooth.disconnect()
        _role.value = null
        _currentConversationId.value = null
    }

    fun openConversation(deviceAddress: String, deviceName: String) {
        _currentConversationId.value = deviceAddress
        viewModelScope.launch {
            val existing = conversationsDao.getConversation(deviceAddress)
            if (existing == null) {
                conversationsDao.insertConversation(Conversation(deviceAddress, deviceName))
            }
            conversationsDao.markAsRead(deviceAddress)
        }
    }

    fun closeConversation() {
        _currentConversationId.value = null
    }

    fun startDiscovery() = bluetooth.startDiscovery()
    fun stopDiscovery() = bluetooth.stopDiscovery()
    fun connectTo(device: BluetoothDevice) = bluetooth.connectToDevice(device)
    fun disconnect() {
        bluetooth.disconnect()
        _currentConversationId.value = null
    }

    fun sendText(content: String) {
        val conversationId = _currentConversationId.value ?: return
        if (content.isBlank()) return
        viewModelScope.launch {
            messagesDao.insertMessage(
                ChatMessage(
                    conversationId = conversationId,
                    content = content.trim(),
                    senderName = "Me",
                    isFromMe = true
                )
            )
            updateConversation(conversationId, bluetooth.connectedDevice.value?.name ?: conversationId, content.trim(), false)
            bluetooth.sendText(content.trim())
        }
    }

    fun sendMedia(media: MediaInfo) {
        val conversationId = _currentConversationId.value ?: return
        viewModelScope.launch {
            val preview = previewText(media.type)
            messagesDao.insertMessage(
                ChatMessage(
                    conversationId = conversationId,
                    content = preview,
                    senderName = "Me",
                    isFromMe = true,
                    messageType = media.type.name,
                    mediaPath = media.path,
                    mediaFileName = media.fileName,
                    mediaMimeType = media.mimeType,
                    mediaDurationMs = media.durationMs,
                    mediaSizeBytes = media.sizeBytes
                )
            )
            updateConversation(conversationId, bluetooth.connectedDevice.value?.name ?: conversationId, preview, false)
            withContext(Dispatchers.IO) {
                val bytes = File(media.path).readBytes()
                val metadata = JSONObject().apply {
                    put("type", media.type.name)
                    put("fileName", media.fileName)
                    put("mimeType", media.mimeType)
                    put("sizeBytes", media.sizeBytes)
                    media.durationMs?.let { put("durationMs", it) }
                }
                bluetooth.sendMedia(bytes, metadata)
            }
        }
    }

    fun deleteConversation(deviceAddress: String) {
        viewModelScope.launch {
            messagesDao.deleteMessagesForConversation(deviceAddress)
            conversationsDao.deleteConversation(deviceAddress)
        }
    }

    override fun onCleared() {
        super.onCleared()
        bluetooth.release()
    }

    private suspend fun saveIncomingText(address: String, name: String, content: String) {
        updateConversation(address, name, content, address != _currentConversationId.value)
        messagesDao.insertMessage(
            ChatMessage(conversationId = address, content = content, senderName = name, isFromMe = false)
        )
    }

    private suspend fun saveIncomingMedia(incoming: IncomingMedia) {
        val type = runCatching {
            MessageType.valueOf(incoming.metadata.optString("type", MessageType.FILE.name))
        }.getOrDefault(MessageType.FILE)
        val fileName = incoming.metadata.optString("fileName", "received-${System.currentTimeMillis()}")
        val file = withContext(Dispatchers.IO) {
            FileUtils.writeBytes(context, incoming.bytes, fileName, folderFor(type))
        }
        val preview = previewText(type)
        updateConversation(incoming.senderAddress, incoming.senderName, preview, incoming.senderAddress != _currentConversationId.value)
        messagesDao.insertMessage(
            ChatMessage(
                conversationId = incoming.senderAddress,
                content = preview,
                senderName = incoming.senderName,
                isFromMe = false,
                messageType = type.name,
                mediaPath = file.absolutePath,
                mediaFileName = file.name,
                mediaMimeType = incoming.metadata.optString("mimeType", "application/octet-stream"),
                mediaDurationMs = incoming.metadata.optLong("durationMs", 0).takeIf { it > 0 },
                mediaSizeBytes = file.length()
            )
        )
    }

    private suspend fun updateConversation(address: String, name: String, lastMessage: String, unread: Boolean) {
        val existing = conversationsDao.getConversation(address)
        if (existing == null) {
            conversationsDao.insertConversation(
                Conversation(address, name, lastMessage, System.currentTimeMillis(), if (unread) 1 else 0)
            )
        } else {
            conversationsDao.updateConversation(
                existing.copy(
                    deviceName = name,
                    lastMessage = lastMessage,
                    lastMessageTime = System.currentTimeMillis(),
                    unreadCount = if (unread) existing.unreadCount + 1 else existing.unreadCount
                )
            )
        }
    }

    private fun previewText(type: MessageType): String {
        return when (type) {
            MessageType.IMAGE -> "📷 Image"
            MessageType.AUDIO -> "🎤 Audio"
            MessageType.VIDEO -> "🎬 Video"
            MessageType.FILE -> "📎 File"
            MessageType.TEXT -> ""
        }
    }

    private fun folderFor(type: MessageType): String {
        return when (type) {
            MessageType.IMAGE -> "images"
            MessageType.AUDIO -> "audio"
            MessageType.VIDEO -> "videos"
            MessageType.FILE, MessageType.TEXT -> "files"
        }
    }
}
