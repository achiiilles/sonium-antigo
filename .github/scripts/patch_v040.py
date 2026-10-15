import subprocess
from pathlib import Path
import re
import xml.etree.ElementTree as ET

print("Running Sonium v0.4.7 restoration & patch...")

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

# 2. Add imports
extra_imports = """package com.music.bitchord.ui.screens

import androidx.compose.ui.text.font.FontWeight
import androidx.compose.foundation.border
import androidx.compose.ui.graphics.Color
import com.music.bitchord.ui.theme.IosSwitch
import com.music.bitchord.ui.theme.SettingsPillCard
import com.music.bitchord.ui.theme.CapsuleShape
import com.music.bitchord.ui.theme.InsetGroupedShape
"""
assert "package com.music.bitchord.ui.screens\n" in code, "package decl missing"
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

# 4. Replace Switch with IosSwitch and fix lambda parameter type
code = code.replace("Switch(", "IosSwitch(")
code = code.replace("onCheckedChange = { enabled ->", "onCheckedChange = { enabled: Boolean ->")

# 5. Remove duplicated back button row and replicate AccountAndScrobblingScreen title style
old_header_block = """        } else {
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

new_header_block = """        } else {
            Text(
                text = selectedCategory!!.title,
                style = MaterialTheme.typography.displayLarge,
                color = MaterialTheme.colorScheme.onBackground,
                modifier = Modifier.padding(start = 20.dp, end = 20.dp, top = 8.dp, bottom = 14.dp),
            )
        }"""
assert old_header_block in code, "old header block missing in SettingsSheet.kt"
code = code.replace(old_header_block, new_header_block, 1)
print("Replaced subpage header with AccountAndScrobblingScreen displayLarge style without duplicate back button")

# 6. Search empty message condition
old_search_empty = "if (!search.anyMatch) {\n            MessageState(stringResource(R.string.settings_search_empty, searchQuery))\n        }"
new_search_empty = "if (searchQuery.isNotBlank() && !search.anyMatch) {\n            MessageState(stringResource(R.string.settings_search_empty, searchQuery))\n        }"
assert old_search_empty in code, "search empty condition missing"
code = code.replace(old_search_empty, new_search_empty)

# 7. Clean footer: Sonium version, GitHub letter, GPL License
footer_start = code.find("if (searchQuery.isBlank() && selectedCategory == null) {\n        Text(\n            text = buildAnnotatedString {")
if footer_start != -1:
    footer_marker = ".padding(top = 24.dp, bottom = 8.dp),\n        )\n        }"
    footer_end = code.find(footer_marker, footer_start)
    if footer_end != -1:
        footer_end += len(footer_marker)
        clean_footer = """if (searchQuery.isBlank() && selectedCategory == null) {
            Text(
                text = buildAnnotatedString {
                    append("Sonium $version  ")
                    val linkStyles = TextLinkStyles(
                        style = SpanStyle(
                            color = MaterialTheme.colorScheme.primary,
                            textDecoration = TextDecoration.Underline,
                        ),
                    )
                    withLink(LinkAnnotation.Url("https://github.com/achiilles75/Sonium", linkStyles)) {
                        append("GitHub")
                    }
                    append("\\nLicença GNU GPL  v3")
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

# 8. Standalone capsule vs Inset Grouped in SettingsGroup with subtle depth border
old_searchable = """    if (scope.entries.isEmpty()) return
    SettingsGroup(header = header, footer = footer, topSpacing = topSpacing) {"""
new_searchable = """    if (scope.entries.isEmpty()) return
    val isSingleItem = scope.entries.size == 1
    SettingsGroup(header = header, footer = footer, topSpacing = topSpacing, isSingleItem = isSingleItem) {"""
assert old_searchable in code, "SearchableSettingsGroup pattern missing"
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
assert old_group_def in code, "SettingsGroup signature missing"
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
assert old_column in code, "SettingsGroup column clip missing"
code = code.replace(old_column, new_column)

# 9. Write patched SettingsSheet.kt
settings_path.write_text(code, encoding="utf-8")
print(f"SettingsSheet.kt saved: {len(code)} bytes")

# 10. Verify build.gradle.kts
gradle_path = Path("app/build.gradle.kts")
gradle = gradle_path.read_text(encoding="utf-8")
if 'versionName = "0.4.7"' not in gradle:
    gradle = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "0.4.7"', gradle)
if 'versionCode = 32' not in gradle:
    gradle = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 32', gradle)
gradle_path.write_text(gradle, encoding="utf-8")
print("Verified app/build.gradle.kts: versionName = 0.4.7, versionCode = 32")

# 11. Verify values-pt-rBR strings.xml
pt_br_res = Path("app/src/main/res/values-pt-rBR/strings.xml")
if pt_br_res.exists():
    ET.parse(str(pt_br_res))
    print("Verified app/src/main/res/values-pt-rBR/strings.xml syntax")

pt_br_shared = Path("sharedUi/src/commonMain/composeResources/values-pt-rBR/strings.xml")
if pt_br_shared.exists():
    ET.parse(str(pt_br_shared))
    print("Verified sharedUi/src/commonMain/composeResources/values-pt-rBR/strings.xml syntax")

# 12. Final Assertions
assert "IosSwitch" in code, "IosSwitch not found in SettingsSheet.kt"
assert "CapsuleShape" in code, "CapsuleShape not found in SettingsSheet.kt"
assert "InsetGroupedShape" in code, "InsetGroupedShape not found in SettingsSheet.kt"
assert "displayLarge" in code, "displayLarge missing in subpage header"
assert "Icons.AutoMirrored.Rounded.ArrowBack" not in code, "ArrowBack still present in SettingsSheet.kt"
assert "searchQuery.isNotBlank() && !search.anyMatch" in code, "Search empty fix missing"
assert "Discord" not in code, "Discord link still in footer"
assert "bitchord.kushagrasingh.in" not in code, "Website link still in footer"
print("All Sonium v0.4.7 checks passed successfully!")
