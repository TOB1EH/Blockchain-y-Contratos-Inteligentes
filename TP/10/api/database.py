"""
Módulo de acceso a la base de datos SQLite para la API CFP.
"""

import json
import sqlite3
import os
from contextlib import contextmanager

# Ruta por defecto de la base de datos, sobreescribible con variable de entorno
DB_PATH = os.environ.get("CFP_DB_PATH", "cfp.db")

def get_connection():
    """Abre una conexión a la base de datos y activa las foreign keys."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row   # permite acceder a las columnas por nombre

    # Habilitar el modo WAL para mejorar concurrencia de lectura/escritura y evitar bloqueos
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

# Context manager es un patrón de diseño que permite gestionar recursos (como conexiones a
# bases de datos) de forma segura y automática, asegurando que se cierren correctamente
# incluso si ocurre un error.
@contextmanager
def transaction():
    """Context manager que abre una conexión, hace commit o rollback automático."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Crea las tablas si no existen y garantiza que admin_state tenga una fila."""
    with transaction() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS registrations (
                address     TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                nonce       INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS calls (
                call_id     TEXT PRIMARY KEY,
                title       TEXT NOT NULL,
                description TEXT NOT NULL,
                creator     TEXT,
                cfp_address TEXT,
                status      TEXT NOT NULL DEFAULT 'pending'
            );

            CREATE TABLE IF NOT EXISTS proposals (
                proposal_id  TEXT PRIMARY KEY,
                call_id      TEXT NOT NULL,
                title        TEXT NOT NULL,
                description  TEXT NOT NULL,
                proof_json   TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS admin_state (
                id    INTEGER PRIMARY KEY DEFAULT 1,
                nonce INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS deliveries (
                proposal_id TEXT PRIMARY KEY,
                call_id     TEXT NOT NULL,
                sender      TEXT NOT NULL,
                files_root  TEXT NOT NULL,
                delivered_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS proposal_files (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                proposal_id TEXT NOT NULL,
                file_hash   TEXT NOT NULL,
                file_name   TEXT NOT NULL,
                file_path   TEXT NOT NULL,
                FOREIGN KEY(proposal_id) REFERENCES deliveries(proposal_id)
            );
        """)

        # Garantizar que exista exactamente una fila en admin_state
        conn.execute(
            "INSERT OR IGNORE INTO admin_state (id, nonce) VALUES (1, 1)"
        )

def get_registration(address: str) -> dict | None:
    """Devuelve el registro de una dirección o None si no existe."""
    with transaction() as conn:
        row = conn.execute(
            "SELECT * FROM registrations WHERE address = ?",
            (address.lower(),)
        ).fetchone()
    return dict(row) if row else None


def get_all_registrations() -> list:
    """Devuelve todos los registros."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT address, name, nonce FROM registrations ORDER BY address"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def upsert_registration(address: str, name: str) -> None:
    """
    Inserta o reemplaza un registro.
    En un re-registro, reemplaza el registro completo reseteando el nonce a 1.
    """
    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO registrations (address, name, nonce)
            VALUES (?, ?, 1)
            ON CONFLICT(address) DO UPDATE SET
                name  = excluded.name,
                nonce = 1
            """,
            (address.lower(), name)
        )


def update_registration_name(address: str, name: str) -> None:
    """Actualiza el nombre e incrementa el nonce de un registro existente."""
    with transaction() as conn:
        conn.execute(
            "UPDATE registrations SET name = ?, nonce = nonce + 1 WHERE address = ?",
            (name, address.lower())
        )


def delete_registration(address: str) -> None:
    """Elimina el registro de una dirección."""
    with transaction() as conn:
        conn.execute(
            "DELETE FROM registrations WHERE address = ?",
            (address.lower(),)
        )


def get_call(call_id: str) -> dict | None:
    """Devuelve los datos de un llamado o None si no existe."""
    with transaction() as conn:
        row = conn.execute(
            "SELECT * FROM calls WHERE call_id = ?",
            (call_id.lower(),)
        ).fetchone()
    return dict(row) if row else None


def get_all_calls(creator: str | None = None) -> list:
    """Devuelve todos los llamados en estado 'created', opcionalmente filtrados por creador."""
    conn = get_connection()
    if creator:
        rows = conn.execute(
            "SELECT * FROM calls WHERE status = 'created' AND creator = ? ORDER BY call_id",
            (creator.lower(),)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM calls WHERE status = 'created' ORDER BY call_id"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def insert_call(call_id: str, title: str, description: str) -> None:
    """Inserta un llamado nuevo en estado pending."""
    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO calls (call_id, title, description, status)
            VALUES (?, ?, ?, 'pending')
            """,
            (call_id.lower(), title, description)
        )


def update_call_created(call_id: str, creator: str, cfp_address: str) -> None:
    """Marca un llamado como creado on-chain con su creador y dirección de contrato."""
    with transaction() as conn:
        conn.execute(
            """
            UPDATE calls
            SET status = 'created', creator = ?, cfp_address = ?
            WHERE call_id = ?
            """,
            (creator, cfp_address, call_id.lower())
        )

def get_proposal(proposal_id: str) -> dict | None:
    """Devuelve los datos de una propuesta registrada via API, o None."""
    with transaction() as conn:
        row = conn.execute(
            "SELECT * FROM proposals WHERE proposal_id = ?",
            (proposal_id.lower(),)
        ).fetchone()
    return dict(row) if row else None


def insert_proposal(
    proposal_id: str, call_id: str, title: str, description: str, proof: dict
) -> None:
    """Inserta una propuesta con sus pruebas de Merkle."""
    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO proposals (proposal_id, call_id, title, description, proof_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                proposal_id.lower(),
                call_id.lower(),
                title,
                description,
                json.dumps(proof)
            )
        )

def get_admin_nonce() -> int:
    """Devuelve el nonce actual del administrador."""
    with transaction() as conn:
        row = conn.execute(
            "SELECT nonce FROM admin_state WHERE id = 1"
        ).fetchone()
    return row["nonce"]


def increment_admin_nonce() -> int:
    """Incrementa el nonce del administrador y devuelve el nuevo valor."""
    with transaction() as conn:
        conn.execute(
            "UPDATE admin_state SET nonce = nonce + 1 WHERE id = 1"
        )
        row = conn.execute(
            "SELECT nonce FROM admin_state WHERE id = 1"
        ).fetchone()
    return row["nonce"]

def get_delivery(proposal_id: str) -> dict | None:
    with transaction() as conn:
        row = conn.execute(
            "SELECT * FROM deliveries WHERE proposal_id = ?",
            (proposal_id.lower(),)
        ).fetchone()
    return dict(row) if row else None

def insert_delivery(proposal_id: str, call_id: str, sender: str, files_root: str) -> None:
    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO deliveries (proposal_id, call_id, sender, files_root)
            VALUES (?, ?, ?, ?)
            """,
            (proposal_id.lower(), call_id.lower(), sender, files_root.lower())
        )

def insert_proposal_file(proposal_id: str, file_hash: str, file_name: str, file_path: str) -> None:
    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO proposal_files (proposal_id, file_hash, file_name, file_path)
            VALUES (?, ?, ?, ?)
            """,
            (proposal_id.lower(), file_hash.lower(), file_name, file_path)
        )

def get_proposal_files(proposal_id: str) -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT file_hash, file_name, file_path FROM proposal_files WHERE proposal_id = ?",
        (proposal_id.lower(),)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
