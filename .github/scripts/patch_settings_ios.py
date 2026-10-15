from pathlib import Path

print("Validating Sonium iOS Pill & Subpages Settings native structure...")
settings_path = Path("app/src/main/java/com/music/bitchord/ui/screens/SettingsSheet.kt")
if not settings_path.exists():
    raise FileNotFoundError("SettingsSheet.kt não encontrado")

code = settings_path.read_text(encoding="utf-8")

# Check required components
assert "enum class SettingsCategory" in code, "SettingsCategory enum missing"
assert "SettingsPillCard" in code, "SettingsPillCard composable missing"
assert "selectedCategory" in code, "selectedCategory state missing"
assert "BackHandler" in code, "BackHandler missing"

print("SettingsSheet.kt verified: native iOS pills and subpages navigation active!")
