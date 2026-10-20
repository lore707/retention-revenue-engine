"""Casi sintetici del primo percorso commerciale; nessun dato cliente reale."""

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from src.engine import _promotions_on, evaluate, evaluate_portfolio, format_operator_view


RULE = "magnetic_concentrator_completion"
SE_LITE_RULE = "se_lite_diffuser_completion"
MINI_WALL_MOUNT_RULE = "mini_wall_mount_completion"
NEO_WALL_MOUNT_RULE = "neo_wall_mount_completion"
BRUSH_RULE = "brush_complement"
AUTOCURL_RULE = "autocurl_cross_sell"
POUCH_RULE = "storage_pouch_cross_sell"
MINI_TRAVEL_RULE = "mini_travel_cross_sell"
HAIR_TO_SHAVERS_RULE = "hair_dryer_to_shavers_category_expansion"
HAIR_TO_WAVE_RULE = "hair_dryer_to_wave_pro_category_expansion"
TOOTHBRUSH_TO_NEO_RULE = "toothbrush_to_neo_category_expansion"
P3_CASE_RULE = "p3_travel_case_cross_sell"
P3_HEAD_RULE = "p3_pro_head_replenishment"
WAVE_HEADS_RULE = "wave_pro_heads_replenishment"
WAVE_REPLACEMENT_RULE = "wave_legacy_to_wave_pro_replacement"


def purchase(record_id="LINE_1", sku="CR05272", day="2026-08-24", validity="valid",
             order_id=None):
    record = {"id": record_id, "sku": sku, "date": day, "validity": validity}
    if order_id is not None:
        record["order_id"] = order_id
    return record


def customer(*purchases):
    return {"customer_id": "SYNTHETIC_001", "history_complete": True,
            "contact_history_complete": True, "contact_channel": "email",
            "marketing_consent": {"email": {"status": "subscribed"}},
            "purchases": list(purchases), "events": []}


def event(record_id, kind="contact", day="2026-09-08", rule_id=RULE):
    return {"id": record_id, "type": kind, "date": day, "rule_id": rule_id}


def plan_event(record_id, kind, day, rule_id, plan_key, included_rule_ids,
               cycle_reference_purchase_id=None):
    primary_key = ["SYNTHETIC_001", rule_id]
    included_keys = [["SYNTHETIC_001", included] for included in included_rule_ids]
    if cycle_reference_purchase_id:
        primary_key.append(cycle_reference_purchase_id)
        included_keys = [
            key + [cycle_reference_purchase_id] if key[1] == rule_id else key
            for key in included_keys
        ]
    record = {
        **event(record_id, kind, day, rule_id),
        "plan_key": plan_key,
        "primary_opportunity_key": primary_key,
        "included_opportunity_keys": included_keys,
    }
    if cycle_reference_purchase_id:
        record["cycle_reference_purchase_id"] = cycle_reference_purchase_id
    return record


class EngineTests(unittest.TestCase):
    def test_shared_commercial_definitions_preserve_decisions_without_mutation(self):
        root = Path(__file__).resolve().parents[1] / "src"
        context = {name: json.loads((root / filename).read_text(encoding="utf-8"))
                   for name, filename in [("catalog", "catalog.json"),
                                          ("definitions", "rules.json"),
                                          ("promotions", "promotions.json")]}
        original = copy.deepcopy(context)
        snapshots = [
            customer(purchase(day="2026-08-01")),
            customer(purchase(day="2026-08-01"), purchase("OWNED", "CP96308", "2026-08-02")),
            customer(purchase(day="2026-10-01")),
        ]
        blocked = customer(purchase(day="2026-08-01"))
        blocked["marketing_consent"]["email"]["status"] = "unsubscribed"
        snapshots.append(blocked)
        for snapshot in snapshots:
            with self.subTest(purchases=len(snapshot["purchases"]),
                              consent=snapshot["marketing_consent"]["email"]["status"]):
                expected = evaluate_portfolio(snapshot, "2026-10-12")
                self.assertEqual(evaluate_portfolio(snapshot, "2026-10-12", **context), expected)
                self.assertEqual(evaluate_portfolio(snapshot, "2026-10-12", **context), expected)
                self.assertEqual(context, original)
        self.assertEqual(evaluate_portfolio(snapshots[0], "2026-10-12", **context)
                         ["portfolio_status"], "contact_review")
        self.assertEqual(evaluate_portfolio(blocked, "2026-10-12", **context)
                         ["portfolio_status"], "blocked_consent")

    def test_every_rule_allows_a_proactive_offer_without_prior_interest(self):
        definitions = json.loads(
            (Path(__file__).resolve().parents[1] / "src/rules.json").read_text(encoding="utf-8")
        )
        self.assertFalse(definitions["shared_policies"]["customer_interest_required"])
        cases = {
            RULE: "CR05272",
            SE_LITE_RULE: "CQ62986",
            MINI_WALL_MOUNT_RULE: "CP34448",
            NEO_WALL_MOUNT_RULE: "CR05272",
            AUTOCURL_RULE: "CR05272",
            MINI_TRAVEL_RULE: "CR05272",
            HAIR_TO_WAVE_RULE: "CR05272",
            HAIR_TO_SHAVERS_RULE: "CR05272",
            TOOTHBRUSH_TO_NEO_RULE: "CR95008",
            POUCH_RULE: "CR05272",
            BRUSH_RULE: "CR05272",
            P3_CASE_RULE: "1ER91-P-XX-BL-002",
            P3_HEAD_RULE: "CP96308",
            WAVE_REPLACEMENT_RULE: "CL97510",
            WAVE_HEADS_RULE: "CR95008",
        }
        self.assertEqual(set(cases), {rule["id"] for rule in definitions["rules"]})
        for rule in definitions["rules"]:
            with self.subTest(rule=rule["id"]):
                self.assertNotIn("customer_interest_required", rule)
                snapshot = customer(purchase(sku=cases[rule["id"]], day="2025-01-01"))
                original = copy.deepcopy(snapshot)
                result = evaluate(snapshot, "2026-12-15", rule["id"])
                self.assertEqual(result["status"], "first_contact_review")
                self.assertFalse(any("interesse" in check for check in result["operator_checks"]))
                self.assertEqual(result, evaluate(snapshot, "2026-12-15", rule["id"]))
                self.assertEqual(snapshot, original)
                snapshot["marketing_consent"]["email"]["status"] = "unsubscribed"
                self.assertEqual(evaluate(snapshot, "2026-12-15", rule["id"])["status"],
                                 "blocked_consent")

    def test_accessory_presentation_is_one_uniform_plan_from_engine(self):
        snapshot = customer(purchase(sku="CR05186", day="2026-09-17", order_id="DEMO_ORDER"))
        original = copy.deepcopy(snapshot)
        result = evaluate_portfolio(snapshot, "2026-10-05")
        presentation = result["primary_contact_plan"]["presentation"]
        self.assertEqual(presentation["layout"], "uniform_product_list")
        self.assertEqual(presentation["eligible_from_date"], "2026-10-02")
        self.assertEqual(presentation["minimum_days"], 15)
        self.assertEqual(presentation["source_purchases"][0]["configuration"], "2 Ugelli")
        self.assertEqual(presentation["source_purchases"][0]["elapsed_days"], 18)
        self.assertEqual([item["rule_id"] for item in presentation["products"]],
                         [RULE, NEO_WALL_MOUNT_RULE, POUCH_RULE, BRUSH_RULE])
        self.assertEqual([item["nominal_value_minor"] for item in presentation["products"]],
                         [2499, 1799, 2999, 1299])
        self.assertEqual(presentation["products"][0]["role"], "primary")
        self.assertIn("mirata", presentation["primary_selection_reason"])
        self.assertIsNone(presentation["purchase_probability"])
        row = next(row for row in result["operator_timeline"]
                   if row["plan_key"] == result["primary_contact_plan"]["plan_key"])
        self.assertEqual(row["presentation"], presentation)
        self.assertEqual(snapshot, original)
        self.assertEqual(result, evaluate_portfolio(snapshot, "2026-10-05"))

    def test_accessory_presentation_excludes_owned_and_included_products(self):
        snapshot = customer(purchase(sku="CQ15841", day="2026-09-17", order_id="DEMO_ORDER"),
                            purchase("POUCH", "CL51809", "2026-09-18"))
        presentation = evaluate_portfolio(snapshot, "2026-10-05")["primary_contact_plan"]["presentation"]
        self.assertEqual([item["rule_id"] for item in presentation["products"]],
                         [NEO_WALL_MOUNT_RULE, BRUSH_RULE])
        self.assertEqual(presentation["source_purchases"][0]["configuration"], "3 Ugelli")
        self.assertEqual(presentation["products"][0]["role"], "primary")

    def test_november_december_campaign_windows_prices_and_catalog_mapping(self):
        expected = {
            **dict.fromkeys(("CQ15839", "CQ15841", "CQ15840"), 11399),
            **dict.fromkeys(("CR68941", "CR68943", "CR68942"), 13599),
            **dict.fromkeys(("CP96308", "CP96436"), 14999),
            **dict.fromkeys(("CR95008", "CR95009", "CR95024"), 7999),
            **dict.fromkeys(("CR95017", "CR95041"), 9499),
            "CR95016": 10999,
            **dict.fromkeys(("1ER91-P-XX-BL-002", "1ER91-P-XX-WH-002"), 12999),
            **dict.fromkeys(("1HD20-S-EU-PU-001", "1HD20-S-EU-WH-001",
                              "1HD20-S-EU-PK-001"), 5499),
        }
        catalog = json.loads((Path(__file__).resolve().parents[1] / "src/catalog.json")
                             .read_text(encoding="utf-8"))
        sellable_skus = {variant["sku"] for product in catalog["products"]
                         for variant in product["variants"]
                         if variant.get("commercial_status") != "historical_only"}
        for day in ("2026-11-19", "2026-11-30", "2026-12-12", "2026-12-25"):
            with self.subTest(day=day):
                version, active = _promotions_on(day)
                self.assertEqual(version, 3)
                self.assertEqual({sku: entry["price_minor"] for sku, entry in active.items()}, expected)
                self.assertTrue({"1HC51-P-EU-BL-001", "1HC51-P-EU-WH-002"}.isdisjoint(active))
                self.assertTrue(set(active) <= sellable_skus)
                self.assertTrue(all(entry["currency"] == "EUR" and entry["status"] == "planned"
                                    for entry in active.values()))
        for day in ("2026-11-18", "2026-12-01", "2026-12-11", "2026-12-26"):
            with self.subTest(day=day):
                self.assertEqual(_promotions_on(day)[1], {})

    def test_october_neo_promotion_applies_only_to_eligible_variants_and_dates(self):
        snapshot = customer(purchase("WAVE", "CR95008", "2026-06-01"))
        before = evaluate_portfolio(snapshot, "2026-09-30")
        during = evaluate_portfolio(snapshot, "2026-10-01")
        after = evaluate_portfolio(snapshot, "2026-10-08")
        def neo_plan(portfolio):
            return next(plan for plan in [portfolio["primary_contact_plan"],
                                          *portfolio["queued_contact_plans"]]
                        if plan["primary_opportunity"]["rule_id"] == TOOTHBRUSH_TO_NEO_RULE)
        self.assertFalse(neo_plan(before)["primary_opportunity"]["promotion_active"])
        promoted = neo_plan(during)["primary_opportunity"]
        self.assertTrue(promoted["promotion_active"])
        self.assertEqual(promoted["nominal_value_minor"], 12499)
        self.assertEqual(promoted["target_sku"], "CQ15839")
        self.assertEqual({option["sku"] for option in promoted["target_options"] if "promotion" in option},
                         {"CQ15839", "CQ15841", "CQ15840"})
        self.assertIn("124.99 EUR", format_operator_view(during))
        self.assertFalse(neo_plan(after)["primary_opportunity"]["promotion_active"])
        self.assertEqual(neo_plan(after)["primary_opportunity"]["nominal_value_minor"], 13499)
        snapshot["purchases"].append(purchase("OWNED", "CR05272", "2026-07-01"))
        excluded = evaluate_portfolio(snapshot, "2026-10-01")
        self.assertFalse(any(plan["primary_opportunity"]["rule_id"] == TOOTHBRUSH_TO_NEO_RULE
                             for plan in [excluded["primary_contact_plan"],
                                          *excluded["queued_contact_plans"]] if plan))

    def test_october_shaver_and_wave_promotions_preserve_category_exclusions(self):
        snapshot = customer(purchase(day="2026-06-01", order_id="HAIR_ORDER"))
        result = evaluate_portfolio(snapshot, "2026-10-12")
        expansion = next(plan for plan in [result["primary_contact_plan"],
                                         *result["queued_contact_plans"]]
                         if plan["commercial_track"] == "category_expansion")
        shavers = expansion["primary_opportunity"]
        self.assertEqual(shavers["rule_id"], HAIR_TO_SHAVERS_RULE)
        self.assertEqual(shavers["nominal_value_minor"], 13999)
        self.assertEqual({option["promotion"]["price_minor"]
                          for option in shavers["target_options"]}, {16999, 13999})
        wave = expansion["secondary_opportunities"][0]
        self.assertEqual(wave["rule_id"], HAIR_TO_WAVE_RULE)
        self.assertEqual({option["promotion"]["price_minor"]
                          for option in wave["target_options"]}, {8499, 9999, 11899})
        snapshot["purchases"].append(purchase("OWNED", "CP96308", "2026-07-01"))
        excluded = evaluate_portfolio(snapshot, "2026-10-12")
        remaining = next(plan for plan in [excluded["primary_contact_plan"],
                                         *excluded["queued_contact_plans"]]
                         if plan["commercial_track"] == "category_expansion")
        self.assertEqual(remaining["primary_opportunity"]["rule_id"], HAIR_TO_WAVE_RULE)

    def test_mature_replenishment_beats_promoted_expansion_but_immature_does_not(self):
        snapshot = customer(
            purchase("NEO", "CR05272", "2026-01-01", order_id="NEO"),
            purchase("CONCENTRATOR", "CP34473", "2026-01-01"),
            purchase("MOUNT", "30101-000092", "2026-01-01"),
            purchase("POUCH", "CL51809", "2026-01-01"),
            purchase("BRUSH", "30101-000041", "2026-01-01"),
            purchase("WAVE", "CR95008", "2026-05-16", order_id="WAVE"))
        before = evaluate_portfolio(snapshot, "2026-10-12")
        self.assertEqual(before["primary_contact_plan"]["primary_opportunity"]["rule_id"], HAIR_TO_SHAVERS_RULE)
        mature = evaluate_portfolio(snapshot, "2026-10-13")
        self.assertEqual(mature["primary_contact_plan"]["primary_opportunity"]["rule_id"], WAVE_HEADS_RULE)
        self.assertEqual(mature, evaluate_portfolio(snapshot, "2026-10-13"))
        key = before["primary_contact_plan"]["plan_key"]
        snapshot["events"] = [plan_event("STARTED", "contact", "2026-10-12", HAIR_TO_SHAVERS_RULE,
                              key, [HAIR_TO_SHAVERS_RULE])]
        locked = evaluate_portfolio(snapshot, "2026-10-13")
        self.assertEqual(locked["primary_contact_plan"]["plan_key"], key)
        self.assertEqual(locked["portfolio_status"], "deferred")

    def test_promotion_changes_priority_only_inside_its_window(self):
        snapshot = customer(
            purchase(day="2026-06-01", order_id="HAIR_ORDER"),
            purchase("POUCH", "CL51809", "2026-06-10"),
            purchase("CONCENTRATOR", "CP34473", "2026-06-10"),
            purchase("MOUNT", "30101-000092", "2026-06-10"),
            purchase("BRUSH", "30101-000041", "2026-06-10"),
            purchase("SHAVER", "CP96308", "2026-06-10"),
        )
        self.assertEqual(evaluate_portfolio(snapshot, "2026-10-11")
                         ["primary_contact_plan"]["primary_opportunity"]["rule_id"], AUTOCURL_RULE)
        promoted = evaluate_portfolio(snapshot, "2026-10-12")
        self.assertEqual(promoted["primary_contact_plan"]["primary_opportunity"]["rule_id"],
                         HAIR_TO_WAVE_RULE)
        self.assertEqual(promoted["primary_contact_plan"]["primary_opportunity"]["nominal_value_minor"],
                         8499)
        self.assertEqual(evaluate_portfolio(snapshot, "2026-10-19")
                         ["primary_contact_plan"]["primary_opportunity"]["rule_id"], AUTOCURL_RULE)

    def test_targeted_precedes_promoted_test_before_during_and_after_promotion(self):
        snapshot = customer(purchase(day="2026-08-01", order_id="ORDER_NEO"))
        original = copy.deepcopy(snapshot)
        self.assertEqual(evaluate_portfolio(snapshot, "2026-10-11")
                         ["primary_contact_plan"]["primary_opportunity"]["rule_id"], RULE)
        result = evaluate_portfolio(snapshot, "2026-10-12")
        plan = result["primary_contact_plan"]
        self.assertEqual(plan["primary_opportunity"]["rule_id"], RULE)
        self.assertEqual(result["portfolio_status"], "contact_review")
        self.assertEqual(plan["blocking_plan_keys"], [])
        self.assertTrue(any(queued["commercial_track"] == "category_expansion"
                            for queued in result["queued_contact_plans"]))
        self.assertEqual(evaluate_portfolio(snapshot, "2026-10-19")
                         ["primary_contact_plan"]["primary_opportunity"]["rule_id"], RULE)
        self.assertEqual(result, evaluate_portfolio(snapshot, "2026-10-12"))
        self.assertEqual(snapshot, original)

    def test_promotion_does_not_advance_day_75_or_offer_owned_categories(self):
        snapshot = customer(purchase(day="2026-07-30", order_id="ORDER_NEO"),
            purchase("CONCENTRATOR", "CP34473", "2026-08-29"),
            purchase("MOUNT", "30101-000092", "2026-08-29"))
        self.assertEqual(evaluate_portfolio(snapshot, "2026-10-12")
                         ["primary_contact_plan"]["primary_opportunity"]["rule_id"], POUCH_RULE)
        self.assertEqual(evaluate_portfolio(snapshot, "2026-10-13")
                         ["primary_contact_plan"]["primary_opportunity"]["rule_id"],
                         HAIR_TO_SHAVERS_RULE)
        snapshot["purchases"].extend([
            purchase("SHAVER", "CP96308", "2026-09-01"),
            purchase("WAVE", "CR95008", "2026-09-01"),
        ])
        result = evaluate_portfolio(snapshot, "2026-10-13")
        self.assertEqual(result["primary_contact_plan"]["primary_opportunity"]["rule_id"],
                         POUCH_RULE)
        self.assertFalse(any(plan["primary_opportunity"]["promotion_active"]
                             for plan in result["queued_contact_plans"]))

    def test_promotion_preserves_contacted_plan_reply_and_contact_gap(self):
        snapshot = customer(purchase(day="2026-08-01", order_id="ORDER_NEO"))
        key = ["ORDER_NEO", "hair_care", "2026-08-16"]
        snapshot["events"] = [plan_event("CONTACT", "contact", "2026-10-07", POUCH_RULE,
                             key, [POUCH_RULE, RULE, NEO_WALL_MOUNT_RULE, BRUSH_RULE])]
        result = evaluate_portfolio(snapshot, "2026-10-12")
        self.assertEqual(result["primary_contact_plan"]["primary_opportunity"]["rule_id"],
                         POUCH_RULE)
        self.assertEqual(result["portfolio_status"], "deferred")
        self.assertEqual(result["next_contact_date"], "2026-10-22")
        expansion = next(plan for plan in result["queued_contact_plans"]
                         if plan["commercial_track"] == "category_expansion")
        self.assertEqual(expansion["raw_status"], "deferred")
        snapshot["events"].append({**event("REPLY", "reply", "2026-10-08", POUCH_RULE),
                                   "plan_key": key})
        result = evaluate_portfolio(snapshot, "2026-10-12")
        self.assertEqual(result["portfolio_status"], "operator_response")
        self.assertEqual(result["primary_contact_plan"]["plan_key"], key)

    def test_travel_window_precedes_higher_price_only_while_eligible(self):
        snapshot = customer(
            purchase(day="2026-01-01", order_id="ORDER_NEO"),
            purchase("POUCH", "CL51809", "2026-01-10"),
            purchase("CONCENTRATOR", "CP34473", "2026-01-10"),
            purchase("MOUNT", "30101-000092", "2026-01-10"),
            purchase("BRUSH", "30101-000041", "2026-01-10"),
        )
        self.assertEqual(evaluate_portfolio(snapshot, "2026-05-14")
                         ["primary_contact_plan"]["primary_opportunity"]["rule_id"],
                         HAIR_TO_SHAVERS_RULE)
        result = evaluate_portfolio(snapshot, "2026-05-15")
        self.assertEqual(result["primary_contact_plan"]["primary_opportunity"]["rule_id"],
                         MINI_TRAVEL_RULE)
        self.assertIn("finestra viaggio", result["primary_contact_plan"]["plan_reason"])
        self.assertEqual(evaluate_portfolio(snapshot, "2026-09-06")
                         ["primary_contact_plan"]["primary_opportunity"]["rule_id"],
                         HAIR_TO_SHAVERS_RULE)
        self.assertEqual(evaluate_portfolio(snapshot, "2026-12-15")
                         ["primary_contact_plan"]["primary_opportunity"]["rule_id"],
                         HAIR_TO_SHAVERS_RULE)
        snapshot["purchases"].append(purchase("MINI", "CP34448", "2026-05-01"))
        result = evaluate_portfolio(snapshot, "2026-05-15")
        self.assertEqual(result["primary_contact_plan"]["primary_opportunity"]["rule_id"],
                         HAIR_TO_SHAVERS_RULE)

    def test_neo_accessories_are_grouped_without_autocurl(self):
        for sku, expected in (("CR05272", [NEO_WALL_MOUNT_RULE, POUCH_RULE, BRUSH_RULE]),
                              ("CQ15839", [POUCH_RULE, BRUSH_RULE])):
            snapshot = customer(purchase(sku=sku, day="2026-01-01", order_id="ORDER_NEO"))
            result = evaluate_portfolio(snapshot, "2026-01-16")
            plan = result["primary_contact_plan"]
            self.assertEqual(plan["plan_key"], ["ORDER_NEO", "hair_care", "2026-01-16"])
            self.assertEqual(plan["primary_opportunity"]["rule_id"], RULE if sku == "CR05272" else NEO_WALL_MOUNT_RULE)
            self.assertEqual([item["rule_id"] for item in plan["secondary_opportunities"]], expected)
            day_45 = next(p for p in result["queued_contact_plans"]
                          if p["primary_opportunity"]["rule_id"] == AUTOCURL_RULE)
            self.assertEqual(day_45["raw_status"], "waiting_for_plan")
            self.assertEqual(day_45["eligible_from_date"], "2026-02-15")
            self.assertEqual({key[1] for key in day_45["included_opportunity_keys"]},
                             {AUTOCURL_RULE})
            self.assertIsNone(day_45["plan_next_contact_date"])

    def accessory_snapshot(self):
        snapshot = customer(purchase(day="2026-01-01", order_id="ORDER_NEO"))
        key = ["ORDER_NEO", "hair_care", "2026-01-16"]
        snapshot["events"] = [plan_event("FIRST", "contact", "2026-01-16", POUCH_RULE,
                             key, [POUCH_RULE, RULE, NEO_WALL_MOUNT_RULE, BRUSH_RULE])]
        return snapshot, key

    def test_day_45_plan_waits_for_accessories_and_second_contact_cooldown(self):
        snapshot, key = self.accessory_snapshot()
        open_plan = evaluate_portfolio(snapshot, "2026-01-31")
        self.assertEqual(open_plan["primary_contact_plan"]["primary_opportunity"]["rule_id"], POUCH_RULE)
        snapshot["events"].append(plan_event("SECOND", "contact", "2026-01-31", POUCH_RULE,
                                 key, [POUCH_RULE, RULE, NEO_WALL_MOUNT_RULE, BRUSH_RULE]))
        before = evaluate_portfolio(snapshot, "2026-02-14")
        self.assertEqual(before["primary_contact_plan"]["primary_opportunity"]["rule_id"],
                         AUTOCURL_RULE)
        self.assertEqual(before["portfolio_status"], "deferred")
        self.assertEqual(before["next_contact_date"], "2026-02-15")
        ready = evaluate_portfolio(snapshot, "2026-02-15")
        self.assertEqual(ready["portfolio_status"], "contact_review")
        self.assertEqual({key[1] for key in ready["primary_contact_plan"]["included_opportunity_keys"]},
                         {AUTOCURL_RULE})
        self.assertEqual({item["rule_id"] for item in ready["suppressed_opportunities"]},
                         {RULE, NEO_WALL_MOUNT_RULE, BRUSH_RULE})

    def test_purchase_of_presented_secondary_closes_shared_contact_plan(self):
        snapshot, key = self.accessory_snapshot()
        snapshot["purchases"].append(purchase("BRUSH", "30101-000041", "2026-01-20"))
        result = evaluate_portfolio(snapshot, "2026-02-15")
        self.assertEqual(result["primary_contact_plan"]["primary_opportunity"]["rule_id"],
                         AUTOCURL_RULE)
        self.assertEqual({item["rule_id"] for item in result["suppressed_opportunities"]},
                         {POUCH_RULE, RULE, NEO_WALL_MOUNT_RULE})

    def test_operator_response_keeps_other_proposals_queued_until_resolved(self):
        snapshot, key = self.accessory_snapshot()
        snapshot["events"].append({**event("REPLY", "reply", "2026-01-20", POUCH_RULE), "plan_key": key})
        result = evaluate_portfolio(snapshot, "2026-04-01")
        self.assertEqual(result["portfolio_status"], "operator_response")
        self.assertEqual(result["primary_contact_plan"]["primary_opportunity"]["rule_id"], POUCH_RULE)
        snapshot["events"].append({"id": "CLOSE", "type": "conversation_closed", "date": "2026-04-02", "plan_key": key})
        result = evaluate_portfolio(snapshot, "2026-04-02")
        self.assertEqual(result["portfolio_status"], "contact_review")
        self.assertEqual(result["primary_contact_plan"]["contact_count"], 1)

    def test_plan_rejection_releases_day_45_plan_after_contact_gap(self):
        snapshot, key = self.accessory_snapshot()
        snapshot["events"].append({"id": "NO", "type": "plan_rejection", "date": "2026-01-17", "plan_key": key})
        result = evaluate_portfolio(snapshot, "2026-02-14")
        self.assertEqual(result["primary_contact_plan"]["primary_opportunity"]["rule_id"],
                         AUTOCURL_RULE)
        self.assertEqual(result["next_contact_date"], "2026-02-15")
        self.assertEqual(len(result["suppressed_opportunities"]), 4)

    def test_product_rejection_does_not_close_other_accessories(self):
        snapshot, key = self.accessory_snapshot()
        snapshot["events"].append({"id": "NO_POUCH", "type": "product_rejection", "date": "2026-01-20",
                                   "plan_key": key, "product_key": "laifen_storage_pouch"})
        result = evaluate_portfolio(snapshot, "2026-01-31")
        plan = result["primary_contact_plan"]
        self.assertEqual(result["portfolio_status"], "operator_response")
        self.assertEqual(plan["primary_opportunity"]["rule_id"], RULE)
        self.assertEqual(plan["contact_count"], 1)
        self.assertEqual(len(plan["secondary_opportunities"]), 2)
        self.assertEqual(result["suppressed_opportunities"][0]["coordination_status"], "product_rejected")

    def test_consent_is_required_for_every_rule_and_selected_channel(self):
        snapshot = customer(purchase(day="2025-01-01"),
                            purchase("WAVE", "CR95008", "2025-01-01"),
                            purchase("P3", "CP96308", "2025-01-01"))
        rules = json.loads((Path(__file__).resolve().parents[1] / "src/rules.json").read_text(encoding="utf-8"))["rules"]
        for status in (None, "unknown", "unsubscribed", "pending", "revoked"):
            with self.subTest(status=status):
                snapshot["marketing_consent"] = {} if status is None else {"email": {"status": status}}
                result = evaluate_portfolio(snapshot, "2026-09-23")
                self.assertEqual(result["portfolio_status"], "blocked_consent")
                self.assertIsNone(result["next_contact_date"])
                self.assertTrue(all(row["state"] == "blocked_consent" and row["next_contact_date"] is None
                                    for row in result["operator_timeline"]))
                for rule in rules:
                    outcome = evaluate(snapshot, "2026-09-23", rule["id"])
                    self.assertNotIn(outcome["status"], {"first_contact_review", "second_contact_review"})
        snapshot["marketing_consent"] = {"email": {"status": "subscribed"}}
        self.assertEqual(evaluate_portfolio(snapshot, "2026-09-23")["portfolio_status"], "contact_review")
        snapshot["contact_channel"] = "sms"
        self.assertEqual(evaluate_portfolio(snapshot, "2026-09-23")["portfolio_status"], "blocked_consent")
        snapshot["marketing_consent"]["sms"] = {"status": "subscribed"}
        self.assertEqual(evaluate_portfolio(snapshot, "2026-09-23")["portfolio_status"], "contact_review")
        snapshot["do_not_contact"] = True
        self.assertEqual(evaluate_portfolio(snapshot, "2026-09-23")["portfolio_status"], "blocked_consent")

    def test_revocation_blocks_follow_up_already_scheduled(self):
        snapshot, key = self.accessory_snapshot()
        self.assertEqual(evaluate_portfolio(snapshot, "2026-01-31")["portfolio_status"], "contact_review")
        snapshot["marketing_consent"]["email"]["status"] = "unsubscribed"
        blocked = evaluate_portfolio(snapshot, "2026-01-31")
        self.assertEqual(blocked["primary_contact_plan"]["primary_opportunity"]["status"], "blocked_consent")
        self.assertIsNone(blocked["primary_contact_plan"]["plan_next_contact_date"])

    def expansion_snapshot(self):
        return customer(purchase(day="2026-01-01", order_id="ORDER_NEO"),
                        purchase("CONCENTRATOR", "CP34473", "2026-01-10"),
                        purchase("POUCH", "CL51809", "2026-01-10"),
                        purchase("MOUNT", "30101-000092", "2026-01-10"),
                        purchase("BRUSH", "30101-000041", "2026-01-10"))

    def expansion_contact(self, snapshot):
        key = ["ORDER_NEO", "category_expansion", "2026-03-17"]
        snapshot["events"].append(plan_event("EXPANSION", "contact", "2026-04-01", HAIR_TO_SHAVERS_RULE,
                                            key, [HAIR_TO_SHAVERS_RULE, HAIR_TO_WAVE_RULE]))
        return key

    def test_day_45_autocurl_and_day_75_expansions_are_separate(self):
        snapshot = self.expansion_snapshot()
        day_45 = evaluate_portfolio(snapshot, "2026-02-15")
        auto = day_45["primary_contact_plan"]
        self.assertEqual(auto["primary_opportunity"]["rule_id"], AUTOCURL_RULE)
        self.assertEqual(auto["primary_opportunity"]["commercial_category"], "test")
        self.assertEqual(auto["secondary_opportunities"], [])
        self.assertEqual(auto["eligible_from_date"], "2026-02-15")
        for rule in (HAIR_TO_SHAVERS_RULE, HAIR_TO_WAVE_RULE):
            self.assertEqual(evaluate(snapshot, "2026-03-16", rule)["status"], "deferred")
            self.assertEqual(evaluate(snapshot, "2026-03-17", rule)["status"], "first_contact_review")
        result = evaluate_portfolio(snapshot, "2026-03-17")
        plan = result["primary_contact_plan"]
        self.assertEqual(plan["eligible_from_date"], "2026-03-17")
        self.assertEqual(plan["primary_opportunity"]["rule_id"], HAIR_TO_SHAVERS_RULE)
        self.assertEqual(plan["primary_opportunity"]["nominal_value_minor"], 16999)
        self.assertEqual([o["product_key"] for o in plan["primary_opportunity"]["target_options"]],
                         ["laifen_p3_pro", "laifen_p3_pro", "laifen_p3", "laifen_p3"])
        self.assertEqual({o["rule_id"] for o in plan["secondary_opportunities"]}, {HAIR_TO_WAVE_RULE})
        self.assertTrue(any(p["primary_opportunity"]["rule_id"] == AUTOCURL_RULE
                            for p in result["queued_contact_plans"]))
        self.assertEqual(result, evaluate_portfolio(snapshot, "2026-03-17"))
        for owned, expected in (("CR95008", {HAIR_TO_SHAVERS_RULE}),
                                ("CL97510", {HAIR_TO_SHAVERS_RULE}),
                                ("CP96308", {HAIR_TO_WAVE_RULE}),
                                ("1ER91-P-XX-BL-002", {HAIR_TO_WAVE_RULE})):
            with self.subTest(owned=owned):
                current = copy.deepcopy(snapshot)
                current["purchases"].append(purchase("OWNED", owned, "2026-02-01"))
                portfolio = evaluate_portfolio(current, "2026-03-17")
                expansion = next(p for p in [portfolio["primary_contact_plan"], *portfolio["queued_contact_plans"]]
                                 if p["eligible_from_date"] == "2026-03-17")
                self.assertEqual({k[1] for k in expansion["included_opportunity_keys"]}, expected)
        snapshot["purchases"].extend([purchase("WAVE", "CR95008", "2026-02-01"),
                                      purchase("P3", "CP96308", "2026-02-01")])
        portfolio = evaluate_portfolio(snapshot, "2026-03-17")
        self.assertFalse(any(p["eligible_from_date"] == "2026-03-17"
                             for p in [portfolio["primary_contact_plan"], *portfolio["queued_contact_plans"]]))
        self.assertEqual(portfolio["primary_contact_plan"]["primary_opportunity"]["rule_id"], AUTOCURL_RULE)

    def test_autocurl_closure_does_not_close_expansion_and_global_gap_still_applies(self):
        snapshot = self.expansion_snapshot()
        auto = evaluate_portfolio(snapshot, "2026-03-12")["primary_contact_plan"]
        self.assertEqual(auto["primary_opportunity"]["rule_id"], AUTOCURL_RULE)
        snapshot["events"].append(plan_event("AUTO", "contact", "2026-03-12", AUTOCURL_RULE,
                                             auto["plan_key"], [AUTOCURL_RULE]))
        snapshot["events"].append({"id": "CLOSE_AUTO", "type": "plan_rejection", "date": "2026-03-13",
                                   "plan_key": auto["plan_key"]})
        blocked = evaluate_portfolio(snapshot, "2026-03-17")
        self.assertEqual(blocked["primary_contact_plan"]["primary_opportunity"]["rule_id"], HAIR_TO_SHAVERS_RULE)
        self.assertEqual(blocked["portfolio_status"], "deferred")
        self.assertEqual(blocked["next_contact_date"], "2026-03-27")
        ready = evaluate_portfolio(snapshot, "2026-03-27")
        self.assertEqual(ready["portfolio_status"], "contact_review")
        self.assertEqual(ready["primary_contact_plan"]["contact_count"], 0)
        self.assertEqual({key[1] for key in ready["primary_contact_plan"]["included_opportunity_keys"]},
                         {HAIR_TO_SHAVERS_RULE, HAIR_TO_WAVE_RULE})
        waiting = evaluate_portfolio(customer(purchase(day="2026-01-01", order_id="ORDER")), "2026-03-17")
        plans = [waiting["primary_contact_plan"], *waiting["queued_contact_plans"]]
        auto = next(p for p in plans if p["primary_opportunity"]["rule_id"] == AUTOCURL_RULE)
        expansion = next(p for p in plans if p["eligible_from_date"] == "2026-03-17")
        self.assertEqual(auto["raw_status"], "waiting_for_plan")
        self.assertEqual(expansion["raw_status"], "first_contact_review")

    def test_shaver_purchase_closes_combined_plan_without_wave_sequence(self):
        for sku in ("CP96308", "CP96436", "1ER91-P-XX-BL-002", "1ER91-P-XX-WH-002", "CR95008"):
            snapshot = self.expansion_snapshot()
            key = self.expansion_contact(snapshot)
            snapshot["purchases"].append(purchase("BOUGHT", sku, "2026-04-05"))
            result = evaluate_portfolio(snapshot, "2026-04-16")
            self.assertFalse(any(row["plan_key"] == key for row in result["operator_timeline"]))
            self.assertTrue(any(item["rule_id"] in {HAIR_TO_WAVE_RULE, HAIR_TO_SHAVERS_RULE}
                                for item in result["suppressed_opportunities"]))

    def test_product_interest_focuses_same_plan_without_resetting_contacts(self):
        snapshot = self.expansion_snapshot()
        key = self.expansion_contact(snapshot)
        snapshot["events"].append({"id": "INTEREST", "type": "product_interest", "date": "2026-04-02",
                                   "plan_key": key, "product_key": "laifen_wave_pro"})
        result = evaluate_portfolio(snapshot, "2026-04-16")
        plan = result["primary_contact_plan"]
        self.assertEqual(result["portfolio_status"], "operator_response")
        self.assertEqual(plan["primary_opportunity"]["rule_id"], HAIR_TO_WAVE_RULE)
        self.assertEqual(plan["contact_count"], 1)
        self.assertEqual(plan["secondary_opportunities"], [])
        snapshot["events"].append({"id": "RESOLVED", "type": "conversation_closed", "date": "2026-04-17", "plan_key": key})
        plan = evaluate_portfolio(snapshot, "2026-04-17")["primary_contact_plan"]
        self.assertEqual(plan["raw_status"], "second_contact_review")
        snapshot["events"].append(plan_event("SECOND", "contact", "2026-04-17", HAIR_TO_WAVE_RULE,
                                            key, [HAIR_TO_WAVE_RULE]))
        result = evaluate_portfolio(snapshot, "2026-05-02")
        self.assertFalse(any(row["plan_key"] == key for row in result["operator_timeline"]))

    def test_refusing_one_shaver_keeps_other_model_and_wave(self):
        snapshot = self.expansion_snapshot()
        key = self.expansion_contact(snapshot)
        snapshot["events"].append({"id": "NO_PRO", "type": "product_rejection", "date": "2026-04-02",
                                   "plan_key": key, "product_key": "laifen_p3_pro"})
        result = evaluate_portfolio(snapshot, "2026-04-16")
        plan = result["primary_contact_plan"]
        self.assertEqual({o["product_key"] for o in plan["primary_opportunity"]["target_options"]}, {"laifen_p3"})
        self.assertEqual({item["rule_id"] for item in plan["secondary_opportunities"]},
                         {HAIR_TO_WAVE_RULE})
        snapshot["events"].append({"id": "NO_ALL", "type": "plan_rejection", "date": "2026-04-17", "plan_key": key})
        result = evaluate_portfolio(snapshot, "2026-04-17")
        self.assertFalse(any(row["plan_key"] == key for row in result["operator_timeline"]))

    def test_future_outcomes_are_ignored_and_event_order_is_deterministic(self):
        snapshot = self.expansion_snapshot()
        key = self.expansion_contact(snapshot)
        expected = evaluate_portfolio(snapshot, "2026-04-16")
        snapshot["events"].append({"id": "FUTURE", "type": "plan_rejection", "date": "2026-05-01", "plan_key": key})
        original = copy.deepcopy(snapshot)
        self.assertEqual(expected, evaluate_portfolio(snapshot, "2026-04-16"))
        snapshot["events"].reverse()
        snapshot["purchases"] *= 2
        self.assertEqual(expected, evaluate_portfolio(snapshot, "2026-04-16"))
        self.assertEqual(original["events"][-1]["type"], "plan_rejection")

    def test_day_45_plan_available_without_remaining_accessories(self):
        snapshot = customer(purchase(day="2026-01-01", order_id="ORDER_NEO"),
                            purchase("C", "CP34473", "2026-01-10"),
                            purchase("P", "CL51809", "2026-01-10"),
                            purchase("M", "30101-000092", "2026-01-10"),
                            purchase("B", "30101-000041", "2026-01-10"))
        result = evaluate_portfolio(snapshot, "2026-02-15")
        self.assertEqual(result["primary_contact_plan"]["primary_opportunity"]["rule_id"],
                         AUTOCURL_RULE)
        self.assertEqual(result["portfolio_status"], "contact_review")
        row = next(row for row in result["operator_timeline"]
                   if any(item["rule_id"] == AUTOCURL_RULE for item in row["proposals"]))
        self.assertEqual(row["next_contact_date"], "2026-02-15")
        self.assertEqual(row["blocking_plan_keys"], [])

    def test_outcomes_do_not_cross_order_or_cycle_boundaries(self):
        snapshot = customer(purchase("P3", "CP96308", "2025-01-01", order_id="SHAVER_ORDER"),
                            purchase("HEAD", "30103-000046", "2026-01-01", order_id="HEAD_ORDER"))
        snapshot["events"] = [{"id": "OLD_REFUSAL", "type": "plan_rejection", "date": "2025-07-01",
                               "plan_key": ["SHAVER_ORDER", "shaving", "2025-06-30"]}]
        result = evaluate_portfolio(snapshot, "2026-06-30")
        self.assertEqual(result["primary_contact_plan"]["primary_opportunity"]["rule_id"], P3_HEAD_RULE)
        self.assertEqual(result["primary_contact_plan"]["source_order_id"], "HEAD_ORDER")
        self.assertEqual(result["primary_contact_plan"]["contact_count"], 0)

    def test_brush_applies_to_every_hair_dryer_configuration_at_fifteen_days(self):
        source_skus = (
            "CR05272", "CQ15839", "CQ62986", "CR68941", "CP38475",
            "CK8063", "CL50961", "CP34448", "1HD20-S-EU-PU-001",
        )
        for sku in source_skus:
            with self.subTest(sku=sku):
                snapshot = customer(purchase(sku=sku, day="2026-09-08"))
                self.assertEqual(evaluate(snapshot, "2026-09-22", BRUSH_RULE)["status"], "deferred")
                result = evaluate(snapshot, "2026-09-23", BRUSH_RULE)
                self.assertEqual(result["status"], "first_contact_review")
                self.assertEqual(result["relationship_type"], "USE_CASE_COMPLEMENT")
                self.assertEqual(result["target_sku"], "30101-000041")
                self.assertEqual(result["nominal_value_minor"], 1299)

    def test_either_brush_color_excludes_the_shared_opportunity(self):
        for sku in ("30101-000041", "CL51811"):
            with self.subTest(sku=sku):
                snapshot = customer(
                    purchase("DRYER", "CR05272", "2026-01-01"),
                    purchase("BRUSH", sku, "2026-09-01"),
                )
                self.assertEqual(evaluate(snapshot, "2026-09-23", BRUSH_RULE)["status"], "excluded")

    def test_autocurl_catalog_and_cross_sell_apply_to_every_hair_dryer(self):
        catalog = json.loads(
            (Path(__file__).resolve().parents[1] / "src" / "catalog.json").read_text(
                encoding="utf-8"
            )
        )
        autocurl = next(product for product in catalog["products"]
                        if product["key"] == "laifen_autocurl")
        self.assertEqual(
            {(variant["sku"], variant["ean"], variant["color"],
              variant["observed_price_minor"]) for variant in autocurl["variants"]},
            {
                ("1HC51-P-EU-BL-001", "6942590703456", "Black", 9999),
                ("1HC51-P-EU-WH-002", "6942590703463", "White", 9999),
            },
        )
        self.assertEqual(set(autocurl["suitability"]["hair_types"]),
                         {"fine", "normal", "thick"})
        source_skus = (
            "CR05272", "CQ15839", "CQ62986", "CR68941", "CP38475",
            "CK8063", "CL50961", "CP34448", "1HD20-S-EU-PU-001",
        )
        for sku in source_skus:
            with self.subTest(sku=sku):
                snapshot = customer(purchase(sku=sku, day="2026-09-08"))
                self.assertEqual(evaluate(snapshot, "2026-10-22", AUTOCURL_RULE)["status"],
                                 "deferred")
                result = evaluate(snapshot, "2026-10-23", AUTOCURL_RULE)
                self.assertEqual(result["status"], "first_contact_review")
                self.assertEqual(result["nominal_value_minor"], 9999)
                self.assertEqual(
                    {(option["sku"], option["color"]) for option in result["target_options"]},
                    {
                        ("1HC51-P-EU-BL-001", "Black"),
                        ("1HC51-P-EU-WH-002", "White"),
                    },
                )
                self.assertFalse(any("interesse" in check for check in result["operator_checks"]))

    def test_either_autocurl_color_excludes_the_shared_opportunity(self):
        for target_sku in ("1HC51-P-EU-BL-001", "1HC51-P-EU-WH-002"):
            with self.subTest(target_sku=target_sku):
                snapshot = customer(
                    purchase("DRYER", "CR05272", "2026-01-01"),
                    purchase("AUTOCURL", target_sku, "2026-09-01"),
                )
                self.assertEqual(
                    evaluate(snapshot, "2026-09-23", AUTOCURL_RULE)["status"],
                    "excluded",
                )

    def test_mini_travel_cross_sell_uses_summer_window_for_other_hair_dryers(self):
        source_skus = (
            "CR05272", "CQ15839", "CQ62986", "CR68941", "CP38475",
            "CK8063", "CL50961", "1HD20-S-EU-PU-001",
        )
        for sku in source_skus:
            with self.subTest(sku=sku):
                snapshot = customer(purchase(sku=sku, day="2026-02-01"))
                before = evaluate(snapshot, "2026-05-14", MINI_TRAVEL_RULE)
                self.assertEqual(before["status"], "deferred")
                self.assertEqual(before["next_contact_date"], "2026-05-15")
                ready = evaluate(snapshot, "2026-05-15", MINI_TRAVEL_RULE)
                self.assertEqual(ready["status"], "first_contact_review")
                self.assertEqual(ready["eligible_from_date"], "2026-05-15")
                self.assertEqual(ready["nominal_value_minor"], 7999)
                self.assertEqual(
                    {option["sku"] for option in ready["target_options"]},
                    {"CP34448", "CP34447", "CP34500", "CR05263"},
                )
                self.assertFalse(any("interesse" in check for check in ready["operator_checks"]))

    def test_mini_travel_windows_repeat_and_include_boundaries(self):
        snapshot = customer(purchase(day="2026-02-01"))
        expected = {
            "2026-09-05": ("first_contact_review", None),
            "2026-09-06": ("deferred", "2026-12-15"),
            "2026-12-14": ("deferred", "2026-12-15"),
            "2026-12-15": ("first_contact_review", None),
            "2027-01-15": ("first_contact_review", None),
            "2027-01-16": ("deferred", "2027-05-15"),
        }
        for day, (status, next_date) in expected.items():
            with self.subTest(day=day):
                result = evaluate(snapshot, day, MINI_TRAVEL_RULE)
                self.assertEqual(result["status"], status)
                self.assertEqual(result["next_contact_date"], next_date)
                self.assertEqual(result["eligible_from_date"], "2026-05-15")

        winter_purchase = customer(purchase(day="2027-01-01"))
        self.assertEqual(evaluate(winter_purchase, "2027-01-01", MINI_TRAVEL_RULE)["status"],
                         "first_contact_review")
        self.assertEqual(evaluate(winter_purchase, "2027-01-01", MINI_TRAVEL_RULE)["eligible_from_date"],
                         "2027-01-01")
        summer_purchase = customer(purchase(day="2026-05-16"))
        self.assertEqual(evaluate(summer_purchase, "2026-05-16", MINI_TRAVEL_RULE)["status"],
                         "first_contact_review")

    def test_mini_travel_follow_up_waits_for_next_window_and_stops_after_two_contacts(self):
        snapshot = customer(purchase(day="2026-02-01"))
        snapshot["events"].append(event("MINI_1", "contact", "2026-09-05", MINI_TRAVEL_RULE))
        before = evaluate(snapshot, "2026-09-20", MINI_TRAVEL_RULE)
        self.assertEqual(before["status"], "deferred")
        self.assertEqual(before["next_contact_date"], "2026-12-15")
        self.assertEqual(before["eligible_from_date"], "2026-05-15")
        self.assertEqual(evaluate(snapshot, "2026-12-15", MINI_TRAVEL_RULE)["status"],
                         "second_contact_review")
        snapshot["events"].append(event("MINI_2", "contact", "2026-12-15", MINI_TRAVEL_RULE))
        self.assertEqual(evaluate(snapshot, "2027-05-15", MINI_TRAVEL_RULE)["status"],
                         "stopped")

    def test_mini_travel_global_contact_gap_does_not_schedule_outside_window(self):
        snapshot = customer(purchase(day="2026-08-01"),
            purchase("CONCENTRATOR", "CP34473", "2026-08-01"),
            purchase("MOUNT", "30101-000092", "2026-08-01"))
        snapshot["events"] = [
            event("POUCH_CONTACT", "contact", "2026-09-05", POUCH_RULE),
            event("POUCH_REJECTED", "rejection", "2026-09-05", POUCH_RULE),
        ]
        result = evaluate_portfolio(snapshot, "2026-09-05")
        self.assertEqual(result["primary_contact_plan"]["primary_opportunity"]["rule_id"],
                         MINI_TRAVEL_RULE)
        self.assertEqual(result["portfolio_status"], "deferred")
        self.assertEqual(result["next_contact_date"], "2026-12-15")
        self.assertEqual(result["primary_contact_plan"]["plan_next_contact_date"],
                         "2026-12-15")
        mini_row = next(row for row in result["operator_timeline"]
                        if row["proposals"][0]["rule_id"] == MINI_TRAVEL_RULE)
        self.assertEqual(mini_row["next_contact_date"], "2026-12-15")

    def test_mini_travel_remains_separate_when_accessories_mature_same_day(self):
        snapshot = customer(purchase(day="2026-04-30", order_id="ORDER_DRYER"))
        result = evaluate_portfolio(snapshot, "2026-05-15")
        mini = [plan for plan in [result["primary_contact_plan"],
                                 *result["queued_contact_plans"]]
                if plan["primary_opportunity"]["rule_id"] == MINI_TRAVEL_RULE]
        self.assertEqual(len(mini), 1)
        self.assertEqual(mini[0]["plan_key"],
                         ["ORDER_DRYER", "seasonal_travel", "2026-05-15"])
        self.assertTrue(any(plan["commercial_track"] == "hair_care"
                            for plan in [result["primary_contact_plan"],
                                         *result["queued_contact_plans"]]))

    def test_existing_mini_excludes_travel_cross_sell_and_mini_alone_is_not_a_source(self):
        for mini_sku in ("CP34448", "CP34447", "CP34500", "CR05263"):
            with self.subTest(mini_sku=mini_sku):
                self.assertEqual(
                    evaluate(
                        customer(purchase("MINI", mini_sku, "2025-01-01")),
                        "2026-09-23",
                        MINI_TRAVEL_RULE,
                    )["status"],
                    "excluded",
                )
                snapshot = customer(
                    purchase("DRYER", "CR05272", "2025-01-01"),
                    purchase("MINI", mini_sku, "2026-01-01"),
                )
                self.assertEqual(
                    evaluate(snapshot, "2026-09-23", MINI_TRAVEL_RULE)["status"],
                    "excluded",
                )

    def test_hair_dryer_to_wave_pro_category_expansion_starts_at_day_75(self):
        source_skus = (
            "CR05272", "CQ15839", "CQ62986", "CR68941", "CP38475",
            "CK8063", "CL50961", "CP34448", "1HD20-S-EU-PU-001",
        )
        for sku in source_skus:
            with self.subTest(sku=sku):
                snapshot = customer(purchase(sku=sku, day="2026-01-01"))
                before = evaluate(snapshot, "2026-03-16", HAIR_TO_WAVE_RULE)
                self.assertEqual(before["status"], "deferred")
                self.assertEqual(before["next_contact_date"], "2026-03-17")
                ready = evaluate(snapshot, "2026-03-17", HAIR_TO_WAVE_RULE)
                self.assertEqual(ready["status"], "first_contact_review")
                self.assertEqual(ready["relationship_type"], "CATEGORY_EXPANSION")
                self.assertEqual(ready["commercial_track"], "category_expansion")
                self.assertEqual(ready["nominal_value_minor"], 9999)
                self.assertEqual(
                    {option["sku"] for option in ready["target_options"]},
                    {"CR95008", "CR95009", "CR95024", "CR95017", "CR95041", "CR95016"},
                )
                self.assertFalse(any("interesse" in check for check in ready["operator_checks"]))

    def test_any_toothbrush_excludes_hair_dryer_to_wave_pro_category_expansion(self):
        toothbrush_skus = (
            "CL97510", "CL97511", "CL97508X", "CP34472X", "CL97509", "C027164",
            "C027165", "CR95008", "CR95009", "CR95024", "CR95017", "CR95041", "CR95016",
        )
        for sku in toothbrush_skus:
            with self.subTest(sku=sku):
                snapshot = customer(
                    purchase("DRYER", "CR05272", "2026-01-01"),
                    purchase("TOOTHBRUSH", sku, "2026-02-01"),
                )
                self.assertEqual(
                    evaluate(snapshot, "2026-09-23", HAIR_TO_WAVE_RULE)["status"],
                    "excluded",
                )

    def test_toothbrush_to_neo_category_expansion_starts_at_day_90(self):
        source_skus = (
            "CL97510", "CL97511", "CL97508X", "CP34472X", "CL97509", "C027164",
            "C027165", "CR95008", "CR95009", "CR95024", "CR95017", "CR95041", "CR95016",
        )
        for sku in source_skus:
            with self.subTest(sku=sku):
                snapshot = customer(purchase(sku=sku, day="2026-01-01"))
                before = evaluate(snapshot, "2026-03-31", TOOTHBRUSH_TO_NEO_RULE)
                self.assertEqual(before["status"], "deferred")
                self.assertEqual(before["next_contact_date"], "2026-04-01")
                ready = evaluate(snapshot, "2026-04-01", TOOTHBRUSH_TO_NEO_RULE)
                self.assertEqual(ready["status"], "first_contact_review")
                self.assertEqual(ready["relationship_type"], "CATEGORY_EXPANSION")
                self.assertEqual(ready["commercial_track"], "category_expansion")
                self.assertEqual(ready["nominal_value_minor"], 13499)
                self.assertEqual(
                    {option["sku"] for option in ready["target_options"]},
                    {"CQ15839", "CQ15841", "CQ15840", "CR05272", "CR05186", "CR05227"},
                )
                self.assertEqual(
                    [option["configuration"] for option in ready["target_options"][:3]],
                    ["three_nozzles"] * 3,
                )
                self.assertFalse(any("interesse" in check for check in ready["operator_checks"]))

    def test_any_hair_dryer_excludes_toothbrush_to_neo_category_expansion(self):
        hair_dryer_skus = (
            "CR05272", "CQ15839", "CQ62986", "CR68941", "CP38475",
            "CK8063", "CL50961", "CP34448", "1HD20-S-EU-PU-001",
        )
        for sku in hair_dryer_skus:
            with self.subTest(sku=sku):
                snapshot = customer(
                    purchase("TOOTHBRUSH", "CR95008", "2026-01-01"),
                    purchase("DRYER", sku, "2026-02-01"),
                )
                self.assertEqual(
                    evaluate(snapshot, "2026-09-23", TOOTHBRUSH_TO_NEO_RULE)["status"],
                    "excluded",
                )

    def test_storage_pouch_applies_to_every_hair_dryer_except_swift_premium(self):
        source_skus = (
            "CR05272", "CQ15839", "CQ62986", "CR68941", "CK8063",
            "CL50961", "CP34448", "1HD20-S-EU-PU-001",
        )
        for sku in source_skus:
            with self.subTest(sku=sku):
                snapshot = customer(purchase(sku=sku, day="2026-09-08"))
                self.assertEqual(evaluate(snapshot, "2026-09-22", POUCH_RULE)["status"],
                                 "deferred")
                result = evaluate(snapshot, "2026-09-23", POUCH_RULE)
                self.assertEqual(result["status"], "first_contact_review")
                self.assertEqual(result["target_sku"], "CL51809")
                self.assertEqual(result["nominal_value_minor"], 2999)

        for sku in ("CP38476", "CP38473", "CP38475"):
            with self.subTest(swift_premium_sku=sku):
                result = evaluate(
                    customer(purchase(sku=sku, day="2026-09-08")),
                    "2026-09-23",
                    POUCH_RULE,
                )
                self.assertEqual(result["status"], "excluded")

    def test_storage_pouch_purchase_excludes_the_shared_opportunity(self):
        snapshot = customer(
            purchase("DRYER", "CR05272", "2026-01-01"),
            purchase("POUCH", "CL51809", "2026-09-01"),
        )
        self.assertEqual(evaluate(snapshot, "2026-09-23", POUCH_RULE)["status"], "excluded")

    def test_p3_family_and_accessories_are_cataloged_with_confirmed_compatibility(self):
        catalog = json.loads(
            (Path(__file__).resolve().parents[1] / "src" / "catalog.json").read_text(
                encoding="utf-8"
            )
        )
        products = {product["key"]: product for product in catalog["products"]}
        p3 = products["laifen_p3"]
        p3_pro = products["laifen_p3_pro"]
        head = products["laifen_p3_pro_replacement_head"]
        travel_case = products["laifen_p3_travel_case"]
        self.assertEqual(
            {(variant["sku"], variant["ean"], variant["material"],
              variant["observed_price_minor"]) for variant in p3["variants"]},
            {
                ("1ER91-P-XX-BL-002", "6942590702466", "Composito ad alta resistenza", 16999),
                ("1ER91-P-XX-WH-002", "6942590702473", "Composito ad alta resistenza", 16999),
            },
        )
        self.assertEqual(
            {(variant["sku"], variant["ean"], variant["material"],
              variant["observed_price_minor"]) for variant in p3_pro["variants"]},
            {
                ("CP96308", "6976973858235", "Alluminio CNC", 19999),
                ("CP96436", "6976973858242", "Alluminio CNC", 19999),
            },
        )
        self.assertEqual(
            {item["key"] for item in p3["configurations"][0]["included_components"]},
            {"p3_shaving_head", "p3_blade_protective_case", "usb_c_charging_cable",
             "user_manual"},
        )
        self.assertEqual(
            {item["key"] for item in p3_pro["configurations"][0]["included_components"]},
            {"p3_pro_blade_protective_case", "usb_c_charging_cable", "user_manual"},
        )
        self.assertEqual(
            {(variant["sku"], variant["ean"], variant["color"],
              variant["observed_price_minor"]) for variant in head["variants"]},
            {
                ("30103-000046", "6976973859362", "Original Aluminium Alloy", 4499),
                ("30103-000047", "6976973859379", "Space Gray Aluminium Alloy", 4499),
            },
        )
        self.assertEqual(
            {item["model"]: item["compatible"] for item in head["compatibility"]},
            {"P3 Pro": True, "P3": False},
        )
        self.assertEqual(
            {(variant["sku"], variant["ean"], variant["color"],
              variant["observed_price_minor"]) for variant in travel_case["variants"]},
            {
                ("30103-000019", "6976973858778", "White", 2999),
                ("30103-000021", "6976973858792", "Gray", 2999),
            },
        )
        self.assertEqual(
            {item["model"]: item["compatible"] for item in travel_case["compatibility"]},
            {"P3 Pro": True, "P3": True},
        )
        rules = json.loads(
            (Path(__file__).resolve().parents[1] / "src" / "rules.json").read_text(
                encoding="utf-8"
            )
        )
        serialized_rules = json.dumps(rules, ensure_ascii=False)
        standby_ids = {item["id"] for item in catalog["standby_checks"]}
        self.assertIn("laifen_p3_pro_replacement_head", serialized_rules)
        self.assertNotIn("p3_pro_replacement_head_p3_compatibility", standby_ids)
        self.assertNotIn("p3_pro_replacement_head_timing", standby_ids)

    def test_p3_travel_case_cross_sell_timing_options_and_exclusion(self):
        for sku in ("1ER91-P-XX-BL-002", "1ER91-P-XX-WH-002", "CP96308", "CP96436"):
            with self.subTest(sku=sku):
                snapshot = customer(purchase(sku=sku, day="2026-09-08"))
                self.assertEqual(evaluate(snapshot, "2026-09-22", P3_CASE_RULE)["status"],
                                 "deferred")
                result = evaluate(snapshot, "2026-09-23", P3_CASE_RULE)
                self.assertEqual(result["status"], "first_contact_review")
                self.assertEqual(result["nominal_value_minor"], 2999)
                self.assertEqual(
                    {(option["sku"], option["color"]) for option in result["target_options"]},
                    {("30103-000019", "White"), ("30103-000021", "Gray")},
                )

        for case_sku in ("30103-000019", "30103-000021"):
            with self.subTest(case_sku=case_sku):
                snapshot = customer(
                    purchase("SHAVER", "CP96308", "2026-01-01"),
                    purchase("CASE", case_sku, "2026-09-01"),
                )
                self.assertEqual(evaluate(snapshot, "2026-09-23", P3_CASE_RULE)["status"],
                                 "excluded")

    def test_p3_pro_head_replenishment_starts_at_day_180_with_matching_finish(self):
        cases = (
            ("CP96308", "30103-000046"),
            ("CP96436", "30103-000047"),
        )
        for source_sku, preferred_sku in cases:
            with self.subTest(source_sku=source_sku):
                snapshot = customer(purchase("P3_PRO", source_sku, "2026-01-01"))
                before = evaluate(snapshot, "2026-06-29", P3_HEAD_RULE)
                self.assertEqual(before["status"], "deferred")
                self.assertEqual(before["next_contact_date"], "2026-06-30")
                ready = evaluate(snapshot, "2026-06-30", P3_HEAD_RULE)
                self.assertEqual(ready["status"], "first_contact_review")
                self.assertEqual(ready["preferred_target_sku"], preferred_sku)
                self.assertEqual(ready["nominal_value_minor"], 4499)
                self.assertEqual(
                    {option["sku"] for option in ready["target_options"]},
                    {"30103-000046", "30103-000047"},
                )

        for p3_sku in ("1ER91-P-XX-BL-002", "1ER91-P-XX-WH-002"):
            with self.subTest(p3_sku=p3_sku):
                result = evaluate(
                    customer(purchase("P3", p3_sku, "2025-01-01")),
                    "2026-09-23",
                    P3_HEAD_RULE,
                )
                self.assertEqual(result["status"], "no_action")

    def test_p3_pro_head_purchase_opens_new_180_day_cycle_and_follow_up(self):
        snapshot = customer(
            purchase("P3_PRO", "CP96308", "2025-01-01"),
            purchase("HEAD", "30103-000047", "2026-01-01"),
        )
        before = evaluate(snapshot, "2026-06-29", P3_HEAD_RULE)
        self.assertEqual(before["status"], "deferred")
        ready = evaluate(snapshot, "2026-06-30", P3_HEAD_RULE)
        self.assertEqual(ready["status"], "first_contact_review")
        self.assertEqual(ready["cycle_kind"], "repeat")
        self.assertEqual(ready["cycle_reference_purchase_id"], "HEAD")
        self.assertEqual(ready["preferred_target_sku"], "30103-000047")
        snapshot["events"] = [
            {
                **event("CONTACT", day="2026-06-30", rule_id=P3_HEAD_RULE),
                "cycle_reference_purchase_id": "HEAD",
            }
        ]
        self.assertEqual(evaluate(snapshot, "2026-07-14", P3_HEAD_RULE)["status"], "deferred")
        self.assertEqual(
            evaluate(snapshot, "2026-07-15", P3_HEAD_RULE)["status"],
            "second_contact_review",
        )

    def test_p3_pro_head_value_precedes_older_travel_case_plan(self):
        snapshot = customer(purchase("P3_PRO", "CP96308", "2026-01-01", order_id="ORDER_P3"))
        result = evaluate_portfolio(snapshot, "2026-06-30")
        self.assertEqual(
            result["primary_contact_plan"]["primary_opportunity"]["rule_id"],
            P3_HEAD_RULE,
        )
        self.assertEqual(
            result["queued_contact_plans"][0]["primary_opportunity"]["rule_id"],
            P3_CASE_RULE,
        )

    def test_wave_pro_variants_are_cataloged_without_hair_dryer_opportunities(self):
        catalog = json.loads(
            (Path(__file__).resolve().parents[1] / "src" / "catalog.json").read_text(encoding="utf-8")
        )
        wave_pro = next(product for product in catalog["products"]
                        if product["key"] == "laifen_wave_pro")
        self.assertEqual(
            {(variant["sku"], variant["ean"], variant["observed_price_minor"])
             for variant in wave_pro["variants"]},
            {
                ("CR95008", "6942590701018", 9999),
                ("CR95009", "6942590701049", 9999),
                ("CR95024", "6942590701025", 9999),
                ("CR95017", "6942590701056", 11999),
                ("CR95041", "6942590701063", 11999),
                ("CR95016", "6942590701100", 13999),
            },
        )
        expected_components = {
            "wave_pro_whitening_head",
            "wave_pro_antiplaque_head",
            "wave_pro_travel_case",
            "wave_pro_wireless_charger",
        }
        self.assertEqual(
            {item["key"] for item in wave_pro["configurations"][0]["included_components"]},
            expected_components,
        )
        for variant in wave_pro["variants"]:
            with self.subTest(sku=variant["sku"]):
                snapshot = customer(purchase(sku=variant["sku"], day="2026-01-01"))
                self.assertEqual(evaluate(snapshot, "2026-09-23", BRUSH_RULE)["status"],
                                 "no_action")

    def test_legacy_wave_is_historical_only_and_opens_replacement_at_six_months(self):
        catalog = json.loads(
            (Path(__file__).resolve().parents[1] / "src" / "catalog.json").read_text(
                encoding="utf-8"
            )
        )
        legacy = next(product for product in catalog["products"]
                      if product["key"] == "laifen_wave_legacy")
        self.assertEqual(legacy["lifecycle"], "discontinued_no_restock")
        self.assertEqual(
            {(variant["sku"], variant["ean"], variant["observed_price_minor"])
             for variant in legacy["variants"]},
            {
                ("CL97510", "6973833032231", 5999),
                ("CL97511", "6973833033160", 5999),
                ("CL97508X", "6976973853650X", 5999),
                ("CP34472X", "6976973853674X", 5999),
                ("CL97509", "6973833032248", 6999),
                ("C027164", "6976973853704", 6999),
                ("C027165", "6976973853698", 6999),
            },
        )
        self.assertEqual(
            {variant["commercial_status"] for variant in legacy["variants"]},
            {"historical_only"},
        )
        for variant in legacy["variants"]:
            with self.subTest(sku=variant["sku"]):
                snapshot = customer(purchase(sku=variant["sku"], day="2026-01-01"))
                self.assertEqual(
                    evaluate(snapshot, "2026-09-23", WAVE_HEADS_RULE)["status"],
                    "first_contact_review",
                )
                before = evaluate(snapshot, "2026-06-29", WAVE_REPLACEMENT_RULE)
                self.assertEqual(before["status"], "deferred")
                self.assertEqual(before["next_contact_date"], "2026-06-30")
                ready = evaluate(snapshot, "2026-06-30", WAVE_REPLACEMENT_RULE)
                self.assertEqual(ready["status"], "first_contact_review")
                self.assertEqual(ready["relationship_type"], "REPLACEMENT")
                self.assertEqual(ready["plan_rank"], 450)
                self.assertEqual(ready["nominal_value_minor"], 9999)
                self.assertEqual(ready["maximum_option_value_minor"], 13999)
                self.assertEqual(len(ready["target_options"]), 6)

    def test_wave_pro_purchase_excludes_legacy_wave_replacement(self):
        for sku in ("CR95008", "CR95009", "CR95024", "CR95017", "CR95041", "CR95016"):
            with self.subTest(sku=sku):
                snapshot = customer(
                    purchase("LEGACY", "CL97510", "2025-01-01"),
                    purchase("PRO", sku, "2026-01-01"),
                )
                result = evaluate(snapshot, "2026-09-23", WAVE_REPLACEMENT_RULE)
                self.assertEqual(result["status"], "excluded")

    def test_legacy_wave_replacement_has_no_maximum_age(self):
        snapshot = customer(purchase(sku="CL97510", day="2020-01-01"))
        result = evaluate(snapshot, "2026-09-23", WAVE_REPLACEMENT_RULE)
        self.assertEqual(result["status"], "first_contact_review")
        self.assertEqual(result["eligible_from_date"], "2020-06-29")

    def test_wave_chargers_are_distinct_catalog_items_without_automatic_opportunities(self):
        catalog = json.loads(
            (Path(__file__).resolve().parents[1] / "src" / "catalog.json").read_text(
                encoding="utf-8"
            )
        )
        cable = next(product for product in catalog["products"]
                     if product["key"] == "laifen_wave_legacy_magnetic_charging_cable")
        base = next(product for product in catalog["products"]
                    if product["key"] == "laifen_wave_pro_charging_base")
        self.assertEqual(
            {(variant["sku"], variant["ean"], variant["observed_price_minor"])
             for variant in cable["variants"]},
            {("6973833031630", "6973833031630", 999)},
        )
        self.assertEqual(cable["compatibility"][0]["model"], "Wave")
        self.assertEqual(set(cable["compatibility"][0]["compatible_materials"]),
                         {"ABS", "Alluminio"})
        self.assertEqual(
            {(variant["sku"], variant["ean"], variant["material"],
              variant["observed_price_minor"])
             for variant in base["variants"]},
            {
                ("30102-000170", "6942590701155", "ABS", 2999),
                ("30102-000171", "6942590701162", "Alluminio", 2999),
            },
        )
        self.assertEqual(base["compatibility"][0]["model"], "Wave Pro")
        rules = json.loads(
            (Path(__file__).resolve().parents[1] / "src" / "rules.json").read_text(
                encoding="utf-8"
            )
        )
        serialized_rules = json.dumps(rules, ensure_ascii=False)
        self.assertNotIn("laifen_wave_legacy_magnetic_charging_cable", serialized_rules)
        self.assertNotIn("laifen_wave_pro_charging_base", serialized_rules)
        standby_ids = {item["id"] for item in catalog["standby_checks"]}
        self.assertNotIn("wave_legacy_charging_cable_commercial_activation", standby_ids)
        self.assertNotIn("wave_pro_charging_base_commercial_activation", standby_ids)
        for sku in ("6973833031630", "30102-000170", "30102-000171"):
            with self.subTest(sku=sku):
                portfolio = evaluate_portfolio(
                    customer(purchase(sku=sku, day="2026-01-01")), "2026-09-23"
                )
                self.assertEqual(portfolio["portfolio_status"], "no_opportunity")

    def test_legacy_wave_travel_box_is_not_compatible_with_wave_pro(self):
        catalog = json.loads(
            (Path(__file__).resolve().parents[1] / "src" / "catalog.json").read_text(
                encoding="utf-8"
            )
        )
        products = {product["key"]: product for product in catalog["products"]}
        travel_box = products["laifen_wave_legacy_travel_box"]
        self.assertEqual(
            {(variant["sku"], variant["ean"], variant["model"],
              variant.get("observed_price_minor"))
             for variant in travel_box["variants"]},
            {("CM61971", "6976973854572", "ABS", 1999), ("CM61972", None, "Alluminio", None)},
        )
        self.assertEqual(travel_box["observed_variant_count"], 2)
        self.assertNotIn("unmapped_variants", travel_box)
        self.assertEqual({variant["material"] for variant in travel_box["variants"]}, {"ABS"})
        self.assertEqual({variant["contained_toothbrush_material"] for variant in travel_box["variants"]}, {"ABS", "Alluminio"})
        compatibility = {item["model"]: item["compatible"]
                         for item in travel_box["compatibility"]}
        self.assertEqual(compatibility, {"Wave": True, "Wave Pro": False})
        legacy_components = {
            item["key"]
            for item in products["laifen_wave_legacy"]["configurations"][0]["included_components"]
        }
        pro_components = {
            item["key"]
            for item in products["laifen_wave_pro"]["configurations"][0]["included_components"]
        }
        self.assertIn("wave_legacy_travel_box", legacy_components)
        self.assertIn("wave_pro_travel_case", pro_components)
        self.assertNotIn("wave_legacy_travel_box", pro_components)
        rules = json.loads(
            (Path(__file__).resolve().parents[1] / "src" / "rules.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertNotIn("laifen_wave_legacy_travel_box",
                         json.dumps(rules, ensure_ascii=False))
        standby_ids = {item["id"] for item in catalog["standby_checks"]}
        self.assertIn("wave_legacy_travel_box_aluminum_identifiers", standby_ids)
        self.assertNotIn("wave_legacy_travel_box_commercial_activation", standby_ids)
        portfolio = evaluate_portfolio(
            customer(purchase(sku="CM61971", day="2026-01-01")), "2026-09-23"
        )
        self.assertEqual(portfolio["portfolio_status"], "no_opportunity")

    def test_wave_pro_replacement_heads_are_cataloged_and_activate_at_day_150(self):
        catalog = json.loads(
            (Path(__file__).resolve().parents[1] / "src" / "catalog.json").read_text(encoding="utf-8")
        )
        heads = next(product for product in catalog["products"]
                     if product["key"] == "laifen_wave_pro_replacement_heads")
        wave_pro = next(product for product in catalog["products"]
                        if product["key"] == "laifen_wave_pro")
        self.assertEqual(
            {(variant["sku"], variant["ean"], variant["type"],
              variant["pack_quantity"], variant["observed_price_minor"])
             for variant in heads["variants"] if not variant.get("purchase_recognition_only")},
            {
                ("CR95042", "6976973851991", "Pro Whitening", 3, 1999),
                ("CR95032", "6976973852004", "Pro Plaque Removal", 3, 1999),
                ("6976973852011", "6976973852011", "Pro Gum Care", 3, 1999),
                ("CR94994", "6976973851984", "Pro Max Brush", 3, 1999),
            },
        )
        for variant in wave_pro["variants"]:
            with self.subTest(sku=variant["sku"]):
                snapshot = customer(purchase(sku=variant["sku"], day="2026-01-01"))
                before = evaluate(snapshot, "2026-05-30", WAVE_HEADS_RULE)
                self.assertEqual(before["status"], "deferred")
                self.assertEqual(before["next_contact_date"], "2026-05-31")
                ready = evaluate(snapshot, "2026-05-31", WAVE_HEADS_RULE)
                self.assertEqual(ready["status"], "first_contact_review")
                self.assertEqual(ready["commercial_track"], "oral_care")
                self.assertEqual(ready["cycle_kind"], "initial")
                self.assertIsNone(ready["preferred_target_sku"])
                self.assertEqual({option["sku"] for option in ready["target_options"]},
                                 {"CR95042", "CR95032", "6976973852011", "CR94994"})

        heads_without_wave = customer(purchase(sku="CR95042", day="2026-01-01"))
        self.assertEqual(evaluate(heads_without_wave, "2026-09-23", WAVE_HEADS_RULE)["status"],
                         "no_action")

    def test_all_wave_head_codes_share_product_and_update_wave_and_wave_pro_cycles(self):
        catalog = json.loads((Path(__file__).resolve().parents[1] / "src" / "catalog.json").read_text(encoding="utf-8"))
        heads = next(p for p in catalog["products"] if p["key"] == "laifen_wave_pro_replacement_heads")
        self.assertEqual(len(heads["variants"]), 8)
        self.assertEqual({item["model"] for item in heads["compatibility"] if item["compatible"]}, {"Wave", "Wave Pro"})
        self.assertNotIn("wave_legacy_replacement_heads_compatibility", {x["id"] for x in catalog["standby_checks"]})
        for sku in ("CP38422", "CP38423", "CP38472", "CP38474"):
            with self.subTest(sku=sku):
                snapshot = customer(purchase("DEVICE", "CR95008", "2025-01-01"), purchase("PACK", sku, "2026-01-01"))
                result = evaluate(snapshot, "2026-08-29", WAVE_HEADS_RULE)
                self.assertEqual(result["cycle_kind"], "repeat")
                self.assertEqual(result["cycle_reference_purchase_id"], "PACK")
                self.assertEqual(result["eligible_from_date"], "2026-08-29")
                self.assertIsNone(result["preferred_target_sku"])
                self.assertNotIn(sku, {x["sku"] for x in result["target_options"]})
                snapshot["purchases"][0]["sku"] = "CL97510"
                self.assertEqual(evaluate(snapshot, "2026-08-28", WAVE_HEADS_RULE)["status"], "deferred")
                legacy = evaluate(snapshot, "2026-08-29", WAVE_HEADS_RULE)
                self.assertEqual(legacy["status"], "first_contact_review")
                self.assertEqual(legacy["cycle_reference_purchase_id"], "PACK")

    def test_wave_pro_heads_follow_up_uses_current_cycle(self):
        snapshot = customer(purchase("WAVE", "CR95008", "2026-01-01"))
        snapshot["events"] = [
            {
                **event("HEADS_CONTACT", day="2026-05-31", rule_id=WAVE_HEADS_RULE),
                "cycle_reference_purchase_id": "WAVE",
            }
        ]
        self.assertEqual(evaluate(snapshot, "2026-06-14", WAVE_HEADS_RULE)["status"],
                         "deferred")
        result = evaluate(snapshot, "2026-06-15", WAVE_HEADS_RULE)
        self.assertEqual(result["status"], "second_contact_review")
        self.assertEqual(result["contact_count"], 1)

    def test_legacy_wave_heads_mature_at_150_days_and_precede_uncontacted_upgrade(self):
        catalog = json.loads((Path(__file__).resolve().parents[1] / "src" / "catalog.json").read_text(encoding="utf-8"))
        legacy = next(p for p in catalog["products"] if p["key"] == "laifen_wave_legacy")
        for variant in legacy["variants"]:
            with self.subTest(sku=variant["sku"]):
                snapshot = customer(purchase("WAVE", variant["sku"], "2026-01-01"))
                self.assertEqual(evaluate(snapshot, "2026-05-30", WAVE_HEADS_RULE)["status"], "deferred")
                ready = evaluate(snapshot, "2026-05-31", WAVE_HEADS_RULE)
                self.assertEqual(ready["status"], "first_contact_review")
                self.assertEqual(ready["eligible_from_date"], "2026-05-31")
                portfolio = evaluate_portfolio(snapshot, "2026-06-30")
                self.assertEqual(portfolio["primary_contact_plan"]["primary_opportunity"]["rule_id"], WAVE_HEADS_RULE)
                self.assertEqual(portfolio, evaluate_portfolio(snapshot, "2026-06-30"))
                self.assertIn(WAVE_REPLACEMENT_RULE, [p["primary_opportunity"]["rule_id"] for p in portfolio["queued_contact_plans"]])
                snapshot["marketing_consent"]["email"]["status"] = "unsubscribed"
                self.assertEqual(evaluate_portfolio(snapshot, "2026-06-30")["portfolio_status"], "blocked_consent")

    def test_adding_legacy_wave_preserves_existing_pro_cycle_and_contact_count(self):
        snapshot = customer(purchase("PRO", "CR95008", "2026-01-01"))
        snapshot["events"] = [{**event("CONTACT", day="2026-05-31", rule_id=WAVE_HEADS_RULE),
                                "cycle_reference_purchase_id": "PRO"}]
        before = evaluate(snapshot, "2026-06-15", WAVE_HEADS_RULE)
        snapshot["purchases"].append(purchase("LEGACY", "CL97510", "2025-01-01"))
        after = evaluate(snapshot, "2026-06-15", WAVE_HEADS_RULE)
        self.assertEqual(after, before)
        self.assertEqual(after["contact_count"], 1)
        self.assertEqual(after["status"], "second_contact_review")
        snapshot["purchases"][0]["validity"] = "returned"
        self.assertEqual(evaluate(snapshot, "2026-06-15", WAVE_HEADS_RULE)["source_purchase_id"], "LEGACY")

    def test_wave_pro_heads_repeat_after_240_days_and_prefer_latest_type(self):
        snapshot = customer(
            purchase("WAVE", "CR95008", "2025-01-01"),
            purchase("HEADS", "CR95032", "2026-01-01"),
        )
        snapshot["events"] = [
            {
                **event("OLD_CYCLE_CONTACT", day="2025-06-01", rule_id=WAVE_HEADS_RULE),
                "cycle_reference_purchase_id": "WAVE",
            }
        ]
        before = evaluate(snapshot, "2026-08-28", WAVE_HEADS_RULE)
        self.assertEqual(before["status"], "deferred")
        self.assertEqual(before["next_contact_date"], "2026-08-29")
        ready = evaluate(snapshot, "2026-08-29", WAVE_HEADS_RULE)
        self.assertEqual(ready["status"], "first_contact_review")
        self.assertEqual(ready["cycle_kind"], "repeat")
        self.assertEqual(ready["cycle_reference_purchase_id"], "HEADS")
        self.assertEqual(ready["preferred_target_sku"], "CR95032")
        self.assertEqual(ready["contact_count"], 0)

    def test_value_breaks_ties_between_ready_targeted_plans(self):
        snapshot = customer(
            purchase("WAVE", "CR95008", "2026-01-01", order_id="ORDER_WAVE"),
            purchase("NEO", "CR05272", "2026-05-16", order_id="ORDER_NEO"),
            purchase("MINI", "CP34448", "2026-05-16", order_id="ORDER_MINI"),
        )
        result = evaluate_portfolio(snapshot, "2026-05-31")
        primary = result["primary_contact_plan"]["primary_opportunity"]
        self.assertEqual(primary["rule_id"], RULE)
        self.assertEqual(primary["commercial_track"], "hair_care")
        self.assertIn(WAVE_HEADS_RULE,
                      [plan["primary_opportunity"]["rule_id"]
                       for plan in result["queued_contact_plans"]])

    def test_t1_pro_is_recognized_as_owned_shaver_without_creating_new_proposals(self):
        for sku in ("CP96306", "CP96307"):
            only_t1 = customer(purchase("T1", sku, "2026-01-01"))
            self.assertIsNone(evaluate_portfolio(only_t1, "2026-10-14")["primary_contact_plan"])
            with_phon = customer(purchase("NEO", "CR05272", "2026-01-01"), *only_t1["purchases"])
            result = evaluate(with_phon, "2026-10-14", HAIR_TO_SHAVERS_RULE)
            self.assertEqual(result["status"], "excluded")
            self.assertEqual(result, evaluate(with_phon, "2026-10-14", HAIR_TO_SHAVERS_RULE))
        without_shaver = customer(purchase("NEO", "CR05272", "2026-01-01"))
        self.assertEqual(evaluate(without_shaver, "2026-10-14", HAIR_TO_SHAVERS_RULE)["status"], "first_contact_review")

    def test_neo_mount_other_verified_colors_count_as_already_owned(self):
        snapshot = customer(purchase(sku="CR05272", day="2026-01-01"))
        allowed = evaluate(snapshot, "2026-10-14", NEO_WALL_MOUNT_RULE)
        self.assertEqual(allowed["status"], "first_contact_review")
        for sku in ("30101-000249", "30101-000248"):
            owned = customer(*snapshot["purchases"], purchase("MOUNT", sku, "2026-02-01"))
            excluded = evaluate(owned, "2026-10-14", NEO_WALL_MOUNT_RULE)
            self.assertEqual(excluded["status"], "excluded")
            self.assertEqual(excluded, evaluate(owned, "2026-10-14", NEO_WALL_MOUNT_RULE))

    def test_shaver_expansion_value_precedes_replacement_without_commercial_occasion(self):
        snapshot = customer(
            purchase("LEGACY", "CL97510", "2026-01-01", order_id="ORDER_WAVE"),
            purchase("HEADS", "CR95042", "2026-09-01"),
            purchase("NEO", "CR05272", "2026-01-01", order_id="ORDER_NEO"),
            purchase("CONCENTRATOR", "CP34473", "2026-01-10"),
            purchase("POUCH", "CL51809", "2026-01-10"),
            purchase("MOUNT", "30101-000092", "2026-01-10"),
            purchase("BRUSH", "30101-000041", "2026-01-10"),
        )
        result = evaluate_portfolio(snapshot, "2026-10-19")
        primary = result["primary_contact_plan"]["primary_opportunity"]
        self.assertEqual(primary["rule_id"], HAIR_TO_SHAVERS_RULE)
        self.assertEqual(primary["nominal_value_minor"], 16999)
        self.assertEqual(
            next(p["primary_opportunity"]["rule_id"] for p in result["queued_contact_plans"]
                 if p["commercial_track"] == "oral_care"),
            WAVE_REPLACEMENT_RULE,
        )

    def test_same_order_with_two_tracks_creates_separate_contact_plans(self):
        snapshot = customer(
            purchase("NEO", "CR05272", "2026-01-01", order_id="MIXED_ORDER"),
            purchase("WAVE", "CR95008", "2026-01-01", order_id="MIXED_ORDER"),
        )
        result = evaluate_portfolio(snapshot, "2026-01-16")
        hair_plan = result["primary_contact_plan"]
        oral_plan = next(plan for plan in result["queued_contact_plans"] if plan["commercial_track"] == "oral_care")
        self.assertEqual(hair_plan["commercial_track"], "hair_care")
        self.assertEqual(len(hair_plan["included_opportunity_keys"]), 4)
        self.assertEqual(oral_plan["commercial_track"], "oral_care")
        self.assertEqual(oral_plan["eligible_from_date"], "2026-05-31")

    def test_neo_wall_mount_all_configs_calendar_boundary_and_exclusion(self):
        for sku in ("CQ15839", "CQ15841", "CQ15840", "CR05272", "CR05186", "CR05227"):
            with self.subTest(sku=sku):
                snapshot = customer(purchase(sku=sku, day="2026-09-08"))
                self.assertEqual(evaluate(snapshot, "2026-09-22", NEO_WALL_MOUNT_RULE)["status"],
                                 "deferred")
                result = evaluate(snapshot, "2026-09-23", NEO_WALL_MOUNT_RULE)
                self.assertEqual(result["status"], "first_contact_review")
                self.assertEqual(result["target_sku"], "30101-000092")
                self.assertEqual(result["nominal_value_minor"], 1799)
                snapshot["purchases"].append(purchase("WALL_MOUNT", "30101-000092"))
                self.assertEqual(evaluate(snapshot, "2026-09-23", NEO_WALL_MOUNT_RULE)["status"],
                                 "excluded")

    def test_two_wall_mounts_remain_distinct_opportunities(self):
        neo_snapshot = customer(purchase(day="2026-01-01"), purchase("MINI_MOUNT", "CP34501"))
        self.assertEqual(evaluate(neo_snapshot, "2026-09-23", NEO_WALL_MOUNT_RULE)["status"],
                         "first_contact_review")
        mini_snapshot = customer(purchase(sku="CP34448", day="2026-01-01"),
                                 purchase("NEO_MOUNT", "30101-000092"))
        self.assertEqual(evaluate(mini_snapshot, "2026-09-23", MINI_WALL_MOUNT_RULE)["status"],
                         "first_contact_review")

    def test_neo_wall_mount_uses_shared_follow_up_policy(self):
        snapshot = customer(purchase(day="2026-01-01"))
        snapshot["events"] = [event("FIRST", rule_id=NEO_WALL_MOUNT_RULE)]
        self.assertEqual(evaluate(snapshot, "2026-09-22", NEO_WALL_MOUNT_RULE)["status"], "deferred")
        self.assertEqual(evaluate(snapshot, "2026-09-23", NEO_WALL_MOUNT_RULE)["status"],
                         "second_contact_review")

    def test_air_all_colors_create_no_unconfirmed_completion_or_wall_mount(self):
        for sku in ("1HD20-S-EU-PU-001", "1HD20-S-EU-WH-001", "1HD20-S-EU-PK-001"):
            with self.subTest(sku=sku):
                snapshot = customer(purchase(sku=sku, day="2026-09-08"))
                self.assertEqual(evaluate(snapshot, "2026-09-23")["status"], "no_action")
                self.assertEqual(evaluate(snapshot, "2026-09-23", SE_LITE_RULE)["status"], "no_action")
                self.assertEqual(evaluate(snapshot, "2026-09-23", MINI_WALL_MOUNT_RULE)["status"],
                                 "no_action")

    def test_air_does_not_block_valid_neo_concentrator_opportunity(self):
        snapshot = customer(
            purchase("SOURCE", "CR05272", "2026-01-01"),
            purchase("AIR", "1HD20-S-EU-PU-001", "2026-09-01"),
        )
        self.assertEqual(evaluate(snapshot, "2026-09-23")["status"], "first_contact_review")

    def test_mini_wall_mount_all_colors_calendar_boundary_and_exclusion(self):
        for sku in ("CP34448", "CP34447", "CP34500", "CR05263"):
            with self.subTest(sku=sku):
                snapshot = customer(purchase(sku=sku, day="2026-09-08"))
                self.assertEqual(evaluate(snapshot, "2026-09-22", MINI_WALL_MOUNT_RULE)["status"],
                                 "deferred")
                result = evaluate(snapshot, "2026-09-23", MINI_WALL_MOUNT_RULE)
                self.assertEqual(result["status"], "first_contact_review")
                self.assertEqual(result["target_sku"], "CP34501")
                self.assertEqual(result["nominal_value_minor"], 1499)
                snapshot["purchases"].append(purchase("WALL_MOUNT", "CP34501"))
                self.assertEqual(evaluate(snapshot, "2026-09-23", MINI_WALL_MOUNT_RULE)["status"],
                                 "excluded")

    def test_mini_wall_mount_uses_shared_follow_up_policy(self):
        snapshot = customer(purchase(sku="CP34448", day="2026-01-01"))
        snapshot["events"] = [event("FIRST", rule_id=MINI_WALL_MOUNT_RULE)]
        self.assertEqual(evaluate(snapshot, "2026-09-22", MINI_WALL_MOUNT_RULE)["status"], "deferred")
        self.assertEqual(evaluate(snapshot, "2026-09-23", MINI_WALL_MOUNT_RULE)["status"],
                         "second_contact_review")

    def test_mini_all_colors_create_no_concentrator_or_se_lite_diffuser_completion(self):
        for sku in ("CP34448", "CP34447", "CP34500", "CR05263"):
            with self.subTest(sku=sku):
                snapshot = customer(purchase(sku=sku, day="2026-09-08"))
                self.assertEqual(evaluate(snapshot, "2026-09-23")["status"], "no_action")
                self.assertEqual(evaluate(snapshot, "2026-09-23", SE_LITE_RULE)["status"], "no_action")

    def test_mini_does_not_block_valid_neo_concentrator_opportunity(self):
        snapshot = customer(
            purchase("SOURCE", "CR05272", "2026-01-01"),
            purchase("MINI", "CP34448", "2026-09-01"),
        )
        self.assertEqual(evaluate(snapshot, "2026-09-23")["status"], "first_contact_review")

    def test_se_special_all_colors_include_accessories_and_create_no_completion_opportunity(self):
        for sku in ("CL50966", "CL50970", "CL50961", "CL50968"):
            with self.subTest(sku=sku):
                snapshot = customer(purchase(sku=sku, day="2026-09-08"))
                self.assertEqual(evaluate(snapshot, "2026-09-23")["status"], "excluded")
                self.assertEqual(evaluate(snapshot, "2026-09-23", SE_LITE_RULE)["status"], "no_action")

    def test_se_special_purchase_excludes_existing_concentrator_opportunity(self):
        snapshot = customer(
            purchase("SOURCE", "CR05272", "2026-01-01"),
            purchase("SE_SPECIAL", "CL50961", "2026-09-01"),
        )
        result = evaluate(snapshot, "2026-09-23")
        self.assertEqual(result["status"], "excluded")
        self.assertTrue(any(item["id"] == "SE_SPECIAL" for item in result["evidence"]))

    def test_gift_edition_all_colors_include_concentrator_and_create_no_accessory_opportunity(self):
        for sku in ("CK8063", "CK80633", "CK80632", "CK80631"):
            with self.subTest(sku=sku):
                snapshot = customer(purchase(sku=sku, day="2026-09-08"))
                self.assertEqual(evaluate(snapshot, "2026-09-23")["status"], "excluded")
                self.assertEqual(evaluate(snapshot, "2026-09-23", SE_LITE_RULE)["status"], "no_action")

    def test_gift_edition_purchase_excludes_existing_concentrator_opportunity(self):
        snapshot = customer(
            purchase("SOURCE", "CR05272", "2026-01-01"),
            purchase("GIFT", "CK8063", "2026-09-01"),
        )
        result = evaluate(snapshot, "2026-09-23")
        self.assertEqual(result["status"], "excluded")
        self.assertTrue(any(item["id"] == "GIFT" for item in result["evidence"]))

    def test_swift_premium_all_colors_timing_and_target_exclusion(self):
        for sku in ("CP38476", "CP38473", "CP38475"):
            with self.subTest(sku=sku):
                snapshot = customer(purchase(sku=sku, day="2026-09-08"))
                self.assertEqual(evaluate(snapshot, "2026-09-22")["status"], "deferred")
                result = evaluate(snapshot, "2026-09-23")
                self.assertEqual(result["status"], "first_contact_review")
                self.assertEqual(result["target_sku"], "CP34473")
                self.assertEqual(result["nominal_value_minor"], 2499)
                snapshot["purchases"].append(purchase("TARGET", "CP34473"))
                self.assertEqual(evaluate(snapshot, "2026-09-23")["status"], "excluded")

    def test_swift_historical_colors_have_no_expiry(self):
        for sku in ("CP38476", "CP38473"):
            with self.subTest(sku=sku):
                snapshot = customer(purchase(sku=sku, day="2020-01-01"))
                self.assertEqual(evaluate(snapshot, "2026-09-23")["status"], "first_contact_review")

    def test_swift_neo_and_special_share_one_concentrator_opportunity(self):
        snapshot = customer(
            purchase("SWIFT", "CP38475", "2026-01-01"),
            purchase("NEO", "CR05272", "2026-02-01"),
            purchase("SPECIAL", "CR68941", "2026-03-01"),
        )
        result = evaluate(snapshot, "2026-09-23")
        self.assertEqual(result["source_purchase_id"], "SWIFT")
        self.assertEqual(result["opportunity_key"], ["SYNTHETIC_001", RULE])
        snapshot["events"] = [event("CONTACT_1")]
        self.assertEqual(evaluate(snapshot, "2026-09-23")["status"], "second_contact_review")

    def test_swift_included_diffuser_does_not_create_se_lite_opportunity(self):
        snapshot = customer(purchase(sku="CP38475"))
        self.assertEqual(evaluate(snapshot, "2026-09-23", SE_LITE_RULE)["status"], "no_action")

    def test_special_all_colors_timing_and_exclusions(self):
        for sku in ("CR68941", "CR68943", "CR68942"):
            with self.subTest(sku=sku):
                snapshot = customer(purchase(sku=sku, day="2026-09-08"))
                self.assertEqual(evaluate(snapshot, "2026-09-22")["status"], "deferred")
                result = evaluate(snapshot, "2026-09-23")
                self.assertEqual(result["status"], "first_contact_review")
                self.assertEqual(result["target_sku"], "CP34473")
                for target in ("CP34473", "CQ15839", "CQ15841", "CQ15840"):
                    snapshot = customer(purchase(sku=sku), purchase("TARGET", target))
                    self.assertEqual(evaluate(snapshot, "2026-09-23")["status"], "excluded")

    def test_special_and_neo_share_one_opportunity_and_contact_history(self):
        snapshot = customer(purchase("NEO", day="2026-09-20"),
                            purchase("SPECIAL", "CR68941", "2026-01-01"))
        result = evaluate(snapshot, "2026-09-23")
        self.assertEqual(result["source_purchase_id"], "SPECIAL")
        self.assertEqual(result["opportunity_key"], ["SYNTHETIC_001", RULE])
        snapshot["events"] = [event("CONTACT_1")]
        self.assertEqual(evaluate(snapshot, "2026-09-22")["status"], "deferred")
        self.assertEqual(evaluate(snapshot, "2026-09-23")["status"], "second_contact_review")
        snapshot["events"].append(event("CONTACT_2", day="2026-09-23"))
        self.assertEqual(evaluate(snapshot, "2027-01-01")["status"], "stopped")

    def test_special_invalid_order_and_diffuser_separation(self):
        for validity in ("cancelled", "returned"):
            with self.subTest(validity=validity):
                self.assertEqual(evaluate(customer(purchase(sku="CR68941", validity=validity)),
                                          "2026-09-23")["status"], "no_action")
        snapshot = customer(purchase(sku="CR68941"))
        self.assertEqual(evaluate(snapshot, "2026-09-23", SE_LITE_RULE)["status"], "no_action")
        snapshot["purchases"].append(purchase("SE", "CQ62986"))
        self.assertEqual(evaluate(snapshot, "2026-09-23", SE_LITE_RULE)["status"], "first_contact_review")

    def test_se_lite_all_colors_calendar_boundary_and_old_purchases(self):
        for sku in ("CQ62986", "CL50959", "CL50963", "CL50964", "CL50962"):
            with self.subTest(sku=sku):
                snapshot = customer(purchase(sku=sku, day="2026-09-08"))
                self.assertEqual(evaluate(snapshot, "2026-09-22", SE_LITE_RULE)["status"], "deferred")
                result = evaluate(snapshot, "2026-09-23", SE_LITE_RULE)
                self.assertEqual(result["status"], "first_contact_review")
                self.assertEqual(result["target_sku"], "CP34510")
                self.assertEqual(result["nominal_value_minor"], 2499)
                self.assertEqual(result["opportunity_key"], ["SYNTHETIC_001", SE_LITE_RULE])
                old = customer(purchase(sku=sku, day="2020-01-01"))
                self.assertEqual(evaluate(old, "2026-09-23", SE_LITE_RULE)["status"], "first_contact_review")

    def test_se_lite_diffuser_purchase_excludes_but_other_accessories_do_not(self):
        for sku, expected in (("CP34510", "excluded"), ("CP34520", "first_contact_review"),
                              ("CP34449", "first_contact_review"), ("CP34473", "first_contact_review"),
                              ("CQ15839", "first_contact_review")):
            with self.subTest(sku=sku):
                snapshot = customer(purchase(sku="CL50959"), purchase("EXTRA", sku))
                self.assertEqual(evaluate(snapshot, "2026-09-23", SE_LITE_RULE)["status"], expected)

    def test_neo_does_not_trigger_se_lite_rule(self):
        self.assertEqual(evaluate(customer(purchase()), "2026-09-23", SE_LITE_RULE)["status"], "no_action")

    def test_se_lite_earliest_valid_purchase_and_invalid_orders(self):
        snapshot = customer(purchase("OLD", "CL50959", "2020-01-01"),
                            purchase("NEW", "CQ62986", "2026-09-20"))
        self.assertEqual(evaluate(snapshot, "2026-09-23", SE_LITE_RULE)["source_purchase_id"], "OLD")
        for validity in ("cancelled", "returned"):
            with self.subTest(validity=validity):
                snapshot = customer(purchase(sku="CQ62986", validity=validity))
                self.assertEqual(evaluate(snapshot, "2026-09-23", SE_LITE_RULE)["status"], "no_action")

    def test_two_real_opportunities_have_independent_followups(self):
        snapshot = customer(purchase(day="2026-01-01"), purchase("SE", "CL50959", "2026-01-01"))
        snapshot["events"] = [event("NEO_REFUSAL", "rejection"),
                              event("SE_CONTACT", rule_id=SE_LITE_RULE)]
        self.assertEqual(evaluate(snapshot, "2026-09-23")["status"], "stopped")
        self.assertEqual(evaluate(snapshot, "2026-09-22", SE_LITE_RULE)["status"], "deferred")
        self.assertEqual(evaluate(snapshot, "2026-09-23", SE_LITE_RULE)["status"], "second_contact_review")
        snapshot["events"].append(event("SE_CONTACT_2", day="2026-09-23", rule_id=SE_LITE_RULE))
        self.assertEqual(evaluate(snapshot, "2027-01-01", SE_LITE_RULE)["status"], "stopped")

    def test_se_lite_reply_rejection_or_purchase_stops_retry(self):
        snapshot = customer(purchase(sku="CQ62986", day="2026-01-01"))
        for kind, expected in (("reply", "operator_response"), ("rejection", "stopped")):
            with self.subTest(kind=kind):
                snapshot["events"] = [event("FIRST", rule_id=SE_LITE_RULE),
                                      event("RESPONSE", kind, rule_id=SE_LITE_RULE)]
                self.assertEqual(evaluate(snapshot, "2026-09-23", SE_LITE_RULE)["status"], expected)
        snapshot["events"] = [event("FIRST", rule_id=SE_LITE_RULE)]
        snapshot["purchases"].append(purchase("DIFFUSER", "CP34510", "2026-09-20"))
        self.assertEqual(evaluate(snapshot, "2026-09-23", SE_LITE_RULE)["status"], "excluded")

    def test_unknown_rule_fails_explicitly(self):
        with self.assertRaises(ValueError):
            evaluate(customer(purchase()), "2026-09-23", "unknown_rule")

    def test_calendar_boundary_and_all_source_colors(self):
        for sku in ("CR05272", "CR05186", "CR05227"):
            with self.subTest(sku=sku):
                snapshot = customer(purchase(sku=sku, day="2026-09-08"))
                self.assertEqual(evaluate(snapshot, "2026-09-22")["status"], "deferred")
                result = evaluate(snapshot, "2026-09-23")
                self.assertEqual(result["status"], "first_contact_review")
                self.assertEqual(result["days_since_purchase"], 15)
                self.assertEqual(result["nominal_value_minor"], 2499)
                self.assertTrue(result["operator_checks"])

    def test_old_purchase_has_no_expiry(self):
        self.assertEqual(evaluate(customer(purchase(day="2022-01-01")), "2026-09-23")["status"],
                         "first_contact_review")

    def test_first_valid_purchase_and_one_stable_opportunity(self):
        old = purchase("OLD", day="2026-01-01")
        recent = purchase("RECENT", day="2026-09-20")
        result = evaluate(customer(recent, old), "2026-09-23")
        self.assertEqual(result["source_purchase_id"], "OLD")
        self.assertEqual(result["opportunity_key"], ["SYNTHETIC_001", RULE])
        self.assertEqual(result, evaluate(customer(old, recent, old), "2026-09-23"))

    def test_cancelled_and_returned_source_do_not_qualify(self):
        for validity in ("cancelled", "returned"):
            with self.subTest(validity=validity):
                self.assertEqual(evaluate(customer(purchase(validity=validity)), "2026-09-23")["status"],
                                 "no_action")

    def test_invalid_old_source_uses_recent_valid_purchase(self):
        result = evaluate(customer(purchase("OLD", day="2020-01-01", validity="cancelled"),
                                   purchase("NEW", day="2026-09-20")), "2026-09-23")
        self.assertEqual(result["status"], "deferred")
        self.assertEqual(result["source_purchase_id"], "NEW")

    def test_unknown_validity_requires_operator(self):
        result = evaluate(customer(purchase(validity="unknown")), "2026-09-23")
        self.assertEqual(result["status"], "first_contact_review")
        self.assertTrue(any("annullamenti" in check for check in result["operator_checks"]))

    def test_target_or_included_target_excludes_all_colors(self):
        for sku in ("CP34473", "CQ15839", "CQ15841", "CQ15840"):
            with self.subTest(sku=sku):
                snapshot = customer(purchase(), purchase("TARGET", sku, "2026-09-20"))
                self.assertEqual(evaluate(snapshot, "2026-09-23")["status"], "excluded")

    def test_cancelled_target_is_not_ownership(self):
        snapshot = customer(purchase(), purchase("TARGET", "CP34473", validity="cancelled"))
        self.assertEqual(evaluate(snapshot, "2026-09-23")["status"], "first_contact_review")

    def test_three_nozzles_alone_does_not_create_completion(self):
        self.assertEqual(evaluate(customer(purchase(sku="CQ15839")), "2026-09-23")["status"], "excluded")

    def test_unknown_sku_and_incomplete_history_are_flagged(self):
        snapshot = customer(purchase(), purchase("UNKNOWN", "UNMAPPED"))
        snapshot["history_complete"] = False
        snapshot["contact_history_complete"] = False
        result = evaluate(snapshot, "2026-09-23")
        self.assertEqual(result["status"], "first_contact_review")
        self.assertTrue(any("SKU non mappati" in check for check in result["operator_checks"]))
        self.assertTrue(any("Storico acquisti incompleto" in check for check in result["operator_checks"]))
        self.assertTrue(any("Storico contatti incompleto" in check for check in result["operator_checks"]))

    def test_no_known_source_with_missing_history_is_insufficient(self):
        snapshot = customer()
        snapshot["history_complete"] = False
        self.assertEqual(evaluate(snapshot, "2026-09-23")["status"], "insufficient_data")
        self.assertEqual(evaluate(customer(), "2026-09-23")["status"], "no_action")

    def test_missing_source_date_is_insufficient(self):
        self.assertEqual(evaluate(customer(purchase(day=None)), "2026-09-23")["status"], "insufficient_data")

    def test_second_contact_at_fifteen_days_not_fourteen(self):
        snapshot = customer(purchase(day="2026-01-01"))
        snapshot["events"] = [event("CONTACT_1")]
        before = evaluate(snapshot, "2026-09-22")
        self.assertEqual(before["status"], "deferred")
        self.assertEqual(before["next_contact_date"], "2026-09-23")
        self.assertEqual(evaluate(snapshot, "2026-09-23")["status"], "second_contact_review")

    def test_stop_after_second_contact_even_much_later(self):
        snapshot = customer(purchase(day="2026-01-01"))
        snapshot["events"] = [event("CONTACT_1"), event("CONTACT_2", day="2026-09-23")]
        self.assertEqual(evaluate(snapshot, "2027-09-23")["status"], "stopped")

    def test_purchase_stops_retry_and_remains_observed_after_two_contacts(self):
        snapshot = customer(purchase(day="2026-01-01"), purchase("TARGET", "CP34473", "2026-09-25"))
        snapshot["events"] = [event("CONTACT_1"), event("CONTACT_2", day="2026-09-23")]
        result = evaluate(snapshot, "2026-09-26")
        self.assertEqual(result["status"], "excluded")
        self.assertTrue(any(e["id"] == "TARGET" for e in result["evidence"]))
        self.assertNotIn("attributed_revenue", result)

    def test_reply_and_rejection_stop_scheduled_retry(self):
        for kind, status in (("reply", "operator_response"), ("rejection", "stopped")):
            with self.subTest(kind=kind):
                snapshot = customer(purchase(day="2026-01-01"))
                snapshot["events"] = [event("CONTACT_1"), event("RESPONSE", kind, "2026-09-10")]
                self.assertEqual(evaluate(snapshot, "2026-09-23")["status"], status)

    def test_single_rule_evaluation_does_not_consume_other_opportunity_attempts(self):
        snapshot = customer(purchase())
        snapshot["events"] = [event("OTHER_1", rule_id="other_rule"),
                              event("OTHER_2", "rejection", rule_id="other_rule")]
        result = evaluate(snapshot, "2026-09-23")
        self.assertEqual(result["status"], "first_contact_review")
        self.assertEqual(result["contact_count"], 0)

    def test_general_do_not_contact_stops(self):
        snapshot = customer(purchase())
        snapshot["do_not_contact"] = True
        self.assertEqual(evaluate(snapshot, "2026-09-23")["status"], "stopped")

    def test_duplicate_event_does_not_consume_second_attempt(self):
        snapshot = customer(purchase(day="2026-01-01"))
        snapshot["events"] = [event("CONTACT_1"), event("CONTACT_1")]
        result = evaluate(snapshot, "2026-09-23")
        self.assertEqual(result["status"], "second_contact_review")
        self.assertEqual(result["contact_count"], 1)

    def test_conflicting_duplicate_id_is_error(self):
        with self.assertRaises(ValueError):
            evaluate(customer(purchase(), purchase(sku="CQ15839")), "2026-09-23")

    def test_future_purchase_and_events_not_used(self):
        snapshot = customer(purchase(), purchase("FUTURE", "CP34473", "2026-10-01"))
        snapshot["events"] = [event("FUTURE", "rejection", "2026-10-01")]
        self.assertEqual(evaluate(snapshot, "2026-09-23")["status"], "first_contact_review")

    def test_bad_date_and_validity_rejected(self):
        for row in (purchase(day="2026-02-30"), purchase(day="2026-09-01T12:00:00"),
                    purchase(validity="paid")):
            with self.subTest(row=row), self.assertRaises(ValueError):
                evaluate(customer(row), "2026-09-23")

    def test_reproducible_and_input_not_mutated(self):
        snapshot = customer(purchase())
        original = copy.deepcopy(snapshot)
        self.assertEqual(evaluate(snapshot, "2026-09-23"), evaluate(snapshot, "2026-09-23"))
        self.assertEqual(snapshot, original)

    def test_cli_from_another_directory_with_synthetic_input(self):
        script = Path(__file__).resolve().parents[1] / "src" / "engine.py"
        with tempfile.TemporaryDirectory() as folder:
            input_file = Path(folder) / "customer.json"
            input_file.write_text(json.dumps(customer(purchase())), encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, "-B", str(script), str(input_file), "--as-of", "2026-09-23"],
                cwd=folder, capture_output=True, check=True,
            )
            result = json.loads(completed.stdout)
            self.assertEqual(result["status"], "first_contact_review")
            self.assertEqual(result["rule_version"], 6)
            input_file.write_text(json.dumps(customer(purchase(sku="CQ62986"))), encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, "-B", str(script), str(input_file), "--as-of", "2026-09-23", "--rule", SE_LITE_RULE],
                cwd=folder, capture_output=True, check=True,
            )
            result = json.loads(completed.stdout)
            self.assertEqual(result["status"], "first_contact_review")
            self.assertEqual(result["rule_id"], SE_LITE_RULE)
            completed = subprocess.run(
                [sys.executable, "-B", str(script), str(input_file), "--as-of", "2026-09-23", "--portfolio"],
                cwd=folder, capture_output=True, check=True,
            )
            result = json.loads(completed.stdout)
            self.assertEqual(
                result["primary_contact_plan"]["primary_opportunity"]["rule_id"],
                SE_LITE_RULE,
            )
            completed = subprocess.run(
                [sys.executable, "-B", str(script), str(input_file), "--as-of", "2026-09-23", "--operator-view"],
                cwd=folder, capture_output=True, check=True,
            )
            view = completed.stdout.decode("utf-8")
            self.assertIn("| Dal | Stato | Prossimo contatto |", view)
            self.assertIn("Consenso: subscribed", view)
            self.assertIn("AutoCurl", view)
            self.assertIn("Attendere la chiusura del piano accessori", view)
            self.assertEqual(list(Path(folder).iterdir()), [input_file])


if __name__ == "__main__":
    unittest.main()
