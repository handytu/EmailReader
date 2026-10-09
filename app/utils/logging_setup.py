from __future__ import annotations
import logging
from pathlib import Path

SENSITIVE_WORDS = ("password", "passwd", "refresh_token", "access_token", "authorization")

class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        text = record.getMessage().lower()
        if any(k in text for k in SENSITIVE_WORDS):
            record.msg = "Sensitive authentication detail suppressed"
            record.args = ()
        return True

def setup_logging(base_dir: Path) -> None:
    log_dir = base_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_dir / "app.log", encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    handler.addFilter(RedactingFilter())
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(handler)
