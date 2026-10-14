import os
import re

# 1. Patch SettingsSheet.kt
settings_path = "app/src/main/java/com/music/bitchord/ui/screens/SettingsSheet.kt"
if os.path.exists(settings_path):
    with open(settings_path, "r", encoding="utf-8") as f:
        sc = f.read()
    sc = sc.replace('subtitle = "Music/BitChord".takeIf { exportDownloads },', 'subtitle = "Music/Sonium".takeIf { exportDownloads },')
    sc = sc.replace("BitChord $version", "Sonium $version")
    sc = sc.replace("https://discord.gg/pDdKfrdHY6", "https://github.com/achiilles75/BitChord")
    sc = sc.replace("https://github.com/kushagrasinghx/BitChord", "https://github.com/achiilles75/BitChord")
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
