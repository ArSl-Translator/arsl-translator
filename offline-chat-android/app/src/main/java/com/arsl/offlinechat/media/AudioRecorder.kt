package com.arsl.offlinechat.media

import android.content.Context
import android.media.MediaRecorder
import android.os.Build
import java.io.File

class AudioRecorder(private val context: Context) {
    private var recorder: MediaRecorder? = null
    private var file: File? = null
    private var startedAt: Long = 0L

    fun start(): File {
        val output = MediaHandler(context).createAudioFile()
        file = output
        recorder = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            MediaRecorder(context)
        } else {
            @Suppress("DEPRECATION")
            MediaRecorder()
        }.apply {
            setAudioSource(MediaRecorder.AudioSource.MIC)
            setOutputFormat(MediaRecorder.OutputFormat.MPEG_4)
            setAudioEncoder(MediaRecorder.AudioEncoder.AAC)
            setOutputFile(output.absolutePath)
            prepare()
            start()
        }
        startedAt = System.currentTimeMillis()
        return output
    }

    fun stop(): Pair<File, Long>? {
        val output = file ?: return null
        val duration = System.currentTimeMillis() - startedAt
        try {
            recorder?.stop()
        } catch (_: RuntimeException) {
            output.delete()
            return null
        } finally {
            recorder?.release()
            recorder = null
        }
        return output to duration
    }

    fun cancel() {
        try {
            recorder?.stop()
        } catch (_: RuntimeException) {
        } finally {
            recorder?.release()
            recorder = null
            file?.delete()
            file = null
        }
    }
}
