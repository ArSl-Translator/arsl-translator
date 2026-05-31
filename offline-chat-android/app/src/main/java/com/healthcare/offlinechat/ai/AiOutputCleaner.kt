package com.healthcare.offlinechat.ai

object AiOutputCleaner {
    fun clean(output: String, mode: String): String {
        var cleaned = output.replace("\r\n", "\n").replace("\r", "\n").trim()
        val cutMarkers = listOf(
            "←",
            "\nالإجابة:",
            "\nAnswer:",
            "\nInput:",
            "\nالإدخال:",
            "\nمثال",
            "\nBad ",
            "\nGood ",
            "\nRules:",
            "\nTask:",
            "\nالقواعد:",
            "\nالمهمة:",
            " يجب إعادة",
            " لا تتحدث",
            " حافظ على",
            " المعنى صحيح",
            " المعنى واضح",
            " كيف يمكنني مساعدتك؟",
            " هل يمكنك كتابة الرسالة؟",
            " لكن يمكنني مساعدتك"
        )

        cutMarkers.forEach { marker ->
            val index = cleaned.indexOf(marker)
            if (index > 0) cleaned = cleaned.substring(0, index).trim()
        }

        cleaned = cleaned.replace("دواعش شديدة", "دوار شديد").replace("دواعش", "دوار")

        return if (mode == "suggestions") {
            cleanSuggestions(cleaned)
        } else {
            cleaned.lineSequence().firstOrNull()?.trim().orEmpty().trim(' ', '\n', '\t', ':', '-')
        }
    }

    private fun cleanSuggestions(output: String): String {
        val blocked = listOf("كيف يمكنني مساعدتك", "هل تحتاج", "do you need", "how can i help")
        val lines = output.lines()
            .map { it.trim() }
            .filter { it.isNotBlank() }
            .filter { line -> blocked.none { line.contains(it, ignoreCase = true) } }

        return lines.take(1).mapIndexedNotNull { index, line ->
            val text = line.replace(Regex("^\\s*\\d+\\s*[.)-]\\s*"), "").trim()
            if (text.isBlank()) null else "${index + 1}. $text"
        }.joinToString("\n")
    }
}
