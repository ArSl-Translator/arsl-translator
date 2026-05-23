package com.arsl.offlinechat.ui.screens

import android.Manifest
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.AttachFile
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.arsl.offlinechat.R
import com.arsl.offlinechat.data.ChatMessage
import com.arsl.offlinechat.media.AudioRecorder
import com.arsl.offlinechat.media.MediaHandler
import com.arsl.offlinechat.media.MediaInfo
import com.arsl.offlinechat.ui.components.AttachmentSheet
import com.arsl.offlinechat.ui.components.MessageBubble
import java.io.File

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChatScreen(
    messages: List<ChatMessage>,
    connectionStatus: String,
    isConnected: Boolean,
    conversationName: String,
    onSendText: (String) -> Unit,
    onSendMedia: (MediaInfo) -> Unit,
    onBack: () -> Unit
) {
    val context = LocalContext.current
    val mediaHandler = remember { MediaHandler(context) }
    val audioRecorder = remember { AudioRecorder(context) }
    val listState = rememberLazyListState()
    var input by remember { mutableStateOf("") }
    var attachmentOpen by remember { mutableStateOf(false) }
    var recording by remember { mutableStateOf(false) }
    var photoFile by remember { mutableStateOf<File?>(null) }

    val mediaPicker = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri: Uri? ->
        if (uri != null) onSendMedia(mediaHandler.processPickedUri(uri))
    }
    val takePhoto = rememberLauncherForActivityResult(ActivityResultContracts.TakePicture()) { ok ->
        if (ok) photoFile?.let { onSendMedia(mediaHandler.processCapturedImage(it)) }
    }
    val audioPermission = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted) {
            audioRecorder.start()
            recording = true
        }
    }

    LaunchedEffect(messages.size) {
        if (messages.isNotEmpty()) listState.animateScrollToItem(messages.lastIndex)
    }

    if (attachmentOpen) {
        AttachmentSheet(
            onDismiss = { attachmentOpen = false },
            onImage = {
                attachmentOpen = false
                mediaPicker.launch("image/*")
            },
            onCamera = {
                attachmentOpen = false
                val file = mediaHandler.createImageFile()
                photoFile = file
                takePhoto.launch(mediaHandler.fileUri(file))
            },
            onVideo = {
                attachmentOpen = false
                mediaPicker.launch("video/*")
            },
            onAudio = {
                attachmentOpen = false
                audioPermission.launch(Manifest.permission.RECORD_AUDIO)
            },
            onFile = {
                attachmentOpen = false
                mediaPicker.launch("*/*")
            }
        )
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text(conversationName)
                        Text(connectionStatus, style = MaterialTheme.typography.bodySmall)
                    }
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = null)
                    }
                }
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .imePadding()
        ) {
            Box(Modifier.weight(1f).fillMaxWidth()) {
                if (messages.isEmpty()) {
                    Box(Modifier.fillMaxSize().padding(28.dp), contentAlignment = Alignment.Center) {
                        Text(
                            text = if (isConnected) stringResource(R.string.say_hello) else stringResource(R.string.waiting_for_connection),
                            textAlign = TextAlign.Center
                        )
                    }
                } else {
                    LazyColumn(
                        modifier = Modifier.fillMaxSize(),
                        state = listState,
                        verticalArrangement = Arrangement.spacedBy(2.dp),
                        contentPadding = androidx.compose.foundation.layout.PaddingValues(top = 12.dp, bottom = 12.dp)
                    ) {
                        items(messages, key = { it.id }) { MessageBubble(it) }
                    }
                }
            }

            if (recording) {
                Row(
                    modifier = Modifier.fillMaxWidth().navigationBarsPadding().padding(8.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(stringResource(R.string.recording), modifier = Modifier.weight(1f), color = MaterialTheme.colorScheme.primary)
                    Button(
                        onClick = {
                            audioRecorder.stop()?.let { (file, duration) ->
                                onSendMedia(mediaHandler.processRecordedAudio(file, duration))
                            }
                            recording = false
                        }
                    ) {
                        Icon(Icons.Default.Stop, contentDescription = null)
                        Text(stringResource(R.string.send))
                    }
                }
            } else {
                Row(
                    modifier = Modifier.fillMaxWidth().navigationBarsPadding().padding(8.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    IconButton(onClick = { attachmentOpen = true }, enabled = isConnected) {
                        Icon(Icons.Default.AttachFile, contentDescription = stringResource(R.string.attach))
                    }
                    Spacer(Modifier.width(4.dp))
                    OutlinedTextField(
                        value = input,
                        onValueChange = { input = it },
                        modifier = Modifier.weight(1f),
                        enabled = isConnected,
                        placeholder = { Text(stringResource(R.string.type_message)) },
                        maxLines = 4
                    )
                    Spacer(Modifier.width(4.dp))
                    IconButton(
                        enabled = isConnected && input.isNotBlank(),
                        onClick = {
                            onSendText(input)
                            input = ""
                        }
                    ) {
                        Icon(Icons.AutoMirrored.Filled.Send, contentDescription = stringResource(R.string.send))
                    }
                }
            }
        }
    }
}
