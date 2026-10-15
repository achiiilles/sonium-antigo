import urllib.request
import re
from pathlib import Path

print("Running Sonium SettingsSheet restoration & patch...")
settings_path = Path("app/src/main/java/com/music/bitchord/ui/screens/SettingsSheet.kt")

# Fetch full authentic SettingsSheet.kt from commit cbb1a631e6f081330c2c6bdb2742795f2e9c20c1
url = "https://raw.githubusercontent.com/achiilles75/Sonium/cbb1a631e6f081330c2c6bdb2742795f2e9c20c1/app/src/main/java/com/music/bitchord/ui/screens/SettingsSheet.kt"
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as resp:
    code = resp.read().decode('utf-8')

print(f"Downloaded authentic SettingsSheet.kt ({len(code)} bytes)")

# 1. Add imports from ui.theme
theme_imports = """
import com.music.bitchord.ui.theme.IosSwitch
import com.music.bitchord.ui.theme.SettingsPillCard
import com.music.bitchord.ui.theme.CapsuleShape
import com.music.bitchord.ui.theme.InsetGroupedShape
"""
code = code.replace("import androidx.compose.ui.text.font.FontWeight", "import androidx.compose.ui.text.font.FontWeight" + theme_imports)

# 2. Update subpage header title to bold headlineMedium
code = code.replace(
    'text = selectedCategory!!.title,\n                    style = MaterialTheme.typography.headlineMedium,',
    'text = selectedCategory!!.title,\n                    style = MaterialTheme.typography.headlineMedium.copy(fontWeight = FontWeight.Bold),'
)

# 3. Update search empty condition so it only displays when searchQuery.isNotBlank()
code = code.replace(
    'if (!search.anyMatch) {\n            MessageState(stringResource(R.string.settings_search_empty, searchQuery))\n        }',
    'if (searchQuery.isNotBlank() && !search.anyMatch) {\n            MessageState(stringResource(R.string.settings_search_empty, searchQuery))\n        }'
)

# 4. Clean footer (remove Discord, Developer, Website and keep only Sonium + GPL v3)
colophon_old = """        if (searchQuery.isBlank() && selectedCategory == null) {
            Text(
                text = buildAnnotatedString {
                    append("Sonium $version  ")
                    val linkStyles = TextLinkStyles(
                        style = SpanStyle(
                            color = MaterialTheme.colorScheme.primary,
                            textDecoration = TextDecoration.Underline,
                        ),
                    )
                    withLink(LinkAnnotation.Url("https://discord.gg/7cR3R9Cq6F", linkStyles)) {
                        append("Discord")
                    }
                    append("  ")
                    withLink(LinkAnnotation.Url("https://bitchord.com", linkStyles)) {
                        append("Website")
                    }
                    append("  ")
                    withLink(LinkAnnotation.Url("https://github.com/fast4x", linkStyles)) {
                        append("Developer")
                    }
                    append("  ")
                    withLink(LinkAnnotation.Url("https://github.com/achiilles75/Sonium", linkStyles)) {
                        append("GitHub")
                    }
                    append("\\nGNU General Public License v3.0")
                },
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = TextAlign.Center,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(top = 24.dp, bottom = 16.dp),
            )
        }"""

colophon_new = """        if (searchQuery.isBlank() && selectedCategory == null) {
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
code = code.replace(colophon_old, colophon_new)

# 5. In SettingsGroup, support standalone capsule vs inset grouped multiple
code = code.replace(
    'topSpacing: Dp = 26.dp,\n    content: @Composable () -> Unit,\n) {\n    if (header != null) {',
    'topSpacing: Dp = 26.dp,\n    isSingleItem: Boolean = false,\n    content: @Composable () -> Unit,\n) {\n    val shape = if (isSingleItem) CapsuleShape else InsetGroupedShape\n    if (header != null) {'
)
code = code.replace(
    '.clip(GroupShape)\n            .background(MaterialTheme.colorScheme.surfaceVariant),',
    '.clip(shape)\n            .background(MaterialTheme.colorScheme.surfaceVariant),'
)
code = code.replace(
    'SettingsGroup(\n        header = header,\n        footer = footer,\n        topSpacing = topSpacing,\n    ) {',
    'val isSingleItem = scope.entries.size == 1\n    SettingsGroup(\n        header = header,\n        footer = footer,\n        topSpacing = topSpacing,\n        isSingleItem = isSingleItem,\n    ) {'
)

# 6. Replace all Switch with IosSwitch in SettingsSheet.kt
# First in trailing/Row scopes
code = code.replace(
    'Switch(\n                            checked = ',
    'IosSwitch(\n                            checked = '
)
code = code.replace(
    'Switch(\n            checked = checked,',
    'IosSwitch(\n            checked = checked,'
)

# 7. Write code to SettingsSheet.kt
settings_path.write_text(code, encoding="utf-8")
print(f"SettingsSheet.kt successfully patched ({len(code)} bytes)!")

# Assertions
assert "IosSwitch" in code, "IosSwitch not found in SettingsSheet.kt"
assert "CapsuleShape" in code, "CapsuleShape not found in SettingsSheet.kt"
assert "SettingsCategory" in code, "SettingsCategory enum missing"
assert "SettingsPillCard" in code, "SettingsPillCard composable missing"
assert "selectedCategory" in code, "selectedCategory state missing"
assert "BackHandler" in code, "BackHandler missing"
print("All assertions passed!")
