from __future__ import annotations
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from app.utils.paths import app_dir

@dataclass
class AppSettings:
    messages_per_load: int = 50
    density: str = "comfortable"
    block_remote_images: bool = True
    confirm_delete: bool = True
    open_last_selected_account: bool = True
    last_selected_account: str = ""
    auto_refresh: bool = True
    brand_email_color: str = "#F1F5F9"
    brand_reader_color: str = "#629CFF"

class SettingsService:
    def __init__(self):
        self.path = app_dir() / "data" / "settings.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> AppSettings:
        if not self.path.exists():
            return AppSettings()
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            defaults = asdict(AppSettings())
            defaults.update({k: v for k, v in raw.items() if k in defaults})
            return AppSettings(**defaults)
        except Exception:
            return AppSettings()

    def save(self, settings: AppSettings) -> None:
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(asdict(settings), ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.path)
