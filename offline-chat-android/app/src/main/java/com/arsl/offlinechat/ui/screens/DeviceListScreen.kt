package com.arsl.offlinechat.ui.screens

import android.bluetooth.BluetoothDevice
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.arsl.offlinechat.R
import com.arsl.offlinechat.ui.components.DeviceItem

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DeviceListScreen(
    pairedDevices: List<BluetoothDevice>,
    scannedDevices: List<BluetoothDevice>,
    onDeviceClick: (BluetoothDevice) -> Unit,
    onStartScan: () -> Unit,
    onStopScan: () -> Unit,
    onBack: () -> Unit
) {
    var scanning by remember { mutableStateOf(false) }
    DisposableEffect(Unit) { onDispose(onStopScan) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(stringResource(R.string.find_device)) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = null)
                    }
                }
            )
        }
    ) { padding ->
        Column(Modifier.fillMaxSize().padding(padding)) {
            Button(
                modifier = Modifier.fillMaxWidth().padding(16.dp),
                onClick = {
                    if (scanning) {
                        onStopScan()
                    } else {
                        onStartScan()
                    }
                    scanning = !scanning
                }
            ) {
                Text(if (scanning) stringResource(R.string.stop_scan) else stringResource(R.string.scan))
            }
            LazyColumn(Modifier.fillMaxSize()) {
                if (pairedDevices.isNotEmpty()) {
                    item { Text(stringResource(R.string.paired_devices), style = MaterialTheme.typography.titleMedium, modifier = Modifier.padding(16.dp)) }
                    items(pairedDevices, key = { it.address }) { DeviceItem(it) { onDeviceClick(it) } }
                }
                if (scannedDevices.isNotEmpty()) {
                    item { Text(stringResource(R.string.available_devices), style = MaterialTheme.typography.titleMedium, modifier = Modifier.padding(16.dp)) }
                    items(scannedDevices, key = { it.address }) { DeviceItem(it) { onDeviceClick(it) } }
                }
                if (pairedDevices.isEmpty() && scannedDevices.isEmpty()) {
                    item {
                        Box(Modifier.fillMaxWidth().padding(32.dp), contentAlignment = Alignment.Center) {
                            Text(stringResource(R.string.no_devices), textAlign = TextAlign.Center)
                        }
                    }
                }
            }
        }
    }
}
