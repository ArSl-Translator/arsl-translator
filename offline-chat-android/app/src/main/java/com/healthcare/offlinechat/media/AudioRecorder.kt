package com.healthcare.offlinechat.media

import android.content.Context
import android.media.MediaRecorder
import android.os.Build
import java.io.File

class AudioRecorder(private val context: Context) {

    private var recorder: MediaRecorder? = null
    private var currentFile: File? = null
    private var startTime: Long = 0

    fun startRecording(): File? {
        val file = FileUtils.createMediaFile(context, "audio", "m4a", "audio")
        currentFile = file

        recorder = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            MediaRecorder(context)
        } else {
            @Suppress("DEPRECATION")
            MediaRecorder()
        }

        recorder?.apply {
            setAudioSource(MediaRecorder.AudioSource.MIC)
            setOutputFormat(MediaRecorder.OutputFormat.MPEG_4)
            setAudioEncoder(MediaRecorder.AudioEncoder.AAC)
            setAudioEncodingBitRate(128000)
            setAudioSamplingRate(44100)
            setOutputFile(file.absolutePath)

            try {
                prepare()
                start()
                startTime = System.currentTimeMillis()
            } catch (e: Exception) {
                e.printStackTrace()
                return null
            }
        }

        return file
    }

    fun stopRecording(): Pair<File?, Long>? {
        val duration = System.currentTimeMillis() - startTime

        return try {
            recorder?.apply {
                stop()
                release()
            }
            recorder = null
            Pair(currentFile, duration)
        } catch (e: Exception) {
            e.printStackTrace()
            recorder?.release()
            recorder = null
            null
        }
    }

    fun cancelRecording() {
        try {
            recorder?.apply {
                stop()
                release()
            }
        } catch (e: Exception) {
            recorder?.release()
        }
        recorder = null
        currentFile?.delete()
        currentFile = null
    }

    fun isRecording(): Boolean = recorder != null
}
