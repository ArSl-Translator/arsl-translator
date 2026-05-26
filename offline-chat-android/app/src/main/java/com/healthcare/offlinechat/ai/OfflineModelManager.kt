package com.healthcare.offlinechat.ai

import android.content.Context
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.withContext
import java.io.File
import java.io.FileOutputStream
import java.net.HttpURLConnection
import java.net.URL
import java.security.MessageDigest
import kotlin.math.min

enum class OfflineModelStatus {
    STARTING,
    RESUMING,
    DOWNLOADING,
    RETRYING,
    READY,
    REMOVED
}

data class OfflineModelState(
    val isDownloaded: Boolean = false,
    val isDownloading: Boolean = false,
    val progress: Float = 0f,
    val downloadedBytes: Long = 0L,
    val totalBytes: Long = OfflineAiModel.SIZE_BYTES,
    val status: OfflineModelStatus? = null,
    val retryAttempt: Int = 0,
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

        if (modelFile.exists() && !sha256(modelFile).equals(OfflineAiModel.SHA256, ignoreCase = true)) {
            modelFile.delete()
        }

        var existingBytes = tempFile.length().takeIf { tempFile.exists() } ?: 0L
        _state.value = currentState().copy(
            isDownloading = true,
            progress = (existingBytes.toDouble() / OfflineAiModel.SIZE_BYTES.toDouble()).coerceIn(0.0, 1.0).toFloat(),
            downloadedBytes = existingBytes,
            status = if (existingBytes > 0L) OfflineModelStatus.RESUMING else OfflineModelStatus.STARTING,
            error = null
        )

        try {
            var attempt = 0
            var lastError: Exception? = null

            while (attempt < MAX_ATTEMPTS && tempFile.length() < OfflineAiModel.SIZE_BYTES) {
                attempt += 1
                try {
                    existingBytes = tempFile.length().takeIf { tempFile.exists() } ?: 0L
                    downloadChunk(existingBytes)
                    lastError = null
                } catch (error: Exception) {
                    lastError = error
                    _state.value = _state.value.copy(
                        isDownloading = true,
                        status = OfflineModelStatus.RETRYING,
                        retryAttempt = attempt,
                        error = error.message
                    )
                    Thread.sleep(min(30_000L, 2_000L * attempt))
                }
            }

            if (lastError != null && tempFile.length() < OfflineAiModel.SIZE_BYTES) {
                throw lastError
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
                status = OfflineModelStatus.READY,
                error = null
            )
        } catch (error: Exception) {
            _state.value = currentState().copy(
                isDownloading = false,
                progress = (tempFile.length().toDouble() / OfflineAiModel.SIZE_BYTES.toDouble()).coerceIn(0.0, 1.0).toFloat(),
                downloadedBytes = tempFile.length(),
                error = error.message ?: "Offline AI download failed"
            )
        }
    }

    suspend fun deleteModel() = withContext(Dispatchers.IO) {
        tempFile.delete()
        modelFile.delete()
        _state.value = currentState().copy(status = OfflineModelStatus.REMOVED, error = null)
    }

    fun refresh() {
        _state.value = currentState()
    }

    private fun currentState(): OfflineModelState {
        val downloaded = when {
            modelFile.exists() -> modelFile.length()
            tempFile.exists() -> tempFile.length()
            else -> 0L
        }
        return OfflineModelState(
            isDownloaded = isModelReady(),
            progress = if (isModelReady()) {
                1f
            } else {
                (downloaded.toDouble() / OfflineAiModel.SIZE_BYTES.toDouble()).coerceIn(0.0, 1.0).toFloat()
            },
            downloadedBytes = downloaded,
            totalBytes = OfflineAiModel.SIZE_BYTES
        )
    }

    private fun downloadChunk(existingBytes: Long) {
        val connection = (URL(OfflineAiModel.URL).openConnection() as HttpURLConnection).apply {
            requestMethod = "GET"
            connectTimeout = 30000
            readTimeout = 120000
            setRequestProperty("Accept", "application/octet-stream")
            if (existingBytes > 0L) {
                setRequestProperty("Range", "bytes=$existingBytes-")
            }
        }

        try {
            val statusCode = connection.responseCode
            if (existingBytes > 0L && statusCode == HttpURLConnection.HTTP_OK) {
                tempFile.delete()
                throw IllegalStateException("Server restarted download instead of resuming")
            }
            if (statusCode !in 200..299) {
                throw IllegalStateException("Model download failed with HTTP $statusCode")
            }

            val total = when {
                connection.getHeaderField("Content-Range")?.contains("/") == true ->
                    connection.getHeaderField("Content-Range").substringAfterLast("/").toLongOrNull()
                connection.contentLengthLong > 0L -> existingBytes + connection.contentLengthLong
                else -> OfflineAiModel.SIZE_BYTES
            } ?: OfflineAiModel.SIZE_BYTES

            var downloaded = existingBytes
            connection.inputStream.use { input ->
                FileOutputStream(tempFile, existingBytes > 0L).buffered().use { output ->
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
                            status = OfflineModelStatus.DOWNLOADING,
                            error = null
                        )
                    }
                }
            }
        } finally {
            connection.disconnect()
        }
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

    companion object {
        private const val MAX_ATTEMPTS = 8
    }
}
