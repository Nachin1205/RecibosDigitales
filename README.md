# Sistema de Recibos Digitales (TUCUMIND)

Generación de **recibos en PDF** con QR de validación, firma (PNG), numeración **centralizada** y autocompletado de clientes.  
Optimizado para Windows, ejecutable con PyInstaller y almacenamiento en carpeta compartida o local.

---

## ✨ Características
- 📄 PDF con **plantilla** (MODELO 2), **firma** y **QR**.
- 🔢 **Numeración** `PV-XXXXXXXX` persistida en `contador_recibos.json` (sin duplicados; sincroniza con PDFs existentes).
- 💳 **Múltiples formas de pago** con tabla **autoajustable** al espacio disponible.
- 🧾 “En concepto de” con **ajuste inteligente** (tamaño/interlínea) para **entrar siempre en 1 página**.
- 👤 **Autocompletado de clientes** (SQLite), con normalización de CUIT y búsqueda tolerante.
- 🗂️ **Rutas centralizadas** por variables de entorno (server o local).

---

## 🧱 Requisitos
- Windows 10/11  
- **Python 3.11** instalado (MS Store o python.org)

Paquetes Python:
- `reportlab`, `PyPDF2`, `pillow`, `qrcode[pil]`, `flask`
- **Opcional**: `num2words` (el código es tolerante si no está)

---

## 📦 Assets incluidos
- `assets/MODELO 2.pdf` → plantilla base del recibo  
- `assets/firma.png` → firma digital (PNG con transparencia)  
- `assets/tucumind.ico` → ícono del ejecutable  

> Si reemplazás firma/plantilla, mantené los mismos nombres o actualizá rutas en `config.py`.

---

## ⚙️ Configuración de rutas (server vs. local)

El proyecto usa variables de entorno:

- `RECIBOS_ROOT` → raíz de datos  
  - En oficina: `M:\Recibos`  
  - En casa (o si no existe `M:`): `C:\RecibosLocal`
- `BASE_QR_URL` → URL base de validación del QR  
  - En local: `http://127.0.0.1:5000/recibo`

**Ejemplo (PowerShell) – Local:**
```powershell
$env:RECIBOS_ROOT = "C:\RecibosLocal"
$env:BASE_QR_URL  = "http://127.0.0.1:5000/recibo"
```
La app crea y usa:

kotlin
Copiar código
{RECIBOS_ROOT}\data\recibos\   ← PDFs
{RECIBOS_ROOT}\data\db\        ← contador_recibos.json y clientes.db
{RECIBOS_ROOT}\data\logs\      ← logs
Si copiás PDFs históricos a data\recibos\, el contador se sincroniza para continuar donde ibas.

🚀 Instalación rápida (una vez)
powershell
Copiar código
python -m pip install --upgrade pip
python -m pip install reportlab PyPDF2 pillow "qrcode[pil]" flask
# opcional:
# python -m pip install num2words
▶️ Ejecutar desde código
powershell
Copiar código
# Parado en la carpeta del repo
$env:RECIBOS_ROOT = "C:\RecibosLocal"
$env:BASE_QR_URL  = "http://127.0.0.1:5000/recibo"

python .\main.py
La GUI levanta y el validador QR corre en http://127.0.0.1:5000 (para los QR de los PDFs).

🏗️ Build de ejecutable (PyInstaller)
powershell
Copiar código
python -m pip install pyinstaller

python -m PyInstaller main.py `
  --name Recibos `
  --noconsole `
  --clean --noconfirm `
  --add-data "assets;assets" `
  --icon "assets\tucumind.ico"
El build queda en dist\Recibos\.

Para usarlo en el server, copiá la carpeta dist\Recibos\ a una ruta accesible por todos y asegurate de que RECIBOS_ROOT apunte a M:\Recibos.

Nota: usá la variante en una sola línea si tu PowerShell no soporta backticks:

powershell
Copiar código
python -m PyInstaller main.py --name Recibos --noconsole --clean --noconfirm --add-data "assets;assets" --icon "assets\tucumind.ico"
🧠 Tips de uso
El número de recibo se sugiere solo (leer contador/PDFs) y se incrementa al generar el PDF.

Autocompletado:

Aprende al generar o con el botón “Guardar cliente”.

Busca por CUIT (solo dígitos) o por nombre (LIKE %texto%, sin importar mayúsculas).

“Forma de pago” y “En concepto de” se ajustan (tamaño/interlínea) para no desbordar y mantener 1 página.

🧰 Solución de problemas
ModuleNotFoundError: instalá el paquete faltante, ej.:

powershell
Copiar código
python -m pip install reportlab
No existe M: en casa: definí RECIBOS_ROOT="C:\RecibosLocal".

El QR no abre: verificá BASE_QR_URL (http://127.0.0.1:5000/recibo en local).

El .exe tarda en abrir: normal en primer arranque (carga DLLs). Recomendado disco local.
```powershell
📁 Estructura del repo
arduino
Copiar código
RecibosDigitales/
├─ assets/
│  ├─ MODELO 2.pdf
│  ├─ firma.png
│  └─ tucumind.ico
├─ interfaz/
│  ├─ nueva.py
│  ├─ buscar_editar.py   (WIP)
│  └─ anular.py          (WIP)
├─ utils/
│  ├─ pdf_generator.py
│  ├─ qr_utils.py
│  ├─ contador.py
│  ├─ clientes.py
│  └─ helpers.py
├─ config.py
├─ main.py
└─ README.md
```
🗺️ Roadmap (WIP)
 Pestaña Editar/Buscar

 Configuración UI para firma/logo/plantilla

🔒 Licencia
Privado – uso interno TUCUMIND.
