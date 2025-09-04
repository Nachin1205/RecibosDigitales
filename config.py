# config.py
import os, sys
from pathlib import Path

# Raíz compartida en el servidor (podés sobreescribir con RECIBOS_ROOT)
def _pick_root():
    # 1) si definís RECIBOS_ROOT, se usa eso
    env = os.getenv("RECIBOS_ROOT")
    if env:
        return Path(env)

    # 2) si existe la M:, usarla; si no, caer a C:\RecibosLocal
    m = Path(r"M:\Recibos")
    m_drive = Path(m.drive + "\\") if m.drive else None
    if m_drive and m_drive.exists():
        return m
    return Path(r"C:\RecibosLocal")

SERVER_ROOT = _pick_root()
DATA_DIR    = SERVER_ROOT / "data"
RECIBOS_DIR = DATA_DIR / "recibos"
DB_DIR      = DATA_DIR / "db"
LOGS_DIR    = DATA_DIR / "logs"

# Donde se guardan los PDFs
SALIDA_DIR = RECIBOS_DIR

# Contador centralizado
CONTADOR_PATH = DB_DIR / "contador_recibos.json"

# Assets (junto al .exe / código)
def _app_dir():
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent

APP_DIR = _app_dir()
ASSETS_DIR = APP_DIR / "assets"

# Firma / logo
LOGO_PATH = None
FIRMA_ENABLED = True
FIRMA_PATH_DEFAULT = str(ASSETS_DIR / "firma.png")
FIRMA_WIDTH_MM, FIRMA_X_MM, FIRMA_Y_MM = 42, 150, 28

# QR
QR_ERROR_CORRECTION, QR_BOX_SIZE, QR_BORDER, QR_TARGET_SIZE_MM = "L", 10, 2, 45
QR_X_MM, QR_Y_MM = 18, 22
BASE_QR_URL  = os.getenv("BASE_QR_URL", "http://192.168.1.80:5000/recibo")
QR_SECRET_KEY = os.getenv("QR_SECRET_KEY", "solo-para-pruebas-locales-cambiar")
FLASK_DEBUG   = os.getenv("FLASK_DEBUG", "1") == "1"

# Tabla forma de pago
FP_MAX_ROWS = 6
FP_OVERFLOW_MODE = "resumen"

# Asegurar estructura de datos
for d in (RECIBOS_DIR, DB_DIR, LOGS_DIR):
    d.mkdir(parents=True, exist_ok=True)
