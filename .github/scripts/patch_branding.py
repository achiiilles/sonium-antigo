import os

def patch_file(path, old, new):
    if not os.path.exists(path):
        print(f"Skipping {path}, does not exist")
        return
    with open(path, "r", encoding="utf-8") as f:
        c = f.read()
    if old in c:
        c = c.replace(old, new)
        with open(path, "w", encoding="utf-8") as f:
            f.write(c)
        print(f"Patched {path}")
    else:
        print(f"Pattern not found in {path}")

# 1. Patch SettingsSheet.kt
settings_path = "app/src/main/java/com/music/bitchord/ui/screens/SettingsSheet.kt"
if os.path.exists(settings_path):
    with open(settings_path, "r", encoding="utf-8") as f:
        sc = f.read()
    sc = sc.replace('subtitle = "Music/BitChord".takeIf { exportDownloads },', 'subtitle = "Music/Sonium".takeIf { exportDownloads },')
    
    old_colophon = """        if (searchQuery.isBlank()) {
        Text(
            text = buildAnnotatedString {
                append("BitChord $version  ")
                val linkStyles = TextLinkStyles(
                    style = SpanStyle(
                        color = MaterialTheme.colorScheme.primary,
                        textDecoration = TextDecoration.Underline,
                    ),
                )
                withLink(LinkAnnotation.Url("https://discord.gg/pDdKfrdHY6", linkStyles)) {
                    append("Discord")
                }
                append("  ")
                withLink(LinkAnnotation.Url("https://github.com/kushagrasinghx/BitChord", linkStyles)) {
                    append("GitHub")
                }
                append("  ")
                withLink(LinkAnnotation.Url("https://bitchord.kushagrasingh.in", linkStyles)) {
                    append("Website")
                }
                append("\\nby Kushagra Singh")
            },
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            textAlign = TextAlign.Center,
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = 24.dp, bottom = 8.dp),
        )
        }"""
    new_colophon = """        if (searchQuery.isBlank()) {
        Text(
            text = buildAnnotatedString {
                append("Sonium $version  ")
                val linkStyles = TextLinkStyles(
                    style = SpanStyle(
                        color = MaterialTheme.colorScheme.primary,
                        textDecoration = TextDecoration.Underline,
                    ),
                )
                withLink(LinkAnnotation.Url("https://github.com/achiilles75/BitChord", linkStyles)) {
                    append("GitHub")
                }
                append("\\n~YouTube Music & Listen Together Backend")
            },
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            textAlign = TextAlign.Center,
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = 24.dp, bottom = 8.dp),
        )
        }"""
    if old_colophon in sc:
        sc = sc.replace(old_colophon, new_colophon)
        with open(settings_path, "w", encoding="utf-8") as f:
            f.write(sc)
        print("SettingsSheet.kt colophon updated")
    else:
        print("Old colophon not found, doing generic replace")
        sc = sc.replace("BitChord $version", "Sonium $version")
        sc = sc.replace("https://discord.gg/pDdKfrdHY6", "https://github.com/achiilles75/BitChord")
        sc = sc.replace("https://github.com/kushagrasinghx/BitChord", "https://github.com/achiilles75/BitChord")
        with open(settings_path, "w", encoding="utf-8") as f:
            f.write(sc)

# 2. Patch strings.xml (values)
strings_en = "app/src/main/res/values/strings.xml"
if os.path.exists(strings_en):
    with open(strings_en, "r", encoding="utf-8") as f:
        se = f.read()
    se = se.replace('<string name="app_name">BitChord</string>', '<string name="app_name">Sonium</string>')
    se = se.replace('BitChord', 'Sonium')
    se = se.replace('bitchord', 'sonium')
    with open(strings_en, "w", encoding="utf-8") as f:
        f.write(se)
    print("values/strings.xml updated to Sonium")

# 3. Patch strings.xml (values-pt)
strings_pt = "app/src/main/res/values-pt/strings.xml"
if os.path.exists(strings_pt):
    with open(strings_pt, "r", encoding="utf-8") as f:
        spt = f.read()
    spt = spt.replace('<string name="app_name">BitChord</string>', '<string name="app_name">Sonium</string>')
    spt = spt.replace('BitChord', 'Sonium')
    spt = spt.replace('bitchord', 'sonium')
    with open(strings_pt, "w", encoding="utf-8") as f:
        f.write(spt)
    print("values-pt/strings.xml updated to Sonium")

# 4. Patch AndroidManifest.xml
manifest_path = "app/src/main/AndroidManifest.xml"
if os.path.exists(manifest_path):
    with open(manifest_path, "r", encoding="utf-8") as f:
        m = f.read()
    m = m.replace('android:scheme="bitchord"', 'android:scheme="sonium"')
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write(m)
    print("AndroidManifest.xml scheme updated")

print("All branding patches completed!")
