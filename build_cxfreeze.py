# build_cxfreeze.py
from pathlib import Path
from cx_Freeze import setup, Executable

ROOT = Path(__file__).parent

# Detectar entry-point (ajusta si tu principal es otro)
ENTRY = None
for candidate in ("app.py", "main.py"):
    if (ROOT / candidate).exists():
        ENTRY = candidate
        break
if not ENTRY:
    raise SystemExit("No encontré app.py ni main.py en la raíz del proyecto.")

# Archivos/carpetas a incluir junto al exe
include_files = []
for d in ("assets", "templates", "static"):
    p = ROOT / d
    if p.exists():
        include_files.append((str(p), d))
# Plantilla suelta en raíz
if (ROOT / "MODELO 2.pdf").exists():
    include_files.append(("MODELO 2.pdf", "templates/MODELO 2.pdf"))

build_exe_options = {
    # incluir ecosistema Flask explícitamente
    "packages": [
        "flask", "jinja2", "werkzeug", "itsdangerous", "click", "markupsafe",
        # si usás tkinter además:
        "tkinter",
        # si usás OCR:
        "reportlab", "openpyxl", "PyPDF2", "fitz", "pytesseract", "pdf2image",
        "qrcode", "dotenv",
    ],
    "include_files": include_files,
    # Incluir runtime de VC++ por si falta en el server
    "include_msvcr": True,
}

# Sin consola (cambiá a "Console" si querés ver prints)
base = "Win32GUI"

NAME = "RecibosDigitales"

setup(
    name=NAME,
    version="0.0.0",
    description="Recibos Digitales",
    options={"build_exe": build_exe_options},
    executables=[Executable(
        ENTRY,
        base=base,
        target_name=f"{NAME}.exe",
        icon=str(ROOT / "assets" / "tucumind.ico") if (ROOT / "assets" / "tucumind.ico").exists() else None
    )],
)
