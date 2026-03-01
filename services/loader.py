import json
from pathlib import Path

RACK_MAP_FILE = Path(__file__).parent.parent / "rack_map.json"

def load_rack_map():
    try:
        with open(RACK_MAP_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        raise RuntimeError("rack_map.json file not found")
    except json.JSONDecodeError:
        raise RuntimeError("Invalid JSON in rack_map.json")