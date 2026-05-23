package com.arsl.offlinechat.data

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase

@Database(
    entities = [Conversation::class, ChatMessage::class],
    version = 1,
    exportSchema = false
)
abstract class AppDatabase : RoomDatabase() {
    abstract fun conversationDao(): ConversationDao
    abstract fun chatMessageDao(): ChatMessageDao

    companion object {
        @Volatile private var instance: AppDatabase? = null

        fun getDatabase(context: Context): AppDatabase {
            return instance ?: synchronized(this) {
                val created = Room.databaseBuilder(
                    context.applicationContext,
                    AppDatabase::class.java,
                    "accessible_offline_chat.db"
                ).fallbackToDestructiveMigration().build()
                instance = created
                created
            }
        }
    }
}
