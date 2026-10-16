"""Normalizza i fatti d'ordine dell'export CSV Shopify, senza dati di contatto."""

import argparse
import csv
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time
from zoneinfo import ZoneInfo


MINIMAL_COLUMNS = [
    "Name", "Id", "Created at", "Financial Status", "Lineitem sku",
    "Lineitem quantity", "Lineitem fulfillment status", "Cancelled at",
    "Refunded Amount", "Email", "Accepts Marketing",
]


def sanitize_export(path):
    """Sostituisce un CSV Shopify con le sole colonne usate dal motore."""
    path = Path(path).resolve()
    if not path.is_file() or path.suffix.lower() != ".csv":
        raise ValueError("Serve un export CSV esistente.")
    initial_stat = path.stat()
    temporary_path = None
    try:
        with path.open(encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            missing = set(MINIMAL_COLUMNS) - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"Colonne Shopify mancanti: {', '.join(sorted(missing))}.")
            if reader.fieldnames == MINIMAL_COLUMNS:
                if any(None in row for row in reader):
                    raise ValueError("Riga CSV con più campi dell'intestazione.")
                return None
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=".sanitizing-", suffix=".tmp", dir=path.parent,
            )
            temporary_path = Path(temporary_name)
            with os.fdopen(descriptor, "w", encoding="utf-8-sig", newline="") as target:
                writer = csv.DictWriter(target, fieldnames=MINIMAL_COLUMNS)
                writer.writeheader()
                row_count = 0
                for row in reader:
                    if None in row:
                        raise ValueError("Riga CSV con più campi dell'intestazione.")
                    writer.writerow({column: row[column] for column in MINIMAL_COLUMNS})
                    row_count += 1
                target.flush()
                os.fsync(target.fileno())
        current_stat = path.stat()
        if (initial_stat.st_size, initial_stat.st_mtime_ns) != (
            current_stat.st_size, current_stat.st_mtime_ns
        ):
            raise ValueError("L'export è cambiato durante la pulizia; riprovare.")
        with temporary_path.open(encoding="utf-8-sig", newline="") as check:
            checked = csv.DictReader(check)
            if checked.fieldnames != MINIMAL_COLUMNS or sum(1 for _ in checked) != row_count:
                raise ValueError("La copia ridotta non ha superato la verifica.")
        os.replace(temporary_path, path)
        temporary_path = None
        return row_count
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def sanitize_local_data(directory, *, watch=False, on_ready=None):
    """Pulisce in loco i CSV completati; sorveglia la cartella se richiesto."""
    directory = Path(directory).resolve()
    if not directory.is_dir():
        raise ValueError("La cartella local-data non esiste.")

    def report(message):
        with (directory / "sanitizer.log").open("a", encoding="utf-8") as log:
            log.write(f"{datetime.now().astimezone().isoformat(timespec='seconds')} {message}\n")
        if sys.stdout is not None:
            print(message, flush=True)

    if watch:
        report("Sorveglianza CSV avviata.")
    observed = {}
    processed = {}
    errors = 0
    while True:
        for path in sorted(directory.glob("*.csv"), key=lambda item: [
            int(part) if part.isdigit() else part.casefold()
            for part in re.split(r"(\d+)", item.name)
        ]):
            try:
                stat = path.stat()
            except FileNotFoundError:
                continue
            signature = (stat.st_size, stat.st_mtime_ns)
            if watch and observed.get(path) != signature:
                observed[path] = signature
                continue
            if watch and (time.time() - stat.st_mtime < 4 or processed.get(path) == signature):
                continue
            try:
                rows = sanitize_export(path)
                stat = path.stat()
                processed[path] = (stat.st_size, stat.st_mtime_ns)
                observed[path] = processed[path]
                if rows is not None:
                    report(f"CSV ridotto: {path.name}; righe: {rows}.")
                if on_ready is not None:
                    message = on_ready(path)
                    if message:
                        report(f"{message}: {path.name}.")
            except (OSError, ValueError) as error:
                report(f"CSV da verificare: {path.name}; {error}")
                processed[path] = signature
                errors += 1
        if not watch:
            return errors
        time.sleep(2)


def import_orders(path, catalog_path=None):
    """Restituisce fatti d'ordine e recapiti associati, in strutture separate."""
    catalog_path = catalog_path or Path(__file__).resolve().parent / "catalog.json"
    catalog = json.loads(Path(catalog_path).read_text(encoding="utf-8"))
    ean_by_sku = {
        variant["sku"]: variant["ean"]
        for product in catalog["products"] for variant in product["variants"]
    }
    skus_by_ean = defaultdict(set)
    for sku, ean in ean_by_sku.items():
        if ean:
            skus_by_ean[ean].add(sku)
    sku_by_ean = {ean: next(iter(skus)) for ean, skus in skus_by_ean.items() if len(skus) == 1}
    with Path(path).open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source)
        missing = set(MINIMAL_COLUMNS) - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Colonne Shopify mancanti: {', '.join(sorted(missing))}.")
        if reader.fieldnames != MINIMAL_COLUMNS:
            raise ValueError("CSV non ridotto: usare il filtro locale prima dell'import.")
        groups = defaultdict(list)
        for row_number, row in enumerate(reader, start=2):
            name = (row["Name"] or "").strip()
            if not name:
                raise ValueError(f"Riga {row_number}: numero ordine mancante.")
            groups[name].append((row_number, row))

    orders = []
    order_contacts = {}
    seen_ids = set()
    for order_number, rows in groups.items():
        order_ids = {(row["Id"] or "").strip() for _, row in rows if (row["Id"] or "").strip()}
        if len(order_ids) != 1:
            raise ValueError("ID ordine assente o discordante nelle righe dello stesso ordine.")
        order_id = order_ids.pop()
        if order_id in seen_ids:
            raise ValueError("Lo stesso ID ordine compare con numeri ordine diversi.")
        seen_ids.add(order_id)
        emails = {(row.get("Email") or "").strip().casefold()
                  for _, row in rows if (row.get("Email") or "").strip()}
        if len(emails) > 1:
            raise ValueError("Email discordanti nelle righe dello stesso ordine.")
        if emails:
            order_contacts[order_id] = {"email": next(iter(emails))}
        financial_values = {(row["Financial Status"] or "").strip().lower()
                            for _, row in rows if (row["Financial Status"] or "").strip()}
        financial = "paid" if financial_values == {"paid"} else "unknown"
        marketing_values = {(row.get("Accepts Marketing") or "").strip().lower()
                            for _, row in rows if (row.get("Accepts Marketing") or "").strip()}
        marketing_signal = (next(iter(marketing_values))
                            if len(marketing_values) == 1 and marketing_values <= {"yes", "no"}
                            else "unknown")
        cancelled = any((row["Cancelled at"] or "").strip() for _, row in rows)
        try:
            refunds = [Decimal((row["Refunded Amount"] or "").strip())
                       for _, row in rows if (row["Refunded Amount"] or "").strip()]
        except InvalidOperation:
            refunds = []
        no_refund = bool(refunds) and all(amount == 0 for amount in refunds)
        lines = []
        lines_by_sku = {}
        dates = set()
        for row_number, row in rows:
            raw_date = (row["Created at"] or "").strip()
            try:
                timestamp = datetime.strptime(raw_date, "%Y-%m-%d %H:%M:%S %z")
            except ValueError as error:
                raise ValueError(f"Riga {row_number}: data ordine non valida.") from error
            dates.add(timestamp.astimezone(ZoneInfo("Europe/Rome")).date().isoformat())
            sku = (row["Lineitem sku"] or "").strip()
            if not sku:
                raise ValueError(f"Riga {row_number}: SKU mancante; riga non identificabile.")
            # Uno SKU esatto prevale; un EAN univoco identifica la stessa variante.
            if sku not in ean_by_sku:
                sku = sku_by_ean.get(sku, sku)
            try:
                quantity = int((row["Lineitem quantity"] or "").strip())
            except ValueError as error:
                raise ValueError(f"Riga {row_number}: quantità non valida.") from error
            if quantity <= 0:
                raise ValueError(f"Riga {row_number}: quantità non positiva.")
            line_status = (row["Lineitem fulfillment status"] or "").strip().lower()
            validity = ("cancelled" if cancelled else "valid"
                        if financial == "paid" and line_status == "fulfilled" and no_refund
                        else "unknown")
            if sku in lines_by_sku:
                previous = lines_by_sku[sku]
                previous["quantity"] += quantity
                previous["validity"] = "unknown" if not cancelled else "cancelled"
                continue
            line = {
                "id": f"{order_id}:{sku}", "order_id": order_id, "sku": sku,
                "ean": ean_by_sku.get(sku), "quantity": quantity, "validity": validity,
            }
            lines_by_sku[sku] = line
            lines.append(line)
        if len(dates) != 1:
            raise ValueError("Date discordanti nelle righe dello stesso ordine.")
        purchased_on = dates.pop()
        for line in lines:
            line["date"] = purchased_on
        orders.append({"id": order_id, "number": order_number, "date": purchased_on,
                       "marketing_signal": marketing_signal, "lines": lines})
    return {"orders": orders, "order_contacts": order_contacts}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verifica un export ordini Shopify senza mostrare dati cliente.")
    parser.add_argument("csv_path", nargs="?", type=Path)
    parser.add_argument("--sanitize-local-data", action="store_true")
    parser.add_argument("--watch", action="store_true")
    arguments = parser.parse_args()
    if arguments.sanitize_local_data:
        if arguments.csv_path:
            parser.error("Indicare solo la pulizia o il CSV da verificare.")
        directory = Path(__file__).resolve().parent.parent / "local-data"
        try:
            errors = sanitize_local_data(directory, watch=arguments.watch)
        except KeyboardInterrupt:
            print("Sorveglianza terminata.")
            errors = 0
        raise SystemExit(bool(errors))
    if not arguments.csv_path or arguments.watch:
        parser.error("Indicare un CSV da verificare oppure --sanitize-local-data.")
    imported = import_orders(arguments.csv_path)
    orders = imported["orders"]
    statuses = Counter(line["validity"] for order in orders for line in order["lines"])
    print(json.dumps({"orders": len(orders), "linked_to_email": len(imported["order_contacts"]),
                      "distinct_emails": len({link["email"] for link in imported["order_contacts"].values()}),
                      "lines": sum(len(o["lines"]) for o in orders),
                      "validity": dict(statuses)}, ensure_ascii=False))
