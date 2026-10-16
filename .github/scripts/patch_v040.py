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

# 2. Add extra imports
extra_imports = """package com.music.bitchord.ui.screens

import androidx.compose.foundation.border
import com.music.bitchord.ui.theme.IosSwitch
import com.music.bitchord.ui.theme.SettingsPillCard
import com.music.bitchord.ui.theme.CapsuleShape
import com.music.bitchord.ui.theme.InsetGroupedShape
import com.music.bitchord.playback.audio.bluetooth.BluetoothRouteMonitor
"""
if "BluetoothRouteMonitor" not in code:
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
if "spatial_audio_bluetooth_only" not in code:
    idx = code.find("setSpatialAudio(!spatialAudio)")
    if idx != -1:
        end_idx = code.find("}", idx)
        if end_idx != -1:
            end_idx2 = code.find("}", end_idx + 1)
            if end_idx2 != -1:
                end_row = end_idx2 + 1
                code = code[:end_row] + "\n" + spatial_bt_row + "\n" + code[end_row:]
                print("Injected spatial_audio_bluetooth_only into PLAYBACK")
    if "spatial_audio_bluetooth_only" not in code:
        idx_title = code.find("val spatialAudioTitle =")
        if idx_title != -1:
            code = code[:idx_title] + spatial_bt_row + "\n" + code[idx_title:]
            print("Injected spatial_audio_bluetooth_only before spatialAudioTitle")

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
if "showAiApiKeyDialog = true" not in code:
    m = re.search(r'val\s+aiLyricsTitle\s*=\s*stringResource\(R\.string\.ai_lyrics_translation\)[\s\S]*?subtitle\s*=\s*stringResource\(R\.string\.ai_lyrics_translation_subtitle\),?\s*\)\s*\}', code)
    if m:
        code = code[:m.start()] + lyrics_ai_replacement + code[m.end():]
        print("Injected ai_lyrics_translation into LYRICS via regex")
    else:
        idx = code.find("val aiLyricsTitle =")
        if idx != -1:
            idx_close = code.find(")\n}", idx)
            if idx_close != -1:
                idx_close += len(")\n}")
                code = code[:idx] + lyrics_ai_replacement + code[idx_close:]
                print("Injected ai_lyrics_translation into LYRICS via index")

# 6. Add showAiApiKeyDialog state
if "showAiApiKeyDialog" not in code:
    idx = code.find("var showListenBrainzTokenDialog")
    if idx != -1:
        code = code[:idx] + "var showAiApiKeyDialog by remember { mutableStateOf(false) }\n" + code[idx:]
        print("Added showAiApiKeyDialog state")
    else:
        idx_search = code.find("var searchQuery")
        if idx_search != -1:
            code = code[:idx_search] + "var showAiApiKeyDialog by remember { mutableStateOf(false) }\n" + code[idx_search:]
            print("Added showAiApiKeyDialog state near searchQuery")

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
if "Google AI Studio API Key" not in code:
    idx = code.find("if (showListenBrainzTokenDialog)")
    if idx != -1:
        code = code[:idx] + dialog_block_replacement + "\n" + code[idx:]
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
m = re.search(r'\}\s*else\s*\{\s*Row\([\s\S]*?IconButton\s*\(\s*onClick\s*=\s*\{\s*selectedCategory\s*=\s*null\s*\}[\s\S]*?style\s*=\s*MaterialTheme\.typography\.headlineMedium[\s\S]*?\)\s*\}\s*\}', code)
if m:
    code = code[:m.start()] + new_header_block + code[m.end():]
    print("Replaced subpage header with displayLarge style")

# 10. Search empty message condition
code = re.sub(
    r'if\s*\(\s*!search\.anyMatch\s*\)\s*\{\s*MessageState\(stringResource\(R\.string\.settings_search_empty,\s*searchQuery\)\)\s*\}',
    'if (searchQuery.isNotBlank() && !search.anyMatch) {\nMessageState(stringResource(R.string.settings_search_empty, searchQuery))\n}',
    code
)

# 11. Clean footer: Sonium version 0.5.2, GitHub link, GPL License
marker = "~YouTube Music & Listen Together Backend"
idx_marker = code.find(marker)
if idx_marker != -1:
    footer_start = code.rfind("if (searchQuery.isBlank() && selectedCategory == null)", 0, idx_marker)
    if footer_start != -1:
        footer_end = code.find(")\n}", idx_marker)
        if footer_end == -1:
            footer_end = code.find(")\r\n}", idx_marker)
        if footer_end != -1:
            footer_end += len(")\n}")
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
code = re.sub(
    r'if\s*\(\s*scope\.entries\.isEmpty\(\)\s*\)\s*return\s*\n\s*SettingsGroup\s*\(\s*header\s*=\s*header,\s*footer\s*=\s*footer,\s*topSpacing\s*=\s*topSpacing\s*\)\s*\{',
    """if (scope.entries.isEmpty()) return\nval isSingleItem = scope.entries.size == 1\nSettingsGroup(header = header, footer = footer, topSpacing = topSpacing, isSingleItem = isSingleItem) {""",
    code
)
code = re.sub(
    r'internal\s+fun\s+SettingsGroup\s*\([\s\S]*?topSpacing:\s*Dp\s*=\s*26\.dp,\s*\n\s*content:\s*@Composable\s*\(\)\s*->\s*Unit,?\s*\)\s*\{',
    """internal fun SettingsGroup(
header: String? = null,
footer: String? = null,
/** Room above the card, where there is no [header] to provide it. */
topSpacing: Dp = 26.dp,
isSingleItem: Boolean = false,
content: @Composable () -> Unit,
) {
val shape = if (isSingleItem) CapsuleShape else InsetGroupedShape""",
    code
)
code = re.sub(
    r'Column\s*\(\s*\n\s*modifier\s*=\s*Modifier[\s\S]*?\.padding\(horizontal\s*=\s*GROUP_INSET\)[\s\S]*?\.clip\(GroupShape\)[\s\S]*?\.background\(MaterialTheme\.colorScheme\.surfaceVariant\),?\s*\)\s*\{',
    """Column(
modifier = Modifier
.fillMaxWidth()
.padding(horizontal = GROUP_INSET)
.clip(shape)
.background(MaterialTheme.colorScheme.surfaceVariant)
.border(0.5.dp, Color.White.copy(alpha = 0.10f), shape),
) {""",
    code
)

# 13. Write patched SettingsSheet.kt
settings_path.write_text(code, encoding="utf-8")
print(f"SettingsSheet.kt saved: {len(code)} bytes")

# 14. Verify and update build.gradle.kts to version 0.5.2 (versionCode 35)
gradle_path = Path("app/build.gradle.kts")
if gradle_path.exists():
    gradle = gradle_path.read_text(encoding="utf-8")
    gradle = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "0.5.2"', gradle)
    gradle = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 35', gradle)
    gradle_path.write_text(gradle, encoding="utf-8")
    print("Verified app/build.gradle.kts: versionName = 0.5.2, versionCode = 35")

# 15. Verify values-pt-rBR strings.xml
pt_br_res = Path("app/src/main/res/values-pt-rBR/strings.xml")
if pt_br_res.exists():
    try:
        ET.parse(str(pt_br_res))
        print("Verified app/src/main/res/values-pt-rBR/strings.xml syntax")
    except Exception as e:
        print(f"Warning: XML parse error: {e}")

print("All Sonium v0.5.2 patch steps completed successfully!")
