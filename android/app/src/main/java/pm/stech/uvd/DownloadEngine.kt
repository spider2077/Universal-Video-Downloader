// Location: Universal-Video-Downloader/android/app/src/main/java/pm/stech/uvd/DownloadEngine.kt
// Android counterpart of download_media() in Downloader.py, built on youtubedl-android
// (bundled Python + yt-dlp + ffmpeg + QuickJS).

package pm.stech.uvd

import android.content.ContentValues
import android.content.Context
import android.net.Uri
import android.os.Environment
import android.provider.MediaStore
import android.util.Log
import org.json.JSONArray
import org.json.JSONObject
import com.yausername.ffmpeg.FFmpeg
import com.yausername.youtubedl_android.YoutubeDL
import com.yausername.youtubedl_android.YoutubeDLRequest
import java.io.File
import java.net.HttpURLConnection
import java.net.URL

class DownloadEngine(private val app: Context) {

    data class Result(val savedAs: String, val folder: String, val converted: Boolean = false)

    /** Cookie files live in app-private storage; they are login sessions and must never be shared. */
    val cookiesDir: File get() = File(app.filesDir, "cookies").apply { mkdirs() }
    private val workRoot: File get() = File(app.cacheDir, "downloads")

    @Volatile private var initialized = false

    @Synchronized
    fun init() {
        if (initialized) return
        YoutubeDL.getInstance().init(app)
        FFmpeg.getInstance().init(app)
        initialized = true
    }

    /** The library reports e.g. "yt-dlp 2026.08.19"; keep just the number. */
    fun ytDlpVersion(): String? = YoutubeDL.getInstance().versionName(app)?.removePrefix("yt-dlp")?.trim()

    /** The yt-dlp shipped inside the library is old; site fixes (e.g. TikTok audio) need a current one. */
    fun updateYtDlp(): String {
        init()
        val status = YoutubeDL.getInstance().updateYoutubeDL(app, YoutubeDL.UpdateChannel.STABLE)
        return when (status) {
            YoutubeDL.UpdateStatus.DONE -> "yt-dlp updated to ${ytDlpVersion()}"
            else -> "yt-dlp is up to date (${ytDlpVersion()})"
        }
    }

    fun cookieFileFor(platform: String?): File? =
        Platforms.cookieFileNames(platform).map { File(cookiesDir, it) }.firstOrNull { it.length() > 0 }

    fun platformsWithCookies(): List<String> =
        Platforms.COOKIE_FILES.keys.filter { cookieFileFor(it) != null }

    fun cancel() {
        YoutubeDL.getInstance().destroyProcessById(PROCESS_ID)
    }

    /** Blocking; call from a background thread. [onProgress] gets 0..100 (or -1 = unknown) and a status line. */
    fun download(rawUrl: String, isAudio: Boolean, onProgress: (Float, String) -> Unit): Result {
        init()
        val platform = Platforms.detectPlatform(rawUrl)
        val url = Platforms.normalizeUrl(rawUrl, platform)

        workRoot.deleteRecursively()
        val workDir = File(workRoot, System.currentTimeMillis().toString()).apply { mkdirs() }
        try {
            val request = YoutubeDLRequest(url).apply {
                addOption("-f", Platforms.formatFor(platform, isAudio))
                // The id keeps names unique: every Instagram reel of an account is titled "Video by <account>"
                addOption("-o", File(workDir, "%(title).80B [%(id)s].%(ext)s").absolutePath)
                addOption("--no-playlist")
                addOption("--no-mtime")
                addOption("--merge-output-format", "mp4")
                addOption("--embed-metadata")
                // Same tags as add_metadata_to_file() on desktop: video title (not the music track name),
                // uploader as artist, platform as album
                addOption("--parse-metadata", "%(title)s:%(meta_title)s")
                addOption("--parse-metadata", "%(uploader,channel,artist|)s:%(meta_artist)s")
                addOption("--parse-metadata", "%(extractor_key)s:%(meta_album)s")
                addOption("--retries", 10)
                addOption("--fragment-retries", 10)
                addOption("--socket-timeout", 30)
                if (isAudio) {
                    addOption("-x")
                    addOption("--audio-format", "mp3")
                    addOption("--audio-quality", "192K")
                }
                if (platform == null) addOption("--force-generic-extractor")
                cookieFileFor(platform)?.let { addOption("--cookies", it.absolutePath) }
            }

            onProgress(-1f, "Reading ${platform ?: "page"} info...")
            YoutubeDL.getInstance().execute(request, PROCESS_ID) { percent, _, line ->
                val text = line.trim()
                when {
                    text.startsWith("[download]") && percent > 0f -> onProgress(percent, "Downloading: ${"%.1f".format(percent)}%")
                    text.startsWith("[Merger]") -> onProgress(-1f, "Merging video and audio...")
                    text.startsWith("[ExtractAudio]") -> onProgress(-1f, "Converting to MP3...")
                    text.startsWith("[Metadata]") -> onProgress(-1f, "Adding metadata...")
                }
            }

            val wanted = if (isAudio) AUDIO_EXTENSIONS else VIDEO_EXTENSIONS
            var output = workDir.listFiles()
                ?.filter { it.isFile && it.extension.lowercase() in wanted }
                ?.maxByOrNull { it.length() }
                ?: throw IllegalStateException("Download finished but output file was not found. Check cookies and try again.")

            // WhatsApp & co only accept H.264/AAC MP4. Facebook and Instagram serve VP9 only, so
            // the format selector alone is not enough: probe the file and convert when needed.
            var converted = false
            if (!isAudio) {
                val probe = probeMedia(output)
                if (probe != null && needsReencode(probe)) {
                    Log.i(TAG, "converting ${probe.vcodec}/${probe.acodec} ${probe.width}x${probe.height} to H.264/AAC")
                    onProgress(-1f, "Converting to H.264/AAC (WhatsApp compatible)...")
                    output = reencode(output, probe, onProgress)
                    converted = true
                }
            }

            onProgress(-1f, "Saving to device...")
            return publish(output, isAudio).copy(converted = converted)
        } finally {
            workRoot.deleteRecursively()
        }
    }

    // --- Output compatibility (mirrors probe_media / needs_reencode / finalize_media in Downloader.py) ---

    data class Probe(val vcodec: String?, val acodec: String?, val pixFmt: String?, val width: Int, val height: Int, val duration: Double)

    private val nativeLibDir: File get() = File(app.applicationInfo.nativeLibraryDir)
    private val packagesDir: File get() = File(File(app.noBackupFilesDir, "youtubedl-android"), "packages")

    /** Same environment youtubedl-android sets up when it launches its own binaries. */
    private fun toolProcess(command: List<String>): ProcessBuilder =
        ProcessBuilder(command).apply {
            environment()["LD_LIBRARY_PATH"] = listOf("python", "ffmpeg").joinToString(":") { File(packagesDir, "$it/usr/lib").absolutePath }
            environment()["PATH"] = System.getenv("PATH") + ":" + nativeLibDir.absolutePath
            environment()["TMPDIR"] = app.cacheDir.absolutePath
        }

    fun probeMedia(file: File): Probe? {
        val ffprobe = File(nativeLibDir, "libffprobe.so")
        if (!ffprobe.exists()) return null
        return try {
            val process = toolProcess(listOf(ffprobe.absolutePath, "-v", "error", "-show_entries",
                "stream=codec_type,codec_name,pix_fmt,width,height:format=duration", "-of", "json", file.absolutePath)).start()
            val text = process.inputStream.bufferedReader().readText()
            process.waitFor()
            val json = JSONObject(text)
            var vcodec: String? = null
            var acodec: String? = null
            var pixFmt: String? = null
            var width = 0
            var height = 0
            val streams = json.optJSONArray("streams") ?: JSONArray()
            for (i in 0 until streams.length()) {
                val stream = streams.getJSONObject(i)
                when (stream.optString("codec_type")) {
                    "video" -> if (vcodec == null && stream.optString("codec_name") !in setOf("mjpeg", "png")) {
                        vcodec = stream.optString("codec_name")
                        pixFmt = stream.optString("pix_fmt").ifEmpty { null }
                        width = stream.optInt("width")
                        height = stream.optInt("height")
                    }
                    "audio" -> if (acodec == null) acodec = stream.optString("codec_name")
                }
            }
            Probe(vcodec, acodec, pixFmt, width, height, json.optJSONObject("format")?.optString("duration")?.toDoubleOrNull() ?: 0.0)
        } catch (e: Exception) {
            Log.w(TAG, "ffprobe failed", e)
            null
        }
    }

    /** Re-encode to H.264 (libx264) + AAC. Returns the new file. */
    private fun reencode(input: File, probe: Probe, onProgress: (Float, String) -> Unit): File {
        val ffmpeg = File(nativeLibDir, "libffmpeg.so")
        val target = File(input.parentFile, input.nameWithoutExtension + ".compat.mp4")
        val videoOk = probe.vcodec == "h264" && (probe.pixFmt ?: "yuv420p") == "yuv420p"
        val audioArgs = if (probe.acodec == null || probe.acodec == "aac") listOf("-c:a", "copy") else listOf("-c:a", "aac", "-b:a", "160k")
        val evenSize = listOf("-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2")
        // h264_mediacodec cannot be used from a child process (it needs the app's JVM), so libx264 it is:
        // about 1.5x real time on a 2020 mid-range phone at 1080p.
        val videoCandidates = if (videoOk) listOf(listOf("-c:v", "copy")) else listOf(
            listOf("-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-profile:v", "high", "-pix_fmt", "yuv420p") + evenSize,
        )
        var lastError = ""
        for (video in videoCandidates) {
            target.delete()
            val command = listOf(ffmpeg.absolutePath, "-y", "-hide_banner", "-loglevel", "error", "-i", input.absolutePath) +
                video + audioArgs + listOf("-map_metadata", "0", "-movflags", "+faststart", "-progress", "pipe:1", "-nostats", target.absolutePath)
            val process = toolProcess(command).start()
            val errReader = Thread { lastError = process.errorStream.bufferedReader().readText() }.apply { start() }
            process.inputStream.bufferedReader().forEachLine { line ->
                if (line.startsWith("out_time_us=") && probe.duration > 0) {
                    val micros = line.substringAfter('=').toLongOrNull() ?: return@forEachLine
                    val percent = (micros / 1_000_000.0 / probe.duration * 100).toFloat().coerceIn(0f, 99f)
                    onProgress(percent, "Converting to H.264/AAC: ${"%.0f".format(percent)}%")
                }
            }
            val code = process.waitFor()
            errReader.join()
            if (code == 0 && target.length() > 0) {
                Log.i(TAG, "converted with ${video[1]}")
                input.delete()
                val finalFile = File(input.parentFile, input.nameWithoutExtension + ".mp4")
                return if (target.renameTo(finalFile)) finalFile else target
            }
            Log.w(TAG, "encoder ${video[1]} failed ($code): ${lastError.take(400)}")
        }
        throw IllegalStateException("Conversion to H.264 failed: ${lastError.trim().lines().lastOrNull() ?: "unknown error"}")
    }

    /** Plain HTTP download for direct media links (used by the Threads path). Blocking. */
    fun downloadDirect(
        mediaUrl: String,
        referer: String,
        title: String,
        onProgress: (Float, String) -> Unit,
    ): Result {
        workRoot.deleteRecursively()
        val workDir = File(workRoot, System.currentTimeMillis().toString()).apply { mkdirs() }
        try {
            val target = File(workDir, sanitizeFileName(title) + ".mp4")
            val connection = (URL(mediaUrl).openConnection() as HttpURLConnection).apply {
                connectTimeout = 30_000
                readTimeout = 30_000
                setRequestProperty("User-Agent", DESKTOP_USER_AGENT)
                setRequestProperty("Referer", referer)
                setRequestProperty("Accept", "*/*")
            }
            try {
                if (connection.responseCode !in 200..299) {
                    throw IllegalStateException("Video server answered HTTP ${connection.responseCode}")
                }
                val total = connection.contentLengthLong
                var done = 0L
                connection.inputStream.use { input ->
                    target.outputStream().use { out ->
                        val buffer = ByteArray(64 * 1024)
                        while (true) {
                            val read = input.read(buffer)
                            if (read < 0) break
                            out.write(buffer, 0, read)
                            done += read
                            if (total > 0) {
                                val percent = done * 100f / total
                                onProgress(percent, "Downloading: ${"%.1f".format(percent)}%")
                            }
                        }
                    }
                }
            } finally {
                connection.disconnect()
            }
            onProgress(-1f, "Saving to device...")
            return publish(target, isAudio = false)
        } finally {
            workRoot.deleteRecursively()
        }
    }

    /** Copy into the shared Movies/ or Music/ collection so the Gallery and players see it. */
    private fun publish(file: File, isAudio: Boolean): Result {
        val resolver = app.contentResolver
        val folder = (if (isAudio) Environment.DIRECTORY_MUSIC else Environment.DIRECTORY_MOVIES) + "/" + OUTPUT_FOLDER
        val collection: Uri =
            if (isAudio) MediaStore.Audio.Media.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY)
            else MediaStore.Video.Media.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY)

        val values = ContentValues().apply {
            put(MediaStore.MediaColumns.DISPLAY_NAME, file.name)
            put(MediaStore.MediaColumns.MIME_TYPE, mimeTypeFor(file.extension))
            put(MediaStore.MediaColumns.RELATIVE_PATH, folder)
            put(MediaStore.MediaColumns.IS_PENDING, 1)
        }
        val uri = resolver.insert(collection, values)
            ?: throw IllegalStateException("Could not create the output file in $folder")
        try {
            resolver.openOutputStream(uri)?.use { out -> file.inputStream().use { it.copyTo(out, 256 * 1024) } }
                ?: throw IllegalStateException("Could not open the output file in $folder")
            values.clear()
            values.put(MediaStore.MediaColumns.IS_PENDING, 0)
            resolver.update(uri, values, null, null)
        } catch (e: Exception) {
            resolver.delete(uri, null, null)
            throw e
        }
        return Result(savedAs = file.name, folder = folder)
    }

    companion object {
        private const val TAG = "UVD"
        const val PROCESS_ID = "uvd-download"

        /** True when WhatsApp & co would reject the file: not H.264 yuv420p + AAC (silent files are fine). */
        fun needsReencode(probe: Probe): Boolean {
            if (probe.vcodec == null) return false
            val videoOk = probe.vcodec == "h264" && (probe.pixFmt ?: "yuv420p") == "yuv420p"
            val audioOk = probe.acodec == null || probe.acodec == "aac"
            return !(videoOk && audioOk)
        }
        const val OUTPUT_FOLDER = "UniversalVideoDownloader"
        const val DESKTOP_USER_AGENT =
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        private val VIDEO_EXTENSIONS = setOf("mp4", "webm", "mkv", "mov", "m4a")
        private val AUDIO_EXTENSIONS = setOf("mp3", "m4a", "opus", "ogg", "webm")

        fun mimeTypeFor(extension: String): String = when (extension.lowercase()) {
            "mp4", "m4v" -> "video/mp4"
            "webm" -> "video/webm"
            "mkv" -> "video/x-matroska"
            "mov" -> "video/quicktime"
            "mp3" -> "audio/mpeg"
            "m4a" -> "audio/mp4"
            "opus", "ogg" -> "audio/ogg"
            else -> "application/octet-stream"
        }

        fun sanitizeFileName(name: String): String {
            val cleaned = name.replace(Regex("""[<>:"/\\|?* -]"""), "_").replace(Regex("_+"), "_").trim(' ', '_', '.')
            return cleaned.take(100).trim().ifEmpty { "download_${System.currentTimeMillis()}" }
        }

        /** Same user-facing wording as format_error_message() in Downloader.py. */
        fun friendlyError(error: Throwable, platform: String?): String {
            val message = (error.message ?: error.javaClass.simpleName).trim()
            val lastError = message.lineSequence().lastOrNull { it.startsWith("ERROR") } ?: message
            return when {
                platform == "facebook" && "Cannot parse data" in message ->
                    "Facebook: import fresh cookies exported from facebook.com"
                "ffmpeg" in message.lowercase() && "not found" in message.lowercase() ->
                    "FFmpeg failed to start — reinstall the app"
                lastError.length > 160 -> lastError.take(157) + "..."
                else -> lastError
            }
        }
    }
}
