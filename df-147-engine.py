
# K16: Concurrent-Spawn-Mutex (fcntl-based, Trinity-CONSERVATIVE 2026-05-17)
def k16_lock_or_exit(df_name: str):
    """Acquire exclusive lock or exit(3). Prevents concurrent DF runs."""
    import fcntl, os, sys
    lock_path = f"/tmp/df-trinity-{df_name}.lock"
    fd = os.open(lock_path, os.O_CREAT | os.O_WRONLY)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return fd
    except BlockingIOError:
        sys.exit(3)


# K13: External-Anchor-Mock-RFC3161 (Trinity-CONSERVATIVE 2026-05-17)
def k13_anchor(payload_hash: str) -> dict:
    """Mock RFC3161-style timestamp anchor."""
    from datetime import datetime, timezone
    return {
        "anchor_type": "rfc3161-mock",
        "iso_ts": datetime.now(timezone.utc).isoformat(),
        "payload_hash": payload_hash,
    }


# K12: HMAC-SHA256-Provenance (Trinity-CONSERVATIVE 2026-05-17)
def k12_provenance(payload: bytes, key: bytes = b"df-trinity-conservative-v1") -> dict:
    """Returns payload_hash + HMAC-SHA256 signature."""
    import hashlib, hmac
    return {
        "payload_hash": hashlib.sha256(payload).hexdigest(),
        "hmac_sha256": hmac.new(key, payload, hashlib.sha256).hexdigest(),
    }

"""DF-147 tracker engine for 9dots-Customer-Success-NPS."""

import re
import os
import json
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from datetime import datetime, timezone

DF_DIR = Path(__file__).parent
LOCK_DIR = Path("/tmp/df-147.lock")
DF_ID = "147"
DECISION_KEYWORDS_REGEX = re.compile(
    r"\b(entscheid[a-z]*|empfehl(?:e|en|t|st)|sollt(?:e|en|est)|recommend[a-z]*|decid[a-z]*|advis[a-z]*|propos[a-z]*)\b",
    re.IGNORECASE,
)

_LOCK_IDENTITY = f"{os.getpid()}:{time.time_ns()}"


@dataclass
class TrackerOutput:
    welle: str = "25"
    df: str = "DF-147"
    iso_timestamp: str = ""
    source: str = "mock"
    nps_avg: float = 0
    promoters_pct: float = 0
    detractors_pct: float = 0
    customer_health_distribution: dict = field(default_factory=dict)
    churn_risk_customers: list = field(default_factory=list)


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _file_stable(path, min_age_sec=300) -> bool:
    p = Path(path)
    if not p.exists() or not p.is_file():
        return False
    try:
        stat = p.stat()
    except OSError:
        return False
    return (time.time() - stat.st_mtime) >= min_age_sec


def acquire_lock_with_identity() -> bool:
    stale_after_sec = 6 * 60 * 60
    now = time.time()

    try:
        LOCK_DIR.mkdir(mode=0o700)
        (LOCK_DIR / "identity").write_text(_LOCK_IDENTITY, encoding="utf-8")
        return True
    except FileExistsError:
        pass
    except OSError:
        return False

    try:
        age = now - LOCK_DIR.stat().st_mtime
    except OSError:
        return False

    if age < stale_after_sec:
        return False

    try:
        for child in LOCK_DIR.iterdir():
            if child.is_file() or child.is_symlink():
                child.unlink()
            elif child.is_dir():
                return False
        LOCK_DIR.rmdir()
        LOCK_DIR.mkdir(mode=0o700)
        (LOCK_DIR / "identity").write_text(_LOCK_IDENTITY, encoding="utf-8")
        return True
    except (FileExistsError, OSError):
        return False


def release_lock() -> None:
    try:
        identity_file = LOCK_DIR / "identity"
        if identity_file.exists():
            identity = identity_file.read_text(encoding="utf-8").strip()
            if identity != _LOCK_IDENTITY:
                return
            identity_file.unlink()
        LOCK_DIR.rmdir()
    except OSError:
        return


def k17_pre_action_verification(anchors) -> dict:
    missing = []
    for anchor in anchors or []:
        if isinstance(anchor, Path):
            exists = anchor.exists()
            name = str(anchor)
        else:
            name = str(anchor)
            exists = bool(os.getenv(name)) if name.startswith("ENV:") else Path(name).exists()
        if not exists:
            missing.append(name)

    return {
        "ok": not missing,
        "missing_anchors": missing,
        "env_tag": os.getenv("DF_147_ENV_TAG", "local"),
    }


def _is_real_api_enabled() -> bool:
    raw = os.getenv("DF_147_REAL_API_ENABLED", "false").strip().lower()
    return raw in {"1", "true", "yes", "y", "on"}


def scan_output_for_decision_keywords(text) -> list:
    if text is None:
        return []
    return sorted({match.group(0) for match in DECISION_KEYWORDS_REGEX.finditer(str(text))})


def assert_no_decision_keywords(output) -> None:
    hits = scan_output_for_decision_keywords(output)
    if hits:
        raise ValueError(f"Q_0/K_0 blocked terms detected: {', '.join(hits)}")


def _float_from_payload(payload, key, default=0.0) -> float:
    try:
        return float(payload.get(key, default))
    except (TypeError, ValueError):
        return float(default)


def _dict_from_payload(payload, key) -> dict:
    value = payload.get(key, {})
    return value if isinstance(value, dict) else {}


def _list_from_payload(payload, key) -> list:
    value = payload.get(key, [])
    return value if isinstance(value, list) else []


def _load_env_payload() -> dict:
    raw = os.getenv("DF_147_INPUT_JSON", "").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def collect_tracker_output() -> TrackerOutput:
    output = TrackerOutput(iso_timestamp=iso_now())

    if not _is_real_api_enabled():
        output.customer_health_distribution = {
            "green": 0,
            "yellow": 0,
            "red": 0,
        }
        output.churn_risk_customers = []
        return output

    payload = _load_env_payload()
    output.source = "real_api_env"
    output.nps_avg = _float_from_payload(payload, "nps_avg")
    output.promoters_pct = _float_from_payload(payload, "promoters_pct")
    output.detractors_pct = _float_from_payload(payload, "detractors_pct")
    output.customer_health_distribution = _dict_from_payload(
        payload, "customer_health_distribution"
    )
    output.churn_risk_customers = _list_from_payload(payload, "churn_risk_customers")
    return output


def _report_path() -> Path:
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return DF_DIR / "reports" / f"df-147-{date}.json"


def _write_report(payload: dict) -> None:
    reports_dir = DF_DIR / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    report_json = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    assert_no_decision_keywords(report_json)
    _report_path().write_text(report_json + "\n", encoding="utf-8")


def main() -> int:
    if not acquire_lock_with_identity():
        return 3

    try:
        anchors = [DF_DIR]
        pav = k17_pre_action_verification(anchors)
        if not pav.get("ok"):
            return 3

        tracker_output = collect_tracker_output()
        payload = asdict(tracker_output)
        payload["df_id"] = DF_ID
        payload["k17_pre_action_verification"] = pav
        _write_report(payload)
        return 0
    except Exception as exc:
        sys.stderr.write(f"DF-147 failed: {exc}\n")
        return 3
    finally:
        release_lock()


if __name__ == "__main__":
    sys.exit(main())