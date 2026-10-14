package com.music.bitchord.data

import com.music.bitchord.data.DebugLog as Log
import com.music.bitchord.data.innertube.Innertube
import com.music.bitchord.data.innertube.InnertubeParser
import com.music.bitchord.data.model.Account
import com.music.bitchord.data.model.AccountChannel
import com.music.bitchord.data.model.isExactArtistMatch
import com.music.bitchord.data.model.normalizedArtistName
import com.music.bitchord.data.model.ArtistPage
import com.music.bitchord.data.model.BrowseType
import com.music.bitchord.data.model.HomeFeed
import com.music.bitchord.data.model.HomeShelf
import com.music.bitchord.data.model.LibraryPage
import com.music.bitchord.data.model.LibraryState
import com.music.bitchord.data.model.LikeStatus
import com.music.bitchord.data.model.MoodGenreSection
import com.music.bitchord.data.model.playlistMoves
import com.music.bitchord.data.model.PlaylistPrivacy
import com.music.bitchord.data.model.SearchFilter
import com.music.bitchord.data.model.SearchResult
import com.music.bitchord.data.model.ShelfItem
import com.music.bitchord.data.model.Song
import com.music.bitchord.data.model.SongMenu
import com.music.bitchord.data.model.UserPlaylist
import com.music.bitchord.data.sources.TrackMatcher
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.JsonObject
import java.util.Locale
import java.util.concurrent.ConcurrentHashMap

/** Suspend API over Innertube. Every call returns a Result so the UI can show a real error. */
object YtMusicRepository {

    private const val TAG = "BitChord"
    private val moodGenreShelfCache = ConcurrentHashMap<String, List<HomeShelf>>()
    // Includes unchanged video fallbacks as well as successful matches. The
    // queue prefetcher asks before a track becomes current; remembering its
    // answer makes the eventual player switch use the exact rendition whose
    // bytes were warmed, without repeating a 10–30 second catalogue search.
    private val audioVersionCache = ConcurrentHashMap<String, Song>()
    // Cache for video version lookups from audio tracks (null means no video found).
    private val videoVersionCache = ConcurrentHashMap<String, Song?>()
    // Cache for artist pages in memory for instant subsequent loads
    private val artistPageCache = ConcurrentHashMap<String, ArtistPage>()
    // In-memory cache for user liked songs
    private var cachedLikedSongs: List<Song>? = null

    fun cachedAudioVersion(videoId: String): Song? = audioVersionCache[videoId]
    fun cachedVideoVersion(videoId: String): Song? = videoVersionCache[videoId]
    fun cachedLikedMusic(): List<Song>? = cachedLikedSongs
    fun clearArtistPageCache() { artistPageCache.clear() }

    /**
     * Retrieves the list of liked songs from memory cache or fetches from LM playlist.
     */
    suspend fun likedSongsList(): List<Song> {
        cachedLikedSongs?.takeIf { it.isNotEmpty() }?.let { return it }
        val fetched = runCatching {
            allSongs(LIKED_MUSIC).getOrNull() ?: browseSongs(LIKED_MUSIC).getOrNull()?.songs
        }.getOrNull().orEmpty()
        if (fetched.isNotEmpty()) {
            cachedLikedSongs = fetched
        }
        return fetched
    }

    /**
     * The core personalised feed. It stays deliberately independent from the
     * optional shelves below: callers can paint this response immediately,
     * rather than making the Play page wait for every supplementary endpoint.
     *
     * FEmusic_home's own continuation token comes back, for [moreHome] —
     * signed in, it keeps paging into mood mixes and more personalised
     * shelves the same way the official app does as you scroll; signed out
     * it's empty and there's nothing more to fetch.
     */
    suspend fun home(): Result<HomeFeed> = call("home") {
        val home = Innertube.browse("FEmusic_home")
        HomeFeed(InnertubeParser.parseHome(home), InnertubeParser.continuationToken(home))
    }

    /** Recently played is rendered independently, at the top of the Play page. */
    suspend fun homeRecentlyPlayed(): Result<HomeShelf?> = call("home:recent") { recentlyPlayed() }

    /** Extra Play shelves are independently fetchable so each can appear as soon as it arrives. */
    suspend fun homeSupplement(browseId: String): Result<List<HomeShelf>> = call("home:$browseId") {
        shelvesOf(browseId)
    }

    val HOME_SUPPLEMENT_BROWSE_IDS = listOf(
        "FEmusic_new_releases",
        "FEmusic_explore",
    )

    /**
     * More Home shelves past [home]'s first page, following FEmusic_home's
     * own continuation — the lever the official app pulls as you scroll
     * rather than a fixed one-shot page. "Recently played" and
     * FEmusic_new_releases are one-shot and don't participate.
     */
    suspend fun moreHome(token: String): Result<HomeFeed> = call("home:more") {
        val response = Innertube.browseContinuation(token)
        HomeFeed(
            shelves = InnertubeParser.parseHomeContinuation(response),
            continuation = InnertubeParser.continuationToken(response),
        )
    }

    /**
     * The lead shelf: the account's listening history, newest first.
     *
     * YouTube's home already carries a "Listen again", but it ranks by how
     * *often* something has been played rather than how recently — so it keeps
     * leading with last month's favourites for days after a change of mood,
     * which reads as the feed being broken. The history feed reflects a play
     * the moment it's registered, so it's what the top of the page is built
     * from. YouTube's own shelf stays below, where its ranking is a feature.
     *
     * Signed-in only; there is no history to read as a guest.
     */
    private suspend fun recentlyPlayed(): HomeShelf? {
        val ytSongs = if (Innertube.cookie != null) {
            runCatching { fetchHistory() }.getOrDefault(emptyList())
        } else {
            emptyList()
        }

        val allSongs = ytSongs.distinctBy { it.videoId }.take(RECENT_LIMIT)
        if (allSongs.isEmpty()) return null
        return HomeShelf(
            title = RECENT_TITLE,
            items = allSongs.map {
                ShelfItem(
                    title = it.title,
                    subtitle = it.artist,
                    thumbnailUrl = it.thumbnailUrl,
                    videoId = it.videoId,
                    browseId = null,
                )
            },
        )
    }

    /**
     * The raw fetch behind both [recentlyPlayed] and [history]: the account's
     * listening history, newest first, one row per play collapsed to one row
     * per track.
     *
     * A track played three times today is three rows in the feed — what that
     * dedupe costs is the times, which is fine for "what you have been
     * listening to" but would matter for a log. YouTube's own page groups them
     * under Today and Yesterday headings that the shelf parser doesn't carry
     * through either.
     */
    private suspend fun fetchHistory(): List<Song> =
        InnertubeParser.collectSongsDeep(Innertube.browse(HISTORY)).distinctBy { it.videoId }

    /**
     * The account's listening history, in the order YouTube Music keeps it.
     *
     * The same feed [recentlyPlayed] reads, without the truncation: that one is
     * a shelf on the home page and stops at [RECENT_LIMIT] so it stays a shelf,
     * whereas this is the page you open when twenty is not enough.
     */
    suspend fun history(): Result<List<Song>> = call("history") { fetchHistory() }

    /** Account listening history for the Recents feed. */
    suspend fun recents(): Result<List<Song>> = call("recents") {
        if (Innertube.cookie != null) {
            val history = runCatching { fetchHistory() }.getOrDefault(emptyList())
            if (history.isNotEmpty()) return@call history
        }
        emptyList()
    }

    /**
     * Recommended discovery tracks for Quick Picks, strictly excluding listening history and recents.
     */
    suspend fun quickPicks(excludeSongIds: Set<String> = emptySet()): Result<List<Song>> = call("quickPicks") {
        val homeRaw = runCatching { Innertube.browse("FEmusic_home") }.getOrNull()
        val shelves = if (homeRaw != null) InnertubeParser.parseHome(homeRaw) else emptyList()

        // 1. Direct "Quick picks" or "Mix" or "Recommendations" shelf
        val qpShelf = shelves.firstOrNull {
            it.title.contains("quick", ignoreCase = true) ||
                it.title.contains("pick", ignoreCase = true) ||
                it.title.contains("mix", ignoreCase = true) ||
                it.title.contains("recommend", ignoreCase = true)
        }
        val qpSongs = qpShelf?.items?.mapNotNull { item ->
            item.videoId?.takeUnless { it in excludeSongIds }?.let { vid ->
                Song(
                    videoId = vid,
                    title = item.title,
                    artist = InnertubeParser.artistFromSubtitle(item.subtitle),
                    thumbnailUrl = item.thumbnailUrl,
                )
            }
        }.orEmpty()
        if (qpSongs.isNotEmpty()) return@call qpSongs

        // 2. All shelves on Home (excluding shelves mentioning recent/history, and skipping top shelf if multiple exist)
        val candidateShelves = if (shelves.size > 1) {
            shelves.drop(1).filterNot {
                it.title.contains("recent", ignoreCase = true) ||
                    it.title.contains("history", ignoreCase = true) ||
                    it.title.contains("listen again", ignoreCase = true)
            }
        } else shelves

        val homeShelfSongs = candidateShelves.flatMap { shelf ->
            shelf.items.mapNotNull { item ->
                item.videoId?.takeUnless { it in excludeSongIds }?.let { vid ->
                    Song(
                        videoId = vid,
                        title = item.title,
                        artist = InnertubeParser.artistFromSubtitle(item.subtitle),
                        thumbnailUrl = item.thumbnailUrl,
                    )
                }
            }
        }.distinctBy { it.videoId }

        if (homeShelfSongs.isNotEmpty()) return@call homeShelfSongs

        // 3. Any shelf items on Home that have videoId
        val allHomeTrackSongs = shelves.flatMap { shelf ->
            shelf.items.mapNotNull { item ->
                item.videoId?.let { vid ->
                    Song(
                        videoId = vid,
                        title = item.title,
                        artist = InnertubeParser.artistFromSubtitle(item.subtitle),
                        thumbnailUrl = item.thumbnailUrl,
                    )
                }
            }
        }.distinctBy { it.videoId }

        val uniqueAllHome = allHomeTrackSongs.filterNot { it.videoId in excludeSongIds }
        if (uniqueAllHome.isNotEmpty()) return@call uniqueAllHome

        // 4. Explore / New releases
        val explore = runCatching { shelvesOf("FEmusic_new_releases") }.getOrDefault(emptyList())
        val exploreSongs = explore.flatMap { shelf ->
            shelf.items.mapNotNull { item ->
                item.videoId?.takeUnless { it in excludeSongIds }?.let { vid ->
                    Song(
                        videoId = vid,
                        title = item.title,
                        artist = InnertubeParser.artistFromSubtitle(item.subtitle),
                        thumbnailUrl = item.thumbnailUrl,
                    )
                }
            }
        }.distinctBy { it.videoId }

        if (exploreSongs.isNotEmpty()) return@call exploreSongs

        // 5. Fallback if everything was filtered out
        allHomeTrackSongs.ifEmpty { exploreSongs }
    }

    private const val HISTORY = "FEmusic_history"
    private const val RECENT_TITLE = "Recents"

    /** Enough to scroll through, short of turning the shelf into the history page. */
    private const val RECENT_LIMIT = 20

    private suspend fun shelvesOf(browseId: String): List<HomeShelf> =
        InnertubeParser.parseHome(Innertube.browse(browseId))

    /** The server-defined mood and genre categories used by Explore. */
    suspend fun moodAndGenres(): Result<List<MoodGenreSection>> = call("moods-and-genres") {
        InnertubeParser.parseMoodAndGenres(Innertube.browse("FEmusic_moods_and_genres"))
    }

    /**
     * The playlist shelves behind one mood/genre category. This result also
     * supplies its tile artwork, so caching it avoids a second request when a
     * user taps a category whose cover has already appeared.
     */
    suspend fun moodGenreShelves(browseId: String, params: String?): Result<List<HomeShelf>> {
        val key = "$browseId:${params.orEmpty()}"
        moodGenreShelfCache[key]?.let { return Result.success(it) }
        return call("mood-genre:$browseId") {
            InnertubeParser.parseHome(Innertube.browse(browseId, params))
        }.also { result -> result.getOrNull()?.let { moodGenreShelfCache.putIfAbsent(key, it) } }
    }

    /** A category card borrows the first real cover from the playlists it opens. */
    suspend fun moodGenreArtwork(browseId: String, params: String?): Result<String?> =
        moodGenreShelves(browseId, params).map { shelves ->
            shelves.asSequence().flatMap { it.items.asSequence() }
                .mapNotNull(ShelfItem::thumbnailUrl)
                .firstOrNull()
        }

    /** One page of a search response, with the token for its next page if present. */
    data class SearchPage(
        val rows: List<SearchResult>,
        val continuation: String?,
    )

    /**
     * Fetches only the first search page. Publishing it immediately keeps the
     * search responsive; the UI asks [searchContinuation] for later pages as
     * the listener reaches the end of the list.
     */
    suspend fun searchPage(query: String, filter: SearchFilter): Result<SearchPage> =
        call("search:${filter.name}") {
            InnertubeParser.parseSearchPage(
                Innertube.search(query, filter.params),
                includeVideos = filter == SearchFilter.VIDEOS,
            ).let { page ->
                SearchPage(page.rows.distinctBy { it.identityKey() }, page.continuation)
            }
        }

    /** Fetches the next page of a search only when the result list needs it. */
    suspend fun searchContinuation(token: String, filter: SearchFilter): Result<SearchPage> = call("search:continuation") {
        InnertubeParser.parseSearchPage(
            Innertube.searchContinuation(token),
            includeVideos = filter == SearchFilter.VIDEOS,
        ).let { page ->
            SearchPage(page.rows.distinctBy { it.identityKey() }, page.continuation)
        }
    }

    /**
     * Compatibility helper for callers that need candidates but not a scrolling
     * result screen. Those callers need the first, most relevant page only.
     */
    suspend fun search(query: String, filter: SearchFilter): Result<List<SearchResult>> =
        searchPage(query, filter).map { it.rows }

    private fun SearchResult.identityKey(): String = when (this) {
        is SearchResult.TopTrack -> "v:${song.videoId}"
        is SearchResult.Track -> "v:${song.videoId}"
        is SearchResult.Browse -> "b:${item.browseId}"
    }

    /**
     * What YouTube Music would suggest completing [input] to, for the search
     * field's typeahead. Unfiltered on purpose: a suggestion is a query, and
     * which tab it is then run against is the user's to pick afterwards.
     */
    suspend fun searchSuggestions(input: String): Result<List<String>> =
        call("suggest") {
            InnertubeParser.parseSearchSuggestions(Innertube.searchSuggestions(input))
        }

    /**
     * Live media results for the typeahead phase — a lightweight search that
     * returns tracks, artists, and albums so the dropdown can show playable
     * cards alongside text completions. Uses the ALL filter to get mixed
     * results quickly; callers may want to limit how many they display.
     *
     * Deliberately unauthenticated: [Innertube.searchTypeahead] strips the
     * session cookie so YouTube Music does not log each debounced keystroke
     * to the account's server-side search history. Confirmed searches (Enter /
     * IME Search / tapping a suggestion) still use the normal authenticated
     * [searchPage] path and are recorded properly.
     */
    suspend fun searchTypeahead(input: String): Result<SearchPage> =
        call("typeahead:$input") {
            InnertubeParser.parseSearchPage(
                Innertube.searchTypeahead(input),
                includeVideos = false,
            ).let { page ->
                SearchPage(page.rows.distinctBy { it.identityKey() }, page.continuation)
            }
        }

    /**
     * The catalogue (audio-only) release of a music-video upload, found the
     * same way the "Switch to audio" toggle in the real app would land on
     * it: searching the title and artist and taking the closest song match.
     * Called before a video-tagged [Song] ever reaches the queue, so
     * playback, the mini player/notification, and YouTube's own history all
     * see the audio track — never the video upload's title, art or id.
     */
    suspend fun resolveAudio(song: Song): Song {
        if (!song.isVideo) return song
        audioVersionCache[song.videoId]?.let { return it }
        val target = TrackMatcher.targetOf(song)
        for (query in TrackMatcher.queries(target)) {
            val candidates = search(query, SearchFilter.SONGS)
                .getOrNull()
                ?.filterIsInstance<SearchResult.Track>()
                ?.map { it.song }
                .orEmpty()
            TrackMatcher.best(candidates, target)?.let { match ->
                Log.d(TAG, "audio switch: '${song.title}' -> '${match.title}' ($query)")
                audioVersionCache[song.videoId] = match
                return match
            }
            TrackMatcher.bestOfficialAudioForVideo(candidates, target)?.let { match ->
                Log.d(TAG, "audio switch: accepted video/runtime drift '${song.title}' -> '${match.title}' ($query)")
                audioVersionCache[song.videoId] = match
                return match
            }
        }
        Log.w(TAG, "audio switch: no official song match for '${song.title}' by '${song.artist}'")
        audioVersionCache[song.videoId] = song
        return song
    }

    /**
     * Resolves an audio-only track to its video version.
     */
    suspend fun resolveVideo(song: Song): Song? {
        if (song.isVideo) return null
        videoVersionCache[song.videoId]?.let { return it }
        val target = TrackMatcher.targetOf(song)
        for (query in TrackMatcher.queries(target)) {
            val candidates = search(query, SearchFilter.VIDEOS)
                .getOrNull()
                ?.filterIsInstance<SearchResult.Track>()
                ?.map { it.song }
                .orEmpty()
            TrackMatcher.best(candidates, target)?.let { match ->
                Log.d(TAG, "video switch: '${song.title}' -> '${match.title}' ($query)")
                videoVersionCache[song.videoId] = match
                return match
            }
        }
        Log.w(TAG, "video switch: no video match for '${song.title}' by '${song.artist}'")
        videoVersionCache[song.videoId] = null
        return null
    }

    /** Signed-in profile for the settings header. Null when signed out. */
    suspend fun account(): Result<Account> = call("account") {
        InnertubeParser.parseAccount(Innertube.accountMenu())
            ?: error("No account details")
    }

    suspend fun accountChannels(): Result<List<AccountChannel>> = call("channels") {
        val viaInnertube = runCatching {
            InnertubeParser.parseAccountChannels(Innertube.accountsList())
        }.onFailure { Log.w(TAG, "accounts_list unavailable: ${it.message}") }
            .getOrNull()
            .orEmpty()
        if (viaInnertube.isNotEmpty()) return@call viaInnertube
        InnertubeParser.parseAccountChannels(Innertube.accountSwitcher())
    }

    /**
     * The whole library in one shot — requires a signed-in session.
     */
    suspend fun library(): Result<LibraryPage> = call("library") {
        coroutineScope {
            val liked = async { browseSongs(LIKED_MUSIC).getOrNull() }
            val added = async { runCatching { songsPaged(LIBRARY_SONGS) }.getOrDefault(emptyList()) }
            val shelves = LIBRARY_FEEDS
                .map { (title, browseId) ->
                    async {
                        HomeShelf(title, runCatching { libraryItemsPaged(browseId) }.getOrDefault(emptyList()))
                    }
                }
                .awaitAll()
                .filter { it.items.isNotEmpty() }

            val likedPage = liked.await()
            val likedSongs = likedPage?.songs.orEmpty()
            val likedIds = likedSongs.mapTo(HashSet()) { it.videoId }
            LikeState.seedLiked(likedIds)
            if (likedSongs.isNotEmpty()) {
                cachedLikedSongs = likedSongs
            }
            LibraryPage(
                likedSongs = likedSongs,
                librarySongs = added.await().filterNot { it.videoId in likedIds },
                shelves = shelves,
                likedContinuation = likedPage?.continuation,
            )
        }
    }

    /**
     * Finishes syncing the liked collection into [LikeState], following
     * [firstToken] page by page until the feed runs dry.
     */
    suspend fun syncLikedMusic(
        firstToken: String?,
        loadNext: suspend (String) -> SongPage? = { moreSongs(it).getOrNull() },
    ) {
        if (firstToken == null) return
        val seen = HashSet<String>()
        var next: String? = firstToken
        while (next != null && seen.add(next)) {
            val page = loadNext(next) ?: return
            LikeState.seedLiked(page.songs.mapTo(HashSet()) { it.videoId })
            next = page.continuation
        }
    }

    /**
     * What YouTube Music would play on after [videoId]. Feeds AutoPlay; the
     * seed track itself comes back first, so callers filter what they have.
     */
    suspend fun radio(videoId: String): Result<List<Song>> = call("radio:$videoId") {
        InnertubeParser.parseWatchQueue(Innertube.next(videoId))
    }

    suspend fun findArtistPageId(name: String): Result<String?> = call("artistByName:$name") {
        if (normalizedArtistName(name).isEmpty()) return@call null
        val filter = SearchFilter.ARTISTS
        InnertubeParser.parseSearchPage(Innertube.search(name, filter.params)).rows
            .filterIsInstance<SearchResult.Browse>()
            .map { it.item }
            .firstOrNull { it.type == BrowseType.ARTIST && isExactArtistMatch(it.title, name) }
            ?.browseId
    }

    suspend fun trackLinks(videoId: String): Result<Song> = call("links:$videoId") {
        InnertubeParser.parseWatchQueue(Innertube.next(videoId))
            .firstOrNull { it.videoId == videoId }
            ?: error("no watch entry for $videoId")
    }

    data class SongPage(
        val songs: List<Song>,
        val continuation: String?,
        val suggested: List<Song> = emptyList(),
        val library: LibraryState? = null,
        val owned: Boolean? = null,
        val header: InnertubeParser.BrowseHeader? = null,
        val description: String? = null,
    )

    suspend fun browseSongs(browseId: String): Result<SongPage> = call("browse:$browseId") {
        val response = Innertube.browse(browseId)
        val page = if (browseId.startsWith("MPREb")) {
            albumPageOf(response)
        } else {
            pageOf(response)
        }
        if (!browseId.startsWith("VL")) page
        else page.copy(owned = InnertubeParser.parsePlaylistOwned(response))
    }

    private suspend fun albumPageOf(albumResponse: JsonObject): SongPage {
        val metadata = pageOf(albumResponse)
        val playlistId = InnertubeParser.parseAlbumPlaylistId(albumResponse) ?: return metadata
        val tracks = pageOf(Innertube.browse("VL${playlistId.removePrefix("VL")}"))
        return tracks.copy(
            library = metadata.library,
            header = metadata.header,
            description = metadata.description,
        )
    }

    suspend fun moreSongs(token: String): Result<SongPage> = call("browse:more") {
        pageOf(Innertube.browseContinuation(token))
    }

    suspend fun playlistOwned(browseId: String): Result<Boolean?> = call("owner:$browseId") {
        InnertubeParser.parsePlaylistOwned(Innertube.browse(browseId))
    }

    private fun pageOf(response: JsonObject): SongPage {
        val library = InnertubeParser.parseLibraryState(response)
        val header = InnertubeParser.parseBrowseHeader(response)
        InnertubeParser.parsePlaylistShelf(response)?.let { shelf ->
            return SongPage(shelf.songs, shelf.continuation, shelf.suggested, library, header = header)
        }
        return SongPage(
            songs = InnertubeParser.collectSongsDeep(response).distinctBy { it.videoId },
            continuation = InnertubeParser.continuationToken(response),
            library = library,
            header = header,
            description = InnertubeParser.parseDescription(response),
        )
    }

    suspend fun allSongs(browseId: String): Result<List<Song>> = call("all:$browseId") {
        songsPaged(browseId).ifEmpty { error("No tracks here") }
    }

    private suspend fun songsPaged(browseId: String): List<Song> {
        val out = LinkedHashMap<String, Song>()
        var response = Innertube.browse(browseId)
        if (browseId.startsWith("MPREb")) {
            InnertubeParser.parseAlbumPlaylistId(response)?.let { playlistId ->
                response = Innertube.browse("VL${playlistId.removePrefix("VL")}")
            }
        }
        var page = 1
        while (true) {
            val shelf = InnertubeParser.parsePlaylistShelf(response)
            (shelf?.songs ?: InnertubeParser.collectSongsDeep(response)).forEach { out[it.videoId] = it }
            val token = shelf?.continuation ?: InnertubeParser.continuationToken(response)
            if (token == null || page++ >= MAX_PAGES) break
            response = runCatching { Innertube.browseContinuation(token) }.getOrNull() ?: break
        }
        return out.values.toList()
    }

    private suspend fun itemsPaged(browseId: String, params: String? = null): List<ShelfItem> {
        val out = LinkedHashMap<String, ShelfItem>()
        var response = Innertube.browse(browseId, params)
        var page = 1
        while (true) {
            val parsed = InnertubeParser.parseLibraryItemPage(response)
            parsed.items.forEach { item ->
                val key = item.browseId ?: item.videoId ?: "${item.title}\n${item.subtitle}"
                out.putIfAbsent(key, item)
            }
            val token = parsed.continuation ?: break
            if (page++ >= MAX_PAGES) break
            response = runCatching { Innertube.browseContinuation(token) }.getOrNull() ?: break
        }
        return out.values.toList()
    }

    private suspend fun libraryItemsPaged(browseId: String): List<ShelfItem> = itemsPaged(browseId, null)

    const val MAX_PAGES = 10
    const val LIKED_MUSIC = "VLLM"
    private const val LIBRARY_SONGS = "FEmusic_liked_videos"
    private const val LIBRARY_PLAYLISTS = "FEmusic_liked_playlists"
    const val PLAYLISTS_SHELF = "Playlists"

    private val LIBRARY_FEEDS = listOf(
        PLAYLISTS_SHELF to LIBRARY_PLAYLISTS,
        "Albums" to "FEmusic_liked_albums",
        "Artists" to "FEmusic_library_corpus_artists",
        "Podcasts" to "FEmusic_library_non_music_audio_list",
    )

    // ---- Writes -------------------------------------------------------------

    suspend fun songMenu(videoId: String): Result<SongMenu> = call("menu:$videoId") {
        InnertubeParser.parseSongMenu(Innertube.next(videoId), videoId)
            ?: error("no menu for $videoId")
    }

    suspend fun rate(videoId: String, status: LikeStatus): Result<Unit> =
        call("rate:$videoId") { Innertube.rate(videoId, status) }

    suspend fun setLibraryStatus(token: String): Result<Unit> =
        call("library:feedback") { Innertube.sendFeedback(token) }

    suspend fun releaseLibraryState(browseId: String): Result<LibraryState?> =
        call("library-state:$browseId") { InnertubeParser.parseLibraryState(Innertube.browse(browseId)) }

    suspend fun setSaved(playlistId: String, saved: Boolean): Result<Unit> =
        call("library:$playlistId") { Innertube.ratePlaylist(playlistId, saved) }

    suspend fun setSubscribed(channelId: String, subscribed: Boolean): Result<Unit> =
        call("subscription:$channelId") { Innertube.setSubscribed(channelId, subscribed) }

    suspend fun userPlaylists(): Result<List<UserPlaylist>> = call("playlists") {
        InnertubeParser.parseUserPlaylists(libraryItemsPaged(LIBRARY_PLAYLISTS))
    }

    suspend fun libraryPlaylists(): Result<List<ShelfItem>> = call("libraryPlaylists") {
        InnertubeParser.parseLibraryItems(Innertube.browse(LIBRARY_PLAYLISTS))
    }

    suspend fun createPlaylist(
        title: String,
        privacy: PlaylistPrivacy,
        videoIds: List<String> = emptyList(),
    ): Result<String> = call("playlist:create") {
        Innertube.createPlaylist(title, privacy, videoIds = videoIds)
    }

    suspend fun addToPlaylist(
        playlistId: String,
        videoIds: List<String>,
    ): Result<Map<String, String>> =
        call("playlist:add") { Innertube.addToPlaylist(playlistId, videoIds) }

    suspend fun removeFromPlaylist(
        playlistId: String,
        entries: List<Pair<String, String>>,
    ): Result<Unit> = call("playlist:remove") {
        Innertube.removeFromPlaylist(playlistId, entries)
    }

    suspend fun playlistEntries(browseId: String): Result<List<Song>> = call("entries:$browseId") {
        val out = LinkedHashMap<String, Song>()
        var response = Innertube.browse(browseId)
        var page = 1
        while (true) {
            val shelf = InnertubeParser.parsePlaylistShelf(response) ?: break
            shelf.songs.forEach { song ->
                val setVideoId = song.setVideoId ?: error("playlist entry without an id")
                out.putIfAbsent(setVideoId, song)
            }
            val token = shelf.continuation ?: break
            if (page++ >= MAX_PAGES) error("playlist too long to reorder")
            response = Innertube.browseContinuation(token)
        }
        out.values.toList()
    }

    suspend fun reorderPlaylist(
        playlistId: String,
        current: List<String>,
        target: List<String>,
    ): Result<Unit> = call("playlist:reorder") {
        playlistMoves(current, target).chunked(MOVE_BATCH).forEach { batch ->
            Innertube.movePlaylistItems(playlistId, batch)
        }
    }

    private const val MOVE_BATCH = 50

    suspend fun renamePlaylist(playlistId: String, title: String): Result<Unit> =
        call("playlist:rename") { Innertube.renamePlaylist(playlistId, title) }

    suspend fun deletePlaylist(playlistId: String): Result<Unit> =
        call("playlist:delete") { Innertube.deletePlaylist(playlistId) }

    /**
     * Artist page with in-memory caching for instant subsequent returns.
     */
    suspend fun artistPage(browseId: String): Result<ArtistPage> {
        artistPageCache[browseId]?.let { return Result.success(it) }
        return call("artist:$browseId") {
            val page = InnertubeParser.parseArtistPage(Innertube.browse(browseId))
            coroutineScope {
                val fullSongsDeferred = async {
                    page.moreSongsBrowseId?.let { playlistId ->
                        runCatching { songsPaged(playlistId) }.getOrNull()
                    }
                }
                val shelvesDeferred = page.sections.map { shelf ->
                    async {
                        val moreBrowseId = shelf.moreBrowseId
                        if (moreBrowseId != null) {
                            val fullItems = runCatching {
                                itemsPaged(moreBrowseId, shelf.moreParams)
                            }.getOrNull()
                            if (!fullItems.isNullOrEmpty()) {
                                shelf.copy(items = fullItems)
                            } else {
                                shelf
                            }
                        } else {
                            shelf
                        }
                    }
                }
                val fullSongs = fullSongsDeferred.await()
                val fullShelves = shelvesDeferred.awaitAll()
                val resolvedSongs = if (!fullSongs.isNullOrEmpty()) fullSongs else page.songs
                page.copy(songs = resolvedSongs, sections = fullShelves)
            }
        }.also { result ->
            result.getOrNull()?.let { artistPageCache.putIfAbsent(browseId, it) }
        }
    }

    private suspend fun <T> call(label: String, block: suspend () -> T): Result<T> =
        withContext(Dispatchers.IO) {
            runCatching { block() }.recoverCatching { failure ->
                val rejected = failure.message?.contains("401") == true ||
                    failure.message?.contains("403") == true ||
                    failure.message?.contains("rejected", true) == true
                if (!rejected || Innertube.cookie == null) throw failure
                Log.w(TAG, "$label rejected; refreshing active session context once")
                Innertube.refreshSessionScope()
                block()
            }
                .onFailure { if (it is CancellationException) throw it }
                .onSuccess { Log.d(TAG, "$label ok") }
                .onFailure { Log.w(TAG, "$label failed: ${it.message}") }
        }
}
