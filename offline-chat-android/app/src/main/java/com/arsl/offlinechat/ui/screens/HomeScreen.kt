package com.arsl.offlinechat.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccessibilityNew
import androidx.compose.material.icons.filled.VolunteerActivism
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.arsl.offlinechat.R
import com.arsl.offlinechat.ui.theme.AccessibleBlue
import com.arsl.offlinechat.ui.theme.HelperGreen
import com.arsl.offlinechat.viewmodel.UserRole

@Composable
fun HomeScreen(onRoleSelected: (UserRole) -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(28.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(stringResource(R.string.home_title), style = MaterialTheme.typography.headlineLarge, color = AccessibleBlue)
        Spacer(Modifier.height(10.dp))
        Text(stringResource(R.string.home_subtitle), textAlign = TextAlign.Center, color = MaterialTheme.colorScheme.onBackground.copy(alpha = 0.72f))
        Spacer(Modifier.height(48.dp))
        Button(
            onClick = { onRoleSelected(UserRole.ASSISTED) },
            modifier = Modifier.fillMaxWidth().height(72.dp),
            colors = ButtonDefaults.buttonColors(containerColor = AccessibleBlue)
        ) {
            Icon(Icons.Default.AccessibilityNew, contentDescription = null)
            Spacer(Modifier.padding(8.dp))
            Column {
                Text(stringResource(R.string.role_assisted), style = MaterialTheme.typography.titleMedium)
                Text(stringResource(R.string.role_assisted_desc), style = MaterialTheme.typography.bodySmall)
            }
        }
        Spacer(Modifier.height(14.dp))
        Button(
            onClick = { onRoleSelected(UserRole.HELPER) },
            modifier = Modifier.fillMaxWidth().height(72.dp),
            colors = ButtonDefaults.buttonColors(containerColor = HelperGreen)
        ) {
            Icon(Icons.Default.VolunteerActivism, contentDescription = null)
            Spacer(Modifier.padding(8.dp))
            Column {
                Text(stringResource(R.string.role_helper), style = MaterialTheme.typography.titleMedium)
                Text(stringResource(R.string.role_helper_desc), style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}
