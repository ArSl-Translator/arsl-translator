package com.arsl.offlinechat

import android.content.Context
import android.content.res.Configuration
import java.util.Locale

object LocaleHelper {
    fun arabicContext(context: Context): Context {
        val locale = Locale("ar")
        Locale.setDefault(locale)
        val config = Configuration(context.resources.configuration)
        config.setLocale(locale)
        config.setLayoutDirection(locale)
        return context.createConfigurationContext(config)
    }
}
