"""Raggruppamento sintetico degli ordini importati."""

import csv
from pathlib import Path
import tempfile
import unittest

from src.customer_profiles import (_profile_counts, customer_signals, engine_snapshot, merge_csv_exports,
                                   merge_orders, review_cases)
from src.engine import evaluate_portfolio


def batch(order_id, email=None, validity="valid", marketing="yes", sku="CR05272",
          day="2026-08-01"):
    order = {"id": order_id, "number": f"#{order_id}", "date": day,
             "marketing_signal": marketing,
             "lines": [{"id": f"{order_id}:{sku}", "order_id": order_id,
                        "sku": sku, "date": day, "validity": validity}]}
    return {"orders": [order],
            "order_contacts": {order_id: {"email": email}} if email else {}}


class CustomerProfilesTests(unittest.TestCase):
    def test_profile_counts_deduplicate_customers_and_keep_unknown_signals_unknown(self):
        state = merge_orders(None, batch("1", "one@example.invalid"))
        first = customer_signals(state, "CUST_000001", "2026-10-12")
        state = merge_orders(state, batch("2", "two@example.invalid"))
        state = merge_orders(state, batch("3", "two@example.invalid"))
        recurring = customer_signals(state, "CUST_000002", "2026-10-12")
        rows = [{"customer_id": "CUST_000001", "customer_profile": first},
                {"customer_id": "CUST_000002", "customer_profile": recurring},
                {"customer_id": "CUST_000002", "customer_profile": recurring}]
        counts = _profile_counts(rows)
        self.assertEqual(counts, _profile_counts(rows))
        self.assertEqual(counts["first_purchase"], 1)
        self.assertEqual(counts["recurring"], 1)
        self.assertEqual(counts["recent_activity"], 0)
        self.assertEqual(counts["multicategory"], 0)
        self.assertIsNone(counts["possible_b2b"])
        self.assertIsNone(counts["high_historical_value"])
        self.assertEqual(_profile_counts([])["recurring"], 0)
        self.assertIsNone(_profile_counts([])["possible_b2b"])

    def test_first_purchase_and_recurring_are_based_on_distinct_valid_orders(self):
        state = merge_orders(None, batch("1", "one@example.invalid"))
        first = customer_signals(state, "CUST_000001", "2026-10-12")
        self.assertEqual([item["key"] for item in first["signals"]], ["first_purchase"])
        state = merge_orders(state, batch("2", "one@example.invalid"))
        state = merge_orders(state, batch("2", "one@example.invalid"))
        recurring = customer_signals(state, "CUST_000001", "2026-10-12")
        self.assertEqual(recurring["valid_orders"], 2)
        self.assertEqual([item["key"] for item in recurring["signals"]], ["recurring"])
        self.assertEqual(recurring, customer_signals(state, "CUST_000001", "2026-10-12"))
        self.assertNotIn("email", str(recurring))

    def test_invalid_unknown_empty_and_future_orders_do_not_qualify(self):
        state = None
        for order_id, validity, day in [("1", "cancelled", "2026-08-01"),
                                        ("2", "unknown", "2026-08-01"),
                                        ("3", "valid", "2026-10-13")]:
            state = merge_orders(state, batch(order_id, "one@example.invalid", validity=validity, day=day))
        state["profiles"]["CUST_000001"]["orders"]["1"]["lines"] = []
        result = customer_signals(state, "CUST_000001", "2026-10-12")
        self.assertEqual(result["valid_orders"], 0)
        self.assertEqual(result["signals"], [])
        self.assertEqual(result["uncertain_orders"], 1)
        self.assertEqual(len(result["unavailable_signals"]), 2)

    def test_recent_activity_inclusive_90_day_window_and_coexisting_signals(self):
        state = None
        for order_id, day in [("1", "2026-07-15"), ("2", "2026-08-01"), ("3", "2026-10-12")]:
            state = merge_orders(state, batch(order_id, "one@example.invalid", day=day))
        result = customer_signals(state, "CUST_000001", "2026-10-12")
        self.assertEqual(result["recent_starts_on"], "2026-07-15")
        self.assertEqual([item["key"] for item in result["signals"]], ["recurring", "recent_activity"])
        state["profiles"]["CUST_000001"]["orders"]["1"]["date"] = "2026-07-14"
        result = customer_signals(state, "CUST_000001", "2026-10-12")
        self.assertEqual(result["recent_valid_orders"], 2)
        self.assertNotIn("recent_activity", [item["key"] for item in result["signals"]])

    def test_multicategory_groups_phon_and_styling_and_ignores_accessories(self):
        import json
        catalog = json.loads((Path(__file__).resolve().parents[1] / "src/catalog.json").read_text(encoding="utf-8"))
        sku = {product["key"]: product["variants"][0]["sku"] for product in catalog["products"]}
        state = merge_orders(None, batch("1", "one@example.invalid"))
        lines = state["profiles"]["CUST_000001"]["orders"]["1"]["lines"]
        for key in ("laifen_autocurl", "laifen_p3_travel_case"):
            lines.append({**lines[0], "sku": sku[key], "id": f"1:{sku[key]}"})
        result = customer_signals(state, "CUST_000001", "2026-10-12", catalog=catalog)
        self.assertEqual(result["main_categories"], ["Cura dei capelli"])
        self.assertNotIn("multicategory", [item["key"] for item in result["signals"]])
        lines.append({**lines[0], "sku": sku["laifen_wave_pro"], "id": "wave"})
        result = customer_signals(state, "CUST_000001", "2026-10-12", catalog=catalog)
        self.assertEqual([item["key"] for item in result["signals"]], ["first_purchase", "multicategory"])
        lines[-1]["validity"] = "unknown"
        result = customer_signals(state, "CUST_000001", "2026-10-12", catalog=catalog)
        self.assertEqual(result["signals"], [])
        self.assertEqual(result["main_categories"], ["Cura dei capelli"])

    def test_multiple_csv_exports_build_one_history_without_duplicate_orders(self):
        columns = ["Name", "Id", "Created at", "Financial Status", "Lineitem sku",
                   "Lineitem quantity", "Lineitem fulfillment status", "Cancelled at",
                   "Refunded Amount", "Email", "Accepts Marketing"]
        with tempfile.TemporaryDirectory() as directory:
            paths = []
            for order_id in ("1", "2"):
                path = Path(directory) / f"orders_{order_id}.csv"
                with path.open("w", encoding="utf-8-sig", newline="") as target:
                    writer = csv.DictWriter(target, fieldnames=columns)
                    writer.writeheader()
                    writer.writerow({"Name": f"#{order_id}", "Id": order_id,
                                     "Created at": "2026-08-01 00:00:00 +0000",
                                     "Financial Status": "paid", "Lineitem sku": "CR05272",
                                     "Lineitem quantity": "1", "Lineitem fulfillment status": "fulfilled",
                                     "Cancelled at": "", "Refunded Amount": "0.00",
                                     "Email": "one@example.invalid", "Accepts Marketing": "yes"})
                paths.append(path)
            state = merge_csv_exports([*paths, paths[0]])
        self.assertEqual(len(state["profiles"]), 1)
        self.assertEqual(set(state["profiles"]["CUST_000001"]["orders"]), {"1", "2"})

    def test_same_email_groups_orders_and_repeat_import_does_not_duplicate(self):
        first = merge_orders(None, batch("1", "one@example.invalid"))
        second = merge_orders(first, batch("2", "one@example.invalid"))
        repeated = merge_orders(second, batch("1", "one@example.invalid", "unknown"))
        self.assertEqual(len(repeated["profiles"]), 1)
        self.assertEqual(set(repeated["profiles"]["CUST_000001"]["orders"]), {"1", "2"})
        self.assertEqual(repeated["profiles"]["CUST_000001"]["orders"]["1"]["lines"][0]["validity"], "unknown")
        self.assertEqual(repeated["contacts"]["CUST_000001"], {"email": "one@example.invalid"})
        self.assertNotIn("email", str(repeated["profiles"]))
        self.assertEqual(len(first["profiles"]["CUST_000001"]["orders"]), 1)

    def test_missing_email_stays_unassigned_until_later_import(self):
        first = merge_orders(None, batch("1"))
        self.assertEqual(first["profiles"], {})
        self.assertIn("1", first["unassigned_orders"])
        second = merge_orders(first, batch("1", "one@example.invalid"))
        self.assertEqual(second["unassigned_orders"], {})
        self.assertIn("1", second["profiles"]["CUST_000001"]["orders"])

    def test_conflicting_email_for_same_order_is_rejected(self):
        first = merge_orders(None, batch("1", "one@example.invalid"))
        with self.assertRaisesRegex(ValueError, "email diverse"):
            merge_orders(first, batch("1", "two@example.invalid"))

    def test_confirmed_purchase_and_yes_consent_reach_existing_rules(self):
        state = merge_orders(None, batch("1", "one@example.invalid"))
        snapshot = engine_snapshot(state, "CUST_000001", "2026-09-29")
        self.assertNotIn("email", str(snapshot["purchases"]))
        self.assertEqual(snapshot["marketing_consent"]["email"]["status"], "subscribed")
        self.assertFalse(snapshot["history_complete"])
        self.assertFalse(snapshot["contact_history_complete"])
        result = evaluate_portfolio(snapshot, "2026-09-29")
        self.assertTrue(result["contact_permission"]["allowed"])
        self.assertIsNotNone(result["primary_contact_plan"])
        self.assertEqual(result["primary_contact_plan"]["primary_opportunity"]["source_order_id"], "1")
        self.assertEqual(review_cases(state, "2026-09-29"), [])

    def test_no_or_conflicting_consent_blocks_and_uncertain_orders_are_separate(self):
        state = merge_orders(None, batch("1", "one@example.invalid", marketing="no"))
        snapshot = engine_snapshot(state, "CUST_000001", "2026-09-29")
        self.assertEqual(snapshot["marketing_consent"]["email"]["status"], "unsubscribed")
        self.assertFalse(evaluate_portfolio(snapshot, "2026-09-29")["contact_permission"]["allowed"])
        state = merge_orders(state, batch("2", "one@example.invalid", validity="unknown"))
        snapshot = engine_snapshot(state, "CUST_000001", "2026-09-29")
        self.assertEqual(snapshot["marketing_consent"]["email"]["status"], "unknown")
        self.assertFalse(evaluate_portfolio(snapshot, "2026-09-29")["contact_permission"]["allowed"])
        state = merge_orders(state, batch("3"))
        self.assertEqual({case["reason"] for case in review_cases(state, "2026-09-29")},
                         {"uncertain_email_consent", "uncertain_purchase", "missing_email"})

    def test_future_order_does_not_change_earlier_consent_or_purchases(self):
        state = merge_orders(None, batch("1", "one@example.invalid", marketing="yes"))
        state = merge_orders(state, batch("2", "one@example.invalid", marketing="no",
                                          day="2026-10-01"))
        before = engine_snapshot(state, "CUST_000001", "2026-09-29")
        after = engine_snapshot(state, "CUST_000001", "2026-10-02")
        self.assertEqual(before["marketing_consent"]["email"]["status"], "subscribed")
        self.assertEqual(len(before["purchases"]), 1)
        self.assertEqual(after["marketing_consent"]["email"]["status"], "unknown")
        self.assertEqual(len(after["purchases"]), 2)


if __name__ == "__main__":
    unittest.main()
