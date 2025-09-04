# utils/qr_utils.py
from __future__ import annotations
import base64, hashlib, hmac, json
from typing import Tuple, Any, Dict

def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

def _b64url_decode(s: str) -> bytes:
    padding = '=' * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + padding)

def _canonical_json(data: Dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def sign_payload_b64url(payload_b64url: str, secret_key: str) -> str:
    mac = hmac.new(secret_key.encode("utf-8"), payload_b64url.encode("utf-8"), hashlib.sha256).digest()
    return _b64url_encode(mac)

def build_qr_data(datos: Dict[str, Any], base_url: str, secret_key: str) -> str:
    payload_json = _canonical_json(datos)
    p = _b64url_encode(payload_json.encode("utf-8"))
    s = sign_payload_b64url(p, secret_key)
    sep = '&' if '?' in base_url else '?'
    return f"{base_url}{sep}p={p}&s={s}"

def verify_qr_params(p: str, s: str, secret_key: str) -> Tuple[bool, Dict[str, Any] | str]:
    try:
        expected = sign_payload_b64url(p, secret_key)
        if not hmac.compare_digest(expected, s):
            return False, "Firma inválida."
        raw = _b64url_decode(p)
        data = json.loads(raw.decode("utf-8"))
        return True, data
    except Exception as e:
        return False, f"Error de decodificación/verificación: {e}"
