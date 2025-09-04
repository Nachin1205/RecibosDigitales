# interfaz/anular.py
import io
import re
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

from config import SALIDA_DIR, LOGO_PATH, FIRMA_PATH_DEFAULT  # SALIDA_DIR debe existir en config.py
from utils.recibo_utils import marcar_anulado

PATRON_NUM_COMPLETO = re.compile(r"^\d{4}-\d{8}$")  # 0001-00000001

def crear_pestana_anular(tabs):
    frame = ttk.Frame(tabs)
    tabs.add(frame, text="🗑️ Anular")

    ttk.Label(frame, text="Buscar (número o nombre parcial)").grid(row=0, column=0, sticky="e", padx=4, pady=4)
    ent_buscar = ttk.Entry(frame, width=32)
    ent_buscar.grid(row=0, column=1, sticky="w", padx=4, pady=4)
    ttk.Button(frame, text="Buscar", command=lambda: _buscar(ent_buscar.get(), lista)).grid(row=0, column=2, padx=6)

    ttk.Label(frame, text="Coincidencias en /recibos").grid(row=1, column=0, columnspan=3, sticky="w", padx=4)
    lista = tk.Listbox(frame, width=90, height=10)
    lista.grid(row=2, column=0, columnspan=3, padx=4, pady=6, sticky="we")

    ttk.Button(frame, text="Anular seleccionado", command=lambda: _anular_seleccion(lista)).grid(row=3, column=0, columnspan=3, pady=10)

def _buscar(texto, lista):
    lista.delete(0, tk.END)
    q = (texto or "").strip().lower()
    pdfs = sorted(Path(SALIDA_DIR).glob("Recibo_*.pdf"))
    encontrados = [p for p in pdfs if q in p.name.lower()]
    if not encontrados:
        messagebox.showinfo("Sin resultados", "No se encontraron PDFs que coincidan.")
        return
    for p in encontrados:
        lista.insert(tk.END, p.name)

def _anular_seleccion(lista):
    if not lista.curselection():
        messagebox.showerror("Atención", "Seleccioná un PDF de la lista.")
        return
    nombre = lista.get(lista.curselection()[0])
    origen = Path(SALIDA_DIR) / nombre

    # Intentar extraer número (para el historial)
    m = re.search(r"Recibo_(\d{4}-\d{8})__", nombre)
    numero = m.group(1) if m else ""

    # Generar archivo de salida
    destino = origen.with_name(reemplazar_por_anulado(origen.name))

    try:
        _crear_pdf_anulado(origen, destino)
    except Exception as e:
        messagebox.showerror("Error al anular", str(e))
        return

    try:
        origen.unlink(missing_ok=True)  # eliminar el original
    except Exception:
        pass

    if numero:
        try:
            marcar_anulado(numero)
        except Exception:
            pass

    messagebox.showinfo("Listo", f"Se creó: {destino.name}")

def reemplazar_por_anulado(nombre: str) -> str:
    # Recibo_0001-00000001__Cliente.pdf -> Recibo_0001-00000001__ANULADO.pdf
    return re.sub(r"__.*?\.pdf$", "__ANULADO.pdf", nombre, flags=re.IGNORECASE)

def _crear_pdf_anulado(origen: Path, destino: Path):
    """Superpone sello 'ANULADO' en todas las páginas del PDF origen y guarda en destino."""
    # Marca de agua en memoria (A4, centrada)
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=A4)
    w, h = A4
    c.setFont("Helvetica-Bold", 120)
    try:
        c.setFillAlpha(0.30)
    except Exception:
        pass
    c.setFillColorRGB(0.85, 0, 0)
    c.translate(w/2, h/2)
    c.rotate(30)
    c.drawCentredString(0, 0, "ANULADO")
    c.save()
    packet.seek(0)

    marca = PdfReader(packet)
    reader = PdfReader(str(origen))
    writer = PdfWriter()

    for page in reader.pages:
        # Superponer (asume A4; si trabajás con otros tamaños, habría que calcular escala/posición)
        page.merge_page(marca.pages[0])
        writer.add_page(page)

    with open(destino, "wb") as f:
        writer.write(f)
