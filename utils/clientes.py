# utils/clientes.py
import sqlite3
import re
from pathlib import Path
from config import DATA_DIR

try:
    import openpyxl
except ModuleNotFoundError:
    openpyxl = None

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

def listar_clientes():
    """
    Devuelve lista de tuplas (nombre, cuit, domicilio, localidad, iva)
    ordenada alfabeticamente por nombre.
    """
    with _conn() as cx:
        cur = cx.execute(
            """
            SELECT nombre, cuit, domicilio, localidad, iva
            FROM clientes
            ORDER BY nombre COLLATE NOCASE;
            """
        )
        return cur.fetchall()

def importar_clientes_desde_excel(path):
    """
    Carga clientes desde un archivo Excel y devuelve resumen con
    cantidad de insertados, actualizados y omitidos.
    El Excel debe tener columnas como: Cliente/Nombre, Domicilio,
    Localidad, CUIT, IVA.
    """
    if openpyxl is None:
        raise ModuleNotFoundError("openpyxl no está instalado.")
    archivo = Path(path)
    if not archivo.exists():
        raise FileNotFoundError(f"No existe el archivo: {archivo}")

    libro = openpyxl.load_workbook(archivo)
    hoja = libro.active
    rows = list(hoja.iter_rows(values_only=True))
    if not rows:
        return {"insertados": 0, "actualizados": 0, "omitidos": 0}

    def _norm(valor):
        valor = str(valor or "").strip().lower()
        valor = re.sub(r"[^a-z0-9]+", "", valor)
        return valor

    alias = {
        "cliente": "nombre",
        "nombre": "nombre",
        "razonsocial": "nombre",
        "domicilio": "domicilio",
        "direccion": "domicilio",
        "direccioncomercial": "domicilio",
        "localidad": "localidad",
        "ciudad": "localidad",
        "cuit": "cuit",
        "cuitcuil": "cuit",
        "condicioniva": "iva",
        "ivadetalle": "iva",
        "iva": "iva",
    }

    headers = rows[0]
    indices = {}
    for idx, raw in enumerate(headers):
        key = alias.get(_norm(raw))
        if key and key not in indices:
            indices[key] = idx

    if "nombre" not in indices:
        raise ValueError("El Excel debe tener al menos una columna 'Cliente' o 'Nombre'.")

    insertados = actualizados = omitidos = 0
    for row in rows[1:]:
        if not row or all((c is None or str(c).strip() == "") for c in row):
            omitidos += 1
            continue
        def _get(campo):
            idx = indices.get(campo)
            if idx is None or idx >= len(row):
                return ""
            val = row[idx]
            if val is None:
                return ""
            return str(val).strip()

        nombre = _get("nombre")
        if not nombre:
            omitidos += 1
            continue
        datos_cliente = (
            _get("cuit"),
            _get("domicilio"),
            _get("localidad"),
            _get("iva"),
        )

        existente = buscar_por_nombre_o_cuit(nombre)
        upsert_cliente(nombre, *datos_cliente)
        if existente:
            actualizados += 1
        else:
            insertados += 1

    return {
        "insertados": insertados,
        "actualizados": actualizados,
        "omitidos": omitidos,
    }

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
