"""Raggruppa gli ordini importati per email, separando recapiti e acquisti."""

import argparse
from calendar import monthrange
from copy import deepcopy
from datetime import date, datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo

from src.engine import commercial_category, evaluate_portfolio
from src.shopify_orders import import_orders, sanitize_local_data
from src.storage import Store


def merge_orders(state, imported):
    """Aggiorna uno stato in memoria usando ID ordine ed email normalizzata."""
    result = deepcopy(state) if state is not None else {
        "profiles": {}, "contacts": {}, "unassigned_orders": {},
    }
    profiles = result["profiles"]
    contacts = result["contacts"]
    unassigned = result["unassigned_orders"]
    email_to_id = {contact["email"]: profile_id for profile_id, contact in contacts.items()}
    order_owners = {
        order_id: profile_id
        for profile_id, profile in profiles.items()
        for order_id in profile["orders"]
    }
    for order in imported["orders"]:
        order_id = order["id"]
        contact = imported["order_contacts"].get(order_id)
        email = contact["email"] if contact else None
        owner = order_owners.get(order_id)
        if owner and email and contacts[owner]["email"] != email:
            raise ValueError("Lo stesso ordine è associato a email diverse tra importazioni.")
        if owner is None and email:
            owner = email_to_id.get(email)
            if owner is None:
                owner = f"CUST_{len(profiles) + 1:06d}"
                email_to_id[email] = owner
                contacts[owner] = {"email": email}
                profiles[owner] = {"customer_id": owner, "orders": {}}
            order_owners[order_id] = owner
        if owner:
            profiles[owner]["orders"][order_id] = order
            unassigned.pop(order_id, None)
        else:
            unassigned[order_id] = order
    return result


def merge_csv_exports(paths, state=None):
    """Importa più export ordini nell'ordine indicato, deduplicando per ID ordine."""
    current = state
    for path in paths:
        current = merge_orders(current, import_orders(path))
    return current


def engine_snapshot(state, customer_id, as_of, *, history_complete=False,
                    contact_history_complete=False, events=()):
    """Prepara gli acquisti e il consenso email per il motore, senza recapiti."""
    profile = state["profiles"][customer_id]
    orders = sorted((order for order in profile["orders"].values()
                     if order["date"] <= as_of),
                    key=lambda order: (order["date"], order["id"]))
    signals = {order["marketing_signal"] for order in orders}
    consent = ({"yes": "subscribed", "no": "unsubscribed"}.get(next(iter(signals)))
               if len(signals) == 1 else None) or "unknown"
    return {
        "customer_id": customer_id,
        "history_complete": history_complete,
        "contact_history_complete": contact_history_complete,
        "contact_channel": "email",
        "marketing_consent": {"email": {"status": consent}},
        "purchases": [line for order in orders for line in order["lines"]],
        "events": list(events),
    }


def customer_signals(state, customer_id, as_of, *, catalog=None, definitions=None):
    """Descrive il profilo osservato; non decide proposte né autorizza contatti."""
    today = date.fromisoformat(as_of)
    if catalog is None or definitions is None:
        root = Path(__file__).resolve().parent
    if catalog is None:
        catalog = json.loads((root / "catalog.json").read_text(encoding="utf-8"))
    if definitions is None:
        definitions = json.loads((root / "rules.json").read_text(encoding="utf-8"))
    policy = definitions["customer_signals"]
    orders = [order for order in state["profiles"][customer_id]["orders"].values()
              if order["date"] <= as_of]
    valid_orders = [order for order in orders if order["lines"]
                    and all(line.get("validity") == "valid" for line in order["lines"])]
    start = today - timedelta(days=policy["recent_activity_calendar_days"] - 1)
    recent = [order for order in valid_orders if order["date"] >= start.isoformat()]
    categories_by_sku = {variant["sku"]: policy["main_categories"].get(product["category"])
                         for product in catalog["products"] for variant in product["variants"]}
    categories = sorted({categories_by_sku[line["sku"]] for order in orders
                         for line in order["lines"] if line.get("validity") == "valid"
                         and categories_by_sku.get(line["sku"])})
    signals = []
    if len(valid_orders) == policy["first_purchase_order_count"]:
        signals.append({"key": "first_purchase", "label": "Primo acquisto"})
    if len(valid_orders) >= policy["recurring_minimum_orders"]:
        signals.append({"key": "recurring", "label": "Cliente ricorrente"})
    if len(recent) >= policy["recent_activity_minimum_orders"]:
        signals.append({"key": "recent_activity", "label": "Alta attività recente"})
    if len(categories) >= policy["multicategory_minimum_categories"]:
        signals.append({"key": "multicategory", "label": "Multicategoria"})
    return {"signals": signals, "valid_orders": len(valid_orders),
            "recent_valid_orders": len(recent), "recent_starts_on": start.isoformat(),
            "main_categories": categories,
            "uncertain_orders": sum(any(line.get("validity", "unknown") == "unknown"
                                        for line in order["lines"]) for order in orders),
            "rules_version": definitions["version"], "history_scope": "imported_orders_only",
            "unavailable_signals": [
                {"key": "possible_b2b", "label": "Possibile B2B",
                 "reason": "Mancano dati aziendali e criteri approvati per l’uso professionale."},
                {"key": "high_historical_value", "label": "Alto valore storico",
                 "reason": "Mancano importi netti effettivi e criteri per calcolare il top 20%."}]}


def review_cases(state, as_of):
    """Elenca separatamente gli ordini non attribuiti o con righe incerte."""
    catalog = json.loads((Path(__file__).resolve().parent / "catalog.json").read_text(encoding="utf-8"))
    known_skus = {variant["sku"] for product in catalog["products"]
                  for variant in product["variants"]}
    cases = [{"order_id": order_id, "reason": "missing_email"}
             for order_id, order in state["unassigned_orders"].items() if order["date"] <= as_of]
    cases.extend(
        {"customer_id": customer_id, "order_id": order["id"], "reason": "uncertain_purchase"}
        for customer_id, profile in state["profiles"].items()
        for order in profile["orders"].values()
        if order["date"] <= as_of and any(line["validity"] == "unknown" for line in order["lines"])
    )
    cases.extend(
        {"customer_id": customer_id, "order_id": order["id"], "reason": "unmapped_sku"}
        for customer_id, profile in state["profiles"].items()
        for order in profile["orders"].values()
        if order["date"] <= as_of and any(line["sku"] not in known_skus for line in order["lines"])
    )
    cases.extend(
        {"customer_id": customer_id, "reason": "uncertain_email_consent"}
        for customer_id in state["profiles"]
        if engine_snapshot(state, customer_id, as_of)["marketing_consent"]["email"]["status"] == "unknown"
    )
    return sorted(cases, key=lambda case: (case.get("order_id", ""), case.get("customer_id", ""),
                                          case["reason"]))


def import_into_store(store, paths):
    """Applica tutti i file e salva solo se l'intera importazione riesce."""
    receipts = [(Path(path).name, hashlib.sha256(Path(path).read_bytes()).hexdigest())
                for path in paths]
    updated = merge_csv_exports(paths, store.load_state())
    if receipts != [(Path(path).name, hashlib.sha256(Path(path).read_bytes()).hexdigest())
                    for path in paths]:
        raise ValueError("Un CSV è cambiato durante l'importazione.")
    store.save_state(updated, receipts)
    return updated


def sync_local_data(store, directory, *, watch=False):
    """Pulisce e importa i CSV locali non ancora acquisiti, anche in sorveglianza."""
    def import_ready(path):
        receipt = (path.name, hashlib.sha256(path.read_bytes()).hexdigest())
        if receipt in {(item["filename"], item["sha256"])
                        for item in store.import_history()}:
            return None
        import_into_store(store, [path])
        return "CSV importato"

    return sanitize_local_data(directory, watch=watch, on_ready=import_ready)


def activate_history(store, day):
    """Dichiara concluso l'import storico e avvia il conteggio dei contatti."""
    date.fromisoformat(day)
    if not store.load_state()["profiles"]:
        raise ValueError("Importare almeno un profilo prima dell'attivazione.")
    store.activate(day)


def evaluate_day(store, as_of):
    """Rende visibili solo i piani certi e maturi; restituisce i casi da verificare."""
    date.fromisoformat(as_of)
    state = store.load_state()
    review = review_cases(state, as_of)
    activation = store.activation_date()
    if not activation or as_of < activation:
        return {"date": as_of, "active": False, "ready": [], "review": review}
    uncertain_ids = {case["customer_id"] for case in review if "customer_id" in case}
    root = Path(__file__).resolve().parent
    catalog = json.loads((root / "catalog.json").read_text(encoding="utf-8"))
    definitions = json.loads((root / "rules.json").read_text(encoding="utf-8"))
    promotions = json.loads((root / "promotions.json").read_text(encoding="utf-8"))
    ready = []
    event_history = store.events_by_customer()
    for customer_id in sorted(state["profiles"]):
        if customer_id in uncertain_ids:
            continue
        snapshot = engine_snapshot(
            state, customer_id, as_of, history_complete=True,
            contact_history_complete=True, events=event_history.get(customer_id, []),
        )
        result = evaluate_portfolio(snapshot, as_of, catalog=catalog, definitions=definitions,
                                    promotions=promotions)
        plan = _workable_plan(result, as_of)
        if not plan:
            continue
        ready.append({"customer_id": customer_id, "plan": plan,
                      "reason": plan["plan_reason"]})
    return {"date": as_of, "active": True, "ready": ready, "review": review}


def _workable_plan(portfolio, as_of):
    plan = portfolio["primary_contact_plan"]
    if (portfolio["portfolio_status"] == "contact_review" and plan
            and plan["raw_status"] in {"first_contact_review", "second_contact_review"}
            and not plan["blocking_plan_keys"]
            and plan["earliest_contact_date"] <= as_of):
        return plan
    return None


def explain_order(store, customer_id, order_id, as_of):
    """Espone per un ordine le decisioni del motore, senza recapiti."""
    date.fromisoformat(as_of)
    state = store.load_state()
    profile = state["profiles"].get(customer_id)
    if not profile or order_id not in profile["orders"]:
        raise ValueError("Ordine non presente nel profilo indicato.")
    order = profile["orders"][order_id]
    if order["date"] > as_of:
        raise ValueError("L'ordine è successivo alla data di valutazione.")

    catalog = json.loads((Path(__file__).resolve().parent / "catalog.json").read_text(encoding="utf-8"))
    products = {variant["sku"]: product["name"] for product in catalog["products"]
                for variant in product["variants"]}
    summary = {
        "customer_id": customer_id,
        "evaluation_date": as_of,
        "history_scope": "imported_orders_only",
        "observed_order_count": sum(item["date"] <= as_of for item in profile["orders"].values()),
        "marketing_consent_status": engine_snapshot(state, customer_id, as_of)[
            "marketing_consent"]["email"]["status"],
        "order": {"id": order_id, "number": order["number"], "date": order["date"],
                  "items": [{"product_name": products.get(line["sku"]), "sku": line["sku"],
                             "quantity": line["quantity"], "validity": line["validity"]}
                            for line in order["lines"]]},
        "review_reasons": sorted({case["reason"] for case in review_cases(state, as_of)
                                  if case.get("customer_id") == customer_id}),
        "purchase_probability": None,
        "contact_permission": None,
        "customer_status": None,
        "customer_primary_order_id": None,
        "current_plan": None,
        "other_plans": [],
        "exclusions": [],
    }
    if summary["review_reasons"]:
        summary["customer_status"] = "review"
        return summary
    activation = store.activation_date()
    if not activation or as_of < activation:
        summary["customer_status"] = "inactive"
        return summary

    snapshot = engine_snapshot(state, customer_id, as_of, history_complete=True,
                               contact_history_complete=True,
                               events=store.events_for(customer_id))
    portfolio = evaluate_portfolio(snapshot, as_of)
    summary["contact_permission"] = portfolio["contact_permission"]
    summary["customer_status"] = portfolio["portfolio_status"]
    if portfolio["primary_contact_plan"]:
        summary["customer_primary_order_id"] = portfolio[
            "primary_contact_plan"]["source_order_id"]
    workable = _workable_plan(portfolio, as_of)

    def brief_opportunity(opportunity):
        return {"rule_id": opportunity["rule_id"],
                "product_name": products[opportunity["target_sku"]],
                "target_sku": opportunity["target_sku"],
                "rationale": opportunity["rationale"],
                "reason": opportunity["reason"],
                "nominal_value_minor": opportunity["nominal_value_minor"],
                "currency": opportunity["currency"],
                "price_basis": opportunity["price_basis"],
                "promotion_active": opportunity["promotion_active"],
                "operator_checks": opportunity["operator_checks"]}

    for plan in [portfolio["primary_contact_plan"], *portfolio["queued_contact_plans"]]:
        if not plan or plan["source_order_id"] != order_id:
            continue
        item = {
            "plan_key": plan["plan_key"],
            "status": plan["plan_status"],
            "reason": plan["plan_reason"],
            "eligible_from_date": plan["eligible_from_date"],
            "next_contact_date": plan["plan_next_contact_date"],
            "contact_count": plan["contact_count"],
            "blocking_plan_keys": plan["blocking_plan_keys"],
            "primary": brief_opportunity(plan["primary_opportunity"]),
            "primary_selection_reason": plan.get("presentation", {}).get(
                "primary_selection_reason", plan["primary_opportunity"]["plan_rank_reason"]),
            "presentation": plan.get("presentation"),
            "alternatives": [brief_opportunity(opportunity)
                             for opportunity in plan["secondary_opportunities"]],
            "other_available_options": [brief_opportunity(opportunity)
                                        for opportunity in plan["other_available_opportunities"]],
            "workable_now": plan is workable,
        }
        if plan is portfolio["primary_contact_plan"]:
            summary["current_plan"] = item
        else:
            summary["other_plans"].append(item)
    summary["exclusions"] = [
        {"rule_id": result["rule_id"], "status": result["status"],
         "reason": result.get("coordination_reason", result["reason"])}
        for result in [*portfolio["other_results"], *portfolio["suppressed_opportunities"]]
        if result.get("source_order_id") == order_id
        and result["status"] in {"excluded", "stopped"}
    ]
    return summary


def _offered_skus(contacts):
    """SKU delle proposte registrate nei contatti del piano."""
    offered_rules = {key[1] for contact in contacts for key in contact["included_opportunity_keys"]}
    definitions = json.loads((Path(__file__).resolve().parent / "rules.json").read_text(encoding="utf-8"))
    catalog = json.loads((Path(__file__).resolve().parent / "catalog.json").read_text(encoding="utf-8"))
    return {sku for rule in definitions["rules"] if rule["id"] in offered_rules
            for sku in (rule.get("target_skus") or ([rule["target_sku"]] if "target_sku" in rule else
                [variant["sku"] for product in catalog["products"] if product["key"] == rule["target_product"]
                 for variant in product["variants"]]))}


def _product_images(catalog):
    """L'immagine della variante prevale sulla foto rappresentativa del prodotto."""
    return {variant["sku"]: variant.get("image") or product["image"]
            for product in catalog["products"] for variant in product["variants"]
            if variant.get("image") or product.get("image")}


def _proposal_presentation(opportunity, rule, variants, as_of, uncertain=False):
    """Motivi sintetici dai fatti del motore; non rivaluta l'idoneità."""
    source = next((item for item in opportunity["evidence"]
                   if item["kind"] == "source_purchase"
                   and item["id"] == opportunity.get("source_purchase_id")), None)
    reasons = []
    description = opportunity["rationale"]
    if uncertain or opportunity["status"] == "insufficient_data":
        reasons.append({"label": "Dati da verificare", "detail": opportunity["reason"],
                        "icon": "document", "tone": "neutral"})
    elif (rule["relationship_type"] == "ACCESSORY_COMPLETION" and source
          and source.get("validity") == "valid"
          and rule.get("evidence", {}).get("compatibility")
          and rule.get("exclusions", {}).get("target_component_in_known_purchased_configuration")):
        name = variants[source["sku"]]["product_name"]
        reasons.extend([
            {"label": "Compatibile", "detail": name, "icon": "check", "tone": "green"},
            {"label": "Non incluso", "detail": "nella configurazione acquistata",
             "icon": "document", "tone": "blue"},
        ])
        description = f"Accessorio compatibile con {name}, non incluso nella configurazione acquistata."
    else:
        labels = {"USE_CASE_COMPLEMENT": "Complemento d’uso", "CATEGORY_EXPANSION": "Nuova categoria",
                  "REPLENISHMENT": "Ricambio previsto", "REPLACEMENT": "Sostituzione prevista"}
        reasons.append({"label": labels.get(rule["relationship_type"], "Proposta del piano"),
                        "detail": opportunity["benefit"], "icon": "document", "tone": "blue"})
    eligible = opportunity.get("eligible_from_date")
    if eligible:
        reasons.append({"label": "Timing maturo" if eligible <= as_of else "Timing futuro",
                        "date": eligible, "icon": "clock", "tone": "blue"})
    return {"description": description, "reasons": reasons}


def plan_detail(store, customer_id, plan_key, as_of):
    """Dettaglio operativo: decisione corrente, storico e modelli degli eventi manuali."""
    state = store.load_state()
    if customer_id not in state["profiles"] or (plan_key is not None and not isinstance(plan_key, list)):
        raise ValueError("Cliente o piano sconosciuto.")
    date.fromisoformat(as_of)
    events = store.events_for(customer_id)
    snapshot = engine_snapshot(state, customer_id, as_of,
        history_complete=True, contact_history_complete=True, events=events)
    portfolio = evaluate_portfolio(snapshot, as_of)
    if plan_key is None and portfolio["primary_contact_plan"]:
        plan_key = portfolio["primary_contact_plan"]["plan_key"]
    current = next((plan for plan in [portfolio["primary_contact_plan"], *portfolio["queued_contact_plans"]]
                    if plan and plan["plan_key"] == plan_key), None)
    history = [event for event in events if event.get("plan_key") == plan_key and event["date"] <= as_of]
    contacts = [event for event in history if event["type"] == "contact"]
    if plan_key is not None and not current and not contacts:
        raise ValueError("Piano non presente nel profilo indicato.")
    root = Path(__file__).resolve().parent
    catalog = json.loads((root / "catalog.json").read_text(encoding="utf-8"))
    definitions = json.loads((root / "rules.json").read_text(encoding="utf-8"))
    variants = {variant["sku"]: {"sku": variant["sku"], "product_key": product["key"], "product_name": product["name"],
                "label": product["name"] + " · " + variant["sku"],
                "color": variant.get("color"),
                "configuration": next((item["label"] for item in product.get("configurations", [])
                                       if item["key"] == variant.get("configuration")), None)}
                for product in catalog["products"] for variant in product["variants"]}
    contact_options = []
    products = {}
    for contact in contacts:
        skus = sorted(_offered_skus([contact]))
        options = [variants[sku] for sku in skus]
        contact_options.append({"id": contact["id"], "date": contact["date"], "products": options,
                                "proposal_names": list(dict.fromkeys(item["product_name"] for item in options))})
        products.update({item["product_key"]: {"key": item["product_key"],
                         "label": item["product_name"]}
                         for item in options})
    templates = {}
    base = {"date": as_of, "plan_key": plan_key}
    activation = store.activation_date()
    review_reasons = sorted({case["reason"] for case in review_cases(state, as_of)
                             if case.get("customer_id") == customer_id})
    uncertain = bool(review_reasons)
    workable = _workable_plan(portfolio, as_of) if activation and activation <= as_of and not uncertain else None
    if workable and workable["plan_key"] == plan_key:
        templates["contact"] = {**base, "type": "contact", "channel": "email",
            "rule_id": workable["primary_opportunity"]["rule_id"],
            "primary_opportunity_key": workable["primary_opportunity"]["opportunity_key"],
            "included_opportunity_keys": workable["included_opportunity_keys"]}
        reference = workable["primary_opportunity"].get("cycle_reference_purchase_id")
        if reference:
            templates["contact"]["cycle_reference_purchase_id"] = reference
    if contacts:
        for kind in ("reply", "product_interest", "product_rejection", "plan_rejection", "conversation_closed"):
            templates[kind] = {**base, "type": kind}
        templates["reply"]["rule_id"] = contacts[-1]["rule_id"]
        if contacts[-1].get("cycle_reference_purchase_id"):
            templates["reply"]["cycle_reference_purchase_id"] = contacts[-1]["cycle_reference_purchase_id"]
        templates["verified_purchase"] = {**base, "type": "verified_purchase", "currency": "EUR"}
    sales = [event for event in history if event["type"] == "verified_purchase"]
    if sales:
        templates["revenue_correction"] = {**base, "type": "revenue_correction", "currency": "EUR"}
    order = state["profiles"][customer_id]["orders"].get(plan_key[0]) if plan_key else None
    purchases = []
    orders = state["profiles"][customer_id]["orders"]
    for purchase_order in sorted(orders.values(), key=lambda item: (item["date"], item["id"]), reverse=True):
        if purchase_order["date"] > as_of:
            continue
        for line in purchase_order["lines"]:
            purchases.append({"order_id": purchase_order["id"], "order_number": purchase_order["number"],
                              **line, **variants.get(line["sku"], {"product_name": line["sku"]})})
    tracked = next((item for item in portfolio["contacted_plans"] if item["plan_key"] == plan_key), None)
    visible_events = []
    for event in events:
        if event["date"] > as_of:
            continue
        item = dict(event)
        if event["type"] == "contact":
            item["proposal_names"] = list(dict.fromkeys(
                variants[sku]["product_name"] for sku in sorted(_offered_skus([event]))))
        if event.get("product_key"):
            item["product_name"] = next((product["name"] for product in catalog["products"]
                                         if product["key"] == event["product_key"]), event["product_key"])
        visible_events.append(item)
    names = {sku: item["product_name"] for sku, item in variants.items()}
    rules = {rule["id"]: rule for rule in definitions["rules"]}
    source = _plan_row(state, customer_id, current, date.fromisoformat(as_of), names, rules) if current else None
    source_purchase = next((item for item in purchases if current and item["id"] == current[
        "primary_opportunity"].get("cycle_reference_purchase_id", current["primary_opportunity"]["source_purchase_id"])), None)
    return {"customer_id": customer_id, "plan_key": plan_key, "date": as_of,
            "product_images": _product_images(catalog),
            "customer_profile": customer_signals(state, customer_id, as_of,
                                                 catalog=catalog, definitions=definitions),
            "minimum_event_date": activation, "order_number": order["number"] if order else None,
            "contact_email": store.contact_email(customer_id),
            "reason": current["plan_reason"] if current else (
                "Piano concluso; storico disponibile." if contacts else "Nessuna proposta attiva; storico disponibile."),
            "proposals": [{"name": variants[item["target_sku"]]["product_name"], "sku": item["target_sku"],
                           "role": item["contact_role"], "rationale": item["rationale"],
                           "commercial_category": item["commercial_category"],
                           "value_minor": item["nominal_value_minor"], "operator_checks": item["operator_checks"],
                           "benefit": item["benefit"],
                           **_proposal_presentation(item, rules[item["rule_id"]], variants, as_of, uncertain),
                           "promotion_active": item["promotion_active"], "options": item.get("target_options", [])}
                          for item in [current["primary_opportunity"], *current["secondary_opportunities"]]] if current else [],
            "presentation": current.get("presentation") if current else None,
            "source": source, "source_purchase": source_purchase,
            "current_plan": {key: current[key] for key in ("raw_status", "contact_count", "plan_next_contact_date")} if current else None,
            "tracked_plan": {key: tracked[key] for key in ("state", "outcome", "contact_count", "last_contact_date")} if tracked else None,
            "contact_permission": portfolio["contact_permission"],
            "review_reasons": review_reasons,
            "active": bool(activation and activation <= as_of),
            "maximum_contacts": definitions["shared_policies"]["follow_up"]["maximum_contacts"],
            "purchases": purchases, "customer_events": visible_events,
            "operator_timeline": [{**item, "order_number": orders[item["plan_key"][0]]["number"]}
                                  for item in portfolio["operator_timeline"]],
            "history_scope": "imported_orders_only",
            "attributed_revenue_minor": sum(sale["amount_minor"] for owner, sale in _verified_sales(store, as_of).values()
                                             if owner == customer_id and sale["plan_key"] == plan_key),
            "events": history, "contacts": contact_options, "products": list(products.values()),
            "sales": [{"id": sale["id"], "order_id": sale["shopify_order_id"]} for sale in sales],
            "event_templates": templates}


def record_event(store, customer_id, event):
    """Registra un evento manuale senza duplicarlo; verifica i contatti sul piano corrente."""
    if not isinstance(event, dict) or not isinstance(event.get("id"), str) or not event["id"]:
        raise ValueError("L'evento richiede un ID non vuoto.")
    existing = store.event_by_id(event["id"])
    if existing:
        if existing != (customer_id, event):
            raise ValueError("ID evento già presente con dati diversi.")
        return
    if customer_id not in store.load_state()["profiles"]:
        raise ValueError("Profilo sconosciuto.")
    try:
        day = date.fromisoformat(event["date"])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("L'evento richiede una data valida.") from error
    activation = store.activation_date()
    if not activation or day < date.fromisoformat(activation):
        raise ValueError("I contatti si registrano dalla data di attivazione.")
    kind = event.get("type")
    allowed = {"contact", "reply", "rejection", "product_interest",
               "product_rejection", "plan_rejection", "conversation_closed",
               "verified_purchase", "revenue_correction"}
    if kind not in allowed or not isinstance(event.get("plan_key"), list):
        raise ValueError("Tipo evento o plan_key non valido.")
    if kind in {"verified_purchase", "revenue_correction"}:
        _validate_revenue_event(store, customer_id, event, day)
    elif kind == "contact":
        if event.get("channel") != "email":
            raise ValueError("Il contatto deve indicare il canale email.")
        current = evaluate_day(store, event["date"])
        plan = next((item["plan"] for item in current["ready"]
                     if item["customer_id"] == customer_id
                     and item["plan"]["plan_key"] == event["plan_key"]), None)
        if not plan:
            raise ValueError("Il piano non è lavorabile per questo cliente e questa data.")
        if (event.get("rule_id") != plan["primary_opportunity"]["rule_id"]
                or event.get("primary_opportunity_key") != plan["primary_opportunity"]["opportunity_key"]
                or event.get("included_opportunity_keys") != plan["included_opportunity_keys"]):
            raise ValueError("L'evento di contatto non corrisponde al piano valutato.")
        reference = plan["primary_opportunity"].get("cycle_reference_purchase_id")
        if reference and event.get("cycle_reference_purchase_id") != reference:
            raise ValueError("Il contatto deve indicare l'acquisto che apre il ciclo di ricambio.")
    else:
        previous_contacts = [previous for previous in store.events_for(customer_id)
                             if previous.get("type") == "contact"
                             and previous.get("plan_key") == event["plan_key"]
                             and previous["date"] <= event["date"]]
        if not previous_contacts:
            raise ValueError("L'esito richiede un contatto precedente dello stesso piano.")
        if kind in {"reply", "rejection"} and event.get("rule_id") not in {
            previous["rule_id"] for previous in previous_contacts
        }:
            raise ValueError("L'esito richiede il rule_id del contatto.")
        if kind in {"reply", "rejection"}:
            reference = next((previous.get("cycle_reference_purchase_id") for previous in previous_contacts
                              if previous["rule_id"] == event["rule_id"]), None)
            if reference and event.get("cycle_reference_purchase_id") != reference:
                raise ValueError("L'esito deve indicare il ciclo di ricambio del contatto.")
        if kind.startswith("product_"):
            root = Path(__file__).resolve().parent
            offered_skus = _offered_skus(previous_contacts)
            catalog = json.loads((root / "catalog.json").read_text(encoding="utf-8"))
            offered_products = {product["key"] for product in catalog["products"]
                                if any(variant["sku"] in offered_skus for variant in product["variants"])}
            if event.get("product_key") not in offered_products:
                raise ValueError("L'esito prodotto richiede un prodotto presentato nello stesso piano.")
    store.add_event(customer_id, event)


def _validate_revenue_event(store, customer_id, event, day):
    if event.get("verified_in_shopify") is not True:
        raise ValueError("L'operatore deve confermare la verifica in Shopify.")
    amount = event.get("amount_minor")
    if type(amount) is not int or amount < 0 or event.get("currency") != "EUR":
        raise ValueError("Indicare un importo non negativo in centesimi di euro.")
    if event["type"] == "verified_purchase":
        order_id = event.get("shopify_order_id")
        if not isinstance(order_id, str) or not order_id.strip():
            raise ValueError("Indicare l'ID ordine Shopify verificato.")
        if store.verified_purchase_for_order(order_id):
            raise ValueError("Ordine Shopify già attribuito.")
        if not isinstance(event.get("contact_event_id"), str):
            raise ValueError("Indicare l'ID del contatto precedente.")
        contact = store.event_by_id(event.get("contact_event_id"))
        if (not contact or contact[0] != customer_id or contact[1].get("type") != "contact"
                or contact[1].get("plan_key") != event["plan_key"]):
            raise ValueError("La vendita richiede un contatto precedente dello stesso piano.")
        try:
            purchase_day = date.fromisoformat(event["purchase_date"])
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("Indicare una data di acquisto valida.") from error
        if not date.fromisoformat(contact[1]["date"]) <= purchase_day <= day:
            raise ValueError("L'acquisto deve seguire il contatto e precedere la verifica.")
        offered_skus = _offered_skus([contact[1]])
        if event.get("purchased_sku") not in offered_skus:
            raise ValueError("Il prodotto acquistato non appartiene alle proposte del contatto.")
    else:
        if not isinstance(event.get("reason"), str) or not event["reason"].strip():
            raise ValueError("La correzione richiede una motivazione.")
        if not isinstance(event.get("verified_purchase_event_id"), str):
            raise ValueError("Indicare l'ID della vendita attribuita.")
        original = store.event_by_id(event.get("verified_purchase_event_id"))
        if (not original or original[0] != customer_id
                or original[1].get("type") != "verified_purchase"
                or original[1].get("plan_key") != event["plan_key"]
                or day < date.fromisoformat(original[1]["date"])):
            raise ValueError("La correzione richiede una vendita attribuita precedente dello stesso piano.")


def _strategy(rule):
    return {"ACCESSORY_COMPLETION": ("completion", "Completamenti funzionali"),
            "USE_CASE_COMPLEMENT": ("complement", "Complementi d’uso"),
            "CATEGORY_EXPANSION": ("expansion", "Espansione di categoria"),
            "REPLENISHMENT": ("replenishment", "Ricambi"),
            "REPLACEMENT": ("replacement", "Sostituzioni / upgrade")}[rule["relationship_type"]]


def _plan_row(state, customer_id, plan, today, names, rules):
    """Presentazione comune dei piani nelle liste operative."""
    proposal = plan["primary_opportunity"]
    order = state["profiles"][customer_id]["orders"][plan["source_order_id"]]
    source_id = proposal.get("cycle_reference_purchase_id", proposal["source_purchase_id"])
    source = next(line for line in order["lines"] if line["id"] == source_id)
    rule = rules[proposal["rule_id"]]
    strategy, label = _strategy(rule)
    return {"customer_id": customer_id, "order_id": order["id"], "order_number": order["number"], "plan_key": plan["plan_key"],
            "source_product": names[source["sku"]], "source_date": source["date"],
            "elapsed_days": (today - date.fromisoformat(source["date"])).days,
            "proposal": names[proposal["target_sku"]], "target_sku": proposal["target_sku"],
            "alternatives_count": len(plan["secondary_opportunities"]),
            "reason": plan["plan_reason"], "rationale": proposal["rationale"],
            "eligible_from_date": plan["eligible_from_date"],
            "value_minor": proposal["nominal_value_minor"], "price_basis": proposal["price_basis"],
            "promotion_active": proposal["promotion_active"],
            "contact_count": plan["contact_count"],
            "strategy": strategy, "strategy_label": label,
            "commercial_category": proposal["commercial_category"]}


def retention_summary(store, as_of):
    """Liste dei piani lavorabili e dei contatti conservati: stati decisi dal motore."""
    today = date.fromisoformat(as_of)
    state = store.load_state()
    root = Path(__file__).resolve().parent
    catalog = json.loads((root / "catalog.json").read_text(encoding="utf-8"))
    definitions = json.loads((root / "rules.json").read_text(encoding="utf-8"))
    promotions = json.loads((root / "promotions.json").read_text(encoding="utf-8"))
    rules = {rule["id"]: rule for rule in definitions["rules"]}
    names = {variant["sku"]: product["name"] for product in catalog["products"] for variant in product["variants"]}
    reviews = review_cases(state, as_of)
    uncertain = {case["customer_id"] for case in reviews if "customer_id" in case}
    active = bool(store.activation_date() and as_of >= store.activation_date())
    sections = {"ready": [], "in_progress": [], "closed": []}
    operational_rows = []
    event_history = store.events_by_customer()
    sales = _verified_sales(store, as_of)
    for customer_id in sorted(state["profiles"]):
        if not any(order["date"] <= as_of for order in state["profiles"][customer_id]["orders"].values()):
            continue
        events = event_history.get(customer_id, [])
        profile = customer_signals(state, customer_id, as_of, catalog=catalog, definitions=definitions)
        portfolio = evaluate_portfolio(engine_snapshot(state, customer_id, as_of, history_complete=True,
                                       contact_history_complete=True, events=events), as_of,
                                       catalog=catalog, definitions=definitions, promotions=promotions)
        reasons = sorted({case["reason"] for case in reviews if case.get("customer_id") == customer_id})
        if portfolio["contact_permission"]["allowed"]:
            operational_rows.append(_operational_row(state, customer_id, as_of, profile, portfolio,
                                    active, reasons, names, rules, definitions))
        if not active or customer_id in uncertain:
            continue
        plan = _workable_plan(portfolio, as_of)
        if plan:
            row = _plan_row(state, customer_id, plan, today, names, rules)
            row.update(state="ready", status_label="Da contattare", tone="blue",
                       maximum_contacts=definitions["shared_policies"]["follow_up"]["maximum_contacts"],
                       customer_profile=profile)
            sections["ready"].append(row)
        for tracked in portfolio["contacted_plans"]:
            current = tracked["current_plan"]
            # Un secondo tentativo oggi lavorabile compare soltanto in Da contattare.
            if plan and plan["plan_key"] == tracked["plan_key"]:
                continue
            if current:
                row = _plan_row(state, customer_id, current, today, names, rules)
            else:
                # Nessun prezzo storico inventato: il contatto non conserva lo SKU scelto.
                order = state["profiles"][customer_id]["orders"].get(tracked["plan_key"][0])
                rule = rules[tracked["rule_id"]]
                strategy, label = _strategy(rule)
                targets = rule.get("target_skus") or ([rule["target_sku"]] if "target_sku" in rule else
                    [variant["sku"] for product in catalog["products"] if product["key"] == rule["target_product"] for variant in product["variants"]])
                row = {"customer_id": customer_id, "order_id": tracked["plan_key"][0],
                       "order_number": order["number"] if order else None,
                       "plan_key": tracked["plan_key"], "source_product": " · ".join(
                           dict.fromkeys(names.get(line["sku"], line["sku"]) for line in order["lines"])) if order else "Ordine storico",
                       "source_date": order["date"] if order else tracked["plan_key"][2],
                       "proposal": " / ".join(dict.fromkeys(names[sku] for sku in targets)), "value_minor": None,
                       "strategy": strategy, "strategy_label": label, "reason": "Piano chiuso",
                       "alternatives_count": 0, "price_basis": None, "promotion_active": False}
            row.update({key: tracked[key] for key in ("state", "outcome", "contact_count", "maximum_contacts", "last_contact_date")})
            row["customer_profile"] = profile
            row["next_contact_date"] = current.get("plan_next_contact_date") if current else None
            row["events"] = tracked["events"]
            outcomes = {"verified_purchase": ("Acquisto verificato", "green"),
                        "plan_rejection": ("Rifiuto del piano", "red"),
                        "attempts_exhausted": ("Tentativi esauriti", "neutral"),
                        "not_eligible": ("Non più proponibile", "neutral")}
            if tracked["state"] == "closed":
                row["status_label"], row["tone"] = outcomes[tracked["outcome"]]
            else:
                response = current["raw_status"] == "operator_response"
                row["status_label"] = "Risposta da gestire" if response else "In attesa di risposta"
                row["tone"] = "amber" if response else "neutral"
            row["revenue_minor"] = None
            sale = next((event for event in tracked["events"] if event["type"] == "verified_purchase"), None)
            if sale:
                row.update(proposal=names[sale["purchased_sku"]], revenue_minor=sales[sale["id"]][1]["amount_minor"],
                           shopify_order_id=sale["shopify_order_id"], purchase_date=sale["purchase_date"])
            sections[tracked["state"]].append(row)
    operational_rows.sort(key=lambda row: ({"targeted": 0, "test": 1, "none": 2}[row["category"]], -(row["value_minor"] or 0), row["customer_id"]))
    for rows in sections.values():
        rows.sort(key=lambda row: (row.get("commercial_category") != "targeted", -(row.get("value_minor") or 0), row["customer_id"], row["plan_key"]))
    summaries = {}
    for section, rows in sections.items():
        if section == "ready":
            summaries[section] = []
        elif section == "in_progress":
            waiting = [row for row in rows if row["status_label"] == "In attesa di risposta"]
            responses = [row for row in rows if row["status_label"] == "Risposta da gestire"]
            summaries[section] = [{"label": "In attesa di risposta", "count": len(waiting), "tone": "blue"},
                                  {"label": "Risposte da gestire", "count": len(responses), "tone": "purple"},
                                  {"label": "Valore potenziale aperto", "count": len(rows), "tone": "green",
                                   "value_minor": sum(row["value_minor"] or 0 for row in rows)}]
        else:
            summaries[section] = [{"label": label, "count": sum(row["outcome"] == key for row in rows), "tone": tone}
                                  for key, label, tone in [("verified_purchase", "Acquisti verificati", "green"),
                                                          ("plan_rejection", "Rifiuti espliciti", "red"),
                                                          ("attempts_exhausted", "Tentativi esauriti", "neutral")]]
            if any(row["outcome"] == "not_eligible" for row in rows):
                summaries[section].append({"label": "Non più proponibili", "count": sum(row["outcome"] == "not_eligible" for row in rows), "tone": "neutral"})
    operational_sections = {key: [row for row in operational_rows if key == row["category"]]
                            for key in ("targeted", "test", "none")}
    return {"date": as_of, "active": active, "sections": sections, "summaries": summaries,
            "product_images": _product_images(catalog),
            "profile_counts": {key: _profile_counts(rows) for key, rows in sections.items()},
            "operational_views": _operational_views(operational_rows),
            "operational_sections": operational_sections,
            "customers": operational_rows, "analyzed_customers": len(operational_rows),
            "unassigned_review_orders": sum(case["reason"] == "missing_email" for case in reviews),
            "metrics": {"ready_customers": len(sections["ready"]),
                        "potential_value_minor": sum(row["value_minor"] for row in sections["ready"]),
                        "registered_contacts": sum(event["type"] == "contact" and event["date"] <= as_of
                            for customer_id in state["profiles"] for event in event_history.get(customer_id, [])),
                        **revenue_summary(store, as_of, customer_ids={row["customer_id"] for row in operational_rows})},
            "totals": {key: sum((row["revenue_minor"] if key == "closed" else row["value_minor"]) or 0 for row in rows)
                       for key, rows in sections.items()},
            "counts": {key: len(rows) for key, rows in sections.items()}, "history_scope": "imported_orders_only"}


def _profile_counts(rows):
    """Conta clienti distinti, anche quando la scheda contiene più piani per cliente."""
    profiles = {row["customer_id"]: row["customer_profile"] for row in rows}
    return {**{key: sum(any(signal["key"] == key for signal in profile["signals"])
                       for profile in profiles.values())
               for key in ("first_purchase", "recurring", "recent_activity", "multicategory")},
            "possible_b2b": None, "high_historical_value": None}


def _operational_row(state, customer_id, as_of, profile, portfolio, active, reviews, names, rules, definitions):
    """Qualifica un cliente sul piano corrente senza cambiare la scelta del motore."""
    plan = portfolio["primary_contact_plan"]
    workable = _workable_plan(portfolio, as_of) if active and not reviews else None
    if plan:
        row = _plan_row(state, customer_id, plan, date.fromisoformat(as_of), names, rules)
    else:
        order = max((order for order in state["profiles"][customer_id]["orders"].values()
                     if order["date"] <= as_of), key=lambda order: (order["date"], order["id"]))
        row = {"customer_id": customer_id, "order_id": order["id"], "order_number": order["number"],
               "plan_key": None, "source_product": " · ".join(dict.fromkeys(
                   names.get(line["sku"], line["sku"]) for line in order["lines"])),
               "source_date": order["date"], "proposal": "Nessuna proposta attiva", "strategy": "",
               "strategy_label": "—", "value_minor": None, "alternatives_count": 0,
               "contact_count": 0, "eligible_from_date": None, "promotion_active": False,
               "price_basis": None, "reason": "Nessuna proposta attiva; storico disponibile."}
    proposals = [plan["primary_opportunity"], *plan["secondary_opportunities"]] if workable else []
    category = ("targeted" if any(item["commercial_category"] == "targeted" for item in proposals)
                else "test" if proposals else "none")
    labels = {"uncertain_purchase": "Acquisti da verificare", "unmapped_sku": "SKU non riconosciuto",
              "uncertain_email_consent": "Consenso email da verificare"}
    reason = (" · ".join(labels.get(value, value) for value in reviews) if reviews else
              "Storico non attivo" if not active else
              portfolio["contact_permission"]["reason"] if not portfolio["contact_permission"]["allowed"] else row["reason"])
    entries = []
    tracked_by_key = {tuple(item["plan_key"]): item for item in portfolio["contacted_plans"]}
    current_plans = ([plan] if plan else []) + portfolio["queued_contact_plans"]
    for candidate in current_plans:
        entry = _plan_row(state, customer_id, candidate, date.fromisoformat(as_of), names, rules)
        is_workable = bool(workable and candidate["plan_key"] == workable["plan_key"])
        tracked = tracked_by_key.get(tuple(candidate["plan_key"]))
        entry["state"] = ("closed" if tracked and tracked["state"] == "closed" else
                          "in_progress" if candidate["contact_count"] else
                          "open" if is_workable else "suspended")
        entry["contactable"] = is_workable
        entry["is_primary"] = candidate is plan
        entry["reason"] = reason if candidate is plan else candidate["plan_reason"]
        entry["opportunities"] = [{"rule_id": item["rule_id"], "proposal": names[item["target_sku"]],
                                  "strategy": _strategy(rules[item["rule_id"]])[0],
                                  "strategy_label": _strategy(rules[item["rule_id"]])[1],
                                  "commercial_category": item["commercial_category"],
                                  "value_minor": item["nominal_value_minor"], "rationale": item["rationale"]}
                                 for item in [candidate["primary_opportunity"], *candidate["secondary_opportunities"],
                                              *candidate["other_available_opportunities"]]]
        entries.append(entry)
    for tracked in portfolio["contacted_plans"]:
        if any(entry["plan_key"] == tracked["plan_key"] for entry in entries):
            continue
        rule_ids = list(dict.fromkeys(key[1] for event in tracked["events"]
                        if event["type"] == "contact" for key in event.get("included_opportunity_keys", []))) or [tracked["rule_id"]]
        opportunities = []
        for rule_id in rule_ids:
            rule = rules[rule_id]
            strategy, label = _strategy(rule)
            targets = rule.get("target_skus") or ([rule["target_sku"]] if "target_sku" in rule else [])
            opportunities.append({"rule_id": rule_id, "strategy": strategy, "strategy_label": label,
                                  "commercial_category": commercial_category(rule, definitions),
                                  "proposal": " / ".join(dict.fromkeys(names.get(sku, sku) for sku in targets)) or rule["target_product"],
                                  "value_minor": None, "rationale": rule["rationale"]})
        entries.append({"plan_key": tracked["plan_key"], "state": tracked["state"], "is_primary": False,
                        "contactable": False, "opportunities": opportunities, "reason": "Piano storico: " + tracked["outcome"]})
    response = bool(active and not reviews and portfolio["contact_permission"]["allowed"]
                    and portfolio["portfolio_status"] == "operator_response" and plan)
    row.update(customer_profile=profile, category=category, reason=reason, plans=entries,
               work_action="reply" if response else "follow_up" if workable and plan["contact_count"] else
                           "first_contact" if workable else None,
               work_date=plan["first_contact_date"] if response else
                         plan["earliest_contact_date"] if workable else None,
               maximum_contacts=definitions["shared_policies"]["follow_up"]["maximum_contacts"],
               contactable=bool(workable), status_label="Da contattare" if workable else "Nessuna azione immediata",
               tone="blue" if category == "targeted" else "purple" if category == "test" else "amber")
    return row


def _operational_views(rows):
    """Partizione dei clienti osservati: nessuna sovrapposizione fra categorie."""
    return [{"key": key, "label": label, "description": description, "tone": tone,
             "count": sum(row["category"] == key for row in rows), "available": True,
             "potential_value_minor": sum(row["value_minor"] or 0 for row in rows
                                           if row["category"] == key and row["contactable"])}
            for key, label, description, tone in (
                ("targeted", "Opportunità mirate", "Completamenti funzionali o ricambi maturi attuabili.", "blue"),
                ("test", "Opportunità da testare", "Proposte attuabili da sperimentare, senza mirate pronte.", "purple"),
                ("none", "Nessuna azione immediata", "Attese, dati da verificare, blocchi o nessuna proposta.", "amber"))]


def filter_retention(data, *, category="", state="", strategy="", profile="", search=""):
    """Filtri coerenti sullo stesso piano/opportunità, una riga per cliente."""
    rows = []
    for row in data["customers"]:
        if category and row["category"] != category:
            continue
        if profile and not any(signal["key"] == profile for signal in row["customer_profile"]["signals"]):
            continue
        matches = [{**plan, "opportunities": [op for op in plan["opportunities"]
                    if not strategy or op["strategy"] == strategy]}
                   for plan in row["plans"] if not state or plan["state"] == state]
        matches = [plan for plan in matches if plan["opportunities"]]
        if (state or strategy) and not matches:
            continue
        if search and search.casefold() not in " ".join([row["customer_id"], row.get("order_number") or "",
                row["source_product"], *[op["proposal"] for plan in matches for op in plan["opportunities"]]]).casefold():
            continue
        rows.append({**row, "matching_plans": matches})
    return rows


def rules_summary():
    """Sezione consultabile derivata dalle definizioni commerciali e dal catalogo."""
    root = Path(__file__).resolve().parent
    definitions = json.loads((root / "rules.json").read_text(encoding="utf-8"))
    catalog = json.loads((root / "catalog.json").read_text(encoding="utf-8"))
    products = {product["key"]: product for product in catalog["products"]}
    variants = {variant["sku"]: {**variant, "name": product["name"]}
                for product in catalog["products"] for variant in product["variants"]}
    images = _product_images(catalog)
    shared = definitions["shared_policies"]
    rules = []
    for rule in definitions["rules"]:
        strategy, label = _strategy(rule)
        targets = rule.get("target_skus") or ([rule["target_sku"]] if "target_sku" in rule else
                  [variant["sku"] for variant in products[rule["target_product"]]["variants"]])
        timing = rule.get("timing", shared["accessory_timing"])
        if "annual_windows" in timing:
            windows = [f"{window['opens'][3:]}/{window['opens'][:2]}–{window['closes'][3:]}/{window['closes'][:2]}"
                       for window in timing["annual_windows"]]
            when = "Solo nelle finestre annuali " + " e ".join(windows) + ", estremi inclusi. Nessuna attesa aggiuntiva dall'acquisto."
        elif "initial_after_calendar_days" in timing:
            when = (f"Prima proposta dopo {timing['initial_after_calendar_days']} giorni dal dispositivo; "
                    f"nuovo ciclo dopo {timing['repeat_after_calendar_days']} giorni dall'ultimo ricambio acquistato.")
        else:
            when = f"Da {timing.get('minimum_days_inclusive', timing.get('after_calendar_days'))} giorni dall'acquisto di partenza."
        exclusions = rule.get("exclusions", {})
        conditions = []
        if exclusions.get("target_sku_in_purchase_history") or exclusions.get("any_wave_pro_variant_in_purchase_history"):
            conditions.append("Escluso se il prodotto proposto risulta già acquistato.")
        if exclusions.get("target_component_in_known_purchased_configuration"):
            conditions.append("Escluso se già incluso nella configurazione acquistata.")
        if exclusions.get("target_category_in_purchase_history"):
            category = {"hair_dryer": "phon", "electric_shaver": "rasoi", "electric_toothbrush": "spazzolini elettrici"}[exclusions["target_category_in_purchase_history"]]
            conditions.append(f"Escluso se nello storico risultano già {category}.")
        if rule["relationship_type"] == "REPLENISHMENT":
            conditions.append("Un acquisto del ricambio aggiorna la data del ciclo; l'usura effettiva non è conosciuta.")
        sources = []
        for source in rule["sources"]:
            product = products[source["product"]]
            configuration = next(item["label"] for item in product["configurations"] if item["key"] == source["configuration"])
            sources.append({"product": product["name"], "product_key": product["key"],
                            "family": product["category"], "configuration": configuration,
                            "image": product.get("image") or next((images[variant["sku"]]
                                for variant in product["variants"] if variant.get("configuration") == source["configuration"]
                                and variant["sku"] in images), None)})
        rules.append({"id": rule["id"], "strategy": strategy, "strategy_label": label,
                      "category": commercial_category(rule, definitions), "sources": sources,
                      "targets": [{"sku": sku, "name": variants[sku]["name"], "image": images.get(sku),
                                   "variant_label": " · ".join(variants[sku][field] for field in ("material", "color") if variants[sku].get(field)),
                                   "value_minor": variants[sku]["observed_price_minor"]} for sku in targets],
                      "rationale": rule["rationale"], "timing": when, "exclusions": conditions,
                      "wait_for_rules": rule.get("wait_for_rules", []),
                      "compatibility": [f"{target_product['name']}: {item['model']} — "
                                        + ("compatibile" if item["compatible"] else "non compatibile")
                                        for target_product in products.values()
                                        if any(variant["sku"] in targets for variant in target_product["variants"])
                                        for item in target_product.get("compatibility", [])]})
    # Percorsi di lettura: fasi ricavate da fonti, percorso e timing delle regole.
    # Non costituiscono un calendario di invii né una valutazione di un cliente.
    flows = []
    for family, label in (("hair_dryer", "Asciugacapelli"),
                          ("electric_shaver", "Rasoi"),
                          ("electric_toothbrush", "Spazzolini")):
        stages = {}
        family_rules = [item for item in rules if any(source["family"] == family for source in item["sources"])]
        for item in family_rules:
            rule = next(rule for rule in definitions["rules"] if rule["id"] == item["id"])
            timing = rule.get("timing", shared["accessory_timing"])
            days = timing.get("minimum_days_inclusive", timing.get("after_calendar_days", timing.get("initial_after_calendar_days")))
            seasonal = bool(timing.get("annual_windows"))
            key = (seasonal, days, rule["commercial_track"])
            stage = stages.setdefault(key, {"days": days, "seasonal": seasonal,
                                            "rule_ids": [], "track": rule["commercial_track"]})
            stage["rule_ids"].append(item["id"])
        ordered = sorted(stages.values(), key=lambda stage: (stage["seasonal"], stage["days"] or 0, stage["track"]))
        for stage in ordered:
            members = [item for item in family_rules if item["id"] in stage["rule_ids"]]
            strategies = {item["strategy"] for item in members}
            stage["label"] = ("Mini stagionale" if stage["seasonal"] else
                              "Accessori e complementi" if len(strategies) > 1 else
                              members[0]["strategy_label"] if len(members) > 1 else
                              " / ".join(dict.fromkeys(target["name"] for target in members[0]["targets"])))
            stage["when"] = "Finestre stagionali" if stage["seasonal"] else f"Da {stage['days']} giorni"
            stage["description"] = (members[0]["timing"] if len(members) == 1 else
                                    "Una mail con le proposte applicabili al modello acquistato, escluse quelle già presenti.")
        supported = {source["product_key"] for item in family_rules for source in item["sources"]}
        flows.append({"id": family, "label": label, "rule_ids": [item["id"] for item in family_rules],
                      "models": [product["name"] for product in products.values() if product["category"] == family],
                      "models_without_rules": [product["name"] for product in products.values()
                                               if product["category"] == family and product["key"] not in supported],
                      "stages": ordered})
    # Testi di consultazione: descrivono i responsabili canonici, non rivalutano clienti.
    coordination = shared["cross_opportunity_coordination"]
    follow_up = shared["follow_up"]
    signals = definitions["customer_signals"]
    categories = _operational_views([])

    def guide(section, title, columns, entries, note=None):
        return {"section": section, "title": title, "columns": columns, "note": note,
                "rows": [{"label": label, "tone": tone, "cells": cells}
                         for label, tone, *cells in entries]}

    guides = [
        guide("retention", "Come funzionano i filtri", ["Filtro", "Che cosa seleziona", "Da ricordare"], [
            ("Categoria commerciale", "blue", "La situazione operativa attuale del cliente.", "Mirata, da testare o nessuna azione immediata: una sola categoria per cliente."),
            ("Stato del piano", "blue", "Clienti con almeno un piano nello stato richiesto.", "Lo stato riguarda il piano, non l'intero cliente."),
            ("Strategia commerciale", "purple", "Clienti con una proposta della strategia richiesta, anche secondaria, futura o storica.", "La proposta principale in tabella resta quella globale: controlla Corrispondenze / motivo."),
            ("Profilo cliente", "slate", "Un segnale alla volta fra quelli osservati negli acquisti.", "I segnali possono sovrapporsi, ma il selettore attuale è singolo."),
            ("Ricerca", None, "ID cliente, ordine e prodotto fonte, proposte nei piani corrispondenti.", "Non cerca l'email o ogni acquisto storico."),
            ("Filtri combinati", None, "Tutti i filtri devono essere soddisfatti; stato e strategia sullo stesso piano.", "I conteggi delle categorie sono globali, prima degli altri filtri.")],
            "La lista e i conteggi includono solo clienti con consenso email valido. I filtri non ricalcolano la raccomandazione e non autorizzano un contatto bloccato."),
        guide("retention", "Le tre categorie cliente", ["Categoria", "Quando viene assegnata"], [
            (item["label"], {"targeted": "green", "test": "purple", "none": "slate"}[item["key"]], item["description"])
            for item in categories], "Conta il piano principale lavorabile oggi, comprese le sue proposte secondarie. Nessuna azione non significa nessuna opportunità futura."),
        guide("retention", "Gli stati del piano", ["Stato", "Significato", "Azione possibile"], [
            ("Aperti", "green", "Mai contattati e lavorabili oggi.", "Primo contatto, dopo le verifiche richieste."),
            ("In corso", "blue", "Già contattati e non conclusi.", "Attesa, gestione della risposta o secondo contatto, se consentito."),
            ("In attesa / sospesi", "amber", "Mai contattati e non lavorabili: futuri, in coda o bloccati.", "Consulta motivo e data; maturazione e data di contatto possono differire."),
            ("Chiusi", "slate", "Piani contattati conclusi per acquisto, rifiuto, tentativi o non più proponibili.", "Consulta lo storico e registra eventuali esiti ammessi.")]),
        guide("retention", "Esempi di combinazione", ["Selezione", "Risultato"], [
            ("Espansione", "purple", "Anche clienti con un'espansione futura o in attesa e un concentratore come proposta principale."),
            ("Espansione + Aperti", "green", "Clienti con un piano aperto lavorabile che contiene un'espansione. Non include i follow-up già in corso."),
            ("Espansione + In corso", "blue", "Un piano già contattato contiene un'espansione; può essere ancora in attesa."),
            ("Mirate + Espansione", None, "Clienti oggi classificati come mirati con un'espansione anche fra gli altri piani.")]),
        guide("retention", "Segnali del profilo", ["Profilo", "Criterio osservato"], [
            ("Primo acquisto", None, f"Esattamente {signals['first_purchase_order_count']} ordine interamente valido."),
            ("Ricorrente", "green", f"Almeno {signals['recurring_minimum_orders']} ordini interamente validi."),
            ("Alta attività recente", "amber", f"Almeno {signals['recent_activity_minimum_orders']} ordini interamente validi negli ultimi {signals['recent_activity_calendar_days']} giorni, oggi incluso."),
            ("Multicategoria", "purple", f"Almeno {signals['multicategory_minimum_categories']} categorie principali da righe valide: cura capelli, igiene orale, rasatura. Accessori e ricambi non aggiungono categorie."),
            ("B2B / Alto valore", "slate", "Non valutabili: dati o criteri non disponibili; opzioni disabilitate.")],
            "I segnali descrivono il cliente: non creano opportunità né autorizzano contatti."),
        guide("plans", "Composizione delle comunicazioni", ["Situazione", "Comportamento"], [
            ("Stesso ordine + percorso + maturazione", "blue", "Una comunicazione con primaria e proposte secondarie. Date o percorsi diversi mantengono piani separati."),
            ("Accessori del phon", None, "Concentratore, diffusore, supporto, pochette e spazzola si uniscono quando applicabili alla stessa fonte e con la stessa maturazione."),
            ("AutoCurl", "purple", "Mail dedicata, separata dalle espansioni. È un complemento da testare; tempi e fonti sono indicati nella regola commerciale."),
            ("Wave Pro + rasoi", "purple", "Mail di espansione con maturazione comune successiva ad AutoCurl. Le esclusioni delle due categorie sono indipendenti; P3 è alternativa a P3 Pro. L'ordine segue le priorità del motore."),
            ("Dipendenza AutoCurl", "amber", "Attende i piani accessori applicabili dello stesso ordine. Questo prerequisito appartiene al piano AutoCurl; non si estende al piano separato delle espansioni. Restano le priorità e la distanza globale fra contatti."),
            ("Mini stagionale", None, "Percorso separato dagli accessori e dalle espansioni anche con la stessa data."),
            ("Promozione", None, "Non anticipa la maturazione e non crea relazioni. Può superare solo prerequisiti da testare mai contattati; non mirate o piani contattati.")]),
        guide("plans", "Scelta del piano principale", ["Precedenza", "Criterio"], [
            ("1 · Conversazioni e contatti avviati", "blue", "Prima risposte da gestire, poi piani già contattati aperti; precede il primo contatto più vecchio."),
            ("2 · Nuovi piani maturi", "green", "Prima mirate, poi promozione, finestra stagionale, valore nominale maggiore, maturazione più vecchia, rango e spareggi."),
            ("3 · Piani futuri", "slate", "Se manca un piano maturo, precede la prossima data utile. Gli altri restano in coda."),
            ("Primaria dentro il piano", None, "Interesse espresso, poi primaria già contattata ancora disponibile; per nuove proposte: mirata, promozione, valore, rango e ID regola."),
            ("Ordine lista Retention", None, "Categoria mirata / da testare / nessuna azione, poi valore principale decrescente e ID cliente. Il filtro non cambia questa graduatoria.")],
            "Un solo piano principale per cliente. Valore nominale non significa probabilità di acquisto, margine o ricavo atteso."),
        guide("contacts", "Condizioni e frequenza", ["Regola", "Comportamento"], [
            ("Canale email", "blue", "Invio manuale fuori dal sistema. Qui si registra il contatto effettuato."),
            ("Consenso e dati", "green", "Storico attivo, consenso email valido e nessun caso di revisione bloccante. Ordini annullati/resi ignorati; righe dubbie e SKU ignoti richiedono verifica."),
            ("Verifiche prima dell'invio", None, " ".join(shared["operator_checks"])),
            ("Interesse preventivo", None, "Non richiesto: proposta proattiva." if not shared["customer_interest_required"] else "Richiesto dalla politica comune."),
            ("Tentativi per piano", "blue", f"Massimo {follow_up['maximum_contacts']} contatti, condivisi da primaria e secondarie."),
            ("Follow-up", "blue", f"Secondo contatto dopo almeno {follow_up['retry_after_calendar_days']} giorni, senza risposta o acquisto che imponga gestione/chiusura."),
            ("Fra piani diversi", "amber", f"Almeno {coordination['minimum_days_between_contacts']} giorni fra qualsiasi contatto registrato del cliente."),
            ("Mini stagionale", None, "Anche il secondo contatto deve cadere nella finestra. I tentativi non ripartono ogni anno."),
            ("Newsletter esterne", "slate", "Storico invii non integrato: non è incluso nel conteggio automatico dei contatti.")]),
        guide("contacts", "Dopo contatto, risposta o acquisto", ["Evento", "Effetto"], [
            ("Primo contatto", "blue", "Il piano mantiene precedenza; iniziano attesa e conteggio comune dei tentativi."),
            ("Risposta", "amber", "Gestione manuale; altri piani attendono finché la conversazione viene chiusa."),
            ("Interesse prodotto", "green", "La conversazione si concentra sul prodotto, senza azzerare i tentativi."),
            ("Rifiuto prodotto", None, "Esclude solo il prodotto; gli altri possono restare disponibili. Richiede gestione della conversazione."),
            ("Chiusura conversazione", None, "Segna risposta gestita e rivaluta il piano. Non equivale al rifiuto dell'intero piano."),
            ("Chiusura piano", "slate", f"Acquisto verificato, rifiuto piano, {follow_up['maximum_contacts']} contatti o proposta presentata non più idonea. Il limite chiude il piano appena raggiunto."),
            ("Proposte secondarie", None, "Quelle presentate in un piano chiuso non aprono sequenze autonome. Nessuna riapertura automatica delle opportunità esaurite."),
            ("Nuovo ricambio acquistato", "green", "Apre un nuovo ciclo con la maturazione prevista dalla relativa regola.")]),
        guide("contacts", "Valore nominale e ricavi", ["Misura", "Come funziona"], [
            ("Valore nominale", "blue", "Prezzo rappresentativo della proposta principale; non somma delle alternative. Non è ricavo previsto."),
            ("Acquisto importato", None, "Può escludere la proposta e chiudere un piano contattato. Non genera automaticamente revenue attribuita."),
            ("Ricavo verificato", "green", "Registrazione manuale con contatto, SKU presentato, ordine Shopify, data e importo EUR verificati dall'operatore."),
            ("Attribuzione", None, "Acquisto dalla data contatto in poi, non oltre la verifica; nessuna finestra massima. Lo stesso ordine si attribuisce una sola volta."),
            ("Correzione importo", None, "L'ultima correzione sostituisce il totale della vendita; non aggiunge un secondo ricavo."),
            ("Limiti", "slate", "Nessuna verifica Shopify live o misura causale. Margine e probabilità non calcolati; prezzi e disponibilità da confermare.")])]
    return {"version": definitions["version"], "rules": rules,
            "guides": guides, "categories": categories, "flows": flows}


def _overview_worklist(evaluation, as_of, recent_days, *, work="", category="", product="",
                       strategy="", profile="", search="", order="recommended"):
    """Organizza soltanto le azioni correnti; non seleziona nuovi piani o prodotti."""
    groups = {"follow_up": [], "recent": [], "backlog": []}
    for row in evaluation["customers"]:
        if not row["work_action"]:
            continue
        age = ((date.fromisoformat(as_of) - date.fromisoformat(row["eligible_from_date"])).days
               if row["work_action"] == "first_contact" else None)
        key = "follow_up" if age is None else "recent" if age < recent_days else "backlog"
        groups[key].append(row)
    views = [{"key": key, "label": label, "description": description, "count": len(groups[key])}
             for key, label, description in (
                 ("follow_up", "Da seguire", "Risposte da gestire e follow-up arrivati alla data consentita."),
                 ("recent", "Nuove opportunità", f"Primo contatto del piano: maturazione da meno di {recent_days} giorni."),
                 ("backlog", "Storico da recuperare", f"Primo contatto del piano: maturazione da almeno {recent_days} giorni."))]
    if work not in groups:
        work = next((key for key, rows in groups.items() if rows), "recent")
    all_rows = [row for rows in groups.values() for row in rows]
    options = {
        "category": [{"value": view["key"], "label": view["label"]}
                     for view in evaluation["operational_views"] if view["key"] != "none"],
        "product": [{"value": name, "label": name} for name in sorted({row["proposal"] for row in all_rows})],
        "strategy": [{"value": key, "label": label} for key, label in sorted(
            {(row["strategy"], row["strategy_label"]) for row in all_rows})],
        "profile": [{"value": key, "label": label} for key, label in sorted(
            {(signal["key"], signal["label"]) for row in all_rows
             for signal in row["customer_profile"]["signals"]})],
    }
    selected = {"category": category, "product": product, "strategy": strategy, "profile": profile}
    selected = {key: value if value in {option["value"] for option in options[key]} else ""
                for key, value in selected.items()}
    search = search.strip()
    rows = [row for row in groups[work]
            if (not selected["category"] or row["commercial_category"] == selected["category"])
            and (not selected["product"] or row["proposal"] == selected["product"])
            and (not selected["strategy"] or row["strategy"] == selected["strategy"])
            and (not selected["profile"] or any(signal["key"] == selected["profile"]
                                               for signal in row["customer_profile"]["signals"]))
            and (not search or search.casefold() in " ".join((row["customer_id"], row.get("order_number") or "",
                                                            row["source_product"], row["proposal"])).casefold())]
    order = order if order in {"recommended", "product"} and work != "follow_up" else "recommended"
    if work == "follow_up":
        rows.sort(key=lambda row: (row["work_action"] != "reply", row["work_date"], row["customer_id"]))
    elif order == "product":
        rows.sort(key=lambda row: (row["commercial_category"] != "targeted", row["proposal"],
                                   row["eligible_from_date"], row["customer_id"]))
    else:
        ordered = []
        for commercial_category in ("targeted", "test"):
            by_product = {}
            for row in sorted(rows, key=lambda item: (item["eligible_from_date"], item["customer_id"])):
                if row["commercial_category"] == commercial_category:
                    by_product.setdefault(row["proposal"], []).append(row)
            queues = sorted(by_product.values(), key=lambda queue: (queue[0]["eligible_from_date"], queue[0]["proposal"]))
            for index in range(max((len(queue) for queue in queues), default=0)):
                ordered.extend(queue[index] for queue in queues if index < len(queue))
        rows = ordered
    return {"work_views": views, "work_group": work, "recent_days": recent_days,
            "filter_options": options, "filters": {**selected, "search": search, "order": order}, "rows": rows}


def overview_summary(store, as_of, period="30d", **filters):
    """Dati dell'Overview: decisioni correnti e ricavi verificati nel periodo."""
    today = date.fromisoformat(as_of)
    if period in {"30d", "90d"}:
        start = today - timedelta(days=int(period[:-1]) - 1)
    elif period in {"6m", "12m"}:
        month_index = today.year * 12 + today.month - 1 - int(period[:-1])
        year, month = divmod(month_index, 12)
        start = date(year, month + 1, min(today.day, monthrange(year, month + 1)[1])) + timedelta(days=1)
    else:
        raise ValueError("Periodo non supportato.")
    evaluation = retention_summary(store, as_of)
    definitions = json.loads((Path(__file__).resolve().parent / "rules.json").read_text(encoding="utf-8"))
    worklist = _overview_worklist(evaluation, as_of, definitions["overview_worklist"]["recent_days"], **filters)
    chart = revenue_summary(store, as_of, starts_on=start.isoformat(), include_series=True,
                            customer_ids={row["customer_id"] for row in evaluation["customers"]})
    if period in {"6m", "12m"}:
        monthly = {}
        for point in chart["series"]:
            month = point["date"][:7]
            monthly[month] = monthly.get(month, 0) + point["amount_minor"]
        chart["series"] = [{"date": month + "-01", "amount_minor": amount}
                           for month, amount in monthly.items()]
    return {"date": as_of, "active": evaluation["active"], "period": period,
            "product_images": evaluation["product_images"],
            "starts_on": start.isoformat(), "chart": chart, **worklist,
            "metrics": evaluation["metrics"],
            "history_scope": "imported_orders_only"}


def _verified_sales(store, as_of):
    """Importi verificati effettivi: una sola applicazione delle correzioni."""
    date.fromisoformat(as_of)
    sales = {}
    corrections = {}
    for customer_id, event in store.revenue_events():
        if event["date"] > as_of:
            continue
        if event["type"] == "verified_purchase":
            sales[event["id"]] = (customer_id, event)
        else:
            corrections[event["verified_purchase_event_id"]] = event
    return {sale_id: (customer_id, {**sale, "amount_minor": corrections.get(sale_id, sale)["amount_minor"]})
            for sale_id, (customer_id, sale) in sales.items()}


def revenue_summary(store, as_of, *, starts_on=None, include_series=False, customer_ids=None):
    """Somma gli importi verificati manualmente, applicando l'ultima correzione."""
    date.fromisoformat(as_of)
    if starts_on and date.fromisoformat(starts_on) > date.fromisoformat(as_of):
        raise ValueError("Il periodo deve iniziare prima della data di valutazione.")
    sales = _verified_sales(store, as_of)
    total = 0
    daily = {}
    verified_orders = 0
    for sale_id, (customer_id, sale) in sales.items():
        if customer_ids is not None and customer_id not in customer_ids:
            continue
        if starts_on and sale["purchase_date"] < starts_on:
            continue
        amount = sale["amount_minor"]
        total += amount
        verified_orders += 1
        daily[sale["purchase_date"]] = daily.get(sale["purchase_date"], 0) + amount
    result = {"as_of": as_of, "currency": "EUR", "verified_orders": verified_orders,
              "attributed_revenue_minor": total}
    if include_series:
        first = date.fromisoformat(starts_on or min(daily, default=as_of))
        last = date.fromisoformat(as_of)
        result["series"] = [{"date": (first + timedelta(days=i)).isoformat(),
                             "amount_minor": daily.get((first + timedelta(days=i)).isoformat(), 0)}
                            for i in range((last - first).days + 1)]
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import, eventi e lista operativa senza recapiti in output.")
    parser.add_argument("--db", default=os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_PATH") or "local-data/retention.sqlite3")
    commands = parser.add_subparsers(dest="command", required=True)
    import_command = commands.add_parser("import")
    import_command.add_argument("csv_paths", nargs="+", type=Path)
    sync_command = commands.add_parser("sync")
    sync_command.add_argument("--watch", action="store_true")
    activate_command = commands.add_parser("activate")
    activate_command.add_argument("--date", required=True)
    evaluate_command = commands.add_parser("evaluate")
    evaluate_command.add_argument("--as-of")
    explain_command = commands.add_parser("explain-order")
    explain_command.add_argument("--customer", required=True)
    explain_command.add_argument("--order", required=True)
    explain_command.add_argument("--as-of")
    event_command = commands.add_parser("event")
    event_command.add_argument("--customer", required=True)
    event_command.add_argument("--json", type=Path, required=True)
    revenue_command = commands.add_parser("revenue")
    revenue_command.add_argument("--as-of")
    arguments = parser.parse_args()
    store = Store(arguments.db)
    try:
        if arguments.command == "sync":
            errors = sync_local_data(store, Path("local-data"), watch=arguments.watch)
            state = store.load_state()
            output = {"profiles": len(state["profiles"]),
                      "orders_without_email": len(state["unassigned_orders"]),
                      "csv_errors": errors}
        elif arguments.command == "import":
            state = import_into_store(store, arguments.csv_paths)
            output = {"profiles": len(state["profiles"]),
                      "orders_without_email": len(state["unassigned_orders"])}
        elif arguments.command == "activate":
            activate_history(store, arguments.date)
            output = {"activation_date": store.activation_date()}
        elif arguments.command == "event":
            event = json.loads(arguments.json.read_text(encoding="utf-8-sig"))
            record_event(store, arguments.customer, event)
            output = {"event_id": event["id"], "recorded": True}
        elif arguments.command == "explain-order":
            today = arguments.as_of or datetime.now(ZoneInfo("Europe/Rome")).date().isoformat()
            output = explain_order(store, arguments.customer, arguments.order, today)
        elif arguments.command == "revenue":
            today = arguments.as_of or datetime.now(ZoneInfo("Europe/Rome")).date().isoformat()
            output = revenue_summary(store, today)
        else:
            today = arguments.as_of or datetime.now(ZoneInfo("Europe/Rome")).date().isoformat()
            output = evaluate_day(store, today)
        print(json.dumps(output, ensure_ascii=False))
    finally:
        store.close()
