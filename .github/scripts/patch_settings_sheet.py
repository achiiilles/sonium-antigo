"""Validação auxiliar de configurações do Sonium (Pílulas e Subpáginas)."""
from pathlib import Path

def validate():
    settings_path = Path("app/src/main/java/com/music/bitchord/ui/screens/SettingsSheet.kt")
    if not settings_path.exists():
        raise FileNotFoundError("SettingsSheet.kt não encontrado")
    code = settings_path.read_text(encoding="utf-8")
    assert "SettingsCategory" in code or "GroupShape" in code, "Estrutura de configurações ausente"
    print("SettingsSheet.kt validado com sucesso.")

if __name__ == "__main__":
    validate()
