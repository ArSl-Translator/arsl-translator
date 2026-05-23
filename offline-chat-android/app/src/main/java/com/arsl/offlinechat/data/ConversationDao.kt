package com.arsl.offlinechat.data

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import kotlinx.coroutines.flow.Flow

@Dao
interface ConversationDao {
    @Query("SELECT * FROM conversations ORDER BY lastMessageTime DESC")
    fun getAllConversations(): Flow<List<Conversation>>

    @Query("SELECT * FROM conversations WHERE deviceAddress = :deviceAddress")
    suspend fun getConversation(deviceAddress: String): Conversation?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertConversation(conversation: Conversation)

    @Update
    suspend fun updateConversation(conversation: Conversation)

    @Query("UPDATE conversations SET unreadCount = 0 WHERE deviceAddress = :deviceAddress")
    suspend fun markAsRead(deviceAddress: String)

    @Query("DELETE FROM conversations WHERE deviceAddress = :deviceAddress")
    suspend fun deleteConversation(deviceAddress: String)
}
