package com.arsl.offlinechat.bluetooth

import android.annotation.SuppressLint
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothSocket
import java.io.IOException

@SuppressLint("MissingPermission")
class BluetoothServer(
    private val adapter: BluetoothAdapter,
    private val onConnected: (BluetoothSocket) -> Unit,
    private val onError: (String) -> Unit
) : Thread("BluetoothServer") {
    private val serverSocket = try {
        adapter.listenUsingRfcommWithServiceRecord(
            BluetoothController.SERVICE_NAME,
            BluetoothController.SERVICE_UUID
        )
    } catch (error: IOException) {
        onError(error.message ?: "Cannot create Bluetooth server socket")
        null
    }

    override fun run() {
        try {
            val socket = serverSocket?.accept()
            if (socket != null) onConnected(socket)
        } catch (error: IOException) {
            onError(error.message ?: "Bluetooth server stopped")
        } finally {
            cancel()
        }
    }

    fun cancel() {
        try {
            serverSocket?.close()
        } catch (_: IOException) {
        }
    }
}
