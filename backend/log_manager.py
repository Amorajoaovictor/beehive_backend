# backend/log_manager.py
import re
import os
import json
from datetime import datetime
from typing import Dict, Any

RAW_LOG_DIR = os.getenv("RAW_LOG_DIR", os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")), "raw_logs"))

CLASSIFICATION_RULES = [
    (r"(?i)sql injection|union select|select .*from", "sql_injection"),
    (r"(?i)failed password|brute force|authentication failure|invalid user", "brute_force"),
    (r"(?i)wget|curl|download|fetch", "file_download"),
    (r"(?i)scanner|nmap|port scan|scan detected", "port_scan"),
    (r"(?i)command executed|command|shell", "command_executed"),
    (r"(?i)login attempt|login malic|login", "login_attempt"),
]

def classify_log(message: str, default: str = "other") -> str:
    if not message:
        return default
    for rx, label in CLASSIFICATION_RULES:
        if re.search(rx, message):
            return label
    return default

def ensure_raw_dir():
    os.makedirs(RAW_LOG_DIR, exist_ok=True)

def save_raw_log(payload: Dict[str, Any]) -> str:
    ensure_raw_dir()
    date = datetime.utcnow().strftime("%Y-%m-%d")
    path = os.path.join(RAW_LOG_DIR, f"{date}.json")
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"received_at": datetime.utcnow().isoformat(), "payload": payload}, ensure_ascii=False) + "\n")
        return path
    except Exception:
        return "error save_raw_log"

def validate_payload(payload: Dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise ValueError("Payload must be a JSON object")
    required = ["honeypot_id", "ip_address"]
    for r in required:
        if r not in payload:
            raise ValueError(f"Missing required field: {r}")
    if "honeypot_id" in payload:
        try:
            int(payload["honeypot_id"])
        except Exception:
            raise ValueError("honeypot_id must be an integer")

def process_log(payload: Dict[str, Any], commit: bool = True) -> Dict[str, Any]:
    from backend import app as _backend_pkg
    from backend.app import app as flask_app, db, Log, Honeypot

    validate_payload(payload)

    honeypot_id = int(payload["honeypot_id"])
    ip_address = str(payload["ip_address"])
    raw_event_type = (payload.get("event_type") or "").strip()
    details = (payload.get("details") or "").strip()

    with flask_app.app_context():
        honeypot = Honeypot.query.get(honeypot_id)
        if not honeypot:
            raise ValueError("Honeypot not found")

        # Classify
        if raw_event_type:
            event_type = raw_event_type
        else:
            event_type = classify_log(details, default="other")

        try:
            log = Log(
                honeypot_id=honeypot_id,
                ip_address=ip_address,
                event_type=event_type,
                details=details
            )
            db.session.add(log)
            if commit:
                db.session.commit()
            else:
                db.session.flush()
            return log.to_dict()
        except Exception as e:
            try:
                save_raw_log(payload)
            except Exception:
                pass
            db.session.rollback()
            raise


def process_log_safe(payload: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return process_log(payload)
    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError(str(e))
