# utils/clientes.py
import sqlite3
from pathlib import Path
from config import DATA_DIR

DB = DATA_DIR / "db" / "clientes.db"
DB.parent.mkdir(parents=True, exist_ok=True)
DB.parent.mkdir(exist_ok=True)

def _conn():
    return sqlite3.connect(DB)

def init_db():
    with _conn() as cx:
        cx.execute("""
        CREATE TABLE IF NOT EXISTS clientes(
            id INTEGER PRIMARY KEY,
            nombre TEXT UNIQUE,
            cuit   TEXT UNIQUE,
            domicilio TEXT,
            localidad TEXT,
            iva TEXT
        );
        """)

def buscar_por_nombre_o_cuit(q: str):
    """
    Devuelve tupla (nombre, cuit, domicilio, localidad, iva) o None
    """
    q = (q or "").strip()
    if not q:
        return None
    with _conn() as cx:
        cur = cx.execute("""
            SELECT nombre, cuit, domicilio, localidad, iva
            FROM clientes
            WHERE lower(nombre) = lower(?)
               OR replace(cuit,'-','') = replace(?,'-','')
            LIMIT 1;
        """, [q, q])
        return cur.fetchone()

def upsert_cliente(nombre, cuit, domicilio, localidad, iva):
    """
    Inserta o actualiza por nombre (único) los datos del cliente.
    """
    nombre = (nombre or "").strip()
    with _conn() as cx:
        cx.execute("""
            INSERT INTO clientes(nombre, cuit, domicilio, localidad, iva)
            VALUES(?,?,?,?,?)
            ON CONFLICT(nombre) DO UPDATE SET
              cuit=excluded.cuit,
              domicilio=excluded.domicilio,
              localidad=excluded.localidad,
              iva=excluded.iva;
        """, [nombre, cuit, domicilio, localidad, iva])
