# main.py
import sys
import threading
import logging, logging.handlers, socket, getpass
import os, sys
if getattr(sys, "frozen", False):
    os.chdir(os.path.dirname(sys.executable))
else:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

import tkinter as tk
from tkinter import ttk
from config import SALIDA_DIR, CONTADOR_PATH
from interfaz.nueva import crear_pestana_nueva
from interfaz.buscar_editar import crear_pestana_buscar
from interfaz.anular import crear_pestana_anular
from config import LOGS_DIR
from config import ASSETS_DIR
from config import DATA_DIR, DB_DIR, RECIBOS_DIR, BASE_QR_URL, VALIDATOR_HOST, VALIDATOR_PORT
from utils import recibos_db
from utils.clientes import init_db as init_clientes_db, listar_clientes
from ui.theme import apply_theme, ToastManager, make_notifier

# -------------------------------
# Logging (rotación por archivo)
# -------------------------------
def setup_logging():
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    host, user = socket.gethostname(), getpass.getuser()
    logfile = LOGS_DIR / f"recibos_{host}_{user}.log"

    logger = logging.getLogger("recibos")
    logger.setLevel(logging.INFO)

    fh = logging.handlers.RotatingFileHandler(
        logfile, maxBytes=2_000_000, backupCount=5, encoding="utf-8"
    )
    fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
    logger.addHandler(fh)

    # Log de excepciones no controladas
    def _exhook(exc_type, exc, tb):
        logger.exception("Excepción no controlada", exc_info=(exc_type, exc, tb))
    sys.excepthook = _exhook

    return logger

# -------------------------------
# Validador Flask en hilo aparte
# -------------------------------
def run_validator_async(logger):
    def _run():
        try:
            from app import app
            # host=127.0.0.1 para uso local; "0.0.0.0" si querés exponer en LAN
            app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
        except OSError as e:
            logger.warning(f"Validador no iniciado (¿puerto en uso?): {e}")
        except Exception:
            logger.exception("Error iniciando validador")
    t = threading.Thread(target=_run, daemon=True, name="validator")
    t.start()
    return t

# -------------------------------
# App Tkinter
# -------------------------------
def main():
    logger = setup_logging()
    logger.info(f"SALIDA_DIR={SALIDA_DIR}")
    logger.info(f"CONTADOR_PATH={CONTADOR_PATH}")
    logger.info("Aplicación iniciada")

    root = tk.Tk()
    try:
        root.iconbitmap(default=str(ASSETS_DIR / "tucumind.ico"))
    except Exception:
        pass
    root.title("Recibos Digitales")
    root.geometry("1240x840")
    root.minsize(1024, 720)
    apply_theme(root)

    toast = ToastManager(root)
    notify = make_notifier(toast)

    root.grid_columnconfigure(1, weight=1)
    root.grid_rowconfigure(0, weight=1)

    sidebar = ttk.Frame(root, style="Sidebar.TFrame", width=220)
    sidebar.grid(row=0, column=0, sticky="ns")
    sidebar.grid_propagate(False)
    sidebar.grid_columnconfigure(0, weight=1)

    content = ttk.Frame(root, style="Content.TFrame")
    content.grid(row=0, column=1, sticky="nsew")
    content.grid_columnconfigure(0, weight=1)
    content.grid_rowconfigure(1, weight=1)

    topbar = ttk.Frame(content, style="Topbar.TFrame", padding=(16, 12))
    topbar.grid(row=0, column=0, sticky="ew")
    topbar.grid_columnconfigure(1, weight=1)
    ttk.Label(topbar, text="Recibos Digitales", style="Title.TLabel").grid(row=0, column=0, sticky="w")
    search_var = tk.StringVar()
    search_entry = ttk.Entry(topbar, textvariable=search_var)
    search_entry.grid(row=0, column=1, sticky="ew", padx=(12, 8))

    body = ttk.Frame(content, style="Content.TFrame", padding=(16, 8, 16, 16))
    body.grid(row=1, column=0, sticky="nsew")
    body.grid_columnconfigure(0, weight=1)
    body.grid_rowconfigure(0, weight=1)

    sections = {
        "dashboard": ttk.Frame(body, style="Content.TFrame"),
        "recibos": ttk.Frame(body, style="Content.TFrame"),
        "clientes": ttk.Frame(body, style="Content.TFrame"),
        "configuracion": ttk.Frame(body, style="Content.TFrame"),
    }
    for f in sections.values():
        f.grid(row=0, column=0, sticky="nsew")

    nav_buttons = {}

    def show_section(name: str):
        for sec, frame in sections.items():
            if sec == name:
                frame.tkraise()
            btn = nav_buttons.get(sec)
            if btn is not None:
                btn.configure(style="NavActive.TButton" if sec == name else "Nav.TButton")

    # -------------------------------
    # Sección Dashboard
    # -------------------------------
    dash = sections["dashboard"]
    dash.grid_columnconfigure((0, 1), weight=1)
    ttk.Label(dash, text="Dashboard", style="Title.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))
    ttk.Label(dash, text="Resumen rápido para demo y operación diaria.", style="Muted.TLabel").grid(row=1, column=0, columnspan=2, sticky="w")

    kpi_vars = {
        "recibos": tk.StringVar(value="0"),
        "clientes": tk.StringVar(value="0"),
        "ultimo": tk.StringVar(value="-"),
    }

    def _kpi_card(parent, row, col, title, var):
        card = ttk.Frame(parent, style="Card.TFrame", padding=16)
        card.grid(row=row, column=col, sticky="nsew", padx=(0 if col == 0 else 8, 8 if col == 0 else 0), pady=8)
        ttk.Label(card, text=title, style="Muted.TLabel").pack(anchor="w")
        ttk.Label(card, textvariable=var, style="Kpi.TLabel").pack(anchor="w", pady=(6, 0))

    _kpi_card(dash, 2, 0, "Recibos cargados", kpi_vars["recibos"])
    _kpi_card(dash, 2, 1, "Clientes registrados", kpi_vars["clientes"])

    info_card = ttk.Frame(dash, style="Card.TFrame", padding=16)
    info_card.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=8)
    ttk.Label(info_card, text="Último número generado", style="Muted.TLabel").grid(row=0, column=0, sticky="w")
    ttk.Label(info_card, textvariable=kpi_vars["ultimo"], style="Kpi.TLabel").grid(row=1, column=0, sticky="w", pady=(6, 10))
    ttk.Label(info_card, text=f"Salida PDF: {RECIBOS_DIR}", style="Muted.TLabel").grid(row=2, column=0, sticky="w")
    ttk.Label(info_card, text=f"Validador QR: http://{VALIDATOR_HOST}:{VALIDATOR_PORT}/recibo", style="Muted.TLabel").grid(row=3, column=0, sticky="w")
    ttk.Label(info_card, text=f"DB: {DB_DIR}", style="Muted.TLabel").grid(row=4, column=0, sticky="w")

    def refresh_dashboard():
        try:
            recibos_db.init_db()
            rows = recibos_db.buscar_recibos(limite=10000)
            kpi_vars["recibos"].set(str(len(rows)))
            kpi_vars["ultimo"].set(rows[0]["numero"] if rows else "-")
        except Exception:
            kpi_vars["recibos"].set("0")
            kpi_vars["ultimo"].set("-")
        try:
            init_clientes_db()
            kpi_vars["clientes"].set(str(len(listar_clientes())))
        except Exception:
            kpi_vars["clientes"].set("0")

    ttk.Button(info_card, text="Actualizar", style="Secondary.TButton", command=refresh_dashboard).grid(row=5, column=0, sticky="w", pady=(12, 0))

    # -------------------------------
    # Sección Recibos (flujo actual)
    # -------------------------------
    recibos_sec = sections["recibos"]
    recibos_sec.grid_columnconfigure(0, weight=1)
    recibos_sec.grid_rowconfigure(1, weight=1)
    ttk.Label(recibos_sec, text="Recibos", style="Title.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))

    tabs = ttk.Notebook(recibos_sec)
    tabs.grid(row=1, column=0, sticky="nsew")
    crear_pestana_nueva(tabs, notify=notify)
    buscar_ctrl = crear_pestana_buscar(tabs, notify=notify)
    crear_pestana_anular(tabs, notify=notify)

    # -------------------------------
    # Sección Clientes
    # -------------------------------
    clientes_sec = sections["clientes"]
    clientes_sec.grid_columnconfigure(0, weight=1)
    ttk.Label(clientes_sec, text="Clientes", style="Title.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))
    panel_clientes = ttk.Frame(clientes_sec, style="Card.TFrame", padding=16)
    panel_clientes.grid(row=1, column=0, sticky="nsew")
    panel_clientes.grid_columnconfigure(0, weight=1)
    ttk.Label(panel_clientes, text="Vista rápida de clientes cargados", style="Panel.TLabel").grid(row=0, column=0, sticky="w")
    clientes_list = tk.Listbox(panel_clientes, height=12, borderwidth=0)
    clientes_list.grid(row=1, column=0, sticky="nsew", pady=8)
    panel_clientes.grid_rowconfigure(1, weight=1)

    def refresh_clientes():
        clientes_list.delete(0, tk.END)
        try:
            init_clientes_db()
            rows = listar_clientes()
        except Exception:
            rows = []
        if not rows:
            clientes_list.insert(tk.END, "No hay clientes cargados.")
            return
        for nombre, cuit, *_ in rows[:100]:
            clientes_list.insert(tk.END, f"{nombre}  |  CUIT: {cuit or '-'}")

    btns_clientes = ttk.Frame(panel_clientes, style="Card.TFrame")
    btns_clientes.grid(row=2, column=0, sticky="w", pady=(8, 0))
    ttk.Button(btns_clientes, text="Refrescar", style="Secondary.TButton", command=refresh_clientes).grid(row=0, column=0, padx=(0, 8))
    ttk.Button(btns_clientes, text="Ir a Nuevo Recibo", style="Primary.TButton", command=lambda: (show_section("recibos"), tabs.select(0))).grid(row=0, column=1)

    # -------------------------------
    # Sección Configuración (mínima)
    # -------------------------------
    conf = sections["configuracion"]
    conf.grid_columnconfigure(0, weight=1)
    ttk.Label(conf, text="Configuración", style="Title.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))
    panel_conf = ttk.Frame(conf, style="Card.TFrame", padding=16)
    panel_conf.grid(row=1, column=0, sticky="nsew")
    ttk.Label(panel_conf, text="Base QR URL", style="Panel.TLabel").grid(row=0, column=0, sticky="w")
    e_qr = ttk.Entry(panel_conf, width=80)
    e_qr.grid(row=1, column=0, sticky="ew", pady=(2, 10))
    e_qr.insert(0, BASE_QR_URL)
    e_qr.configure(state="readonly")
    ttk.Label(panel_conf, text="Raíz de datos", style="Panel.TLabel").grid(row=2, column=0, sticky="w")
    e_data = ttk.Entry(panel_conf, width=80)
    e_data.grid(row=3, column=0, sticky="ew", pady=(2, 10))
    e_data.insert(0, str(DATA_DIR))
    e_data.configure(state="readonly")
    ttk.Label(panel_conf, text="En Fase 4 se habilita edición y guardado en config.", style="Muted.TLabel").grid(row=4, column=0, sticky="w")

    # -------------------------------
    # Sidebar + buscador global
    # -------------------------------
    ttk.Label(sidebar, text="Recibos", style="Sidebar.TLabel", padding=(14, 16)).grid(row=0, column=0, sticky="w")
    nav_defs = [
        ("dashboard", "Dashboard"),
        ("recibos", "Recibos"),
        ("clientes", "Clientes"),
        ("configuracion", "Configuración"),
    ]
    for idx, (key, label) in enumerate(nav_defs, start=1):
        b = ttk.Button(sidebar, text=label, style="Nav.TButton", command=lambda k=key: show_section(k))
        b.grid(row=idx, column=0, sticky="ew", padx=10, pady=4)
        nav_buttons[key] = b

    def run_global_search():
        txt = (search_var.get() or "").strip()
        if not txt:
            notify("warning", "Búsqueda", "Ingresá número, cliente o fecha (DD/MM/AAAA).")
            return
        show_section("recibos")
        try:
            tabs.select(buscar_ctrl["frame"])
            buscar_ctrl["buscar_global"](txt)
        except Exception:
            notify("error", "Búsqueda", "No se pudo ejecutar la búsqueda global.")

    ttk.Button(topbar, text="Buscar", style="Primary.TButton", command=run_global_search).grid(row=0, column=2, sticky="e")
    search_entry.bind("<Return>", lambda _e: run_global_search())

    # Levantar validador Flask en segundo plano
    run_validator_async(logger)

    refresh_dashboard()
    refresh_clientes()
    show_section("dashboard")

    def _on_close():
        logger.info("Cierre solicitado por el usuario")
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", _on_close)
    root.mainloop()

if __name__ == "__main__":
    main()
