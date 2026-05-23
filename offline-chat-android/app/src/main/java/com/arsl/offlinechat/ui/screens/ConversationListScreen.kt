package com.arsl.offlinechat.ui.screens

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.BluetoothSearching
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.arsl.offlinechat.R
import com.arsl.offlinechat.data.Conversation
import com.arsl.offlinechat.ui.components.ConversationItem

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ConversationListScreen(
    conversations: List<Conversation>,
    connectionStatus: String,
    onConversationClick: (Conversation) -> Unit,
    onBack: () -> Unit
) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text(stringResource(R.string.messages))
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
        ) {
            Card(Modifier.padding(16.dp)) {
                Column(Modifier.padding(16.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                    Icon(Icons.Default.BluetoothSearching, contentDescription = null)
                    Text(stringResource(R.string.your_device_ready), style = MaterialTheme.typography.titleMedium)
                    Text(stringResource(R.string.ready_desc), textAlign = TextAlign.Center)
                }
            }
            if (conversations.isEmpty()) {
                Box(Modifier.fillMaxSize().padding(32.dp), contentAlignment = Alignment.Center) {
                    Text(stringResource(R.string.no_conversations), textAlign = TextAlign.Center)
                }
            } else {
                LazyColumn {
                    items(conversations, key = { it.deviceAddress }) {
                        ConversationItem(it) { onConversationClick(it) }
                    }
                }
            }
        }
    }
}
