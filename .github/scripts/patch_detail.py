import io
import re

path = "app/src/main/java/com/music/bitchord/ui/screens/DetailScreen.kt"
with io.open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add import for YtMusicRepository if not present
import_target = "import com.music.bitchord.download.Downloads"
if import_target in content and "import com.music.bitchord.data.YtMusicRepository" not in content:
    content = content.replace(import_target, f"{import_target}\nimport com.music.bitchord.data.YtMusicRepository", 1)

# 2. Update libraryArtistSongs block
old_block = """    val context = LocalPlatformContext.current
    var libraryArtistSongs by remember(page.browseId, page.title) {
        mutableStateOf<List<Song>>(emptyList())
    }
    LaunchedEffect(page.browseId, page.title, isArtist) {
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

new_block = """    val context = LocalPlatformContext.current
    val likeOverrides by LikeState.overrides.collectAsStateWithLifecycle()
    var libraryArtistSongs by remember(page.browseId, page.title) {
        mutableStateOf<List<Song>>(emptyList())
    }
    LaunchedEffect(page.browseId, page.title, isArtist, likeOverrides) {
        if (!isArtist) return@LaunchedEffect
        withContext(Dispatchers.IO) {
            val downloaded = runCatching { LocalMediaRepository.getDownloadedSongs(context) }.getOrDefault(emptyList())
            val local = if (LocalMediaRepository.hasStoragePermission(context)) {
                runCatching { LocalMediaRepository.getLocalMusic(context) }.getOrDefault(emptyList())
            } else {
                emptyList()
            }
            val likedIds = likeOverrides.filterValues { it == LikeStatus.LIKE }.keys
            val dislikedIds = likeOverrides.filterValues { it == LikeStatus.DISLIKE }.keys
            val downloadedIds = Downloads.saved.value.keys
            val likedOrDownloadedFromRaw = rawSongs.filter {
                (it.videoId in likedIds || it.videoId in downloadedIds) && it.videoId !in dislikedIds
            }

            fun computeMatching(accountLiked: List<Song>): List<Song> {
                val validAccountLiked = accountLiked.filterNot { it.videoId in dislikedIds }
                val allLibrary = (validAccountLiked + likedOrDownloadedFromRaw + downloaded + local)
                    .distinctBy { it.videoId.ifBlank { it.localUri ?: it.title } }
                return allLibrary.filter { song ->
                    isSongByArtist(song, page.browseId, page.title)
                }
            }

            val initialCached = YtMusicRepository.cachedLikedMusic().orEmpty()
            val initialMatching = computeMatching(initialCached)
            if (initialMatching.isNotEmpty()) {
                withContext(Dispatchers.Main) {
                    libraryArtistSongs = initialMatching
                }
            }

            val fetchedLiked = runCatching { YtMusicRepository.likedSongsList() }.getOrDefault(initialCached)
            val fullMatching = computeMatching(fetchedLiked)
            withContext(Dispatchers.Main) {
                libraryArtistSongs = fullMatching
            }
        }
    }"""

if old_block in content:
    content = content.replace(old_block, new_block, 1)
    with io.open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("SUCCESS: DetailScreen.kt updated with liked songs")
elif new_block in content:
    print("ALREADY_PATCHED: DetailScreen.kt already contains liked songs logic")
else:
    pat = r"val\s+context\s*=\s*LocalPlatformContext\.current[\s\S]*?withContext\(Dispatchers\.Main\)\s*\{\s*libraryArtistSongs\s*=\s*matching\s*\}\s*\}\s*\}"
    if re.search(pat, content):
        content = re.sub(pat, new_block.strip(), content, count=1)
        with io.open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print("SUCCESS: regex replaced in DetailScreen.kt")
    else:
        raise RuntimeError("Could not find libraryArtistSongs block in DetailScreen.kt")
