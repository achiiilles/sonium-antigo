import os
import re

# 1. Patch SettingsSheet.kt
settings_path = "app/src/main/java/com/music/bitchord/ui/screens/SettingsSheet.kt"
if os.path.exists(settings_path):
    with open(settings_path, "r", encoding="utf-8") as f:
        sc = f.read()
    sc = sc.replace('subtitle = "Music/BitChord".takeIf { exportDownloads },', 'subtitle = "Music/Sonium".takeIf { exportDownloads },')
    
    # Substituir colophon do rodapé
    old_colophon_pattern = re.compile(r'if \(searchQuery\.isBlank\(\)\) \{\s*Text\(\s*text = buildAnnotatedString \{.*?\n\s*append\("\\n~YouTube Music & Listen Together Backend"\)\s*\},', re.DOTALL)
    new_colophon = """if (searchQuery.isBlank()) {
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
                append("\\n~YouTube Music & Listen Together Backend")
            },"""
    if old_colophon_pattern.search(sc):
        sc = old_colophon_pattern.sub(new_colophon, sc)
        print("SettingsSheet.kt colophon updated cleanly with regex")
    else:
        # Fallback manual string replacement
        sc = sc.replace("bitchord $version", "Sonium $version")
        sc = sc.replace("BitChord $version", "Sonium $version")
        sc = sc.replace("https://github.com/kushagrasinghx/BitChord", "https://github.com/achiilles75/Sonium")
        sc = sc.replace("https://github.com/achiilles75/BitChord", "https://github.com/achiilles75/Sonium")
    
    with open(settings_path, "w", encoding="utf-8") as f:
        f.write(sc)
    print("SettingsSheet.kt updated")

# 2. Helper to replace only inside tag text, not tag attributes (preserves resource IDs)
def replace_tag_text(xml_content):
    def repl(m):
        val = m.group(1)
        val = val.replace("BitChord", "Sonium").replace("bitchord", "sonium")
        return f">{val}<"
    return re.sub(r'>([^<]+)<', repl, xml_content)

for strings_file in ["app/src/main/res/values/strings.xml", "app/src/main/res/values-pt/strings.xml"]:
    if os.path.exists(strings_file):
        with open(strings_file, "r", encoding="utf-8") as f:
            content = f.read()
        content = replace_tag_text(content)
        with open(strings_file, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Updated text in {strings_file}")

print("All branding patches completed successfully!")
