# utils/contador.py
from __future__ import annotations
from pathlib import Path
import json, os, time, re
from config import CONTADOR_PATH, SALIDA_DIR  # <- rutas centralizadas
import re, json
_PATRON = re.compile(r"(\d{4})-(\d{8})")

DEF_PUNTO_VENTA = "0001"
DEF_ULTIMO_NUM  = 0

def _scan_max_from_pdfs():
    mayor = 0; pv = "0001"
    for f in SALIDA_DIR.glob("*.pdf"):
        m = _PATRON.search(f.name)
        if m:
            pv = m.group(1); mayor = max(mayor, int(m.group(2)))
    return pv, mayor

def _init_if_missing():
    """Si no existe el JSON, lo crea tomando como base los PDFs ya guardados."""
    if not CONTADOR_PATH.exists():
        pv, mayor = _scan_max_from_pdfs()
        data = {"punto_venta": pv, "ultimo_numero": mayor}
        CONTADOR_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONTADOR_PATH.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

def _leer():
    if not CONTADOR_PATH.exists():
        pv, mayor = _scan_max_from_pdfs()
        data = {"punto_venta": pv, "ultimo_numero": mayor}
        CONTADOR_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONTADOR_PATH.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return data
    try:
        data = json.loads(CONTADOR_PATH.read_text(encoding="utf-8"))
    except Exception:
        data = {"punto_venta": "0001", "ultimo_numero": 0}
    pv_pdf, mayor_pdf = _scan_max_from_pdfs()
    if mayor_pdf > int(data.get("ultimo_numero", 0)):
        if pv_pdf: data["punto_venta"] = pv_pdf
        data["ultimo_numero"] = mayor_pdf
        _guardar(data)
    return data

def _guardar(data: dict) -> None:
    CONTADOR_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = CONTADOR_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    tmp.replace(CONTADOR_PATH)

def _zfill8(n: int) -> str:
    return str(n).zfill(8)

def _with_lock(func):
    """Lock por archivo: evita que dos procesos incrementen al mismo tiempo."""
    lock = CONTADOR_PATH.with_suffix(".lock")
    for _ in range(30):  # ~3s máximo
        try:
            fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            try:
                return func()
            finally:
                try:
                    os.remove(lock)
                except OSError:
                    pass
        except FileExistsError:
            time.sleep(0.1)
    # fallback si no se pudo bloquear
    return func()

def ver_numero_siguiente() -> str:
    """No incrementa; muestra el siguiente (preview)."""
    data = _leer()
    pv = str(data.get("punto_venta", DEF_PUNTO_VENTA)).zfill(4)
    siguiente = int(data.get("ultimo_numero", DEF_ULTIMO_NUM)) + 1
    return f"{pv}-{_zfill8(siguiente)}"

def incrementar_contador() -> str:
    """Incrementa y devuelve el nuevo número ya formateado (con lock)."""
    def _update():
        data = _leer()
        data["ultimo_numero"] = int(data.get("ultimo_numero", DEF_ULTIMO_NUM)) + 1
        _guardar(data)
        pv = str(data.get("punto_venta", DEF_PUNTO_VENTA)).zfill(4)
        return f"{pv}-{_zfill8(data['ultimo_numero'])}"
    return _with_lock(_update)

def set_punto_venta(nuevo_pv: str) -> None:
    """Cambia el PV; no toca el contador."""
    def _set():
        data = _leer()
        data["punto_venta"] = str(nuevo_pv).zfill(4)
        _guardar(data)
    _with_lock(_set)
