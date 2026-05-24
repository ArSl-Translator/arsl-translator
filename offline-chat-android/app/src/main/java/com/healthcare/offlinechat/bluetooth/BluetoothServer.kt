package com.healthcare.offlinechat.bluetooth

import android.annotation.SuppressLint
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothSocket
import java.io.IOException

@SuppressLint("MissingPermission")
class BluetoothServer(
    private val bluetoothAdapter: BluetoothAdapter,
    private val onConnectionEstablished: (BluetoothSocket) -> Unit,
    private val onError: (String) -> Unit
) : Thread() {

    private val serverSocket = try {
        bluetoothAdapter.listenUsingRfcommWithServiceRecord(
            BluetoothController.SERVICE_NAME,
            BluetoothController.SERVICE_UUID
        )
    } catch (e: IOException) {
        onError("Could not create server socket: ${e.message}")
        null
    }

    override fun run() {
        var shouldLoop = true

        while (shouldLoop) {
            val socket = try {
                serverSocket?.accept()
            } catch (e: IOException) {
                shouldLoop = false
                null
            }

            socket?.let {
                onConnectionEstablished(it)
                serverSocket?.close()
                shouldLoop = false
            }
        }
    }

    fun cancel() {
        try {
            serverSocket?.close()
        } catch (e: IOException) {
        }
    }
}
