"""Server della dashboard, locale o protetto su Render, senza dipendenze aggiuntive."""

import argparse
from contextlib import nullcontext
from base64 import b64encode
from datetime import datetime
from email.parser import BytesParser
from email.policy import default
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
from secrets import compare_digest
import tempfile
from threading import Lock
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo

from src.customer_profiles import (activate_history, evaluate_day, explain_order, import_into_store,
                                   merge_orders, overview_summary, retention_summary, record_event, plan_detail, filter_retention, rules_summary)
from src.shopify_orders import sanitize_export
from src.storage import Store

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"


def demo_store(path):
    """Fixture sintetica del design, valutata dalle regole reali."""
    store = Store(path)
    specifications = [
        ("DEMO-04490", "2026-08-18", ["CR05186", "CL51809", "CP34473", "30101-000092", "30101-000041"]),
        ("DEMO-05873", "2026-03-20", ["CP96308", "30103-000019"]),
        ("DEMO-01842", "2026-09-17", ["CR05186"]),
        ("DEMO-02921", "2026-09-10", ["CP96308"]),
        ("DEMO-03001", "2026-09-17", ["CR05186", "CL51809", "30101-000092", "30101-000041"]),
        ("DEMO-03002", "2026-09-17", ["CP38476", "30101-000041"]),
        ("DEMO-03003", "2026-09-17", ["CR05272", "CL51809", "30101-000092", "30101-000041"]),
        *[(f"DEMO-SALE-{i}", "2026-08-01", ["CP96308"]) for i in range(4)],
    ]
    state = None
    for customer, day, skus in specifications:
        order = {"id": customer, "number": "#" + customer, "date": day, "marketing_signal": "yes",
                 "lines": [{"id": customer + ":" + sku, "order_id": customer, "sku": sku,
                            "date": day, "validity": "valid", "quantity": 1} for sku in skus]}
        state = merge_orders(state, {"orders": [order], "order_contacts": {
            customer: {"email": customer.lower() + "@example.invalid"}}})
        generated = next(key for key, value in state["profiles"].items() if customer in value["orders"])
        state["profiles"][customer] = state["profiles"].pop(generated)
        state["contacts"][customer] = state["contacts"].pop(generated)
    store.save_state(state)
    activate_history(store, "2026-08-01")
    for i in range(4):
        customer = f"DEMO-SALE-{i}"
        plan = next(item["plan"] for item in evaluate_day(store, "2026-08-20")["ready"]
                    if item["customer_id"] == customer)
        for attempt, day in enumerate(["2026-08-20", "2026-09-04"]):
            record_event(store, customer, {"id": f"CONTACT-{i}-{attempt}", "type": "contact", "date": day,
                         "rule_id": plan["primary_opportunity"]["rule_id"],
                         "channel": "email", "plan_key": plan["plan_key"],
                         "primary_opportunity_key": plan["primary_opportunity"]["opportunity_key"],
                         "included_opportunity_keys": plan["included_opportunity_keys"]})
        if i < 3:
            day = ["2026-09-08", "2026-09-16", "2026-09-25"][i]
            record_event(store, customer, {"id": f"SALE-{i}", "type": "verified_purchase", "date": day,
                         "purchase_date": day, "plan_key": plan["plan_key"], "shopify_order_id": f"DEMO-ORDER-{i}",
                         "purchased_sku": "30103-000019", "amount_minor": [2999, 2999, 1999][i],
                         "currency": "EUR", "verified_in_shopify": True, "contact_event_id": f"CONTACT-{i}-1"})
    return store


def make_handler(store, *, demo=False, as_of=None, credentials=None, public_origin=None):
    write_lock = Lock()
    authorization = b"Basic " + b64encode(":".join(credentials).encode("utf-8")) if credentials else None

    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(10)
            self._store = None

        @property
        def store(self):
            if self._store is None:
                self._store = Store(store.database, initialize=False)
            return self._store

        def finish(self):
            try:
                super().finish()
            finally:
                if self._store is not None:
                    self._store.close()

        def reply(self, status, payload, content_type="application/json; charset=utf-8", headers=None):
            body = json.dumps(payload, ensure_ascii=False).encode() if isinstance(payload, dict) else payload
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "same-origin")
            for name, value in (headers or {}).items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(body)

        def authorized(self):
            if authorization is None or compare_digest(
                    self.headers.get("Authorization", "").encode("utf-8"), authorization):
                return True
            self.reply(401, {"error": "Accesso riservato."}, headers={
                "WWW-Authenticate": 'Basic realm="Retention Revenue Engine", charset="UTF-8"'})
            return False

        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path == "/healthz":
                self.reply(200, {"status": "ok"})
                return
            if not self.authorized():
                return
            day = as_of or datetime.now(ZoneInfo("Europe/Rome")).date().isoformat()
            try:
                query = parse_qs(parsed.query)
                if parsed.path == "/api/overview":
                    data = overview_summary(self.store, day, query.get("period", ["30d"])[0])
                    data["demo"] = demo
                    self.reply(200, data)
                elif parsed.path == "/api/order":
                    self.reply(200, explain_order(self.store, query["customer"][0], query["order"][0], day))
                elif parsed.path == "/api/retention":
                    data = retention_summary(self.store, day)
                    data["rows"] = filter_retention(data, **{key: query.get(key, [""])[0]
                        for key in ("category", "state", "strategy", "profile", "search")})
                    data["demo"] = demo
                    self.reply(200, data)
                elif parsed.path == "/api/rules":
                    self.reply(200, rules_summary())
                elif parsed.path == "/api/plan":
                    data = plan_detail(self.store, query["customer"][0], json.loads(query["plan"][0]), day)
                    data["demo"] = demo
                    self.reply(200, data)
                else:
                    pages = {"/": "overview.html", "/retention": "retention.html", "/rules": "rules.html"}
                    path = FRONTEND / pages.get(parsed.path, parsed.path.lstrip("/"))
                    path = path.resolve()
                    if not path.is_relative_to(FRONTEND.resolve()) or not path.is_file():
                        self.reply(404, {"error": "Pagina non trovata."})
                        return
                    content_type = {
                        ".html": "text/html; charset=utf-8",
                        ".css": "text/css; charset=utf-8",
                        ".js": "text/javascript; charset=utf-8",
                    }.get(path.suffix.lower(), mimetypes.guess_type(path.name)[0] or "application/octet-stream")
                    self.reply(200, path.read_bytes(), content_type)
            except (ValueError, KeyError, TypeError, IndexError):
                self.reply(400, {"error": "Richiesta non valida."})

        def do_POST(self):
            if not self.authorized():
                return
            origin = self.headers.get("Origin")
            if origin and origin != (public_origin or "http://" + self.headers.get("Host", "")):
                self.reply(400, {"error": "Origine della richiesta non valida."})
                return
            if self.path == "/api/events":
                try:
                    if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                        raise ValueError("La registrazione richiede dati JSON.")
                    length = int(self.headers.get("Content-Length", 0))
                    if not 0 < length <= 65536:
                        raise ValueError("Dimensione evento non valida.")
                    payload = json.loads(self.rfile.read(length))
                    event = payload["event"]
                    day = as_of or datetime.now(ZoneInfo("Europe/Rome")).date().isoformat()
                    if event["date"] > day:
                        raise ValueError("Non si possono registrare eventi futuri.")
                    with write_lock:
                        record_event(self.store, payload["customer_id"], event)
                    self.reply(200, {"saved": True, "event_id": event["id"]})
                except (ValueError, KeyError, TypeError, UnicodeError) as error:
                    self.reply(400, {"error": str(error) or "Evento non valido."})
                return
            if self.path != "/api/import":
                self.reply(404, {"error": "Pagina non trovata."})
                return
            if demo:
                self.reply(409, {"error": "Il caricamento CSV è disponibile in modalità dati locali."})
                return
            try:
                length = int(self.headers.get("Content-Length", 0))
                if not 0 < length <= 50 * 1024 * 1024:
                    raise ValueError("Dimensione non valida (massimo 50 MB).")
                message = BytesParser(policy=default).parsebytes(
                    ("Content-Type: " + self.headers.get("Content-Type", "") + "\r\n\r\n").encode()
                    + self.rfile.read(length))
                paths = []
                upload_directory = (tempfile.TemporaryDirectory(prefix="rre-upload-") if self.store.postgres
                                    else nullcontext(str(self.store.path.parent / "uploads")))
                with upload_directory as folder:
                    directory = Path(folder)
                    directory.mkdir(parents=True, exist_ok=True)
                    for part in message.iter_parts():
                        name = part.get_filename()
                        if not name:
                            continue
                        if Path(name).suffix.lower() != ".csv":
                            raise ValueError("Sono ammessi solo CSV.")
                        # Nome locale univoco: non sovrascrive export esistenti.
                        with tempfile.NamedTemporaryFile(prefix="upload-", suffix=".csv", dir=directory, delete=False) as file:
                            file.write(part.get_payload(decode=True))
                            path = Path(file.name)
                        sanitize_export(path)
                        paths.append(path)
                    if not paths:
                        raise ValueError("Selezionare almeno un export CSV.")
                    with write_lock:
                        import_into_store(self.store, paths)
                    self.reply(200, {"imported_files": len(paths), "active": bool(self.store.activation_date())})
            except (ValueError, UnicodeError) as error:
                self.reply(400, {"error": str(error)})

        def log_message(self, format, *args):
            pass

    return Handler


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--database", default=os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_PATH"),
                      help="PostgreSQL via DATABASE_URL oppure SQLite via DATABASE_PATH.")
    mode.add_argument("--demo", action="store_true", help="Usa soltanto dati sintetici, separati dal database reale.")
    parser.add_argument("--host", default="0.0.0.0" if os.environ.get("RENDER") else "127.0.0.1")
    parser.add_argument("--port", type=int, default=os.environ.get("PORT", "8000"))
    parser.add_argument("--as-of", help="Data di valutazione; in demo il riferimento Figma è 2026-10-05.")
    args = parser.parse_args(argv)
    if os.environ.get("DATABASE_URL") and os.environ.get("DATABASE_PATH"):
        parser.error("Configurare DATABASE_URL oppure DATABASE_PATH, non entrambi.")
    username, password = os.environ.get("RRE_USERNAME"), os.environ.get("RRE_PASSWORD")
    if bool(username) != bool(password) or (username and ":" in username):
        parser.error("Impostare RRE_USERNAME (senza due punti) e RRE_PASSWORD insieme.")
    if (os.environ.get("RENDER") or args.host not in ("127.0.0.1", "localhost", "::1")) and not username:
        parser.error("L'accesso remoto richiede RRE_USERNAME e RRE_PASSWORD.")
    if os.environ.get("RENDER") and not args.demo and not args.database:
        parser.error("Su Render impostare DATABASE_URL (PostgreSQL) oppure DATABASE_PATH sul disco persistente.")
    public_origin = os.environ.get("RENDER_EXTERNAL_URL", "").rstrip("/") or None
    with tempfile.TemporaryDirectory(prefix="rre-demo-") as directory:
        database = args.database or ROOT / "local-data" / "retention.sqlite3"
        store = demo_store(Path(directory) / "demo.sqlite3") if args.demo else Store(database)
        server = ThreadingHTTPServer((args.host, args.port), make_handler(
            store, demo=args.demo, as_of=args.as_of or ("2026-10-05" if args.demo else None),
            credentials=(username, password) if username else None, public_origin=public_origin))
        print(f"Dashboard in ascolto su {args.host}:{args.port} ({'demo' if args.demo else 'dati importati'})", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
            store.close()


if __name__ == "__main__":
    main()
