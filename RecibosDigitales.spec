# RecibosDigitales.spec — generado automáticamente
from PyInstaller.utils.hooks import collect_submodules

hidden = []
hidden += collect_submodules('openpyxl')
hidden += collect_submodules('reportlab')
hidden += collect_submodules('PyPDF2')
hidden += collect_submodules('fitz')
hidden += collect_submodules('pytesseract')
hidden += collect_submodules('pdf2image')

datas = [

]

block_cipher = None

a = Analysis(
    ['RecibosDigitales/main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='RecibosDigitales',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='assets/tucumind.ico'
)

coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=True, upx_exclude=[],
    name='RecibosDigitales'
)
