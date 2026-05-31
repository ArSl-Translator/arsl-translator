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
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.AttachFile
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Cloud
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Download
import androidx.compose.material.icons.filled.PhoneAndroid
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
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
import com.healthcare.offlinechat.ai.AiAssistantRouter
import com.healthcare.offlinechat.ai.AiMode
import com.healthcare.offlinechat.ai.AiModePreferences
import com.healthcare.offlinechat.ai.AiAssistantClient
import com.healthcare.offlinechat.ai.LocalLlmAssistant
import com.healthcare.offlinechat.ai.LlamaBridge
import com.healthcare.offlinechat.ai.OfflineAiModel
import com.healthcare.offlinechat.ai.OfflineModelManager
import com.healthcare.offlinechat.ai.OfflineModelState
import com.healthcare.offlinechat.ai.OfflineModelStatus
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

private data class SuggestionPrompt(
    val title: String,
    val prompt: String,
    val language: String = "ar"
)

private val suggestionPrompts = listOf(
    SuggestionPrompt("في عيادة الطبيب", "أنا في عيادة الطبيب وأحتاج مساعدة"),
    SuggestionPrompt("لم أفهم الطبيب", "لم أفهم ما قاله الطبيب"),
    SuggestionPrompt("سؤال عن الدواء", "أحتاج أن أعرف كيف أتناول الدواء"),
    SuggestionPrompt("نتيجة التحاليل", "أحتاج معرفة نتيجة التحاليل"),
    SuggestionPrompt("الألم يزداد", "الألم يزداد سوءاً"),
    SuggestionPrompt("مساعدة طارئة", "أحتاج مساعدة طارئة الآن"),
    SuggestionPrompt("التحدث مع الممرضة", "أريد التحدث مع الممرضة"),
    SuggestionPrompt("مساعدة في الفاتورة", "أحتاج مساعدة لفهم الفاتورة"),
    SuggestionPrompt("أنا وحدي", "أنا وحدي في المستشفى وليس معي أحد"),
    SuggestionPrompt("مساعدة للمشي", "أحتاج مساعدة للمشي")
)

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
    val offlineModelManager = remember { OfflineModelManager(context) }
    val aiPreferences = remember { AiModePreferences(context) }
    val localAssistant = remember { LocalLlmAssistant(offlineModelManager, aiClient) }
    val offlineEngineAvailable = remember { LlamaBridge.isAvailable() }
    val aiRouter = remember {
        AiAssistantRouter(
            preferences = aiPreferences,
            onlineClient = aiClient,
            localAssistant = localAssistant,
            modelManager = offlineModelManager
        )
    }
    val offlineModelState by offlineModelManager.state.collectAsState()
    val scope = rememberCoroutineScope()
    val generatingText = stringResource(R.string.generating)

    var messageText by remember { mutableStateOf("") }
    var aiOutputs by remember { mutableStateOf<Map<Long, String>>(emptyMap()) }
    var aiStatus by remember { mutableStateOf<String?>(null) }
    var aiMode by remember { mutableStateOf(aiRouter.getMode()) }
    var showAiSettings by remember { mutableStateOf(false) }
    var showSuggestionPicker by remember { mutableStateOf(false) }
    val listState = rememberLazyListState()

    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    val aiSettingsSheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    val suggestionSheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    var showMediaPicker by remember { mutableStateOf(false) }

    LaunchedEffect(showMediaPicker) {
        if (showMediaPicker) {
            sheetState.show()
        }
    }

    LaunchedEffect(showAiSettings) {
        if (showAiSettings) {
            aiSettingsSheetState.show()
        }
    }

    LaunchedEffect(showSuggestionPicker) {
        if (showSuggestionPicker) {
            suggestionSheetState.show()
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

    if (showAiSettings) {
        ModalBottomSheet(
            onDismissRequest = { showAiSettings = false },
            sheetState = aiSettingsSheetState
        ) {
            AiSettingsSheet(
                aiMode = aiMode,
                offlineModelState = offlineModelState,
                offlineEngineAvailable = offlineEngineAvailable,
                onModeChange = { mode ->
                    aiMode = mode
                    aiRouter.setMode(mode)
                },
                onDownload = {
                    scope.launch {
                        offlineModelManager.downloadModel()
                    }
                },
                onDelete = {
                    scope.launch {
                        offlineModelManager.deleteModel()
                        if (aiMode == AiMode.OFFLINE) {
                            aiMode = AiMode.ONLINE
                            aiRouter.setMode(AiMode.ONLINE)
                        }
                    }
                }
            )
        }
    }

    if (showSuggestionPicker) {
        ModalBottomSheet(
            onDismissRequest = { showSuggestionPicker = false },
            sheetState = suggestionSheetState
        ) {
            SuggestionPromptSheet(
                prompts = suggestionPrompts,
                onSelect = { suggestionPrompt ->
                    showSuggestionPicker = false
                    aiStatus = context.getString(R.string.generatingsuggestions)
                    scope.launch {
                        runCatching {
                            aiRouter.assist(
                                text = suggestionPrompt.prompt,
                                mode = "suggestions",
                                context = "chat",
                                language = suggestionPrompt.language
                            )
                        }.onSuccess { result ->
                            messageText = firstSuggestion(result.output)
                            aiStatus = null
                        }.onFailure { error ->
                            aiStatus = error.message ?: context.getString(R.string.aiunavailable)
                        }
                    }
                }
            )
        }
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
                actions = {
                    IconButton(onClick = { showAiSettings = true }) {
                        Icon(
                            imageVector = Icons.Default.Settings,
                            contentDescription = stringResource(R.string.aisettings),
                            tint = MaterialTheme.colorScheme.onPrimary
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
                                UserRole.ASSISTANT -> stringResource(R.string.makeclearer)
                                UserRole.ASSISTED -> stringResource(R.string.simplify)
                            }
                            MessageBubble(
                                message = message,
                                onImageClick = { selectedImageUri = it },
                                onVideoClick = { selectedVideoUri = it },
                                aiText = aiOutputs[message.id],
                                aiActionLabel = if (!message.isFromMe && message.messageType == com.healthcare.offlinechat.data.MessageType.TEXT.name) aiLabel else null,
                                onAiAction = if (!message.isFromMe && message.messageType == com.healthcare.offlinechat.data.MessageType.TEXT.name) {
                                    {
                                        aiOutputs = aiOutputs + (message.id to generatingText)
                                        scope.launch {
                                            runCatching {
                                                aiRouter.assist(
                                                    text = message.content,
                                                    mode = aiMode,
                                                    context = "chat",
                                                    language = aiRouter.detectLanguage(message.content)
                                                )
                                            }.onSuccess { result ->
                                                aiOutputs = aiOutputs + (message.id to result.output)
                                            }.onFailure { error ->
                                                aiOutputs = aiOutputs + (message.id to (error.message ?: context.getString(R.string.aiunavailable)))
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
                            showSuggestionPicker = true
                        },
                        enabled = isConnected && (aiMode == AiMode.ONLINE || (offlineModelState.isDownloaded && offlineEngineAvailable))
                    ) {
                        Icon(
                            imageVector = Icons.Default.AutoAwesome,
                            contentDescription = stringResource(R.string.aisuggestions),
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

@Composable
private fun SuggestionPromptSheet(
    prompts: List<SuggestionPrompt>,
    onSelect: (SuggestionPrompt) -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 24.dp, vertical = 16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text(
            text = "اختر الحالة",
            style = MaterialTheme.typography.titleLarge
        )
        Text(
            text = "سيحوّلها الذكاء الاصطناعي إلى رسالة واحدة جاهزة للإرسال.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
        )
        LazyColumn(
            modifier = Modifier.heightIn(max = 420.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            items(prompts) { prompt ->
                OutlinedButton(
                    onClick = { onSelect(prompt) },
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text(prompt.title)
                }
            }
        }
    }
}

@Composable
private fun AiSettingsSheet(
    aiMode: AiMode,
    offlineModelState: OfflineModelState,
    offlineEngineAvailable: Boolean,
    onModeChange: (AiMode) -> Unit,
    onDownload: () -> Unit,
    onDelete: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 24.dp, vertical = 16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Text(
            text = stringResource(R.string.aiassistant),
            style = MaterialTheme.typography.titleLarge
        )

        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            FilterChip(
                selected = aiMode == AiMode.ONLINE,
                onClick = { onModeChange(AiMode.ONLINE) },
                label = { Text(stringResource(R.string.aionline)) },
                leadingIcon = {
                    Icon(
                        imageVector = Icons.Default.Cloud,
                        contentDescription = null,
                        modifier = Modifier.size(18.dp)
                    )
                }
            )
            FilterChip(
                selected = aiMode == AiMode.OFFLINE,
                onClick = { onModeChange(AiMode.OFFLINE) },
                enabled = offlineModelState.isDownloaded && offlineEngineAvailable,
                label = { Text(stringResource(R.string.aioffline)) },
                leadingIcon = {
                    Icon(
                        imageVector = Icons.Default.PhoneAndroid,
                        contentDescription = null,
                        modifier = Modifier.size(18.dp)
                    )
                }
            )
        }

        HorizontalDivider()

        Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = stringResource(R.string.offlinemodel),
                    style = MaterialTheme.typography.titleMedium
                )
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        imageVector = if (offlineModelState.isDownloaded) Icons.Default.CheckCircle else Icons.Default.Download,
                        contentDescription = null,
                        tint = if (offlineModelState.isDownloaded) {
                            MaterialTheme.colorScheme.primary
                        } else {
                            MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f)
                        },
                        modifier = Modifier.size(18.dp)
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    Text(
                        text = if (offlineModelState.isDownloaded) {
                            stringResource(R.string.offlinemodelready)
                        } else {
                            stringResource(R.string.offlinemodelnotdownloaded)
                        },
                        style = MaterialTheme.typography.labelMedium
                    )
                }
            }

            Text(
                text = stringResource(R.string.offlinemodelname, OfflineAiModel.DISPLAY_SIZE),
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
            )

            if (offlineModelState.isDownloading) {
                LinearProgressIndicator(
                    progress = { offlineModelState.progress },
                    modifier = Modifier.fillMaxWidth()
                )
                Text(
                    text = "${formatBytes(offlineModelState.downloadedBytes)} / ${formatBytes(offlineModelState.totalBytes)}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.65f)
                )
            }

            offlineModelState.status?.let {
                Text(
                    text = localizedOfflineStatus(offlineModelState),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.primary
                )
            }

            offlineModelState.error?.let {
                Text(
                    text = stringResource(R.string.offlinedownloadfailed),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.error
                )
            }

            if (offlineModelState.isDownloaded && !offlineEngineAvailable) {
                Text(
                    text = stringResource(R.string.offlinemodelenginehint),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.65f)
                )
            }
        }

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Button(
                onClick = onDownload,
                enabled = !offlineModelState.isDownloading,
                modifier = Modifier.weight(1f)
            ) {
                Icon(
                    imageVector = Icons.Default.Download,
                    contentDescription = null,
                    modifier = Modifier.size(18.dp)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    if (offlineModelState.isDownloaded) {
                        stringResource(R.string.redownload)
                    } else {
                        stringResource(R.string.download)
                    }
                )
            }

            OutlinedButton(
                onClick = onDelete,
                enabled = offlineModelState.isDownloaded || offlineModelState.isDownloading,
                modifier = Modifier.weight(1f)
            ) {
                Icon(
                    imageVector = Icons.Default.Delete,
                    contentDescription = null,
                    modifier = Modifier.size(18.dp)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(stringResource(R.string.delete))
            }
        }
    }
}

private fun firstSuggestion(output: String): String {
    return output
        .lineSequence()
        .map { it.trim() }
        .filter { it.isNotBlank() }
        .map { it.replace(Regex("^\\s*\\d+\\s*[.)-]\\s*"), "").trim() }
        .firstOrNull { it.isNotBlank() }
        .orEmpty()
}

private fun formatBytes(bytes: Long): String {
    val mb = bytes.toDouble() / (1024.0 * 1024.0)
    return if (mb >= 1024.0) {
        String.format("%.2f GB", mb / 1024.0)
    } else {
        String.format("%.0f MB", mb)
    }
}

@Composable
private fun localizedOfflineStatus(state: OfflineModelState): String {
    return when (state.status) {
        OfflineModelStatus.STARTING -> stringResource(R.string.downloadstarting)
        OfflineModelStatus.RESUMING -> stringResource(R.string.downloadresuming)
        OfflineModelStatus.DOWNLOADING -> stringResource(R.string.downloadofflineai)
        OfflineModelStatus.RETRYING -> stringResource(
            R.string.downloadretrying,
            state.retryAttempt,
            8
        )
        OfflineModelStatus.READY -> stringResource(R.string.offlineaiready)
        OfflineModelStatus.REMOVED -> stringResource(R.string.offlineairemoved)
        null -> ""
    }
}
