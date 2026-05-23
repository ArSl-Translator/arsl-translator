package com.arsl.offlinechat.bluetooth

import android.annotation.SuppressLint
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothSocket
import java.io.IOException

@SuppressLint("MissingPermission")
class BluetoothClient(
    private val device: BluetoothDevice,
    private val onConnected: (BluetoothSocket) -> Unit,
    private val onError: (String) -> Unit
) : Thread("BluetoothClient") {
    private val socket = try {
        device.createRfcommSocketToServiceRecord(BluetoothController.SERVICE_UUID)
    } catch (error: IOException) {
        onError(error.message ?: "Cannot create Bluetooth client socket")
        null
    }

    override fun run() {
        val activeSocket = socket ?: return
        try {
            activeSocket.connect()
            onConnected(activeSocket)
        } catch (error: IOException) {
            onError(error.message ?: "Bluetooth connection failed")
            cancel()
        }
    }

    fun cancel() {
        try {
            socket?.close()
        } catch (_: IOException) {
        }
    }
}
