package com.arsl.offlinechat.data

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "chat_messages")
data class ChatMessage(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val conversationId: String,
    val content: String,
    val senderName: String,
    val isFromMe: Boolean,
    val messageType: String = MessageType.TEXT.name,
    val mediaPath: String? = null,
    val mediaFileName: String? = null,
    val mediaMimeType: String? = null,
    val mediaDurationMs: Long? = null,
    val mediaSizeBytes: Long? = null,
    val timestamp: Long = System.currentTimeMillis()
)
