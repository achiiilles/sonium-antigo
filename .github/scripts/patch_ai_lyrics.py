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


def add_strings(path, entries):
    file = Path(path)
    if not file.exists():
        return
    text = file.read_text(encoding='utf-8')
    to_add = []
    for name, val in entries.items():
        if f'name="{name}"' not in text:
            to_add.append(f'    <string name="{name}">{val}</string>')
    if to_add:
        text = text.replace('</resources>', '\n'.join(to_add) + '\n</resources>')
        file.write_text(text, encoding='utf-8')
        ET.parse(path)


root = 'app/src/main/java/com/music/bitchord/'

# 1. AuthStore: Encrypted SharedPreferences dedicated to Gemini key without fallback
edit(root+'auth/AuthStore.kt', 'import android.content.SharedPreferences', '''import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey''')

edit(root+'auth/AuthStore.kt', '    private val prefs: SharedPreferences =', '''    // Dedicated encrypted store: never degrades to unencrypted preferences.
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
            val stored = aiKeyPrefs?.edit()?.putString("openai_api_key", value?.trim()?.ifEmpty { null })?.commit()
            if (stored != true) throw IllegalStateException("Encrypted AI key storage unavailable")
        }

    private val prefs: SharedPreferences =''')

# 2. Exclude sonium_ai_auth.xml from backups
for resource in ['backup_rules.xml', 'data_extraction_rules.xml']:
    path = root.replace('java/com/music/bitchord/', 'res/xml/') + resource
    if Path(path).exists():
        text = Path(path).read_text(encoding='utf-8')
        if 'sonium_ai_auth.xml' not in text:
            text = text.replace('path="bitchord_auth.xml" />', 'path="bitchord_auth.xml" />\n        <exclude domain="sharedpref" path="sonium_ai_auth.xml" />')
            Path(path).write_text(text, encoding='utf-8')
            ET.parse(path)

# 3. Add strings to resource files
add_strings('app/src/main/res/values/strings.xml', {
    'ai_lyrics_translation': 'AI lyric translation',
    'ai_lyrics_translation_subtitle': 'Poetic, rhythmic translation in the active language',
    'ai_lyrics_api_key': 'Google AI Studio (Gemini) API key',
    'ai_lyrics_api_key_hint': 'AIza…',
    'spatial_audio_bluetooth_only': 'Enable only with Bluetooth headphones',
    'spatial_audio_bluetooth_only_subtitle': 'Automatically enables spatial audio when connected to Bluetooth headphones and disables on speaker',
})
add_strings('app/src/main/res/values-pt-rBR/strings.xml', {
    'ai_lyrics_translation': 'Tradução de letras por IA',
    'ai_lyrics_translation_subtitle': 'Tradução poética e rítmica no idioma ativo',
    'ai_lyrics_api_key': 'Chave Google AI Studio (Gemini)',
    'ai_lyrics_api_key_hint': 'AIza…',
    'spatial_audio_bluetooth_only': 'Ativar apenas com fones Bluetooth',
    'spatial_audio_bluetooth_only_subtitle': 'Liga o áudio espacial automaticamente ao conectar fones sem fio e desativa ao desconectar',
})
add_strings('app/src/main/res/values-pt/strings.xml', {
    'ai_lyrics_translation': 'Tradução de letras por IA',
    'ai_lyrics_translation_subtitle': 'Tradução poética e rítmica no idioma ativo',
    'ai_lyrics_api_key': 'Chave Google AI Studio (Gemini)',
    'ai_lyrics_api_key_hint': 'AIza…',
    'spatial_audio_bluetooth_only': 'Ativar apenas com fones Bluetooth',
    'spatial_audio_bluetooth_only_subtitle': 'Liga o áudio espacial automaticamente ao conectar fones sem fio e desativa ao desconectar',
})

# 4. AppSettings
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
        val normalized = value.trim()
        authStore.aiLyricsApiKey = normalized.ifEmpty { null }
        aiLyricsApiKey.value = normalized
    }

    fun setSyncedLyrics(value: Boolean) {''')

# 5. AndroidPlayerHost
host = root+'ui/player/AndroidPlayerHost.kt'
edit(host, 'import com.music.bitchord.data.lyrics.LyricsTranslation', '''import com.music.bitchord.data.lyrics.LyricsTranslation
import com.music.bitchord.data.lyrics.AiLyricsTranslator
import com.music.bitchord.data.lyrics.translationLanguageName''')

edit(host, '        when (val result = LyricsTranslation.translate(trackId, lines, targetLanguageTag)) {', '''        when (val result = AiLyricsTranslator.translatePoetic(
            trackId, lines, targetLanguageTag,
            translationLanguageName(targetLanguageTag, Locale.forLanguageTag(targetLanguageTag)),
            apiKey = AppSettings.aiLyricsApiKey.value,
            aiLyricsEnabled = AppSettings.aiLyricsEnabled.value,
        )) {''')

# 6. BitChordApplication
app = root+'BitChordApplication.kt'
edit(app, 'import com.music.bitchord.data.lyrics.LyricsTranslation', '''import com.music.bitchord.data.lyrics.LyricsTranslation
import com.music.bitchord.data.lyrics.AiLyricsTranslator''')

edit(app, '        LyricsTranslation.cacheDir = cacheDir', '''        LyricsTranslation.cacheDir = cacheDir
        AiLyricsTranslator.cacheDir = cacheDir''')

# 7. AiLyricsTranslator: Já migrado diretamente no repositório para o Gemini 1.5 Flash.

# 8. SettingsSheet - Tradução por IA
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
                            Switch(
                                checked = aiLyricsEnabled,
                                onCheckedChange = AppSettings::setAiLyricsEnabled,
                            )
                        },
                        onClick = { AppSettings.setAiLyricsEnabled(!aiLyricsEnabled) },
                    )
                }
                val keyTitle = stringResource(R.string.ai_lyrics_api_key)
                row(keyTitle, "AI", "Gemini", "Google", "lyrics") {
                    SettingsRow(
                        icon = Icons.Rounded.Tune,
                        title = keyTitle,
                        subtitle = if (aiLyricsApiKey.isBlank()) stringResource(R.string.ai_lyrics_api_key_hint) else "••••••••",
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
                    } catch (e: IllegalStateException) { aiKeyError = true }
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

# 9. SettingsSheet - Switch de Áudio Espacial Bluetooth
edit(ui, 'import com.music.bitchord.playback.AudioCache', '''import com.music.bitchord.playback.AudioCache
import com.music.bitchord.playback.audio.bluetooth.BluetoothRouteMonitor''')

edit(ui, '    val spatialAudio by AppSettings.spatialAudio.collectAsStateWithLifecycle()', '''    val spatialAudio by AppSettings.spatialAudio.collectAsStateWithLifecycle()
    LaunchedEffect(Unit) {
        BluetoothRouteMonitor.init(context.applicationContext)
    }
    val spatialAudioAutoBluetooth by BluetoothRouteMonitor.autoBluetoothFlow.collectAsStateWithLifecycle()''')

edit(ui, '''            val spatialAudioTitle = stringResource(R.string.spatial_audio)
            row(spatialAudioTitle, "surround", "3d") {
                SettingsRow(
                    icon = Icons.Rounded.SurroundSound,
                    title = spatialAudioTitle,
                    // Widening a JOC stream would fight the object-based mix
                    // Dolby has already spatialized, so the service holds this
                    // off for the duration of an Atmos track — see
                    // `PlaybackService.applySpatialAudioEnabled`. Said on the
                    // row because the switch stays where the listener left it,
                    // and a switch reading "on" over an effect that is not
                    // running is the same silent lie the equaliser screen used
                    // to tell.
                    subtitle = if (playingDolbyAtmos) {
                        stringResource(R.string.spatial_audio_atmos_subtitle)
                    } else {
                        stringResource(R.string.spatial_audio_subtitle)
                    },
                    trailing = {
                        Switch(
                            checked = spatialAudio,
                            onCheckedChange = AppSettings::setSpatialAudio,
                            colors = SwitchDefaults.colors(
                                checkedTrackColor = MaterialTheme.colorScheme.primary,
                                checkedBorderColor = MaterialTheme.colorScheme.primary,
                            ),
                        )
                    },
                    onClick = { AppSettings.setSpatialAudio(!spatialAudio) },
                )
            }''', '''            val spatialAudioTitle = stringResource(R.string.spatial_audio)
            row(spatialAudioTitle, "surround", "3d") {
                SettingsRow(
                    icon = Icons.Rounded.SurroundSound,
                    title = spatialAudioTitle,
                    // Widening a JOC stream would fight the object-based mix
                    // Dolby has already spatialized, so the service holds this
                    // off for the duration of an Atmos track — see
                    // `PlaybackService.applySpatialAudioEnabled`. Said on the
                    // row because the switch stays where the listener left it,
                    // and a switch reading "on" over an effect that is not
                    // running is the same silent lie the equaliser screen used
                    // to tell.
                    subtitle = if (playingDolbyAtmos) {
                        stringResource(R.string.spatial_audio_atmos_subtitle)
                    } else {
                        stringResource(R.string.spatial_audio_subtitle)
                    },
                    trailing = {
                        Switch(
                            checked = spatialAudio,
                            onCheckedChange = AppSettings::setSpatialAudio,
                            colors = SwitchDefaults.colors(
                                checkedTrackColor = MaterialTheme.colorScheme.primary,
                                checkedBorderColor = MaterialTheme.colorScheme.primary,
                            ),
                        )
                    },
                    onClick = { AppSettings.setSpatialAudio(!spatialAudio) },
                )
            }
            val spatialAudioBluetoothTitle = stringResource(R.string.spatial_audio_bluetooth_only)
            row(spatialAudioBluetoothTitle, "bluetooth", "surround", "3d", "headphones", divided = false) {
                SettingsSubRow(
                    title = spatialAudioBluetoothTitle,
                    subtitle = stringResource(R.string.spatial_audio_bluetooth_only_subtitle),
                    checked = spatialAudioAutoBluetooth,
                    onCheckedChange = { BluetoothRouteMonitor.setAutoBluetoothEnabled(context.applicationContext, it) },
                )
            }''')

print('AI lyrics & Bluetooth Spatial Audio patch applied: Gemini 1.5 Flash key, settings UI, Bluetooth switch, cache and fallback')
