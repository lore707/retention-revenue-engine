"""Persistenza locale dei profili e degli eventi, separando recapiti e acquisti."""

import json
from pathlib import Path
import sqlite3


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.execute("PRAGMA foreign_keys = ON")
        with self.connection:
            self.connection.executescript("""
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
            """)

    def close(self):
        self.connection.close()

    def load_state(self):
        profiles = {
            profile_id: {"customer_id": profile_id, "orders": json.loads(orders_json)}
            for profile_id, orders_json in self.connection.execute(
                "SELECT id, orders_json FROM profiles ORDER BY id"
            )
        }
        contacts = {
            profile_id: {"email": email}
            for profile_id, email in self.connection.execute(
                "SELECT profile_id, email FROM contacts ORDER BY profile_id"
            )
        }
        unassigned = {
            order_id: json.loads(order_json)
            for order_id, order_json in self.connection.execute(
                "SELECT id, order_json FROM unassigned_orders ORDER BY id"
            )
        }
        return {"profiles": profiles, "contacts": contacts, "unassigned_orders": unassigned}

    def save_state(self, state, imports=()):
        if set(state["profiles"]) != set(state["contacts"]):
            raise ValueError("Ogni profilo deve avere un recapito separato.")
        with self.connection:
            for profile_id, profile in state["profiles"].items():
                self.connection.execute(
                    "INSERT INTO profiles(id, orders_json) VALUES (?, ?) "
                    "ON CONFLICT(id) DO UPDATE SET orders_json=excluded.orders_json",
                    (profile_id, json.dumps(profile["orders"], ensure_ascii=False)),
                )
                self.connection.execute(
                    "INSERT INTO contacts(profile_id, email) VALUES (?, ?) "
                    "ON CONFLICT(profile_id) DO UPDATE SET email=excluded.email",
                    (profile_id, state["contacts"][profile_id]["email"]),
                )
            self.connection.execute("DELETE FROM unassigned_orders")
            self.connection.executemany(
                "INSERT INTO unassigned_orders(id, order_json) VALUES (?, ?)",
                ((order_id, json.dumps(order, ensure_ascii=False))
                 for order_id, order in state["unassigned_orders"].items()),
            )
            self.connection.executemany(
                "INSERT INTO imports(filename, sha256) VALUES (?, ?)", imports,
            )

    def import_history(self):
        return [dict(sequence=sequence, filename=filename, sha256=digest)
                for sequence, filename, digest in self.connection.execute(
                    "SELECT sequence, filename, sha256 FROM imports ORDER BY sequence"
                )]

    def activation_date(self):
        row = self.connection.execute(
            "SELECT value FROM settings WHERE key='activation_date'"
        ).fetchone()
        return row[0] if row else None

    def contact_email(self, profile_id):
        row = self.connection.execute(
            "SELECT email FROM contacts WHERE profile_id=?", (profile_id,)
        ).fetchone()
        return row[0] if row else None

    def activate(self, day):
        existing = self.activation_date()
        if existing and existing != day:
            raise ValueError("Lo storico è già stato attivato con un'altra data.")
        with self.connection:
            self.connection.execute(
                "INSERT OR IGNORE INTO settings(key, value) VALUES ('activation_date', ?)",
                (day,),
            )

    def events_for(self, profile_id):
        return [json.loads(row[0]) for row in self.connection.execute(
            "SELECT event_json FROM events WHERE profile_id=? ORDER BY id", (profile_id,)
        )]

    def event_by_id(self, event_id):
        row = self.connection.execute(
            "SELECT profile_id, event_json FROM events WHERE id=?", (event_id,)
        ).fetchone()
        return (row[0], json.loads(row[1])) if row else None

    def verified_purchase_for_order(self, order_id):
        for profile_id, payload in self.connection.execute(
            "SELECT profile_id, event_json FROM events"
        ):
            event = json.loads(payload)
            if (event.get("type") == "verified_purchase"
                    and event.get("shopify_order_id") == order_id):
                return profile_id, event
        return None

    def revenue_events(self):
        events = []
        for profile_id, payload in self.connection.execute(
            "SELECT profile_id, event_json FROM events ORDER BY rowid"
        ):
            event = json.loads(payload)
            if event.get("type") in {"verified_purchase", "revenue_correction"}:
                events.append((profile_id, event))
        return events

    def add_event(self, profile_id, event):
        payload = json.dumps(event, ensure_ascii=False, sort_keys=True)
        row = self.connection.execute(
            "SELECT profile_id, event_json FROM events WHERE id=?", (event["id"],)
        ).fetchone()
        if row:
            if row != (profile_id, payload):
                raise ValueError("ID evento già presente con dati diversi.")
            return
        with self.connection:
            self.connection.execute(
                "INSERT INTO events(id, profile_id, event_json) VALUES (?, ?, ?)",
                (event["id"], profile_id, payload),
            )
