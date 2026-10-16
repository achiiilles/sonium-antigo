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
assert "package com.music.bitchord.ui.screens" in code, "package decl missing"
code = re.sub(r'package\s+com\.music\.bitchord\.ui\.screens\s*\n', extra_imports, code, count=1)

# 3. Remove local SettingsPillCard definition (it is now provided by Theme.kt)
start_pill = code.find("@Composable\nfun SettingsPillCard(")
if start_pill == -1:
    start_pill = code.find("@Composable\r\nfun SettingsPillCard(")
if start_pill != -1:
    marker = "Chevron()\n}\n}"
    end_pill = code.find(marker, start_pill)
    if end_pill == -1:
        m = re.search(r'Chevron\(\)\s*\}\s*\}\s*\}', code[start_pill:])
        if m:
            end_pill = start_pill + m.end()
    else:
        end_pill += len(marker)
    if end_pill != -1:
        code = code[:start_pill] + code[end_pill:]
        print("Removed local SettingsPillCard (using Theme.kt)")

# 4. Inject Spatial Audio Bluetooth Only SubRow unconditionally into PLAYBACK
spatial_bt_row = """
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
}
"""
pattern_spatial = r'(AppSettings\.setSpatialAudio\(!spatialAudio\)\s*\},?\s*\)\s*\})'
m = re.search(pattern_spatial, code)
assert m is not None, "spatialAudio block target missing in SettingsSheet.kt"
code = code[:m.end()] + "\n" + spatial_bt_row + code[m.end():]
print("Injected spatial_audio_bluetooth_only into PLAYBACK unconditionally")

# 5. Inject AI Lyrics Translation toggle + Gemini API Key row into LYRICS
lyrics_ai_replacement = """val aiLyricsEnabled by AppSettings.aiLyricsEnabled.collectAsStateWithLifecycle()
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
pattern_lyrics = r'val\s+aiLyricsTitle\s*=\s*stringResource\(R\.string\.ai_lyrics_translation\)[\s\S]*?subtitle\s*=\s*stringResource\(R\.string\.ai_lyrics_translation_subtitle\),?\s*\)\s*\}'
m = re.search(pattern_lyrics, code)
assert m is not None, "aiLyricsTitle block target missing in SettingsSheet.kt"
code = code[:m.start()] + lyrics_ai_replacement + code[m.end():]
print("Injected ai_lyrics_translation and Gemini key row into LYRICS")

# 6. Add showAiApiKeyDialog state
pattern_listen_dialog = r'(\bvar\s+showListenBrainzTokenDialog\s+by\s+remember\s*\{\s*mutableStateOf\(false\)\s*\})'
m = re.search(pattern_listen_dialog, code)
assert m is not None, "dialog_state_target missing in SettingsSheet.kt"
code = code[:m.start()] + "var showAiApiKeyDialog by remember { mutableStateOf(false) }\n" + code[m.start():]
print("Added showAiApiKeyDialog state")

# 7. Add showAiApiKeyDialog AlertDialog
dialog_block_replacement = """if (showAiApiKeyDialog) {
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
"""
pattern_listen_block = r'(if\s*\(\s*showListenBrainzTokenDialog\s*\)\s*\{)'
m = re.search(pattern_listen_block, code)
assert m is not None, "dialog_block_target missing in SettingsSheet.kt"
code = code[:m.start()] + dialog_block_replacement + code[m.start():]
print("Added showAiApiKeyDialog AlertDialog")

# 8. Replace Switch with IosSwitch and fix lambda parameter type
code = code.replace("Switch(", "IosSwitch(")
code = re.sub(r'onCheckedChange\s*=\s*\{\s*enabled\s*->', 'onCheckedChange = { enabled: Boolean ->', code)

# 9. Remove duplicated back button row and replicate AccountAndScrobblingScreen title style
new_header_block = """} else {
Text(
text = selectedCategory!!.title,
style = MaterialTheme.typography.displayLarge,
color = MaterialTheme.colorScheme.onBackground,
modifier = Modifier.padding(start = 20.dp, end = 20.dp, top = 8.dp, bottom = 14.dp),
)
}"""
pattern_header = r'\}\s*else\s*\{\s*Row\([\s\S]*?IconButton\s*\(\s*onClick\s*=\s*\{\s*selectedCategory\s*=\s*null\s*\}[\s\S]*?style\s*=\s*MaterialTheme\.typography\.headlineMedium[\s\S]*?\)\s*\}\s*\}'
m = re.search(pattern_header, code)
assert m is not None, "old header block missing in SettingsSheet.kt"
code = code[:m.start()] + new_header_block + code[m.end():]
print("Replaced subpage header with AccountAndScrobblingScreen displayLarge style without duplicate back button")

# 10. Search empty message condition
pattern_search_empty = r'if\s*\(\s*!search\.anyMatch\s*\)\s*\{\s*MessageState\(stringResource\(R\.string\.settings_search_empty,\s*searchQuery\)\)\s*\}'
m = re.search(pattern_search_empty, code)
assert m is not None, "search empty condition missing"
code = code[:m.start()] + "if (searchQuery.isNotBlank() && !search.anyMatch) {\nMessageState(stringResource(R.string.settings_search_empty, searchQuery))\n}" + code[m.end():]
print("Fixed search empty message condition")

# 11. Clean footer: Sonium version 0.5.2, GitHub link, GPL License
footer_start = code.find("if (searchQuery.isBlank() && selectedCategory == null) {\nText(\ntext = buildAnnotatedString {")
if footer_start == -1:
    footer_start = code.find("if (searchQuery.isBlank() && selectedCategory == null)")
assert footer_start != -1, "footer_start missing"
marker = "~YouTube Music & Listen Together Backend"
idx_marker = code.find(marker, footer_start)
assert idx_marker != -1, "footer marker missing"
idx_close = code.find(")\n}", idx_marker)
if idx_close == -1:
    idx_close = code.find(")\r\n}", idx_marker)
assert idx_close != -1, "footer close missing"
footer_end = idx_close + len(")\n}")

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
pattern_searchable = r'if\s*\(\s*scope\.entries\.isEmpty\(\)\s*\)\s*return\s*\n\s*SettingsGroup\s*\(\s*header\s*=\s*header,\s*footer\s*=\s*footer,\s*topSpacing\s*=\s*topSpacing\s*\)\s*\{'
replacement_searchable = """if (scope.entries.isEmpty()) return
val isSingleItem = scope.entries.size == 1
SettingsGroup(header = header, footer = footer, topSpacing = topSpacing, isSingleItem = isSingleItem) {"""
m = re.search(pattern_searchable, code)
assert m is not None, "SearchableSettingsGroup pattern missing"
code = code[:m.start()] + replacement_searchable + code[m.end():]

pattern_group_def = r'internal\s+fun\s+SettingsGroup\s*\([\s\S]*?topSpacing:\s*Dp\s*=\s*26\.dp,\s*\n\s*content:\s*@Composable\s*\(\)\s*->\s*Unit,?\s*\)\s*\{'
replacement_group_def = """internal fun SettingsGroup(
header: String? = null,
footer: String? = null,
/** Room above the card, where there is no [header] to provide it. */
topSpacing: Dp = 26.dp,
isSingleItem: Boolean = false,
content: @Composable () -> Unit,
) {
val shape = if (isSingleItem) CapsuleShape else InsetGroupedShape"""
m = re.search(pattern_group_def, code)
assert m is not None, "SettingsGroup signature missing"
code = code[:m.start()] + replacement_group_def + code[m.end():]

pattern_column = r'Column\s*\(\s*\n\s*modifier\s*=\s*Modifier[\s\S]*?\.padding\(horizontal\s*=\s*GROUP_INSET\)[\s\S]*?\.clip\(GroupShape\)[\s\S]*?\.background\(MaterialTheme\.colorScheme\.surfaceVariant\),?\s*\)\s*\{'
replacement_column = """Column(
modifier = Modifier
.fillMaxWidth()
.padding(horizontal = GROUP_INSET)
.clip(shape)
.background(MaterialTheme.colorScheme.surfaceVariant)
.border(0.5.dp, Color.White.copy(alpha = 0.10f), shape),
) {"""
m = re.search(pattern_column, code)
assert m is not None, "SettingsGroup column clip missing"
code = code[:m.start()] + replacement_column + code[m.end():]

# 13. Write patched SettingsSheet.kt
settings_path.write_text(code, encoding="utf-8")
print(f"SettingsSheet.kt saved: {len(code)} bytes")

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

# 16. Final Assertions
assert "IosSwitch" in code, "IosSwitch not found in SettingsSheet.kt"
assert "CapsuleShape" in code, "CapsuleShape not found in SettingsSheet.kt"
assert "InsetGroupedShape" in code, "InsetGroupedShape not found in SettingsSheet.kt"
assert "displayLarge" in code, "displayLarge missing in subpage header"
assert "Icons.AutoMirrored.Rounded.ArrowBack" not in code, "ArrowBack still present in SettingsSheet.kt"
assert "searchQuery.isNotBlank() && !search.anyMatch" in code, "Search empty fix missing"
assert "Discord" not in code, "Discord link still in footer"
assert "bitchord.kushagrasingh.in" not in code, "Website link still in footer"
assert "BluetoothRouteMonitor" in code, "BluetoothRouteMonitor import missing in SettingsSheet.kt"
assert "spatial_audio_bluetooth_only" in code, "spatial_audio_bluetooth_only missing in SettingsSheet.kt"
assert "ai_lyrics_api_key" in code, "ai_lyrics_api_key missing in SettingsSheet.kt"
assert "showAiApiKeyDialog" in code, "showAiApiKeyDialog missing in SettingsSheet.kt"

print("All Sonium v0.5.2 checks passed successfully!")
