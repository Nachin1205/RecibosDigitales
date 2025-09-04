# app.py
from flask import Flask, request, render_template, abort
from config import QR_SECRET_KEY
from utils.qr_utils import verify_qr_params

app = Flask(__name__, template_folder="Templates")

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
    # Para que funcione desde otros equipos de la LAN:
    app.run(host="0.0.0.0", port=5000, debug=True)
