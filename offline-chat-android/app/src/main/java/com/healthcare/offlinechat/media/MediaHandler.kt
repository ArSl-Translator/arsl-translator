package com.healthcare.offlinechat.media

import android.content.Context
import android.media.MediaMetadataRetriever
import android.net.Uri
import androidx.core.content.FileProvider
import com.healthcare.offlinechat.data.MessageType
import java.io.File

data class MediaInfo(
    val uri: Uri,
    val localPath: String,
    val fileName: String,
    val mimeType: String,
    val size: Long,
    val duration: Long? = null,
    val messageType: MessageType
)

class MediaHandler(private val context: Context) {

    fun processMedia(uri: Uri): MediaInfo? {
        return try {
            val mimeType = FileUtils.getMimeType(context, uri)
            val fileName = FileUtils.getFileName(context, uri)
            val size = FileUtils.getFileSize(context, uri)

            val messageType = when {
                mimeType.startsWith("image/") -> MessageType.IMAGE
                mimeType.startsWith("audio/") -> MessageType.AUDIO
                mimeType.startsWith("video/") -> MessageType.VIDEO
                else -> MessageType.FILE
            }

            val subFolder = when (messageType) {
                MessageType.IMAGE -> "images"
                MessageType.AUDIO -> "audio"
                MessageType.VIDEO -> "videos"
                else -> "files"
            }

            val localFile = FileUtils.copyUriToInternalStorage(context, uri, subFolder)
                ?: return null

            val duration = if (messageType == MessageType.AUDIO || messageType == MessageType.VIDEO) {
                getMediaDuration(localFile)
            } else {
                null
            }

            MediaInfo(
                uri = getUriForFile(localFile),
                localPath = localFile.absolutePath,
                fileName = fileName,
                mimeType = mimeType,
                size = size,
                duration = duration,
                messageType = messageType
            )
        } catch (e: Exception) {
            e.printStackTrace()
            null
        }
    }

    fun processAudioRecording(file: File, duration: Long): MediaInfo {
        return MediaInfo(
            uri = getUriForFile(file),
            localPath = file.absolutePath,
            fileName = file.name,
            mimeType = "audio/mp4",
            size = file.length(),
            duration = duration,
            messageType = MessageType.AUDIO
        )
    }

    fun processCapturedPhoto(file: File): MediaInfo {
        return MediaInfo(
            uri = getUriForFile(file),
            localPath = file.absolutePath,
            fileName = file.name,
            mimeType = "image/jpeg",
            size = file.length(),
            duration = null,
            messageType = MessageType.IMAGE
        )
    }

    fun processCapturedVideo(file: File): MediaInfo? {
        return try {
            MediaInfo(
                uri = getUriForFile(file),
                localPath = file.absolutePath,
                fileName = file.name,
                mimeType = "video/mp4",
                size = file.length(),
                duration = getMediaDuration(file),
                messageType = MessageType.VIDEO
            )
        } catch (e: Exception) {
            e.printStackTrace()
            null
        }
    }

    fun getUriForFile(file: File): Uri {
        return FileProvider.getUriForFile(
            context,
            "${context.packageName}.provider",
            file
        )
    }

    fun createImageFile(): File {
        return FileUtils.createMediaFile(context, "IMG", "jpg", "images")
    }

    fun createVideoFile(): File {
        return FileUtils.createMediaFile(context, "VID", "mp4", "videos")
    }

    private fun getMediaDuration(file: File): Long? {
        return try {
            val retriever = MediaMetadataRetriever()
            retriever.setDataSource(file.absolutePath)
            val duration = retriever.extractMetadata(MediaMetadataRetriever.METADATA_KEY_DURATION)
            retriever.release()
            duration?.toLongOrNull()
        } catch (e: Exception) {
            e.printStackTrace()
            null
        }
    }
}
