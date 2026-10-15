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

# 1. Add imports from ui.theme and typography at the very top after package declaration
package_decl = "package com.music.bitchord.ui.screens"
extra_imports = """package com.music.bitchord.ui.screens

import androidx.compose.ui.text.font.FontWeight
import com.music.bitchord.ui.theme.IosSwitch
import com.music.bitchord.ui.theme.SettingsPillCard
import com.music.bitchord.ui.theme.CapsuleShape
import com.music.bitchord.ui.theme.InsetGroupedShape
"""
assert package_decl in code, "package declaration missing"
code = code.replace(package_decl, extra_imports, 1)

# 2. Remove the old local SettingsPillCard declaration from SettingsSheet.kt so it uses Theme.kt's official one
m = re.search(r'@Composable\s*\nfun SettingsPillCard\([\s\S]*?\n\}\n\}', code)
if m:
    code = code[:m.start()] + code[m.end():]
    print("Removed local SettingsPillCard definition.")

# 3. Add trailing = { Chevron() } to SettingsPillCard in the category loop
code = re.sub(
    r'(SettingsPillCard\s*\(\s*icon\s*=\s*category\.icon,\s*title\s*=\s*category\.title,\s*subtitle\s*=\s*category\.subtitle,\s*onClick\s*=\s*\{\s*selectedCategory\s*=\s*category\s*\},\s*modifier\s*=\s*Modifier\.padding\([^)]+\),)',
    r'\1\n                    trailing = { Chevron() },',
    code
)

# 4. Update subpage header title to bold headlineMedium
code = re.sub(
    r'text\s*=\s*selectedCategory!!\.title,\s*style\s*=\s*MaterialTheme\.typography\.headlineMedium,',
    'text = selectedCategory!!.title,\n                    style = MaterialTheme.typography.headlineMedium.copy(fontWeight = FontWeight.Bold),',
    code
)

# 5. Update search empty condition so it only displays when searchQuery.isNotBlank()
code = re.sub(
    r'if\s*\(!search\.anyMatch\)\s*\{\s*MessageState\(stringResource\(R\.string\.settings_search_empty,\s*searchQuery\)\)\s*\}',
    'if (searchQuery.isNotBlank() && !search.anyMatch) {\n            MessageState(stringResource(R.string.settings_search_empty, searchQuery))\n        }',
    code
)

# 6. Clean footer (remove Discord, Developer, Website and keep only Sonium + GPL v3)
clean_footer = """        if (searchQuery.isBlank() && selectedCategory == null) {
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

code = re.sub(
    r'if\s*\(searchQuery\.isBlank\(\)\s*&&\s*selectedCategory\s*==\s*null\)\s*\{\s*Text\(\s*text\s*=\s*buildAnnotatedString\s*\{[\s\S]*?padding\(top\s*=\s*24\.dp,\s*bottom\s*=\s*\d+\.dp\),\s*\)\s*\}',
    clean_footer,
    code
)

# 7. In SettingsGroup, support standalone capsule vs inset grouped multiple
code = re.sub(
    r'topSpacing:\s*Dp\s*=\s*26\.dp,\s*content:\s*@Composable\s*\(\)\s*->\s*Unit,\s*\)\s*\{\s*if\s*\(header\s*!=\s*null\)\s*\{',
    'topSpacing: Dp = 26.dp,\n    isSingleItem: Boolean = false,\n    content: @Composable () -> Unit,\n) {\n    val shape = if (isSingleItem) CapsuleShape else InsetGroupedShape\n    if (header != null) {',
    code
)
code = re.sub(
    r'\.clip\(GroupShape\)\s*\.background\(MaterialTheme\.colorScheme\.surfaceVariant\),',
    '.clip(shape)\n            .background(MaterialTheme.colorScheme.surfaceVariant),',
    code
)
code = re.sub(
    r'SettingsGroup\(\s*header\s*=\s*header,\s*footer\s*=\s*footer,\s*topSpacing\s*=\s*topSpacing,\s*\)\s*\{',
    'val isSingleItem = scope.entries.size == 1\n    SettingsGroup(\n        header = header,\n        footer = footer,\n        topSpacing = topSpacing,\n        isSingleItem = isSingleItem,\n    ) {',
    code
)

# 8. Replace all Switch with IosSwitch in SettingsSheet.kt
code = re.sub(r'\bSwitch\(', 'IosSwitch(', code)

# 9. Explicit parameter type for highPerformanceMode onCheckedChange
code = code.replace(
    'onCheckedChange = { enabled ->',
    'onCheckedChange = { enabled: Boolean ->'
)

# 10. Write code to SettingsSheet.kt
settings_path.write_text(code, encoding="utf-8")
print(f"SettingsSheet.kt successfully patched ({len(code)} bytes)!")

# Assertions
assert "IosSwitch" in code, "IosSwitch not found in SettingsSheet.kt"
assert "CapsuleShape" in code, "CapsuleShape not found in SettingsSheet.kt"
assert "InsetGroupedShape" in code, "InsetGroupedShape not found in SettingsSheet.kt"
assert "FontWeight" in code, "FontWeight missing"
assert "SettingsCategory" in code, "SettingsCategory enum missing"
assert "selectedCategory" in code, "selectedCategory state missing"
assert "BackHandler" in code, "BackHandler missing"
assert "Discord" not in code, "Discord link still present in footer"
assert "bitchord.kushagrasingh.in" not in code, "Website link still present in footer"
print("All assertions passed!")
