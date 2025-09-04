from pathlib import Path
from openpyxl import load_workbook, Workbook

# Intentamos tomar la ruta del historial desde config.py; si no existe, usamos una por defecto
try:
    from config import HISTORIAL_XLSX  # ej: Path("historial/recibos.xlsx")
except Exception:
    HISTORIAL_XLSX = Path("historial/recibos.xlsx")

def _asegurar_historial():
    """Crea el archivo de historial si no existe, con las columnas estándar."""
    p = Path(HISTORIAL_XLSX)
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        wb = Workbook()
        ws = wb.active
        ws.title = "Recibos"
        ws.append(["Número", "Cliente", "Fecha", "Subtotal", "Total", "Estado"])
        wb.save(p)
def posible_duplicado(cliente: str, fecha: str, total: float) -> bool:
    """
    True si ya hay una fila con el mismo (cliente, fecha, total).
    """
    _asegurar_historial()
    wb = load_workbook(HISTORIAL_XLSX)
    ws = wb.active
    cli_norm = (cliente or "").strip().lower()
    for row in ws.iter_rows(min_row=2, values_only=True):
        _num, _cli, _fec, _sub, _tot, _est = row
        try:
            tot_val = float(str(_tot).replace(",", "."))
        except Exception:
            tot_val = None
        if (str(_fec) == fecha
            and (str(_cli or "").strip().lower() == cli_norm)
            and tot_val is not None
            and abs(tot_val - float(total)) < 0.01):
            return True
    return False

def marcar_anulado(numero: str):
    """
    Marca como 'Anulado' el recibo con ese número en el historial.
    Si no existe, agrega una fila nueva con Estado = 'Anulado'.
    """
    _asegurar_historial()
    wb = load_workbook(HISTORIAL_XLSX)
    ws = wb.active

    encontrado = False
    for row in ws.iter_rows(min_row=2):
        if str(row[0].value) == str(numero):
            # Columna 6 = 'Estado' (índice 5)
            row[5].value = "Anulado"
            encontrado = True
            break

    if not encontrado:
        # Si no estaba en el historial, lo agregamos como anulado
        ws.append([numero, "", "", "", "", "Anulado"])

    wb.save(HISTORIAL_XLSX)
