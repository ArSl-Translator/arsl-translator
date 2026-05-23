package com.arsl.offlinechat

import android.app.Application
import android.content.Context
import com.arsl.offlinechat.data.AppDatabase

class AccessibleChatApplication : Application() {
    val database: AppDatabase by lazy { AppDatabase.getDatabase(this) }

    override fun attachBaseContext(base: Context) {
        super.attachBaseContext(LocaleHelper.arabicContext(base))
    }
}
