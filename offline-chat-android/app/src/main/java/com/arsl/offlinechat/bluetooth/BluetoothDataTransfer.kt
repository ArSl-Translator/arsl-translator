package com.arsl.offlinechat.bluetooth

import android.bluetooth.BluetoothSocket
import org.json.JSONObject
import java.io.DataInputStream
import java.io.DataOutputStream
import java.io.IOException

class BluetoothDataTransfer(
    socket: BluetoothSocket,
    private val onTextReceived: (String) -> Unit,
    private val onMediaReceived: (ByteArray, JSONObject) -> Unit,
    private val onConnectionLost: () -> Unit
) {
    private val input = DataInputStream(socket.inputStream)
    private val output = DataOutputStream(socket.outputStream)
    private var running = false
    private var listener: Thread? = null

    companion object {
        private const val TYPE_TEXT = 1
        private const val TYPE_MEDIA = 2
        private const val MAX_MEDIA_BYTES = 25 * 1024 * 1024
    }

    fun startListening() {
        running = true
        listener = Thread {
            while (running) {
                try {
                    when (input.readByte().toInt()) {
                        TYPE_TEXT -> onTextReceived(readString())
                        TYPE_MEDIA -> {
                            val metadata = JSONObject(readString())
                            val size = input.readInt()
                            if (size <= 0 || size > MAX_MEDIA_BYTES) {
                                throw IOException("Unsupported media size: $size")
                            }
                            val media = ByteArray(size)
                            input.readFully(media)
                            onMediaReceived(media, metadata)
                        }
                    }
                } catch (_: IOException) {
                    running = false
                    onConnectionLost()
                }
            }
        }
        listener?.start()
    }

    @Synchronized
    fun sendText(message: String): Boolean {
        return try {
            output.writeByte(TYPE_TEXT)
            writeString(message)
            output.flush()
            true
        } catch (_: IOException) {
            onConnectionLost()
            false
        }
    }

    @Synchronized
    fun sendMedia(bytes: ByteArray, metadata: JSONObject): Boolean {
        return try {
            if (bytes.size > MAX_MEDIA_BYTES) return false
            output.writeByte(TYPE_MEDIA)
            writeString(metadata.toString())
            output.writeInt(bytes.size)
            output.write(bytes)
            output.flush()
            true
        } catch (_: IOException) {
            onConnectionLost()
            false
        }
    }

    fun close() {
        running = false
        try {
            input.close()
            output.close()
        } catch (_: IOException) {
        }
    }

    private fun readString(): String {
        val length = input.readInt()
        val bytes = ByteArray(length)
        input.readFully(bytes)
        return bytes.toString(Charsets.UTF_8)
    }

    private fun writeString(value: String) {
        val bytes = value.toByteArray(Charsets.UTF_8)
        output.writeInt(bytes.size)
        output.write(bytes)
    }
}
