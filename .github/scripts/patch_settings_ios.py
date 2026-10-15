import re
from pathlib import Path

print("Applying Sonium iOS Pill & Subpages Settings patch...")

settings_path = Path("app/src/main/java/com/music/bitchord/ui/screens/SettingsSheet.kt")
if not settings_path.exists():
    raise FileNotFoundError("SettingsSheet.kt não encontrado")

code = settings_path.read_text(encoding="utf-8")

# 1. Atualizar GroupShape para cantos arredondados de pílula (20.dp) e fundo translúcido iOS
code = re.sub(
    r'internal val GroupShape = RoundedCornerShape\(\d+\.dp\)',
    'internal val GroupShape = RoundedCornerShape(20.dp)\ninternal val PillShape = RoundedCornerShape(20.dp)',
    code
)

# Fundo translúcido sutil sobre preto puro nas pílulas e grupos
old_group_bg = 'MaterialTheme.colorScheme.surfaceVariant'
new_group_bg = 'Color(0xFF1C1C1E).copy(alpha = 0.95f)'

# Atualiza background do SettingsGroup
if 'Column(\n        modifier = Modifier\n            .fillMaxWidth()\n            .padding(horizontal = GROUP_INSET)\n            .clip(GroupShape)\n            .background(MaterialTheme.colorScheme.surfaceVariant)' in code:
    code = code.replace(
        'Column(\n        modifier = Modifier\n            .fillMaxWidth()\n            .padding(horizontal = GROUP_INSET)\n            .clip(GroupShape)\n            .background(MaterialTheme.colorScheme.surfaceVariant)',
        'Column(\n        modifier = Modifier\n            .fillMaxWidth()\n            .padding(horizontal = GROUP_INSET)\n            .clip(GroupShape)\n            .background(Color(0xFF1C1C1E).copy(alpha = 0.95f))'
    )
elif '.background(MaterialTheme.colorScheme.surfaceVariant)' in code:
    code = code.replace('.background(MaterialTheme.colorScheme.surfaceVariant)', '.background(Color(0xFF1C1C1E).copy(alpha = 0.95f))')

# 2. Injetar imports necessários se ausentes
needed_imports = [
    "import androidx.activity.compose.BackHandler",
    "import androidx.compose.material.icons.automirrored.rounded.ArrowBack",
    "import androidx.compose.ui.text.input.PasswordVisualTransformation",
    "import com.music.bitchord.playback.audio.bluetooth.BluetoothRouteMonitor",
    "import com.music.bitchord.data.lyrics.translationLanguageName",
]
for imp in needed_imports:
    if imp not in code:
        code = code.replace("package com.music.bitchord.ui.screens", f"package com.music.bitchord.ui.screens\n{imp}")

# 3. Injetar enum SettingsCategory e componente SettingsPillCard se ausentes
if "enum class SettingsCategory" not in code:
    category_enum_and_pill = '''
/**
 * Categorias principais de configurações do Sonium para navegação em subpáginas.
 */
enum class SettingsCategory(
    val title: String,
    val subtitle: String,
    val icon: ImageVector,
) {
    ACCOUNT("Conta & Conexões", "Contas, Last.fm, Listen Together e sessões", Icons.Rounded.Person),
    PLAYBACK("Reprodução & Áudio", "Qualidade, áudio espacial, equalizador e saída", Icons.Rounded.GraphicEq),
    LYRICS("Letras", "Letras sincronizadas, tradução poética e fontes", Icons.AutoMirrored.Rounded.Notes),
    APPEARANCE("Aparência & Interface", "Tema, efeito de vidro, capas e animações", Icons.Rounded.AutoAwesome),
    LIBRARY("Biblioteca & Armazenamento", "Downloads, pastas locais, cache e limpeza", Icons.Rounded.Storage),
    SYSTEM("Geral & Sistema", "Idioma, backup, desempenho e sobre o app", Icons.Rounded.Tune);
}

/**
 * Card individual flutuante em formato de pílula (estilo iOS / cápsula com RoundedCornerShape 20.dp).
 */
@Composable
internal fun SettingsPillCard(
    icon: ImageVector,
    title: String,
    subtitle: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Row(
        modifier = modifier
            .fillMaxWidth()
            .padding(horizontal = GROUP_INSET, vertical = 5.dp)
            .clip(PillShape)
            .background(Color(0xFF1C1C1E).copy(alpha = 0.95f))
            .clickable(onClick = onClick)
            .padding(horizontal = ROW_INSET, vertical = 14.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(
            imageVector = icon,
            contentDescription = null,
            tint = MaterialTheme.colorScheme.primary,
            modifier = Modifier.size(ICON_SIZE),
        )
        Spacer(Modifier.width(ICON_GAP))
        Column(Modifier.weight(1f)) {
            Text(
                text = title,
                style = MaterialTheme.typography.titleMedium,
                color = MaterialTheme.colorScheme.onBackground,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Spacer(Modifier.height(2.dp))
            Text(
                text = subtitle,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
        }
        Spacer(Modifier.width(8.dp))
        Chevron()
    }
}
'''
    code = code.replace("// ---- Building blocks", category_enum_and_pill + "\n// ---- Building blocks")

# 4. Injetar estados de Bluetooth e AI Lyrics se ausentes
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

# Diálogo de configuração da chave Gemini
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

# Injetar estado de navegação de subpáginas
if "var selectedCategory by rememberSaveable" not in code:
    anchor_state = "var searchQuery by remember { mutableStateOf(\"\") }"
    replacement_state = '''var searchQuery by remember { mutableStateOf("") }
    var selectedCategory by rememberSaveable { mutableStateOf<SettingsCategory?>(null) }
    if (selectedCategory != null) {
        BackHandler { selectedCategory = null }
    }'''
    code = code.replace(anchor_state, replacement_state, 1)

# 5. Adicionar chave Bluetooth auto no grupo de Áudio Espacial se ausente
if "spatialAudioBluetoothTitle" not in code:
    old_spatial = '''            val spatialAudioTitle = stringResource(R.string.spatial_audio)
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
    new_spatial = '''            val spatialAudioTitle = stringResource(R.string.spatial_audio)
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
    if old_spatial in code:
        code = code.replace(old_spatial, new_spatial, 1)

# 6. Remover bloco duplicado de letras de dentro de Aparência se presente
# O bloco de letras deve residir única e exclusivamente na categoria Letras
duplicate_lyrics_pattern = r'val syncedLyricsTitle = stringResource\(R\.string\.synced_lyrics\)[\s\S]*?onClick = onTranslationLanguage,\s*\)\s*\}\s*\}'
# Verifica se há mais de uma ocorrência de syncedLyricsTitle e remove a que estiver dentro de Aparência
if code.count("val syncedLyricsTitle = stringResource(R.string.synced_lyrics)") > 1:
    first_idx = code.find("val syncedLyricsTitle = stringResource(R.string.synced_lyrics)")
    second_idx = code.find("val syncedLyricsTitle = stringResource(R.string.synced_lyrics)", first_idx + 1)
    # A segunda ocorrência geralmente é a duplicata dentro de Aparência
    if second_idx > 0:
        # Encontra o final do if (syncedLyrics) {...}
        end_idx = code.find("SearchableSettingsGroup(search, header = stringResource(R.string.performance))", second_idx)
        if end_idx > 0:
            dup_block = code[second_idx:end_idx]
            code = code[:second_idx] + code[end_idx:]

# 7. Renomear e alinhar os headers das 6 categorias oficiais
code = code.replace('header = stringResource(R.string.account_integrations)', 'header = "Conta & Conexões"')
code = code.replace('header = stringResource(R.string.audio_quality)', 'header = "Reprodução & Áudio"')
code = code.replace('header = stringResource(R.string.playback)', 'header = "Opções de Reprodução"')
code = code.replace('header = stringResource(R.string.appearance)', 'header = "Aparência & Interface"')
code = code.replace('header = stringResource(R.string.downloads)', 'header = "Biblioteca & Armazenamento"')
code = code.replace('header = stringResource(R.string.miscellaneous)', 'header = "Geral & Sistema"')
code = code.replace('header = stringResource(R.string.storage)', 'header = "Armazenamento & Cache"')

# Card dedicado de Letras com AI Lyrics e Chave Gemini se não existir
if 'header = "Letras"' not in code:
    lyrics_group = '''        SearchableSettingsGroup(search, header = "Letras") {
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
            if (syncedLyrics) {
                val lyricsBlurTitle = stringResource(R.string.blur_unfocused_lyrics)
                row(lyricsBlurTitle, "lyrics", "blur") {
                    SettingsRow(
                        icon = Icons.Rounded.BlurOn,
                        title = lyricsBlurTitle,
                        subtitle = stringResource(R.string.blur_unfocused_lyrics_subtitle),
                        trailing = {
                            Switch(
                                checked = lyricsBlur,
                                onCheckedChange = AppSettings::setLyricsBlur,
                                colors = SwitchDefaults.colors(
                                    checkedTrackColor = MaterialTheme.colorScheme.primary,
                                    checkedBorderColor = MaterialTheme.colorScheme.primary,
                                ),
                            )
                        },
                        onClick = { AppSettings.setLyricsBlur(!lyricsBlur) },
                    )
                }
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
    code = code.replace('SearchableSettingsGroup(search, header = "Aparência & Interface")', lyrics_group + '        SearchableSettingsGroup(search, header = "Aparência & Interface")')

# Salva arquivo atualizado
settings_path.write_text(code, encoding="utf-8")
print("patch_settings_ios.py executado com sucesso: Pílulas, Subpáginas e Desduplicação aplicados!")
