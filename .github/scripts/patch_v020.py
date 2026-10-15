import os
import re

print("Starting Sonium 0.5.0 patch application...")

# 0. Patch app/build.gradle.kts (Versionamento: Sonium 0.5.0)
gradle_path = "app/build.gradle.kts"
if os.path.exists(gradle_path):
    with open(gradle_path, "r", encoding="utf-8") as f:
        gc = f.read()
    gc = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "0.5.0"', gc)
    gc = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 33', gc)
    gc = gc.replace('resValue("string", "app_name", "BitChord Dev")', 'resValue("string", "app_name", "Sonium Dev")')
    with open(gradle_path, "w", encoding="utf-8") as f:
        f.write(gc)
    print("app/build.gradle.kts patched to version 0.5.0 and Sonium Dev.")

# 1. Patch InnertubeParser.kt (Parser de artista limpo sem rótulo de tipo)
ip_path = "shared/src/jvmSharedMain/kotlin/com/music/bitchord/data/innertube/InnertubeParser.kt"
if os.path.exists(ip_path):
    with open(ip_path, "r", encoding="utf-8") as f:
        ipc = f.read()
    new_type_words = """    private val TYPE_WORDS = setOf(
        "song", "video", "album", "single", "ep", "artist",
        "playlist", "podcast", "episode", "música", "musica",
        "vídeo", "faixa", "áudio", "audio", "track", "álbum", "artista",
    )"""
    ipc = re.sub(
        r'private val TYPE_WORDS\s*=\s*setOf\([^)]+\)',
        new_type_words.strip(),
        ipc,
        flags=re.DOTALL
    )
    if "val validGroups = groups.filter" not in ipc:
        target_runs_pattern = re.compile(
            r'val artistGroup = groups\.firstOrNull \{ group ->\s*group\.any \{ run ->\s*val pageType = run\.o\("navigationEndpoint"\)\.o\("browseEndpoint"\)\s*\.o\("browseEndpointContextSupportedConfigs"\)\s*\.o\("browseEndpointContextMusicConfig"\)\.s\("pageType"\)\.orEmpty\(\)\s*"ARTIST" in pageType\s*\}\s*\} \?: return null',
            re.DOTALL
        )
        replacement_artist_runs = """val validGroups = groups.filter { group ->
            val text = group.joinToString("") { it.s("text").orEmpty() }.trim()
            val lower = text.lowercase(Locale.ROOT)
            text.isNotBlank() && lower !in TYPE_WORDS && !text.matches(DURATION) && !text.matches(TALLY) && !text.matches(YEAR)
        }
        val artistGroup = validGroups.firstOrNull { group ->
            group.any { run ->
                val browse = run.o("navigationEndpoint").o("browseEndpoint")
                val pageType = browse?.o("browseEndpointContextSupportedConfigs")
                    ?.o("browseEndpointContextMusicConfig")?.s("pageType").orEmpty()
                val browseId = browse?.s("browseId").orEmpty()
                "ARTIST" in pageType || "USER_CHANNEL" in pageType || browseId.startsWith("UC")
            }
        } ?: validGroups.firstOrNull() ?: return null"""
        ipc = target_runs_pattern.sub(replacement_artist_runs, ipc)
    with open(ip_path, "w", encoding="utf-8") as f:
        f.write(ipc)
    print("InnertubeParser.kt patched for clean artist runs.")

# 2. Patch PlayerConnection.kt (Sanitização de artista no player)
pc_path = "app/src/main/java/com/music/bitchord/playback/PlayerConnection.kt"
if os.path.exists(pc_path):
    with open(pc_path, "r", encoding="utf-8") as f:
        pc = f.read()
    helper = r'''private const val ARTISTS_NAMES = "artistNames"
private const val ARTISTS_IDS = "artistIds"
private val MEDIA_PREFIX_REGEX = Regex("^(?:(?:m[úu]sica|song|v[íi]deo|track|faixa|áudio|audio|single|ep|álbum|album)\\s*[•·\\-|:]\\s*)+", RegexOption.IGNORE_CASE)
private val MEDIA_TYPE_ISOLATED = setOf("música", "musica", "song", "vídeo", "video", "track", "faixa", "áudio", "audio", "álbum", "album", "single", "ep", "artist", "artista")

fun cleanMediaArtist(raw: String): String {
    val cleaned = raw.replace(MEDIA_PREFIX_REGEX, "").trim()
    if (cleaned.lowercase(Locale.ROOT) in MEDIA_TYPE_ISOLATED) {
        return ""
    }
    return cleaned
}
'''
    if "fun cleanMediaArtist(" not in pc:
        target_artists = 'private const val ARTISTS_NAMES = "artistNames"\nprivate const val ARTISTS_IDS = "artistIds"'
        if target_artists in pc:
            pc = pc.replace(target_artists, helper.strip())
        else:
            pc = re.sub(r'private const val ARTISTS_NAMES = "artistNames"\r?\nprivate const val ARTISTS_IDS = "artistIds"', helper.strip(), pc)
    else:
        old_helper = r'''fun cleanMediaArtist(raw: String): String =
    raw.replace(MEDIA_PREFIX_REGEX, "").trim()'''
        new_helper = r'''fun cleanMediaArtist(raw: String): String {
    val cleaned = raw.replace(MEDIA_PREFIX_REGEX, "").trim()
    if (cleaned.lowercase(Locale.ROOT) in MEDIA_TYPE_ISOLATED) {
        return ""
    }
    return cleaned
}'''
        if old_helper in pc:
            pc = pc.replace(old_helper, new_helper)

    pc = pc.replace(
        'artist = mediaMetadata.artist?.toString().orEmpty(),',
        'artist = cleanMediaArtist(mediaMetadata.artist?.toString().orEmpty()).ifBlank { mediaMetadata.extras?.artistsFromBundle()?.firstOrNull()?.name?.let { cleanMediaArtist(it) }?.ifBlank { null } ?: "Unknown artist" },'
    )
    pc = pc.replace(
        'artist = b.getString("artist").orEmpty(),',
        'artist = cleanMediaArtist(b.getString("artist").orEmpty()).ifBlank { b.artistsFromBundle().firstOrNull()?.name?.let { cleanMediaArtist(it) }?.ifBlank { null } ?: "Unknown artist" },'
    )
    old_to_media = """.setTitle(title)
            .setArtist(artist)"""
    new_to_media = """.setTitle(title)
            .setArtist(cleanMediaArtist(artist).ifBlank { artists.firstOrNull()?.name?.let { cleanMediaArtist(it) }?.ifBlank { null } ?: artist })"""
    pc = pc.replace(old_to_media, new_to_media)

    with open(pc_path, "w", encoding="utf-8") as f:
        f.write(pc)
    print("PlayerConnection.kt patched for clean artist.")

# 3. Patch PlaybackService.kt (Álbum no MediaSession mesmo em rádio/aleatório)
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

# 4. Patch HomeScreen.kt (Memória de rolagem global + fotos redondas de artistas)
hs_path = "sharedUi/src/jvmSharedMain/kotlin/com/music/bitchord/ui/screens/HomeScreen.kt"
if os.path.exists(hs_path):
    with open(hs_path, "r", encoding="utf-8") as f:
        hs = f.read()
    if "import androidx.compose.runtime.saveable.rememberSaveable" not in hs:
        hs = re.sub(
            r'import androidx\.compose\.runtime\.remember\r?\n',
            'import androidx.compose.runtime.remember\nimport androidx.compose.runtime.DisposableEffect\nimport androidx.compose.runtime.saveable.rememberSaveable\n',
            hs,
            count=1
        )
    if "homeShelfScrollPositions" not in hs:
        hs = re.sub(
            r'private const val RECENT_TRACKS_PER_COLUMN = 4',
            'private const val RECENT_TRACKS_PER_COLUMN = 4\n\n/** Stores the scroll state of home shelves across screen transitions. */\nprivate val homeShelfScrollPositions = mutableMapOf<String, Pair<Int, Int>>()',
            hs,
            count=1
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
    val rowState = rememberSaveable(key = shelfKey, saver = LazyListState.Saver) {
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
    if old_shelf in hs:
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
    val rowState = rememberSaveable(key = shelfKey, saver = LazyListState.Saver) {
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
    if old_hero_shelf in hs:
        hs = hs.replace(old_hero_shelf, new_hero_shelf)

    old_shelf_card_art = """        else -> {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .aspectRatio(1f)
                    .clip(RoundedCornerShape(12.dp))
                    .thumbnailBorder(RoundedCornerShape(12.dp))
                    .background(MaterialTheme.colorScheme.surfaceVariant),
            ) {"""
    new_shelf_card_art = """        else -> {
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
    if old_shelf_card_art in hs:
        hs = hs.replace(old_shelf_card_art, new_shelf_card_art)

    with open(hs_path, "w", encoding="utf-8") as f:
        f.write(hs)
    print("HomeScreen.kt patched for scroll memory and round artist cards.")

# 5. Patch DetailScreen.kt (Fotos redondas na seção de fãs também podem gostar)
ds_path = "app/src/main/java/com/music/bitchord/ui/screens/DetailScreen.kt"
if os.path.exists(ds_path):
    with open(ds_path, "r", encoding="utf-8") as f:
        ds = f.read()
    sec_card_pattern = re.compile(
        r'(\s+)AsyncImage\(\s*model\s*=\s*item\.thumbnailUrl\.artworkAt\(CARD_ART_PX\),\s*contentDescription\s*=\s*null,\s*modifier\s*=\s*Modifier\s*\.fillMaxWidth\(\)\s*\.aspectRatio\(1f\)\s*\.clip\(RoundedCornerShape\(10\.dp\)\)\s*\.thumbnailBorder\(RoundedCornerShape\(10\.dp\)\)\s*\.background\(palette\.elevated\),\s*\)',
        re.DOTALL
    )
    new_sec_card_replacement = r'''\1val isArtistCard = item.browseId?.startsWith("UC") == true ||
\1    item.browseId?.startsWith("FEmusic_library_corpus_artist") == true ||
\1    item.subtitle.equals("Artist", ignoreCase = true) ||
\1    item.subtitle.equals("Artista", ignoreCase = true) ||
\1    item.subtitle.contains("Artist •", ignoreCase = true) ||
\1    item.subtitle.contains("Artista •", ignoreCase = true) ||
\1    item.subtitle.contains("• Artist", ignoreCase = true) ||
\1    item.subtitle.contains("• Artista", ignoreCase = true) ||
\1    item.subtitle.contains("subscribers", ignoreCase = true) ||
\1    item.subtitle.contains("inscritos", ignoreCase = true)
\1val cardShape = if (isArtistCard) CircleShape else RoundedCornerShape(10.dp)
\1AsyncImage(
\1    model = item.thumbnailUrl.artworkAt(CARD_ART_PX),
\1    contentDescription = null,
\1    contentScale = ContentScale.Crop,
\1    modifier = Modifier
\1        .fillMaxWidth()
\1        .aspectRatio(1f)
\1        .clip(cardShape)
\1        .thumbnailBorder(cardShape)
\1        .background(palette.elevated),
\1)'''
    if sec_card_pattern.search(ds):
        ds = sec_card_pattern.sub(new_sec_card_replacement, ds)
        with open(ds_path, "w", encoding="utf-8") as f:
            f.write(ds)
        print("DetailScreen.kt patched for round artist SectionCard.")
    elif "val isArtistCard = item.browseId?.startsWith(\"UC\")" in ds:
        print("DetailScreen.kt SectionCard already patched.")

# 6. Patch SearchScreen.kt (Prioridade na busca: artistas no topo + tradução para português)
ss_path = "sharedUi/src/jvmSharedMain/kotlin/com/music/bitchord/ui/screens/SearchScreen.kt"
if os.path.exists(ss_path):
    with open(ss_path, "r", encoding="utf-8") as f:
        ss = f.read()
    new_sec_pt = """    return listOf(
        SearchSection("Artistas", rows.filterIsInstance<SearchRow.ItemRow>().filter { it.item.type == BrowseType.ARTIST }),
        SearchSection("Músicas", rows.filterIsInstance<SearchRow.ItemRow>().filter { it.item.type == BrowseType.SONG }),
        SearchSection("Álbuns", rows.filterIsInstance<SearchRow.ItemRow>().filter { it.item.type == BrowseType.ALBUM }),
        SearchSection("Playlists", rows.filterIsInstance<SearchRow.ItemRow>().filter { it.item.type == BrowseType.PLAYLIST }),
        SearchSection("Mais", rows.filterIsInstance<SearchRow.ItemRow>().filter { it.item.type == BrowseType.OTHER }),
    ).filter { it.rows.isNotEmpty() }"""
    ss = re.sub(
        r'return listOf\(\s*SearchSection\("(?:Songs|Artists)".*?\)\.filter \{ it\.rows\.isNotEmpty\(\) \}',
        new_sec_pt.strip(),
        ss,
        flags=re.DOTALL
    )

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
    if old_recent_entity in ss:
        ss = ss.replace(old_recent_entity, new_recent_entity)

    with open(ss_path, "w", encoding="utf-8") as f:
        f.write(ss)
    print("SearchScreen.kt patched for translated sections and round recent entity cards.")

# 7. Patch LibraryScreen.kt (Fotos redondas nos artistas da biblioteca e Ver tudo)
ls_path = "sharedUi/src/jvmSharedMain/kotlin/com/music/bitchord/ui/screens/LibraryScreen.kt"
if os.path.exists(ls_path):
    with open(ls_path, "r", encoding="utf-8") as f:
        ls = f.read()
    old_grid_items = """                items(sortedShelf.items, key = { it.browseId ?: it.title }) { item ->
                    ShelfCard(
                        item = item,
                        onClick = { onItemClick(item) },
                        onLongPress = { onItemLongPress(item) },
                        modifier = Modifier.fillMaxWidth(),
                        isPinned = item.browseId != null && item.browseId in pinnedPlaylists,
                    )
                }"""
    new_grid_items = """                val isArtistShelf = shelf.title.equals("Artists", ignoreCase = true) ||
                    shelf.title.equals("Artistas", ignoreCase = true)
                items(sortedShelf.items, key = { it.browseId ?: it.title }) { rawItem ->
                    val item = if (isArtistShelf && rawItem.subtitle.isBlank()) {
                        rawItem.copy(subtitle = "Artista")
                    } else if (isArtistShelf && !rawItem.subtitle.contains("Artist", ignoreCase = true) && !rawItem.subtitle.contains("Artista", ignoreCase = true)) {
                        rawItem.copy(subtitle = "Artista • ${rawItem.subtitle}")
                    } else rawItem
                    ShelfCard(
                        item = item,
                        onClick = { onItemClick(item) },
                        onLongPress = { onItemLongPress(item) },
                        modifier = Modifier.fillMaxWidth(),
                        isPinned = item.browseId != null && item.browseId in pinnedPlaylists,
                    )
                }"""
    if old_grid_items in ls:
        ls = ls.replace(old_grid_items, new_grid_items)

    old_shelf_items = """                items(visibleItems) { item ->
                    ShelfCard(
                        item = item,
                        onClick = { onItemClick(item) },
                        onLongPress = { onItemLongPress(item) },
                        isPinned = item.browseId != null && item.browseId in pinnedPlaylists,
                    )
                }"""
    new_shelf_items = """                items(visibleItems) { rawItem ->
                    val item = if (isArtistShelf && rawItem.subtitle.isBlank()) {
                        rawItem.copy(subtitle = "Artista")
                    } else if (isArtistShelf && !rawItem.subtitle.contains("Artist", ignoreCase = true) && !rawItem.subtitle.contains("Artista", ignoreCase = true)) {
                        rawItem.copy(subtitle = "Artista • ${rawItem.subtitle}")
                    } else rawItem
                    ShelfCard(
                        item = item,
                        onClick = { onItemClick(item) },
                        onLongPress = { onItemLongPress(item) },
                        isPinned = item.browseId != null && item.browseId in pinnedPlaylists,
                    )
                }"""
    if old_shelf_items in ls:
        ls = ls.replace(old_shelf_items, new_shelf_items)

    with open(ls_path, "w", encoding="utf-8") as f:
        f.write(ls)
    print("LibraryScreen.kt patched for round artist cards in shelf and Ver tudo grid.")

# 8. Patch Models.kt (Tradução das cápsulas de busca)
models_path = "shared/src/commonMain/kotlin/com/music/bitchord/data/model/Models.kt"
if os.path.exists(models_path):
    with open(models_path, "r", encoding="utf-8") as f:
        mc = f.read()
    mc = mc.replace('ALL("All", null)', 'ALL("Tudo", null)')
    mc = mc.replace('ALL("Todos", null)', 'ALL("Tudo", null)')
    mc = mc.replace('SONGS("Songs",', 'SONGS("Músicas",')
    mc = mc.replace('VIDEOS("Videos",', 'VIDEOS("Vídeos",')
    mc = mc.replace('ALBUMS("Albums",', 'ALBUMS("Álbuns",')
    mc = mc.replace('ARTISTS("Artists",', 'ARTISTS("Artistas",')
    mc = mc.replace('PLAYLISTS("Playlists",', 'PLAYLISTS("Playlists",')
    with open(models_path, "w", encoding="utf-8") as f:
        f.write(mc)
    print("Models.kt patched for Portuguese SearchFilter labels.")

print("All Sonium 0.5.0 patches applied successfully!")
