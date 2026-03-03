# interfaz/nueva.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from utils.qr_utils import build_qr_data
from config import BASE_QR_URL, QR_SECRET_KEY, SALIDA_DIR, ASSETS_DIR
import re
from utils.clientes import (
    init_db,
    upsert_cliente,
    listar_clientes,
    importar_clientes_desde_excel,
    buscar_por_nombre_o_cuit,
)
from utils import recibos_db
from utils.helpers import validar_fecha_no_futura
from utils.recibo_utils import posible_duplicado
from utils.recibo_utils import upsert_historial_con_json
from utils.pdf_generator import generar_pdf
from utils.contador import ver_numero_siguiente, incrementar_contador

# Rutas/constantes 

LOGO_PATH = None
FIRMA_PATH = ASSETS_DIR / "firma.png"   # ✅ sirve en .py y en el .exe
# No definimos CARPETA_SALIDA: los PDFs van a SALIDA_DIR (servidor)

def _notify(notify, level: str, title: str, message: str):
    if callable(notify):
        notify(level, title, message)
        return
    if level == "error":
        messagebox.showerror(title, message)
    elif level == "warning":
        messagebox.showwarning(title, message)
    else:
        messagebox.showinfo(title, message)


def crear_pestana_nueva(tabs: ttk.Notebook, notify=None):
    frame = ttk.Frame(tabs)
    tabs.add(frame, text="🧾 Nuevo Recibo")

    # Base de clientes (para autocompletado) y DB de recibos
    init_db()
    recibos_db.init_db()
    clientes_cache = listar_clientes()
    clientes_filtrados = list(clientes_cache)
    cliente_busqueda_var = tk.StringVar()
    cliente_listbox = None
    btn_agregar_cliente = None
    btn_importar_excel = None
    cliente_busqueda_entry = None

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
        if key == "cliente":
            cliente_container = ttk.Frame(frame)
            cliente_container.grid(row=i, column=1, sticky="we", padx=4, pady=2)
            cliente_container.columnconfigure(0, weight=1)

            entry = ttk.Entry(cliente_container, width=40, state="readonly")
            entry.grid(row=0, column=0, columnspan=2, sticky="we")

            selector_frame = ttk.Frame(cliente_container)
            selector_frame.grid(row=1, column=0, columnspan=2, sticky="we", pady=(4, 0))
            selector_frame.columnconfigure(1, weight=1)
            ttk.Label(selector_frame, text="Buscar").grid(row=0, column=0, padx=(0, 4))
            cliente_busqueda_entry = ttk.Entry(selector_frame, width=26, textvariable=cliente_busqueda_var)
            cliente_busqueda_entry.grid(row=0, column=1, sticky="we")
            btn_agregar_cliente = ttk.Button(selector_frame, text="Agregar cliente...", command=lambda: None)
            btn_agregar_cliente.grid(row=0, column=2, padx=(6, 0))
            btn_importar_excel = ttk.Button(selector_frame, text="Importar Excel...", command=lambda: None)
            btn_importar_excel.grid(row=0, column=3, padx=(6, 0))

            cliente_listbox = tk.Listbox(cliente_container, height=5, width=40, exportselection=False)
            cliente_listbox.grid(row=2, column=0, columnspan=2, sticky="we", pady=(4, 0))
        else:
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

    # --- Recalcula retenciones y el TOTAL NETO (solo UI) ---
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

    # --- Grilla de pagos (hasta 6 visibles en PDF) ---
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
            _notify(notify, "error", "Pago", "Seleccioná un tipo.")
            return
        if im <= 0:
            _notify(notify, "error", "Pago", "Importe inválido.")
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

    # ---- Gestión de clientes con filtro ----
    def _set_cliente_entry(nombre_text: str):
        entry_cliente = campos["cliente"]
        entry_cliente.config(state="normal")
        entry_cliente.delete(0, tk.END)
        if nombre_text:
            entry_cliente.insert(0, nombre_text)
        entry_cliente.config(state="readonly")

    def _rellenar_campos_cliente(data, actualizar_busqueda=False):
        if not data:
            return
        nombre, cuit, dom, loc, iva = data
        _set_cliente_entry(nombre or "")
        if actualizar_busqueda:
            cliente_busqueda_var.set(nombre or "")
        for widget, value in (
            (campos["cuit"], cuit),
            (campos["domicilio"], dom),
            (campos["localidad"], loc),
            (campos["iva"], iva),
        ):
            widget.delete(0, tk.END)
            if value:
                widget.insert(0, value)

    def _actualizar_listbox(*_):
        nonlocal clientes_filtrados
        filtro = (cliente_busqueda_var.get() or "").strip().lower()
        filtrados = []
        for data in clientes_cache:
            nombre = (data[0] or "").lower()
            if not filtro or filtro in nombre:
                filtrados.append(data)
        clientes_filtrados = filtrados
        if cliente_listbox is None:
            return
        cliente_listbox.delete(0, tk.END)
        for nombre, *_ in clientes_filtrados:
            cliente_listbox.insert(tk.END, nombre)

    def _on_listbox_select(_event=None):
        if cliente_listbox is None:
            return
        sel = cliente_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        if idx >= len(clientes_filtrados):
            return
        _rellenar_campos_cliente(clientes_filtrados[idx])

    def _refrescar_clientes_cache(nombre_preseleccionado=""):
        nonlocal clientes_cache, clientes_filtrados
        try:
            clientes_cache = listar_clientes()
        except Exception:
            clientes_cache = []
        clientes_filtrados = list(clientes_cache)
        _actualizar_listbox()
        if nombre_preseleccionado:
            for data in clientes_cache:
                if (data[0] or "").lower() == nombre_preseleccionado.lower():
                    _rellenar_campos_cliente(data, actualizar_busqueda=True)
                    break

    def importar_excel_clientes():
        archivo = filedialog.askopenfilename(
            title="Importar clientes desde Excel",
            filetypes=[("Archivos de Excel", "*.xlsx *.xls"), ("Todos los archivos", "*.*")],
        )
        if not archivo:
            return
        try:
            resumen = importar_clientes_desde_excel(archivo)
        except ModuleNotFoundError:
            _notify(notify, "error", "Clientes", "Necesitás tener 'openpyxl' instalado para importar desde Excel.")
            return
        except Exception as exc:
            _notify(notify, "error", "Clientes", f"No se pudo importar: {exc}")
            return

        _refrescar_clientes_cache()
        msg = (
            "Importación completada.\n"
            f"Nuevos: {resumen.get('insertados', 0)}\n"
            f"Actualizados: {resumen.get('actualizados', 0)}\n"
            f"Omitidos: {resumen.get('omitidos', 0)}"
        )
        _notify(notify, "success", "Clientes", msg)

    def abrir_modal_cliente():
        pre_data = None
        if cliente_listbox is not None:
            sel = cliente_listbox.curselection()
            if sel and sel[0] < len(clientes_filtrados):
                pre_data = clientes_filtrados[sel[0]]
        if not pre_data:
            # Intentar por nombre actual en entry
            nombre_actual = campos["cliente"].get().strip()
            if nombre_actual:
                pre_data = buscar_por_nombre_o_cuit(nombre_actual)

        modal = tk.Toplevel(frame)
        modal.title("Agregar / editar cliente")
        modal.transient(frame.winfo_toplevel())
        modal.grab_set()
        modal.resizable(False, False)

        campos_modal = {}
        info_var = tk.StringVar()
        modal_fields = [
            ("Nombre", "nombre"),
            ("CUIT", "cuit"),
            ("Domicilio", "domicilio"),
            ("Localidad", "localidad"),
            ("IVA", "iva"),
        ]
        for i, (lbl, key) in enumerate(modal_fields):
            ttk.Label(modal, text=lbl).grid(row=i, column=0, sticky="e", padx=6, pady=4)
            e = ttk.Entry(modal, width=40)
            e.grid(row=i, column=1, sticky="w", padx=6, pady=4)
            campos_modal[key] = e

        info_lbl = ttk.Label(modal, textvariable=info_var, foreground="gray")
        info_lbl.grid(row=len(modal_fields), column=0, columnspan=2, padx=6, pady=(0, 6), sticky="w")

        if pre_data:
            nombre, cuit, dom, loc, iva = pre_data
            campos_modal["nombre"].insert(0, nombre or "")
            campos_modal["cuit"].insert(0, cuit or "")
            campos_modal["domicilio"].insert(0, dom or "")
            campos_modal["localidad"].insert(0, loc or "")
            campos_modal["iva"].insert(0, iva or "")
            info_var.set(f"Editás a {nombre}. Guardando se reemplazarán sus datos.")
        else:
            info_var.set("Nuevo cliente. Quedará disponible para seleccionar al guardar.")

        def _guardar_modal():
            nombre = campos_modal["nombre"].get().strip()
            if not nombre:
                _notify(notify, "error", "Clientes", "El nombre es obligatorio.")
                return

            nombre_actual = (pre_data[0] if pre_data else "") or ""
            existente = None
            try:
                existente = buscar_por_nombre_o_cuit(nombre)
            except Exception:
                existente = None
            if existente and nombre.strip().lower() != nombre_actual.strip().lower():
                _notify(
                    notify,
                    "error",
                    "Clientes",
                    "Ya existe otro cliente con ese nombre. Seleccionalo para editarlo o usá un nombre distinto.",
                )
                return

            try:
                upsert_cliente(
                    nombre,
                    campos_modal["cuit"].get().strip(),
                    campos_modal["domicilio"].get().strip(),
                    campos_modal["localidad"].get().strip(),
                    campos_modal["iva"].get().strip(),
                )
            except Exception as exc:
                _notify(notify, "error", "Clientes", f"No se pudo guardar: {exc}")
                return

            _notify(notify, "success", "Clientes", "Cliente guardado correctamente.")
            modal.destroy()
            _refrescar_clientes_cache(nombre)
            if cliente_busqueda_entry is not None:
                cliente_busqueda_entry.focus_set()

        btns = ttk.Frame(modal)
        btns.grid(row=len(modal_fields)+1, column=0, columnspan=2, pady=(4, 0))
        ttk.Button(btns, text="Guardar", command=_guardar_modal).grid(row=0, column=0, padx=4)
        ttk.Button(btns, text="Cancelar", command=modal.destroy).grid(row=0, column=1, padx=4)

    if cliente_listbox is not None:
        cliente_listbox.bind("<<ListboxSelect>>", _on_listbox_select)
        cliente_listbox.bind("<Double-Button-1>", _on_listbox_select)
    cliente_busqueda_var.trace_add("write", lambda *_: _actualizar_listbox())
    _actualizar_listbox()
    if btn_agregar_cliente is not None:
        btn_agregar_cliente.config(command=abrir_modal_cliente)
    if btn_importar_excel is not None:
        btn_importar_excel.config(command=importar_excel_clientes)

    # ---- Generar ----
    def generar():
        numero_recibo = None  # ← evita UnboundLocalError en cualquier except

        try:
            if not campos["fecha"].get().strip():
                _notify(notify, "error", "Error", "La fecha es obligatoria.")
                return
            if not campos["cliente"].get().strip():
                _notify(notify, "error", "Error", "El cliente es obligatorio.")
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

            # ---- guardar/actualizar historial con payload completo ----
            try:
                upsert_historial_con_json(
                    numero=numero_recibo,
                    cliente=datos["cliente"],
                    fecha=datos["fecha"],
                    subtotal="",
                    total=datos["total"],
                    estado="",
                    datos=datos,
                )
            except Exception as e:
                # Informar explícitamente; suele fallar si falta openpyxl o si el Excel está abierto/bloqueado
                try:
                    from config import HISTORIAL_XLSX
                    ubic = str(HISTORIAL_XLSX)
                except Exception:
                    ubic = "historial/recibos.xlsx"
                _notify(
                    notify,
                    "warning",
                    "Historial",
                    "No se pudo actualizar el historial en Excel.\n"
                    f"Archivo: {ubic}\n\n"
                    "Cerrá el archivo si está abierto y verificá que 'openpyxl' esté instalado.\n\n"
                    f"Detalle: {e}",
                )

            # ---- persistir recibo en la base SQLite ----
            try:
                recibos_db.guardar_recibo(datos, neto)
            except Exception as e:
                _notify(
                    notify,
                    "warning",
                    "Recibos",
                    "El recibo se generó pero no se pudo guardar en la base.\n"
                    f"Detalle: {e}",
                )

            # ---- refrescar preview del siguiente ----
            try:
                campos["numero_recibo"].config(state="normal")
                campos["numero_recibo"].delete(0, tk.END)
                campos["numero_recibo"].insert(0, ver_numero_siguiente())
                campos["numero_recibo"].config(state="readonly")
            except Exception:
                pass

            _notify(notify, "success", "Éxito", f"Recibo generado correctamente:\n{ruta_pdf}")

        except Exception as e:
            # Si falló antes de asignar el número, no lo referencies
            _notify(notify, "error", "Error", str(e))

    ttk.Button(frame, text="Generar Recibo", command=generar)\
        .grid(row=13, column=0, columnspan=2, pady=10)
