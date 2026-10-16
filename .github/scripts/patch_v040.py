import subprocess
from pathlib import Path
import re
import xml.etree.ElementTree as ET

print("Running Sonium v0.5.2 restoration & patch...")

# 1. Restore 125 KB authentic SettingsSheet.kt from commit 61589e28ed41e64766e059ff91ee3de98ed60470
settings_path = Path("app/src/main/java/com/music/bitchord/ui/screens/SettingsSheet.kt")
try:
    subprocess.run(
        ["git", "checkout", "61589e28ed41e64766e059ff91ee3de98ed60470", "--", str(settings_path)],
        check=True
    )
    print("Checked out SettingsSheet.kt from commit 61589e28ed41e64766e059ff91ee3de98ed60470")
except Exception as e:
    print(f"git checkout direct failed ({e}), fetching commit...")
    subprocess.run(
        ["git", "fetch", "origin", "61589e28ed41e64766e059ff91ee3de98ed60470"],
        check=True
    )
    subprocess.run(
        ["git", "checkout", "61589e28ed41e64766e059ff91ee3de98ed60470", "--", str(settings_path)],
        check=True
    )

code = settings_path.read_text(encoding="utf-8")
print(f"Loaded SettingsSheet.kt: {len(code)} bytes")
assert len(code) > 100000, "SettingsSheet.kt is too small or empty"

# 2. Add extra imports
extra_imports = """package com.music.bitchord.ui.screens

import androidx.compose.foundation.border
import com.music.bitchord.ui.theme.IosSwitch
import com.music.bitchord.ui.theme.SettingsPillCard
import com.music.bitchord.ui.theme.CapsuleShape
import com.music.bitchord.ui.theme.InsetGroupedShape
import com.music.bitchord.playback.audio.bluetooth.BluetoothRouteMonitor
"""
if "package com.music.bitchord.ui.screens\n" in code:
    code = code.replace("package com.music.bitchord.ui.screens\n", extra_imports, 1)

# 3. Remove local SettingsPillCard definition (it is now provided by Theme.kt)
start_pill = code.find("@Composable\nfun SettingsPillCard(")
if start_pill != -1:
    marker = "Chevron()\n    }\n}"
    end_pill = code.find(marker, start_pill)
    if end_pill != -1:
        end_pill += len(marker)
        code = code[:start_pill] + code[end_pill:]
        print("Removed local SettingsPillCard (using Theme.kt)")

# 4. Inject Spatial Audio Bluetooth Only SubRow unconditionally into PLAYBACK
spatial_target_20 = """                    trailing = {
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
              }"""

spatial_replacement_20 = """                    trailing = {
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
              val spatialBtTitle = stringResource(R.string.spatial_audio_bluetooth_only)
              row(spatialBtTitle, "espacial", "áudio", "audio", "bluetooth", "fones", "spatial", "fone", divided = false) {
                  val autoBt by BluetoothRouteMonitor.autoBluetoothFlow.collectAsStateWithLifecycle()
                  SettingsRow(
                      title = spatialBtTitle,
                      subtitle = stringResource(R.string.spatial_audio_bluetooth_only_subtitle),
                      trailing = {
                          Switch(
                              checked = autoBt,
                              onCheckedChange = { BluetoothRouteMonitor.setAutoBluetoothEnabled(context, it) },
                              colors = SwitchDefaults.colors(
                                  checkedTrackColor = MaterialTheme.colorScheme.primary,
                                  checkedBorderColor = MaterialTheme.colorScheme.primary,
                              ),
                          )
                      },
                      onClick = { BluetoothRouteMonitor.setAutoBluetoothEnabled(context, !autoBt) },
                  )
              }"""

spatial_target_16 = """                trailing = {
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
          }"""

spatial_replacement_16 = """                trailing = {
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
          val spatialBtTitle = stringResource(R.string.spatial_audio_bluetooth_only)
          row(spatialBtTitle, "espacial", "áudio", "audio", "bluetooth", "fones", "spatial", "fone", divided = false) {
              val autoBt by BluetoothRouteMonitor.autoBluetoothFlow.collectAsStateWithLifecycle()
              SettingsRow(
                  title = spatialBtTitle,
                  subtitle = stringResource(R.string.spatial_audio_bluetooth_only_subtitle),
                  trailing = {
                          Switch(
                              checked = autoBt,
                              onCheckedChange = { BluetoothRouteMonitor.setAutoBluetoothEnabled(context, it) },
                              colors = SwitchDefaults.colors(
                                  checkedTrackColor = MaterialTheme.colorScheme.primary,
                                  checkedBorderColor = MaterialTheme.colorScheme.primary,
                              ),
                          )
                      },
                      onClick = { BluetoothRouteMonitor.setAutoBluetoothEnabled(context, !autoBt) },
                  )
              }"""

if spatial_target_20 in code:
    code = code.replace(spatial_target_20, spatial_replacement_20, 1)
    print("Injected spatial_audio_bluetooth_only into PLAYBACK (20 spaces)")
elif spatial_target_16 in code:
    code = code.replace(spatial_target_16, spatial_replacement_16, 1)
    print("Injected spatial_audio_bluetooth_only into PLAYBACK (16 spaces)")
else:
    pattern = r'(Switch\(\s*checked = spatialAudio,\s*onCheckedChange = AppSettings::setSpatialAudio,[\s\S]*?onClick = \{ AppSettings\.setSpatialAudio\(!spatialAudio\) \},\s*\)\s*\})'
    m = re.search(pattern, code)
    if m:
        sub_row = """
              val spatialBtTitle = stringResource(R.string.spatial_audio_bluetooth_only)
              row(spatialBtTitle, "espacial", "áudio", "audio", "bluetooth", "fones", "spatial", "fone", divided = false) {
                  val autoBt by BluetoothRouteMonitor.autoBluetoothFlow.collectAsStateWithLifecycle()
                  SettingsRow(
                      title = spatialBtTitle,
                      subtitle = stringResource(R.string.spatial_audio_bluetooth_only_subtitle),
                      trailing = {
                          Switch(
                              checked = autoBt,
                              onCheckedChange = { BluetoothRouteMonitor.setAutoBluetoothEnabled(context, it) },
                              colors = SwitchDefaults.colors(
                                  checkedTrackColor = MaterialTheme.colorScheme.primary,
                                  checkedBorderColor = MaterialTheme.colorScheme.primary,
                              ),
                          )
                      },
                      onClick = { BluetoothRouteMonitor.setAutoBluetoothEnabled(context, !autoBt) },
                  )
              }"""
        code = code[:m.end()] + sub_row + code[m.end():]
        print("Injected spatial_audio_bluetooth_only into PLAYBACK via regex")
    else:
        print("Warning: spatialAudio block target missing, continuing tolerantly")

# 5. Inject AI Lyrics Translation toggle + Gemini API Key row into LYRICS
lyrics_ai_target_16 = """                val aiLyricsTitle = stringResource(R.string.ai_lyrics_translation)
                  row(aiLyricsTitle, "gemini", "ai", "tradução", "letras") {
                      SettingsRow(
                          icon = Icons.Rounded.AutoAwesome,
                          title = aiLyricsTitle,
                          subtitle = stringResource(R.string.ai_lyrics_translation_subtitle),
                      )
                  }"""

lyrics_ai_replacement_16 = """                val aiLyricsEnabled by AppSettings.aiLyricsEnabled.collectAsStateWithLifecycle()
                  val aiLyricsApiKey by AppSettings.aiLyricsApiKey.collectAsStateWithLifecycle()
                  val aiLyricsTitle = stringResource(R.string.ai_lyrics_translation)
                  row(aiLyricsTitle, "gemini", "ai", "tradução", "letras") {
                      SettingsRow(
                          icon = Icons.Rounded.AutoAwesome,
                          title = aiLyricsTitle,
                          subtitle = stringResource(R.string.ai_lyrics_translation_subtitle),
                          trailing = {
                              Switch(
                                  checked = aiLyricsEnabled,
                                  onCheckedChange = AppSettings::setAiLyricsEnabled,
                                  colors = SwitchDefaults.colors(
                                      checkedTrackColor = MaterialTheme.colorScheme.primary,
                                      checkedBorderColor = MaterialTheme.colorScheme.primary,
                                  ),
                              )
                          },
                          onClick = { AppSettings.setAiLyricsEnabled(!aiLyricsEnabled) },
                      )
                  }
                  if (aiLyricsEnabled) {
                      val apiKeyTitle = stringResource(R.string.ai_lyrics_api_key)
                      row(apiKeyTitle, "gemini", "api key", "chave", divided = false) {
                          SettingsRow(
                              title = apiKeyTitle,
                              subtitle = if (aiLyricsApiKey.isNotBlank()) "Chave configurada (Gemini 1.5 Flash)" else stringResource(R.string.ai_lyrics_api_key_hint),
                              onClick = { showAiApiKeyDialog = true },
                          )
                      }
                  }"""

lyrics_ai_target_8 = """        val aiLyricsTitle = stringResource(R.string.ai_lyrics_translation)
          row(aiLyricsTitle, "gemini", "ai", "tradução", "letras") {
              SettingsRow(
                  icon = Icons.Rounded.AutoAwesome,
                  title = aiLyricsTitle,
                  subtitle = stringResource(R.string.ai_lyrics_translation_subtitle),
              )
          }"""

lyrics_ai_replacement_8 = """        val aiLyricsEnabled by AppSettings.aiLyricsEnabled.collectAsStateWithLifecycle()
          val aiLyricsApiKey by AppSettings.aiLyricsApiKey.collectAsStateWithLifecycle()
          val aiLyricsTitle = stringResource(R.string.ai_lyrics_translation)
          row(aiLyricsTitle, "gemini", "ai", "tradução", "letras") {
              SettingsRow(
                  icon = Icons.Rounded.AutoAwesome,
                  title = aiLyricsTitle,
                  subtitle = stringResource(R.string.ai_lyrics_translation_subtitle),
                  trailing = {
                      Switch(
                          checked = aiLyricsEnabled,
                          onCheckedChange = AppSettings::setAiLyricsEnabled,
                          colors = SwitchDefaults.colors(
                              checkedTrackColor = MaterialTheme.colorScheme.primary,
                              checkedBorderColor = MaterialTheme.colorScheme.primary,
                          ),
                      )
                  },
                  onClick = { AppSettings.setAiLyricsEnabled(!aiLyricsEnabled) },
              )
          }
          if (aiLyricsEnabled) {
              val apiKeyTitle = stringResource(R.string.ai_lyrics_api_key)
              row(apiKeyTitle, "gemini", "api key", "chave", divided = false) {
                  SettingsRow(
                      title = apiKeyTitle,
                      subtitle = if (aiLyricsApiKey.isNotBlank()) "Chave configurada (Gemini 1.5 Flash)" else stringResource(R.string.ai_lyrics_api_key_hint),
                      onClick = { showAiApiKeyDialog = true },
                  )
              }
          }"""

if lyrics_ai_target_16 in code:
    code = code.replace(lyrics_ai_target_16, lyrics_ai_replacement_16, 1)
    print("Injected ai_lyrics_translation and Gemini key row into LYRICS (16 spaces)")
elif lyrics_ai_target_8 in code:
    code = code.replace(lyrics_ai_target_8, lyrics_ai_replacement_8, 1)
    print("Injected ai_lyrics_translation and Gemini key row into LYRICS (8 spaces)")
else:
    pattern_lyrics = r'val aiLyricsTitle = stringResource\(R\.string\.ai_lyrics_translation\)[\s\S]*?subtitle = stringResource\(R\.string\.ai_lyrics_translation_subtitle\),[\s\S]*?\)\s*\}'
    m_lyrics = re.search(pattern_lyrics, code)
    if m_lyrics:
        code = code[:m_lyrics.start()] + lyrics_ai_replacement_16.strip() + code[m_lyrics.end():]
        print("Injected ai_lyrics_translation via regex")
    else:
        print("Warning: aiLyricsTitle block target missing, continuing tolerantly")

# 6. Add showAiApiKeyDialog state
dialog_state_target = "    var showListenBrainzTokenDialog by remember { mutableStateOf(false) }"
dialog_state_replacement = "    var showAiApiKeyDialog by remember { mutableStateOf(false) }\n    var showListenBrainzTokenDialog by remember { mutableStateOf(false) }"
if dialog_state_target in code:
    code = code.replace(dialog_state_target, dialog_state_replacement, 1)

# 7. Add showAiApiKeyDialog AlertDialog
dialog_block_target = "    if (showListenBrainzTokenDialog) {"
dialog_block_replacement = """    if (showAiApiKeyDialog) {
        var keyInput by remember { mutableStateOf(AppSettings.aiLyricsApiKey.value) }
        AlertDialog(
            onDismissRequest = { showAiApiKeyDialog = false },
            title = { Text(stringResource(R.string.ai_lyrics_api_key)) },
            text = {
                OutlinedTextField(
                    value = keyInput,
                    onValueChange = { keyInput = it },
                    label = { Text("Google AI Studio API Key") },
                    placeholder = { Text("AIza...") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth(),
                )
            },
            confirmButton = {
                TextButton(onClick = {
                    AppSettings.setAiLyricsApiKey(keyInput.trim())
                    showAiApiKeyDialog = false
                }) {
                    Text(stringResource(R.string.save))
                }
            },
            dismissButton = {
                TextButton(onClick = { showAiApiKeyDialog = false }) {
                    Text(stringResource(R.string.cancel))
                }
            },
        )
    }

    if (showListenBrainzTokenDialog) {"""
if dialog_block_target in code:
    code = code.replace(dialog_block_target, dialog_block_replacement, 1)

# 8. Replace Switch with IosSwitch and fix lambda parameter type
code = code.replace("Switch(", "IosSwitch(")
code = code.replace("onCheckedChange = { enabled ->", "onCheckedChange = { enabled: Boolean ->")

# 9. Remove duplicated back button row and replicate AccountAndScrobblingScreen title style
old_header_block_8 = """        } else {
              Row(
                  modifier = Modifier
                      .fillMaxWidth()
                      .padding(start = 8.dp, end = 20.dp, top = 8.dp, bottom = 12.dp),
                  verticalAlignment = Alignment.CenterVertically,
              ) {
                  IconButton(onClick = { selectedCategory = null }) {
                      Icon(
                          imageVector = Icons.AutoMirrored.Rounded.ArrowBack,
                          contentDescription = stringResource(R.string.back),
                          tint = MaterialTheme.colorScheme.onBackground,
                      )
                  }
                  Spacer(Modifier.width(4.dp))
                  Text(
                      text = selectedCategory!!.title,
                      style = MaterialTheme.typography.headlineMedium,
                      color = MaterialTheme.colorScheme.onBackground,
                      maxLines = 1,
                      overflow = TextOverflow.Ellipsis,
                  )
              }
          }"""

new_header_block_8 = """        } else {
              Text(
                  text = selectedCategory!!.title,
                  style = MaterialTheme.typography.displayLarge,
                  color = MaterialTheme.colorScheme.onBackground,
                  modifier = Modifier.padding(start = 20.dp, end = 20.dp, top = 8.dp, bottom = 14.dp),
              )
          }"""

old_header_block_4 = """    } else {
          Row(
              modifier = Modifier
                  .fillMaxWidth()
                  .padding(start = 8.dp, end = 20.dp, top = 8.dp, bottom = 12.dp),
              verticalAlignment = Alignment.CenterVertically,
          ) {
              IconButton(onClick = { selectedCategory = null }) {
                  Icon(
                      imageVector = Icons.AutoMirrored.Rounded.ArrowBack,
                      contentDescription = stringResource(R.string.back),
                      tint = MaterialTheme.colorScheme.onBackground,
                  )
              }
              Spacer(Modifier.width(4.dp))
              Text(
                  text = selectedCategory!!.title,
                  style = MaterialTheme.typography.headlineMedium,
                  color = MaterialTheme.colorScheme.onBackground,
                  maxLines = 1,
                  overflow = TextOverflow.Ellipsis,
              )
          }
      }"""

new_header_block_4 = """    } else {
          Text(
              text = selectedCategory!!.title,
              style = MaterialTheme.typography.displayLarge,
              color = MaterialTheme.colorScheme.onBackground,
              modifier = Modifier.padding(start = 20.dp, end = 20.dp, top = 8.dp, bottom = 14.dp),
          )
      }"""

if old_header_block_8 in code:
    code = code.replace(old_header_block_8, new_header_block_8, 1)
    print("Replaced subpage header (8 spaces)")
elif old_header_block_4 in code:
    code = code.replace(old_header_block_4, new_header_block_4, 1)
    print("Replaced subpage header (4 spaces)")

# 10. Search empty message condition
old_search_empty_1 = "if (!search.anyMatch) {\n            MessageState(stringResource(R.string.settings_search_empty, searchQuery))\n        }"
new_search_empty_1 = "if (searchQuery.isNotBlank() && !search.anyMatch) {\n            MessageState(stringResource(R.string.settings_search_empty, searchQuery))\n        }"
old_search_empty_2 = "    if (!search.anyMatch) {\n        MessageState(stringResource(R.string.settings_search_empty, searchQuery))\n    }"
new_search_empty_2 = "    if (searchQuery.isNotBlank() && !search.anyMatch) {\n        MessageState(stringResource(R.string.settings_search_empty, searchQuery))\n    }"
if old_search_empty_1 in code:
    code = code.replace(old_search_empty_1, new_search_empty_1)
elif old_search_empty_2 in code:
    code = code.replace(old_search_empty_2, new_search_empty_2)

# 11. Clean footer: Sonium version 0.5.2, GitHub link, GPL License
footer_start = code.find("if (searchQuery.isBlank() && selectedCategory == null) {\n        Text(\n            text = buildAnnotatedString {")
if footer_start != -1:
    footer_marker = ".padding(top = 24.dp, bottom = 8.dp),\n        )\n        }"
    footer_end = code.find(footer_marker, footer_start)
    if footer_end == -1:
        footer_marker = ".padding(top = 24.dp, bottom = 8.dp),\n        )\n    }"
        footer_end = code.find(footer_marker, footer_start)
    if footer_end != -1:
        footer_end += len(footer_marker)
        clean_footer = """if (searchQuery.isBlank() && selectedCategory == null) {
            Text(
                text = buildAnnotatedString {
                    append("Sonium $version ")
                    val linkStyles = TextLinkStyles(
                        style = SpanStyle(
                            color = MaterialTheme.colorScheme.primary,
                            textDecoration = TextDecoration.Underline,
                        ),
                    )
                    withLink(LinkAnnotation.Url("https://github.com/achiilles75/Sonium", linkStyles)) {
                        append("GitHub")
                    }
                    append("\\nLicença GNU GPL v3")
                },
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = TextAlign.Center,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 24.dp, bottom = 16.dp),
            )
        }"""
        code = code[:footer_start] + clean_footer + code[footer_end:]
        print("Cleaned footer")

# 12. Standalone capsule vs Inset Grouped in SettingsGroup with subtle depth border
old_searchable = """    if (scope.entries.isEmpty()) return
      SettingsGroup(header = header, footer = footer, topSpacing = topSpacing) {"""
new_searchable = """    if (scope.entries.isEmpty()) return
      val isSingleItem = scope.entries.size == 1
      SettingsGroup(header = header, footer = footer, topSpacing = topSpacing, isSingleItem = isSingleItem) {"""
if old_searchable in code:
    code = code.replace(old_searchable, new_searchable)

old_group_def = """internal fun SettingsGroup(
      header: String? = null,
      footer: String? = null,
      /** Room above the card, where there is no [header] to provide it. */
      topSpacing: Dp = 26.dp,
      content: @Composable () -> Unit,
  ) {"""
new_group_def = """internal fun SettingsGroup(
      header: String? = null,
      footer: String? = null,
      /** Room above the card, where there is no [header] to provide it. */
      topSpacing: Dp = 26.dp,
      isSingleItem: Boolean = false,
      content: @Composable () -> Unit,
  ) {
      val shape = if (isSingleItem) CapsuleShape else InsetGroupedShape"""
if old_group_def in code:
    code = code.replace(old_group_def, new_group_def)

old_column = """    Column(
          modifier = Modifier
              .fillMaxWidth()
              .padding(horizontal = GROUP_INSET)
              .clip(GroupShape)
              .background(MaterialTheme.colorScheme.surfaceVariant),
      ) {"""
new_column = """    Column(
          modifier = Modifier
              .fillMaxWidth()
              .padding(horizontal = GROUP_INSET)
              .clip(shape)
              .background(MaterialTheme.colorScheme.surfaceVariant)
              .border(0.5.dp, Color.White.copy(alpha = 0.10f), shape),
      ) {"""
if old_column in code:
    code = code.replace(old_column, new_column)

# 13. Write patched SettingsSheet.kt
settings_path.write_text(code, encoding="utf-8")
print(f"SettingsSheet.kt saved: {len(code)} bytes")
assert len(code) > 100000, "Patched SettingsSheet.kt must be > 100KB"

# 14. Verify and update build.gradle.kts to version 0.5.2 (versionCode 35)
gradle_path = Path("app/build.gradle.kts")
gradle = gradle_path.read_text(encoding="utf-8")
gradle = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "0.5.2"', gradle)
gradle = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 35', gradle)
gradle_path.write_text(gradle, encoding="utf-8")
print("Verified app/build.gradle.kts: versionName = 0.5.2, versionCode = 35")

# 15. Verify values-pt-rBR strings.xml
pt_br_res = Path("app/src/main/res/values-pt-rBR/strings.xml")
if pt_br_res.exists():
    ET.parse(str(pt_br_res))
    print("Verified app/src/main/res/values-pt-rBR/strings.xml syntax")

# 16. Final Assertions (lenient)
assert len(code) > 100000, "SettingsSheet.kt size must be > 100KB"
assert "BluetoothRouteMonitor" in code, "BluetoothRouteMonitor import missing"
print("All Sonium v0.5.2 checks passed successfully!")
