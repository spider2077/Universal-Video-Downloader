// Location: Universal-Video-Downloader/android/app/src/test/java/pm/stech/uvd/PlatformsTest.kt

package pm.stech.uvd

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class PlatformsTest {

    @Test
    fun detectsSupportedPlatforms() {
        val cases = mapOf(
            "https://www.youtube.com/watch?v=abc" to "youtube",
            "https://youtu.be/abc" to "youtube",
            "https://m.youtube.com/watch?v=a" to "youtube",
            "https://music.youtube.com/watch?v=a" to "youtube",
            "https://www.facebook.com/reel/123" to "facebook",
            "https://fb.watch/abc/" to "facebook",
            "https://www.instagram.com/natgeo/reel/abc/" to "instagram",
            "https://x.com/user/status/1" to "twitter",
            "https://twitter.com/user/status/1" to "twitter",
            "https://www.tiktok.com/@u/video/1" to "tiktok",
            "https://vm.tiktok.com/ZMabc/" to "tiktok",
            "https://www.reddit.com/r/x/comments/1/" to "reddit",
            "https://v.redd.it/abc" to "reddit",
            "https://soundcloud.com/a/b" to "soundcloud",
            "https://bsky.app/profile/a/post/b" to "bluesky",
            "https://www.threads.net/@u/post/abc" to "threads",
            "https://www.threads.com/@u/post/abc" to "threads",
            "HTTPS://WWW.TIKTOK.COM/@u/video/1" to "tiktok",
            "x.com/user/status/1" to "twitter",
        )
        for ((url, want) in cases) assertEquals(url, want, Platforms.detectPlatform(url))
    }

    @Test
    fun rejectsLookalikeHosts() {
        for (url in listOf(
            "https://www.netflix.com/title/1",
            "https://www.dropbox.com/s/abc/v.mp4",
            "https://example.com/?ref=youtube.com",
            "https://notfacebook.com/video",
            "https://vimeo.com/123",
            "https://[bad",
            "",
        )) assertNull(url, Platforms.detectPlatform(url))
        assertNull(Platforms.detectPlatform(null))
    }

    @Test
    fun extractsUrlFromSharedText() {
        assertEquals("https://vm.tiktok.com/ZMabc/", Platforms.extractUrl("Check this out! https://vm.tiktok.com/ZMabc/"))
        assertEquals("https://youtu.be/abc", Platforms.extractUrl("Watch (https://youtu.be/abc)."))
        assertEquals("https://x.com/a/status/1", Platforms.extractUrl("https://x.com/a/status/1"))
        assertNull(Platforms.extractUrl("no link here"))
        assertNull(Platforms.extractUrl(null))
    }

    @Test
    fun validatesUrls() {
        assertTrue(Platforms.isValidUrl("https://youtu.be/abc"))
        assertFalse(Platforms.isValidUrl("youtu.be/abc"))
        assertFalse(Platforms.isValidUrl("https://www.netflix.com/title/1"))
        assertFalse(Platforms.isValidUrl(null))
    }

    @Test
    fun normalizesFacebookShareLinks() {
        assertEquals(
            "https://www.facebook.com/share/v/abc/",
            Platforms.normalizeUrl("https://www.facebook.com/share/v/abc/?rdid=xyz&share_url=foo", "facebook"),
        )
        assertEquals(
            "https://www.facebook.com/watch/?v=123",
            Platforms.normalizeUrl("https://www.facebook.com/watch/?v=123&rdid=xyz", "facebook"),
        )
        assertEquals("https://youtu.be/a?t=1", Platforms.normalizeUrl(" https://youtu.be/a?t=1 ", "youtube"))
    }

    @Test
    fun picksFormats() {
        assertEquals(Platforms.TIKTOK_VIDEO_FORMAT, Platforms.formatFor("tiktok", false))
        assertEquals(Platforms.TIKTOK_AUDIO_FORMAT, Platforms.formatFor("tiktok", true))
        assertEquals(Platforms.DEFAULT_VIDEO_FORMAT, Platforms.formatFor("youtube", false))
        assertEquals(Platforms.DEFAULT_AUDIO_FORMAT, Platforms.formatFor(null, true))
        // Must stay identical to COMPAT_VIDEO_FORMAT in Downloader.py
        assertEquals(
            "bestvideo[ext=mp4][vcodec~='^(avc1|h264)']+bestaudio[ext=m4a][acodec~='^(mp4a|aac)']" +
                "/best[ext=mp4][vcodec~='^(avc1|h264)'][acodec~='^(mp4a|aac)']" +
                "/bestvideo[vcodec~='^(avc1|h264)']+bestaudio[acodec~='^(mp4a|aac)']" +
                "/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            Platforms.DEFAULT_VIDEO_FORMAT,
        )
        // Must stay identical to TIKTOK_VIDEO_FORMAT in Downloader.py
        assertEquals(
            "best[ext=mp4][vcodec=h264]/best[ext=mp4][vcodec!=h265]/best[ext=mp4]/best",
            Platforms.TIKTOK_VIDEO_FORMAT,
        )
    }

    @Test
    fun mapsCookieFiles() {
        assertEquals("twitter", Platforms.platformForCookieFile("x.com_cookies.txt"))
        assertEquals("facebook", Platforms.platformForCookieFile("WWW.FACEBOOK.COM_cookies.txt"))
        assertNull(Platforms.platformForCookieFile("cookies.txt"))
        assertEquals(listOf("bsky.app_cookies.txt"), Platforms.cookieFileNames("bluesky"))
        assertEquals(emptyList<String>(), Platforms.cookieFileNames("generic"))
    }

    @Test
    fun namesCookieFileFromContent() {
        val tiktok = "# Netscape HTTP Cookie File\n.tiktok.com\tTRUE\t/\tTRUE\t0\tname\tvalue\n" +
            "#HttpOnly_.tiktok.com\tTRUE\t/\tTRUE\t0\tname2\tvalue\n.google.com\tTRUE\t/\tTRUE\t0\tn\tv\n"
        assertEquals("www.tiktok.com_cookies.txt", Platforms.cookieFileNameForContent(tiktok))
        assertEquals("x.com_cookies.txt", Platforms.cookieFileNameForContent(".x.com\tTRUE\t/\tTRUE\t0\tn\tv\n"))
        assertNull(Platforms.cookieFileNameForContent("# Netscape HTTP Cookie File\n.example.org\tTRUE\t/\tTRUE\t0\tn\tv\n"))
    }

    @Test
    fun decidesWhenToReencode() {
        fun probe(v: String?, a: String?, pix: String? = "yuv420p") = DownloadEngine.Probe(v, a, pix, 1080, 1920, 10.0)
        assertFalse(DownloadEngine.needsReencode(probe("h264", "aac")))
        assertFalse(DownloadEngine.needsReencode(probe("h264", null)))        // silent video is fine
        assertFalse(DownloadEngine.needsReencode(probe(null, "mp3", null)))   // audio file
        assertTrue(DownloadEngine.needsReencode(probe("vp9", "aac")))
        assertTrue(DownloadEngine.needsReencode(probe("av1", "aac")))
        assertTrue(DownloadEngine.needsReencode(probe("hevc", "aac")))
        assertTrue(DownloadEngine.needsReencode(probe("h264", "opus")))
        assertTrue(DownloadEngine.needsReencode(probe("h264", "aac", "yuv420p10le")))
    }
}
