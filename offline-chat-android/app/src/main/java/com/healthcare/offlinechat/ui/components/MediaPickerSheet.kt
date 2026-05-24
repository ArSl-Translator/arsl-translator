package com.healthcare.offlinechat.ui.components

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AttachFile
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material.icons.filled.Image
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.VideoLibrary
import androidx.compose.material.icons.filled.Videocam
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.SheetState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.healthcare.offlinechat.R

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MediaPickerSheet(
    sheetState: SheetState,
    onDismiss: () -> Unit,
    onTakePhoto: () -> Unit,
    onChooseImage: () -> Unit,
    onRecordVideo: () -> Unit,
    onChooseVideo: () -> Unit,
    onRecordAudio: () -> Unit,
    onChooseFile: () -> Unit,
    modifier: Modifier = Modifier
) {
    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = sheetState,
        modifier = modifier
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp)
        ) {
            Text(
                text = stringResource(R.string.attachmedia),
                style = MaterialTheme.typography.titleLarge,
                modifier = Modifier.padding(bottom = 16.dp)
            )

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceEvenly
            ) {
                MediaOption(
                    icon = Icons.Default.CameraAlt,
                    label = stringResource(R.string.takephoto),
                    color = Color(0xFFE91E63),
                    onClick = {
                        onDismiss()
                        onTakePhoto()
                    }
                )
                MediaOption(
                    icon = Icons.Default.Image,
                    label = stringResource(R.string.chooseimage),
                    color = Color(0xFF9C27B0),
                    onClick = {
                        onDismiss()
                        onChooseImage()
                    }
                )
                MediaOption(
                    icon = Icons.Default.Videocam,
                    label = stringResource(R.string.recordvideo),
                    color = Color(0xFFFF5722),
                    onClick = {
                        onDismiss()
                        onRecordVideo()
                    }
                )
            }

            Spacer(modifier = Modifier.height(16.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceEvenly
            ) {
                MediaOption(
                    icon = Icons.Default.VideoLibrary,
                    label = stringResource(R.string.choosevideo),
                    color = Color(0xFF00BCD4),
                    onClick = {
                        onDismiss()
                        onChooseVideo()
                    }
                )
                MediaOption(
                    icon = Icons.Default.Mic,
                    label = stringResource(R.string.recordaudio),
                    color = Color(0xFF4CAF50),
                    onClick = {
                        onDismiss()
                        onRecordAudio()
                    }
                )
                MediaOption(
                    icon = Icons.Default.AttachFile,
                    label = stringResource(R.string.choosefile),
                    color = Color(0xFF607D8B),
                    onClick = {
                        onDismiss()
                        onChooseFile()
                    }
                )
            }

            Spacer(modifier = Modifier.height(32.dp))
        }
    }
}

@Composable
private fun MediaOption(
    icon: ImageVector,
    label: String,
    color: Color,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier
            .clip(RoundedCornerShape(12.dp))
            .clickable(onClick = onClick)
            .padding(12.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Icon(
            imageVector = icon,
            contentDescription = label,
            tint = color,
            modifier = Modifier.size(32.dp)
        )
        Spacer(modifier = Modifier.height(8.dp))
        Text(
            text = label,
            style = MaterialTheme.typography.bodySmall
        )
    }
}
