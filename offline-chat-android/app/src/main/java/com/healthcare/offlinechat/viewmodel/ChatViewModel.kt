package com.healthcare.offlinechat.viewmodel

import android.annotation.SuppressLint
import android.app.Application
import android.bluetooth.BluetoothDevice
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.healthcare.offlinechat.OfflineChatApplication
import com.healthcare.offlinechat.bluetooth.BluetoothController
import com.healthcare.offlinechat.data.ChatMessage
import com.healthcare.offlinechat.data.Conversation
import com.healthcare.offlinechat.data.MessageType
import com.healthcare.offlinechat.media.FileUtils
import com.healthcare.offlinechat.media.MediaInfo
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

@SuppressLint("MissingPermission")
class ChatViewModel(application: Application) : AndroidViewModel(application) {

    private val context = application.applicationContext
    private val database = (application as OfflineChatApplication).database
    private val messageDao = database.chatMessageDao()
    private val conversationDao = database.conversationDao()

    val bluetoothController = BluetoothController(context)

    private val _userName = MutableStateFlow("User")
    val userName: StateFlow<String> = _userName.asStateFlow()

    private val _userRole = MutableStateFlow<UserRole?>(null)
    val userRole: StateFlow<UserRole?> = _userRole.asStateFlow()

    private val _currentConversationId = MutableStateFlow<String?>(null)
    val currentConversationId: StateFlow<String?> = _currentConversationId.asStateFlow()

    val conversations = conversationDao.getAllConversations()
        .stateIn(
            scope = viewModelScope,
            started = SharingStarted.WhileSubscribed(5000),
            initialValue = emptyList()
        )

    @OptIn(ExperimentalCoroutinesApi::class)
    val messages = _currentConversationId.flatMapLatest { conversationId ->
        if (conversationId != null) {
            messageDao.getMessagesForConversation(conversationId)
        } else {
            flowOf(emptyList())
        }
    }.stateIn(
        scope = viewModelScope,
        started = SharingStarted.WhileSubscribed(5000),
        initialValue = emptyList()
    )

    val scannedDevices = bluetoothController.scannedDevices
    val pairedDevices = bluetoothController.pairedDevices
    val isConnected = bluetoothController.isConnected
    val connectionStatus = bluetoothController.connectionStatus
    val connectedDevice = bluetoothController.connectedDevice

    init {
        viewModelScope.launch {
            bluetoothController.incomingMessages.collect { incomingMessage ->
                incomingMessage?.let { msg ->
                    handleIncomingTextMessage(msg.senderAddress, msg.senderName, msg.content)
                    bluetoothController.clearIncomingMessage()
                }
            }
        }

        viewModelScope.launch {
            bluetoothController.incomingMedia.collect { incomingMedia ->
                incomingMedia?.let { media ->
                    handleIncomingMedia(media)
                    bluetoothController.clearIncomingMedia()
                }
            }
        }

        viewModelScope.launch {
            bluetoothController.connectedDevice.collect { device ->
                device?.let {
                    setCurrentConversation(it.address, it.name ?: "Unknown")
                }
            }
        }
    }

    private suspend fun handleIncomingTextMessage(senderAddress: String, senderName: String, content: String) {
        updateOrCreateConversation(senderAddress, senderName, content)

        val chatMessage = ChatMessage(
            conversationId = senderAddress,
            content = content,
            senderName = senderName,
            isFromMe = false,
            messageType = MessageType.TEXT.name
        )
        messageDao.insertMessage(chatMessage)
    }

    private suspend fun handleIncomingMedia(media: com.healthcare.offlinechat.bluetooth.IncomingMedia) {
        val metadata = media.metadata
        val messageType = metadata.optString("type", MessageType.FILE.name)
        val fileName = metadata.optString("fileName", "file_${System.currentTimeMillis()}")
        val mimeType = metadata.optString("mimeType", "application/octet-stream")
        val duration = metadata.optLong("duration", 0L).takeIf { it > 0 }
        val size = metadata.optLong("size", 0L)

        val subFolder = when (messageType) {
            MessageType.IMAGE.name -> "images"
            MessageType.AUDIO.name -> "audio"
            MessageType.VIDEO.name -> "videos"
            else -> "files"
        }

        val localFile = withContext(Dispatchers.IO) {
            FileUtils.writeByteArrayToFile(context, media.bytes, fileName, subFolder)
        }

        val localPath = localFile?.absolutePath ?: return

        updateOrCreateConversation(
            media.senderAddress,
            media.senderName,
            getMediaPreviewText(messageType)
        )

        val chatMessage = ChatMessage(
            conversationId = media.senderAddress,
            content = getMediaPreviewText(messageType),
            senderName = media.senderName,
            isFromMe = false,
            messageType = messageType,
            mediaUri = localPath,
            mediaFileName = fileName,
            mediaMimeType = mimeType,
            mediaDuration = duration,
            mediaSize = size
        )
        messageDao.insertMessage(chatMessage)
    }

    private fun getMediaPreviewText(messageType: String): String {
        return when (messageType) {
            MessageType.IMAGE.name -> "📷 Image"
            MessageType.AUDIO.name -> "🎵 Audio"
            MessageType.VIDEO.name -> "🎬 Video"
            else -> "📎 File"
        }
    }

    private suspend fun updateOrCreateConversation(deviceAddress: String, deviceName: String, lastMessage: String) {
        val existingConversation = conversationDao.getConversation(deviceAddress)
        if (existingConversation == null) {
            conversationDao.insertConversation(
                Conversation(
                    deviceAddress = deviceAddress,
                    deviceName = deviceName,
                    lastMessage = lastMessage,
                    lastMessageTime = System.currentTimeMillis(),
                    unreadCount = if (_currentConversationId.value == deviceAddress) 0 else 1
                )
            )
        } else {
            conversationDao.updateConversation(
                existingConversation.copy(
                    deviceName = deviceName,
                    lastMessage = lastMessage,
                    lastMessageTime = System.currentTimeMillis(),
                    unreadCount = if (_currentConversationId.value == deviceAddress)
                        0 else existingConversation.unreadCount + 1
                )
            )
        }
    }

    fun setUserName(name: String) {
        _userName.value = name
    }

    fun setRole(role: UserRole) {
        _userRole.value = role

        when (role) {
            UserRole.ASSISTED -> {
                _userName.value = "User"
                bluetoothController.startServer()
            }
            UserRole.ASSISTANT -> {
                _userName.value = "Assistant"
                bluetoothController.updatePairedDevices()
            }
        }
    }

    fun setCurrentConversation(deviceAddress: String, deviceName: String) {
        _currentConversationId.value = deviceAddress

        viewModelScope.launch {
            conversationDao.markAsRead(deviceAddress)

            val existingConversation = conversationDao.getConversation(deviceAddress)
            if (existingConversation == null) {
                conversationDao.insertConversation(
                    Conversation(
                        deviceAddress = deviceAddress,
                        deviceName = deviceName
                    )
                )
            }
        }
    }

    fun clearCurrentConversation() {
        _currentConversationId.value = null
    }

    fun startDiscovery() {
        bluetoothController.startDiscovery()
    }

    fun stopDiscovery() {
        bluetoothController.stopDiscovery()
    }

    fun connectToDevice(device: BluetoothDevice) {
        bluetoothController.connectToDevice(device)
    }

    fun sendMessage(content: String) {
        if (content.isBlank()) return

        val conversationId = _currentConversationId.value ?: return

        viewModelScope.launch {
            val message = ChatMessage(
                conversationId = conversationId,
                content = content,
                senderName = _userName.value,
                isFromMe = true,
                messageType = MessageType.TEXT.name
            )
            messageDao.insertMessage(message)

            updateConversationLastMessage(conversationId, content)

            bluetoothController.sendMessage(content)
        }
    }

    fun sendMedia(mediaInfo: MediaInfo) {
        val conversationId = _currentConversationId.value ?: return

        viewModelScope.launch {
            val message = ChatMessage(
                conversationId = conversationId,
                content = getMediaPreviewText(mediaInfo.messageType.name),
                senderName = _userName.value,
                isFromMe = true,
                messageType = mediaInfo.messageType.name,
                mediaUri = mediaInfo.localPath,
                mediaFileName = mediaInfo.fileName,
                mediaMimeType = mediaInfo.mimeType,
                mediaDuration = mediaInfo.duration,
                mediaSize = mediaInfo.size
            )
            messageDao.insertMessage(message)

            updateConversationLastMessage(conversationId, getMediaPreviewText(mediaInfo.messageType.name))

            withContext(Dispatchers.IO) {
                val bytes = File(mediaInfo.localPath).readBytes()
                val metadata = JSONObject().apply {
                    put("type", mediaInfo.messageType.name)
                    put("fileName", mediaInfo.fileName)
                    put("mimeType", mediaInfo.mimeType)
                    put("size", mediaInfo.size)
                    mediaInfo.duration?.let { put("duration", it) }
                }
                bluetoothController.sendMedia(bytes, metadata)
            }
        }
    }

    private suspend fun updateConversationLastMessage(conversationId: String, lastMessage: String) {
        val conversation = conversationDao.getConversation(conversationId)
        if (conversation != null) {
            conversationDao.updateConversation(
                conversation.copy(
                    lastMessage = lastMessage,
                    lastMessageTime = System.currentTimeMillis()
                )
            )
        }
    }

    fun deleteConversation(deviceAddress: String) {
        viewModelScope.launch {
            messageDao.deleteMessagesForConversation(deviceAddress)
            conversationDao.deleteConversation(deviceAddress)
        }
    }

    fun clearMessages() {
        viewModelScope.launch {
            messageDao.clearAllMessages()
        }
    }

    fun disconnect() {
        bluetoothController.disconnect()
        _currentConversationId.value = null
    }

    fun goBackToHome() {
        disconnect()
        _userRole.value = null
    }

    override fun onCleared() {
        super.onCleared()
        bluetoothController.release()
    }
}

enum class UserRole {
    ASSISTED,
    ASSISTANT
}
