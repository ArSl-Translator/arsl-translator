package com.arsl.offlinechat.media

import android.content.Context
import android.net.Uri
import android.provider.OpenableColumns
import java.io.File
import java.io.FileOutputStream
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

object FileUtils {
    fun displayName(context: Context, uri: Uri): String {
        context.contentResolver.query(uri, null, null, null, null)?.use { cursor ->
            val index = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
            if (index >= 0 && cursor.moveToFirst()) return cursor.getString(index)
        }
        return "file-${System.currentTimeMillis()}"
    }

    fun size(context: Context, uri: Uri): Long {
        context.contentResolver.query(uri, null, null, null, null)?.use { cursor ->
            val index = cursor.getColumnIndex(OpenableColumns.SIZE)
            if (index >= 0 && cursor.moveToFirst()) return cursor.getLong(index)
        }
        return 0L
    }

    fun mimeType(context: Context, uri: Uri): String {
        return context.contentResolver.getType(uri) ?: "application/octet-stream"
    }

    fun copyUri(context: Context, uri: Uri, folderName: String): File {
        val folder = File(context.filesDir, folderName).also { it.mkdirs() }
        val target = File(folder, displayName(context, uri))
        context.contentResolver.openInputStream(uri).use { input ->
            FileOutputStream(target).use { output ->
                requireNotNull(input).copyTo(output)
            }
        }
        return target
    }

    fun newMediaFile(context: Context, prefix: String, extension: String, folderName: String): File {
        val stamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())
        val folder = File(context.filesDir, folderName).also { it.mkdirs() }
        return File(folder, "$prefix-$stamp.$extension")
    }

    fun writeBytes(context: Context, bytes: ByteArray, fileName: String, folderName: String): File {
        val folder = File(context.filesDir, folderName).also { it.mkdirs() }
        val safeName = fileName.replace(Regex("""[\\/:*?"<>|]"""), "_")
        return File(folder, safeName).also { file ->
            FileOutputStream(file).use { it.write(bytes) }
        }
    }

    fun formatSize(size: Long): String {
        return when {
            size < 1024 -> "$size B"
            size < 1024 * 1024 -> "${size / 1024} KB"
            else -> "${size / (1024 * 1024)} MB"
        }
    }

    fun formatDuration(durationMs: Long): String {
        val totalSeconds = durationMs / 1000
        val minutes = totalSeconds / 60
        val seconds = totalSeconds % 60
        return "%d:%02d".format(minutes, seconds)
    }
}
