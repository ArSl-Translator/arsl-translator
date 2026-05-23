package com.arsl.offlinechat.ui.components

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.weight
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AttachFile
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material.icons.filled.Image
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.Videocam
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.arsl.offlinechat.R

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AttachmentSheet(
    onDismiss: () -> Unit,
    onImage: () -> Unit,
    onCamera: () -> Unit,
    onVideo: () -> Unit,
    onAudio: () -> Unit,
    onFile: () -> Unit
) {
    ModalBottomSheet(onDismissRequest = onDismiss) {
        Column(Modifier.padding(18.dp)) {
            Text(stringResource(R.string.attach), style = MaterialTheme.typography.titleLarge)
            Spacer(Modifier.height(12.dp))
            Row(Modifier.fillMaxWidth()) {
                SheetButton(Icons.Default.Image, stringResource(R.string.choose_image), onImage, Modifier.weight(1f))
                SheetButton(Icons.Default.CameraAlt, stringResource(R.string.take_photo), onCamera, Modifier.weight(1f))
                SheetButton(Icons.Default.Videocam, stringResource(R.string.choose_video), onVideo, Modifier.weight(1f))
            }
            Row(Modifier.fillMaxWidth()) {
                SheetButton(Icons.Default.Mic, stringResource(R.string.record_audio), onAudio, Modifier.weight(1f))
                SheetButton(Icons.Default.AttachFile, stringResource(R.string.choose_file), onFile, Modifier.weight(1f))
            }
            Spacer(Modifier.height(24.dp))
        }
    }
}

@Composable
private fun SheetButton(icon: ImageVector, label: String, onClick: () -> Unit, modifier: Modifier = Modifier) {
    Column(
        modifier = modifier
            .clickable(onClick = onClick)
            .padding(12.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Icon(icon, contentDescription = label)
        Spacer(Modifier.height(8.dp))
        Text(label)
    }
}
