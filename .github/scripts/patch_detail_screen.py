import os

path = "app/src/main/java/com/music/bitchord/ui/screens/DetailScreen.kt"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Add import if missing
if "import com.music.bitchord.data.YtMusicRepository" not in content:
    content = content.replace(
        "import com.music.bitchord.data.LocalMediaRepository",
        "import com.music.bitchord.data.LocalMediaRepository\nimport com.music.bitchord.data.YtMusicRepository"
    )

target = """    LaunchedEffect(page.browseId, page.title, isArtist) {
        if (!isArtist) return@LaunchedEffect
        withContext(Dispatchers.IO) {
            val downloaded = runCatching { LocalMediaRepository.getDownloadedSongs(context) }.getOrDefault(emptyList())
            val local = if (LocalMediaRepository.hasStoragePermission(context)) {
                runCatching { LocalMediaRepository.getLocalMusic(context) }.getOrDefault(emptyList())
            } else {
                emptyList()
            }
            val likedIds = LikeState.overrides.value.filterValues { it == LikeStatus.LIKE }.keys
            val downloadedIds = Downloads.saved.value.keys
            val likedOrDownloadedFromRaw = rawSongs.filter { it.videoId in likedIds || it.videoId in downloadedIds }

            val allLibrary = (downloaded + local + likedOrDownloadedFromRaw)
                .distinctBy { it.videoId.ifBlank { it.localUri ?: it.title } }

            val matching = allLibrary.filter { song ->
                isSongByArtist(song, page.browseId, page.title)
            }
            withContext(Dispatchers.Main) {
                libraryArtistSongs = matching
            }
        }
    }"""

replacement = """    LaunchedEffect(page.browseId, page.title, isArtist, rawSongs) {
        if (!isArtist) return@LaunchedEffect
        val matching: List<Song> = withContext(Dispatchers.IO) {
            val liked: List<Song> = com.music.bitchord.data.YtMusicRepository.likedSongsList()
            val downloaded: List<Song> = runCatching { LocalMediaRepository.getDownloadedSongs(context) }.getOrDefault(emptyList())
            val local: List<Song> = if (LocalMediaRepository.hasStoragePermission(context)) {
                runCatching { LocalMediaRepository.getLocalMusic(context) }.getOrDefault(emptyList())
            } else {
                emptyList()
            }
            val likedIds = LikeState.overrides.value.filterValues { it == LikeStatus.LIKE }.keys
            val downloadedIds = Downloads.saved.value.keys
            val savedFromPage: List<Song> = rawSongs.filter { it.videoId in likedIds || it.videoId in downloadedIds }
            val allLibrary: List<Song> = (liked + downloaded + local + savedFromPage)
            allLibrary
                .distinctBy { it.videoId.ifBlank { it.localUri ?: it.title } }
                .filter { isSongByArtist(it, page.browseId, page.title) }
        }
        libraryArtistSongs = matching
    }"""

if target in content:
    content = content.replace(target, replacement, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("DetailScreen.kt patched successfully")
else:
    print("Target block not found, checking if already patched...")
    if "com.music.bitchord.data.YtMusicRepository.likedSongsList()" in content:
        print("Already patched")
    else:
        raise Exception("Could not find target code block to patch")
