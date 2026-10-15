import os
import re
import xml.etree.ElementTree as ET

# 1. Patch SettingsSheet.kt
settings_path = "app/src/main/java/com/music/bitchord/ui/screens/SettingsSheet.kt"
if os.path.exists(settings_path):
    with open(settings_path, "r", encoding="utf-8") as f:
        sc = f.read()
    sc = sc.replace('subtitle = "Music/BitChord".takeIf { exportDownloads },', 'subtitle = "Music/Sonium".takeIf { exportDownloads },')
    
    # Substituir colophon do rodapé
    old_colophon_pattern = re.compile(r'if \(searchQuery\.isBlank\(\)\) \{\s*Text\(\s*text = buildAnnotatedString \{.*?\n\s*append\("\\n~YouTube Music & Listen Together Backend"\)\s*\},', re.DOTALL)
    new_colophon = r'''if (searchQuery.isBlank()) {
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
                append("\n~YouTube Music & Listen Together Backend")
            },'''
    if old_colophon_pattern.search(sc):
        sc = old_colophon_pattern.sub(lambda m: new_colophon, sc)
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

# 3. Patch strings files for branding and essential identifiers
strings_files = [
    "app/src/main/res/values/strings.xml",
    "app/src/main/res/values-pt/strings.xml",
    "app/src/main/res/values-pt-rBR/strings.xml",
    "sharedUi/src/commonMain/composeResources/values-pt-rBR/strings.xml",
    "sharedUi/src/commonMain/composeResources/values-pt/strings.xml",
]

for strings_file in strings_files:
    if os.path.exists(strings_file):
        with open(strings_file, "r", encoding="utf-8") as f:
            content = f.read()
        content = replace_tag_text(content)
        
        # Ensure default values/strings.xml has all necessary base resource IDs
        if strings_file == "app/src/main/res/values/strings.xml":
            base_extra = """
    <string name="portuguese_pt">Portuguese (Portugal)</string>
    <string name="portuguese_br">Portuguese (Brazil)</string>
    <string name="spatial_audio_bluetooth_only">Enable only on Bluetooth headphones</string>
    <string name="spatial_audio_bluetooth_only_subtitle">Automatically turns spatial audio on when connecting wireless headphones and off when disconnected</string>
    <string name="ai_lyrics_translation">AI lyric translation</string>
    <string name="ai_lyrics_translation_subtitle">Translates and adapts lyrics while preserving poetic rhythm and natural rhymes for the app language</string>
    <string name="ai_lyrics_api_key">AI Translation API key</string>
    <string name="ai_lyrics_api_key_hint">Paste your API key</string>
    <string name="lyrics_offset_description">Positive values show lyrics later</string>
</resources>"""
            if "portuguese_br" not in content:
                content = content.replace("</resources>", base_extra)
        
        # Ensure values-pt/strings.xml differentiates PT-PT and PT-BR
        if strings_file == "app/src/main/res/values-pt/strings.xml":
            pt_extra = """
    <string name="portuguese">Português (Portugal)</string>
    <string name="portuguese_pt">Português (Portugal)</string>
    <string name="portuguese_br">Português (Brasil)</string>
    <string name="spatial_audio_bluetooth_only">Ativar apenas com auscultadores Bluetooth</string>
    <string name="spatial_audio_bluetooth_only_subtitle">Ativa o áudio espacial automaticamente ao ligar auscultadores sem fios e desativa ao desligar</string>
    <string name="ai_lyrics_translation">Tradução de letras por IA</string>
    <string name="ai_lyrics_translation_subtitle">Traduz e adapta mantendo o ritmo poético e rimas naturais para o idioma da aplicação</string>
    <string name="ai_lyrics_api_key">Chave de API de Tradução IA</string>
    <string name="ai_lyrics_api_key_hint">Cole a sua chave de API</string>
    <string name="lyrics_offset_description">Valores positivos mostram as letras mais tarde</string>
</resources>"""
            if "portuguese_pt" not in content:
                content = content.replace("</resources>", pt_extra)
            content = content.replace('<string name="portuguese">Português</string>', '<string name="portuguese">Português (Portugal)</string>')
            content = content.replace('<string name="prefer_music_only">Prefer music-only version</string>', '<string name="prefer_music_only">Preferir versão só de música</string>')
            content = content.replace('<string name="prefer_music_only_subtitle">For music videos, show the video details while finding and loading the catalogue audio version</string>', '<string name="prefer_music_only_subtitle">Para vídeos musicais, reproduz automaticamente a versão áudio oficial</string>')

        with open(strings_file, "w", encoding="utf-8") as f:
            f.write(content)
        ET.parse(strings_file)
        print(f"Updated and validated {strings_file}")

print("All branding patches completed successfully!")
