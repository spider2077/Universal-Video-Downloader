// Location: Universal-Video-Downloader/android/app/src/main/java/pm/stech/uvd/MainViewModel.kt

package pm.stech.uvd

import android.app.Application
import android.net.Uri
import android.provider.OpenableColumns
import android.util.Log
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File

data class UiState(
    val url: String = "",
    val status: String = "Starting...",
    val isError: Boolean = false,
    val progress: Float = 0f,          // 0..100, or -1 for "busy, amount unknown"
    val busy: Boolean = true,          // true while initializing or downloading
    val downloading: Boolean = false,
    val ytDlpVersion: String = "",
    val cookiePlatforms: List<String> = emptyList(),
)

class MainViewModel(application: Application) : AndroidViewModel(application) {

    private val engine = DownloadEngine(application)
    private val _state = MutableStateFlow(UiState())
    val state: StateFlow<UiState> = _state.asStateFlow()
    private var job: Job? = null

    init {
        viewModelScope.launch {
            try {
                withContext(Dispatchers.IO) { engine.init() }
                refreshInfo()
                val prefs = application.getSharedPreferences("uvd", 0)
                val lastUpdate = prefs.getLong(KEY_LAST_UPDATE, 0)
                // The yt-dlp bundled in the library is years old: update on first run, then weekly
                if (System.currentTimeMillis() - lastUpdate > UPDATE_INTERVAL_MS) {
                    setStatus("Updating yt-dlp...", progress = -1f)
                    try {
                        val message = withContext(Dispatchers.IO) { engine.updateYtDlp() }
                        prefs.edit().putLong(KEY_LAST_UPDATE, System.currentTimeMillis()).apply()
                        refreshInfo()
                        setStatus(message)
                    } catch (e: Exception) {
                        Log.w(TAG, "yt-dlp update failed", e)
                        setStatus("Could not update yt-dlp (offline?) — using ${engine.ytDlpVersion()}", isError = true)
                    }
                } else {
                    setStatus("Ready to download")
                }
            } catch (e: Exception) {
                Log.e(TAG, "init failed", e)
                setStatus("Failed to start the download engine: ${e.message}", isError = true)
            } finally {
                _state.update { it.copy(busy = false) }
            }
        }
    }

    fun setUrl(url: String) = _state.update { it.copy(url = url) }

    /** Text arriving from the share sheet or the clipboard; may contain words around the link. */
    fun offerText(text: String?) {
        Platforms.extractUrl(text)?.let { setUrl(it) }
    }

    fun start(isAudio: Boolean) {
        val url = Platforms.extractUrl(_state.value.url) ?: _state.value.url.trim()
        if (url.isEmpty()) {
            setStatus("Please enter a URL", isError = true)
            return
        }
        if (_state.value.busy) return
        val platform = Platforms.detectPlatform(url)
        _state.update { it.copy(busy = true, downloading = true, progress = -1f, isError = false, status = "Starting...") }

        job = viewModelScope.launch {
            try {
                val result = if (platform == "threads") {
                    if (isAudio) throw IllegalStateException("Threads: audio extraction is not supported — use Download Video")
                    setStatus("Opening Threads post...", progress = -1f)
                    val post = ThreadsExtractor.extract(getApplication(), url)
                    withContext(Dispatchers.IO) { engine.downloadDirect(post.videoUrl, url, post.title, ::onProgress) }
                } else {
                    if (platform == "facebook" && engine.cookieFileFor(platform) == null) {
                        setStatus("Facebook usually needs cookies — trying without...", progress = -1f)
                    }
                    withContext(Dispatchers.IO) { engine.download(url, isAudio, ::onProgress) }
                }
                _state.update {
                    val label = if (isAudio) "Audio saved" else if (result.converted) "Saved (converted for WhatsApp)" else "Saved"
                    it.copy(progress = 100f, isError = false, status = "$label: ${result.folder}/${result.savedAs}")
                }
            } catch (e: CancellationException) {
                setStatus("Cancelled")
                throw e
            } catch (e: com.yausername.youtubedl_android.YoutubeDL.CanceledException) {
                setStatus("Cancelled")
            } catch (e: Exception) {
                Log.e(TAG, "download failed", e)
                _state.update { it.copy(progress = 0f, isError = true, status = "Error: ${DownloadEngine.friendlyError(e, platform)}") }
            } finally {
                _state.update { it.copy(busy = false, downloading = false) }
            }
        }
    }

    fun cancel() {
        engine.cancel()
        job?.cancel()
    }

    fun updateYtDlp() {
        if (_state.value.busy) return
        _state.update { it.copy(busy = true, progress = -1f, isError = false, status = "Updating yt-dlp...") }
        viewModelScope.launch {
            try {
                val message = withContext(Dispatchers.IO) { engine.updateYtDlp() }
                getApplication<Application>().getSharedPreferences("uvd", 0).edit()
                    .putLong(KEY_LAST_UPDATE, System.currentTimeMillis()).apply()
                refreshInfo()
                setStatus(message)
            } catch (e: Exception) {
                setStatus("yt-dlp update failed: ${e.message}", isError = true)
            } finally {
                _state.update { it.copy(busy = false) }
            }
        }
    }

    /** Copies picked Netscape cookie files into app-private storage under their canonical names. */
    fun importCookies(uris: List<Uri>) {
        if (uris.isEmpty()) return
        viewModelScope.launch {
            val report = withContext(Dispatchers.IO) {
                val resolver = getApplication<Application>().contentResolver
                val imported = ArrayList<String>()
                val skipped = ArrayList<String>()
                for (uri in uris) {
                    val displayName = resolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use {
                        if (it.moveToFirst()) it.getString(0) else null
                    } ?: "cookies.txt"
                    val content = try {
                        resolver.openInputStream(uri)?.use { stream ->
                            val bytes = stream.readBytes()
                            (if (bytes.size > MAX_COOKIE_BYTES) bytes.copyOf(MAX_COOKIE_BYTES) else bytes).decodeToString()
                        }
                    } catch (e: Exception) {
                        null
                    }
                    val targetName = when {
                        content == null -> null
                        Platforms.platformForCookieFile(displayName) != null -> displayName.lowercase()
                        else -> Platforms.cookieFileNameForContent(content)
                    }
                    if (content == null || targetName == null) {
                        skipped += displayName
                    } else {
                        File(engine.cookiesDir, targetName).writeText(content)
                        imported += Platforms.platformForCookieFile(targetName) ?: targetName
                    }
                }
                buildString {
                    if (imported.isNotEmpty()) append("Cookies imported: ${imported.joinToString()}")
                    if (skipped.isNotEmpty()) {
                        if (isNotEmpty()) append(" — ")
                        append("not recognised: ${skipped.joinToString()}")
                    }
                }
            }
            refreshInfo()
            setStatus(report, isError = report.startsWith("not recognised"))
        }
    }

    fun clearCookies() {
        engine.cookiesDir.listFiles()?.forEach { it.delete() }
        refreshInfo()
        setStatus("All cookies removed from this app")
    }

    private fun onProgress(percent: Float, line: String) {
        _state.update { it.copy(progress = percent, status = line, isError = false) }
    }

    private fun refreshInfo() {
        _state.update { it.copy(ytDlpVersion = engine.ytDlpVersion().orEmpty(), cookiePlatforms = engine.platformsWithCookies()) }
    }

    private fun setStatus(text: String, isError: Boolean = false, progress: Float = 0f) {
        _state.update { it.copy(status = text, isError = isError, progress = progress) }
    }

    private companion object {
        const val TAG = "UVD"
        const val KEY_LAST_UPDATE = "last_ytdlp_update"
        const val UPDATE_INTERVAL_MS = 7L * 24 * 60 * 60 * 1000
        const val MAX_COOKIE_BYTES = 1024 * 1024
    }
}
