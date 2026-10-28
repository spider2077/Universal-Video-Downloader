// Location: Universal-Video-Downloader/android/app/src/main/java/pm/stech/uvd/MainActivity.kt

package pm.stech.uvd

import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.ExperimentalComposeUiApi
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.testTagsAsResourceId
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle

class MainActivity : ComponentActivity() {

    private val viewModel: MainViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        if (savedInstanceState == null) handleShare(intent)
        setContent {
            MaterialTheme(colorScheme = if (isSystemInDarkTheme()) darkColorScheme() else lightColorScheme()) {
                Surface(Modifier.fillMaxSize()) { Screen() }
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handleShare(intent)
    }

    /** "Share" from TikTok, YouTube, a browser... lands here with the link inside EXTRA_TEXT. */
    private fun handleShare(intent: Intent?) {
        when (intent?.action) {
            Intent.ACTION_SEND -> viewModel.offerText(intent.getStringExtra(Intent.EXTRA_TEXT))
            Intent.ACTION_VIEW -> viewModel.offerText(intent.dataString)
        }
    }

    private fun pasteFromClipboard() {
        val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
        val text = clipboard.primaryClip?.takeIf { it.itemCount > 0 }?.getItemAt(0)?.coerceToText(this)?.toString()
        viewModel.offerText(text)
    }

    @OptIn(ExperimentalComposeUiApi::class)
    @Composable
    private fun Screen() {
        val state by viewModel.state.collectAsStateWithLifecycle()
        var showAbout by remember { mutableStateOf(false) }
        var showCookieHelp by remember { mutableStateOf(false) }
        val cookiePicker = rememberLauncherForActivityResult(ActivityResultContracts.OpenMultipleDocuments()) { uris: List<Uri> ->
            viewModel.importCookies(uris)
        }

        // Downloads run inside the app process: keep the screen on so the phone doesn't doze mid-download
        if (state.downloading) window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        else window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)

        Column(
            modifier = Modifier
                .fillMaxSize()
                .safeDrawingPadding()
                .semantics { testTagsAsResourceId = true }
                .verticalScroll(rememberScrollState())
                .padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Text("Universal Video Downloader", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
            Text(
                "v${BuildInfo.VERSION}  ·  yt-dlp ${state.ytDlpVersion.ifEmpty { "…" }}",
                style = MaterialTheme.typography.bodySmall,
            )

            OutlinedTextField(
                value = state.url,
                onValueChange = viewModel::setUrl,
                label = { Text("Video URL") },
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri),
                modifier = Modifier.fillMaxWidth().testTag("url"),
            )
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = ::pasteFromClipboard, modifier = Modifier.testTag("paste")) { Text("Paste") }
                OutlinedButton(onClick = { viewModel.setUrl("") }) { Text("Clear") }
            }

            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                Button(
                    onClick = { viewModel.start(isAudio = false) },
                    enabled = !state.busy,
                    modifier = Modifier.weight(1f).testTag("download_video"),
                ) { Text("Download Video") }
                Button(
                    onClick = { viewModel.start(isAudio = true) },
                    enabled = !state.busy,
                    modifier = Modifier.weight(1f).testTag("download_audio"),
                ) { Text("Download Audio") }
            }

            if (state.progress < 0f) {
                LinearProgressIndicator(Modifier.fillMaxWidth())
            } else {
                LinearProgressIndicator(progress = { state.progress / 100f }, modifier = Modifier.fillMaxWidth())
            }
            Text(
                state.status,
                color = if (state.isError) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onSurface,
                modifier = Modifier.testTag("status"),
            )
            if (state.downloading) {
                OutlinedButton(onClick = viewModel::cancel) { Text("Cancel") }
            }

            Spacer(Modifier.height(8.dp))
            Text(
                if (state.cookiePlatforms.isEmpty()) "No cookies imported"
                else "Cookies: " + state.cookiePlatforms.joinToString { it.replaceFirstChar(Char::uppercase) },
                style = MaterialTheme.typography.bodySmall,
                modifier = Modifier.testTag("cookies"),
            )
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = { cookiePicker.launch(arrayOf("text/plain", "application/octet-stream", "*/*")) }, enabled = !state.busy) {
                    Text("Import cookies")
                }
                TextButton(onClick = { showCookieHelp = true }) { Text("How?") }
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = viewModel::updateYtDlp, enabled = !state.busy) { Text("Update yt-dlp") }
                TextButton(onClick = { showAbout = true }) { Text("About") }
            }
            Text(
                "Videos are saved to Movies/${DownloadEngine.OUTPUT_FOLDER}, audio to Music/${DownloadEngine.OUTPUT_FOLDER}.",
                style = MaterialTheme.typography.bodySmall,
            )
        }

        if (showCookieHelp) {
            AlertDialog(
                onDismissRequest = { showCookieHelp = false },
                confirmButton = { TextButton(onClick = { showCookieHelp = false }) { Text("Close") } },
                dismissButton = { TextButton(onClick = { showCookieHelp = false; viewModel.clearCookies() }) { Text("Remove all cookies") } },
                title = { Text("Cookies") },
                text = {
                    Text(
                        "Some sites (Facebook almost always) only serve videos to a logged-in session.\n\n" +
                            "1. On a PC, log in to the site in Chrome and export cookies with the \"Get cookies.txt\" extension.\n" +
                            "2. Copy the .txt files to this phone.\n" +
                            "3. Tap \"Import cookies\" and select them — several at once is fine. The app works out which site each file is for.\n\n" +
                            "Cookie files are your login session. They are kept in this app's private storage and never leave the phone. Never share them."
                    )
                },
            )
        }
        if (showAbout) {
            AlertDialog(
                onDismissRequest = { showAbout = false },
                confirmButton = { TextButton(onClick = { showAbout = false }) { Text("Close") } },
                dismissButton = {
                    TextButton(onClick = { startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(BuildInfo.WEBSITE))) }) { Text("Visit website") }
                },
                title = { Text("Universal Video Downloader") },
                text = {
                    Text(
                        "Version ${BuildInfo.VERSION}\n\n" +
                            "A lightweight tool for downloading videos and audio from popular social platforms using yt-dlp.\n\n" +
                            "For personal, quick downloads. Respect copyright and platform terms of service.\n\n" +
                            "Copyright (c) 2026 ${BuildInfo.COMPANY}\n${BuildInfo.LOCATION}\n${BuildInfo.WEBSITE}\n\n" +
                            "Licensed under the MIT License."
                    )
                },
            )
        }
    }
}

object BuildInfo {
    const val VERSION = BuildConfig.VERSION_NAME
    const val COMPANY = "Spiders Tech SRL"
    const val LOCATION = "Dolj, Romania"
    const val WEBSITE = "https://www.s-tech.pm"
}
