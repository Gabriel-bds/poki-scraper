"""SQLite storage for Poki game data and daily rating snapshots."""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "poki.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS games (
    slug TEXT PRIMARY KEY,
    name TEXT,
    studio TEXT,
    category TEXT,
    url TEXT,
    published_date TEXT,   -- datePublished declarado pelo Poki
    first_seen_date TEXT,  -- primeira vez que o nosso scraper viu esse jogo no site
    last_seen_date TEXT    -- última vez que o jogo apareceu no sitemap (ainda ativo)
);

CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    slug TEXT NOT NULL REFERENCES games(slug),
    snapshot_date TEXT NOT NULL,
    rating_value REAL,
    rating_count INTEGER,
    UNIQUE(slug, snapshot_date)
);
"""


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn):
    conn.executescript(SCHEMA)
    conn.commit()


def upsert_game(conn, slug, name, studio, category, url, published_date, today):
    """Insere o jogo se for novo (first_seen_date = today) ou atualiza os dados existentes."""
    row = conn.execute("SELECT first_seen_date FROM games WHERE slug = ?", (slug,)).fetchone()
    is_new = row is None
    first_seen = row[0] if row else today
    conn.execute(
        """
        INSERT INTO games (slug, name, studio, category, url, published_date, first_seen_date, last_seen_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(slug) DO UPDATE SET
            name=excluded.name,
            studio=excluded.studio,
            category=excluded.category,
            url=excluded.url,
            published_date=excluded.published_date,
            last_seen_date=excluded.last_seen_date
        """,
        (slug, name, studio, category, url, published_date, first_seen, today),
    )
    return is_new


def insert_snapshot(conn, slug, snapshot_date, rating_value, rating_count):
    conn.execute(
        """
        INSERT INTO snapshots (slug, snapshot_date, rating_value, rating_count)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(slug, snapshot_date) DO UPDATE SET
            rating_value=excluded.rating_value,
            rating_count=excluded.rating_count
        """,
        (slug, snapshot_date, rating_value, rating_count),
    )
