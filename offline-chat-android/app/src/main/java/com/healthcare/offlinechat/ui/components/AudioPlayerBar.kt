package com.healthcare.offlinechat.ui.components

import android.net.Uri
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Pause
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.core.net.toUri
import androidx.media3.common.MediaItem
import androidx.media3.common.Player
import androidx.media3.exoplayer.ExoPlayer
import com.healthcare.offlinechat.R
import com.healthcare.offlinechat.media.FileUtils
import com.healthcare.offlinechat.ui.theme.AudioWaveform
import com.healthcare.offlinechat.ui.theme.LocalChatColors
import com.healthcare.offlinechat.ui.theme.PlayButtonColor
import kotlinx.coroutines.delay
import java.io.File

@Composable
fun AudioPlayerBar(
    audioUri: String,
    duration: Long?,
    isFromMe: Boolean,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val chatColors = LocalChatColors.current

    var isPlaying by remember { mutableStateOf(false) }
    var progress by remember { mutableFloatStateOf(0f) }
    var currentPosition by remember { mutableLongStateOf(0L) }

    val mediaUri = remember(audioUri) {
        when {
            audioUri.startsWith("content:") || audioUri.startsWith("file:") -> Uri.parse(audioUri)
            else -> File(audioUri).toUri()
        }
    }

    val player = remember(audioUri) {
        ExoPlayer.Builder(context).build().apply {
            setMediaItem(MediaItem.fromUri(mediaUri))
            prepare()
        }
    }

    DisposableEffect(audioUri) {
        val listener = object : Player.Listener {
            override fun onPlaybackStateChanged(playbackState: Int) {
                if (playbackState == Player.STATE_ENDED) {
                    isPlaying = false
                    progress = 0f
                    currentPosition = 0L
                    player.seekTo(0)
                }
            }

            override fun onIsPlayingChanged(playing: Boolean) {
                isPlaying = playing
            }
        }
        player.addListener(listener)

        onDispose {
            player.removeListener(listener)
            player.release()
        }
    }

    LaunchedEffect(isPlaying) {
        while (isPlaying) {
            val totalDuration = player.duration.takeIf { it > 0 } ?: (duration ?: 1L)
            currentPosition = player.currentPosition
            progress = currentPosition.toFloat() / totalDuration.toFloat().coerceAtLeast(1f)
            delay(100)
        }
    }

    Row(
        modifier = modifier
            .clip(RoundedCornerShape(8.dp))
            .background(
                if (isFromMe) chatColors.myMessageBackground.copy(alpha = 0.3f)
                else chatColors.otherMessageBackground.copy(alpha = 0.3f)
            )
            .padding(8.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        IconButton(
            onClick = {
                if (isPlaying) {
                    player.pause()
                } else {
                    player.play()
                }
            },
            modifier = Modifier
                .size(40.dp)
                .clip(CircleShape)
                .background(PlayButtonColor)
        ) {
            Icon(
                imageVector = if (isPlaying) Icons.Default.Pause else Icons.Default.PlayArrow,
                contentDescription = if (isPlaying) {
                    stringResource(R.string.pause)
                } else {
                    stringResource(R.string.play)
                },
                tint = Color.White,
                modifier = Modifier.size(24.dp)
            )
        }

        Spacer(modifier = Modifier.width(8.dp))

        Column(
            modifier = Modifier.weight(1f)
        ) {
            LinearProgressIndicator(
                progress = { progress },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(4.dp)
                    .clip(RoundedCornerShape(2.dp)),
                color = AudioWaveform,
                trackColor = AudioWaveform.copy(alpha = 0.3f)
            )

            Spacer(modifier = Modifier.height(4.dp))

            Text(
                text = if (isPlaying || currentPosition > 0) {
                    FileUtils.formatDuration(currentPosition)
                } else {
                    FileUtils.formatDuration(duration ?: 0)
                },
                style = MaterialTheme.typography.labelSmall,
                color = if (isFromMe) chatColors.myMessageText.copy(alpha = 0.7f)
                else chatColors.otherMessageText.copy(alpha = 0.7f)
            )
        }
    }
}
