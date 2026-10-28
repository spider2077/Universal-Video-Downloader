// Location: Universal-Video-Downloader/android/app/src/main/java/pm/stech/uvd/ThreadsExtractor.kt
// yt-dlp has no Threads extractor. The desktop app drives headless Chrome through Selenium
// (download_threads_video); here an off-screen WebView loads the post and reads the <video> src.

package pm.stech.uvd

import android.annotation.SuppressLint
import android.content.Context
import android.webkit.WebView
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import org.json.JSONArray
import kotlin.coroutines.resume

object ThreadsExtractor {

    data class Post(val videoUrl: String, val title: String)

    // Current Threads markup is a bare <video src="https://...mp4">; the post text is the document title.
    private const val PROBE_JS = """
        (function() {
            var v = document.querySelector('video');
            var src = v ? (v.currentSrc || v.src || '') : '';
            if (!src && v) { var s = v.querySelector('source'); if (s) src = s.src || ''; }
            return JSON.stringify([src, document.title || '']);
        })()
    """

    @SuppressLint("SetJavaScriptEnabled")
    suspend fun extract(context: Context, url: String, timeoutMs: Long = 25_000): Post =
        withContext(Dispatchers.Main) {
            val webView = WebView(context.applicationContext)
            try {
                webView.settings.javaScriptEnabled = true
                webView.settings.domStorageEnabled = true
                webView.settings.mediaPlaybackRequiresUserGesture = true
                webView.settings.userAgentString = DownloadEngine.DESKTOP_USER_AGENT
                // Give the page a real viewport, otherwise lazy content never renders off-screen
                webView.layout(0, 0, 1280, 1920)
                webView.loadUrl(url)

                val deadline = System.currentTimeMillis() + timeoutMs
                while (System.currentTimeMillis() < deadline) {
                    delay(750)
                    val (src, title) = probe(webView)
                    if (src.startsWith("http")) {
                        return@withContext Post(src, title.ifBlank { "Threads_Video_${System.currentTimeMillis()}" })
                    }
                }
                throw IllegalStateException("Could not find a video in the Threads post")
            } finally {
                webView.stopLoading()
                webView.destroy()
            }
        }

    private suspend fun probe(webView: WebView): Pair<String, String> =
        suspendCancellableCoroutine { continuation ->
            webView.evaluateJavascript(PROBE_JS) { raw ->
                val parsed = try {
                    // evaluateJavascript returns a JSON-encoded string containing our JSON array
                    val inner = JSONArray("[$raw]").getString(0)
                    val array = JSONArray(inner)
                    array.getString(0) to array.getString(1)
                } catch (e: Exception) {
                    "" to ""
                }
                if (continuation.isActive) continuation.resume(parsed)
            }
        }
}
