package com.arsl.offlinechat.media

import android.content.Context
import android.media.MediaMetadataRetriever
import android.net.Uri
import androidx.core.content.FileProvider
import com.arsl.offlinechat.data.MessageType
import java.io.File

data class MediaInfo(
    val path: String,
    val fileName: String,
    val mimeType: String,
    val sizeBytes: Long,
    val durationMs: Long?,
    val type: MessageType
)

class MediaHandler(private val context: Context) {
    fun processPickedUri(uri: Uri): MediaInfo {
        val mimeType = FileUtils.mimeType(context, uri)
        val type = when {
            mimeType.startsWith("image/") -> MessageType.IMAGE
            mimeType.startsWith("audio/") -> MessageType.AUDIO
            mimeType.startsWith("video/") -> MessageType.VIDEO
            else -> MessageType.FILE
        }
        val folder = folderFor(type)
        val file = FileUtils.copyUri(context, uri, folder)
        return MediaInfo(
            path = file.absolutePath,
            fileName = file.name,
            mimeType = mimeType,
            sizeBytes = file.length().takeIf { it > 0 } ?: FileUtils.size(context, uri),
            durationMs = if (type == MessageType.AUDIO || type == MessageType.VIDEO) duration(file) else null,
            type = type
        )
    }

    fun createImageFile(): File = FileUtils.newMediaFile(context, "image", "jpg", "images")
    fun createAudioFile(): File = FileUtils.newMediaFile(context, "audio", "m4a", "audio")

    fun fileUri(file: File): Uri {
        return FileProvider.getUriForFile(context, "${context.packageName}.provider", file)
    }

    fun processCapturedImage(file: File): MediaInfo {
        return MediaInfo(file.absolutePath, file.name, "image/jpeg", file.length(), null, MessageType.IMAGE)
    }

    fun processRecordedAudio(file: File, durationMs: Long): MediaInfo {
        return MediaInfo(file.absolutePath, file.name, "audio/mp4", file.length(), durationMs, MessageType.AUDIO)
    }

    private fun duration(file: File): Long? {
        return try {
            val retriever = MediaMetadataRetriever()
            retriever.setDataSource(file.absolutePath)
            val value = retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION)
            retriever.release()
            value?.toLongOrNull()
        } catch (_: Exception) {
            null
        }
    }

    private fun folderFor(type: MessageType): String {
        return when (type) {
            MessageType.IMAGE -> "images"
            MessageType.AUDIO -> "audio"
            MessageType.VIDEO -> "videos"
            MessageType.FILE, MessageType.TEXT -> "files"
        }
    }
}
