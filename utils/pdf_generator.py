from pathlib import Path
from io import BytesIO
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, Frame
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from xml.sax.saxutils import escape
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader, simpleSplit
import re
from PyPDF2 import PdfReader, PdfWriter
from pathlib import Path
from config import ASSETS_DIR  # ⬅️ usar ruta robusta a assets en .py y .exe
# ----------------------------------------------------------------------
# Layout (coordenadas y estilos)
# ----------------------------------------------------------------------
POS = {
    "logo":           (20*mm, 265*mm),   # posición del logo en mm desde abajo-izq
    "logo_w":         28*mm,
    "logo_h":         28*mm,
    "titulo_recibo":  (20*mm, 245*mm),
    "nro_recibo":     (200*mm, 245*mm),

    "cliente":        (20*mm, 238*mm),
    "domicilio":      (20*mm, 230*mm),
    "localidad":      (20*mm, 222*mm),
    "cuit":           (20*mm, 214*mm),
    "iva":            (20*mm, 206*mm),

    "leyenda":        (20*mm, 194*mm),
    "monto_letras":   (20*mm, 188*mm),

    "concepto_t":     (20*mm, 176*mm),
    "concepto":       (20*mm, 170*mm),

    "ret_t":          (20*mm, 150*mm),
    "ret_col_x":      [20*mm, 70*mm, 120*mm, 170*mm],
    "ret_y":          144*mm,

    # Totales en la columna derecha
    "ret_total":      (200*mm, 134*mm),
    "subtotal":       (200*mm, 130*mm),
    "total":          (200*mm, 120*mm),

    "fp_t":           (20*mm, 108*mm),
    "fp_y":           102*mm,
    "fp_cells_x":     [20*mm, 68*mm, 116*mm, 150*mm, 180*mm],

    # Firma (label + box)
    "firma_lbl":      (20*mm, 38*mm),
    "firma_box":      (20*mm, 15*mm),
    "firma_box_w":    60*mm,
    "firma_box_h":    20*mm,

    # QR (posición y tamaño)
    "qr":             (160*mm, 15*mm),
    "qr_size":        35*mm,   
}
# Caja donde va el texto de "En concepto de" (coordenadas en mm desde el borde inferior/izquierdo)
CONCEPTO_X_MM        = 18     # margen izquierdo
CONCEPTO_Y_MM        = 102    # **altura del borde inferior** de la caja (ajustá según tu modelo)
CONCEPTO_W_MM        = 175    # ancho útil del bloque
CONCEPTO_H_MM        = 38     # alto útil (subí/bajá para más/menos renglones)

# Estilo del párrafo
CONCEPTO_FONT        = "Helvetica"
CONCEPTO_FONT_SIZE   = 10     # si no entra, abajo lo reducimos a 9/8 automáticamente
CONCEPTO_LEADING     = 12     # interlineado (pt)

FONTS = {
    "title": ("Helvetica-Bold", 16),
    "h1":    ("Helvetica-Bold", 11),
    "text":  ("Helvetica", 10),
    "small": ("Helvetica", 8),
}

COLORS = {
    "primary": colors.HexColor("#002060"),
    "text":    colors.black,
    "muted":   colors.HexColor("#5A5A5A"),
    "stamp":   colors.HexColor("#D7263D"),
}
# Ancho máximo para envolver el “monto en letras”
MONTO_LETRAS_MAX_W = 170*mm  
MONTO_LETRAS_LINE_SPACING = 2  

# ----------------------------------------------------------------------
# Utilidades
# ----------------------------------------------------------------------
def _fmt_money(v) -> str:
    try:
        return f"${float(v):,.2f}"
    except Exception:
        return "$0.00"

def _numero_a_letras(n: int) -> str:
    """Convierte un entero en palabras en castellano (hasta millones)."""
    unidades = [
        "", "uno", "dos", "tres", "cuatro", "cinco", "seis",
        "siete", "ocho", "nueve", "diez", "once", "doce",
        "trece", "catorce", "quince", "dieciséis", "diecisiete",
        "dieciocho", "diecinueve", "veinte"
    ]
    decenas = [
        "", "", "veinte", "treinta", "cuarenta", "cincuenta",
        "sesenta", "setenta", "ochenta", "noventa"
    ]
    centenas = [
        "", "ciento", "doscientos", "trescientos", "cuatrocientos",
        "quinientos", "seiscientos", "setecientos", "ochocientos",
        "novecientos"
    ]

    if n == 0:
        return "cero"
    if n == 100:
        return "cien"
    if n <= 20:
        return unidades[n]
    if n < 100:
        d, u = divmod(n, 10)
        return decenas[d] + ("" if u == 0 else " y " + unidades[u])
    if n < 1000:
        c, r = divmod(n, 100)
        return centenas[c] + ("" if r == 0 else " " + _numero_a_letras(r))
    if n < 1_000_000:
        m, r = divmod(n, 1000)
        pref = "mil" if m == 1 else _numero_a_letras(m) + " mil"
        return pref + ("" if r == 0 else " " + _numero_a_letras(r))
    if n < 1_000_000_000:
        m, r = divmod(n, 1_000_000)
        pref = "un millón" if m == 1 else _numero_a_letras(m) + " millones"
        return pref + ("" if r == 0 else " " + _numero_a_letras(r))
    if n < 1_000_000_000_000:
        g, r = divmod(n, 1_000_000_000)
        pref = "mil millones" if g == 1 else _numero_a_letras(g) + " mil millones"
        return pref + ("" if r == 0 else " " + _numero_a_letras(r))
    return str(n)

def _peso_en_letras(monto: float) -> str:
    entero = int(monto)
    cent = int(round((monto - entero) * 100))
    letras = _numero_a_letras(entero).upper()
    return f"{letras} PESOS CON {cent:02d}/100"

def _draw_right(c, x, y, txt, font=("Helvetica",10), color=colors.black):
    name, size = font
    c.setFont(name, size); c.setFillColor(color)
    w = c.stringWidth(txt, name, size)
    c.drawString(x - w, y, txt)
#-----------Normaliza strings con coma/punto a float (acepta '1.234,56', '1,234.56', etc.).-----------------------
def _to_num(x):
    """Normaliza strings con coma/punto a float sin alterar enteros."""
    if x is None:
        return 0.0
    if isinstance(x, (int, float)):
        return float(x)
    
    s = str(x).strip()
    if not s:
        return 0.0

    # Detectar si es un número entero (solo dígitos)
    if s.isdigit():
        return float(s)

    # Caso con coma decimal y sin punto
    if "," in s and "." not in s:
        s = s.replace(".", "").replace(",", ".")
    # Caso con coma y punto: decidir cuál es el decimal
    elif "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    else:
        s = s.replace(",", "")
    try:
        return float(s)
    except Exception:
        return 0.0

# --- QR helper ------------------------------------------------
def _build_qr_png_bytes(qr_data: str) -> bytes | None:
    if not qr_data:
        return None
    try:
        import qrcode
        from qrcode.constants import ERROR_CORRECT_L
    except Exception:
        print("[AVISO] Falta instalar qrcode: pip install qrcode[pil]")
        return None

    qr = qrcode.QRCode(
        version=None,                 # elige versión mínima
        error_correction=ERROR_CORRECT_L,  # menos denso
        box_size=10,                  # módulos grandes
        border=2,                     # borde (2–3)
    )
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    bio = BytesIO()
    img.save(bio, format="PNG")
    return bio.getvalue()

# ----------------------------------------------------------------------
# Overlay: todo lo que va por encima del template (texto, QR, firma)
# ----------------------------------------------------------------------
def _make_overlay_page(
    datos: dict,
    logo_path: Path | None,
    firma_path: Path | None,
    anulado: bool,
    qr_data: str | None
):
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)

    # --- Logo (si existe) ---
    if logo_path and Path(logo_path).exists():
        img = ImageReader(str(logo_path))
        c.drawImage(img, POS["logo"][0], POS["logo"][1],
            width=POS["logo_w"], height=POS["logo_h"], mask='auto')

    # --- Título y cabecera ---
    c.setFont(*FONTS["title"]); c.setFillColor(COLORS["primary"])
    c.drawString(*POS["titulo_recibo"], "RECIBO")
    _draw_right(c, *POS["nro_recibo"], f"Nº {datos.get('numero_recibo','')}", FONTS["h1"], COLORS["text"])
    _draw_right(c, POS["nro_recibo"][0], POS["nro_recibo"][1]-12, f"Fecha: {datos.get('fecha','')}", FONTS["text"], COLORS["text"])

    # --- Datos del cliente ---
    c.setFont(*FONTS["h1"]); c.setFillColor(COLORS["text"])
    c.drawString(*POS["cliente"],   f"Cliente:   {datos.get('cliente','')}")
    c.drawString(*POS["domicilio"], f"Domicilio: {datos.get('domicilio','')}")
    c.drawString(*POS["localidad"], f"Localidad: {datos.get('localidad','')}")
    c.drawString(*POS["cuit"],      f"CUIT:      {datos.get('cuit','')}")
    c.drawString(*POS["iva"],       f"Condición IVA: {datos.get('iva','')}")

    # --- Monto en letras (usando SUBTOTAL) ---
    subtotal_val = _to_num(datos.get("subtotal", 0.0))
    total_val    = _to_num(datos.get("total", 0.0))

    c.setFont(*FONTS["h1"]); c.setFillColor(COLORS["text"])
    c.drawString(*POS["leyenda"], "Recibimos la suma de pesos:")

    # Texto a mostrar (cambiá a total_val si querés el TOTAL en letras)
    letras_txt = _peso_en_letras(total_val)

    # Envolver el texto al ancho disponible
    font_name, font_size = FONTS["text"]
    c.setFont(font_name, font_size); c.setFillColor(COLORS["text"])

    x_letras, y_letras = POS["monto_letras"]
    wrapped_lines = simpleSplit(letras_txt, font_name, font_size, MONTO_LETRAS_MAX_W)

    # Dibujar hasta 3 líneas (caben sin pisar "En concepto de:")
    max_lines = 3
    for i, line in enumerate(wrapped_lines[:max_lines]):
        y_line = y_letras - i * (font_size + MONTO_LETRAS_LINE_SPACING)
        c.drawString(x_letras, y_line, line)


    # --- Concepto ---
    c.setFont(*FONTS["h1"]); c.setFillColor(COLORS["text"])
    c.drawString(*POS["concepto_t"], "En concepto de:")

    # Geometría: usar casi todo el alto entre título y "Retenciones"
    x       = POS["concepto"][0]
    top     = POS["concepto_t"][1] - 1*mm     # ↓ achicamos margen superior
    ret_y   = POS["ret_t"][1]
    gap     = 2 * mm                           # ↓ margen inferior mínimo
    bottom  = ret_y + gap
    w       = 175 * mm                         # ↔ ajustá si te da aire
    h_avail = max(8*mm, top - bottom)

    # Texto → HTML simple
    concepto_raw  = (datos.get("concepto") or "").strip()
    concepto_html = escape(concepto_raw).replace("\n", "<br/>")

    # Estilo base
    BASE_SIZE = FONTS["text"][1]  # normalmente 10
    style = ParagraphStyle(
        "Concepto",
        fontName = FONTS["text"][0],
        fontSize = BASE_SIZE,
        leading  = BASE_SIZE + 1,  # interlineado ajustado
        alignment= TA_LEFT,
        spaceBefore=0, spaceAfter=0,  # sin márgenes extra
    )

    def _measure(par: Paragraph, W, Hmax=10_000*mm):
        """Devuelve alto necesario (pt) para renderizar par a ancho W (sin dibujar)."""
        _, h_need = par.wrap(W, Hmax)
        return h_need

    def _make_par(sz: float, lead_factor: float) -> Paragraph:
        style.fontSize = sz
        # leading mínimo: igual al tamaño; con factor 1.02–1.15 vamos soltando
        style.leading  = max(sz, round(sz * lead_factor, 2))
        return Paragraph(concepto_html, style)

    # 1) probamos con tamaño base y leading 1.12
    p = _make_par(BASE_SIZE, 1.12)
    h_need = _measure(p, w)

    # 2) si no entra, bajamos tamaño de a 0.25 pt hasta 6.0,
    #    y para cada tamaño compactamos leading: 1.15→1.12→1.08→1.05→1.03→1.02→1.00
    if h_need > h_avail:
        fitted = None
        for sz in [BASE_SIZE - 0.25*i for i in range(int((BASE_SIZE-6.0)/0.25)+1)] + [6.0]:
            for lf in (1.15, 1.12, 1.08, 1.05, 1.03, 1.02, 1.00):
                cand = _make_par(sz, lf)
                if _measure(cand, w) <= h_avail:
                    fitted = cand
                    break
            if fitted:
                break
        p = fitted or _make_par(6.0, 1.00)  # último recurso: 6pt con leading = 6pt

    # 3) dibujamos una sola vez
    frame = Frame(
        x, bottom, w, h_avail,
        leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0,
        showBoundary=0  # poné 1 para debug
    )
    frame.addFromList([p], c)

    # --- Retenciones ---
    c.setFont(*FONTS["h1"]); c.setFillColor(COLORS["text"])
    c.drawString(*POS["ret_t"], "Retenciones")

    c.setFont(*FONTS["small"]); c.setFillColor(COLORS["muted"])
    rets = datos.get("retenciones", {}) or {}
    labels = [
        ("Ganancias", rets.get("Ganancias", 0.0)),
        ("SUSS",      rets.get("SUSS", 0.0)),
        ("TEM",       rets.get("TEM", 0.0)),
        ("IIBB",      rets.get("IIBB", 0.0)),
    ]
    for i, (k, v) in enumerate(labels):
        xi = POS["ret_col_x"][i]; yi = POS["ret_y"]
        c.drawString(xi, yi, k)
        c.setFont(*FONTS["text"]); c.setFillColor(COLORS["text"])
        c.drawString(xi, yi - (FONTS["text"][1] + 2), _fmt_money(v))
        c.setFont(*FONTS["small"]); c.setFillColor(COLORS["muted"])

    # --- Total Retenciones (derecha) ---
    ret_total = sum(_to_num(v) for _, v in labels)
    _draw_right(c, *POS["ret_total"], f"Total Ret.: {_fmt_money(ret_total)}",
        FONTS.get("h1", FONTS["text"]), COLORS["text"])

    # --- Subtotal / Total ---
  #  _draw_right(c, *POS["subtotal"], f"Subtotal: {_fmt_money(subtotal_val)}",
   #     FONTS["text"], COLORS["text"])
    _draw_right(c, *POS["total"],    f"Total: {_fmt_money(total_val)}",
        FONTS["h1"], COLORS["primary"])

    # --- Forma de pago (ajuste automático para que SIEMPRE entre en 1 página) ---
    from config import FP_MAX_ROWS, FP_OVERFLOW_MODE
    
    c.setFont(*FONTS["h1"]); c.setFillColor(COLORS["text"])
    c.drawString(*POS["fp_t"], "Forma de pago")

    HEAD_FONT   = FONTS["small"]   # encabezados
    HEAD_COLOR  = COLORS["muted"]
    CELL_COLOR  = COLORS["text"]
    COLS_X      = POS["fp_cells_x"]           # [Tipo, Número, C/Banco, Fecha, Importe]
    HEADER_GAP  = HEAD_FONT[1] + 2            # separación entre encabezado y primera fila

    # Normalizar a lista
    fps = datos.get("forma_pago") or []
    if isinstance(fps, dict):
        fps = [fps]
    elif not isinstance(fps, list):
        fps = []

    # Dibujar encabezados
    c.setFont(*HEAD_FONT); c.setFillColor(HEAD_COLOR)
    headers = ["Tipo", "Número", "C/Banco", "Fecha", "Importe"]
    for i, htxt in enumerate(headers):
        c.drawString(COLS_X[i], POS["fp_y"], htxt)

    # Cálculo del alto disponible (desde primera fila hasta encima de firma/QR)
    y_start = POS["fp_y"] - HEADER_GAP  # primera fila
    bottom_limit = max(
        POS["firma_box"][1] + POS["firma_box_h"],
        POS["qr"][1]        + POS["qr_size"],
    ) + 3*mm  # margen de seguridad inferior
    avail_h = max(12*mm, y_start - bottom_limit)

    n = len(fps)
    datos["_fp_overflow"] = []  # anulamos overflow para no usar 2ª página ni "+N más…"

    if n > 0:
        # Buscar combinación (tamaño, gap) que permita n filas dentro de avail_h
        base_sz = float(FONTS["text"][1])  # normalmente 10
        best = None
        sizes = [round(base_sz - 0.25*i, 2) for i in range(int((base_sz - 6.0)/0.25) + 1)] + [6.0]
        gaps  = [4, 3, 2, 1]  # espacio extra por fila

        for sz in sizes:
            for gap in gaps:
                row_h = sz + gap
                need_h = n * row_h
                if need_h <= (avail_h / (1.0)) * 72 / 25.4:  # convertir mm→pt de forma implícita
                    best = (sz, gap)
                    break
            if best:
                break

        # Si no encontró (caso extremo), usar el mínimo: 6pt y gap=1
        if best is None:
            best = (6.0, 1)

        cell_sz, row_gap = best
        row_h = cell_sz + row_gap

        # Limitar textos según el tamaño escogido (más chico → más caracteres posibles)
        scale = cell_sz / base_sz if base_sz else 1.0
        lim_tipo   = max(8,  int(12 * scale))
        lim_num    = max(10, int(16 * scale))
        lim_banco  = max(10, int(18 * scale))
        lim_fecha  = max(8,  int(12 * scale))

        def _short(txt: str, n: int) -> str:
            s = str(txt or "")
            return s if len(s) <= n else (s[:max(0, n-1)] + "…")

        def _money(v) -> str:
            try:
                return f"${float(v):,.2f}"
            except Exception:
                return "$0.00"

        # Dibujar filas comprimidas
        c.setFont(FONTS["text"][0], cell_sz); c.setFillColor(CELL_COLOR)
        y = y_start
        for fp in fps:
            tipo   = _short(fp.get("tipo",""),   lim_tipo)
            numero = _short(fp.get("numero",""), lim_num)
            banco  = _short(fp.get("banco",""),  lim_banco)
            fecha  = _short(fp.get("fecha",""),  lim_fecha)
            imp    = _money(fp.get("importe") or 0.0)

            c.drawString(COLS_X[0], y, tipo)
            c.drawString(COLS_X[1], y, numero)
            c.drawString(COLS_X[2], y, banco)
            c.drawString(COLS_X[3], y, fecha)
            c.drawString(COLS_X[4], y, imp)  # izquierdo (si querés a la derecha, puedo pasarlo con _draw_right y ancho fijo)
            y -= row_h


    # --- Firma (encima del box, escala > 1) ---
    c.setFont(*FONTS["text"]); c.setFillColor(COLORS["muted"])
    c.drawString(*POS["firma_lbl"], "Firma y aclaración:")
   # c.rect(POS["firma_box"][0], POS["firma_box"][1], POS["firma_box_w"], POS["firma_box_h"], stroke=1, fill=0)
    if firma_path and Path(firma_path).exists():
        img = ImageReader(str(firma_path))
        escala = 1.1  # 10% más grande que el box
        w = (POS["firma_box_w"] - 4*mm) * escala
        h = (POS["firma_box_h"] - 4*mm) * escala
        x = POS["firma_box"][0] + 2*mm
        y = POS["firma_box"][1] + 2*mm
        c.drawImage(img, x, y, width=w, height=h, mask='auto')

    # --- QR (menos denso) ---
    if qr_data:
        png = _build_qr_png_bytes(qr_data)
        if png:
            img_qr = ImageReader(BytesIO(png))
            c.drawImage(img_qr,
                POS["qr"][0], POS["qr"][1],
                width=POS["qr_size"], height=POS["qr_size"],
                preserveAspectRatio=True, mask='auto')

    # --- Sello ANULADO (opcional) ---
    if anulado:
        c.saveState()
        c.setFont("Helvetica-Bold", 58)
        c.setFillColor(COLORS["stamp"])
        page_w, page_h = A4
        c.translate(page_w/2, page_h/2)
        c.rotate(25)
        c.drawCentredString(0, 0, "ANULADO")
        c.restoreState()

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()


# ----------------------------------------------------------------------
# Página extra con overflow de formas de pago (si se usa)
# ----------------------------------------------------------------------
def _make_fp_overflow_page(fps_rest: list) -> bytes:
    """
    Genera una página extra solo para mostrar formas de pago adicionales.
    Se mergea sobre el mismo template.
    """
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)

    # Título de continuación
    c.setFont(*FONTS["title"]); c.setFillColor(COLORS["primary"])
    c.drawString(20*mm, 260*mm, "Detalle de pagos (continuación)")

    # Encabezados
    headers = ["Tipo", "Número", "C/Banco", "Fecha", "Importe"]
    COLS_X  = [20*mm, 68*mm, 116*mm, 150*mm, 180*mm]
    START_Y = 246*mm
    ROW_H   = FONTS["text"][1] + 6

    c.setFont(*FONTS["small"]); c.setFillColor(COLORS["muted"])
    for i, h in enumerate(headers):
        c.drawString(COLS_X[i], START_Y, h)

    def _short(txt: str, n: int) -> str:
        s = str(txt or "")
        return s if len(s) <= n else (s[:n-1] + "…")

    def _money(v) -> str:
        try:
            return f"${float(v):,.2f}"
        except Exception:
            return "$0.00"

    # Filas (llenamos la página hasta ~40 filas seguras)
    y = START_Y - (FONTS["small"][1] + 2)
    MAX_ROWS_PAGE = 40
    c.setFont(*FONTS["text"]); c.setFillColor(COLORS["text"])

    for idx, fp in enumerate(fps_rest[:MAX_ROWS_PAGE]):
        tipo   = _short(fp.get("tipo",""),   16)
        numero = _short(fp.get("numero",""), 22)
        banco  = _short(fp.get("banco",""),  24)
        fecha  = _short(fp.get("fecha",""),  12)
        imp    = _money(fp.get("importe") or 0.0)

        c.drawString(COLS_X[0], y, tipo)
        c.drawString(COLS_X[1], y, numero)
        c.drawString(COLS_X[2], y, banco)
        c.drawString(COLS_X[3], y, fecha)
        c.drawString(COLS_X[4], y, imp)
        y -= ROW_H

        if idx == MAX_ROWS_PAGE - 1 and len(fps_rest) > MAX_ROWS_PAGE:
            c.setFont(*FONTS["small"]); c.setFillColor(COLORS["muted"])
            c.drawString(COLS_X[0], y + ROW_H/4, f"+{len(fps_rest)-MAX_ROWS_PAGE} más…")
            break

    c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()


# ----------------------------------------------------------------------
# Generación final: merge overlay + template
# ----------------------------------------------------------------------
def generar_pdf(
    datos: dict,
    ruta_salida: Path | str,
    logo_path: Path | str | None = None,
    firma_path: Path | str | None = None,
    anulado: bool = False,
    qr_data: str | None = None,
    template_pdf: Path | str | None = None,
):
    from config import FP_OVERFLOW_MODE

    # Normalizar rutas
    ruta_salida = Path(ruta_salida)
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)

    # Defaults robustos (sirven en .py y .exe)
    tpl_path = Path(template_pdf) if template_pdf else (ASSETS_DIR / "MODELO 2.pdf")
    firm_path = Path(firma_path) if firma_path else (ASSETS_DIR / "firma.png")

    if not tpl_path.exists():
        raise FileNotFoundError(f"Plantilla no encontrada: {tpl_path.resolve()}")

    # Página 1 (overlay)
    overlay_bytes = _make_overlay_page(
        datos=datos,
        logo_path=logo_path,
        firma_path=str(firm_path),  # por si tu overlay espera str
        anulado=anulado,
        qr_data=qr_data,
    )

    reader_tpl = PdfReader(str(tpl_path))
    writer = PdfWriter()

    # Merge página 1
    base_page_1 = reader_tpl.pages[0]
    overlay_page_1 = PdfReader(BytesIO(overlay_bytes)).pages[0]
    try:
        base_page_1.merge_page(overlay_page_1)
    except Exception:
        base_page_1.mergePage(overlay_page_1)
    writer.add_page(base_page_1)

    # ¿Segunda página por overflow?
    fps_rest = datos.get("_fp_overflow") or []
    if FP_OVERFLOW_MODE == "segunda_pagina" and fps_rest:
        overlay2 = _make_fp_overflow_page(fps_rest)
        base_page_2 = reader_tpl.pages[0]  # mismo template
        overlay_page_2 = PdfReader(BytesIO(overlay2)).pages[0]
        try:
            base_page_2.merge_page(overlay_page_2)
        except Exception:
            base_page_2.mergePage(overlay_page_2)
        writer.add_page(base_page_2)

    # Guardar
    with open(ruta_salida, "wb") as f:
        writer.write(f)
