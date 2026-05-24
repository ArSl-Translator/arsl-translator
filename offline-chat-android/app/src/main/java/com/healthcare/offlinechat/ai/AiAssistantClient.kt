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
    suspend fun assist(
        text: String,
        mode: String,
        context: String,
        language: String = "auto"
    ): AiAssistResult = withContext(Dispatchers.IO) {
        val url = URL("${baseUrl.trimEnd('/')}/ai/assist")
        val body = JSONObject().apply {
            put("text", text)
            put("mode", mode)
            put("context", context)
            put("language", language)
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
            AiAssistResult(
                output = json.optString("output"),
                model = json.optString("model"),
                source = json.optString("source")
            )
        } finally {
            connection.disconnect()
        }
    }
}
