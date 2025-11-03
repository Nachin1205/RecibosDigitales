# config.py
import os, sys
from pathlib import Path
import platform

# Raíz compartida en el servidor (podés sobreescribir con RECIBOS_ROOT)
def _pick_root():
    # 1) si definís RECIBOS_ROOT, se usa eso (aplica también en Docker)
    env = os.getenv("RECIBOS_ROOT")
    if env:
        return Path(env)

    # 2) Si estamos en Windows, usar M: si existe; si no, C:\RecibosLocal
    if os.name == "nt":
        m = Path(r"M:\Recibos")
        m_drive = Path(m.drive + "\\") if m.drive else None
        if m_drive and m_drive.exists():
            return m
        return Path(r"C:\RecibosLocal")

    # 3) En entornos no-Windows (p.ej. Docker Linux), usar /data por defecto
    return Path(os.getenv("RECIBOS_ROOT_DEFAULT", "/data"))

SERVER_ROOT = _pick_root()
DATA_DIR    = SERVER_ROOT / "data"
RECIBOS_DIR = DATA_DIR / "recibos"
DB_DIR      = DATA_DIR / "db"
LOGS_DIR    = DATA_DIR / "logs"

# Donde se guardan los PDFs
SALIDA_DIR = RECIBOS_DIR

# Contador centralizado
CONTADOR_PATH = DB_DIR / "contador_recibos.json"

# Historial de recibos (Excel) centralizado junto a la DB para que
# sea estable tanto en .py como en ejecutable empaquetado. Los
# módulos que lo usan hacen `from config import HISTORIAL_XLSX`.
# Para máxima compatibilidad con tu flujo actual, guardamos el Excel
# junto al código (carpeta 'historial' dentro de la app), de modo que
# sea el mismo archivo que ya venías usando.
HISTORIAL_XLSX = Path(__file__).resolve().parent / "historial" / "recibos.xlsx"

# Assets (junto al .exe / código)
def app_dir() -> Path:
    # PyInstaller one-file (extrae a carpeta temporal)
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)

    # Ejecutables "congelados": cx_Freeze (y PyInstaller one-dir)
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent

    # Ejecución normal (desde el código fuente)
    return Path(__file__).resolve().parent

APP_DIR = app_dir()
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

# Validador (host/puerto parametrizables; útil para Docker)
VALIDATOR_HOST = os.getenv("VALIDATOR_HOST", "127.0.0.1")
try:
    VALIDATOR_PORT = int(os.getenv("VALIDATOR_PORT", "5000"))
except Exception:
    VALIDATOR_PORT = 5000

# Tabla forma de pago
FP_MAX_ROWS = 6
FP_OVERFLOW_MODE = "resumen"

# Asegurar estructura de datos
for d in (RECIBOS_DIR, DB_DIR, LOGS_DIR):
    d.mkdir(parents=True, exist_ok=True)
