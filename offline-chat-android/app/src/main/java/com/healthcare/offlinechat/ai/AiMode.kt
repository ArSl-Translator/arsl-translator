package com.healthcare.offlinechat.ai

enum class AiMode {
    ONLINE,
    OFFLINE
}

object OfflineAiModel {
    const val URL = "https://arsl.hadighazi.com/models/qwen25-healthcare-finetuned-q4.gguf"
    const val FILE_NAME = "qwen25-healthcare-finetuned-q4.gguf"
    const val SHA256 = "d976297d8777616e8b297b544751a6a48155a3e2dada070e60f4a82fbd4f784a"
    const val SIZE_BYTES = 986_047_968L
    const val DISPLAY_SIZE = "941 MB"
}
