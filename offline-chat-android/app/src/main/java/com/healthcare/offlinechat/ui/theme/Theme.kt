package com.healthcare.offlinechat.ui.theme

import android.app.Activity
import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.SideEffect
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat

data class ChatColors(
    val myMessageBackground: Color,
    val myMessageText: Color,
    val otherMessageBackground: Color,
    val otherMessageText: Color,
    val timestampText: Color
)

val LocalChatColors = staticCompositionLocalOf {
    ChatColors(
        myMessageBackground = MessageBubbleMine,
        myMessageText = MessageBubbleMineText,
        otherMessageBackground = MessageBubbleOther,
        otherMessageText = MessageBubbleOtherText,
        timestampText = Color(0xFF667781)
    )
}

private val DarkColorScheme = darkColorScheme(
    primary = Purple80,
    secondary = PurpleGrey80,
    tertiary = Pink80,
    background = Color(0xFF0B141A),
    surface = Color(0xFF1F2C34)
)

private val LightColorScheme = lightColorScheme(
    primary = AssistedBlue,
    secondary = AssistantPurple,
    tertiary = Pink40,
    background = Color(0xFFF0F2F5),
    surface = Color.White
)

private val LightChatColors = ChatColors(
    myMessageBackground = MessageBubbleMine,
    myMessageText = MessageBubbleMineText,
    otherMessageBackground = MessageBubbleOther,
    otherMessageText = MessageBubbleOtherText,
    timestampText = Color(0xFF667781)
)

private val DarkChatColors = ChatColors(
    myMessageBackground = MessageBubbleMineDark,
    myMessageText = MessageBubbleMineTextDark,
    otherMessageBackground = MessageBubbleOtherDark,
    otherMessageText = MessageBubbleOtherTextDark,
    timestampText = Color(0xFF8696A0)
)

@Composable
fun OfflineChatTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    dynamicColor: Boolean = false,
    content: @Composable () -> Unit
) {
    val colorScheme = when {
        dynamicColor && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> {
            val context = LocalContext.current
            if (darkTheme) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
        }
        darkTheme -> DarkColorScheme
        else -> LightColorScheme
    }

    val chatColors = if (darkTheme) DarkChatColors else LightChatColors

    val view = LocalView.current
    if (!view.isInEditMode) {
        SideEffect {
            val window = (view.context as Activity).window
            window.statusBarColor = colorScheme.primary.toArgb()
            WindowCompat.getInsetsController(window, view).isAppearanceLightStatusBars = !darkTheme
        }
    }

    CompositionLocalProvider(
        LocalChatColors provides chatColors
    ) {
        MaterialTheme(
            colorScheme = colorScheme,
            typography = Typography,
            content = content
        )
    }
}
