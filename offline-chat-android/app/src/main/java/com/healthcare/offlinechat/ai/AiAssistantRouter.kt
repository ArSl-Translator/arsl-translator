package com.healthcare.offlinechat.ai

class AiAssistantRouter(
    private val preferences: AiModePreferences,
    private val onlineClient: AiAssistantClient,
    private val localAssistant: LocalLlmAssistant,
    private val modelManager: OfflineModelManager
) {
    fun detectLanguage(text: String): String = onlineClient.detectLanguage(text)

    fun getMode(): AiMode = preferences.getMode()

    fun setMode(mode: AiMode) {
        preferences.setMode(mode)
    }

    suspend fun assist(
        text: String,
        mode: String,
        context: String,
        language: String = detectLanguage(text)
    ): AiAssistResult {
        return if (preferences.getMode() == AiMode.OFFLINE) {
            if (!modelManager.isModelReady()) {
                throw IllegalStateException("Download offline AI first")
            }
            localAssistant.assist(text, mode, context, language)
        } else {
            onlineClient.assist(text, mode, context, language)
        }
    }

    fun close() {
        localAssistant.close()
    }
}
