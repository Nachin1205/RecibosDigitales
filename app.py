# app.py
import os
import logging
from flask import Flask, request, render_template, abort
from config import QR_SECRET_KEY, VALIDATOR_HOST, VALIDATOR_PORT, FLASK_DEBUG
from utils.qr_utils import verify_qr_params

app = Flask(__name__, template_folder="Templates")

# Logging básico a consola (útil en Docker)
if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("validator")

# Advertir si la clave es el valor por defecto (no romper, pero avisar)
if QR_SECRET_KEY == "solo-para-pruebas-locales-cambiar":
    logger.warning("QR_SECRET_KEY usa el valor por defecto. Definí una clave segura en producción.")

@app.route("/health")
def health():
    return "OK", 200

@app.route("/recibo", methods=["GET"])
def recibo():
    p = request.args.get("p")
    s = request.args.get("s")
    if not p or not s:
        abort(400, description="Falta p o s en la URL.")

    ok, data_or_err = verify_qr_params(p, s, QR_SECRET_KEY)
    if not ok:
        abort(400, description=str(data_or_err))

    return render_template("recibo.html", datos=data_or_err)

@app.errorhandler(400)
def bad_request(e):
    return f"<h1>Solicitud inválida</h1><p>{e.description}</p>", 400

@app.errorhandler(404)
def not_found(e):
    return "<h1>No encontrado</h1>", 404

if __name__ == "__main__":
    # Host/puerto configurables por env (útil para Docker/CI)
    app.run(host=VALIDATOR_HOST, port=VALIDATOR_PORT, debug=FLASK_DEBUG)
