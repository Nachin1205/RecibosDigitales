# main.py
import sys
import threading
import logging, logging.handlers, socket, getpass
import tkinter as tk
from tkinter import ttk, messagebox  # si no usás messagebox, podés quitarlo
from config import SALIDA_DIR, CONTADOR_PATH
from interfaz.nueva import crear_pestana_nueva
from interfaz.buscar_editar import crear_pestana_buscar
from interfaz.anular import crear_pestana_anular
from config import LOGS_DIR
from config import ASSETS_DIR

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
    root.iconbitmap(default=str(ASSETS_DIR / "tucumind.ico"))
    root.title("Recibos Digitales - MODELO 2")
    root.geometry("820x720")

    tabs = ttk.Notebook(root)
    tabs.pack(expand=True, fill="both")

    # Pestañas
    crear_pestana_nueva(tabs)
    crear_pestana_buscar(tabs)
    crear_pestana_anular(tabs)

    # Levantar validador Flask en segundo plano
    run_validator_async(logger)

    def _on_close():
        logger.info("Cierre solicitado por el usuario")
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", _on_close)
    root.mainloop()

if __name__ == "__main__":
    main()
