package com.music.bitchord.data.lyrics

import com.music.bitchord.data.Http
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import kotlinx.serialization.Serializable
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.File
import java.io.FileInputStream
import java.io.FileOutputStream
import java.security.MessageDigest
import java.util.Locale
import java.util.zip.GZIPInputStream
import java.util.zip.GZIPOutputStream

/**
 * Tradutor de letras inteligente por IA com prompt poético dinâmico.
 * Adapta rimas, métrica lírica e vocabulário para o idioma ativo do app,
 * preservando a quantidade estrita de linhas e armazenando traduções em cache local.
 * Utiliza o endpoint oficial da API do Gemini 1.5 Flash (Google AI Studio).
 */
object AiLyricsTranslator {

    private const val CACHE_DIR_NAME = "sonium_ai_lyrics_v1"
    private const val MAX_CACHE_BYTES = 5L * 1024L * 1024L // 5MB
    private val json = Json { ignoreUnknownKeys = true }
    private val diskMutex = Mutex()

    @Volatile
    var cacheDir: File? = null

    private val memoryCache = object {
        private val entries = object : LinkedHashMap<String, CachedAiTranslation>(16, 0.75f, true) {
            override fun removeEldestEntry(eldest: Map.Entry<String, CachedAiTranslation>) = size > 20
        }

        @Synchronized
        fun get(key: String): CachedAiTranslation? = entries[key]

        @Synchronized
        fun put(key: String, value: CachedAiTranslation) {
            entries[key] = value
        }
    }

    @Serializable
    data class CachedAiTranslation(
        val targetLanguage: String,
        val lines: List<String>,
    )

    fun buildPoeticPrompt(targetLanguageName: String, originalText: String, lineCount: Int): String {
        return """Traduza e adapte a letra para $targetLanguageName, preservando o ritmo lírico, rimas e expressões naturais de falantes nativos de $targetLanguageName. Devolva estritamente a mesma quantidade de linhas ($lineCount linhas), linha por linha, sem numeração, sem comentários ou explicações adicionais:

$originalText"""
    }

    /**
     * Traduz uma lista de linhas de letra de forma poética.
     */
    suspend fun translatePoetic(
        trackId: String,
        lines: List<LyricLine>,
        targetLanguageTag: String,
        targetLanguageDisplayName: String,
        apiKey: String = "",
        aiLyricsEnabled: Boolean = true,
    ): LyricsTranslation.Result {
        if (lines.isEmpty()) return LyricsTranslation.Result.Unavailable

        val key = apiKey.trim()

        // Se chave de API não foi configurada ou IA não habilitada, delega para tradução tradicional
        if (key.isBlank() || !aiLyricsEnabled) {
            return LyricsTranslation.translate(trackId, lines, targetLanguageTag)
        }

        val plainLines = lines.map { it.text }
        val lineCount = plainLines.size
        val cacheKey = hashKey(trackId, targetLanguageTag, plainLines)

        // 1. Verificar cache em memória ou disco
        val cached = memoryCache.get(cacheKey) ?: readCache(cacheKey)?.also {
            memoryCache.put(cacheKey, it)
        }
        if (cached != null && cached.lines.size == lines.size) {
            val rebuilt = lines.mapIndexed { idx, lyricLine ->
                lyricLine.copy(text = cached.lines[idx])
            }
            return LyricsTranslation.Result.Translated(
                lines = rebuilt,
                sourceLanguage = "auto",
                fromCache = true,
            )
        }

        // 2. Chamada à API de IA (Google AI Studio - Gemini 1.5 Flash)
        val originalBody = plainLines.joinToString("\n")
        val prompt = buildPoeticPrompt(targetLanguageDisplayName, originalBody, lineCount)

        val translatedLines = withContext(Dispatchers.IO) {
            callAiCompletion(prompt, key)
        }

        if (translatedLines == null || translatedLines.size != lines.size) {
            // Fallback transparente para o tradutor nativo em caso de divergência de linhas
            return LyricsTranslation.translate(trackId, lines, targetLanguageTag)
        }

        val entry = CachedAiTranslation(
            targetLanguage = targetLanguageTag,
            lines = translatedLines,
        )
        memoryCache.put(cacheKey, entry)
        writeCache(cacheKey, entry)

        val rebuilt = lines.mapIndexed { idx, lyricLine ->
            lyricLine.copy(text = translatedLines[idx])
        }
        return LyricsTranslation.Result.Translated(
            lines = rebuilt,
            sourceLanguage = "auto",
            fromCache = false,
        )
    }

    private fun callAiCompletion(prompt: String, apiKey: String): List<String>? {
        return try {
            val url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=$apiKey"
            val combinedPrompt = "Você é um poeta e letrista musical de renome internacional especializado em versões e traduções de letras musicais.\n\n$prompt"
            val reqPayload = """{
  "contents": [
    {
      "parts": [
        {
          "text": ${json.encodeToString(combinedPrompt)}
        }
      ]
    }
  ],
  "generationConfig": {
    "temperature": 0.4
  }
}"""
            val body = reqPayload.toRequestBody("application/json".toMediaType())
            val request = Request.Builder()
                .url(url)
                .header("Content-Type", "application/json")
                .post(body)
                .build()

            val response = Http.client.newCall(request).execute()
            val respStr = response.body?.string() ?: return null
            if (!response.isSuccessful) return null

            val parsed = json.parseToJsonElement(respStr).jsonObject
            val content = parsed["candidates"]?.jsonArray?.getOrNull(0)?.jsonObject
                ?.get("content")?.jsonObject
                ?.get("parts")?.jsonArray?.getOrNull(0)?.jsonObject
                ?.get("text")?.jsonPrimitive?.content ?: return null

            val lines = content.lines().map { it.trim() }.filter { it.isNotEmpty() }
            lines
        } catch (_: Exception) {
            null
        }
    }

    private fun hashKey(trackId: String, target: String, lines: List<String>): String {
        val src = buildString {
            append(trackId).append('\u0000').append(target)
            lines.forEach { append('\u0000').append(it) }
        }
        return MessageDigest.getInstance("SHA-256")
            .digest(src.toByteArray(Charsets.UTF_8))
            .joinToString("") { "%02x".format(it) }
    }

    private suspend fun readCache(key: String): CachedAiTranslation? = withContext(Dispatchers.IO) {
        diskMutex.withLock {
            val root = cacheDir ?: return@withLock null
            val file = File(File(root, CACHE_DIR_NAME), "$key.json.gz")
            if (!file.isFile) return@withLock null
            runCatching {
                val value = GZIPInputStream(FileInputStream(file)).bufferedReader().use {
                    json.decodeFromString<CachedAiTranslation>(it.readText())
                }
                file.setLastModified(System.currentTimeMillis())
                value
            }.getOrNull()
        }
    }

    private suspend fun writeCache(key: String, value: CachedAiTranslation) = withContext(Dispatchers.IO) {
        diskMutex.withLock {
            val root = cacheDir ?: return@withLock
            val dir = File(root, CACHE_DIR_NAME)
            if (!dir.exists() && !dir.mkdirs()) return@withLock
            val dest = File(dir, "$key.json.gz")
            val tmp = File(dir, "$key.tmp")
            runCatching {
                GZIPOutputStream(FileOutputStream(tmp)).bufferedWriter().use {
                    it.write(json.encodeToString(value))
                }
                if (!tmp.renameTo(dest)) {
                    tmp.copyTo(dest, overwrite = true)
                    tmp.delete()
                }
                trimCache(dir)
            }.onFailure { tmp.delete() }
        }
    }

    private fun trimCache(dir: File) {
        val files = dir.listFiles { file -> file.extension == "gz" }
            ?.sortedByDescending { it.lastModified() }
            .orEmpty()
        var kept = 0L
        files.forEach { file ->
            kept += file.length()
            if (kept > MAX_CACHE_BYTES) file.delete()
        }
    }
}
