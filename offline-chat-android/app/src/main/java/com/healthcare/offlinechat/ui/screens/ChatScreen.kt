package com.healthcare.offlinechat.ui.screens

import android.Manifest
import android.content.Intent
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
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.core.content.FileProvider
import com.healthcare.offlinechat.R
import com.healthcare.offlinechat.ai.AiAssistantClient
import com.healthcare.offlinechat.data.ChatMessage
import com.healthcare.offlinechat.media.AudioRecorder
import com.healthcare.offlinechat.media.MediaHandler
import com.healthcare.offlinechat.media.MediaInfo
import com.healthcare.offlinechat.ui.components.AudioRecorderBar
import com.healthcare.offlinechat.ui.components.ImageViewer
import com.healthcare.offlinechat.ui.components.MediaPickerSheet
import com.healthcare.offlinechat.ui.components.MessageBubble
import com.healthcare.offlinechat.viewmodel.UserRole
import androidx.core.net.toUri
import java.io.File
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChatScreen(
    messages: List<ChatMessage>,
    connectionStatus: String,
    isConnected: Boolean,
    conversationName: String,
    onSendMessage: (String) -> Unit,
    onSendMedia: (MediaInfo) -> Unit,
    onBack: () -> Unit,
    userRole: UserRole,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val aiClient = remember { AiAssistantClient() }
    val scope = rememberCoroutineScope()

    var messageText by remember { mutableStateOf("") }
    var aiOutputs by remember { mutableStateOf<Map<Long, String>>(emptyMap()) }
    var aiStatus by remember { mutableStateOf<String?>(null) }
    val listState = rememberLazyListState()

    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    var showMediaPicker by remember { mutableStateOf(false) }

    LaunchedEffect(showMediaPicker) {
        if (showMediaPicker) {
            sheetState.show()
        }
    }

    val audioRecorder = remember { AudioRecorder(context) }
    var isRecording by remember { mutableStateOf(false) }

    val mediaHandler = remember { MediaHandler(context) }

    var selectedImageUri by remember { mutableStateOf<String?>(null) }
    var selectedVideoUri by remember { mutableStateOf<String?>(null) }

    var photoFile by remember { mutableStateOf<File?>(null) }
    var videoFile by remember { mutableStateOf<File?>(null) }

    val takePhotoLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.TakePicture()
    ) { success ->
        if (success) {
            photoFile?.let { file ->
                val mediaInfo = mediaHandler.processCapturedPhoto(file)
                onSendMedia(mediaInfo)
            }
        }
    }

    val recordVideoLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.CaptureVideo()
    ) { success ->
        if (success) {
            videoFile?.let { file ->
                mediaHandler.processCapturedVideo(file)?.let { mediaInfo ->
                    onSendMedia(mediaInfo)
                }
            }
        }
    }

    val cameraPermissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (granted) {
            val file = mediaHandler.createImageFile()
            photoFile = file
            val uri = FileProvider.getUriForFile(
                context,
                "${context.packageName}.provider",
                file
            )
            takePhotoLauncher.launch(uri)
        }
    }

    val videoPermissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (granted) {
            val file = mediaHandler.createVideoFile()
            videoFile = file
            val uri = FileProvider.getUriForFile(
                context,
                "${context.packageName}.provider",
                file
            )
            recordVideoLauncher.launch(uri)
        }
    }

    val audioPermissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (granted) {
            audioRecorder.startRecording()
            isRecording = true
        }
    }

    val imagePickerLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.GetContent()
    ) { uri: Uri? ->
        uri?.let {
            mediaHandler.processMedia(it)?.let { mediaInfo -> onSendMedia(mediaInfo) }
        }
    }

    val videoPickerLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.GetContent()
    ) { uri: Uri? ->
        uri?.let {
            mediaHandler.processMedia(it)?.let { mediaInfo -> onSendMedia(mediaInfo) }
        }
    }

    val filePickerLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.GetContent()
    ) { uri: Uri? ->
        uri?.let {
            mediaHandler.processMedia(it)?.let { mediaInfo -> onSendMedia(mediaInfo) }
        }
    }

    LaunchedEffect(messages.size) {
        if (messages.isNotEmpty()) {
            listState.animateScrollToItem(messages.size - 1)
        }
    }

    LaunchedEffect(selectedVideoUri) {
        val path = selectedVideoUri ?: return@LaunchedEffect
        val uri = when {
            path.startsWith("content:") || path.startsWith("file:") -> Uri.parse(path)
            else -> File(path).toUri()
        }
        val intent = Intent(Intent.ACTION_VIEW).apply {
            setDataAndType(uri, "video/*")
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        runCatching { context.startActivity(intent) }
        selectedVideoUri = null
    }

    selectedImageUri?.let { uri ->
        ImageViewer(
            imageUri = uri,
            onDismiss = { selectedImageUri = null }
        )
    }

    if (showMediaPicker) {
        MediaPickerSheet(
            sheetState = sheetState,
            onDismiss = { showMediaPicker = false },
            onTakePhoto = {
                cameraPermissionLauncher.launch(Manifest.permission.CAMERA)
            },
            onChooseImage = {
                imagePickerLauncher.launch("image/*")
            },
            onRecordVideo = {
                videoPermissionLauncher.launch(Manifest.permission.CAMERA)
            },
            onChooseVideo = {
                videoPickerLauncher.launch("video/*")
            },
            onRecordAudio = {
                audioPermissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
            },
            onChooseFile = {
                filePickerLauncher.launch("*/*")
            }
        )
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text(conversationName)
                        Text(
                            text = connectionStatus,
                            style = MaterialTheme.typography.bodySmall
                        )
                    }
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(
                            imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                            contentDescription = stringResource(R.string.back)
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primary,
                    titleContentColor = MaterialTheme.colorScheme.onPrimary,
                    navigationIconContentColor = MaterialTheme.colorScheme.onPrimary
                )
            )
        }
    ) { paddingValues ->
        Column(
            modifier = modifier
                .fillMaxSize()
                .padding(paddingValues)
                .imePadding()
        ) {
            Box(
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth()
            ) {
                if (messages.isEmpty()) {
                    Box(
                        modifier = Modifier.fillMaxSize(),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = if (isConnected) {
                                stringResource(R.string.nomessagesconnected)
                            } else {
                                stringResource(R.string.nomessageswaiting)
                            },
                            style = MaterialTheme.typography.bodyLarge,
                            textAlign = TextAlign.Center,
                            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f)
                        )
                    }
                } else {
                    LazyColumn(
                        modifier = Modifier.fillMaxSize(),
                        state = listState,
                        verticalArrangement = Arrangement.spacedBy(4.dp)
                    ) {
                        items(
                            items = messages,
                            key = { it.id }
                        ) { message ->
                            val aiMode = when (userRole) {
                                UserRole.ASSISTANT -> "deaf_to_hearing"
                                UserRole.ASSISTED -> "hearing_to_deaf"
                            }
                            val aiLabel = when (userRole) {
                                UserRole.ASSISTANT -> "Make clearer"
                                UserRole.ASSISTED -> "Simplify"
                            }
                            MessageBubble(
                                message = message,
                                onImageClick = { selectedImageUri = it },
                                onVideoClick = { selectedVideoUri = it },
                                aiText = aiOutputs[message.id],
                                aiActionLabel = if (!message.isFromMe && message.messageType == com.healthcare.offlinechat.data.MessageType.TEXT.name) aiLabel else null,
                                onAiAction = if (!message.isFromMe && message.messageType == com.healthcare.offlinechat.data.MessageType.TEXT.name) {
                                    {
                                        aiOutputs = aiOutputs + (message.id to "Generating...")
                                        scope.launch {
                                            runCatching {
                                                aiClient.assist(
                                                    text = message.content,
                                                    mode = aiMode,
                                                    context = "chat",
                                                    language = "auto"
                                                )
                                            }.onSuccess { result ->
                                                aiOutputs = aiOutputs + (message.id to result.output)
                                            }.onFailure { error ->
                                                aiOutputs = aiOutputs + (message.id to (error.message ?: "AI assistant is unavailable"))
                                            }
                                        }
                                    }
                                } else null
                            )
                        }
                    }
                }
            }

            if (isRecording) {
                AudioRecorderBar(
                    onCancel = {
                        audioRecorder.cancelRecording()
                        isRecording = false
                    },
                    onSend = {
                        val result = audioRecorder.stopRecording()
                        result?.let { (file, duration) ->
                            file?.let {
                                val mediaInfo = mediaHandler.processAudioRecording(it, duration)
                                onSendMedia(mediaInfo)
                            }
                        }
                        isRecording = false
                    },
                    modifier = Modifier.navigationBarsPadding()
                )
            } else {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .navigationBarsPadding()
                        .padding(8.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    IconButton(
                        onClick = { showMediaPicker = true },
                        enabled = isConnected
                    ) {
                        Icon(
                            imageVector = Icons.Default.AttachFile,
                            contentDescription = stringResource(R.string.attachmedia),
                            tint = if (isConnected) {
                                MaterialTheme.colorScheme.primary
                            } else {
                                MaterialTheme.colorScheme.onSurface.copy(alpha = 0.3f)
                            }
                        )
                    }

                    Spacer(modifier = Modifier.width(4.dp))

                    IconButton(
                        onClick = {
                            aiStatus = "Generating suggestions..."
                            scope.launch {
                                runCatching {
                                    aiClient.assist(
                                        text = messageText,
                                        mode = "suggestions",
                                        context = "chat",
                                        language = "auto"
                                    )
                                }.onSuccess { result ->
                                    messageText = result.output
                                    aiStatus = null
                                }.onFailure { error ->
                                    aiStatus = error.message ?: "AI assistant is unavailable"
                                }
                            }
                        },
                        enabled = isConnected
                    ) {
                        Icon(
                            imageVector = Icons.Default.AutoAwesome,
                            contentDescription = "AI suggestions",
                            tint = if (isConnected) {
                                MaterialTheme.colorScheme.primary
                            } else {
                                MaterialTheme.colorScheme.onSurface.copy(alpha = 0.3f)
                            }
                        )
                    }

                    Spacer(modifier = Modifier.width(4.dp))

                    OutlinedTextField(
                        value = messageText,
                        onValueChange = { messageText = it },
                        modifier = Modifier.weight(1f),
                        placeholder = {
                            Text(
                                if (isConnected) stringResource(R.string.typemessage)
                                else stringResource(R.string.waitingconnection)
                            )
                        },
                        enabled = isConnected,
                        maxLines = 4
                    )

                    Spacer(modifier = Modifier.width(4.dp))

                    IconButton(
                        onClick = {
                            if (messageText.isNotBlank()) {
                                onSendMessage(messageText)
                                messageText = ""
                            }
                        },
                        enabled = isConnected && messageText.isNotBlank()
                    ) {
                        Icon(
                            imageVector = Icons.AutoMirrored.Filled.Send,
                            contentDescription = stringResource(R.string.send),
                            tint = if (isConnected && messageText.isNotBlank()) {
                                MaterialTheme.colorScheme.primary
                            } else {
                                MaterialTheme.colorScheme.onSurface.copy(alpha = 0.3f)
                            }
                        )
                    }
                }

                aiStatus?.let { status ->
                    Text(
                        text = status,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f),
                        modifier = Modifier.padding(horizontal = 16.dp, vertical = 4.dp)
                    )
                }
            }
        }
    }
}
