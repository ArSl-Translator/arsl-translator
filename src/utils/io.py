import json
import os
from typing import Any

def ensure_dir(path: str) -> None:
os.makedirs(path, exist_ok=True)

def write_json(path: str, data: Any) -> None:
ensure_dir(os.path.dirname(path))
with open(path, "w", encoding="utf-8") as f:
json.dump(data, f, ensure_ascii=False, indent=2)

def read_env_default(name: str, default: str) -> str:
return os.environ.get(name, default)
