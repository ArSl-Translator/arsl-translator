package com.healthcare.offlinechat.ai

object LlamaBridge {
    private val libraryLoaded: Boolean = runCatching {
        System.loadLibrary("arsl_llama")
    }.isSuccess

    fun isAvailable(): Boolean = libraryLoaded

    fun load(modelPath: String): Long {
        ensureAvailable()
        return loadModel(modelPath)
    }

    fun complete(handle: Long, prompt: String, maxTokens: Int, temperature: Float): String {
        ensureAvailable()
        return generate(handle, prompt, maxTokens, temperature)
    }

    fun close(handle: Long) {
        if (libraryLoaded && handle != 0L) {
            freeModel(handle)
        }
    }

    private fun ensureAvailable() {
        if (!libraryLoaded) {
            throw IllegalStateException("Offline AI engine is not installed in this APK")
        }
    }

    private external fun loadModel(modelPath: String): Long
    private external fun generate(
        handle: Long,
        prompt: String,
        maxTokens: Int,
        temperature: Float
    ): String
    private external fun freeModel(handle: Long)
}
