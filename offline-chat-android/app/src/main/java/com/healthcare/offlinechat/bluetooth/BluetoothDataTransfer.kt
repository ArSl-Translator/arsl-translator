package com.healthcare.offlinechat.bluetooth

import android.bluetooth.BluetoothSocket
import org.json.JSONObject
import java.io.IOException
import java.io.InputStream
import java.io.OutputStream
import java.nio.ByteBuffer
import kotlin.math.min

class BluetoothDataTransfer(
    private val socket: BluetoothSocket,
    private val onMessageReceived: (String) -> Unit,
    private val onMediaReceived: (ByteArray, String) -> Unit,
    private val onConnectionLost: () -> Unit
) {
    private var inputStream: InputStream? = null
    private var outputStream: OutputStream? = null
    private var listeningThread: Thread? = null
    private var isRunning = false

    companion object {
        private const val MESSAGE_TYPE_TEXT: Byte = 0x01
        private const val MESSAGE_TYPE_MEDIA: Byte = 0x02
        private const val CHUNK_SIZE = 8192
    }

    init {
        try {
            inputStream = socket.inputStream
            outputStream = socket.outputStream
        } catch (e: IOException) {
            onConnectionLost()
        }
    }

    fun startListening() {
        isRunning = true

        listeningThread = Thread {
            val stream = inputStream ?: return@Thread

            while (isRunning) {
                try {
                    val typeByte = stream.read()
                    if (typeByte == -1) {
                        isRunning = false
                        onConnectionLost()
                        break
                    }

                    when (typeByte.toByte()) {
                        MESSAGE_TYPE_TEXT -> {
                            val lengthBytes = ByteArray(4)
                            if (!stream.readFully(lengthBytes)) {
                                isRunning = false
                                onConnectionLost()
                                break
                            }
                            val length = ByteBuffer.wrap(lengthBytes).int
                            if (length < 0 || length > 10_000_000) {
                                isRunning = false
                                onConnectionLost()
                                break
                            }
                            val messageBytes = ByteArray(length)
                            if (!stream.readFully(messageBytes)) {
                                isRunning = false
                                onConnectionLost()
                                break
                            }
                            val message = String(messageBytes, Charsets.UTF_8)
                            onMessageReceived(message)
                        }

                        MESSAGE_TYPE_MEDIA -> {
                            val metaLengthBytes = ByteArray(4)
                            if (!stream.readFully(metaLengthBytes)) {
                                isRunning = false
                                onConnectionLost()
                                break
                            }
                            val metaLength = ByteBuffer.wrap(metaLengthBytes).int
                            if (metaLength < 0 || metaLength > 1_000_000) {
                                isRunning = false
                                onConnectionLost()
                                break
                            }
                            val metaBytes = ByteArray(metaLength)
                            if (!stream.readFully(metaBytes)) {
                                isRunning = false
                                onConnectionLost()
                                break
                            }
                            val metadata = String(metaBytes, Charsets.UTF_8)

                            val mediaLengthBytes = ByteArray(8)
                            if (!stream.readFully(mediaLengthBytes)) {
                                isRunning = false
                                onConnectionLost()
                                break
                            }
                            val mediaLength = ByteBuffer.wrap(mediaLengthBytes).long
                            if (mediaLength < 0 || mediaLength > Int.MAX_VALUE.toLong()) {
                                isRunning = false
                                onConnectionLost()
                                break
                            }

                            val mediaBytes = ByteArray(mediaLength.toInt())
                            var mediaRead = 0L
                            while (mediaRead < mediaLength) {
                                val toRead = min(CHUNK_SIZE, (mediaLength - mediaRead).toInt())
                                val read = stream.read(mediaBytes, mediaRead.toInt(), toRead)
                                if (read == -1) {
                                    isRunning = false
                                    onConnectionLost()
                                    break
                                }
                                mediaRead += read
                            }
                            if (mediaRead == mediaLength) {
                                onMediaReceived(mediaBytes, metadata)
                            }
                        }

                        else -> {
                            isRunning = false
                            onConnectionLost()
                            break
                        }
                    }
                } catch (e: IOException) {
                    isRunning = false
                    onConnectionLost()
                    break
                }
            }
        }
        listeningThread?.start()
    }

    private fun InputStream.readFully(buffer: ByteArray): Boolean {
        var offset = 0
        while (offset < buffer.size) {
            val read = read(buffer, offset, buffer.size - offset)
            if (read == -1) return false
            offset += read
        }
        return true
    }

    fun sendMessage(message: String): Boolean {
        return try {
            val messageBytes = message.toByteArray(Charsets.UTF_8)
            val lengthBytes = ByteBuffer.allocate(4).putInt(messageBytes.size).array()
            outputStream?.write(byteArrayOf(MESSAGE_TYPE_TEXT))
            outputStream?.write(lengthBytes)
            outputStream?.write(messageBytes)
            outputStream?.flush()
            true
        } catch (e: IOException) {
            onConnectionLost()
            false
        }
    }

    fun sendMedia(mediaBytes: ByteArray, metadata: JSONObject): Boolean {
        return try {
            val metaBytes = metadata.toString().toByteArray(Charsets.UTF_8)
            val metaLengthBytes = ByteBuffer.allocate(4).putInt(metaBytes.size).array()
            val mediaLengthBytes = ByteBuffer.allocate(8).putLong(mediaBytes.size.toLong()).array()
            outputStream?.write(byteArrayOf(MESSAGE_TYPE_MEDIA))
            outputStream?.write(metaLengthBytes)
            outputStream?.write(metaBytes)
            outputStream?.write(mediaLengthBytes)
            var offset = 0
            while (offset < mediaBytes.size) {
                val chunkSize = min(CHUNK_SIZE, mediaBytes.size - offset)
                outputStream?.write(mediaBytes, offset, chunkSize)
                offset += chunkSize
            }
            outputStream?.flush()
            true
        } catch (e: IOException) {
            onConnectionLost()
            false
        }
    }

    fun close() {
        isRunning = false
        listeningThread?.interrupt()
        try {
            inputStream?.close()
            outputStream?.close()
            socket.close()
        } catch (e: IOException) {
            // Ignore
        }
    }
}
