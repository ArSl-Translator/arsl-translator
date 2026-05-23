package com.arsl.offlinechat.ui.components

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Description
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.core.net.toUri
import coil.compose.AsyncImage
import com.arsl.offlinechat.R
import com.arsl.offlinechat.data.ChatMessage
import com.arsl.offlinechat.data.MessageType
import com.arsl.offlinechat.media.FileUtils
import com.arsl.offlinechat.ui.theme.BubbleText
import com.arsl.offlinechat.ui.theme.MutedText
import com.arsl.offlinechat.ui.theme.MyBubble
import com.arsl.offlinechat.ui.theme.OtherBubble
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@Composable
fun MessageBubble(message: ChatMessage) {
    val context = LocalContext.current
    val type = runCatching { MessageType.valueOf(message.messageType) }.getOrDefault(MessageType.TEXT)
    val bubble = if (message.isFromMe) MyBubble else OtherBubble
    val arrangement = if (message.isFromMe) Arrangement.Start else Arrangement.End

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 12.dp, vertical = 3.dp),
        horizontalArrangement = arrangement
    ) {
        Column(
            modifier = Modifier
                .widthIn(min = 96.dp, max = 300.dp)
                .clip(RoundedCornerShape(16.dp))
                .background(bubble)
                .padding(if (type == MessageType.IMAGE || type == MessageType.VIDEO) 6.dp else 12.dp)
        ) {
            if (!message.isFromMe) {
                Text(message.senderName, color = MaterialTheme.colorScheme.primary, style = MaterialTheme.typography.labelMedium)
                Spacer(Modifier.height(3.dp))
            }
            when (type) {
                MessageType.TEXT -> Text(message.content, color = BubbleText, style = MaterialTheme.typography.bodyLarge)
                MessageType.IMAGE -> {
                    val uri = message.mediaPath?.let { pathToUri(it) }
                    AsyncImage(
                        model = uri,
                        contentDescription = stringResource(R.string.media_image),
                        modifier = Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(12.dp)),
                        contentScale = ContentScale.FillWidth
                    )
                }
                MessageType.AUDIO -> MediaRow(Icons.Default.Mic, stringResource(R.string.media_audio), message)
                MessageType.VIDEO -> {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .clip(RoundedCornerShape(12.dp))
                            .background(BubbleText.copy(alpha = 0.08f))
                            .clickable {
                                val uri = message.mediaPath?.let { pathToUri(it) } ?: return@clickable
                                context.startActivity(Intent(Intent.ACTION_VIEW).setDataAndType(uri, "video/*").addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION))
                            }
                            .padding(24.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(Icons.Default.PlayArrow, contentDescription = stringResource(R.string.media_video), modifier = Modifier.size(42.dp))
                    }
                }
                MessageType.FILE -> MediaRow(Icons.Default.Description, message.mediaFileName ?: stringResource(R.string.media_file), message)
            }
            Spacer(Modifier.height(4.dp))
            Text(
                formatTime(message.timestamp),
                color = MutedText,
                style = MaterialTheme.typography.labelSmall,
                modifier = Modifier.align(Alignment.End)
            )
        }
    }
}

@Composable
private fun MediaRow(icon: androidx.compose.ui.graphics.vector.ImageVector, label: String, message: ChatMessage) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Box(
            modifier = Modifier
                .size(42.dp)
                .clip(CircleShape)
                .background(BubbleText.copy(alpha = 0.08f)),
            contentAlignment = Alignment.Center
        ) {
            Icon(icon, contentDescription = null, tint = BubbleText)
        }
        Spacer(Modifier.width(10.dp))
        Column {
            Text(label, color = BubbleText, style = MaterialTheme.typography.bodyMedium)
            val detail = message.mediaDurationMs?.let { FileUtils.formatDuration(it) }
                ?: message.mediaSizeBytes?.let { FileUtils.formatSize(it) }
            if (detail != null) Text(detail, color = MutedText, style = MaterialTheme.typography.labelSmall)
        }
    }
}

private fun pathToUri(path: String): Uri {
    return if (path.startsWith("content:") || path.startsWith("file:")) path.toUri() else File(path).toUri()
}

private fun formatTime(timestamp: Long): String {
    return SimpleDateFormat("HH:mm", Locale.getDefault()).format(Date(timestamp))
}
