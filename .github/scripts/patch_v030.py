from pathlib import Path
import re

# Runs after patch_v020.py so the previous version cannot overwrite 0.4.0.
gradle_path = Path("app/build.gradle.kts")
gradle = gradle_path.read_text(encoding="utf-8")
gradle, name_count = re.subn(r'versionName\s*=\s*"[^"]+"', 'versionName = "0.4.0"', gradle)
if name_count != 1:
    raise RuntimeError(f"Expected one versionName, found {name_count}")
gradle, code_count = re.subn(r'versionCode\s*=\s*\d+', 'versionCode = 29', gradle)
if code_count != 1:
    raise RuntimeError(f"Expected one versionCode, found {code_count}")

models_path = Path("shared/src/commonMain/kotlin/com/music/bitchord/data/model/Models.kt")
models = models_path.read_text(encoding="utf-8")
pattern = r'(enum class SearchFilter\(val label: String, val params: String\?\)\s*\{)(.*?)(\n\})'
match = re.search(pattern, models, flags=re.DOTALL)
if match is None:
    raise RuntimeError("SearchFilter declaration not found")
body = match.group(2)
labels = {
    "ALL": "Tudo",
    "SONGS": "Músicas",
    "VIDEOS": "Vídeos",
    "ALBUMS": "Álbuns",
    "ARTISTS": "Artistas",
    "PLAYLISTS": "Playlists",
}
for key, label in labels.items():
    entry_pattern = rf'(\b{key}\(")[^"]+("\s*,)'
    body, count = re.subn(entry_pattern, lambda m: m.group(1) + label + m.group(2), body)
    if count != 1:
        raise RuntimeError(f"Expected one label for {key}, found {count}")
# The replacement touches display labels only; API params and enum names stay intact.
old_params = re.findall(r'\b(?:ALL|SONGS|VIDEOS|ALBUMS|ARTISTS|PLAYLISTS)\("[^"]+",\s*(null|"[^"]+")\)', match.group(2))
new_params = re.findall(r'\b(?:ALL|SONGS|VIDEOS|ALBUMS|ARTISTS|PLAYLISTS)\("[^"]+",\s*(null|"[^"]+")\)', body)
if len(new_params) != 6 or new_params != old_params:
    raise RuntimeError("SearchFilter API parameters changed")
models = models[:match.start(2)] + body + models[match.end(2):]
for key, label in labels.items():
    if f'{key}("{label}",' not in models:
        raise RuntimeError(f"Translated label missing: {key}")
# Write only after every precondition and validation has passed.
gradle_path.write_text(gradle, encoding="utf-8")
models_path.write_text(models, encoding="utf-8")
print("Validated Sonium 0.4.0 (versionCode 29): Tudo, Músicas, Vídeos, Álbuns, Artistas, Playlists")
