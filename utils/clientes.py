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
    """
    Crea la tabla si no existe y migra esquemas antiguos que tenían
    restricción UNIQUE en CUIT.
    - Clave única: solo 'nombre'.
    - 'cuit' ya NO es único para permitir clientes con mismo CUIT.
    """
    with _conn() as cx:
        # Crear si no existe con el esquema correcto (cuit sin UNIQUE)
        cx.execute(
            """
            CREATE TABLE IF NOT EXISTS clientes(
                id INTEGER PRIMARY KEY,
                nombre TEXT UNIQUE,
                cuit   TEXT,
                domicilio TEXT,
                localidad TEXT,
                iva TEXT
            );
            """
        )

        # Detectar si la tabla existente aún tiene 'cuit TEXT UNIQUE'
        cur = cx.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='clientes'")
        row = cur.fetchone()
        sql_def = row[0] if row else ""
        if "cuit   TEXT UNIQUE" in (sql_def or ""):
            # Migrar: recrear sin UNIQUE en CUIT
            cx.execute(
                """
                CREATE TABLE IF NOT EXISTS clientes__new(
                    id INTEGER PRIMARY KEY,
                    nombre TEXT UNIQUE,
                    cuit   TEXT,
                    domicilio TEXT,
                    localidad TEXT,
                    iva TEXT
                );
                """
            )
            # Copiar datos
            cx.execute(
                """
                INSERT OR IGNORE INTO clientes__new(id, nombre, cuit, domicilio, localidad, iva)
                SELECT id, nombre, cuit, domicilio, localidad, iva FROM clientes;
                """
            )
            # Reemplazar tabla
            cx.execute("DROP TABLE clientes")
            cx.execute("ALTER TABLE clientes__new RENAME TO clientes")

def buscar_por_nombre_o_cuit(q: str):
    """
    Devuelve tupla (nombre, cuit, domicilio, localidad, iva) o None.
    Búsqueda SOLO por nombre exacto (insensible a mayúsculas/minúsculas).
    Ya no se busca por CUIT para evitar ambigüedades.
    """
    q = (q or "").strip()
    if not q:
        return None
    with _conn() as cx:
        cur = cx.execute(
            """
            SELECT nombre, cuit, domicilio, localidad, iva
            FROM clientes
            WHERE lower(nombre) = lower(?)
            LIMIT 1;
            """,
            [q],
        )
        return cur.fetchone()

def upsert_cliente(nombre, cuit, domicilio, localidad, iva):
    """
    Inserta o actualiza por nombre (único) los datos del cliente.
    """
    nombre = (nombre or "").strip()
    with _conn() as cx:
        cx.execute(
            """
            INSERT INTO clientes(nombre, cuit, domicilio, localidad, iva)
            VALUES(?,?,?,?,?)
            ON CONFLICT(nombre) DO UPDATE SET
              cuit=excluded.cuit,
              domicilio=excluded.domicilio,
              localidad=excluded.localidad,
              iva=excluded.iva;
            """,
            [nombre, cuit, domicilio, localidad, iva],
        )
