package com.healthcare.offlinechat.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.Description
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.healthcare.offlinechat.R
import com.healthcare.offlinechat.data.ChatMessage
import com.healthcare.offlinechat.data.MessageType
import com.healthcare.offlinechat.media.FileUtils
import com.healthcare.offlinechat.ui.theme.LocalChatColors
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@Composable
fun MessageBubble(
    message: ChatMessage,
    onImageClick: (String) -> Unit,
    onVideoClick: (String) -> Unit,
    aiText: String? = null,
    aiActionLabel: String? = null,
    onAiAction: (() -> Unit)? = null,
    modifier: Modifier = Modifier
) {
    val chatColors = LocalChatColors.current

    val bubbleColor = if (message.isFromMe) chatColors.myMessageBackground else chatColors.otherMessageBackground
    val textColor = if (message.isFromMe) chatColors.myMessageText else chatColors.otherMessageText
    val alignment = if (message.isFromMe) Arrangement.End else Arrangement.Start

    val messageType = try {
        MessageType.valueOf(message.messageType)
    } catch (e: Exception) {
        MessageType.TEXT
    }

    Row(
        modifier = modifier
            .fillMaxWidth()
            .padding(horizontal = 12.dp, vertical = 4.dp),
        horizontalArrangement = alignment
    ) {
        Box(
            modifier = Modifier
                .widthIn(min = 80.dp, max = 280.dp)
                .shadow(
                    elevation = 1.dp,
                    shape = RoundedCornerShape(
                        topStart = 16.dp,
                        topEnd = 16.dp,
                        bottomStart = if (message.isFromMe) 16.dp else 4.dp,
                        bottomEnd = if (message.isFromMe) 4.dp else 16.dp
                    )
                )
                .clip(
                    RoundedCornerShape(
                        topStart = 16.dp,
                        topEnd = 16.dp,
                        bottomStart = if (message.isFromMe) 16.dp else 4.dp,
                        bottomEnd = if (message.isFromMe) 4.dp else 16.dp
                    )
                )
                .background(bubbleColor)
                .padding(
                    if (messageType == MessageType.IMAGE || messageType == MessageType.VIDEO) 4.dp else 12.dp
                )
        ) {
            Column {
                if (!message.isFromMe) {
                    Text(
                        text = message.senderName,
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.padding(
                            start = if (messageType == MessageType.IMAGE || messageType == MessageType.VIDEO) 8.dp else 0.dp,
                            bottom = 4.dp
                        )
                    )
                }

                when (messageType) {
                    MessageType.TEXT -> {
                        Text(
                            text = message.content,
                            style = MaterialTheme.typography.bodyLarge,
                            color = textColor
                        )
                    }

                    MessageType.IMAGE -> {
                        message.mediaUri?.let { uri ->
                            val model = when {
                                uri.startsWith("content:") || uri.startsWith("file:") -> uri
                                else -> File(uri)
                            }
                            AsyncImage(
                                model = model,
                                contentDescription = stringResource(R.string.imagemessage),
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .clip(RoundedCornerShape(12.dp))
                                    .clickable { onImageClick(uri) },
                                contentScale = ContentScale.FillWidth
                            )
                        }
                    }

                    MessageType.AUDIO -> {
                        message.mediaUri?.let { uri ->
                            AudioPlayerBar(
                                audioUri = uri,
                                duration = message.mediaDuration,
                                isFromMe = message.isFromMe
                            )
                        }
                    }

                    MessageType.VIDEO -> {
                        message.mediaUri?.let { uri ->
                            val model = when {
                                uri.startsWith("content:") || uri.startsWith("file:") -> uri
                                else -> File(uri)
                            }
                            Box(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .clip(RoundedCornerShape(12.dp))
                                    .clickable { onVideoClick(uri) },
                                contentAlignment = Alignment.Center
                            ) {
                                AsyncImage(
                                    model = model,
                                    contentDescription = stringResource(R.string.videomessage),
                                    modifier = Modifier.fillMaxWidth(),
                                    contentScale = ContentScale.FillWidth
                                )

                                Box(
                                    modifier = Modifier
                                        .size(48.dp)
                                        .clip(CircleShape)
                                        .background(Color.Black.copy(alpha = 0.5f)),
                                    contentAlignment = Alignment.Center
                                ) {
                                    Icon(
                                        imageVector = Icons.Default.PlayArrow,
                                        contentDescription = stringResource(R.string.play),
                                        tint = Color.White,
                                        modifier = Modifier.size(32.dp)
                                    )
                                }
                            }

                            message.mediaDuration?.let { duration ->
                                Text(
                                    text = FileUtils.formatDuration(duration),
                                    style = MaterialTheme.typography.labelSmall,
                                    color = textColor.copy(alpha = 0.7f),
                                    modifier = Modifier.padding(top = 4.dp, start = 8.dp)
                                )
                            }
                        }
                    }

                    MessageType.FILE -> {
                        Row(
                            modifier = Modifier
                                .clip(RoundedCornerShape(8.dp))
                                .background(
                                    if (message.isFromMe) chatColors.myMessageBackground.copy(alpha = 0.5f)
                                    else chatColors.otherMessageBackground.copy(alpha = 0.5f)
                                )
                                .padding(8.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(
                                imageVector = Icons.Default.Description,
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.primary,
                                modifier = Modifier.size(32.dp)
                            )

                            Spacer(modifier = Modifier.width(8.dp))

                            Column {
                                Text(
                                    text = message.mediaFileName ?: stringResource(R.string.filemessage),
                                    style = MaterialTheme.typography.bodyMedium,
                                    color = textColor
                                )
                                message.mediaSize?.let { size ->
                                    Text(
                                        text = FileUtils.formatFileSize(size),
                                        style = MaterialTheme.typography.labelSmall,
                                        color = textColor.copy(alpha = 0.7f)
                                    )
                                }
                            }
                        }
                    }
                }

                if (messageType == MessageType.TEXT && aiActionLabel != null && onAiAction != null) {
                    AssistChip(
                        onClick = onAiAction,
                        label = { Text(aiActionLabel) },
                        leadingIcon = {
                            Icon(
                                imageVector = Icons.Default.AutoAwesome,
                                contentDescription = null,
                                modifier = Modifier.size(16.dp)
                            )
                        },
                        modifier = Modifier.padding(top = 8.dp)
                    )
                }

                if (!aiText.isNullOrBlank()) {
                    Text(
                        text = aiText,
                        style = MaterialTheme.typography.bodyMedium,
                        color = textColor,
                        modifier = Modifier
                            .padding(top = 8.dp)
                            .clip(RoundedCornerShape(10.dp))
                            .background(Color.White.copy(alpha = if (message.isFromMe) 0.18f else 0.75f))
                            .padding(8.dp)
                    )
                }

                Text(
                    text = formatTime(message.timestamp),
                    style = MaterialTheme.typography.labelSmall,
                    color = chatColors.timestampText,
                    modifier = Modifier
                        .align(Alignment.End)
                        .padding(
                            top = 4.dp,
                            end = if (messageType == MessageType.IMAGE || messageType == MessageType.VIDEO) 8.dp else 0.dp
                        )
                )
            }
        }
    }
}

private fun formatTime(timestamp: Long): String {
    val sdf = SimpleDateFormat("HH:mm", Locale.getDefault())
    return sdf.format(Date(timestamp))
}
