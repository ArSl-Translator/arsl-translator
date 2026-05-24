package com.healthcare.offlinechat

import android.app.Application
import com.healthcare.offlinechat.data.AppDatabase

class OfflineChatApplication : Application() {

    val database: AppDatabase by lazy {
        AppDatabase.getDatabase(this)
    }
}
