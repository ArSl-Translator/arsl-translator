package com.arsl.offlinechat.bluetooth

import org.json.JSONObject

data class IncomingText(
    val content: String,
    val senderAddress: String,
    val senderName: String
)

data class IncomingMedia(
    val bytes: ByteArray,
    val metadata: JSONObject,
    val senderAddress: String,
    val senderName: String
) {
    override fun equals(other: Any?): Boolean {
        return other is IncomingMedia &&
            bytes.contentEquals(other.bytes) &&
            metadata.toString() == other.metadata.toString() &&
            senderAddress == other.senderAddress
    }

    override fun hashCode(): Int {
        var result = bytes.contentHashCode()
        result = 31 * result + metadata.toString().hashCode()
        result = 31 * result + senderAddress.hashCode()
        return result
    }
}
