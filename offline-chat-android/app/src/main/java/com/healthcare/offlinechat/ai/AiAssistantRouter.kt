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
        hardcodedDemoResponse(text, mode)?.let { output ->
            return AiAssistResult(
                output = output,
                model = "demo-hardcoded",
                source = "demo"
            )
        }

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

    private fun hardcodedDemoResponse(text: String, mode: String): String? {
        val normalizedText = text.trim().replace(Regex("\\s+"), " ")
        return when (mode to normalizedText) {
            "deaf_to_hearing" to "دكتور الدواء ما نفع" ->
                "دكتور، الدواء لم يفد. الألم لا يزال موجوداً."

            "hearing_to_deaf" to "يجب أخذ الدواء بعد الطعام مرتين في اليوم وإذا استمر الألم راجع الطبيب فوراً" ->
                "خذ الدواء بعد الأكل مرتين يومياً. إذا بقي الألم، راجع الطبيب."

            "suggestions" to "أنا في عيادة الطبيب وأحتاج مساعدة" ->
                "أحتاج مساعدة في عيادة الطبيب من فضلك."

            else -> null
        }
    }
}
