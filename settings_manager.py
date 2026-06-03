import json
from pathlib import Path
from typing import Dict

from rapid_rag.utils import mkdir, read_yaml


CONFIG_PATH = "rapid_rag/config.yaml"


def _get_settings_path() -> Path:
    config = read_yaml(CONFIG_PATH)
    settings_path = Path(config.get("settings_path", "data/settings/app_config.json"))
    mkdir(settings_path.parent)
    return settings_path


def get_default_settings() -> Dict:
    config = read_yaml(CONFIG_PATH)
    return {
        "site_title": config.get("title", "School Rules QA System"),
        "bot_name": "校规助手",
        "bot_avatar": "",
        "welcome_message": "请输入你想咨询的学校制度问题。",
        "admin_password": "admin123",
    }


def load_settings() -> Dict:
    settings_path = _get_settings_path()
    if not settings_path.exists():
        settings = get_default_settings()
        save_settings(settings)
        return settings
    return json.loads(settings_path.read_text(encoding="utf-8"))


def save_settings(settings: Dict) -> None:
    settings_path = _get_settings_path()
    settings_path.write_text(
        json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8"
    )
