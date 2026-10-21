"""Contratto dei dati dell'Overview, usando soltanto ordini sintetici."""

from pathlib import Path
from base64 import b64encode
import csv
from http.server import ThreadingHTTPServer
import io
import json
import socket
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from src.customer_profiles import (RETENTION_URGENCY, _order_retention_rows, _product_images, activate_history, evaluate_day, merge_orders, overview_summary,
                                   record_event, retention_summary, revenue_summary, plan_detail, filter_retention, rules_summary)
from src.storage import Store
from src.shopify_orders import MINIMAL_COLUMNS
from src.web import main, make_handler


class RetentionUrgencyTests(unittest.TestCase):
    def row(self, customer, product, day, key="first_targeted"):
        return {"customer_id": customer, "proposal": product, "urgency": {**RETENTION_URGENCY[key], "key": key, "date": day},
                "category": "targeted" if key == "first_targeted" else "test" if key == "first_test" else "none",
                "customer_profile": {"signals": []}, "purchased_products": ["include"],
                "plans": [], "value_minor": 999999 if key == "waiting" else 1}

    def test_priority_product_rotation_age_and_determinism_without_changing_rows(self):
        rows = [self.row("A2", "A", "2026-08-02"), self.row("B1", "B", "2026-07-01"),
                self.row("R2", "R", "2026-09-02", "reply"), self.row("WAIT", "W", None, "waiting"),
                self.row("A1", "A", "2026-08-01"), self.row("B2", "B", "2026-07-02"),
                self.row("TEST", "T", "2026-01-01", "first_test"), self.row("A3", "A", "2026-08-03"),
                self.row("F2", "F", "2026-08-02", "follow_up"), self.row("R1", "R", "2026-09-01", "reply"),
                self.row("F1", "F", "2026-08-01", "follow_up")]
        original = json.loads(json.dumps(rows))
        ordered = _order_retention_rows(rows)
        self.assertEqual([row["customer_id"] for row in ordered], ["R1", "R2", "F1", "F2", "B1", "A1", "B2", "A2", "A3", "TEST", "WAIT"])
        self.assertEqual(ordered, _order_retention_rows(list(reversed(rows))))
        self.assertEqual(rows, original)
        self.assertEqual(_order_retention_rows([]), [])
        self.assertEqual(len({row["customer_id"] for row in ordered}), len(rows))

    def test_rotation_is_recomputed_for_filtered_rows(self):
        rows = [self.row("A1", "A", "2026-08-01"), self.row("A2", "A", "2026-08-02"),
                self.row("B1", "B", "2026-07-01"), self.row("B2", "B", "2026-07-02")]
        rows[2]["purchased_products"] = ["exclude"]
        data = {"customers": rows, "activity_views": [], "purchased_product_options": []}
        self.assertEqual([row["customer_id"] for row in filter_retention(data)], ["B1", "A1", "B2", "A2"])
        self.assertEqual([row["customer_id"] for row in filter_retention(data, product="include")], ["B2", "A1", "A2"])
        self.assertEqual(filter_retention(data, category="test"), [])


class OverviewTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.directory.name) / "test.sqlite3")
        order = {"id": "1", "number": "#1", "date": "2026-08-01", "marketing_signal": "yes",
                 "lines": [{"id": "1:CR05272", "order_id": "1", "sku": "CR05272",
                            "date": "2026-08-01", "quantity": 1, "validity": "valid"}]}
        self.store.save_state(merge_orders(None, {"orders": [order], "order_contacts": {
            "1": {"email": "demo@example.invalid"}}}))
        activate_history(self.store, "2026-08-01")

    def tearDown(self):
        self.store.close()
        self.directory.cleanup()

    def test_only_certain_contactable_profiles_contribute_to_queue_and_potential(self):
        data = overview_summary(self.store, "2026-10-05")
        self.assertEqual(data, overview_summary(self.store, "2026-10-05"))
        self.assertEqual(data["metrics"]["ready_customers"], 1)
        self.assertEqual(data["metrics"]["potential_value_minor"], 2499)
        self.assertEqual(data["metrics"]["attributed_revenue_minor"], 0)
        self.assertEqual(data["rows"][0]["customer_profile"]["signals"],
                         [{"key": "first_purchase", "label": "Primo acquisto"}])
        row = data["rows"][0]
        detail = plan_detail(self.store, row["customer_id"], row["plan_key"], "2026-10-05")
        self.assertEqual(detail["customer_profile"], row["customer_profile"])
        retention = retention_summary(self.store, "2026-10-05")
        self.assertEqual(retention["sections"]["ready"][0]["customer_profile"], detail["customer_profile"])
        self.assertEqual(retention["sections"]["ready"][0]["order_number"], "#1")
        self.assertEqual(retention["metrics"], data["metrics"])
        self.assertEqual(retention["profile_counts"]["ready"]["first_purchase"], 1)
        self.assertIsNone(retention["profile_counts"]["ready"]["possible_b2b"])
        self.assertEqual(data["activity_views"], retention["activity_views"])
        self.assertEqual(data["analyzed_customers"], 1)
        self.assertEqual({view["key"]: view["count"] for view in data["activity_views"]},
                         {"today": 0, "opportunities": 0, "history": 1})
        for consent in ("no", "unknown"):
            state = self.store.load_state()
            state["profiles"]["CUST_000001"]["orders"]["1"]["marketing_signal"] = consent
            self.store.save_state(state)
            result = overview_summary(self.store, "2026-10-05")
            self.assertEqual(result["rows"], [])
            self.assertEqual(result["metrics"]["potential_value_minor"], 0)

    def test_chart_uses_purchase_date_latest_correction_and_inclusive_period(self):
        for event in [
            {"id": "old", "type": "verified_purchase", "date": "2026-09-07",
             "purchase_date": "2026-09-05", "amount_minor": 1000},
            {"id": "in", "type": "verified_purchase", "date": "2026-09-08",
             "purchase_date": "2026-09-06", "amount_minor": 2999},
            {"id": "fix", "type": "revenue_correction", "date": "2026-10-01",
             "verified_purchase_event_id": "in", "amount_minor": 2499},
            {"id": "future", "type": "revenue_correction", "date": "2026-10-06",
             "verified_purchase_event_id": "in", "amount_minor": 0},
        ]:
            self.store.add_event("CUST_000001", event)
        result = overview_summary(self.store, "2026-10-05")
        self.assertEqual(result["starts_on"], "2026-09-06")
        self.assertEqual(result["chart"]["verified_orders"], 1)
        self.assertEqual(result["chart"]["attributed_revenue_minor"], 2499)
        self.assertEqual(result["chart"]["series"][0], {"date": "2026-09-06", "amount_minor": 2499})
        self.assertEqual(len(result["chart"]["series"]), 30)
        self.assertTrue(all(point["amount_minor"] == 0 for point in result["chart"]["series"][1:]))
        self.assertEqual(result["metrics"]["attributed_revenue_minor"], 3499)
        self.assertEqual(revenue_summary(self.store, "2026-10-05")["attributed_revenue_minor"], 3499)

    def test_proposal_reasons_follow_engine_facts_and_do_not_invent_completion_claims(self):
        detail = plan_detail(self.store, "CUST_000001", None, "2026-10-05")
        self.assertEqual(detail, plan_detail(self.store, "CUST_000001", None, "2026-10-05"))
        concentrator = next(p for p in detail["proposals"] if p["sku"] == "CP34473")
        self.assertEqual([reason["label"] for reason in concentrator["reasons"]],
                         ["Compatibile", "Non incluso", "Timing maturo"])
        self.assertEqual(concentrator["reasons"][-1]["date"], "2026-08-16")
        brush = next(p for p in detail["proposals"] if p["name"] == "Spazzola Laifen")
        self.assertEqual(brush["reasons"][0]["label"], "Complemento d’uso")
        self.assertFalse(any(reason["label"] == "Non incluso" for reason in brush["reasons"]))
        future = plan_detail(self.store, "CUST_000001", detail["plan_key"], "2026-08-05")
        self.assertEqual(future["proposals"][0]["reasons"][-1]["label"], "Timing futuro")
        self.assertNotIn("contact", future["event_templates"])
        state = self.store.load_state()
        order = state["profiles"]["CUST_000001"]["orders"]["1"]
        order["marketing_signal"] = "unknown"
        self.store.save_state(state)
        review = plan_detail(self.store, "CUST_000001", detail["plan_key"], "2026-10-05")
        self.assertTrue(review["review_reasons"])
        self.assertNotIn("contact", review["event_templates"])
        self.assertTrue(all(p["reasons"][0]["label"] == "Dati da verificare" for p in review["proposals"]))
        order["marketing_signal"] = "yes"
        order["lines"].append({"id": "OWNED", "order_id": "1", "sku": "CP34473",
                               "date": "2026-08-01", "quantity": 1, "validity": "valid"})
        self.store.save_state(state)
        owned = plan_detail(self.store, "CUST_000001", None, "2026-10-05")
        self.assertNotIn("CP34473", {p["sku"] for p in owned["proposals"]})
        order["lines"] = [{**order["lines"][0], "sku": "CQ15839"}]
        self.store.save_state(state)
        included = plan_detail(self.store, "CUST_000001", None, "2026-10-05")
        self.assertNotIn("CP34473", {p["sku"] for p in included["proposals"]})

    def test_replenishment_reasons_keep_future_timing_and_allow_repeat_purchase(self):
        state = self.store.load_state()
        order = state["profiles"]["CUST_000001"]["orders"]["1"]
        order["lines"] = [{**order["lines"][0], "sku": "CP96308"}]
        self.store.save_state(state)
        detail = plan_detail(self.store, "CUST_000001", None, "2026-10-05")
        heads = next(plan for plan in detail["operator_timeline"] if any(
            p["rule_id"] == "p3_pro_head_replenishment" for p in plan["proposals"]))
        future = plan_detail(self.store, "CUST_000001", heads["plan_key"], "2026-10-05")
        self.assertEqual([r["label"] for r in future["proposals"][0]["reasons"]],
                         ["Ricambio previsto", "Timing futuro"])
        self.assertNotIn("contact", future["event_templates"])
        order["lines"].append({"id": "HEAD", "order_id": "1", "sku": "30103-000019",
                               "date": "2026-08-01", "quantity": 1, "validity": "valid"})
        self.store.save_state(state)
        mature = plan_detail(self.store, "CUST_000001", None, "2027-02-01")
        self.assertIn("contact", mature["event_templates"])
        self.assertEqual([r["label"] for r in mature["proposals"][0]["reasons"]],
                         ["Ricambio previsto", "Timing maturo"])

    def test_customer_timing_separates_purchase_maturity_contact_and_seasonal_windows(self):
        state = self.store.load_state()
        order = state["profiles"]["CUST_000001"]["orders"]["1"]
        order["date"] = order["lines"][0]["date"] = "2026-09-07"
        self.store.save_state(state)
        detail = plan_detail(self.store, "CUST_000001", None, "2026-10-21")
        self.assertEqual(detail["timing"]["reference_date"], "2026-09-07")
        self.assertEqual(detail["timing"]["eligible_from_date"], "2026-09-22")
        self.assertEqual(detail["timing"]["days"], 15)
        self.assertEqual(detail["event_templates"]["contact"]["date"], "2026-10-21")
        by_rule = {p["rule_id"]: plan for plan in detail["operator_timeline"] for p in plan["proposals"]}
        auto = by_rule["autocurl_cross_sell"]
        self.assertEqual(auto["timing"]["label"], "Da 45 gg")
        self.assertFalse(auto["timing"]["awaiting_first_contact"])
        self.assertEqual(auto["timing"]["eligible_from_date"], "2026-10-22")
        self.assertIsNone(auto["next_contact_date"])
        self.assertEqual(by_rule["hair_dryer_to_shavers_category_expansion"]["timing"]["days"], 75)
        mini = by_rule["mini_travel_cross_sell"]
        self.assertEqual(mini["timing"]["label"], "Stagionale")
        self.assertIsNone(mini["timing"]["days"])
        self.assertEqual(mini["eligible_from_date"], "2026-12-15")
        before = plan_detail(self.store, "CUST_000001", detail["plan_key"], "2026-09-21")
        self.assertNotIn("contact", before["event_templates"])
        self.assertEqual(before["timing"], detail["timing"])
        record_event(self.store, "CUST_000001", {**detail["event_templates"]["contact"], "id": "ACTUAL-DATE"})
        saved = plan_detail(self.store, "CUST_000001", detail["plan_key"], "2026-10-21")
        self.assertEqual(saved["contacts"][0]["date"], "2026-10-21")
        auto = next(p for p in saved["operator_timeline"] if p["timing"]["days"] == 45)
        self.assertEqual(auto["timing"]["reference_date"], "2026-09-07")
        self.assertEqual(auto["timing"]["eligible_from_date"], "2026-10-22")
        self.assertIn("do_not_contact", saved["event_templates"])
        with self.assertRaises(ValueError):
            record_event(self.store, "CUST_000001", {**detail["event_templates"]["contact"], "date": "2026-10-22", "id": "EARLY"})
        record_event(self.store, "CUST_000001", {**saved["event_templates"]["do_not_contact"], "id": "STOP"})
        blocked = plan_detail(self.store, "CUST_000001", detail["plan_key"], "2026-10-21")
        self.assertFalse(blocked["contact_permission"]["allowed"])
        self.assertNotIn("contact", blocked["event_templates"])


    def test_repeat_head_timing_references_replacement_purchase_instead_of_initial_device(self):
        state = self.store.load_state()
        orders = state["profiles"]["CUST_000001"]["orders"]
        orders["1"]["date"] = orders["1"]["lines"][0]["date"] = "2026-01-01"
        orders["1"]["lines"][0]["sku"] = "CR95008"
        orders["2"] = {"id": "2", "number": "#SYNTHETIC-HEADS", "date": "2026-02-01", "marketing_signal": "yes",
                       "lines": [{"id": "HEADS", "order_id": "2", "sku": "CP38422", "date": "2026-02-01", "validity": "valid", "quantity": 1}]}
        self.store.save_state(state)
        detail = plan_detail(self.store, "CUST_000001", None, "2026-10-21")
        self.assertEqual(detail["timing"]["days"], 240)
        self.assertEqual(detail["timing"]["reference_date"], "2026-02-01")
        self.assertEqual(detail["timing"]["reference_label"], "Acquisto ricambio")
        self.assertEqual(detail["timing"]["eligible_from_date"], "2026-09-29")

    def test_categories_are_exclusive_and_secondary_strategy_is_searchable(self):
        data = retention_summary(self.store, "2026-10-05")
        self.assertEqual(data, retention_summary(self.store, "2026-10-05"))
        self.assertEqual(sum(view["count"] for view in data["operational_views"]), data["analyzed_customers"])
        self.assertEqual(len(data["operational_sections"]["targeted"]), 1)
        self.assertEqual(data["operational_sections"]["test"], [])
        self.assertEqual(filter_retention(data, category="targeted", strategy="complement", state="open"), [])
        self.assertEqual(len(filter_retention(data, strategy="completion")), 1)
        rows = filter_retention(data, category="targeted", strategy="complement", state="open", scope="all_plans")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["strategy"], "completion")
        self.assertTrue(all(op["strategy"] == "complement" for plan in rows[0]["matching_plans"] for op in plan["opportunities"]))
        self.assertEqual(filter_retention(data, category="test", strategy="complement"), [])
        self.assertEqual(filter_retention(data, state="open", strategy="expansion"), [])
        self.assertEqual(filter_retention(data, state="suspended", strategy="expansion"), [])
        self.assertEqual(len(filter_retention(data, state="suspended", strategy="expansion", scope="all_plans")), 1)
        self.assertEqual(filter_retention(data, profile="recurring"), [])
        self.assertEqual(len(filter_retention(data, profile="first_purchase")), 1)
        self.assertNotIn("demo@example.invalid", json.dumps(data))

    def test_purchased_product_filter_uses_all_valid_observed_purchases_and_combines_with_primary_filters(self):
        base = retention_summary(self.store, "2026-10-05")
        source_keys = set(base["customers"][0]["purchased_products"])
        state = self.store.load_state()
        orders = state["profiles"]["CUST_000001"]["orders"]
        orders["2"] = {"id": "2", "number": "#SYNTHETIC-SECOND", "date": "2026-09-01", "marketing_signal": "yes",
                       "lines": [{"id": "2:BRUSH", "order_id": "2", "sku": "CL51809", "date": "2026-09-01", "validity": "valid", "quantity": 1}]}
        self.store.save_state(state)
        data = retention_summary(self.store, "2026-10-05")
        brush = next(key for key in data["customers"][0]["purchased_products"] if key not in source_keys)
        rows = filter_retention(data, product=brush, strategy="completion", category="targeted", profile="recurring", activity="history")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["proposal"], base["customers"][0]["proposal"])
        self.assertEqual(filter_retention(data, product=brush, strategy="expansion"), [])
        self.assertEqual(filter_retention(data, product="unknown-product"), [])
        self.assertEqual(data, retention_summary(self.store, "2026-10-05"))
        label = next(option["label"] for option in data["purchased_product_options"] if option["value"] == brush)
        self.assertEqual(len(filter_retention(data, search=label)), 1)
        self.assertEqual(len(filter_retention(data, search="#synthetic-second")), 1)
        self.assertEqual(filter_retention(data, search="#missing-order"), [])
        for validity, day in (("unknown", "2026-09-01"), ("cancelled", "2026-09-01"), ("valid", "2026-10-06")):
            orders["2"]["date"] = orders["2"]["lines"][0]["date"] = day
            orders["2"]["lines"][0]["validity"] = validity
            self.store.save_state(state)
            excluded = retention_summary(self.store, "2026-10-05")
            self.assertEqual(filter_retention(excluded, product=brush), [])
            self.assertNotIn(brush, [option["value"] for option in excluded["purchased_product_options"]])
        self.assertEqual(filter_retention(excluded, search="#SYNTHETIC-SECOND"), [])

    def test_filters_preserve_accessory_and_replenishment_compatibility_for_every_device_variant(self):
        catalog = json.loads((Path(__file__).resolve().parents[1] / "src/catalog.json").read_text(encoding="utf-8"))
        expected = {
            "laifen_neo": {"neo_wall_mount_completion"},
            "laifen_neo_special": {"magnetic_concentrator_completion", "neo_wall_mount_completion"},
            "laifen_swift_premium": {"magnetic_concentrator_completion"},
            "laifen_se_lite": {"se_lite_diffuser_completion"},
            "laifen_mini": {"mini_wall_mount_completion"},
            "laifen_gift_edition": set(), "laifen_se_special": set(), "laifen_air": set(),
            "laifen_wave_legacy": {"wave_pro_heads_replenishment"},
            "laifen_wave_pro": {"wave_pro_heads_replenishment"},
            "laifen_p3": set(), "laifen_p3_pro": {"p3_pro_head_replenishment"},
        }
        checked_rules = set().union(*expected.values())
        orders, contacts, cases = [], {}, {}
        for product in catalog["products"]:
            if product["key"] not in expected:
                continue
            for variant in product["variants"]:
                sku = variant["sku"]
                orders.append({"id": sku, "number": "#SYNTHETIC-" + sku, "date": "2026-01-01", "marketing_signal": "yes",
                               "lines": [{"id": sku, "order_id": sku, "sku": sku, "date": "2026-01-01", "validity": "valid", "quantity": 1}]})
                contacts[sku] = {"email": sku.lower() + "@example.invalid"}
                allowed = expected[product["key"]].copy()
                if product["key"] == "laifen_neo" and variant["configuration"] == "two_nozzles":
                    allowed.add("magnetic_concentrator_completion")
                cases[sku] = (product["key"], allowed)
        self.store.save_state(merge_orders(None, {"orders": orders, "order_contacts": contacts}))
        data = retention_summary(self.store, "2026-06-30")
        self.assertEqual(len(data["customers"]), len(cases))
        for row in data["customers"]:
            sku = row["order_number"].removeprefix("#SYNTHETIC-")
            product, allowed = cases[sku]
            with self.subTest(sku=sku):
                actual = {op["rule_id"] for plan in row["plans"] for op in plan["opportunities"]} & checked_rules
                self.assertEqual(actual, allowed)
                self.assertIn(row["customer_id"], {r["customer_id"] for r in filter_retention(data, product=product)})
                for strategy in ("completion", "replenishment"):
                    matches = filter_retention(data, product=product, strategy=strategy, scope="all_plans")
                    self.assertEqual(row["customer_id"] in {r["customer_id"] for r in matches},
                                     any(op["strategy"] == strategy for p in row["plans"] for op in p["opportunities"]))

    def test_unmature_unknown_and_unsubscribed_do_not_become_workable_views(self):
        for day, consent, validity, purchase_day in [("2026-10-05", "yes", "valid", "2026-10-01"),
                                       ("2026-10-05", "no", "valid", "2026-08-01"),
                                       ("2026-10-05", "yes", "unknown", "2026-08-01")]:
            with self.subTest(day=day, consent=consent, validity=validity):
                state = self.store.load_state()
                order = state["profiles"]["CUST_000001"]["orders"]["1"]
                order["marketing_signal"] = consent
                order["lines"][0]["validity"] = validity
                order["date"] = purchase_day
                order["lines"][0]["date"] = purchase_day
                self.store.save_state(state)
                data = retention_summary(self.store, day)
                self.assertEqual(data["operational_sections"]["targeted"], [])
                self.assertEqual(data["operational_sections"]["test"], [])
                if consent == "no":
                    self.assertEqual(data["customers"], [])
                    self.assertEqual(data["analyzed_customers"], 0)
                    self.assertEqual(data["operational_sections"]["none"], [])
                    continue
                self.assertEqual(len(data["operational_sections"]["none"]), 1)
                row = data["operational_sections"]["none"][0]
                self.assertFalse(row["contactable"])
                detail = plan_detail(self.store, row["customer_id"], row["plan_key"], day)
                self.assertNotIn("contact", detail["event_templates"])

    def test_recurring_without_plan_is_no_action_and_can_open_history(self):
        state = self.store.load_state()
        orders = state["profiles"]["CUST_000001"]["orders"]
        orders["1"]["lines"][0]["sku"] = "CL51809"
        orders["2"] = {**orders["1"], "id": "2", "number": "#2", "date": "2026-08-10",
                       "lines": [{**orders["1"]["lines"][0], "id": "2:CL51809", "order_id": "2", "date": "2026-08-10"}]}
        self.store.save_state(state)
        data = retention_summary(self.store, "2026-10-05")
        row = filter_retention(data, profile="recurring")[0]
        self.assertEqual(row["customer_profile"]["valid_orders"], 2)
        self.assertIsNone(row["plan_key"])
        self.assertFalse(row["contactable"])
        self.assertEqual(len(data["operational_sections"]["none"]), 1)
        detail = plan_detail(self.store, row["customer_id"], None, "2026-10-05")
        self.assertEqual(len(detail["purchases"]), 2)
        self.assertEqual(detail["event_templates"], {})
        orders["2"]["marketing_signal"] = "no"
        self.store.save_state(state)
        blocked = retention_summary(self.store, "2026-10-05")
        self.assertEqual(filter_retention(blocked, profile="recurring"), [])
        self.assertEqual(blocked["operational_sections"]["none"], [])
        orders.pop("2")
        self.store.save_state(state)
        self.assertEqual(filter_retention(retention_summary(self.store, "2026-10-05"), profile="recurring"), [])

    def test_dashboard_consent_scope_excludes_invalid_signals_and_restores_valid_customers(self):
        for consent in ("yes", "no", "unknown", "yes"):
            with self.subTest(consent=consent):
                state = self.store.load_state()
                state["profiles"]["CUST_000001"]["orders"]["1"]["marketing_signal"] = consent
                self.store.save_state(state)
                data = retention_summary(self.store, "2026-10-05")
                expected = int(consent == "yes")
                self.assertEqual(data["analyzed_customers"], expected)
                self.assertEqual(len(filter_retention(data)), expected)
                self.assertEqual(sum(view["count"] for view in data["operational_views"]), expected)
                self.assertEqual(len(self.store.load_state()["profiles"]), 1)
                self.assertEqual(overview_summary(self.store, "2026-10-05")["activity_views"],
                                 data["activity_views"])

    def test_activity_cards_follow_maturity_actual_contacts_waiting_and_due_followup(self):
        customer = "CUST_000001"
        recent = retention_summary(self.store, "2026-09-14")
        self.assertEqual(recent["customers"][0]["activity"], "opportunities")
        historical = retention_summary(self.store, "2026-09-15")
        self.assertEqual(historical["customers"][0]["activity"], "history")
        self.assertEqual(historical["customers"][0]["urgency"]["key"], "first_targeted")
        self.assertTrue(historical["customers"][0]["urgency"]["mixed_plan"])
        self.assertEqual(filter_retention(historical, activity="opportunities"), [])
        self.assertEqual(len(filter_retention(historical, activity="history", category="targeted")), 1)
        self.assertEqual(filter_retention(historical, activity="history", category="test"), [])
        detail = plan_detail(self.store, customer, None, "2026-09-15")
        original_plan = detail["plan_key"]
        record_event(self.store, customer, {**detail["event_templates"]["contact"], "id": "SYNTHETIC-START"})
        waiting = retention_summary(self.store, "2026-09-29")
        self.assertEqual(waiting["customers"][0]["activity"], "today")
        self.assertEqual(waiting["customers"][0]["urgency"]["key"], "waiting")
        self.assertEqual(len(filter_retention(waiting, activity="today")), 1)
        self.assertEqual(filter_retention(waiting, activity="working"), filter_retention(waiting, activity="today"))
        self.assertEqual(waiting["customers"][0]["urgency"]["date"], "2026-09-30")
        self.assertEqual(waiting["customers"][0]["urgency"]["date_label"], "Attendi fino al")
        self.assertEqual(filter_retention(waiting, activity="history"), [])
        due = retention_summary(self.store, "2026-09-30")
        self.assertEqual(due["customers"][0]["activity"], "today")
        self.assertEqual(due["customers"][0]["urgency"]["key"], "follow_up")
        self.assertEqual(due["customers"][0]["urgency"]["date"], "2026-09-30")
        self.assertEqual(due["customers"][0]["plan_key"], original_plan)
        self.assertEqual(due["customers"][0]["source_date"], "2026-08-01")
        detail = plan_detail(self.store, customer, original_plan, "2026-10-01")
        record_event(self.store, customer, {**detail["event_templates"]["reply"], "id": "SYNTHETIC-RESPONSE"})
        response = retention_summary(self.store, "2026-10-01")
        self.assertEqual(response["customers"][0]["activity"], "today")
        self.assertEqual(response["customers"][0]["urgency"]["key"], "reply")
        self.assertEqual(response["customers"][0]["urgency"]["date"], "2026-09-15")
        self.assertFalse(response["customers"][0]["contactable"])
        self.assertEqual(response, retention_summary(self.store, "2026-10-01"))
        self.assertEqual(sum(view["count"] for view in response["activity_views"]), 1)
        detail = plan_detail(self.store, customer, original_plan, "2026-10-01")
        record_event(self.store, customer, {**detail["event_templates"]["plan_rejection"], "id": "SYNTHETIC-CLOSE"})
        after_close = retention_summary(self.store, "2026-10-01")
        self.assertEqual(filter_retention(after_close, activity="today"), [])
        self.assertNotEqual(after_close["customers"][0]["plan_key"], original_plan)
        self.assertIsNone(after_close["customers"][0]["activity"])
        self.assertFalse(after_close["customers"][0]["contactable"])
        self.assertEqual(retention_summary(self.store, "2026-10-30")["customers"][0]["activity"], "opportunities")
        self.assertEqual(after_close["customers"][0]["contact_count"], 0)
        self.assertEqual(sum(view["count"] for view in after_close["activity_views"])
                         + after_close["activity_unassigned_customers"], after_close["analyzed_customers"])

    def test_activity_cards_keep_future_uncertain_and_inactive_outside_recovery_and_exclude_no_consent(self):
        original = self.store.load_state()
        state = self.store.load_state()
        order = state["profiles"]["CUST_000001"]["orders"]["1"]
        order["date"] = order["lines"][0]["date"] = "2026-10-01"
        self.store.save_state(state)
        future = overview_summary(self.store, "2026-10-02")
        self.assertEqual(sum(view["count"] for view in future["activity_views"]), 0)
        self.assertEqual(future["activity_unassigned_customers"], 1)
        self.store.save_state(original)
        with patch.object(self.store, "activation_date", return_value=None):
            inactive = overview_summary(self.store, "2026-10-05")
            self.assertEqual(sum(view["count"] for view in inactive["activity_views"]), 0)
        for consent, validity in (("yes", "unknown"), ("no", "valid")):
            order = original["profiles"]["CUST_000001"]["orders"]["1"]
            order["marketing_signal"] = consent
            order["lines"][0]["validity"] = validity
            self.store.save_state(original)
            result = overview_summary(self.store, "2026-10-05")
            self.assertEqual(sum(view["count"] for view in result["activity_views"]), 0)
            self.assertEqual(result["analyzed_customers"], int(consent == "yes"))

    def test_hidden_customer_preserves_contacts_revenue_and_history(self):
        plan, contact = self.first_contact()
        record_event(self.store, "CUST_000001", {"id": "SALE_CONSENT", "type": "verified_purchase",
            "date": "2026-10-02", "plan_key": plan["plan_key"], "contact_event_id": contact["id"],
            "shopify_order_id": "SYNTHETIC_SALE", "purchased_sku": plan["primary_opportunity"]["target_sku"],
            "purchase_date": "2026-10-02", "amount_minor": 2499, "currency": "EUR", "verified_in_shopify": True})
        state = self.store.load_state()
        state["profiles"]["CUST_000001"]["orders"]["1"]["marketing_signal"] = "no"
        self.store.save_state(state)
        data = retention_summary(self.store, "2026-10-05")
        self.assertEqual(data["customers"], [])
        self.assertEqual(filter_retention(data, search="CUST_000001"), [])
        self.assertEqual(data["metrics"]["registered_contacts"], 1)
        self.assertEqual(data["metrics"]["attributed_revenue_minor"], 0)
        self.assertEqual(data["metrics"]["verified_orders"], 0)
        for period in ("30d", "90d", "6m", "12m"):
            overview = overview_summary(self.store, "2026-10-05", period)
            self.assertEqual(overview["chart"]["attributed_revenue_minor"], 0)
            self.assertEqual(overview["chart"]["verified_orders"], 0)
        self.assertEqual(revenue_summary(self.store, "2026-10-05")["attributed_revenue_minor"], 2499)
        detail = plan_detail(self.store, "CUST_000001", plan["plan_key"], "2026-10-05")
        self.assertEqual(len(detail["purchases"]), 1)
        self.assertEqual(len(detail["contacts"]), 1)
        self.assertNotIn("contact", detail["event_templates"])
        self.assertEqual(detail["attributed_revenue_minor"], 2499)
        state["profiles"]["CUST_000001"]["orders"]["1"]["marketing_signal"] = "yes"
        self.store.save_state(state)
        restored = overview_summary(self.store, "2026-10-05")
        self.assertEqual(restored["metrics"]["attributed_revenue_minor"], 2499)
        self.assertEqual(restored["chart"]["attributed_revenue_minor"], 2499)
        self.assertEqual(restored["chart"]["verified_orders"], 1)

    def test_case_and_upgrade_are_campaigns_while_mature_head_is_priority(self):
        original = self.store.load_state()
        for skus, day, expected in [(["CP96308"], "2026-10-05", "test"),
                                     (["CP96308", "30103-000019"], "2027-02-01", "targeted"),
                                     (["CL97510"], "2027-02-01", "targeted"),
                                     (["CL97510", "CR95042"], "2027-02-01", "test")]:
            with self.subTest(skus=skus):
                state = json.loads(json.dumps(original))
                order = state["profiles"]["CUST_000001"]["orders"]["1"]
                order["lines"] = [{"id": "1:"+sku, "order_id": "1", "sku": sku,
                                   "date": order["date"], "validity": "valid", "quantity": 1} for sku in skus]
                self.store.save_state(state)
                data = retention_summary(self.store, day)
                self.assertEqual(len(data["operational_sections"][expected]), 1)
                opposite = "targeted" if expected == "test" else "test"
                self.assertEqual(data["operational_sections"][opposite], [])

    def test_closed_plan_and_new_open_plan_keep_current_category_and_coherent_filters(self):
        plan, _ = self.first_contact()
        record_event(self.store, "CUST_000001", {"id": "CLOSE", "type": "plan_rejection",
                     "date": "2026-10-02", "plan_key": plan["plan_key"]})
        data = retention_summary(self.store, "2026-11-20")
        self.assertEqual(data["customers"][0]["category"], "test")
        self.assertEqual(data["customers"][0]["urgency"]["key"], "first_test")
        self.assertFalse(data["customers"][0]["urgency"]["mixed_plan"])
        self.assertEqual(filter_retention(data, category="test", state="closed", strategy="completion"), [])
        self.assertEqual(len(filter_retention(data, category="test", state="closed", strategy="completion", scope="all_plans")), 1)
        self.assertEqual(filter_retention(data, state="closed", strategy="expansion"), [])
        self.assertEqual(len(filter_retention(data, state="suspended", strategy="expansion", scope="all_plans")), 1)
        self.assertEqual(filter_retention(data, category="none", state="closed"), [])
        self.assertEqual(len(filter_retention(data)), 1)

    def test_rulebook_contains_all_rules_and_separates_strategies_from_categories(self):
        book = rules_summary()
        self.assertEqual(book, rules_summary())
        self.assertEqual(len(book["rules"]), 15)
        self.assertEqual(len({rule["id"] for rule in book["rules"]}), 15)
        self.assertEqual(len({rule["strategy"] for rule in book["rules"]}), 5)
        self.assertEqual(sum(rule["category"] == "targeted" for rule in book["rules"]), 6)
        self.assertTrue(all(rule["sources"] and rule["targets"] and rule["timing"] for rule in book["rules"]))
        self.assertTrue(all(target["sku"] and isinstance(target["value_minor"], int)
                            for rule in book["rules"] for target in rule["targets"]))
        self.assertNotIn("email", book)
        self.assertNotIn("policies", book)
        self.assertTrue(all(set(profile) == {"key", "label", "criterion"} for profile in book["profiles"]))
        self.assertNotIn("guides", book)
        self.assertEqual(len(book["strategies"]), 5)
        calendar = book["contact_calendar"]
        self.assertEqual(len(calendar["rows"]), 3)
        self.assertIn("45", calendar["rows"][1]["standard"])
        self.assertIn("45 giorni", calendar["rows"][1]["delayed"])
        self.assertIn("75", calendar["rows"][2]["standard"])
        self.assertIn("75 giorni", calendar["rows"][2]["delayed"])

        self.assertEqual({key for strategy in book["strategies"] for key in strategy["rule_ids"]},
                         {rule["id"] for rule in book["rules"]})
        for strategy in book["strategies"]:
            members = [rule for rule in book["rules"] if rule["id"] in strategy["rule_ids"]]
            self.assertTrue(strategy["meaning"] and strategy["examples"])
            self.assertEqual({rule["strategy"] for rule in members}, {strategy["key"]})
            self.assertEqual({rule["category"] for rule in members}, {strategy["category"]})
        self.assertIn("non è una probabilità", book["proposal_change"]["caveat"])

    def test_rulebook_profiles_describe_current_thresholds_without_changing_them(self):
        book = rules_summary()
        profiles = {item["key"]: item["criterion"] for item in book["profiles"]}
        self.assertEqual(set(profiles), {"first_purchase", "recurring", "multicategory", "recent_activity"})
        self.assertIn("3 ordini", profiles["recent_activity"])
        self.assertIn("90 giorni", profiles["recent_activity"])
        original = json.loads
        def changed_settings(value, *args, **kwargs):
            data = original(value, *args, **kwargs)
            if isinstance(data, dict) and "customer_signals" in data:
                data["customer_signals"]["recent_activity_minimum_orders"] = 5
                data["customer_signals"]["recent_activity_calendar_days"] = 60
            return data
        with patch("src.customer_profiles.json.loads", side_effect=changed_settings):
            updated = {item["key"]: item["criterion"] for item in rules_summary()["profiles"]}
        self.assertIn("5 ordini", updated["recent_activity"])
        self.assertIn("60 giorni", updated["recent_activity"])
        self.assertNotIn("90 giorni", updated["recent_activity"])

    def test_rulebook_flows_cover_rules_and_keep_seasonal_and_unsupported_models_separate(self):
        book = rules_summary()
        flows = {flow["id"]: flow for flow in book["flows"]}
        self.assertEqual(set(flows), {"hair_dryer", "electric_shaver", "electric_toothbrush"})
        self.assertEqual({key for flow in flows.values() for key in flow["rule_ids"]}, {r["id"] for r in book["rules"]})
        hair = flows["hair_dryer"]["stages"]
        self.assertEqual([stage["days"] for stage in hair], [15, 45, 75, None])
        self.assertEqual(hair[1]["rule_ids"], ["autocurl_cross_sell"])
        self.assertEqual(set(hair[2]["rule_ids"]), {"hair_dryer_to_wave_pro_category_expansion", "hair_dryer_to_shavers_category_expansion"})
        self.assertTrue(hair[-1]["seasonal"])
        self.assertEqual(hair[-1]["rule_ids"], ["mini_travel_cross_sell"])
        self.assertTrue(any("T1 Pro" in name for name in flows["electric_shaver"]["models_without_rules"]))
        self.assertEqual(flows["electric_toothbrush"]["models_without_rules"], [])

    def test_product_images_follow_catalog_skus_and_distinguish_p3_from_p3_pro(self):
        data = retention_summary(self.store, "2026-10-05")
        images = data["product_images"]
        self.assertEqual(images["1ER91-P-XX-BL-002"]["src"], "/assets/laifen-p3.jpg")
        self.assertEqual(images["1HC51-P-EU-WH-002"]["src"], "/assets/laifen-autocurl.jpg")
        self.assertEqual(images["CP96308"]["src"], "/assets/laifen-p3-pro-silver.jpg")
        self.assertNotEqual(images["CP96308"]["src"], images["1ER91-P-XX-BL-002"]["src"])
        self.assertEqual(images["CR05272"]["src"], "/assets/laifen-neo-black.jpg")
        self.assertEqual(images, overview_summary(self.store, "2026-10-05")["product_images"])
        self.assertEqual(images, plan_detail(self.store, "CUST_000001", data["customers"][0]["plan_key"], "2026-10-05")["product_images"])
        targets = [target for rule in rules_summary()["rules"] for target in rule["targets"]]
        self.assertTrue(all(target["image"] == images.get(target["sku"]) for target in targets))

    def test_air_and_wave_pro_photos_are_bound_to_exact_variants(self):
        images = retention_summary(self.store, "2026-10-05")["product_images"]
        expected = {"1HD20-S-EU-PU-001": "laifen-air-purple", "1HD20-S-EU-WH-001": "laifen-air-white",
                    "1HD20-S-EU-PK-001": "laifen-air-pink", "CR95008": "laifen-wave-pro-abs-white",
                    "CR95009": "laifen-wave-pro-abs-black", "CR95024": "laifen-wave-pro-abs-pink",
                    "CR95017": "laifen-wave-pro-aluminium-silver", "CR95041": "laifen-wave-pro-aluminium-grey",
                    "CR95016": "laifen-wave-pro-transparent"}
        for sku, filename in expected.items():
            self.assertEqual(images[sku]["src"], "/assets/" + filename + ".jpg")
        self.assertEqual(len({images[sku]["src"] for sku in expected}), 9)
        for sku in ("30102-000170", "30102-000171"):
            self.assertEqual(images[sku]["src"], "/assets/laifen-wave-pro-charging-base.jpg")
        for sku in ("CR95042", "CR95032", "6976973852011", "CR94994"):
            self.assertEqual(images[sku]["src"], "/assets/laifen-wave-pro-replacement-heads.jpg")
        self.assertEqual(images["CL97510"]["src"], "/assets/laifen-wave-abs-white.jpg")
        self.assertNotEqual(images["CL97510"]["src"], images["CR95008"]["src"])
        self.assertNotIn("CL97511", images)
        self.assertEqual(images["CP34510"]["src"], "/assets/laifen-se-lite-diffuser-grey.jpg")
        self.assertNotEqual(images["CP34510"]["src"], images["CP34520"]["src"])

    def test_variant_photo_overrides_product_photo_and_missing_photo_stays_absent(self):
        generic, specific = {"src": "/generic.jpg"}, {"src": "/specific.jpg"}
        catalog = {"products": [{"image": generic, "variants": [{"sku": "A", "image": specific}, {"sku": "B"}]},
                                {"variants": [{"sku": "C"}]}]}
        self.assertEqual(_product_images(catalog), {"A": specific, "B": generic})

    def test_supported_ranges_zero_history_and_invalid_period(self):
        for period, start in [("90d", "2026-07-08"), ("6m", "2026-04-06"), ("12m", "2025-10-06")]:
            result = overview_summary(self.store, "2026-10-05", period)
            self.assertEqual(result["starts_on"], start)
            self.assertTrue(all(point["amount_minor"] == 0 for point in result["chart"]["series"]))
        with self.assertRaisesRegex(ValueError, "Periodo non supportato"):
            overview_summary(self.store, "2026-10-05", "future")

    def first_contact(self):
        plan = evaluate_day(self.store, "2026-10-01")["ready"][0]["plan"]
        event = {"id": "CONTACT", "type": "contact", "date": "2026-10-01", "channel": "email",
                 "rule_id": plan["primary_opportunity"]["rule_id"], "plan_key": plan["plan_key"],
                 "primary_opportunity_key": plan["primary_opportunity"]["opportunity_key"],
                 "included_opportunity_keys": plan["included_opportunity_keys"]}
        record_event(self.store, "CUST_000001", event)
        return plan, event

    def test_overview_preview_reuses_retention_rows_for_ready_waiting_follow_up_and_replies(self):
        def check(day, urgency):
            retention = retention_summary(self.store, day)
            overview = overview_summary(self.store, day, evaluation=retention)
            self.assertEqual(overview["rows"], filter_retention(retention))
            self.assertEqual(overview["metrics"], retention["metrics"])
            self.assertEqual(overview["rows"][0]["urgency"]["key"], urgency)
            return overview
        check("2026-10-01", "first_targeted")
        plan, _ = self.first_contact()
        waiting = check("2026-10-02", "waiting")
        self.assertEqual(waiting["metrics"]["ready_customers"], 0)
        self.assertEqual({v["key"]: v["count"] for v in waiting["activity_views"]},
                         {"today": 1, "opportunities": 0, "history": 0})
        self.assertEqual(waiting["activity_unassigned_customers"], 0)
        self.assertEqual(len(waiting["rows"]), 1)
        check("2026-10-16", "follow_up")
        record_event(self.store, "CUST_000001", {"id": "REPLY", "type": "reply", "date": "2026-10-16",
                     "plan_key": plan["plan_key"], "rule_id": plan["primary_opportunity"]["rule_id"]})
        reply = check("2026-10-16", "reply")
        self.assertFalse(reply["rows"][0]["contactable"])
        state = self.store.load_state()
        state["profiles"]["CUST_000001"]["orders"]["1"]["marketing_signal"] = "no"
        self.store.save_state(state)
        self.assertEqual(overview_summary(self.store, "2026-10-16")["rows"], [])

    def test_retention_retry_moves_once_and_exhaustion_does_not_mean_rejection(self):
        plan, contact = self.first_contact()
        pending = retention_summary(self.store, "2026-10-02")
        self.assertEqual(pending["counts"]["ready"], 0)
        self.assertEqual(pending["counts"]["in_progress"], 1)
        self.assertEqual(pending["sections"]["in_progress"][0]["next_contact_date"], "2026-10-16")
        retry = retention_summary(self.store, "2026-10-16")
        self.assertEqual(retry["counts"]["in_progress"], 0)
        self.assertEqual(retry["sections"]["ready"][0]["plan_key"], plan["plan_key"])
        record_event(self.store, "CUST_000001", {**contact, "id": "SECOND", "date": "2026-10-16"})
        closed = retention_summary(self.store, "2026-10-16")["sections"]["closed"][0]
        self.assertEqual(closed["outcome"], "attempts_exhausted")
        self.assertEqual(closed["tone"], "neutral")
        self.assertIsNone(closed["revenue_minor"])
        self.assertEqual(len(closed["events"]), 2)

    def test_retention_product_rejection_keeps_plan_open_and_plan_rejection_closes(self):
        plan, _ = self.first_contact()
        record_event(self.store, "CUST_000001", {"id": "PRODUCT", "type": "product_rejection",
                     "date": "2026-10-02", "plan_key": plan["plan_key"],
                     "product_key": plan["primary_opportunity"]["target_product"]})
        pending = retention_summary(self.store, "2026-10-02")
        self.assertEqual(pending["counts"]["closed"], 0)
        self.assertEqual(pending["sections"]["in_progress"][0]["status_label"], "Risposta da gestire")
        record_event(self.store, "CUST_000001", {"id": "PLAN", "type": "plan_rejection",
                     "date": "2026-10-03", "plan_key": plan["plan_key"]})
        closed = retention_summary(self.store, "2026-10-03")["sections"]["closed"][0]
        self.assertEqual(closed["tone"], "red")
        self.assertIsNone(closed["revenue_minor"])

    def test_retention_verified_revenue_uses_same_corrections_as_overview(self):
        plan, contact = self.first_contact()
        record_event(self.store, "CUST_000001", {"id": "SALE", "type": "verified_purchase",
                     "date": "2026-10-02", "purchase_date": "2026-10-02", "plan_key": plan["plan_key"],
                     "contact_event_id": contact["id"], "purchased_sku": "CL51809", "shopify_order_id": "DEMO-2",
                     "amount_minor": 2499, "currency": "EUR", "verified_in_shopify": True})
        record_event(self.store, "CUST_000001", {"id": "FIX", "type": "revenue_correction",
                     "date": "2026-10-03", "plan_key": plan["plan_key"], "verified_purchase_event_id": "SALE",
                     "amount_minor": 1999, "currency": "EUR", "verified_in_shopify": True, "reason": "Sconto verificato"})
        for day, expected in [("2026-10-02", 2499), ("2026-10-03", 1999)]:
            data = retention_summary(self.store, day)
            self.assertEqual(data["totals"]["closed"], expected)
            self.assertEqual(data["sections"]["closed"][0]["tone"], "green")
            self.assertEqual(data["totals"]["closed"], revenue_summary(self.store, day)["attributed_revenue_minor"])
        state = self.store.load_state()
        state["profiles"]["CUST_000001"]["orders"]["1"]["marketing_signal"] = "unknown"
        self.store.save_state(state)
        self.assertEqual(retention_summary(self.store, "2026-10-03")["sections"], {"ready": [], "in_progress": [], "closed": []})


class QueueActionsTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.directory.name) / "queue.sqlite3")
        order = {"id": "QUEUE-1", "number": "#QUEUE-1", "date": "2026-08-01", "marketing_signal": "yes",
                 "lines": [{"id": "QUEUE-LINE", "order_id": "QUEUE-1", "sku": "CR05272",
                            "date": "2026-08-01", "quantity": 1, "validity": "valid"}]}
        self.store.save_state(merge_orders(None, {"orders": [order], "order_contacts": {
            "QUEUE-1": {"email": "queue@example.invalid"}}}))
        activate_history(self.store, "2026-08-01")
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.store, as_of="2026-10-05"))
        self.worker = threading.Thread(target=self.server.serve_forever)
        self.worker.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        self.row = self.get("/api/retention")["sections"]["ready"][0]

    def tearDown(self):
        self.server.shutdown()
        self.worker.join()
        self.server.server_close()
        self.store.close()
        self.directory.cleanup()

    def get(self, path):
        with urlopen(self.base + path, timeout=10) as response:
            return json.load(response)

    def detail(self):
        from urllib.parse import urlencode
        return self.get("/api/plan?" + urlencode({"customer": self.row["customer_id"],
                                                 "plan": json.dumps(self.row["plan_key"])}))

    def post(self, event, expected=200, **headers):
        request = Request(self.base + "/api/events", method="POST",
                          data=json.dumps({"customer_id": self.row["customer_id"], "event": event}).encode(),
                          headers={"Content-Type": "application/json", **headers})
        if expected != 200:
            with self.assertRaises(HTTPError) as caught:
                urlopen(request, timeout=10)
            self.assertEqual(caught.exception.code, expected)
            return json.load(caught.exception)
        with urlopen(request, timeout=10) as response:
            return json.load(response)

    def contact(self):
        event = {**self.detail()["event_templates"]["contact"], "id": "QUEUE-CONTACT"}
        self.post(event)
        return event

    def test_http_filters_and_rulebook(self):
        self.assertEqual(self.get("/api/retention?category=targeted&strategy=complement&state=open")["rows"], [])
        data = self.get("/api/retention?category=targeted&strategy=complement&state=open&scope=all_plans")
        self.assertEqual(len(data["rows"]), 1)

        self.assertEqual(data["rows"][0]["strategy"], "completion")
        self.assertEqual(self.get("/api/retention?category=test&strategy=complement")["rows"], [])
        self.assertEqual(data["metrics"], self.get("/api/retention")["metrics"])
        self.assertEqual(len(self.get("/api/rules")["rules"]), 15)
        self.assertEqual(len(self.get("/api/retention?activity=history")["rows"]), 1)
        self.assertEqual(self.get("/api/retention?activity=today")["rows"], [])
        self.assertEqual(self.get("/api/retention?activity=history&category=test")["rows"], [])
        product = data["purchased_product_options"][0]["value"]
        self.assertEqual(len(self.get("/api/retention?product=" + product)["rows"]), 1)
        self.assertEqual(self.get("/api/retention?product=unknown-product")["rows"], [])
        with urlopen(self.base + "/rules") as response:
            self.assertEqual(response.status, 200)
            self.assertIn(b"/rules.js", response.read())

    def test_read_cache_shares_evaluation_and_never_reuses_old_committed_data(self):
        # setUp has warmed the cache. Filters/periods reuse it; external Store writes invalidate it.
        with patch("src.web.retention_summary", wraps=retention_summary) as evaluate:
            original = self.get("/api/retention")
            self.get("/api/overview?period=30d")
            self.get("/api/overview?period=90d")
            self.get("/api/retention?strategy=expansion")
            self.assertEqual(evaluate.call_count, 0)
            self.assertEqual(self.get("/api/retention"), original)
            state = self.store.load_state()
            state["profiles"][self.row["customer_id"]]["orders"]["QUEUE-1"]["marketing_signal"] = "no"
            self.store.save_state(state)
            self.assertEqual(self.get("/api/retention")["rows"], [])
            self.assertEqual(self.get("/api/overview")["metrics"]["ready_customers"], 0)
            self.assertEqual(evaluate.call_count, 1)

    def test_compact_compressed_response_keeps_filtering_and_removes_duplicate_collections(self):
        import gzip
        full = self.get("/api/retention?category=targeted")
        request = Request(self.base + "/api/retention?category=targeted&compact=1", headers={"Accept-Encoding": "gzip"})
        with urlopen(request, timeout=10) as response:
            body = response.read()
            self.assertEqual(response.headers["Content-Encoding"], "gzip")
            self.assertEqual(response.headers["Cache-Control"], "no-store")
            compact = json.loads(gzip.decompress(body))
        self.assertLess(len(body), len(json.dumps(full).encode()))
        for key in ("rows", "metrics", "activity_views", "operational_views", "purchased_product_options", "urgency_legend"):
            self.assertEqual(compact[key], full[key])
        for key in ("sections", "customers", "operational_sections", "summaries", "profile_counts"):
            self.assertNotIn(key, compact)
        self.assertEqual(self.get("/api/retention?category=targeted"), full)
        for encoding in ("br", "gzip;q=0"):
            with urlopen(Request(self.base + "/api/retention?compact=1", headers={"Accept-Encoding": encoding}), timeout=10) as response:
                self.assertIsNone(response.headers.get("Content-Encoding"))
                self.assertEqual(json.load(response)["metrics"], full["metrics"])

    def test_concurrent_cold_requests_evaluate_the_portfolio_once(self):
        from concurrent.futures import ThreadPoolExecutor
        self.server.RequestHandlerClass = make_handler(self.store, as_of="2026-10-05")
        with patch("src.web.retention_summary", wraps=retention_summary) as evaluate:
            with ThreadPoolExecutor(max_workers=4) as pool:
                responses = list(pool.map(self.get, ["/api/overview", "/api/retention?compact=1",
                                                    "/api/overview?period=90d", "/api/retention?strategy=expansion"]))
            self.assertEqual(evaluate.call_count, 1)
            self.assertTrue(all(response["date"] == "2026-10-05" for response in responses))

    def test_day_and_configuration_changes_invalidate_cached_evaluation(self):
        import os
        self.server.RequestHandlerClass = make_handler(self.store)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("catalog.json", "rules.json", "promotions.json"):
                (root / name).write_text("{}", encoding="utf-8")
            with patch("src.web.__file__", str(root / "web.py")), patch("src.web.datetime") as clock, \
                    patch("src.web.retention_summary", wraps=retention_summary) as evaluate:
                clock.now.return_value.date.return_value.isoformat.return_value = "2026-10-05"
                self.get("/api/retention")
                self.get("/api/overview")
                self.assertEqual(evaluate.call_count, 1)
                clock.now.return_value.date.return_value.isoformat.return_value = "2026-10-06"
                self.assertEqual(self.get("/api/overview")["date"], "2026-10-06")
                self.assertEqual(evaluate.call_count, 2)
                path = root / "rules.json"
                stat = path.stat()
                os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1000000000))
                self.get("/api/retention")
                self.assertEqual(evaluate.call_count, 3)

    def test_upgrade_contact_history_has_real_wave_pro_variants(self):
        state = self.store.load_state()
        order = state["profiles"][self.row["customer_id"]]["orders"]["QUEUE-1"]
        order["date"] = "2026-01-01"
        order["lines"] = [{"id": "WAVE", "order_id": "QUEUE-1", "sku": "CL97510",
                           "date": order["date"], "validity": "valid", "quantity": 1},
                          {"id": "HEADS", "order_id": "QUEUE-1", "sku": "CR95042",
                           "date": "2026-09-01", "validity": "valid", "quantity": 1}]
        self.store.save_state(state)
        plan = next(item["plan"] for item in evaluate_day(self.store, "2026-10-05")["ready"])
        self.assertEqual(plan["primary_opportunity"]["rule_id"], "toothbrush_to_neo_category_expansion")
        # Exclude hair expansion with an already owned phon and its completions.
        for sku in ("CR05272", "CL51809", "CP34473", "30101-000092", "30101-000041", "CP96308", "30103-000019", "1HC51-P-EU-BL-001"):
            order["lines"].append({"id": sku, "order_id": "QUEUE-1", "sku": sku,
                                   "date": "2026-09-01", "validity": "valid", "quantity": 1})
        self.store.save_state(state)
        row = self.get("/api/retention")["rows"][0]
        self.assertEqual(row["strategy"], "replacement")
        detail = plan_detail(self.store, row["customer_id"], row["plan_key"], "2026-10-05")
        record_event(self.store, row["customer_id"], {**detail["event_templates"]["contact"], "id": "UPGRADE"})
        detail = plan_detail(self.store, row["customer_id"], row["plan_key"], "2026-10-05")
        self.assertTrue(all(product["sku"] for product in detail["contacts"][0]["products"]))
        self.assertNotIn("CL97510", {product["sku"] for product in detail["contacts"][0]["products"]})

    def test_legacy_wave_heads_reach_overview_retention_detail_and_rulebook(self):
        state = self.store.load_state()
        order = state["profiles"][self.row["customer_id"]]["orders"]["QUEUE-1"]
        order["date"] = "2026-01-01"
        order["lines"] = [{"id": "WAVE", "order_id": "QUEUE-1", "sku": "CL97510", "date": "2026-01-01",
                           "validity": "valid", "quantity": 1}]
        self.store.save_state(state)
        data = self.get("/api/retention?compact=1&strategy=replenishment")
        self.assertEqual(len(data["rows"]), 1)
        row = data["rows"][0]
        self.assertEqual(row["category"], "targeted")
        self.assertEqual(self.get("/api/overview")["rows"][0]["strategy"], "replenishment")
        detail = plan_detail(self.store, row["customer_id"], row["plan_key"], "2026-10-05")
        self.assertIn("contact", detail["event_templates"])
        self.assertEqual(detail["event_templates"]["contact"]["cycle_reference_purchase_id"], "WAVE")
        rule = next(r for r in self.get("/api/rules")["rules"] if r["id"] == "wave_pro_heads_replenishment")
        self.assertEqual({source["product_key"] for source in rule["sources"]}, {"laifen_wave_legacy", "laifen_wave_pro"})
        order["marketing_signal"] = "no"
        self.store.save_state(state)
        self.assertEqual(self.get("/api/retention?compact=1&strategy=replenishment")["rows"], [])

    def test_contact_is_idempotent_and_refreshes_queue_without_leaking_email_to_lists(self):
        detail = self.detail()
        self.assertEqual(detail, self.detail())
        self.assertEqual(detail["contact_email"], "queue@example.invalid")
        self.assertNotIn("queue@example.invalid", json.dumps(self.get("/api/retention")))
        self.assertEqual(set(detail["event_templates"]), {"contact"})
        event = self.contact()
        self.post(event)
        self.assertEqual(len(self.store.events_for(self.row["customer_id"])), 1)
        self.assertEqual(self.get("/api/retention")["counts"], {"ready": 0, "in_progress": 1, "closed": 0})
        self.assertNotIn("contact", self.detail()["event_templates"])
        self.post({**event, "id": "SECOND-TOO-SOON"}, expected=400)
        self.post({**event, "date": "2026-10-04"}, expected=400)

    def test_customer_detail_includes_both_products_and_backend_timeline_for_shared_or_separate_orders(self):
        original = self.store.load_state()
        for shared_order in (True, False):
            with self.subTest(shared_order=shared_order):
                state = json.loads(json.dumps(original))
                orders = state["profiles"][self.row["customer_id"]]["orders"]
                wave = {"id": "WAVE-LINE", "order_id": "QUEUE-1" if shared_order else "QUEUE-2",
                        "sku": "CR95008", "date": "2026-08-01", "quantity": 1, "validity": "valid"}
                if shared_order:
                    orders["QUEUE-1"]["lines"].append(wave)
                else:
                    orders["QUEUE-2"] = {"id": "QUEUE-2", "number": "#QUEUE-2", "date": "2026-08-01",
                                         "marketing_signal": "yes", "lines": [wave]}
                orders["FUTURE"] = {"id": "FUTURE", "number": "#FUTURE", "date": "2027-01-01",
                    "marketing_signal": "no", "lines": [{"id": "FUTURE-LINE", "sku": "CL51809",
                    "order_id": "FUTURE", "date": "2027-01-01", "quantity": 1, "validity": "valid"}]}
                self.store.save_state(state)
                detail = self.detail()
                self.assertEqual(detail, self.detail())
                self.assertEqual({item["sku"] for item in detail["purchases"]}, {"CR05272", "CR95008"})
                self.assertEqual(detail["source_purchase"]["sku"], "CR05272")
                self.assertEqual(detail["source_purchase"]["configuration"], "2 Ugelli")
                self.assertEqual(detail["source_purchase"]["color"], "Shadow Black")
                self.assertEqual(detail["source_purchase"]["order_number"], "#QUEUE-1")
                rules = {proposal["rule_id"] for item in detail["operator_timeline"] for proposal in item["proposals"]}
                self.assertIn("wave_pro_heads_replenishment", rules)
                self.assertNotIn("hair_dryer_to_wave_pro_category_expansion", rules)
                heads = next(item for item in detail["operator_timeline"] if any(
                    proposal["rule_id"] == "wave_pro_heads_replenishment" for proposal in item["proposals"]))
                self.assertEqual(heads["eligible_from_date"], "2026-12-29")
                self.assertIsNone(heads["next_contact_date"])
                self.assertIn(detail["plan_key"], heads["blocking_plan_keys"])
                self.assertEqual(detail["contact_permission"]["consent_status"], "subscribed")
                self.assertNotIn("queue@example.invalid", json.dumps(self.get("/api/overview")))

    def test_customer_history_includes_other_plans_without_mixing_outcome_options(self):
        state = self.store.load_state()
        profile = state["profiles"][self.row["customer_id"]]
        profile["orders"]["CASE"] = {"id": "CASE", "number": "#CASE", "date": "2026-08-02",
            "marketing_signal": "yes", "lines": [{"id": "CASE-LINE", "order_id": "CASE",
            "date": "2026-08-02", "sku": "CP96308", "quantity": 1, "validity": "valid"}]}
        order = profile["orders"]["QUEUE-1"]
        for sku in ("CP34473", "30101-000092"):
            order["lines"].append({"id": sku, "order_id": order["id"], "date": order["date"], "sku": sku, "quantity": 1, "validity": "valid"})
        self.store.save_state(state)
        other = next(item["plan"] for item in evaluate_day(self.store, "2026-08-20")["ready"]
                     if item["customer_id"] == self.row["customer_id"])
        template = plan_detail(self.store, self.row["customer_id"], other["plan_key"], "2026-08-20")["event_templates"]["contact"]
        record_event(self.store, self.row["customer_id"], {**template, "id": "OTHER-CONTACT"})
        detail = self.detail()
        self.assertEqual([event["id"] for event in detail["customer_events"]], ["OTHER-CONTACT"])
        self.assertEqual(detail["customer_events"][0]["proposal_names"], ["Laifen Mini"])
        self.assertEqual(detail["events"], [])
        self.assertEqual(detail["products"], [])
        self.assertNotIn("verified_purchase", detail["event_templates"])

    def test_replenishment_contact_and_reply_keep_cycle_and_reject_missing_or_wrong_reference(self):
        state = self.store.load_state()
        order = state["profiles"][self.row["customer_id"]]["orders"]["QUEUE-1"]
        order["date"] = "2026-01-01"
        order["lines"] = [{"id": "P3", "order_id": "QUEUE-1", "sku": "CP96308", "date": "2026-01-01",
                           "quantity": 1, "validity": "valid"},
                          {"id": "CASE", "order_id": "QUEUE-1", "sku": "30103-000019", "date": "2026-01-01",
                           "quantity": 1, "validity": "valid"}]
        self.store.save_state(state)
        self.row = self.get("/api/retention")["sections"]["ready"][0]
        detail = self.detail()
        event = {**detail["event_templates"]["contact"], "id": "CYCLE-CONTACT"}
        self.assertEqual(event["cycle_reference_purchase_id"], "P3")
        missing = dict(event)
        missing.pop("cycle_reference_purchase_id")
        self.post(missing, expected=400)
        self.post({**event, "cycle_reference_purchase_id": "OTHER"}, expected=400)
        self.assertEqual(self.store.events_for(self.row["customer_id"]), [])
        self.post(event)
        detail = self.detail()
        self.assertEqual(detail["tracked_plan"]["contact_count"], 1)
        reply = {**detail["event_templates"]["reply"], "id": "CYCLE-REPLY"}
        self.assertEqual(reply["cycle_reference_purchase_id"], "P3")
        self.post({**reply, "cycle_reference_purchase_id": "OTHER"}, expected=400)
        self.post(reply)
        self.assertEqual(self.detail()["current_plan"]["raw_status"], "operator_response")
        self.post({**detail["event_templates"]["conversation_closed"], "id": "CYCLE-HANDLED"})
        self.assertEqual(self.detail()["tracked_plan"]["contact_count"], 1)

    def test_responses_use_presented_products_and_plan_rejection_closes(self):
        self.contact()
        detail = self.detail()
        interest = {**detail["event_templates"]["product_interest"], "id": "INTEREST",
                    "product_key": detail["products"][0]["key"]}
        self.post({**interest, "product_key": "not-presented"}, expected=400)
        self.post(interest)
        self.assertEqual(self.get("/api/retention")["sections"]["in_progress"][0]["status_label"], "Risposta da gestire")
        self.post({**detail["event_templates"]["conversation_closed"], "id": "HANDLED"})
        self.post({**detail["event_templates"]["product_rejection"], "id": "PRODUCT-NO",
                   "product_key": detail["products"][0]["key"]})
        self.assertEqual(self.get("/api/retention")["counts"]["closed"], 0)
        self.post({**detail["event_templates"]["plan_rejection"], "id": "PLAN-NO"})
        self.assertEqual(self.get("/api/retention")["sections"]["closed"][0]["outcome"], "plan_rejection")

    def test_purchase_and_correction_update_results_with_existing_validation(self):
        contact = self.contact()
        detail = self.detail()
        sale = {**detail["event_templates"]["verified_purchase"], "id": "SALE", "shopify_order_id": "QUEUE-SALE",
                "contact_event_id": contact["id"], "purchased_sku": detail["contacts"][0]["products"][0]["sku"],
                "purchase_date": "2026-10-05", "amount_minor": 2999, "verified_in_shopify": True}
        self.post({**sale, "verified_in_shopify": False}, expected=400)
        self.post({**sale, "purchased_sku": "CR05272"}, expected=400)
        self.post(sale)
        self.post(sale)
        self.post({**sale, "id": "DUPLICATE-SALE"}, expected=400)
        self.assertEqual(self.get("/api/retention")["totals"]["closed"], 2999)
        correction = {**self.detail()["event_templates"]["revenue_correction"], "id": "CORRECTION",
                      "verified_purchase_event_id": "SALE", "amount_minor": 2499,
                      "verified_in_shopify": True, "reason": "Rimborso parziale verificato"}
        self.post({**correction, "reason": ""}, expected=400)
        self.post(correction)
        self.assertEqual(self.get("/api/overview")["metrics"]["attributed_revenue_minor"], 2499)
        self.assertEqual(self.get("/api/retention")["totals"]["closed"], 2499)
        self.assertEqual(len(self.detail()["events"]), 3)
        self.assertEqual(self.detail()["attributed_revenue_minor"], 2499)
        self.assertEqual(self.detail()["tracked_plan"]["outcome"], "verified_purchase")

    def test_invalid_stale_and_cross_origin_requests_do_not_write(self):
        event = {**self.detail()["event_templates"]["contact"], "id": "INVALID"}
        self.post({**event, "date": "2026-10-06"}, expected=400)
        self.post(event, expected=400, Origin="https://example.invalid")
        self.post(event, expected=400, **{"Content-Type": "text/plain"})
        self.post(None, expected=400)
        self.post({**event, "included_opportunity_keys": []}, expected=400)
        self.post({"id": "NO-CONTACT", "type": "reply", "date": "2026-10-05",
                   "plan_key": event["plan_key"], "rule_id": event["rule_id"]}, expected=400)
        state = self.store.load_state()
        state["profiles"][self.row["customer_id"]]["orders"]["QUEUE-1"]["marketing_signal"] = "no"
        self.store.save_state(state)
        self.assertNotIn("contact", self.detail()["event_templates"])
        self.post(event, expected=400)
        self.assertEqual(self.store.events_for(self.row["customer_id"]), [])


class OverviewServerTests(unittest.TestCase):
    def test_upload_is_sanitized_imported_idempotently_and_demo_rejects_upload(self):
        with tempfile.TemporaryDirectory() as directory, patch("src.web.ROOT", Path(directory)):
            ready = threading.Event()
            servers = []

            def run(demo):
                store = Store(Path(directory) / "test.sqlite3")
                server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(store, demo=demo, as_of="2026-10-05"))
                servers.append(server)
                ready.set()
                try:
                    server.serve_forever()
                finally:
                    server.server_close()
                    store.close()

            buffer = io.StringIO(newline="")
            writer = csv.DictWriter(buffer, fieldnames=MINIMAL_COLUMNS + ["Billing Name"])
            writer.writeheader()
            writer.writerow({"Name": "#DEMO", "Id": "DEMO", "Created at": "2026-08-01 12:00:00 +0200",
                             "Financial Status": "paid", "Lineitem sku": "CR05272", "Lineitem quantity": "1",
                             "Lineitem fulfillment status": "fulfilled", "Refunded Amount": "0",
                             "Email": "demo@example.invalid", "Accepts Marketing": "yes", "Billing Name": "Demo"})
            body = ('--test\r\nContent-Disposition: form-data; name="files"; filename="demo.csv"\r\n'
                    'Content-Type: text/csv\r\n\r\n' + buffer.getvalue() + '\r\n--test--\r\n').encode()
            for demo in (False, True):
                ready.clear()
                worker = threading.Thread(target=run, args=(demo,))
                worker.start()
                self.assertTrue(ready.wait(10))
                server = servers[-1]
                base = f"http://127.0.0.1:{server.server_port}"
                try:
                    # Una connessione anticipata del browser non deve bloccare pagina o API.
                    with socket.create_connection(("127.0.0.1", server.server_port), timeout=3) as idle:
                        self.assertEqual(urlopen(base + "/", timeout=3).status, 200)
                        self.assertEqual(urlopen(base + "/retention", timeout=3).status, 200)
                        self.assertEqual(json.load(urlopen(base + "/api/retention", timeout=3))["counts"]["ready"], 0)
                        self.assertEqual(json.load(urlopen(base + "/api/overview", timeout=3))["demo"], demo)
                    request = Request(base + "/api/import", data=body,
                                      headers={"Content-Type": "multipart/form-data; boundary=test"})
                    if demo:
                        with self.assertRaises(HTTPError) as caught:
                            urlopen(request, timeout=10)
                        self.assertEqual(caught.exception.code, 409)
                        continue
                    for _ in range(2):
                        self.assertEqual(json.load(urlopen(request, timeout=10))["imported_files"], 1)
                    data = json.load(urlopen(base + "/api/overview", timeout=10))
                    self.assertFalse(data["active"])
                    retention = json.load(urlopen(base + "/api/retention", timeout=10))
                    self.assertEqual(data["rows"], retention["rows"])
                    self.assertTrue(all(not row["contactable"] for row in data["rows"]))
                    self.assertEqual(data["metrics"]["ready_customers"], 0)
                    exports = list((Path(directory) / "uploads").glob("*.csv"))
                    self.assertEqual(len(exports), 2)
                    for export in exports:
                        with export.open(encoding="utf-8-sig", newline="") as source:
                            self.assertEqual(csv.DictReader(source).fieldnames, MINIMAL_COLUMNS)
                finally:
                    server.shutdown()
                    worker.join(10)
            store = Store(Path(directory) / "test.sqlite3")
            try:
                self.assertEqual(len(store.load_state()["profiles"]), 1)
                self.assertEqual(len(store.load_state()["profiles"]["CUST_000001"]["orders"]), 1)
            finally:
                store.close()


class HostedServerTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.directory.name) / "retention.sqlite3")
        self.authorization = "Basic " + b64encode(b"synthetic:synthetic-password").decode()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(
            self.store, credentials=("synthetic", "synthetic-password"),
            public_origin="https://retention.example.invalid", as_of="2026-10-05"))
        self.worker = threading.Thread(target=self.server.serve_forever)
        self.worker.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.worker.join()
        self.server.server_close()
        self.store.close()
        self.directory.cleanup()

    def test_pages_assets_and_apis_require_correct_credentials_but_health_does_not(self):
        for route in ("/", "/retention", "/rules", "/ui.js", "/api/overview", "/api/rules", "/api/plan"):
            for authorization in ("", "Basic invalid", "Bearer synthetic", "Basic d3Jvbmc6d3Jvbmc="):
                with self.subTest(route=route, authorization=authorization):
                    request = Request(self.base + route, headers={"Authorization": authorization})
                    with self.assertRaises(HTTPError) as caught:
                        urlopen(request, timeout=5)
                    self.assertEqual(caught.exception.code, 401)
                    self.assertIn("Basic", caught.exception.headers["WWW-Authenticate"])
                    self.assertEqual(caught.exception.headers["Cache-Control"], "no-store")
            if route != "/api/plan":
                request = Request(self.base + route, headers={"Authorization": self.authorization})
                with urlopen(request, timeout=5) as response:
                    self.assertEqual(response.status, 200)
        with urlopen(self.base + "/healthz", timeout=5) as response:
            self.assertEqual(json.load(response), {"status": "ok"})
            self.assertIsNone(response.headers.get("WWW-Authenticate"))
        with patch.dict("os.environ", {"RENDER_GIT_COMMIT": "synthetic-revision"}):
            with urlopen(self.base + "/healthz", timeout=5) as response:
                self.assertEqual(response.headers["X-App-Revision"], "synthetic-revision")

    def test_posts_require_login_and_exact_https_origin_before_reading_or_writing(self):
        payload = {"customer_id": "SYNTHETIC", "event": {"id": "SYNTHETIC-CONTACT", "date": "2026-10-05"}}
        with patch("src.web.record_event") as save:
            for route in ("/api/events", "/api/import"):
                request = Request(self.base + route, data=b"{}")
                with self.assertRaises(HTTPError) as caught:
                    urlopen(request, timeout=5)
                self.assertEqual(caught.exception.code, 401)
                for origin in ("https://other.example.invalid", self.base, "null"):
                    request = Request(self.base + route, data=b"{}", headers={
                        "Authorization": self.authorization, "Origin": origin})
                    with self.assertRaises(HTTPError) as caught:
                        urlopen(request, timeout=5)
                    self.assertEqual(caught.exception.code, 400)
                    self.assertIn("Origine", json.load(caught.exception)["error"])
            save.assert_not_called()
            request = Request(self.base + "/api/events", data=json.dumps(payload).encode(), headers={
                "Authorization": self.authorization, "Origin": "https://retention.example.invalid",
                "Content-Type": "application/json"})
            with urlopen(request, timeout=5) as response:
                self.assertEqual(json.load(response), {"saved": True, "event_id": "SYNTHETIC-CONTACT"})
            self.assertEqual(save.call_args.args[1:], (payload["customer_id"], payload["event"]))

    def test_static_resources_health_and_rejected_login_do_not_open_database(self):
        with patch("src.web.Store", side_effect=AssertionError("Il file statico non deve aprire il database")), \
                patch("src.web.mimetypes.guess_type", return_value=("application/octet-stream", None)):
            for route, content_type in [("/", "text/html"), ("/overview.css", "text/css"),
                                        ("/ui.js", "text/javascript"), ("/overview.js", "text/javascript"),
                                        ("/retention.css", "text/css"), ("/rules.js", "text/javascript")]:
                request = Request(self.base + route, headers={"Authorization": self.authorization})
                with urlopen(request, timeout=5) as response:
                    self.assertEqual(response.status, 200)
                    self.assertEqual(response.headers.get_content_type(), content_type)
                    self.assertEqual(response.headers.get_content_charset(), "utf-8")
                    self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
            self.assertEqual(urlopen(self.base + "/healthz", timeout=5).status, 200)
            for route in ("/", "/overview.css", "/ui.js", "/api/overview"):
                with self.assertRaises(HTTPError) as caught:
                    urlopen(self.base + route, timeout=5)
                self.assertEqual(caught.exception.code, 401)

    def test_api_connection_reuses_schema_initialized_at_server_start(self):
        with patch("src.web.Store", wraps=Store) as connect:
            request = Request(self.base + "/api/overview", headers={"Authorization": self.authorization})
            with urlopen(request, timeout=5) as response:
                self.assertEqual(response.status, 200)
            connect.assert_called_once_with(self.store.database, initialize=False)

    def test_render_environment_sets_binding_database_and_closes_resources(self):
        environment = {"RENDER": "true", "PORT": "10000", "DATABASE_PATH": str(self.store.path),
                       "RRE_USERNAME": "synthetic", "RRE_PASSWORD": "synthetic-password",
                       "RENDER_EXTERNAL_URL": "https://retention.example.invalid/"}
        with patch.dict("os.environ", environment, clear=True), patch("src.web.ThreadingHTTPServer") as server:
            main([])
            self.assertEqual(server.call_args.args[0], ("0.0.0.0", 10000))
            server.return_value.serve_forever.assert_called_once()
            server.return_value.server_close.assert_called_once()

    def test_authenticated_upload_uses_database_directory_and_survives_reopening(self):
        buffer = io.StringIO(newline="")
        writer = csv.DictWriter(buffer, fieldnames=MINIMAL_COLUMNS)
        writer.writeheader()
        writer.writerow({"Name": "#HOSTED-DEMO", "Id": "HOSTED-DEMO",
                         "Created at": "2026-08-01 12:00:00 +0200", "Financial Status": "paid",
                         "Lineitem sku": "CR05272", "Lineitem quantity": "1",
                         "Lineitem fulfillment status": "fulfilled", "Refunded Amount": "0",
                         "Email": "hosted@example.invalid", "Accepts Marketing": "yes"})
        body = ('--hosted\r\nContent-Disposition: form-data; name="files"; filename="synthetic.csv"\r\n'
                'Content-Type: text/csv\r\n\r\n' + buffer.getvalue() + '\r\n--hosted--\r\n').encode()
        request = Request(self.base + "/api/import", data=body, headers={
            "Authorization": self.authorization, "Origin": "https://retention.example.invalid",
            "Content-Type": "multipart/form-data; boundary=hosted"})
        with urlopen(request, timeout=5) as response:
            self.assertEqual(json.load(response), {"imported_files": 1, "active": False})
        exports = list((self.store.path.parent / "uploads").glob("*.csv"))
        self.assertEqual(len(exports), 1)
        with exports[0].open(encoding="utf-8-sig", newline="") as source:
            self.assertEqual(csv.DictReader(source).fieldnames, MINIMAL_COLUMNS)
        reopened = Store(self.store.path)
        try:
            self.assertEqual(len(reopened.load_state()["profiles"]), 1)
            self.assertIsNone(reopened.activation_date())
        finally:
            reopened.close()

    def test_public_demo_startup_uses_only_synthetic_store_without_login(self):
        with patch.dict("os.environ", {"RENDER": "true", "PORT": "10000"}, clear=True), \
                patch("src.web.demo_store") as synthetic, patch("src.web.Store") as real_store, \
                patch("src.web.make_handler", wraps=make_handler) as handler, \
                patch("src.web.ThreadingHTTPServer") as server:
            main(["--demo"])
            synthetic.assert_called_once()
            real_store.assert_not_called()
            self.assertTrue(handler.call_args.kwargs["demo"])
            self.assertIsNone(handler.call_args.kwargs["credentials"])
            self.assertEqual(server.call_args.args[0], ("0.0.0.0", 10000))
            server.return_value.serve_forever.assert_called_once()
            synthetic.return_value.close.assert_called_once()

    def test_remote_startup_rejects_missing_login_or_missing_render_storage(self):
        for environment, arguments in [
            ({"RENDER": "true"}, []),
            ({"RENDER": "true", "DATABASE_PATH": "synthetic.sqlite3"}, []),
            ({"RENDER": "true", "DATABASE_URL": "postgresql://example.invalid/test"}, ["--demo"]),
            ({"DATABASE_PATH": "synthetic.sqlite3"}, ["--demo"]),
            ({"RENDER": "true", "RRE_USERNAME": "synthetic", "RRE_PASSWORD": "password"}, []),
            ({}, ["--host", "0.0.0.0"]),
            ({"RRE_USERNAME": "synthetic"}, []),
            ({"RRE_USERNAME": "bad:name", "RRE_PASSWORD": "password"}, []),
            ({"DATABASE_URL": "postgresql://example.invalid/test", "DATABASE_PATH": "local.sqlite3"}, []),
        ]:
            with self.subTest(environment=list(environment), arguments=arguments), \
                    patch.dict("os.environ", environment, clear=True), \
                    patch("src.web.ThreadingHTTPServer") as server, patch("sys.stderr", io.StringIO()):
                with self.assertRaises(SystemExit) as caught:
                    main(arguments)
                self.assertEqual(caught.exception.code, 2)
                server.assert_not_called()

    def test_render_postgres_url_is_passed_to_store_without_becoming_a_file_path(self):
        environment = {"RENDER": "true", "PORT": "10000",
                       "DATABASE_URL": "postgresql://synthetic:password@example.invalid/test",
                       "RRE_USERNAME": "synthetic", "RRE_PASSWORD": "synthetic-password"}
        with patch.dict("os.environ", environment, clear=True), patch("src.web.Store") as store, \
                patch("src.web.ThreadingHTTPServer") as server:
            main([])
            store.assert_called_once_with(environment["DATABASE_URL"])
            self.assertEqual(server.call_args.args[0], ("0.0.0.0", 10000))


if __name__ == "__main__":
    unittest.main()
