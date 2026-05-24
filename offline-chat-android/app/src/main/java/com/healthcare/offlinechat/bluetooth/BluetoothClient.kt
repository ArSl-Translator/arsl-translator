package com.healthcare.offlinechat.bluetooth

import android.annotation.SuppressLint
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothSocket
import java.io.IOException

@SuppressLint("MissingPermission")
class BluetoothClient(
    private val device: BluetoothDevice,
    private val onConnectionEstablished: (BluetoothSocket) -> Unit,
    private val onError: (String) -> Unit
) : Thread() {

    private val socket: BluetoothSocket? = try {
        device.createRfcommSocketToServiceRecord(BluetoothController.SERVICE_UUID)
    } catch (e: IOException) {
        onError("Could not create client socket: ${e.message}")
        null
    }

    override fun run() {
        socket?.let { sock ->
            try {
                sock.connect()
                onConnectionEstablished(sock)
            } catch (e: IOException) {
                onError("Connection failed: ${e.message}")
                try {
                    sock.close()
                } catch (closeException: IOException) {
                    // Ignore
                }
            }
        }
    }

    fun cancel() {
        try {
            socket?.close()
        } catch (e: IOException) {
            // Ignore
        }
    }
}
