package com.healthcare.offlinechat.ai

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

data class AiAssistResult(
    val output: String,
    val model: String,
    val source: String
)

class AiAssistantClient(
    private val baseUrl: String = "https://arsl.hadighazi.com/api"
) {
    fun detectLanguage(text: String): String {
        return when {
            text.any { it.isArabicScript() } -> "ar"
            text.isBlank() -> "ar"
            else -> "en"
        }
    }

    suspend fun assist(
        text: String,
        mode: String,
        context: String,
        language: String = detectLanguage(text)
    ): AiAssistResult = withContext(Dispatchers.IO) {
        val url = URL("${baseUrl.trimEnd('/')}/ai/assist")
        val resolvedLanguage = if (language == "ar" || language == "en") language else detectLanguage(text)
        val body = JSONObject().apply {
            put("text", text)
            put("mode", mode)
            put("context", context)
            put("language", resolvedLanguage)
        }.toString().toByteArray(Charsets.UTF_8)

        val connection = (url.openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            connectTimeout = 15000
            readTimeout = 120000
            doOutput = true
            setRequestProperty("Content-Type", "application/json; charset=utf-8")
            setRequestProperty("Accept", "application/json")
        }

        try {
            connection.outputStream.use { it.write(body) }
            val status = connection.responseCode
            val stream = if (status in 200..299) connection.inputStream else connection.errorStream
            val response = stream?.bufferedReader(Charsets.UTF_8)?.use { it.readText() }.orEmpty()

            if (status !in 200..299) {
                throw IllegalStateException("AI assistant request failed ($status): $response")
            }

            val json = JSONObject(response)
            val output = json.optString("output")
            if (isWrongScript(output, resolvedLanguage)) {
                throw IllegalStateException("AI assistant is unavailable")
            }
            AiAssistResult(
                output = output,
                model = json.optString("model"),
                source = json.optString("source")
            )
        } finally {
            connection.disconnect()
        }
    }

    private fun isWrongScript(output: String, language: String): Boolean {
        if (output.any { it.isCjkScript() }) return true

        if (language == "ar") {
            val arabicCount = output.count { it.isArabicScript() }
            val latinCount = output.count { it in 'A'..'Z' || it in 'a'..'z' }
            return arabicCount == 0 || latinCount > arabicCount
        }

        return false
    }

    private fun Char.isArabicScript(): Boolean {
        return this in '\u0600'..'\u06FF' ||
            this in '\u0750'..'\u077F' ||
            this in '\u08A0'..'\u08FF' ||
            this in '\uFB50'..'\uFDFF' ||
            this in '\uFE70'..'\uFEFF'
    }

    private fun Char.isCjkScript(): Boolean {
        return this in '\u3400'..'\u9FFF' ||
            this in '\u3040'..'\u30FF' ||
            this in '\uAC00'..'\uD7AF'
    }
}
