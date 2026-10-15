import re
from pathlib import Path

print("Applying iOS Inset Grouped Settings patch...")

settings_path = Path("app/src/main/java/com/music/bitchord/ui/screens/SettingsSheet.kt")
code = settings_path.read_text(encoding="utf-8")

# 1. Update GroupShape and styling for iOS Inset Grouped
# rounded corners 18.dp, background translúcido sobre preto puro
code = code.replace(
    "internal val GroupShape = RoundedCornerShape(14.dp)",
    "internal val GroupShape = RoundedCornerShape(18.dp)"
)

# In SettingsGroup, update background to subtle translucent card on pure black:
old_group_col = '''        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = GROUP_INSET)
                .clip(GroupShape)
                .background(MaterialTheme.colorScheme.surfaceVariant),
        ) {'''

new_group_col = '''        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = GROUP_INSET)
                .clip(GroupShape)
                .background(Color(0xFF1C1C1E).copy(alpha = 0.95f)),
        ) {'''

if old_group_col in code:
    code = code.replace(old_group_col, new_group_col)

# 2. Add required imports if missing
required_imports = [
    "import androidx.compose.ui.text.input.PasswordVisualTransformation",
    "import com.music.bitchord.playback.audio.bluetooth.BluetoothRouteMonitor",
]
for imp in required_imports:
    if imp not in code:
        code = code.replace("package com.music.bitchord.ui.screens", f"package com.music.bitchord.ui.screens\n{imp}")

# 3. Add AI lyrics and Bluetooth state collectors if missing
if "val aiLyricsEnabled" not in code:
    anchor_trans = "val translationLanguage by AppSettings.translationLanguage.collectAsStateWithLifecycle()"
    replacement_trans = '''val translationLanguage by AppSettings.translationLanguage.collectAsStateWithLifecycle()
    val aiLyricsEnabled by AppSettings.aiLyricsEnabled.collectAsStateWithLifecycle()
    val aiLyricsApiKey by AppSettings.aiLyricsApiKey.collectAsStateWithLifecycle()
    var editingAiKey by remember { mutableStateOf(false) }
    var aiKeyError by remember { mutableStateOf(false) }'''
    code = code.replace(anchor_trans, replacement_trans, 1)

if "BluetoothRouteMonitor.init" not in code:
    anchor_spatial = "val spatialAudio by AppSettings.spatialAudio.collectAsStateWithLifecycle()"
    replacement_spatial = '''val spatialAudio by AppSettings.spatialAudio.collectAsStateWithLifecycle()
    LaunchedEffect(Unit) {
        BluetoothRouteMonitor.init(context.applicationContext)
    }
    val spatialAudioAutoBluetooth by BluetoothRouteMonitor.autoBluetoothFlow.collectAsStateWithLifecycle()'''
    code = code.replace(anchor_spatial, replacement_spatial, 1)

if "if (editingAiKey) {" not in code:
    anchor_dialog = "if (showListenBrainzTokenDialog) {"
    replacement_dialog = '''if (editingAiKey) {
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
    if (showListenBrainzTokenDialog) {'''
    code = code.replace(anchor_dialog, replacement_dialog, 1)

# 4. Restructure sections into the 5 iOS Grouped Cards:
# 1) "Reprodução & Áudio" (includes playback, audio quality, spatial audio + Bluetooth auto)
# 2) "Letras" (synced lyrics, translation, AI translation toggle, Gemini key)
# 3) "Conteúdo & Biblioteca" (account, listen together, downloads, local music, replay/data)
# 4) "Aparência" (theme, reduce animation/blur, liquid glass, full screen artwork, cover art, app language)
# 5) "Sobre" (version, credits, links, licenses)

# Update section headers:
code = code.replace('header = stringResource(R.string.audio_quality)', 'header = "Reprodução & Áudio"')
code = code.replace('header = stringResource(R.string.playback)', 'header = "Opções de Reprodução"')
code = code.replace('header = stringResource(R.string.downloads)', 'header = "Conteúdo & Biblioteca"')
code = code.replace('header = stringResource(R.string.appearance)', 'header = "Aparência"')

# Add Bluetooth switch inside spatial audio if not present:
if "spatialAudioBluetoothTitle" not in code:
    old_spatial_block = '''            val spatialAudioTitle = stringResource(R.string.spatial_audio)
            row(spatialAudioTitle, "surround", "3d") {
                SettingsRow(
                    icon = Icons.Rounded.SurroundSound,
                    title = spatialAudioTitle,
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
            }'''

    new_spatial_block = '''            val spatialAudioTitle = stringResource(R.string.spatial_audio)
            row(spatialAudioTitle, "surround", "3d") {
                SettingsRow(
                    icon = Icons.Rounded.SurroundSound,
                    title = spatialAudioTitle,
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
            }'''
    code = code.replace(old_spatial_block, new_spatial_block, 1)

# Ensure "Letras" has its own dedicated card
if 'header = "Letras"' not in code:
    lyrics_card = '''        SearchableSettingsGroup(search, header = "Letras") {
            val syncedLyricsTitle = stringResource(R.string.synced_lyrics)
            row(syncedLyricsTitle, "lyrics", "translation", "lrclib", "musixmatch") {
                SettingsRow(
                    icon = Icons.AutoMirrored.Rounded.Notes,
                    title = syncedLyricsTitle,
                    subtitle = stringResource(R.string.synced_lyrics_subtitle),
                    trailing = {
                        Switch(
                            checked = syncedLyrics,
                            onCheckedChange = AppSettings::setSyncedLyrics,
                            colors = SwitchDefaults.colors(
                                checkedTrackColor = MaterialTheme.colorScheme.primary,
                                checkedBorderColor = MaterialTheme.colorScheme.primary,
                            ),
                        )
                    },
                    onClick = { AppSettings.setSyncedLyrics(!syncedLyrics) },
                )
            }
            val aiTitle = stringResource(R.string.ai_lyrics_translation)
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
            val translationLanguageTitle = stringResource(R.string.translation_language)
            row(translationLanguageTitle, "lyrics", "translate") {
                SettingsRow(
                    icon = Icons.Rounded.Translate,
                    title = translationLanguageTitle,
                    subtitle = if (translationLanguage.isBlank()) {
                        stringResource(R.string.translation_language_subtitle)
                    } else {
                        translationLanguageName(
                            translationLanguage,
                            AppCompatDelegate.getApplicationLocales().get(0) ?: Locale.getDefault(),
                        )
                    },
                    trailing = { Chevron() },
                    onClick = onTranslationLanguage,
                )
            }
            val lyricsSourcesTitle = stringResource(R.string.lyrics_sources)
            row(lyricsSourcesTitle, "lyrics", "lrclib", "musixmatch") {
                SettingsRow(
                    icon = Icons.Rounded.Language,
                    title = lyricsSourcesTitle,
                    subtitle = lyricsSources
                        .sortedBy { it.ordinal }
                        .joinToString(", ") { it.label }
                        .ifEmpty { stringResource(R.string.no_lyrics_sources_enabled) },
                    trailing = { Chevron() },
                    onClick = onLyricsSources,
                )
            }
        }
'''
    # Insert "Letras" right before "Aparência"
    code = code.replace('SearchableSettingsGroup(search, header = "Aparência")', lyrics_card + '        SearchableSettingsGroup(search, header = "Aparência")')

# Add "Sobre" section card wrapping the version and links if not present
if 'header = "Sobre"' not in code:
    about_card = '''        SearchableSettingsGroup(search, header = "Sobre") {
            row("versão", "sobre", "sonium", "créditos") {
                SettingsRow(
                    icon = Icons.Rounded.BarChart,
                    title = "Sonium $version",
                    subtitle = "Repositório achiilles75/Sonium · Base BitChord",
                )
            }
        }
'''
    code = code.replace('SearchableSettingsGroup(search, header = stringResource(R.string.language))', about_card + '        SearchableSettingsGroup(search, header = stringResource(R.string.language))')

settings_path.write_text(code, encoding="utf-8")
print("SettingsSheet.kt successfully updated to 5 Inset Grouped iOS cards!")
