package com.healthcare.offlinechat.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.Send
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.unit.dp
import com.healthcare.offlinechat.ai.AiAssistantClient
import kotlinx.coroutines.launch

private data class AssistantMode(
    val id: String,
    val label: String,
    val hint: String
)

private val modes = listOf(
    AssistantMode(
        id = "deaf_to_hearing",
        label = "Clear message",
        hint = "Write a simple idea. The assistant makes it clear for a hearing person."
    ),
    AssistantMode(
        id = "hearing_to_deaf",
        label = "Simplify",
        hint = "Paste a hearing person's message. The assistant makes it shorter and easier."
    ),
    AssistantMode(
        id = "phrasebook",
        label = "Phrasebook",
        hint = "Choose a context and generate useful ready-to-send phrases."
    ),
    AssistantMode(
        id = "smart_replies",
        label = "Quick replies",
        hint = "Generate short replies for the selected situation."
    )
)

private val contexts = listOf("general", "clinic", "classroom", "public service", "emergency")

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AiAssistantScreen(
    onBack: () -> Unit,
    modifier: Modifier = Modifier
) {
    val client = remember { AiAssistantClient() }
    val scope = rememberCoroutineScope()
    val clipboard = LocalClipboardManager.current

    var selectedMode by remember { mutableStateOf(modes.first()) }
    var selectedContext by remember { mutableStateOf(contexts.first()) }
    var input by remember { mutableStateOf("") }
    var output by remember { mutableStateOf("") }
    var status by remember { mutableStateOf("Optional online AI. Bluetooth chat still works without internet.") }
    var loading by remember { mutableStateOf(false) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Assistive Message Studio") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
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
                .verticalScroll(rememberScrollState())
                .padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Text(
                text = "Use AI to write clearer messages, simplify text, or prepare useful phrases.",
                style = MaterialTheme.typography.bodyLarge,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.72f)
            )

            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Mode", style = MaterialTheme.typography.titleSmall)
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    modes.take(2).forEach { mode ->
                        AssistChip(
                            onClick = {
                                selectedMode = mode
                                output = ""
                            },
                            label = { Text(mode.label) },
                            leadingIcon = if (selectedMode.id == mode.id) {
                                { Icon(Icons.Default.Send, contentDescription = null) }
                            } else null
                        )
                    }
                }
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    modes.drop(2).forEach { mode ->
                        AssistChip(
                            onClick = {
                                selectedMode = mode
                                output = ""
                            },
                            label = { Text(mode.label) },
                            leadingIcon = if (selectedMode.id == mode.id) {
                                { Icon(Icons.Default.Send, contentDescription = null) }
                            } else null
                        )
                    }
                }
                Text(
                    text = selectedMode.hint,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.62f)
                )
            }

            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Context", style = MaterialTheme.typography.titleSmall)
                contexts.chunked(3).forEach { row ->
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        row.forEach { context ->
                            AssistChip(
                                onClick = { selectedContext = context },
                                label = { Text(context) }
                            )
                        }
                    }
                }
            }

            OutlinedTextField(
                value = input,
                onValueChange = { input = it },
                modifier = Modifier.fillMaxWidth(),
                minLines = 4,
                label = { Text("Message or situation") },
                placeholder = { Text("Example: I did not understand the doctor") }
            )

            Button(
                onClick = {
                    loading = true
                    status = "Generating..."
                    output = ""
                    scope.launch {
                        runCatching {
                            client.assist(
                                text = input,
                                mode = selectedMode.id,
                                context = selectedContext,
                                language = "ar"
                            )
                        }.onSuccess { result ->
                            output = result.output
                            status = "Generated with ${result.model} (${result.source})"
                        }.onFailure { error ->
                            status = error.message ?: "AI assistant is unavailable"
                        }
                        loading = false
                    }
                },
                enabled = !loading,
                modifier = Modifier.fillMaxWidth()
            ) {
                Icon(Icons.Default.Send, contentDescription = null)
                Text(if (loading) "Generating..." else "Generate")
            }

            Text(
                text = status,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.65f)
            )

            if (output.isNotBlank()) {
                Spacer(modifier = Modifier.height(4.dp))
                OutlinedTextField(
                    value = output,
                    onValueChange = { output = it },
                    modifier = Modifier.fillMaxWidth(),
                    minLines = 5,
                    label = { Text("Suggested text") }
                )
                Button(
                    onClick = { clipboard.setText(AnnotatedString(output)) },
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Icon(Icons.Default.ContentCopy, contentDescription = null)
                    Text("Copy suggested text")
                }
            }
        }
    }
}
