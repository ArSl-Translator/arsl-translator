package com.healthcare.offlinechat.ai

import android.content.Context

class AiModePreferences(context: Context) {
    private val prefs = context.getSharedPreferences("ai_assistant_settings", Context.MODE_PRIVATE)

    fun getMode(): AiMode {
        return runCatching {
            AiMode.valueOf(prefs.getString(KEY_MODE, AiMode.ONLINE.name) ?: AiMode.ONLINE.name)
        }.getOrDefault(AiMode.ONLINE)
    }

    fun setMode(mode: AiMode) {
        prefs.edit().putString(KEY_MODE, mode.name).apply()
    }

    companion object {
        private const val KEY_MODE = "ai_mode"
    }
}
