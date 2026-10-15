from pathlib import Path
import xml.etree.ElementTree as ET


def edit(path, old, new):
    file = Path(path)
    text = file.read_text(encoding='utf-8')
    if old not in text:
        if new in text:
            return
        raise RuntimeError(f'Expected anchor missing: {path}: {old[:70]}')
    file.write_text(text.replace(old, new, 1), encoding='utf-8')

root = 'app/src/main/java/com/music/bitchord/'
edit(root+'auth/AuthStore.kt', 'import android.content.SharedPreferences', '''import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey''')
edit(root+'auth/AuthStore.kt', 'class AuthStore(context: Context) {\n    private val prefs:', '''class AuthStore(context: Context) {
    // Dedicated encrypted store: never degrades to unencrypted preferences.
    // If Keystore fails, the AI key is unavailable and the normal translator remains usable.
    private val aiKeyPrefs: SharedPreferences? = runCatching {
        EncryptedSharedPreferences.create(
            context, "sonium_ai_auth",
            MasterKey.Builder(context).setKeyScheme(MasterKey.KeyScheme.AES256_GCM).build(),
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
        )
    }.getOrNull()

    var aiLyricsApiKey: String?
        get() = runCatching { aiKeyPrefs?.getString("openai_api_key", null) }.getOrNull()
        set(value) {
            // commit reports failure; never silently fall back to plain storage.
            val stored = aiKeyPrefs?.edit()?.putString("openai_api_key", value?.trim()?.ifEmpty { null })?.commit()
            if (stored != true) throw IllegalStateException("Encrypted AI key storage unavailable")
        }

    private val prefs:''')
for resource in ['backup_rules.xml', 'data_extraction_rules.xml']:
    path = root.replace('java/com/music/bitchord/', 'res/xml/')+resource
    text = Path(path).read_text(encoding='utf-8')
    text = text.replace('<exclude domain="sharedpref" path="bitchord_auth.xml" />', '<exclude domain="sharedpref" path="bitchord_auth.xml" />\n        <exclude domain="sharedpref" path="sonium_ai_auth.xml" />')
    Path(path).write_text(text, encoding='utf-8')
    ET.parse(path)

settings = root+'data/settings/AppSettings.kt'
edit(settings, '    val translationLanguage = MutableStateFlow("")', '''    val translationLanguage = MutableStateFlow("")
    val aiLyricsEnabled = MutableStateFlow(false)
    // In-memory mirror only; never write a credential to bitchord_settings or its export.
    val aiLyricsApiKey = MutableStateFlow("")''')
edit(settings, '        translationLanguage.value = prefs.getString(KEY_TRANSLATION_LANGUAGE, "").orEmpty()', '''        translationLanguage.value = prefs.getString(KEY_TRANSLATION_LANGUAGE, "").orEmpty()
        aiLyricsEnabled.value = prefs.getBoolean("ai_lyrics_enabled", false)
        aiLyricsApiKey.value = authStore.aiLyricsApiKey.orEmpty()''')
edit(settings, '    fun setSyncedLyrics(value: Boolean) {', '''    fun setAiLyricsEnabled(value: Boolean) {
        aiLyricsEnabled.value = value
        prefs.edit().putBoolean("ai_lyrics_enabled", value).apply()
    }

    fun setAiLyricsApiKey(value: String) {
        // Persist first. If Keystore fails, leave the old key and setting unchanged.
        val normalized = value.trim()
        authStore.aiLyricsApiKey = normalized.ifEmpty { null }
        aiLyricsApiKey.value = normalized
    }

    fun setSyncedLyrics(value: Boolean) {''')

host = root+'ui/player/AndroidPlayerHost.kt'
edit(host, 'import com.music.bitchord.data.lyrics.LyricsTranslation', '''import com.music.bitchord.data.lyrics.LyricsTranslation
import com.music.bitchord.data.lyrics.AiLyricsTranslator
import com.music.bitchord.data.lyrics.translationLanguageName''')
edit(host, '    ): LyricsTranslationResult = when (val result = LyricsTranslation.translate(trackId, lines, targetLanguageTag)) {', '''    ): LyricsTranslationResult = when (val result = AiLyricsTranslator.translatePoetic(
        trackId, lines, targetLanguageTag,
        translationLanguageName(targetLanguageTag, Locale.forLanguageTag(targetLanguageTag)),
        apiKey = AppSettings.aiLyricsApiKey.value,
        aiLyricsEnabled = AppSettings.aiLyricsEnabled.value,
    )) {''')
app = root+'BitChordApplication.kt'
edit(app, 'import com.music.bitchord.data.lyrics.LyricsTranslation', '''import com.music.bitchord.data.lyrics.LyricsTranslation
import com.music.bitchord.data.lyrics.AiLyricsTranslator''')
edit(app, '        LyricsTranslation.cacheDir = cacheDir', '''        LyricsTranslation.cacheDir = cacheDir
        AiLyricsTranslator.cacheDir = cacheDir''')

translator = 'shared/src/jvmSharedMain/kotlin/com/music/bitchord/data/lyrics/AiLyricsTranslator.kt'
edit(translator, '''        // 1. Verificar cache em memória ou disco''', '''        // The off switch must bypass AI output, including previously cached AI output.
        if (key.isBlank() || !aiLyricsEnabled) {
            return LyricsTranslation.translate(trackId, lines, targetLanguageTag)
        }

        // 1. Verificar cache em memória ou disco''')
edit(translator, '''        // Se chave de API não foi configurada ou IA não habilitada, delega para tradução tradicional
        if (key.isBlank() || !aiLyricsEnabled) {
            return LyricsTranslation.translate(trackId, lines, targetLanguageTag)
        }

        // 2. Chamada à API de IA''', '''        // 2. Chamada à API de IA''')

ui = root+'ui/screens/SettingsSheet.kt'
edit(ui, 'import androidx.compose.ui.text.LinkAnnotation', '''import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.LinkAnnotation''')
edit(ui, '    val translationLanguage by AppSettings.translationLanguage.collectAsStateWithLifecycle()', '''    val translationLanguage by AppSettings.translationLanguage.collectAsStateWithLifecycle()
    val aiLyricsEnabled by AppSettings.aiLyricsEnabled.collectAsStateWithLifecycle()
    val aiLyricsApiKey by AppSettings.aiLyricsApiKey.collectAsStateWithLifecycle()
    var editingAiKey by remember { mutableStateOf(false) }
    var aiKeyError by remember { mutableStateOf(false) }''')
edit(ui, '''                val translationLanguageTitle = stringResource(R.string.translation_language)''', '''                val aiTitle = stringResource(R.string.ai_lyrics_translation)
                row(aiTitle, "lyrics", "AI", "translate") {
                    SettingsRow(
                        icon = Icons.Rounded.AutoAwesome,
                        title = aiTitle,
                        subtitle = stringResource(R.string.ai_lyrics_translation_subtitle),
                        trailing = {
                            Switch(checked = aiLyricsEnabled,
                                onCheckedChange = AppSettings::setAiLyricsEnabled)
                        },
                        onClick = { AppSettings.setAiLyricsEnabled(!aiLyricsEnabled) },
                    )
                }
                val keyTitle = stringResource(R.string.ai_lyrics_api_key)
                row(keyTitle, "AI", "OpenAI", "lyrics") {
                    SettingsRow(
                        icon = Icons.Rounded.Tune,
                        title = keyTitle,
                        subtitle = if (aiLyricsApiKey.isBlank())
                            stringResource(R.string.ai_lyrics_api_key_hint) else "••••••••",
                        onClick = { editingAiKey = true },
                    )
                }
                val translationLanguageTitle = stringResource(R.string.translation_language)''')
edit(ui, '    if (showListenBrainzTokenDialog) {', '''    if (editingAiKey) {
        var keyInput by remember { mutableStateOf("") }
        AlertDialog(
            onDismissRequest = { editingAiKey = false },
            title = { Text(stringResource(R.string.ai_lyrics_api_key)) },
            text = {
                Column {
                    OutlinedTextField(
                        value = keyInput,
                        onValueChange = { keyInput = it; aiKeyError = false },
                        singleLine = true,
                        visualTransformation = PasswordVisualTransformation(),
                        label = { Text(stringResource(R.string.ai_lyrics_api_key_hint)) },
                    )
                    if (aiKeyError) Text("Encrypted storage unavailable", color = MaterialTheme.colorScheme.error)
                }
            },
            confirmButton = {
                TextButton(onClick = {
                    try {
                        AppSettings.setAiLyricsApiKey(keyInput)
                        editingAiKey = false
                        keyInput = ""
                    } catch (_: IllegalStateException) { aiKeyError = true }
                }) { Text(stringResource(R.string.save)) }
            },
            dismissButton = {
                TextButton(onClick = { editingAiKey = false; keyInput = "" }) {
                    Text(stringResource(R.string.cancel))
                }
            },
        )
    }

    if (showListenBrainzTokenDialog) {''')
print('AI lyrics patch applied: secure key, settings UI, player, cache and fallback')