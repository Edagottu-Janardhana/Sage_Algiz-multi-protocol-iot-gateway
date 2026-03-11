import json
import os

CONFIG_FILE = "/home/rpi4/Documents/Sage_Algiz/config.json"

def has_sequence():
    if not os.path.exists(CONFIG_FILE):
        return False

    try:
        with open(CONFIG_FILE, "r") as f:
            cfg = json.load(f)
        return "seq_no" in cfg
    except Exception:
        return False


def save_config(seq_no, role):
    cfg = {
        "seq_no": seq_no,
        "role": role
    }

    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)

    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)