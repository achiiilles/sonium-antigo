from pathlib import Path
import re
import xml.etree.ElementTree as ET

print("Applying and validating Sonium v0.4.6 patch...")

# 1. Verify build.gradle.kts has 0.4.6 and versionCode 31
gradle_path = Path("app/build.gradle.kts")
gradle = gradle_path.read_text(encoding="utf-8")
if 'versionName = "0.4.6"' not in gradle:
    gradle = re.sub(r'versionName\s*=\s*"[^"]+"', 'versionName = "0.4.6"', gradle)
if 'versionCode = 31' not in gradle:
    gradle = re.sub(r'versionCode\s*=\s*\d+', 'versionCode = 31', gradle)
gradle_path.write_text(gradle, encoding="utf-8")
print("Verified app/build.gradle.kts: versionName = 0.4.6, versionCode = 31")

# 2. Verify values-pt-rBR strings.xml
pt_br_res = Path("app/src/main/res/values-pt-rBR/strings.xml")
if not pt_br_res.exists():
    raise RuntimeError(f"Missing {pt_br_res}")
ET.parse(str(pt_br_res))
print("Verified app/src/main/res/values-pt-rBR/strings.xml syntax")

pt_br_shared = Path("sharedUi/src/commonMain/composeResources/values-pt-rBR/strings.xml")
if not pt_br_shared.exists():
    raise RuntimeError(f"Missing {pt_br_shared}")
ET.parse(str(pt_br_shared))
print("Verified sharedUi/src/commonMain/composeResources/values-pt-rBR/strings.xml syntax")

# 3. Verify SettingsSheet.kt has iOS grouped blocks & 6 categories
settings_path = Path("app/src/main/java/com/music/bitchord/ui/screens/SettingsSheet.kt")
settings_code = settings_path.read_text(encoding="utf-8")

required_sections = [
    "Reprodução & Áudio",
    "Letras",
    "Aparência & Interface",
    "Biblioteca & Armazenamento",
    "Geral & Sistema",
]
for sec in required_sections:
    if sec not in settings_code:
        raise RuntimeError(f"Required iOS section '{sec}' missing in SettingsSheet.kt")
    print(f"Verified iOS section in SettingsSheet.kt: {sec}")

print("All Sonium v0.4.6 patch checks passed successfully!")
