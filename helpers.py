import os
import time
import json

QUEUE_FILE = "data/entries.json"

def format_time_ago(timestamp: int) -> str:
    now = int(time.time())
    diff = now - timestamp

    if diff < 60:
        return f"{diff} seconds ago"
    elif diff < 3600:
        minutes = diff // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif diff < 86400:
        hours = diff // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    else:
        days = diff // 86400
        return f"{days} day{'s' if days != 1 else ''} ago"

def create_data_directory() -> None:
    if not os.path.exists("data"):
        os.makedirs("data")

def create_logs_directory() -> None:
    logs_path = "data/logs"
    if not os.path.exists(logs_path):
        os.makedirs(logs_path)

def set_last_checked() -> None:
    with open("data/last_checked.txt", "w", encoding="utf-8") as handle:
        handle.write(str(int(time.time())))

def get_last_checked() -> int:
    try:
        with open("data/last_checked.txt", "r", encoding="utf-8") as handle:
            return int(handle.read().strip())
    except (FileNotFoundError, ValueError):
        return 0


def _write_queue(entries: list[dict]) -> None:
    with open(QUEUE_FILE, "w", encoding="utf-8") as handle:
        json.dump(entries, handle, ensure_ascii=False, indent=2)


def _read_legacy_line_entries() -> list[dict]:
    entries = []
    with open(QUEUE_FILE, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
                if isinstance(parsed, dict):
                    entries.append(parsed)
            except json.JSONDecodeError:
                continue
    return entries
    
def add_entry(label: str, path: str, skip: bool = False, url: str = "") -> None:
    entry = {
        "label": label,
        "path": path,
        "skip": skip,
        "url": url
    }
    entries = read_entries()
    entries.append(entry)
    _write_queue(entries)

def edit_entry(index: int, label: str, path: str, skip: bool = False, url: str = "") -> None:
    entries = read_entries()
    if 0 <= index < len(entries):
        entries[index] = {
            "label": label,
            "path": path,
            "skip": skip,
            "url": url
        }
        _write_queue(entries)

def delete_entry(index: int) -> None:
    entries = read_entries()
    if 0 <= index < len(entries):
        del entries[index]
        _write_queue(entries)


def clear_entries() -> None:
    _write_queue([])
        
def read_entries() -> list:
    if not os.path.exists(QUEUE_FILE):
        return []

    try:
        with open(QUEUE_FILE, "r", encoding="utf-8") as handle:
            data = json.load(handle)
            if isinstance(data, list):
                return [entry for entry in data if isinstance(entry, dict)]
            return []
    except json.JSONDecodeError:
        legacy_entries = _read_legacy_line_entries()
        _write_queue(legacy_entries)
        return legacy_entries

def read_config() -> dict:
    config_path = "data/config.json"
    if not os.path.exists(config_path):
        return {}
    try:
        with open(config_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
            if isinstance(data, dict):
                return data
            return {}
    except json.JSONDecodeError:
        return {}
    
def write_config(config: dict) -> None:
    config_path = "data/config.json"
    with open(config_path, "w", encoding="utf-8") as handle:
        json.dump(config, handle, ensure_ascii=False, indent=2)