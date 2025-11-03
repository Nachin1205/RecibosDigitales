from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import SALIDA_DIR, HISTORIAL_XLSX  # type: ignore
from utils.recibo_utils import upsert_historial_con_json  # type: ignore

try:
    from PyPDF2 import PdfReader
except Exception as e:  # pragma: no cover
    print("Falta PyPDF2 para leer PDFs:", e)
    sys.exit(1)


def _to_float(s: str) -> float:
    try:
        s = str(s).strip()
        if not s:
            return 0.0
        if s.isdigit():
            return float(s)
        if "," in s and "." not in s:
            s = s.replace(".", "").replace(",", ".")
        elif "," in s and "." in s:
            if s.rfind(",") > s.rfind("."):
                s = s.replace(".", "").replace(",", ".")
            else:
                s = s.replace(",", "")
        else:
            s = s.replace(",", "")
        return float(s)
    except Exception:
        return 0.0


def parse_pdf(p: Path) -> dict | None:
    reader = PdfReader(str(p))
    txt = "\n".join((pg.extract_text() or "") for pg in reader.pages)
    def find(pat, flags=0, default=""):
        m = re.search(pat, txt, flags)
        return m.group(1).strip() if m else default

    mnum = re.search(r"Recibo_(\d{4}-\d{8})__", p.name)
    numero = mnum.group(1) if mnum else ""

    fecha     = find(r"Fecha:\s*(\d{2}/\d{2}/\d{4})")
    cliente   = find(r"Cliente:\s*(.+)")
    domicilio = find(r"Domicilio:\s*(.+)")
    localidad = find(r"Localidad:\s*(.+)")
    cuit      = find(r"CUIT:\s*([\d\-\.\s]+)")
    iva       = find(r"Condici.?n\s+IVA:\s*(.+)")
    total_s   = find(r"Total:\s*\$?\s*([0-9\.,]+)")
    total_v   = _to_float(total_s)
    conc_m    = re.search(r"En concepto de:\s*(.*?)\s*Retenciones", txt, re.DOTALL)
    concepto  = conc_m.group(1).strip() if conc_m else ""

    if not numero:
        return None

    return {
        "numero_recibo": numero,
        "fecha": fecha,
        "cliente": cliente,
        "domicilio": domicilio,
        "localidad": localidad,
        "cuit": cuit,
        "iva": iva,
        "concepto": concepto,
        "retenciones": {"Ganancias": 0.0, "SUSS": 0.0, "TEM": 0.0, "IIBB": 0.0},
        "forma_pago": [],
        "total": total_v,
    }


def main():
    base = Path(SALIDA_DIR)
    pdfs = sorted(base.glob("Recibo_*__.pdf")) + sorted(base.glob("Recibo_*__*.pdf"))
    if not pdfs:
        print("No se encontraron PDFs en:", base)
        return
    n_ok, n_err = 0, 0
    for p in pdfs:
        try:
            datos = parse_pdf(p)
            if not datos:
                continue
            numero = datos["numero_recibo"]
            estado = "Anulado" if p.name.upper().endswith("__ANULADO.PDF") else ""
            upsert_historial_con_json(
                numero=numero,
                cliente=datos.get("cliente", ""),
                fecha=datos.get("fecha", ""),
                subtotal="",
                total=datos.get("total", 0.0),
                estado=estado,
                datos=datos,
            )
            n_ok += 1
        except Exception as e:  # pragma: no cover
            n_err += 1
            print("Error con", p.name, "->", e)
    print(f"Listo. Cargados {n_ok} PDF(s) en {HISTORIAL_XLSX}. Errores: {n_err}.")


if __name__ == "__main__":
    main()

