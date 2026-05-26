package com.healthcare.offlinechat.ai

import android.content.Context
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.withContext
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import java.security.MessageDigest

data class OfflineModelState(
    val isDownloaded: Boolean = false,
    val isDownloading: Boolean = false,
    val progress: Float = 0f,
    val downloadedBytes: Long = 0L,
    val totalBytes: Long = OfflineAiModel.SIZE_BYTES,
    val status: String? = null,
    val error: String? = null
)

class OfflineModelManager(context: Context) {
    private val appContext = context.applicationContext
    private val modelsDir = File(appContext.filesDir, "models")
    private val modelFile = File(modelsDir, OfflineAiModel.FILE_NAME)
    private val tempFile = File(modelsDir, "${OfflineAiModel.FILE_NAME}.tmp")

    private val _state = MutableStateFlow(currentState())
    val state: StateFlow<OfflineModelState> = _state.asStateFlow()

    fun getModelPath(): String = modelFile.absolutePath

    fun isModelReady(): Boolean = modelFile.isFile && modelFile.length() > 0L

    suspend fun downloadModel() = withContext(Dispatchers.IO) {
        if (_state.value.isDownloading) return@withContext
        modelsDir.mkdirs()
        tempFile.delete()

        _state.value = currentState().copy(
            isDownloading = true,
            progress = 0f,
            downloadedBytes = 0L,
            status = "Starting download",
            error = null
        )

        try {
            val connection = (URL(OfflineAiModel.URL).openConnection() as HttpURLConnection).apply {
                requestMethod = "GET"
                connectTimeout = 15000
                readTimeout = 120000
                setRequestProperty("Accept", "application/octet-stream")
            }

            try {
                val statusCode = connection.responseCode
                if (statusCode !in 200..299) {
                    throw IllegalStateException("Model download failed with HTTP $statusCode")
                }

                val total = connection.contentLengthLong.takeIf { it > 0L } ?: OfflineAiModel.SIZE_BYTES
                var downloaded = 0L

                connection.inputStream.use { input ->
                    tempFile.outputStream().buffered().use { output ->
                        val buffer = ByteArray(DEFAULT_BUFFER_SIZE)
                        while (true) {
                            val read = input.read(buffer)
                            if (read == -1) break
                            output.write(buffer, 0, read)
                            downloaded += read

                            val progress = (downloaded.toDouble() / total.toDouble())
                                .coerceIn(0.0, 1.0)
                                .toFloat()
                            _state.value = _state.value.copy(
                                isDownloading = true,
                                progress = progress,
                                downloadedBytes = downloaded,
                                totalBytes = total,
                                status = "Downloading offline AI"
                            )
                        }
                    }
                }
            } finally {
                connection.disconnect()
            }

            val actualHash = sha256(tempFile)
            if (!actualHash.equals(OfflineAiModel.SHA256, ignoreCase = true)) {
                tempFile.delete()
                throw IllegalStateException("Downloaded model checksum did not match")
            }

            if (modelFile.exists()) modelFile.delete()
            if (!tempFile.renameTo(modelFile)) {
                throw IllegalStateException("Could not save offline model")
            }

            _state.value = currentState().copy(
                status = "Offline AI is ready",
                error = null
            )
        } catch (error: Exception) {
            tempFile.delete()
            _state.value = currentState().copy(
                isDownloading = false,
                progress = 0f,
                error = error.message ?: "Offline AI download failed"
            )
        }
    }

    suspend fun deleteModel() = withContext(Dispatchers.IO) {
        tempFile.delete()
        modelFile.delete()
        _state.value = currentState().copy(status = "Offline AI removed", error = null)
    }

    fun refresh() {
        _state.value = currentState()
    }

    private fun currentState(): OfflineModelState {
        val downloaded = modelFile.length().takeIf { modelFile.exists() } ?: 0L
        return OfflineModelState(
            isDownloaded = isModelReady(),
            progress = if (isModelReady()) 1f else 0f,
            downloadedBytes = downloaded,
            totalBytes = OfflineAiModel.SIZE_BYTES
        )
    }

    private fun sha256(file: File): String {
        val digest = MessageDigest.getInstance("SHA-256")
        file.inputStream().buffered().use { input ->
            val buffer = ByteArray(DEFAULT_BUFFER_SIZE)
            while (true) {
                val read = input.read(buffer)
                if (read == -1) break
                digest.update(buffer, 0, read)
            }
        }
        return digest.digest().joinToString("") { "%02x".format(it) }
    }
}
