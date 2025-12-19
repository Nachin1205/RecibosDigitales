import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any

from config import DATA_DIR

DB_PATH = DATA_DIR / "db" / "recibos.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def _conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    with _conn() as cx:
        cx.execute(
            """
            CREATE TABLE IF NOT EXISTS recibos(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero TEXT UNIQUE,
                fecha TEXT,
                fecha_iso TEXT,
                cliente_nombre TEXT,
                cliente_cuit TEXT,
                total_bruto REAL,
                total_neto REAL,
                datos_json TEXT,
                creado_en TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        cx.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_recibos_cliente_fecha
            ON recibos(cliente_nombre, fecha_iso);
            """
        )


def _fecha_a_iso(fecha: str) -> Optional[str]:
    try:
        return datetime.strptime(fecha.strip(), "%d/%m/%Y").strftime("%Y-%m-%d")
    except Exception:
        return None


def guardar_recibo(datos: Dict[str, Any], total_neto: float):
    """
    Inserta o actualiza un recibo usando su numero como identificador unico.
    """
    init_db()
    numero = datos.get("numero_recibo")
    fecha = datos.get("fecha", "")
    iso = _fecha_a_iso(fecha) or ""
    cliente = datos.get("cliente", "")
    cliente_cuit = datos.get("cuit", "")
    total_bruto = float(datos.get("total") or 0.0)
    total_neto = float(total_neto or 0.0)
    payload = json.dumps(datos, ensure_ascii=False)
    with _conn() as cx:
        cx.execute(
            """
            INSERT INTO recibos(numero, fecha, fecha_iso, cliente_nombre, cliente_cuit,
                                total_bruto, total_neto, datos_json)
            VALUES(?,?,?,?,?,?,?,?)
            ON CONFLICT(numero) DO UPDATE SET
                fecha=excluded.fecha,
                fecha_iso=excluded.fecha_iso,
                cliente_nombre=excluded.cliente_nombre,
                cliente_cuit=excluded.cliente_cuit,
                total_bruto=excluded.total_bruto,
                total_neto=excluded.total_neto,
                datos_json=excluded.datos_json;
            """,
            [numero, fecha, iso, cliente, cliente_cuit, total_bruto, total_neto, payload],
        )


def buscar_recibos(
    numero: Optional[str] = None,
    cliente: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    limite: int = 200,
) -> List[Dict[str, Any]]:
    init_db()
    filtros = []
    params: List[Any] = []

    if numero:
        filtros.append("numero LIKE ?")
        params.append(f"%{numero.strip()}%")
    if cliente:
        filtros.append("LOWER(cliente_nombre) LIKE ?")
        params.append(f"%{cliente.strip().lower()}%")

    def _maybe_iso(val):
        if not val:
            return None
        return _fecha_a_iso(val) or val

    iso_desde = _maybe_iso(fecha_desde)
    iso_hasta = _maybe_iso(fecha_hasta)
    if iso_desde:
        filtros.append("fecha_iso >= ?")
        params.append(iso_desde)
    if iso_hasta:
        filtros.append("fecha_iso <= ?")
        params.append(iso_hasta)

    where = f"WHERE {' AND '.join(filtros)}" if filtros else ""
    sql = f"""
        SELECT numero, fecha, cliente_nombre, cliente_cuit,
               total_bruto, total_neto, fecha_iso, datos_json
        FROM recibos
        {where}
        ORDER BY fecha_iso DESC, numero DESC
        LIMIT ?
    """
    params.append(limite)
    with _conn() as cx:
        cur = cx.execute(sql, params)
        filas = cur.fetchall()
    resultados = []
    for numero, fecha, cliente_nombre, cliente_cuit, total_bruto, total_neto, fecha_iso, datos_json in filas:
        try:
            datos = json.loads(datos_json)
        except Exception:
            datos = {}
        resultados.append(
            {
                "numero": numero,
                "fecha": fecha,
                "fecha_iso": fecha_iso,
                "cliente": cliente_nombre,
                "cuit": cliente_cuit,
                "total_bruto": total_bruto,
                "total_neto": total_neto,
                "datos": datos,
            }
        )
    return resultados


def contar_recibos_por_cliente(cliente: str) -> int:
    if not cliente:
        return 0
    init_db()
    with _conn() as cx:
        cur = cx.execute(
            "SELECT COUNT(*) FROM recibos WHERE LOWER(cliente_nombre) = LOWER(?)",
            [cliente.strip()],
        )
        row = cur.fetchone()
    return int(row[0]) if row else 0
