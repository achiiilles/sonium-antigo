import os
import re

print("Starting Sonium 0.2.0 patch application...")

# 0. Patch app/build.gradle.kts (Versionamento: Sonium 0.2.0)
gradle_path = "app/build.gradle.kts"
if os.path.exists(gradle_path):
    with open(gradle_path, "r", encoding="utf-8") as f:
        gc = f.read()
    gc = gc.replace('versionName = "1.8"', 'versionName = "0.2.0"')
    gc = gc.replace('resValue("string", "app_name", "BitChord Dev")', 'resValue("string", "app_name", "Sonium Dev")')
    with open(gradle_path, "w", encoding="utf-8") as f:
        f.write(gc)
    print("app/build.gradle.kts patched to version 0.2.0 and Sonium Dev.")

# 1. Patch PlayerConnection.kt (Artista limpo no player)
pc_path = "app/src/main/java/com/music/bitchord/playback/PlayerConnection.kt"
if os.path.exists(pc_path):
    with open(pc_path, "r", encoding="utf-8") as f:
        pc = f.read()

    if "fun cleanMediaArtist(" not in pc:
        helper = """private const val ARTISTS_NAMES = "artistNames"
private const val ARTISTS_IDS = "artistIds"

private val MEDIA_PREFIX_REGEX = Regex("^(?:(?:m[úu]sica|song|v[íi]deo|track|faixa|áudio|audio|single|ep|álbum|album)\\\\s*[•·\\\\-|:]\\\\s*)+", RegexOption.IGNORE_CASE)

fun cleanMediaArtist(raw: String): String =
    raw.replace(MEDIA_PREFIX_REGEX, "").trim()
"""
        pc = pc.replace(
            """private const val ARTISTS_NAMES = "artistNames"\nprivate const val ARTISTS_IDS = "artistIds"\n""",
            helper
        )

    pc = pc.replace(
        'artist = mediaMetadata.artist?.toString().orEmpty(),',
        'artist = cleanMediaArtist(mediaMetadata.artist?.toString().orEmpty()),'
    )

    pc = pc.replace(
        'artist = b.getString("artist").orEmpty(),',
        'artist = cleanMediaArtist(b.getString("artist").orEmpty()),'
    )

    old_to_media = """.setTitle(title)
            .setArtist(artist)"""
    new_to_media = """.setTitle(title)
            .setArtist(cleanMediaArtist(artist))"""
    pc = pc.replace(old_to_media, new_to_media)

    with open(pc_path, "w", encoding="utf-8") as f:
        f.write(pc)
    print("PlayerConnection.kt patched for clean artist.")

# 2. Patch PlaybackService.kt (Álbum no MediaSession mesmo em rádio/aleatório)
ps_path = "app/src/main/java/com/music/bitchord/playback/PlaybackService.kt"
if os.path.exists(ps_path):
    with open(ps_path, "r", encoding="utf-8") as f:
        ps = f.read()

    if "resolveAlbumMetadata" not in ps:
        target_trigger = """        mediaItem?.mediaId?.let { id ->
            resolveLocalBitrate(id, mediaItem)
        }"""
        new_trigger = """        mediaItem?.mediaId?.let { id ->
            resolveLocalBitrate(id, mediaItem)
        }
        if (mediaItem != null && mediaItem.mediaMetadata.albumTitle.isNullOrBlank() &&
            !mediaItem.mediaId.startsWith("content://") && !mediaItem.mediaId.startsWith("file://")
        ) {
            resolveAlbumMetadata(mediaItem)
        }"""
        ps = ps.replace(target_trigger, new_trigger, 1)

        method_code = """    private var albumResolveJob: Job? = null

    private fun resolveAlbumMetadata(currentItem: MediaItem) {
        val mediaId = currentItem.mediaId
        albumResolveJob?.cancel()
        albumResolveJob = scope.launch(Dispatchers.IO) {
            val song = YtMusicRepository.trackLinks(mediaId).getOrNull() ?: return@launch
            val albumName = song.albumName?.takeIf { it.isNotBlank() } ?: return@launch
            withContext(Dispatchers.Main) {
                val activePlayer = player ?: return@withContext
                val currentIndex = activePlayer.currentMediaItemIndex
                val liveItem = activePlayer.currentMediaItem ?: return@withContext
                if (liveItem.mediaId != mediaId) return@withContext
                if (!liveItem.mediaMetadata.albumTitle.isNullOrBlank()) return@withContext

                val updatedExtras = (liveItem.mediaMetadata.extras ?: Bundle()).apply {
                    if (song.albumId != null) putString("bitchord.albumId", song.albumId)
                }
                val updatedMetadata = liveItem.mediaMetadata.buildUpon()
                    .setAlbumTitle(albumName)
                    .setExtras(updatedExtras)
                    .build()
                val updatedItem = liveItem.buildUpon()
                    .setMediaMetadata(updatedMetadata)
                    .build()

                val pos = activePlayer.currentPosition
                val wasPlaying = activePlayer.isPlaying
                swappingMediaId = mediaId
                activePlayer.replaceMediaItem(currentIndex, updatedItem)
                activePlayer.seekTo(currentIndex, pos)
                if (wasPlaying) activePlayer.play()
                val updatedSong = updatedItem.toSong()
                if (listenBrainzSong?.videoId == mediaId) {
                    listenBrainzSong = updatedSong
                }
            }
        }
    }

"""
        ps = ps.replace("    override fun onCreate() {", method_code + "    override fun onCreate() {", 1)

        with open(ps_path, "w", encoding="utf-8") as f:
            f.write(ps)
        print("PlaybackService.kt patched for album metadata resolution.")

# 3. Patch HomeScreen.kt (Memória de rolagem global + fotos redondas de artistas)
hs_path = "sharedUi/src/jvmSharedMain/kotlin/com/music/bitchord/ui/screens/HomeScreen.kt"
if os.path.exists(hs_path):
    with open(hs_path, "r", encoding="utf-8") as f:
        hs = f.read()

    if "import androidx.compose.runtime.saveable.rememberSaveable" not in hs:
        hs = hs.replace(
            "import androidx.compose.runtime.remember",
            "import androidx.compose.runtime.remember\\nimport androidx.compose.runtime.DisposableEffect\\nimport androidx.compose.runtime.saveable.rememberSaveable"
        )

    if "homeShelfScrollPositions" not in hs:
        hs = hs.replace(
            'private const val RECENT_TRACKS_PER_COLUMN = 4',
            'private const val RECENT_TRACKS_PER_COLUMN = 4\\n\\n/** Stores the scroll state of home shelves across screen transitions. */\\nprivate val homeShelfScrollPositions = mutableMapOf<String, Pair<Int, Int>>()'
        )

    old_shelf = """@Composable
internal fun Shelf(
    shelf: HomeShelf,
    onItemClick: (ShelfItem) -> Unit,
    onItemLongPress: ((ShelfItem) -> Unit)? = null,
    leadingCard: (@Composable () -> Unit)? = null,
    currentSong: Song? = null,
    isPlaying: Boolean = false,
) {
    Column(Modifier.padding(bottom = 26.dp)) {
        SectionHeader(shelf.title, shelf.subtitle)
        ShelfRow(
            contentPadding = PaddingValues(horizontal = PAGE_GUTTER),
            horizontalArrangement = Arrangement.spacedBy(14.dp),
        ) {"""

    new_shelf = """@Composable
internal fun Shelf(
    shelf: HomeShelf,
    onItemClick: (ShelfItem) -> Unit,
    onItemLongPress: ((ShelfItem) -> Unit)? = null,
    leadingCard: (@Composable () -> Unit)? = null,
    currentSong: Song? = null,
    isPlaying: Boolean = false,
) {
    val shelfKey = shelf.browseId ?: shelf.title
    val rowState = rememberSaveable(shelfKey, saver = LazyListState.Saver) {
        val (index, offset) = homeShelfScrollPositions[shelfKey] ?: (0 to 0)
        LazyListState(firstVisibleItemIndex = index, firstVisibleItemScrollOffset = offset)
    }
    DisposableEffect(shelfKey, rowState) {
        onDispose {
            homeShelfScrollPositions[shelfKey] = rowState.firstVisibleItemIndex to rowState.firstVisibleItemScrollOffset
        }
    }
    Column(Modifier.padding(bottom = 26.dp)) {
        SectionHeader(shelf.title, shelf.subtitle)
        ShelfRow(
            state = rowState,
            contentPadding = PaddingValues(horizontal = PAGE_GUTTER),
            horizontalArrangement = Arrangement.spacedBy(14.dp),
        ) {"""
    hs = hs.replace(old_shelf, new_shelf)

    old_hero_shelf = """@Composable
private fun HeroShelf(
    shelf: HomeShelf,
    onItemClick: (ShelfItem) -> Unit,
    onItemLongPress: ((ShelfItem) -> Unit)? = null,
    currentSong: Song? = null,
    isPlaying: Boolean = false,
) {
    Column(Modifier.padding(bottom = 26.dp)) {
        SectionHeader(shelf.title, shelf.subtitle)
        // Measured rather than taken as a share of the parent, because the card
        // has a ceiling as well as a fraction — see [heroCardWidth]. A fixed
        // width is also the only one of the two the aspect ratio below can turn
        // into a height, so the card keeps its shape however it was arrived at.
        BoxWithConstraints {
            val cardWidth = heroCardWidth(maxWidth)
            ShelfRow(
                state = rememberLazyListState(),
                contentPadding = PaddingValues(horizontal = PAGE_GUTTER),
                horizontalArrangement = Arrangement.spacedBy(14.dp),
            ) {"""

    new_hero_shelf = """@Composable
private fun HeroShelf(
    shelf: HomeShelf,
    onItemClick: (ShelfItem) -> Unit,
    onItemLongPress: ((ShelfItem) -> Unit)? = null,
    currentSong: Song? = null,
    isPlaying: Boolean = false,
) {
    val shelfKey = shelf.browseId ?: shelf.title
    val rowState = rememberSaveable(shelfKey, saver = LazyListState.Saver) {
        val (index, offset) = homeShelfScrollPositions[shelfKey] ?: (0 to 0)
        LazyListState(firstVisibleItemIndex = index, firstVisibleItemScrollOffset = offset)
    }
    DisposableEffect(shelfKey, rowState) {
        onDispose {
            homeShelfScrollPositions[shelfKey] = rowState.firstVisibleItemIndex to rowState.firstVisibleItemScrollOffset
        }
    }
    Column(Modifier.padding(bottom = 26.dp)) {
        SectionHeader(shelf.title, shelf.subtitle)
        BoxWithConstraints {
            val cardWidth = heroCardWidth(maxWidth)
            ShelfRow(
                state = rowState,
                contentPadding = PaddingValues(horizontal = PAGE_GUTTER),
                horizontalArrangement = Arrangement.spacedBy(14.dp),
            ) {"""
    hs = hs.replace(old_hero_shelf, new_hero_shelf)

    old_shelf_card_art = """            else -> {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .aspectRatio(1f)
                        .clip(RoundedCornerShape(12.dp))
                        .thumbnailBorder(RoundedCornerShape(12.dp))
                        .background(MaterialTheme.colorScheme.surfaceVariant),
                ) {"""

    new_shelf_card_art = """            else -> {
                val isArtistCard = item.browseId?.startsWith("UC") == true ||
                    item.browseId?.startsWith("FEmusic_library_corpus_artist") == true ||
                    item.subtitle.equals("Artist", ignoreCase = true) ||
                    item.subtitle.equals("Artista", ignoreCase = true) ||
                    item.subtitle.contains("Artist •", ignoreCase = true) ||
                    item.subtitle.contains("Artista •", ignoreCase = true) ||
                    item.subtitle.contains("• Artist", ignoreCase = true) ||
                    item.subtitle.contains("• Artista", ignoreCase = true)
                val cardShape = if (isArtistCard) CircleShape else RoundedCornerShape(12.dp)
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .aspectRatio(1f)
                        .clip(cardShape)
                        .thumbnailBorder(cardShape)
                        .background(MaterialTheme.colorScheme.surfaceVariant),
                ) {"""
    hs = hs.replace(old_shelf_card_art, new_shelf_card_art)

    with open(hs_path, "w", encoding="utf-8") as f:
        f.write(hs)
    print("HomeScreen.kt patched for scroll memory and round artist cards.")

# 4. Patch SearchScreen.kt (Prioridade na busca: artistas no topo + fotos circulares)
ss_path = "sharedUi/src/jvmSharedMain/kotlin/com/music/bitchord/ui/screens/SearchScreen.kt"
if os.path.exists(ss_path):
    with open(ss_path, "r", encoding="utf-8") as f:
        ss = f.read()

    old_sections = """    return listOf(
        SearchSection("Songs", rows.filterIsInstance<SearchResult.Track>()),
        SearchSection("Artists", rows.filterIsInstance<SearchResult.Browse>().filter { it.item.type == BrowseType.ARTIST }),"""

    new_sections = """    return listOf(
        SearchSection("Artists", rows.filterIsInstance<SearchResult.Browse>().filter { it.item.type == BrowseType.ARTIST }),
        SearchSection("Songs", rows.filterIsInstance<SearchResult.Track>()),"""
    ss = ss.replace(old_sections, new_sections)

    old_recent_entity = """        Box(Modifier.size(52.dp)) {
            AsyncImage(
                model = entity.artworkUrl,
                contentDescription = null,
                modifier = Modifier
                    .size(52.dp)
                    .clip(RoundedCornerShape(8.dp))
                    .thumbnailBorder(RoundedCornerShape(8.dp))
                    .background(MaterialTheme.colorScheme.surfaceVariant),
            )"""

    new_recent_entity = """        Box(Modifier.size(52.dp)) {
            val isArtist = entity.entityType == EntityType.ARTIST
            val entityShape = if (isArtist) CircleShape else RoundedCornerShape(8.dp)
            AsyncImage(
                model = entity.artworkUrl,
                contentDescription = null,
                modifier = Modifier
                    .size(52.dp)
                    .clip(entityShape)
                    .thumbnailBorder(entityShape)
                    .background(MaterialTheme.colorScheme.surfaceVariant),
            )"""
    ss = ss.replace(old_recent_entity, new_recent_entity)

    with open(ss_path, "w", encoding="utf-8") as f:
        f.write(ss)
    print("SearchScreen.kt patched for artist priority in search and round recent entity cards.")

print("All Sonium 0.2.0 patches applied successfully!")
