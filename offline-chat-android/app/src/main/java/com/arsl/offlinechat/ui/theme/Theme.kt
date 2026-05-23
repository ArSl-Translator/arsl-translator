package com.arsl.offlinechat.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.ui.unit.LayoutDirection

private val Scheme = lightColorScheme(
    primary = AccessibleBlue,
    secondary = HelperGreen,
    background = AppBackground,
    surface = OtherBubble,
    onPrimary = OtherBubble,
    onSecondary = OtherBubble,
    onBackground = BubbleText,
    onSurface = BubbleText
)

@Composable
fun AccessibleChatTheme(content: @Composable () -> Unit) {
    CompositionLocalProvider(LocalLayoutDirection provides LayoutDirection.Rtl) {
        MaterialTheme(
            colorScheme = Scheme,
            content = content
        )
    }
}
