// Location: Universal-Video-Downloader/android/app/src/main/java/pm/stech/uvd/Platforms.kt
// Port of the platform / format logic in Downloader.py. Keep the two in sync.
// No Android imports here: this file is unit-tested on the JVM.

package pm.stech.uvd

import java.net.URI

object Platforms {

    /** Cookie file names per platform, same convention as the desktop app. */
    val COOKIE_FILES: Map<String, List<String>> = linkedMapOf(
        "youtube" to listOf("www.youtube.com_cookies.txt"),
        "instagram" to listOf("www.instagram.com_cookies.txt"),
        "facebook" to listOf("www.facebook.com_cookies.txt"),
        "twitter" to listOf("www.twitter.com_cookies.txt", "x.com_cookies.txt"),
        "tiktok" to listOf("www.tiktok.com_cookies.txt"),
        "reddit" to listOf("www.reddit.com_cookies.txt"),
        "soundcloud" to listOf("www.soundcloud.com_cookies.txt", "soundcloud.com_cookies.txt"),
        "threads" to listOf("www.threads.net_cookies.txt", "www.threads.com_cookies.txt"),
        "bluesky" to listOf("bsky.app_cookies.txt"),
        "pornhub" to listOf("www.pornhub.com_cookies.txt"),
    )

    // Matched against the URL's hostname (exact or subdomain), never as a substring:
    // a plain "x.com" substring test also matches netflix.com, dropbox.com, etc.
    val DOMAINS: Map<String, List<String>> = linkedMapOf(
        "youtube" to listOf("youtube.com", "youtu.be", "youtube-nocookie.com"),
        "facebook" to listOf("facebook.com", "fb.watch"),
        "instagram" to listOf("instagram.com"),
        "twitter" to listOf("twitter.com", "x.com"),
        "threads" to listOf("threads.net", "threads.com"),
        "tiktok" to listOf("tiktok.com", "tiktokv.com"),
        "reddit" to listOf("reddit.com", "redd.it"),
        "soundcloud" to listOf("soundcloud.com"),
        "bluesky" to listOf("bsky.app", "bluesky.app"),
        "pornhub" to listOf("pornhub.com"),
    )

    // TikTok's highest-bitrate files are HEVC and some carry no audio track; the only
    // separate audio format is the background music, not the video's soundtrack.
    // Prefer the H.264 muxed file. See the v2.0.4 entry in WORKLOG.md.
    const val TIKTOK_VIDEO_FORMAT =
        "best[ext=mp4][vcodec=h264]/best[ext=mp4][vcodec!=h265]/best[ext=mp4]/best"
    const val TIKTOK_AUDIO_FORMAT = "best[ext=mp4][vcodec=h264]/best[ext=mp4]/bestaudio/best"
    // WhatsApp, Telegram and stock players only accept H.264 + AAC inside MP4; "best" would
    // happily pick VP9/AV1 (YouTube, Facebook, Instagram). Ask for H.264/AAC first.
    private const val H264 = "vcodec~='^(avc1|h264)'"
    private const val AAC = "acodec~='^(mp4a|aac)'"
    const val DEFAULT_VIDEO_FORMAT =
        "bestvideo[ext=mp4][$H264]+bestaudio[ext=m4a][$AAC]" +
            "/best[ext=mp4][$H264][$AAC]" +
            "/bestvideo[$H264]+bestaudio[$AAC]" +
            "/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
    const val DEFAULT_AUDIO_FORMAT = "bestaudio/best"

    private val URL_IN_TEXT = Regex("""https?://\S+""", RegexOption.IGNORE_CASE)

    fun detectPlatform(url: String?): String? {
        if (url.isNullOrBlank()) return null
        val cleaned = url.trim().lowercase()
        val host = try {
            URI(if ("://" in cleaned) cleaned else "//$cleaned").host
        } catch (e: Exception) {
            null
        } ?: return null
        for ((platform, domains) in DOMAINS) {
            if (domains.any { host == it || host.endsWith(".$it") }) return platform
        }
        return null
    }

    /** Apps share text like "Check this out! https://vm.tiktok.com/abc/" — pull the link out. */
    fun extractUrl(text: String?): String? {
        if (text.isNullOrBlank()) return null
        return URL_IN_TEXT.find(text)?.value?.trimEnd('.', ',', ')', ']', '"', '\'')
    }

    fun isValidUrl(url: String?): Boolean =
        url != null && Regex("^https?://", RegexOption.IGNORE_CASE).containsMatchIn(url) &&
            detectPlatform(url) != null

    fun normalizeUrl(url: String, platform: String?): String {
        var result = url.trim()
        if (platform == "facebook") {
            result = result.replace(Regex("[?&]share_url=[^&]+"), "")
            result = result.replace(Regex("[?&]rdid=[^&]+"), "")
            result = result.trimEnd('?', '&')
        }
        return result
    }

    fun formatFor(platform: String?, isAudio: Boolean): String = when {
        platform == "tiktok" -> if (isAudio) TIKTOK_AUDIO_FORMAT else TIKTOK_VIDEO_FORMAT
        isAudio -> DEFAULT_AUDIO_FORMAT
        else -> DEFAULT_VIDEO_FORMAT
    }

    fun cookieFileNames(platform: String?): List<String> = COOKIE_FILES[platform] ?: emptyList()

    /** Which platform a cookie file belongs to, judged by its name (used when importing). */
    fun platformForCookieFile(fileName: String): String? =
        COOKIE_FILES.entries.firstOrNull { (_, names) -> names.any { it.equals(fileName, ignoreCase = true) } }?.key

    /**
     * Guess the canonical cookie file name from the domains inside a Netscape cookie file,
     * so an export saved under any name (e.g. "cookies.txt") can still be imported.
     */
    fun cookieFileNameForContent(content: String): String? {
        val counts = HashMap<String, Int>()
        for (line in content.lineSequence()) {
            if (line.isBlank() || (line.startsWith("#") && !line.startsWith("#HttpOnly_"))) continue
            val domain = line.removePrefix("#HttpOnly_").substringBefore('\t').trim().trimStart('.').lowercase()
            if (domain.isEmpty()) continue
            val platform = DOMAINS.entries.firstOrNull { (_, ds) -> ds.any { domain == it || domain.endsWith(".$it") } }?.key
                ?: continue
            counts[platform] = (counts[platform] ?: 0) + 1
        }
        val best = counts.maxByOrNull { it.value }?.key ?: return null
        val names = COOKIE_FILES[best] ?: return null
        // twitter exports are x.com nowadays; everything else uses its first name
        return if (best == "twitter") "x.com_cookies.txt" else names.first()
    }
}
