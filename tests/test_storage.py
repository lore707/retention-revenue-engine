"""Persistenza e ciclo operativo con dati sintetici."""

import csv
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.customer_profiles import (activate_history, evaluate_day, explain_order, import_into_store,
                                   merge_orders, record_event, revenue_summary, sync_local_data)
from src.storage import Store, migrate_sqlite


def imported(order_id="1", *, email="one@example.invalid", marketing="yes",
             validity="valid", sku="CR05272"):
    order = {"id": order_id, "number": f"#{order_id}", "date": "2026-08-01",
             "marketing_signal": marketing,
             "lines": [{"id": f"{order_id}:{sku}", "order_id": order_id, "sku": sku,
                        "date": "2026-08-01", "validity": validity, "quantity": 1}]}
    return {"orders": [order],
            "order_contacts": {order_id: {"email": email}} if email else {}}


class StorageTests(unittest.TestCase):
    def test_shopify_verified_sale_is_attributed_once_and_correction_is_auditable(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / "retention.sqlite3")
            store.save_state(merge_orders(None, imported()))
            activate_history(store, "2026-09-29")
            plan = evaluate_day(store, "2026-09-29")["ready"][0]["plan"]
            contact = {"id": "CONTACT", "type": "contact", "date": "2026-09-29",
                       "channel": "email", "rule_id": plan["primary_opportunity"]["rule_id"],
                       "plan_key": plan["plan_key"],
                       "primary_opportunity_key": plan["primary_opportunity"]["opportunity_key"],
                       "included_opportunity_keys": plan["included_opportunity_keys"]}
            sale = {"id": "SALE", "type": "verified_purchase", "date": "2026-10-01",
                    "plan_key": plan["plan_key"], "contact_event_id": "CONTACT",
                    "shopify_order_id": "SHOPIFY_2", "purchase_date": "2026-09-30",
                    "purchased_sku": "CL51809", "amount_minor": 2499, "currency": "EUR",
                    "verified_in_shopify": True}
            with self.assertRaisesRegex(ValueError, "contatto precedente"):
                record_event(store, "CUST_000001", sale)
            record_event(store, "CUST_000001", contact)
            with self.assertRaisesRegex(ValueError, "non appartiene"):
                record_event(store, "CUST_000001", {**sale, "purchased_sku": "CR05272"})
            with self.assertRaisesRegex(ValueError, "verifica in Shopify"):
                record_event(store, "CUST_000001", {**sale, "verified_in_shopify": False})
            record_event(store, "CUST_000001", sale)
            record_event(store, "CUST_000001", sale)
            self.assertEqual(revenue_summary(store, "2026-09-30")["attributed_revenue_minor"], 0)
            self.assertEqual(revenue_summary(store, "2026-10-01"),
                             {"as_of": "2026-10-01", "currency": "EUR",
                              "verified_orders": 1, "attributed_revenue_minor": 2499})
            self.assertTrue(all(item["plan"]["plan_key"] != plan["plan_key"]
                                for item in evaluate_day(store, "2026-10-14")["ready"]))
            with self.assertRaisesRegex(ValueError, "già attribuito"):
                record_event(store, "CUST_000001", {**sale, "id": "DUPLICATE"})
            correction = {"id": "CORRECTION", "type": "revenue_correction",
                          "date": "2026-10-02", "plan_key": plan["plan_key"],
                          "verified_purchase_event_id": "SALE", "amount_minor": 0,
                          "currency": "EUR", "reason": "Rimborso verificato in Shopify",
                          "verified_in_shopify": True}
            record_event(store, "CUST_000001", correction)
            self.assertEqual(revenue_summary(store, "2026-10-01")["attributed_revenue_minor"], 2499)
            self.assertEqual(revenue_summary(store, "2026-10-02")["attributed_revenue_minor"], 0)
            self.assertEqual(len(store.events_for("CUST_000001")), 3)
            store.close()

    def test_order_explanation_shows_current_alternatives_and_future_from_engine(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / "retention.sqlite3")
            store.save_state(merge_orders(None, imported()))
            activate_history(store, "2026-09-29")
            explanation = explain_order(store, "CUST_000001", "1", "2026-09-29")
            ready = evaluate_day(store, "2026-09-29")["ready"][0]["plan"]
            self.assertEqual(explanation, explain_order(store, "CUST_000001", "1", "2026-09-29"))
            self.assertEqual(explanation["current_plan"]["plan_key"], ready["plan_key"])
            self.assertTrue(explanation["current_plan"]["workable_now"])
            self.assertEqual(explanation["current_plan"]["presentation"], ready["presentation"])
            self.assertEqual(explanation["current_plan"]["primary_selection_reason"],
                             ready["presentation"]["primary_selection_reason"])
            self.assertEqual(explanation["current_plan"]["primary"]["rule_id"],
                             "magnetic_concentrator_completion")
            self.assertIn("brush_complement", {item["rule_id"]
                          for item in explanation["current_plan"]["alternatives"]})
            self.assertIn("hair_dryer_to_shavers_category_expansion",
                          {item["primary"]["rule_id"] for item in explanation["other_plans"]})
            self.assertIsNone(explanation["purchase_probability"])
            self.assertNotIn("one@example.invalid", str(explanation))
            store.close()

    def test_order_explanation_updates_after_target_purchase_and_shows_exclusion(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / "retention.sqlite3")
            store.save_state(merge_orders(None, imported()))
            activate_history(store, "2026-09-29")
            self.assertEqual(explain_order(store, "CUST_000001", "1", "2026-09-29")
                             ["current_plan"]["primary"]["rule_id"],
                             "magnetic_concentrator_completion")
            store.save_state(merge_orders(store.load_state(), imported("2", sku="CP34473")))
            updated = explain_order(store, "CUST_000001", "1", "2026-09-29")
            self.assertNotEqual(updated["current_plan"]["primary"]["rule_id"],
                                "magnetic_concentrator_completion")
            self.assertIn("magnetic_concentrator_completion", {item["rule_id"]
                          for item in updated["exclusions"]})
            self.assertEqual(updated["observed_order_count"], 2)
            store.close()

    def test_order_explanation_blocks_uncertain_profile_and_without_consent(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / "retention.sqlite3")
            state = merge_orders(None, imported(marketing="no"))
            state = merge_orders(state, imported("2", email="two@example.invalid",
                                                 validity="unknown"))
            store.save_state(state)
            activate_history(store, "2026-09-29")
            blocked = explain_order(store, "CUST_000001", "1", "2026-09-29")
            self.assertEqual(blocked["customer_status"], "blocked_consent")
            self.assertFalse(blocked["contact_permission"]["allowed"])
            self.assertFalse(blocked["current_plan"]["workable_now"])
            review = explain_order(store, "CUST_000002", "2", "2026-09-29")
            self.assertEqual(review["customer_status"], "review")
            self.assertIsNone(review["current_plan"])
            self.assertIn("uncertain_purchase", review["review_reasons"])
            with self.assertRaisesRegex(ValueError, "Ordine non presente"):
                explain_order(store, "CUST_000001", "2", "2026-09-29")
            store.close()

    def test_sync_imports_new_reduced_exports_once_and_updates_existing_profile(self):
        columns = ["Name", "Id", "Created at", "Financial Status", "Lineitem sku",
                   "Lineitem quantity", "Lineitem fulfillment status", "Cancelled at",
                   "Refunded Amount", "Email", "Accepts Marketing"]
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            store = Store(folder / "retention.sqlite3")

            def add_export(number, *, extra=False):
                path = folder / f"orders_export ({number}).csv"
                with path.open("w", encoding="utf-8-sig", newline="") as target:
                    writer = csv.DictWriter(target, fieldnames=columns + (["Phone"] if extra else []))
                    writer.writeheader()
                    writer.writerow({"Name": f"#{number}", "Id": str(number),
                                     "Created at": "2026-08-01 00:00:00 +0000",
                                     "Financial Status": "paid", "Lineitem sku": "CR05272",
                                     "Lineitem quantity": "1", "Lineitem fulfillment status": "fulfilled",
                                     "Cancelled at": "", "Refunded Amount": "0.00",
                                     "Email": "one@example.invalid", "Accepts Marketing": "yes",
                                     **({"Phone": "+390000000000"} if extra else {})})
                return path

            first = add_export(1, extra=True)
            self.assertEqual(sync_local_data(store, folder), 0)
            self.assertNotIn("Phone", first.read_text(encoding="utf-8-sig").splitlines()[0])
            self.assertEqual(len(store.import_history()), 1)
            add_export(2)
            self.assertEqual(sync_local_data(store, folder), 0)
            self.assertEqual(sync_local_data(store, folder), 0)
            self.assertEqual(len(store.import_history()), 2)
            state = store.load_state()
            self.assertEqual(len(state["profiles"]), 1)
            self.assertEqual(set(state["profiles"]["CUST_000001"]["orders"]), {"1", "2"})
            store.close()

    def test_sync_skips_invalid_export_without_importing_it(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            store = Store(folder / "retention.sqlite3")
            path = folder / "invalid.csv"
            path.write_text("Name,Phone\n#1,+390000000000\n", encoding="utf-8")
            self.assertEqual(sync_local_data(store, folder), 1)
            self.assertEqual(store.import_history(), [])
            self.assertEqual(store.load_state()["profiles"], {})
            self.assertIn("Phone", path.read_text(encoding="utf-8"))
            store.close()

    def test_sync_watch_imports_reduced_file_after_it_stabilizes(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            store = Store(folder / "retention.sqlite3")
            path = folder / "orders.csv"
            columns = ["Name", "Id", "Created at", "Financial Status", "Lineitem sku",
                       "Lineitem quantity", "Lineitem fulfillment status", "Cancelled at",
                       "Refunded Amount", "Email", "Accepts Marketing"]
            with path.open("w", encoding="utf-8-sig", newline="") as target:
                writer = csv.DictWriter(target, fieldnames=columns)
                writer.writeheader()
                writer.writerow({"Name": "#1", "Id": "1",
                                 "Created at": "2026-08-01 00:00:00 +0000",
                                 "Financial Status": "paid", "Lineitem sku": "CR05272",
                                 "Lineitem quantity": "1", "Lineitem fulfillment status": "fulfilled",
                                 "Cancelled at": "", "Refunded Amount": "0.00",
                                 "Email": "one@example.invalid", "Accepts Marketing": "yes"})
            with patch("src.shopify_orders.time.time", return_value=path.stat().st_mtime + 10), \
                 patch("src.shopify_orders.time.sleep", side_effect=[None, KeyboardInterrupt]):
                with self.assertRaises(KeyboardInterrupt):
                    sync_local_data(store, folder, watch=True)
            self.assertEqual(len(store.import_history()), 1)
            self.assertEqual(len(store.load_state()["profiles"]), 1)
            store.close()

    def test_csv_import_is_atomic_and_can_add_later_orders(self):
        columns = ["Name", "Id", "Created at", "Financial Status", "Lineitem sku",
                   "Lineitem quantity", "Lineitem fulfillment status", "Cancelled at",
                   "Refunded Amount", "Email", "Accepts Marketing"]
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / "retention.sqlite3")
            paths = []
            for order_id, email in (("1", "one@example.invalid"),
                                    ("2", "one@example.invalid")):
                path = Path(directory) / f"orders_{order_id}.csv"
                with path.open("w", encoding="utf-8-sig", newline="") as target:
                    writer = csv.DictWriter(target, fieldnames=columns)
                    writer.writeheader()
                    writer.writerow({"Name": f"#{order_id}", "Id": order_id,
                                     "Created at": "2026-08-01 00:00:00 +0000",
                                     "Financial Status": "paid", "Lineitem sku": "CR05272",
                                     "Lineitem quantity": "1", "Lineitem fulfillment status": "fulfilled",
                                     "Cancelled at": "", "Refunded Amount": "0.00",
                                     "Email": email, "Accepts Marketing": "yes"})
                paths.append(path)
            import_into_store(store, paths)
            self.assertEqual([entry["filename"] for entry in store.import_history()],
                             ["orders_1.csv", "orders_2.csv"])
            self.assertEqual(set(store.load_state()["profiles"]["CUST_000001"]["orders"]),
                             {"1", "2"})
            self.assertEqual(store.contact_email("CUST_000001"), "one@example.invalid")
            import_into_store(store, [paths[0]])
            self.assertEqual(len(store.load_state()["profiles"]["CUST_000001"]["orders"]), 2)
            self.assertEqual(len(store.import_history()), 3)
            with paths[1].open("w", encoding="utf-8-sig", newline="") as target:
                writer = csv.DictWriter(target, fieldnames=columns)
                writer.writeheader()
                writer.writerow({"Name": "#2", "Id": "2",
                                 "Created at": "2026-08-01 00:00:00 +0000",
                                 "Financial Status": "paid", "Lineitem sku": "CR05272",
                                 "Lineitem quantity": "1", "Lineitem fulfillment status": "fulfilled",
                                 "Cancelled at": "", "Refunded Amount": "0.00",
                                 "Email": "other@example.invalid", "Accepts Marketing": "yes"})
            with self.assertRaisesRegex(ValueError, "email diverse"):
                import_into_store(store, [paths[1]])
            self.assertEqual(store.contact_email("CUST_000001"), "one@example.invalid")
            self.assertEqual(len(store.import_history()), 3)
            store.close()

    def test_state_survives_reopen_and_repeated_import_keeps_stable_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "retention.sqlite3"
            store = Store(path)
            state = merge_orders(None, imported())
            store.save_state(state)
            store.close()
            store = Store(path)
            loaded = store.load_state()
            self.assertEqual(loaded, state)
            updated = merge_orders(loaded, imported("2"))
            updated = merge_orders(updated, imported())
            store.save_state(updated)
            store.close()
            store = Store(path)
            self.assertEqual(set(store.load_state()["profiles"]["CUST_000001"]["orders"]),
                             {"1", "2"})
            self.assertEqual(store.load_state()["contacts"]["CUST_000001"]["email"],
                             "one@example.invalid")
            store.close()

    def test_activation_and_events_change_daily_queue(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / "retention.sqlite3")
            store.save_state(merge_orders(None, imported()))
            self.assertEqual(evaluate_day(store, "2026-09-29")["ready"], [])
            activate_history(store, "2026-09-29")
            ready = evaluate_day(store, "2026-09-29")["ready"]
            self.assertEqual(len(ready), 1)
            plan = ready[0]["plan"]
            event = {"id": "EVENT_1", "type": "contact", "date": "2026-09-29",
                     "channel": "email", "rule_id": plan["primary_opportunity"]["rule_id"],
                     "plan_key": plan["plan_key"],
                     "primary_opportunity_key": plan["primary_opportunity"]["opportunity_key"],
                     "included_opportunity_keys": plan["included_opportunity_keys"]}
            record_event(store, "CUST_000001", event)
            record_event(store, "CUST_000001", event)
            self.assertEqual(len(store.events_for("CUST_000001")), 1)
            after_contact = explain_order(store, "CUST_000001", "1", "2026-09-29")
            self.assertEqual(after_contact["current_plan"]["contact_count"], 1)
            self.assertFalse(after_contact["current_plan"]["workable_now"])
            store.save_state(merge_orders(store.load_state(), imported()))
            self.assertEqual(len(store.events_for("CUST_000001")), 1)
            self.assertEqual(evaluate_day(store, "2026-09-29")["ready"], [])
            store.close()
            store = Store(Path(directory) / "retention.sqlite3")
            self.assertEqual(len(store.events_for("CUST_000001")), 1)
            self.assertEqual(len(evaluate_day(store, "2026-10-14")["ready"]), 1)
            rejection = {"id": "EVENT_2", "type": "plan_rejection", "date": "2026-10-14",
                         "plan_key": plan["plan_key"]}
            record_event(store, "CUST_000001", rejection)
            self.assertTrue(all(item["plan"]["plan_key"] != plan["plan_key"]
                                for item in evaluate_day(store, "2026-10-15")["ready"]))
            with self.assertRaisesRegex(ValueError, "dati diversi"):
                record_event(store, "CUST_000001", {**event, "date": "2026-09-30"})
            store.close()

    def test_uncertain_or_unsubscribed_profiles_never_enter_ready_queue(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / "retention.sqlite3")
            state = merge_orders(None, imported(marketing="no"))
            state = merge_orders(state, imported("2", email="two@example.invalid",
                                                 validity="unknown"))
            state = merge_orders(state, imported("3", email="three@example.invalid",
                                                 sku="UNKNOWN-SKU"))
            state = merge_orders(state, imported("4", email=None))
            store.save_state(state)
            activate_history(store, "2026-09-29")
            result = evaluate_day(store, "2026-09-29")
            self.assertEqual(result["ready"], [])
            self.assertEqual({case["reason"] for case in result["review"]},
                             {"missing_email", "uncertain_purchase", "unmapped_sku"})
            store.close()

    def test_new_order_with_conflicting_marketing_status_removes_ready_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / "retention.sqlite3")
            store.save_state(merge_orders(None, imported()))
            activate_history(store, "2026-09-29")
            self.assertEqual(len(evaluate_day(store, "2026-09-29")["ready"]), 1)
            store.save_state(merge_orders(store.load_state(), imported("2", marketing="no")))
            result = evaluate_day(store, "2026-09-29")
            self.assertEqual(result["ready"], [])
            self.assertEqual({case["reason"] for case in result["review"]},
                             {"uncertain_email_consent"})
            store.close()

    def test_reply_holds_queue_until_conversation_is_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / "retention.sqlite3")
            store.save_state(merge_orders(None, imported()))
            activate_history(store, "2026-09-29")
            plan = evaluate_day(store, "2026-09-29")["ready"][0]["plan"]
            contact = {"id": "CONTACT", "type": "contact", "date": "2026-09-29",
                       "channel": "email", "rule_id": plan["primary_opportunity"]["rule_id"],
                       "plan_key": plan["plan_key"],
                       "primary_opportunity_key": plan["primary_opportunity"]["opportunity_key"],
                       "included_opportunity_keys": plan["included_opportunity_keys"]}
            record_event(store, "CUST_000001", contact)
            record_event(store, "CUST_000001", {"id": "REPLY", "type": "reply",
                         "date": "2026-09-30", "rule_id": contact["rule_id"],
                         "plan_key": plan["plan_key"]})
            self.assertEqual(evaluate_day(store, "2026-10-14")["ready"], [])
            record_event(store, "CUST_000001", {"id": "CLOSED", "type": "conversation_closed",
                         "date": "2026-10-01", "plan_key": plan["plan_key"]})
            self.assertEqual(len(evaluate_day(store, "2026-10-14")["ready"]), 1)
            store.close()

    def test_contact_without_ready_plan_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / "retention.sqlite3")
            store.save_state(merge_orders(None, imported(marketing="no")))
            activate_history(store, "2026-09-29")
            with self.assertRaisesRegex(ValueError, "non è lavorabile"):
                record_event(store, "CUST_000001", {"id": "EVENT", "type": "contact",
                    "date": "2026-09-29", "channel": "email", "plan_key": ["1", "hair_care", "2026-08-16"]})
            self.assertEqual(store.events_for("CUST_000001"), [])
            store.close()


class MigrationTests(unittest.TestCase):
    def populate(self, store):
        state = merge_orders(None, imported())
        state = merge_orders(state, imported("2", email=None))
        store.save_state(state, imports=[("synthetic.csv", "synthetic-hash")])
        activate_history(store, "2026-09-29")
        store.add_event("CUST_000001", {"id": "Z-FIRST", "type": "contact", "date": "2026-09-29"})
        store.add_event("CUST_000001", {"id": "A-SECOND", "type": "reply", "date": "2026-09-30"})

    def test_copy_preserves_every_table_backup_and_insertion_order_without_changing_source(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Store(Path(directory) / "source.sqlite3")
            target = Store(Path(directory) / "target.sqlite3")
            try:
                self.populate(source)
                before = source._snapshot()
                result = migrate_sqlite(source.path, target)
                self.assertEqual(target._snapshot(), before)
                self.assertEqual(source._snapshot(), before)
                self.assertTrue(Path(result["backup"]).is_file())
                self.assertEqual(result["rows"], {"profiles": 1, "contacts": 1, "unassigned_orders": 1,
                                                "events": 2, "settings": 1, "imports": 1})
                self.assertEqual([row[0] for row in before["events"]], ["Z-FIRST", "A-SECOND"])
                with self.assertRaisesRegex(ValueError, "non vuota"):
                    migrate_sqlite(source.path, target)
                self.assertEqual(target._snapshot(), before)
            finally:
                source.close()
                target.close()

    def test_failed_verification_rolls_back_all_copied_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Store(Path(directory) / "source.sqlite3")
            target = Store(Path(directory) / "target.sqlite3")
            try:
                self.populate(source)
                empty = target._snapshot()
                with patch.object(target, "_snapshot", side_effect=[empty, {}]):
                    with self.assertRaisesRegex(ValueError, "Verifica"):
                        migrate_sqlite(source.path, target)
                self.assertEqual(target._snapshot(), empty)
                self.assertEqual(source.activation_date(), "2026-09-29")
            finally:
                source.close()
                target.close()

    def test_batch_events_match_individual_reads_and_include_later_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / "source.sqlite3")
            try:
                self.populate(store)
                self.assertEqual(store.events_by_customer(), {"CUST_000001": store.events_for("CUST_000001")})
                store.add_event("CUST_000001", {"id": "B-THIRD", "type": "reply", "date": "2026-10-01"})
                self.assertEqual(len(store.events_by_customer()["CUST_000001"]), 3)
            finally:
                store.close()

    def test_postgres_uses_tls_private_schema_and_preserves_connection_across_transactions(self):
        from unittest.mock import MagicMock
        import psycopg
        with self.assertRaisesRegex(ValueError, "stringa PostgreSQL"):
            Store("https://example.invalid")
        connection = MagicMock()
        with patch("psycopg.connect", return_value=connection) as connect:
            store = Store("postgresql://synthetic:password@example.invalid/test")
            self.assertTrue(store.postgres)
            self.assertIsNone(store.path)
            self.assertEqual(connect.call_args.kwargs["sslmode"], "require")
            self.assertTrue(connect.call_args.kwargs["autocommit"])
            sql = "\n".join(call.args[0] for call in connection.execute.call_args_list)
            self.assertIn("SET search_path TO retention", sql)
            self.assertIn("REVOKE ALL ON SCHEMA retention FROM PUBLIC", sql)
            self.assertIn("BIGSERIAL", sql)
            self.assertNotIn("AUTOINCREMENT", sql)
            store.contact_email("SYNTHETIC")
            self.assertIn("%s", connection.execute.call_args.args[0])
            connection.close.assert_not_called()
            store.close()
            connection.close.assert_called_once()
        connection = MagicMock()
        with patch("psycopg.connect", return_value=connection):
            store = Store("postgresql://synthetic:password@example.invalid/test", initialize=False)
            try:
                self.assertEqual([call.args[0] for call in connection.execute.call_args_list],
                                 ["SET search_path TO retention"])
            finally:
                store.close()
        with patch("psycopg.connect", side_effect=psycopg.OperationalError("synthetic secret")):
            with self.assertRaises(ValueError) as caught:
                Store("postgresql://synthetic:password@example.invalid/test")
            self.assertNotIn("synthetic secret", str(caught.exception))

    @unittest.skipUnless(os.environ.get("RRE_TEST_DATABASE_URL"), "PostgreSQL di test non configurato")
    def test_real_postgres_migration_and_new_imports_inside_rolled_back_transaction(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Store(Path(directory) / "source.sqlite3")
            target = Store(os.environ["RRE_TEST_DATABASE_URL"])
            try:
                self.assertFalse(any(target._snapshot().values()), "Usare un database di test vuoto.")
                self.populate(source)
                with target.connection.transaction(force_rollback=True):
                    migrate_sqlite(source.path, target)
                    self.assertEqual(target._snapshot(), source._snapshot())
                    updated = merge_orders(target.load_state(), imported("3"))
                    target.save_state(updated, imports=[("later.csv", "later-hash")])
                    self.assertEqual(len(target.load_state()["profiles"]["CUST_000001"]["orders"]), 2)
                    self.assertEqual(target.import_history()[-1]["sequence"], 2)
                    self.assertEqual(target.events_by_customer(), source.events_by_customer())
                self.assertFalse(any(target._snapshot().values()))
            finally:
                source.close()
                target.close()


if __name__ == "__main__":
    unittest.main()
