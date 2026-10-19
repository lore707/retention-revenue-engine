"""Persistenza SQLite/PostgreSQL, separando recapiti e acquisti."""

from contextlib import contextmanager
import json
import os
from pathlib import Path
import sqlite3
import tempfile


TABLE_COLUMNS = {
    "profiles": "id, orders_json", "contacts": "profile_id, email",
    "unassigned_orders": "id, order_json", "events": "id, profile_id, event_json",
    "settings": "key, value", "imports": "sequence, filename, sha256",
}


class Store:
    def __init__(self, path, *, initialize=True):
        self.database = str(path)
        self.postgres = self.database.startswith(("postgresql://", "postgres://"))
        if "://" in self.database and not self.postgres:
            raise ValueError("Usare una stringa PostgreSQL oppure un percorso SQLite, non l'URL del sito.")
        self.path = None if self.postgres else Path(path)
        if self.postgres:
            import psycopg
            try:
                self.connection = psycopg.connect(self.database, autocommit=True, connect_timeout=10,
                                                  sslmode="require", prepare_threshold=None)
            except psycopg.Error:
                raise ValueError("Connessione PostgreSQL non riuscita: verificare configurazione e disponibilità.") from None
            if initialize:
                self.connection.execute("CREATE SCHEMA IF NOT EXISTS retention")
                self.connection.execute("REVOKE ALL ON SCHEMA retention FROM PUBLIC")
            self.connection.execute("SET search_path TO retention")
        else:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.connection = sqlite3.connect(self.path)
            self.connection.execute("PRAGMA foreign_keys = ON")
        if not initialize:
            return
        schema = """
                CREATE TABLE IF NOT EXISTS profiles (
                    id TEXT PRIMARY KEY, orders_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS contacts (
                    profile_id TEXT PRIMARY KEY REFERENCES profiles(id),
                    email TEXT NOT NULL UNIQUE
                );
                CREATE TABLE IF NOT EXISTS unassigned_orders (
                    id TEXT PRIMARY KEY, order_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    profile_id TEXT NOT NULL REFERENCES profiles(id),
                    event_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY, value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS imports (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    sha256 TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS events_by_profile ON events(profile_id);
            """
        if self.postgres:
            schema = schema.replace("sequence INTEGER PRIMARY KEY AUTOINCREMENT", "sequence BIGSERIAL PRIMARY KEY")
            schema = schema.replace("CREATE TABLE IF NOT EXISTS events (", "CREATE TABLE IF NOT EXISTS events (sequence BIGSERIAL UNIQUE,")
        with self._transaction():
            for statement in schema.split(";"):
                if statement.strip():
                    self._execute(statement)

    @contextmanager
    def _transaction(self):
        with self.connection.transaction() if self.postgres else self.connection:
            yield

    def _execute(self, query, parameters=()):
        return self.connection.execute(query.replace("?", "%s") if self.postgres else query, parameters)

    def _executemany(self, query, parameters):
        cursor = self.connection.cursor()
        try:
            cursor.executemany(query.replace("?", "%s") if self.postgres else query, parameters)
        finally:
            cursor.close()

    def close(self):
        self.connection.close()

    def load_state(self):
        profiles = {
            profile_id: {"customer_id": profile_id, "orders": json.loads(orders_json)}
            for profile_id, orders_json in self._execute(
                "SELECT id, orders_json FROM profiles ORDER BY id"
            )
        }
        contacts = {
            profile_id: {"email": email}
            for profile_id, email in self._execute(
                "SELECT profile_id, email FROM contacts ORDER BY profile_id"
            )
        }
        unassigned = {
            order_id: json.loads(order_json)
            for order_id, order_json in self._execute(
                "SELECT id, order_json FROM unassigned_orders ORDER BY id"
            )
        }
        return {"profiles": profiles, "contacts": contacts, "unassigned_orders": unassigned}

    def save_state(self, state, imports=()):
        if set(state["profiles"]) != set(state["contacts"]):
            raise ValueError("Ogni profilo deve avere un recapito separato.")
        with self._transaction():
            self._executemany(
                "INSERT INTO profiles(id, orders_json) VALUES (?, ?) "
                "ON CONFLICT(id) DO UPDATE SET orders_json=excluded.orders_json",
                ((profile_id, json.dumps(profile["orders"], ensure_ascii=False))
                 for profile_id, profile in state["profiles"].items()),
            )
            self._executemany(
                "INSERT INTO contacts(profile_id, email) VALUES (?, ?) "
                "ON CONFLICT(profile_id) DO UPDATE SET email=excluded.email",
                ((profile_id, state["contacts"][profile_id]["email"]) for profile_id in state["profiles"]),
            )
            self._execute("DELETE FROM unassigned_orders")
            self._executemany(
                "INSERT INTO unassigned_orders(id, order_json) VALUES (?, ?)",
                ((order_id, json.dumps(order, ensure_ascii=False))
                 for order_id, order in state["unassigned_orders"].items()),
            )
            self._executemany(
                "INSERT INTO imports(filename, sha256) VALUES (?, ?)", imports,
            )

    def import_history(self):
        return [dict(sequence=sequence, filename=filename, sha256=digest)
                for sequence, filename, digest in self._execute(
                    "SELECT sequence, filename, sha256 FROM imports ORDER BY sequence"
                )]

    def activation_date(self):
        row = self._execute(
            "SELECT value FROM settings WHERE key='activation_date'"
        ).fetchone()
        return row[0] if row else None

    def contact_email(self, profile_id):
        row = self._execute(
            "SELECT email FROM contacts WHERE profile_id=?", (profile_id,)
        ).fetchone()
        return row[0] if row else None

    def activate(self, day):
        existing = self.activation_date()
        if existing and existing != day:
            raise ValueError("Lo storico è già stato attivato con un'altra data.")
        with self._transaction():
            self._execute(
                "INSERT INTO settings(key, value) VALUES ('activation_date', ?) ON CONFLICT(key) DO NOTHING",
                (day,),
            )

    def events_for(self, profile_id):
        return [json.loads(row[0]) for row in self._execute(
            "SELECT event_json FROM events WHERE profile_id=? ORDER BY id", (profile_id,)
        )]

    def events_by_customer(self):
        result = {}
        for profile_id, payload in self._execute("SELECT profile_id, event_json FROM events ORDER BY id"):
            result.setdefault(profile_id, []).append(json.loads(payload))
        return result

    def event_by_id(self, event_id):
        row = self._execute(
            "SELECT profile_id, event_json FROM events WHERE id=?", (event_id,)
        ).fetchone()
        return (row[0], json.loads(row[1])) if row else None

    def verified_purchase_for_order(self, order_id):
        for profile_id, payload in self._execute(
            "SELECT profile_id, event_json FROM events"
        ):
            event = json.loads(payload)
            if (event.get("type") == "verified_purchase"
                    and event.get("shopify_order_id") == order_id):
                return profile_id, event
        return None

    def revenue_events(self):
        events = []
        for profile_id, payload in self._execute(
            "SELECT profile_id, event_json FROM events ORDER BY " + ("sequence" if self.postgres else "rowid")
        ):
            event = json.loads(payload)
            if event.get("type") in {"verified_purchase", "revenue_correction"}:
                events.append((profile_id, event))
        return events

    def add_event(self, profile_id, event):
        payload = json.dumps(event, ensure_ascii=False, sort_keys=True)
        row = self._execute(
            "SELECT profile_id, event_json FROM events WHERE id=?", (event["id"],)
        ).fetchone()
        if row:
            if row != (profile_id, payload):
                raise ValueError("ID evento già presente con dati diversi.")
            return
        with self._transaction():
            self._execute(
                "INSERT INTO events(id, profile_id, event_json) VALUES (?, ?, ?)",
                (event["id"], profile_id, payload),
            )

    def _snapshot(self):
        result = {}
        for table, columns in TABLE_COLUMNS.items():
            order = ("sequence" if self.postgres else "rowid") if table == "events" else columns.split(",")[0]
            result[table] = list(self._execute(f"SELECT {columns} FROM {table} ORDER BY {order}"))
        return result


def migrate_sqlite(source_path, destination):
    """Copia verificata verso uno store vuoto; non sovrascrive dati già presenti."""
    source_path = Path(source_path).resolve(strict=True)
    with tempfile.NamedTemporaryFile(prefix=source_path.stem + "-migration-", suffix=".sqlite3",
                                     dir=source_path.parent, delete=False) as file:
        backup_path = Path(file.name)
    source = sqlite3.connect(source_path.as_uri() + "?mode=ro", uri=True)
    backup = sqlite3.connect(backup_path)
    try:
        source.backup(backup)
    finally:
        backup.close()
        source.close()
    copy = Store(backup_path)
    try:
        expected = copy._snapshot()
    finally:
        copy.close()
    with destination._transaction():
        if destination.postgres:
            destination._execute("LOCK TABLE " + ", ".join(TABLE_COLUMNS) + " IN ACCESS EXCLUSIVE MODE")
        else:
            destination._execute("BEGIN IMMEDIATE")
        if any(destination._snapshot().values()):
            raise ValueError("Destinazione non vuota: migrazione interrotta senza sovrascrivere dati.")
        for table, columns in TABLE_COLUMNS.items():
            placeholders = ", ".join("?" for _ in columns.split(","))
            destination._executemany(f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", expected[table])
        if destination.postgres:
            destination._execute("SELECT setval(pg_get_serial_sequence('imports', 'sequence'), ?, false)",
                                 (max((row[0] for row in expected["imports"]), default=0) + 1,))
        if destination._snapshot() != expected:
            raise ValueError("Verifica della copia fallita: migrazione annullata.")
    return {"backup": str(backup_path), "rows": {table: len(rows) for table, rows in expected.items()}}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Migrazione verificata SQLite → PostgreSQL, con backup locale.")
    parser.add_argument("--source", type=Path, default=Path("local-data/retention.sqlite3"))
    arguments = parser.parse_args()
    destination_url = os.environ.get("DATABASE_URL", "")
    if not destination_url.startswith(("postgresql://", "postgres://")):
        parser.error("Impostare DATABASE_URL nelle variabili di ambiente, senza passarla nella riga di comando.")
    target = None
    try:
        target = Store(destination_url)
        print(json.dumps(migrate_sqlite(arguments.source, target)))
    except Exception:
        parser.exit(1, "Migrazione non completata. Controllare connessione, credenziali e destinazione vuota. Nessuna credenziale è stata mostrata.\n")
    finally:
        if target:
            target.close()
