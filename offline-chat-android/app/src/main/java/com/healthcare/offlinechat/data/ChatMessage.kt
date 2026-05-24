package com.healthcare.offlinechat.data

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "chatmessages")
data class ChatMessage(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    val conversationId: String,
    val content: String,
    val senderName: String,
    val isFromMe: Boolean,
    val messageType: String = MessageType.TEXT.name,
    val mediaUri: String? = null,
    val mediaFileName: String? = null,
    val mediaMimeType: String? = null,
    val mediaDuration: Long? = null,
    val mediaSize: Long? = null,
    val timestamp: Long = System.currentTimeMillis()
)
