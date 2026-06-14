"""
Database layer - .accdb via pyodbc + SQLite in-memory cache.
Writes go to both; reads come from SQLite only.
"""

import re
import sqlite3
import sys
from pathlib import Path
from datetime import datetime
import hashlib

DB_PATH: Path | None = None
_conn: sqlite3.Connection | None = None  # SQLite in-memory
_ac_conn = None  # pyodbc → .accdb

_ACCDB_TABLES = {"category", "product", "store_product",
                 "employee", "customer_card", "check", "sale", "auth"}

_ISO_DT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}$")


def _db() -> sqlite3.Connection:
    if _conn is None:
        raise RuntimeError("Database not initialized. Call db.init() first.")
    return _conn


def _dt(val) -> str | None:
    """Normalize Access date strings / datetime objects to ISO."""
    if val is None:
        return None
    if hasattr(val, "strftime"):
        return val.strftime("%Y-%m-%d %H:%M:%S")
    val = str(val).strip()
    if not val:
        return None
    for fmt in ("%m/%d/%y %H:%M:%S", "%m/%d/%Y %H:%M:%S",
                "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(val, fmt).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass
    return val


def _hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


def _to_ac_params(params):
    """Convert ISO datetime strings to datetime objects for pyodbc."""
    result = []
    for p in params:
        if isinstance(p, str) and _ISO_DT_RE.match(p):
            try:
                result.append(datetime.strptime(p, "%Y-%m-%d %H:%M:%S"))
                continue
            except ValueError:
                pass
        result.append(p)
    return result


def _ac_execute(sql: str, params=()):
    """Mirror a write to .accdb."""
    if _ac_conn is None:
        return
    m = re.search(r"(?:INTO|FROM|UPDATE)\s+\[?(\w+)\]?", sql, re.I)
    if not m or m.group(1).lower() not in _ACCDB_TABLES:
        return
    table = m.group(1).lower()
    # Access doesn't support INSERT OR IGNORE
    if re.match(r"INSERT\s+OR\s+IGNORE", sql, re.I):
        return
    # Access doesn't cascade delete, so remove Sale rows manually
    if table == "check" and re.match(r"\s*DELETE", sql, re.I):
        chk_m = re.search(r"check_number\s*=\s*\?", sql, re.I)
        if chk_m and params:
            try:
                _ac_conn.execute("DELETE FROM Sale WHERE check_number=?", (params[-1],))
            except Exception:
                pass
    # percent is reserved in Access SQL
    ac_sql = re.sub(r'\bpercent\b', '[percent]', sql, flags=re.I)
    try:
        _ac_conn.execute(ac_sql, _to_ac_params(list(params)))
        _ac_conn.commit()
    except Exception as exc:
        print(f"[accdb] {exc}  SQL={sql!r}", file=sys.stderr)


def _read_table_pyodbc(table: str) -> list[dict]:
    import pyodbc
    conn_str = (
        r"Driver={Microsoft Access Driver (*.mdb, *.accdb)};"
        f"DBQ={DB_PATH};"
    )
    try:
        ac = pyodbc.connect(conn_str)
    except pyodbc.Error:
        conn_str = (
            r"Driver={Microsoft Access Driver (*.mdb)};"
            f"DBQ={DB_PATH};"
        )
        ac = pyodbc.connect(conn_str)
    cur = ac.cursor()
    cur.execute(f"SELECT * FROM [{table}]")
    cols = [c[0] for c in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    ac.close()
    return rows


def _read_table(table: str) -> list[dict]:
    return _read_table_pyodbc(table)


def init(accdb_path: str):
    global DB_PATH, _conn, _ac_conn
    DB_PATH = Path(accdb_path)

    _conn = sqlite3.connect(":memory:", check_same_thread=False)
    _conn.row_factory = sqlite3.Row
    _conn.execute("PRAGMA foreign_keys = ON")

    import pyodbc
    conn_str = (
        r"Driver={Microsoft Access Driver (*.mdb, *.accdb)};"
        f"DBQ={DB_PATH};"
    )
    try:
        _ac_conn = pyodbc.connect(conn_str)
        _ac_conn.autocommit = False
    except pyodbc.Error:
        try:
            conn_str = (
                r"Driver={Microsoft Access Driver (*.mdb)};"
                f"DBQ={DB_PATH};"
            )
            _ac_conn = pyodbc.connect(conn_str)
            _ac_conn.autocommit = False
        except pyodbc.Error:
            _ac_conn = None

    _create_schema()
    _load_data()
    _ensure_auth_table()


def _create_schema():
    _db().executescript("""
    CREATE TABLE IF NOT EXISTS Category (
        category_number INTEGER PRIMARY KEY,
        category_name   TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS Product (
        id_product      INTEGER PRIMARY KEY,
        category_number INTEGER NOT NULL REFERENCES Category(category_number)
                        ON UPDATE CASCADE ON DELETE NO ACTION,
        product_name    TEXT NOT NULL,
        characteristics TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS Store_Product (
        UPC                 TEXT PRIMARY KEY,
        UPC_prom            TEXT REFERENCES Store_Product(UPC)
                            ON UPDATE CASCADE ON DELETE NO ACTION,
        id_product          INTEGER NOT NULL REFERENCES Product(id_product)
                            ON UPDATE CASCADE ON DELETE NO ACTION,
        selling_price       REAL NOT NULL CHECK(selling_price >= 0),
        products_number     INTEGER NOT NULL CHECK(products_number >= 0),
        promotional_product INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS Employee (
        id_employee     TEXT PRIMARY KEY,
        empl_surname    TEXT NOT NULL,
        empl_name       TEXT NOT NULL,
        empl_patronymic TEXT,
        empl_role       TEXT NOT NULL,
        salary          REAL NOT NULL CHECK(salary >= 0),
        date_of_birth   TEXT NOT NULL,
        date_of_start   TEXT NOT NULL,
        phone_number    TEXT NOT NULL,
        city            TEXT NOT NULL,
        street          TEXT NOT NULL,
        zip_code        TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS Customer_Card (
        card_number     TEXT PRIMARY KEY,
        cust_surname    TEXT NOT NULL,
        cust_name       TEXT NOT NULL,
        cust_patronymic TEXT,
        phone_number    TEXT NOT NULL,
        city            TEXT,
        street          TEXT,
        zip_code        TEXT,
        percent         INTEGER NOT NULL CHECK(percent >= 0)
    );
    CREATE TABLE IF NOT EXISTS [Check] (
        check_number TEXT PRIMARY KEY,
        id_employee  TEXT NOT NULL REFERENCES Employee(id_employee)
                     ON UPDATE CASCADE ON DELETE NO ACTION,
        card_number  TEXT REFERENCES Customer_Card(card_number)
                     ON UPDATE CASCADE ON DELETE NO ACTION,
        print_date   TEXT NOT NULL,
        sum_total    REAL NOT NULL CHECK(sum_total >= 0),
        vat          REAL NOT NULL CHECK(vat >= 0)
    );
    CREATE TABLE IF NOT EXISTS Sale (
        UPC            TEXT NOT NULL REFERENCES Store_Product(UPC)
                       ON UPDATE CASCADE ON DELETE NO ACTION,
        check_number   TEXT NOT NULL REFERENCES [Check](check_number)
                       ON UPDATE CASCADE ON DELETE CASCADE,
        product_number INTEGER NOT NULL CHECK(product_number > 0),
        selling_price  REAL NOT NULL CHECK(selling_price >= 0),
        PRIMARY KEY (UPC, check_number)
    );
    """)
    _db().commit()


def _str(v) -> str:
    return "" if v is None else str(v)


def _load_data():
    c = _db()

    for row in _read_table("Category"):
        c.execute("INSERT OR IGNORE INTO Category VALUES (?,?)",
                  (_str(row.get("category_number")), _str(row.get("category_name"))))

    for row in _read_table("Employee"):
        c.execute("INSERT OR IGNORE INTO Employee VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (
            _str(row["id_employee"]),
            _str(row["empl_surname"]),
            _str(row["empl_name"]),
            _str(row.get("empl_patronymic")) or None,
            _str(row["empl_role"]),
            float(row["salary"] or 0),
            _dt(row["date_of_birth"]),
            _dt(row["date_of_start"]),
            _str(row["phone_number"]),
            _str(row["city"]),
            _str(row["street"]),
            _str(row["zip_code"]),
        ))

    for row in _read_table("Customer_Card"):
        c.execute("INSERT OR IGNORE INTO Customer_Card VALUES (?,?,?,?,?,?,?,?,?)", (
            _str(row["card_number"]),
            _str(row["cust_surname"]),
            _str(row["cust_name"]),
            _str(row.get("cust_patronymic")) or None,
            _str(row["phone_number"]),
            _str(row.get("city")) or None,
            _str(row.get("street")) or None,
            _str(row.get("zip_code")) or None,
            int(row["percent"] or 0),
        ))

    for row in _read_table("Product"):
        c.execute("INSERT OR IGNORE INTO Product VALUES (?,?,?,?)", (
            int(row["id_product"]),
            int(row["category_number"]),
            _str(row["product_name"]),
            _str(row["characteristics"]),
        ))

    # non-promo rows first so FK references exist for promo rows
    sp_rows = _read_table("Store_Product")
    for row in sorted(sp_rows, key=lambda r: 1 if r.get("UPC_prom") else 0):
        promo_val = row.get("promotional_product")
        promo = int(bool(promo_val) if isinstance(promo_val, bool)
                    else int(promo_val or 0))
        c.execute("INSERT OR IGNORE INTO Store_Product VALUES (?,?,?,?,?,?)", (
            _str(row["UPC"]),
            _str(row.get("UPC_prom")) or None,
            int(row["id_product"]),
            float(row["selling_price"] or 0),
            int(row["products_number"] or 0),
            promo,
        ))

    for row in _read_table("Check"):
        c.execute('INSERT OR IGNORE INTO [Check] VALUES (?,?,?,?,?,?)', (
            _str(row["check_number"]),
            _str(row["id_employee"]),
            _str(row.get("card_number")) or None,
            _dt(row["print_date"]),
            float(row["sum_total"] or 0),
            float(row["vat"] or 0),
        ))

    for row in _read_table("Sale"):
        c.execute("INSERT OR IGNORE INTO Sale VALUES (?,?,?,?)", (
            _str(row["UPC"]),
            _str(row["check_number"]),
            int(row["product_number"] or 0),
            float(row["selling_price"] or 0),
        ))

    _db().commit()


def _ensure_auth_table():
    _db().execute("""
        CREATE TABLE IF NOT EXISTS Auth (
            id_employee   TEXT PRIMARY KEY REFERENCES Employee(id_employee),
            password_hash TEXT NOT NULL
        )
    """)
    _db().commit()

    if _ac_conn is not None:
        try:
            existing_tables = [
                t.table_name for t in _ac_conn.cursor().tables(tableType="TABLE")
            ]
            if "Auth" not in existing_tables:
                _ac_conn.execute("""
                    CREATE TABLE Auth (
                        id_employee   TEXT(50) NOT NULL,
                        password_hash TEXT(64) NOT NULL,
                        CONSTRAINT pk_auth PRIMARY KEY (id_employee)
                    )
                """)
                _ac_conn.commit()
        except Exception as exc:
            print(f"[auth create] {exc}", file=sys.stderr)

    if _ac_conn is not None:
        try:
            for row in _ac_conn.execute("SELECT id_employee, password_hash FROM Auth").fetchall():
                _db().execute("INSERT OR IGNORE INTO Auth VALUES (?,?)", (row[0], row[1]))
            _db().commit()
        except Exception as exc:
            print(f"[auth load] {exc}", file=sys.stderr)

    # set default password (= id lowercase) for employees without one
    for emp in fetchall("SELECT id_employee FROM Employee"):
        eid = emp["id_employee"]
        if not fetchone("SELECT id_employee FROM Auth WHERE id_employee=?", (eid,)):
            ph = _hash_pw(eid.lower())
            _db().execute("INSERT OR IGNORE INTO Auth VALUES (?,?)", (eid, ph))
            if _ac_conn is not None:
                try:
                    _ac_conn.execute("INSERT INTO Auth VALUES (?,?)", (eid, ph))
                    _ac_conn.commit()
                except Exception as exc:
                    print(f"[auth default pw] {exc}", file=sys.stderr)
    _db().commit()


def get_conn() -> sqlite3.Connection:
    return _db()


def fetchall(sql: str, params=()) -> list[sqlite3.Row]:
    return _db().execute(sql, params).fetchall()


def fetchone(sql: str, params=()):
    return _db().execute(sql, params).fetchone()


def execute(sql: str, params=()):
    cur = _db().execute(sql, params)
    _db().commit()
    _ac_execute(sql, params)
    return cur


def authenticate(employee_id: str, password: str):
    ph = _hash_pw(password)
    return fetchone(
        "SELECT e.* FROM Employee e JOIN Auth a ON e.id_employee=a.id_employee "
        "WHERE a.id_employee=? AND a.password_hash=?",
        (employee_id, ph)
    )


def change_password(employee_id: str, new_password: str):
    execute("UPDATE Auth SET password_hash=? WHERE id_employee=?",
            (_hash_pw(new_password), employee_id))


def next_employee_id() -> str:
    row = fetchone("SELECT MAX(CAST(SUBSTR(id_employee,2) AS INT)) as m FROM Employee")
    return f"E{(row['m'] or 0) + 1:03d}"


def next_check_number() -> str:
    row = fetchone("SELECT MAX(CAST(SUBSTR(check_number,3) AS INT)) as m FROM [Check]")
    return f"CH{(row['m'] or 0) + 1:08d}"


def next_card_number() -> str:
    row = fetchone("SELECT MAX(CAST(SUBSTR(card_number,3) AS INT)) as m FROM Customer_Card")
    return f"CC{(row['m'] or 0) + 1:010d}"


def next_product_id() -> int:
    row = fetchone("SELECT MAX(id_product) as m FROM Product")
    return (row["m"] or 0) + 1


def next_upc(promo=False) -> str:
    flt = "WHERE promotional_product=1" if promo else "WHERE promotional_product=0"
    row = fetchone(f"SELECT MAX(CAST(UPC AS INT)) as m FROM Store_Product {flt}")
    return f"{(row['m'] or 0) + 1:012d}"
