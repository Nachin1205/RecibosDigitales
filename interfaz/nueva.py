# interfaz/nueva.py
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from utils.qr_utils import build_qr_data
from config import BASE_QR_URL, QR_SECRET_KEY, SALIDA_DIR, ASSETS_DIR
import re
from utils.clientes import init_db, buscar_por_nombre_o_cuit, upsert_cliente
from utils.helpers import validar_fecha_no_futura
from utils.recibo_utils import posible_duplicado
from utils.pdf_generator import generar_pdf
from utils.contador import ver_numero_siguiente, incrementar_contador

# Rutas/constantes 

LOGO_PATH = None
FIRMA_PATH = ASSETS_DIR / "firma.png"   # ✅ sirve en .py y en el .exe
# No definimos CARPETA_SALIDA: los PDFs van a SALIDA_DIR (servidor)

def crear_pestana_nueva(tabs: ttk.Notebook):
    frame = ttk.Frame(tabs)
    tabs.add(frame, text="🧾 Nuevo Recibo")

    # Base de clientes (para autocompletado)
    init_db()

    # ---- Entradas básicas ----
    campos = {}
    filas = [
        ("Número de recibo", "numero_recibo"),
        ("Fecha (DD/MM/AAAA)", "fecha"),
        ("Cliente", "cliente"),
        ("Domicilio", "domicilio"),
        ("Localidad", "localidad"),
        ("CUIT", "cuit"),
        ("Condición IVA", "iva"),
        ("Total ($)", "total"),
    ]
    for i, (label, key) in enumerate(filas):
        ttk.Label(frame, text=label).grid(row=i, column=0, sticky="e", padx=4, pady=2)
        entry = ttk.Entry(frame, width=40)
        entry.grid(row=i, column=1, sticky="w", padx=4, pady=2)
        campos[key] = entry

    # Número de recibo (preview)
    try:
        campos["numero_recibo"].insert(0, ver_numero_siguiente())
    except Exception:
        campos["numero_recibo"].insert(0, "0001-00000001")
    campos["numero_recibo"].config(state="readonly")

    # Concepto (multilínea)
    ttk.Label(frame, text="En concepto de").grid(row=8, column=0, sticky="ne", padx=4)
    concepto_text = tk.Text(frame, width=38, height=4)
    concepto_text.grid(row=8, column=1, sticky="w", padx=4, pady=2)

    # Retenciones
    ttk.Label(frame, text="Retenciones ($)").grid(row=9, column=0, sticky="ne", padx=4)
    ret_frame = ttk.Frame(frame)
    ret_frame.grid(row=9, column=1, sticky="w", padx=4, pady=4)

    ret_labels = ["Ganancias", "SUSS", "TEM", "IIBB"]
    ret_entries = {}

    # Fila 0: encabezados
    for j, lbl in enumerate(ret_labels):
        ttk.Label(ret_frame, text=lbl).grid(row=0, column=j, padx=5)

    # Fila 1: entradas
    for j, lbl in enumerate(ret_labels):
        e = ttk.Entry(ret_frame, width=10)
        e.grid(row=1, column=j, padx=5)
        ret_entries[lbl] = e

    # Fila 2: Total de retenciones
    ret_total_var = tk.StringVar(value="0.00")
    ttk.Label(ret_frame, text="Total ret.:").grid(row=2, column=0, padx=5, pady=(6, 0), sticky="e")
    ttk.Entry(ret_frame, width=12, state="readonly", textvariable=ret_total_var)\
        .grid(row=2, column=1, columnspan=3, padx=5, pady=(6, 0), sticky="w")

    # Total - Retenciones (solo lectura)
    ttk.Label(frame, text="Total - Retenciones ($)").grid(row=10, column=0, sticky="e", padx=4)
    total_entry = ttk.Entry(frame, width=40, state="readonly")
    total_entry.grid(row=10, column=1, sticky="w", padx=4, pady=2)

    def _safe_float(s):
        try:
            return float(s.replace(",", ".")) if isinstance(s, str) else float(s)
        except Exception:
            return 0.0

    def _parse_monetario(s) -> float:
        """
        Convierte '5.582.420,00', '5,582,420.00', '5582420.00', '5582420' a float
        sin mover el decimal.
        """
        try:
            s = str(s).strip().replace(" ", "")
            if not s:
                return 0.0
            # Entero puro
            if s.isdigit():
                return float(s)
            # Tiene coma y punto -> el último separador es el decimal
            if "," in s and "." in s:
                if s.rfind(",") > s.rfind("."):
                    s = s.replace(".", "").replace(",", ".")
                else:
                    s = s.replace(",", "")
            # Solo coma -> coma decimal
            elif "," in s:
                s = s.replace(".", "").replace(",", ".")
            # Solo punto o ninguno -> ya sirve
            else:
                s = s.replace(",", "")
            return float(s)
        except Exception:
            return 0.0

    # --- NUEVO: recalcula retenciones y el TOTAL NETO (solo UI) ---
    def recalcular_totales(*_):
        # Tomamos el "Total ($)" de arriba como BRUTO.
        # Si aún no cambiaste el nombre del campo a 'total', usa 'subtotal' automáticamente.
        bruto_str = campos["total"].get() if "total" in campos else campos["subtotal"].get()
        bruto = _parse_monetario(bruto_str)

        # Suma de retenciones
        r_sum = sum(_parse_monetario(ret_entries[k].get()) for k in ret_labels)

        # Mostrar total de retenciones en el recuadro
        ret_total_var.set(f"{r_sum:.2f}")

        # TOTAL NETO (solo visual, no se imprime en el PDF)
        neto = max(0.0, bruto - r_sum)
        total_entry.config(state="normal")
        total_entry.delete(0, tk.END)
        total_entry.insert(0, f"{neto:.2f}")
        total_entry.config(state="readonly")


    # Binds: cuando cambie el Total de arriba o alguna retención, actualizamos el label gris
    if "total" in campos:
        campos["total"].bind("<KeyRelease>", recalcular_totales)
    else:
        # Compatibilidad si todavía se llama 'subtotal'
        campos["subtotal"].bind("<KeyRelease>", recalcular_totales)

    for e in ret_entries.values():
        e.bind("<KeyRelease>", recalcular_totales)

    # =========================
    # Forma de pago (MÚLTIPLE)
    # =========================
    ttk.Label(frame, text="Forma de pago").grid(row=11, column=0, sticky="ne", padx=4)
    fp_frame = ttk.Frame(frame)
    fp_frame.grid(row=11, column=1, sticky="w", padx=4, pady=4)

    # --- Editor de fila (igual que antes) ---
    for j, lbl in enumerate(["Tipo", "Número", "C/Banco", "Fecha", "Importe"]):
        ttk.Label(fp_frame, text=lbl).grid(row=0, column=j, padx=5)

    fp_tipo = ttk.Combobox(fp_frame, values=["Efectivo", "Cheque", "Transferencia"], width=12, state="readonly")
    fp_tipo.grid(row=1, column=0, padx=5)
    fp_nro = ttk.Entry(fp_frame, width=12);   fp_nro.grid(row=1, column=1, padx=5)
    fp_banco = ttk.Entry(fp_frame, width=16); fp_banco.grid(row=1, column=2, padx=5)
    fp_fecha = ttk.Entry(fp_frame, width=12); fp_fecha.grid(row=1, column=3, padx=5)
    fp_importe = ttk.Entry(fp_frame, width=12); fp_importe.grid(row=1, column=4, padx=5)

    # --- NUEVO: grilla de pagos (hasta 6 visibles en PDF) ---
    pagos_tree = ttk.Treeview(fp_frame, columns=("tipo","numero","banco","fecha","importe"),
                              show="headings", height=6)
    for col, txt, w in [
        ("tipo","Tipo",120), ("numero","Número",150), ("banco","C/Banco",150),
        ("fecha","Fecha",90), ("importe","Importe",110)
    ]:
        pagos_tree.heading(col, text=txt)
        pagos_tree.column(col, width=w, anchor="w")

    pagos_tree.grid(row=2, column=0, columnspan=5, sticky="ew", padx=2, pady=(6,2))

    # Botones para la grilla
    def _ui_safe_float(val:str)->float:
        try:
            return float(str(val).replace(".", "").replace(",", "."))
        except Exception:
            return 0.0

    def agregar_pago():
        t = fp_tipo.get().strip()
        n = fp_nro.get().strip()
        b = fp_banco.get().strip()
        f = fp_fecha.get().strip()
        im = _parse_monetario(fp_importe.get().strip())

        if not t:
            messagebox.showerror("Pago", "Seleccioná un tipo.")
            return
        if im <= 0:
            messagebox.showerror("Pago", "Importe inválido.")
            return

        pagos_tree.insert("", "end", values=(t, n, b, f, f"{im:.2f}"))
        # Limpiar campos (opcional)
        # fp_nro.delete(0, tk.END); fp_banco.delete(0, tk.END); fp_fecha.delete(0, tk.END); fp_importe.delete(0, tk.END)

    def quitar_pago():
        sel = pagos_tree.selection()
        if not sel:
            return
        for iid in sel:
            pagos_tree.delete(iid)

    btns = ttk.Frame(fp_frame)
    btns.grid(row=3, column=0, columnspan=5, sticky="w", pady=(2,0))
    ttk.Button(btns, text="Agregar pago", command=agregar_pago).grid(row=0, column=0, padx=(0,6))
    ttk.Button(btns, text="Quitar seleccionado", command=quitar_pago).grid(row=0, column=1)

    def _colectar_pagos():
        pagos = []
        for iid in pagos_tree.get_children():
            t, n, b, f, im = pagos_tree.item(iid, "values")
            pagos.append({
                "tipo": t, "numero": n, "banco": b, "fecha": f,
                "importe": _parse_monetario(im),
            })
        return pagos

    # ---- Autocompletado (ya con los Entry creados) ----
    ent_cliente    = campos["cliente"]
    ent_cuit       = campos["cuit"]
    ent_domicilio  = campos["domicilio"]
    ent_localidad  = campos["localidad"]
    ent_iva        = campos["iva"]

    def _try_autocomplete(_event=None):
        q = ent_cliente.get().strip() or ent_cuit.get().strip()
        if not q:
            return
        try:
            r = buscar_por_nombre_o_cuit(q)  # (nombre, cuit, dom, loc, iva) o None
        except Exception:
            return
        if not r:
            return
        nombre, cuit, dom, loc, iva = r
        if nombre and not ent_cliente.get().strip():
            ent_cliente.insert(0, nombre)
        if cuit and not ent_cuit.get().strip():
            ent_cuit.insert(0, cuit)
        if dom and not ent_domicilio.get().strip():
            ent_domicilio.insert(0, dom)
        if loc and not ent_localidad.get().strip():
            ent_localidad.insert(0, loc)
        if iva and not ent_iva.get().strip():
            ent_iva.insert(0, iva)

    ent_cliente.bind("<FocusOut>", _try_autocomplete)
    ent_cuit.bind(   "<FocusOut>", _try_autocomplete)

    # ---- Generar ----
    def generar():
        numero_recibo = None  # ← evita UnboundLocalError en cualquier except

        try:
            if not campos["fecha"].get().strip():
                messagebox.showerror("Error", "La fecha es obligatoria.")
                return
            if not campos["cliente"].get().strip():
                messagebox.showerror("Error", "El cliente es obligatorio.")
                return

            # ---- importes / retenciones ----
            bruto = _parse_monetario(campos["total"].get() if "total" in campos else campos["subtotal"].get())
            ret = {
                "Ganancias": _parse_monetario(ret_entries["Ganancias"].get()),
                "SUSS":      _parse_monetario(ret_entries["SUSS"].get()),
                "TEM":       _parse_monetario(ret_entries["TEM"].get()),
                "IIBB":      _parse_monetario(ret_entries["IIBB"].get()),
            }
            ret_sum = sum(ret.values())
            neto = max(0.0, bruto - ret_sum)

            # ---- formas de pago ----
            fps = _colectar_pagos()
            if not fps:
                fps = [{
                    "tipo": fp_tipo.get().strip(),
                    "numero": fp_nro.get().strip(),
                    "banco": fp_banco.get().strip(),
                    "fecha": fp_fecha.get().strip(),
                    "importe": _parse_monetario(fp_importe.get()),
                }]

            suma_fp = sum(p.get("importe", 0.0) for p in fps)
            if abs(suma_fp - (bruto - ret_sum)) > 0.01:
                if not messagebox.askyesno(
                    "Atención",
                    f"La suma de pagos (${suma_fp:.2f}) no coincide con (Total - Retenciones) (${(bruto - ret_sum):.2f}).\n¿Continuar?"
                ):
                    return

            # ---- confirmación (AÚN SIN NÚMERO) ----
            resumen = [
                f"Fecha: {campos['fecha'].get().strip()}",
                f"Cliente: {campos['cliente'].get().strip()}",
                f"Total (bruto): ${bruto:.2f}",
                f"Retenciones: ${ret_sum:.2f}",
                f"Pagos esperados (Total - Retenciones): ${neto:.2f}",
                f"Suma de pagos: ${suma_fp:.2f}",
            ]
            if not messagebox.askyesno("Confirmar", "¿Generar el recibo con estos datos?\n\n" + "\n".join(resumen)):
                return

            # ---- AHORA sí asignamos el número real e incrementamos ----
            from utils.contador import incrementar_contador, ver_numero_siguiente
            numero_recibo = incrementar_contador()

            # ---- datos para el PDF (con el número real) ----
            datos = {
                "numero_recibo": numero_recibo,
                "fecha": campos["fecha"].get().strip(),
                "cliente": campos["cliente"].get().strip(),
                "domicilio": campos["domicilio"].get().strip(),
                "localidad": campos["localidad"].get().strip(),
                "cuit": campos["cuit"].get().strip(),
                "iva": campos["iva"].get().strip(),
                "concepto": concepto_text.get("1.0", tk.END).strip(),
                "retenciones": ret,
                "forma_pago": fps,
                "total": bruto,
            }

            # ---- QR ----
            qr_payload = build_qr_data(datos, BASE_QR_URL, QR_SECRET_KEY)

            # ---- salida centralizada ----
            output_dir = SALIDA_DIR
            output_dir.mkdir(parents=True, exist_ok=True)
            cliente_sanit = (datos["cliente"] or "Cliente").replace(" ", "_")
            ruta_pdf = output_dir / f"Recibo_{numero_recibo}__{cliente_sanit}.pdf"

            # ---- generar PDF (assets desde ASSETS_DIR) ----
            from config import ASSETS_DIR
            generar_pdf(
                datos,
                ruta_pdf,
                logo_path=None,
                firma_path=str(ASSETS_DIR / "firma.png"),
                anulado=False,
                qr_data=qr_payload,
                template_pdf=str(ASSETS_DIR / "MODELO 2.pdf"),
            )

            # ---- persistir cliente (best-effort) ----
            try:
                upsert_cliente(datos["cliente"], datos["cuit"], datos["domicilio"], datos["localidad"], datos["iva"])
            except Exception:
                pass

            # ---- refrescar preview del siguiente ----
            try:
                campos["numero_recibo"].config(state="normal")
                campos["numero_recibo"].delete(0, tk.END)
                campos["numero_recibo"].insert(0, ver_numero_siguiente())
                campos["numero_recibo"].config(state="readonly")
            except Exception:
                pass

            messagebox.showinfo("Éxito", f"Recibo generado correctamente:\n{ruta_pdf}")

        except Exception as e:
            # Si falló antes de asignar el número, no lo referencies
            messagebox.showerror("Error", str(e))

    ttk.Button(frame, text="Generar Recibo", command=generar)\
        .grid(row=13, column=0, columnspan=2, pady=10)
