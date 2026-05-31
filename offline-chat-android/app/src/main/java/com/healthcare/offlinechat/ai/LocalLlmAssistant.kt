package com.healthcare.offlinechat.ai

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext

class LocalLlmAssistant(
    private val modelManager: OfflineModelManager,
    private val onlineClient: AiAssistantClient
) {
    private val mutex = Mutex()
    private var handle: Long = 0L

    fun detectLanguage(text: String): String = onlineClient.detectLanguage(text)

    suspend fun assist(
        text: String,
        mode: String,
        context: String,
        language: String = detectLanguage(text)
    ): AiAssistResult = withContext(Dispatchers.IO) {
        if (!modelManager.isModelReady()) {
            throw IllegalStateException("Download offline AI first")
        }
        if (!LlamaBridge.isAvailable()) {
            throw IllegalStateException("Offline AI engine is not installed in this APK")
        }

        mutex.withLock {
            if (handle == 0L) {
                handle = LlamaBridge.load(modelManager.getModelPath())
            }

            val prompt = buildPrompt(text, mode, language)
            val maxTokens = if (mode == "suggestions") 60 else 80
            val raw = LlamaBridge.complete(handle, prompt, maxTokens, 0.0f).trim()
            val cleaned = AiOutputCleaner.clean(raw, mode)
            AiAssistResult(
                output = cleaned.ifBlank { fallback(text, mode, language) },
                model = OfflineAiModel.FILE_NAME,
                source = "offline"
            )
        }
    }

    fun close() {
        LlamaBridge.close(handle)
        handle = 0L
    }

    private fun buildPrompt(text: String, mode: String, language: String): String {
        val input = text.trim().ifBlank {
            if (language == "ar") "اكتب اقتراحات قصيرة مناسبة." else "Write short useful suggestions."
        }

        return when (mode to language) {
            "deaf_to_hearing" to "ar" -> """
                أعد صياغة الرسالة التالية بالعربية الواضحة والطبيعية.
                حافظ على المعنى والفاعل. لا تعكس المعنى. لا تتحدث مع المريض.
                اكتب الإجابة فقط بدون شرح أو أمثلة.

                الإدخال: $input
                الإجابة:
            """.trimIndent()

            "deaf_to_hearing" to "en" -> """
                Rewrite the following message in clear, natural English.
                Preserve the exact meaning and speaker. Do not answer the user.
                Write only the final rewritten message.

                Input: $input
                Answer:
            """.trimIndent()

            "hearing_to_deaf" to "ar" -> """
                بسّط الرسالة التالية إلى عربية قصيرة ومباشرة.
                حافظ على المعنى والفاعل. اكتب الإجابة فقط.

                الإدخال: $input
                الإجابة:
            """.trimIndent()

            "hearing_to_deaf" to "en" -> """
                Simplify the following message into short, direct English.
                Preserve the exact meaning and speaker. Write only the final message.

                Input: $input
                Answer:
            """.trimIndent()

            "suggestions" to "ar" -> """
                اكتب 3 إلى 5 رسائل جاهزة للإرسال من قِبَل المريض.
                كل رسالة من وجهة نظر المريض، وليست من الطاقم الطبي. رقّم الاقتراحات.
                اكتب الاقتراحات فقط.

                الإدخال: $input
                الإجابة:
            """.trimIndent()

            else -> """
                Write one ready-to-send message from the patient.
                The message must be from the patient's perspective.
                Write only the final message.

                Input: $input
                Answer:
            """.trimIndent()
        }
    }

    private fun fallback(text: String, mode: String, language: String): String {
        if (mode != "suggestions") return text
        return if (language == "ar") {
            "أحتاج مساعدة."
        } else {
            "I need help."
        }
    }
}
