import os
import sqlite3 as sql

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database.db")


def get_connection():
    conn = sql.connect(DB_PATH)
    conn.row_factory = sql.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            prenom TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pdfs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            filepath TEXT NOT NULL UNIQUE,
            contenu TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE (user_id, filename)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pdf_id INTEGER NOT NULL,
            offre TEXT NOT NULL,
            score INTEGER,
            resultat TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (pdf_id) REFERENCES pdfs(id) ON DELETE CASCADE,
            UNIQUE (pdf_id, offre)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS entretiens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            pdf_id INTEGER NOT NULL,
            offre TEXT NOT NULL,
            live_session_id TEXT UNIQUE,
            transcription TEXT,
            evaluation TEXT,
            statut TEXT NOT NULL DEFAULT 'en_cours',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (pdf_id) REFERENCES pdfs(id) ON DELETE CASCADE
        )
    """)

    # Migration : ajoute la colonne contenu si la table pdfs existait déjà sans elle
    colonnes = [c["name"] for c in cursor.execute("PRAGMA table_info(pdfs)")]
    if "contenu" not in colonnes:
        cursor.execute("ALTER TABLE pdfs ADD COLUMN contenu TEXT")

    # Migration : ajoute l'identifiant de session GPT Live aux entretiens existants
    colonnes = [c["name"] for c in cursor.execute("PRAGMA table_info(entretiens)")]
    if "live_session_id" not in colonnes:
        cursor.execute("ALTER TABLE entretiens ADD COLUMN live_session_id TEXT")
        cursor.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_entretiens_live_session ON entretiens(live_session_id)"
        )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("Base de données initialisée.")
