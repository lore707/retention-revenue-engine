"""Verifiche con righe sintetiche nel formato dell'export ordini osservato."""

import csv
import io
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from src.shopify_orders import (MINIMAL_COLUMNS, import_orders, sanitize_export,
                                sanitize_local_data)


COLUMNS = [
    "Name", "Id", "Created at", "Financial Status", "Lineitem sku",
    "Lineitem quantity", "Lineitem fulfillment status", "Cancelled at",
    "Refunded Amount", "Email", "Accepts Marketing",
]


def row(**changes):
    result = {
        "Name": "#1001", "Id": "5001", "Created at": "2026-08-31 23:30:00 +0000",
        "Financial Status": "paid", "Lineitem sku": "CR05272",
        "Lineitem quantity": "1", "Lineitem fulfillment status": "fulfilled",
        "Cancelled at": "", "Refunded Amount": "0.00",
        "Email": "synthetic@example.invalid", "Accepts Marketing": "yes",
    }
    return {**result, **changes}


class ShopifyOrdersTests(unittest.TestCase):
    def load(self, rows):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "orders.csv"
            with path.open("w", encoding="utf-8-sig", newline="") as target:
                writer = csv.DictWriter(target, fieldnames=COLUMNS)
                writer.writeheader()
                writer.writerows(rows)
            return import_orders(path)

    def test_multiline_order_uses_one_order_id_and_rome_purchase_date(self):
        imported = self.load([
            row(),
            row(Id="", **{"Financial Status": "", "Refunded Amount": "",
                          "Lineitem sku": "30101-000092", "Accepts Marketing": ""}),
        ])
        orders = imported["orders"]
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0]["number"], "#1001")
        self.assertEqual(orders[0]["date"], "2026-09-01")
        self.assertEqual([line["id"] for line in orders[0]["lines"]],
                         ["5001:CR05272", "5001:30101-000092"])
        self.assertTrue(all(line["validity"] == "valid" for line in orders[0]["lines"]))
        self.assertTrue(orders[0]["lines"][0]["ean"])
        self.assertEqual(orders[0]["marketing_signal"], "yes")
        self.assertNotIn("marketing_consent", orders[0])
        self.assertNotIn("synthetic@example.invalid", str(orders))
        self.assertEqual(imported["order_contacts"],
                         {"5001": {"email": "synthetic@example.invalid"}})

    def test_marketing_signal_keeps_no_and_ambiguous_values_distinct(self):
        orders = self.load([
            row(Name="#1001", Id="5001", **{"Accepts Marketing": "no"}),
            row(Name="#1002", Id="5002", **{"Accepts Marketing": ""}),
            row(Name="#1003", Id="5003", **{"Accepts Marketing": "yes"}),
            row(Name="#1003", Id="", **{"Lineitem sku": "30101-000092",
                                         "Accepts Marketing": "no"}),
        ])["orders"]
        self.assertEqual([order["marketing_signal"] for order in orders],
                         ["no", "unknown", "unknown"])

    def test_pending_refund_and_cancelled_are_not_treated_as_valid_purchases(self):
        orders = self.load([
            row(Name="#1001", Id="5001", **{"Lineitem fulfillment status": "pending"}),
            row(Name="#1002", Id="5002", **{"Refunded Amount": "10.00"}),
            row(Name="#1003", Id="5003", **{"Cancelled at": "2026-09-01 00:00:00 +0000"}),
            row(Name="#1004", Id="5004", **{"Financial Status": "partially_paid"}),
        ])["orders"]
        self.assertEqual([order["lines"][0]["validity"] for order in orders],
                         ["unknown", "unknown", "cancelled", "unknown"])

    def test_refund_recorded_on_continuation_row_requires_review_for_whole_order(self):
        orders = self.load([
            row(),
            row(Id="", **{"Lineitem sku": "30101-000092", "Refunded Amount": "5.00"}),
        ])["orders"]
        self.assertEqual([line["validity"] for line in orders[0]["lines"]],
                         ["unknown", "unknown"])

    def test_unknown_sku_is_not_guessed_and_duplicate_sku_requires_review(self):
        orders = self.load([row(**{"Lineitem sku": "UNKNOWN-SKU"})])["orders"]
        self.assertIsNone(orders[0]["lines"][0]["ean"])
        duplicate = self.load([row(), row(Id="", **{"Lineitem sku": "CR05272"})])["orders"][0]
        self.assertEqual(len(duplicate["lines"]), 1)
        self.assertEqual(duplicate["lines"][0]["id"], "5001:CR05272")
        self.assertEqual(duplicate["lines"][0]["quantity"], 2)
        self.assertEqual(duplicate["lines"][0]["validity"], "unknown")

    def test_ean_in_sku_column_resolves_exact_catalog_variant(self):
        for ean, sku in [("6942590700097", "CR68943"), ("6942590700103", "CR68942")]:
            with self.subTest(ean=ean):
                order = self.load([row(**{"Lineitem sku": ean})])["orders"][0]
                self.assertEqual(order["lines"][0]["sku"], sku)
                self.assertEqual(order["lines"][0]["ean"], ean)
                self.assertEqual(order["lines"][0]["id"], f"5001:{sku}")
        # Questo codice numerico è uno SKU canonico e deve restare tale.
        line = self.load([row(**{"Lineitem sku": "6976973852011"})])["orders"][0]["lines"][0]
        self.assertEqual(line["sku"], "6976973852011")
        unknown = self.load([row(**{"Lineitem sku": "9999999999999"})])["orders"][0]["lines"][0]
        self.assertEqual(unknown["sku"], "9999999999999")
        self.assertIsNone(unknown["ean"])

    def test_ean_and_sku_duplicate_still_requires_review(self):
        order = self.load([row(**{"Lineitem sku": "6942590700097"}),
                           row(Id="", **{"Lineitem sku": "CR68943"})])["orders"][0]
        self.assertEqual(len(order["lines"]), 1)
        self.assertEqual(order["lines"][0]["quantity"], 2)
        self.assertEqual(order["lines"][0]["validity"], "unknown")

    def test_confirmed_wave_accessory_codes_are_known_without_invented_eans(self):
        for sku in ("CP38422", "CP38423", "CP38472", "CP38474", "CM61972"):
            with self.subTest(sku=sku):
                line = self.load([row(**{"Lineitem sku": sku})])["orders"][0]["lines"][0]
                self.assertEqual(line["sku"], sku)
                self.assertIsNone(line["ean"])
                self.assertEqual(line["validity"], "valid")

    def test_missing_or_conflicting_email_never_creates_a_contact_link(self):
        imported = self.load([row(**{"Email": ""})])
        self.assertEqual(imported["order_contacts"], {})
        self.assertEqual(len(imported["orders"]), 1)
        with self.assertRaisesRegex(ValueError, "Email discordanti"):
            self.load([row(), row(Id="", **{"Email": "other@example.invalid",
                                         "Lineitem sku": "30101-000092"})])

    def test_sanitizer_removes_unneeded_personal_columns_without_changing_import(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "orders.csv"
            with source.open("w", encoding="utf-8-sig", newline="") as target:
                writer = csv.DictWriter(target, fieldnames=COLUMNS + ["Billing Name", "Phone"])
                writer.writeheader()
                writer.writerow({**row(), "Billing Name": "Synthetic Person",
                                 "Phone": "+390000000000"})
            expected = self.load([row()])
            self.assertEqual(sanitize_export(source), 1)
            self.assertTrue(source.exists())
            with source.open(encoding="utf-8-sig", newline="") as clean:
                reader = csv.DictReader(clean)
                self.assertEqual(reader.fieldnames, MINIMAL_COLUMNS)
                self.assertEqual(len(list(reader)), 1)
            self.assertEqual(import_orders(source), expected)
            self.assertIsNone(sanitize_export(source))

    def test_import_rejects_full_export_before_reading_order_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "orders.csv"
            with source.open("w", encoding="utf-8-sig", newline="") as target:
                writer = csv.DictWriter(target, fieldnames=COLUMNS + ["Billing Name"])
                writer.writeheader()
                writer.writerow({**row(), "Billing Name": "Synthetic Person"})
            with self.assertRaisesRegex(ValueError, "CSV non ridotto"):
                import_orders(source)
            self.assertTrue(source.exists())

    def test_sanitizer_preserves_source_on_invalid_schema_or_malformed_row(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "orders.csv"
            with source.open("w", encoding="utf-8-sig", newline="") as target:
                writer = csv.DictWriter(target, fieldnames=["Name", "Billing Name"])
                writer.writeheader()
                writer.writerow({"Name": "#1001", "Billing Name": "Synthetic Person"})
            with self.assertRaisesRegex(ValueError, "Colonne Shopify mancanti"):
                sanitize_export(source)
            self.assertTrue(source.exists())
            with source.open("w", encoding="utf-8-sig", newline="") as target:
                writer = csv.writer(target)
                writer.writerow(COLUMNS)
                writer.writerow(list(row().values()) + ["extra"])
            original = source.read_bytes()
            with self.assertRaisesRegex(ValueError, "più campi"):
                sanitize_export(source)
            self.assertEqual(source.read_bytes(), original)

    def test_sanitizer_keeps_unchanged_reduced_csv(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "orders.csv"
            with source.open("w", encoding="utf-8-sig", newline="") as target:
                writer = csv.DictWriter(target, fieldnames=COLUMNS)
                writer.writeheader()
                writer.writerow(row())
            original = source.read_bytes()
            self.assertIsNone(sanitize_export(source))
            self.assertEqual(source.read_bytes(), original)

    def test_watch_mode_waits_for_stable_csv_then_sanitizes_it(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "orders.csv"
            with source.open("w", encoding="utf-8-sig", newline="") as target:
                writer = csv.DictWriter(target, fieldnames=COLUMNS + ["Shipping Name"])
                writer.writeheader()
                writer.writerow({**row(), "Shipping Name": "Synthetic Person"})
            with patch("src.shopify_orders.time.time", return_value=source.stat().st_mtime + 10), \
                 patch("src.shopify_orders.time.sleep", side_effect=[None, KeyboardInterrupt]), \
                 redirect_stdout(io.StringIO()):
                with self.assertRaises(KeyboardInterrupt):
                    sanitize_local_data(directory, watch=True)
            self.assertTrue(source.exists())
            self.assertEqual(import_orders(source)["orders"][0]["id"], "5001")
            log = (Path(directory) / "sanitizer.log").read_text(encoding="utf-8")
            self.assertIn("Sorveglianza CSV avviata.", log)
            self.assertIn("CSV ridotto: orders.csv; righe: 1.", log)
            self.assertNotIn("Synthetic Person", log)


if __name__ == "__main__":
    unittest.main()
