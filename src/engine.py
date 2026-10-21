"""Valutazione e coordinamento opportunità su uno snapshot, senza I/O di contatto.

Date ISO YYYY-MM-DD già normalizzate in Europe/Rome. validity si riferisce
alla riga acquistata: valid, cancelled, returned (reso completo), unknown.
Non dedurre questi stati dal solo importo di un rimborso.
"""

import argparse
from datetime import date, timedelta
import json
from pathlib import Path
import sys


SOURCE_DIR = Path(__file__).resolve().parent


def _day(value):
    if not isinstance(value, str) or len(value) != 10:
        raise ValueError("Usare date locali ISO YYYY-MM-DD.")
    return date.fromisoformat(value)


def _next_annual_window_day(on_or_after, windows):
    """Prima data inclusa in una finestra annuale, anche a cavallo d'anno."""
    candidates = []
    for window in windows:
        open_month, open_day = map(int, window["opens"].split("-"))
        close_month, close_day = map(int, window["closes"].split("-"))
        crosses_year = (close_month, close_day) < (open_month, open_day)
        for year in (on_or_after.year - 1, on_or_after.year, on_or_after.year + 1):
            opens = date(year, open_month, open_day)
            closes = date(year + crosses_year, close_month, close_day)
            if closes >= on_or_after:
                candidates.append(max(opens, on_or_after))
    return min(candidates)


def _unique_records(records):
    """Identici ID non moltiplicano acquisti o tentativi; conflitti sono errori."""
    unique = {}
    for record in records:
        record_id = record["id"]
        if not isinstance(record_id, str) or not record_id:
            raise ValueError("Ogni record deve avere un ID non vuoto.")
        if record_id in unique and unique[record_id] != record:
            raise ValueError("Record discordanti con lo stesso ID.")
        unique[record_id] = record
    return list(unique.values())


def _promotions_on(evaluation_date, *, definitions=None):
    """Promozioni pianificate per SKU nella data locale di valutazione."""
    source = SOURCE_DIR / "promotions.json"
    if definitions is None:
        definitions = json.loads(source.read_text(encoding="utf-8"))
    today = _day(evaluation_date)
    active = {}
    for campaign in definitions["campaigns"]:
        if not _day(campaign["starts_on"]) <= today <= _day(campaign["ends_on"]):
            continue
        for sku in campaign["skus"]:
            if sku in active:
                raise ValueError(f"Promozioni sovrapposte per SKU {sku}.")
            active[sku] = {
                "campaign_id": campaign["id"],
                "status": campaign["status"],
                "starts_on": campaign["starts_on"],
                "ends_on": campaign["ends_on"],
                "price_minor": campaign["price_minor"],
                "currency": campaign["currency"],
            }
    return definitions["version"], active


def _evaluate_replenishment(customer, evaluation_date, today, catalog, definitions,
                            rule, policies, variants):
    """Valuta un ciclo di ricambio identificato dall'acquisto che lo ha aperto."""
    target_skus = set(rule["target_skus"])
    target_product = next(product for product in catalog["products"]
                          if product["key"] == rule["benefit_product_key"])
    replacement_skus = {variant["sku"] for variant in target_product["variants"]}
    target_options = []
    for sku in rule["target_skus"]:
        _, variant = variants[sku]
        option = {
            "sku": sku,
            "observed_price_minor": variant["observed_price_minor"],
            "currency": variant["currency"],
        }
        for field in ("type", "pack_quantity", "version", "color"):
            if field in variant:
                option[field] = variant[field]
        target_options.append(option)

    checks = list(policies["operator_checks"]) + list(rule.get("operator_checks", []))
    evidence = []
    if not customer.get("history_complete", False):
        checks.append("Storico acquisti incompleto: verificare prodotti sorgente e ricambi precedenti.")
    if not customer.get("contact_history_complete", False):
        checks.append("Storico contatti incompleto: verificare i tentativi del ciclo di ricambio corrente.")

    sources = []
    replacements = []
    undated_source = False
    unknown_skus = False
    for purchase in _unique_records(customer.get("purchases", [])):
        validity = purchase.get("validity", "unknown")
        if validity not in {"valid", "unknown", "cancelled", "returned"}:
            raise ValueError("Validità della riga acquisto non riconosciuta.")
        purchased_on = _day(purchase["date"]) if purchase.get("date") else None
        if purchased_on and purchased_on > today:
            continue
        if validity in {"cancelled", "returned"}:
            continue
        if validity == "unknown":
            checks.append("Verificare validità, resi, annullamenti ed evasione delle righe con stato sconosciuto.")
        if not purchased_on:
            checks.append("Verificare la data delle righe acquisto prive di data.")
        sku = purchase.get("sku")
        if sku not in variants:
            unknown_skus = True
            checks.append("SKU non mappati: verificare gli acquisti del prodotto sorgente e dei ricambi.")
            continue
        product, variant = variants[sku]
        is_source = any(
            product["key"] == source["product"]
            and variant.get("configuration") == source["configuration"]
            for source in rule["sources"]
        )
        if is_source:
            if purchased_on:
                sources.append((purchased_on, purchase["id"], sku, validity,
                                purchase.get("order_id", purchase["id"])))
            else:
                undated_source = True
        if sku in replacement_skus and purchased_on:
            replacements.append((purchased_on, purchase["id"], sku, validity,
                                 purchase.get("order_id", purchase["id"])))

    if not sources:
        base = {
            "customer_id": customer["customer_id"],
            "opportunity_key": [customer["customer_id"], rule["id"]],
            "rule_id": rule["id"],
            "rule_version": rule["version"],
            "rules_version": definitions["version"],
            "catalog_version": catalog["version"],
            "evaluation_date": evaluation_date,
            "relationship_type": rule["relationship_type"],
            "commercial_track": rule["commercial_track"],
            "plan_rank": rule["plan_rank"],
            "plan_rank_reason": rule["plan_rank_reason"],
            "rationale": rule["rationale"],
            "benefit": target_product["declared_benefit"],
            "target_options": target_options,
            "preferred_target_sku": None,
            "nominal_value_minor": target_options[0]["observed_price_minor"],
            "currency": target_options[0]["currency"],
            "price_basis": "catalog_observed_price",
            "operator_checks": sorted(set(checks)),
            "evidence": [],
            "contact_count": 0,
            "first_contact_date": None,
            "eligible_from_date": None,
            "next_contact_date": None,
        }
        if undated_source or unknown_skus or not customer.get("history_complete", False):
            base.update(status="insufficient_data",
                        reason="Manca un acquisto datato e riconoscibile del prodotto sorgente.")
        else:
            base.update(status="no_action", reason="Nessun acquisto valido del prodotto sorgente nello storico fornito.")
        return base

    confirmed_sources = [item for item in sources if item[3] == "valid"]
    source_candidates = confirmed_sources or sources
    preferred_sources = [item for item in source_candidates
                         if variants[item[2]][0]["key"] == rule.get("preferred_source_product")]
    source = min(preferred_sources or source_candidates)
    source_day, source_id, source_sku, source_validity, source_order_id = source
    eligible_replacements = [item for item in replacements if item[0] >= source_day]
    confirmed_replacements = [item for item in eligible_replacements if item[3] == "valid"]
    latest_replacement = max(confirmed_replacements or eligible_replacements, default=None)
    reference = latest_replacement or source
    reference_day, reference_id, reference_sku, reference_validity, reference_order_id = reference
    cycle_kind = "repeat" if latest_replacement else "initial"
    preferred_target_sku = (
        reference_sku if cycle_kind == "repeat" and reference_sku in target_skus
        else None if cycle_kind == "repeat"
        else rule.get("initial_preferred_target_by_source_sku", {}).get(source_sku)
    )
    timing_days = (rule["timing"]["repeat_after_calendar_days"] if cycle_kind == "repeat"
                   else rule["timing"]["initial_after_calendar_days"])
    available_on = reference_day + timedelta(days=timing_days)

    evidence.append({"id": source_id, "kind": "source_purchase", "sku": source_sku,
                     "date": source_day.isoformat(), "validity": source_validity})
    if latest_replacement:
        evidence.append({"id": reference_id, "kind": "replenishment_purchase",
                         "sku": reference_sku, "date": reference_day.isoformat(),
                         "validity": reference_validity})

    events = []
    for event in _unique_records(customer.get("events", [])):
        if event["rule_id"] != rule["id"]:
            continue
        if event["type"] not in {"contact", "reply", "rejection"}:
            raise ValueError("Tipo evento non riconosciuto.")
        if not event.get("cycle_reference_purchase_id"):
            raise ValueError("Gli eventi di ricambio devono indicare cycle_reference_purchase_id.")
        event_day = _day(event["date"])
        if event_day <= today and event["cycle_reference_purchase_id"] == reference_id:
            events.append((event_day, event))
    contacts = sorted(day for day, event in events if event["type"] == "contact")
    for _, event in events:
        evidence.append({"id": event["id"], "kind": event["type"], "date": event["date"]})

    preferred_option = next((option for option in target_options
                             if option["sku"] == preferred_target_sku), target_options[0])
    result = {
        "customer_id": customer["customer_id"],
        "opportunity_key": [customer["customer_id"], rule["id"], reference_id],
        "rule_id": rule["id"],
        "rule_version": rule["version"],
        "rules_version": definitions["version"],
        "catalog_version": catalog["version"],
        "evaluation_date": evaluation_date,
        "relationship_type": rule["relationship_type"],
        "commercial_track": rule["commercial_track"],
        "plan_rank": rule["plan_rank"],
        "plan_rank_reason": rule["plan_rank_reason"],
        "rationale": rule["rationale"],
        "benefit": target_product["declared_benefit"],
        "target_options": target_options,
        "preferred_target_sku": preferred_target_sku,
        "nominal_value_minor": preferred_option["observed_price_minor"],
        "currency": preferred_option["currency"],
        "price_basis": "catalog_observed_price",
        "operator_checks": checks,
        "evidence": evidence,
        "contact_count": len(contacts),
        "first_contact_date": contacts[0].isoformat() if contacts else None,
        "eligible_from_date": available_on.isoformat(),
        "cycle_kind": cycle_kind,
        "cycle_reference_purchase_id": reference_id,
        "cycle_reference_purchase_date": reference_day.isoformat(),
        "source_order_id": source_order_id,
        "source_purchase_date": source_day.isoformat(),
        "cycle_reference_order_id": reference_order_id,
        "source_purchase_id": source_id,
        "days_since_cycle_reference": (today - reference_day).days,
    }

    def finish(status, reason, next_date=None):
        result.update(status=status, reason=reason,
                      next_contact_date=next_date.isoformat() if next_date else None)
        result["operator_checks"] = sorted(set(checks))
        result["evidence"] = sorted(evidence, key=lambda item: (item["id"], item["kind"]))
        return result

    if customer.get("do_not_contact", False):
        return finish("stopped", "Richiesta generale di non essere contattato.")
    if any(event["type"] == "rejection" for _, event in events):
        return finish("stopped", "Rifiuto esplicito della proposta nel ciclo corrente.")
    if len(contacts) >= policies["follow_up"]["maximum_contacts"]:
        return finish("stopped", "Numero massimo di tentativi raggiunto nel ciclo corrente.")
    if any(event["type"] == "reply" for _, event in events):
        return finish("operator_response", "Risposta ricevuta: l'operatore gestisce la conversazione.")
    if today < available_on:
        return finish("deferred", "Il ciclo di ricambio non ha ancora raggiunto il timing previsto.",
                      available_on)
    if contacts:
        retry_on = contacts[0] + timedelta(days=rule["timing"]["follow_up_after_calendar_days"])
        if today < retry_on:
            return finish("deferred", "Attendere prima del secondo contatto.", retry_on)
        return finish("second_contact_review", "Secondo e ultimo tentativo valutabile nel ciclo corrente.")
    return finish("first_contact_review", "Ricambio valutabile per il ciclo corrente.")


def _evaluate_replacement(customer, evaluation_date, today, catalog, definitions,
                          rule, policies, variants):
    """Valuta la sostituzione del precedente Wave con una variante Wave Pro."""
    target_product = next(product for product in catalog["products"]
                          if product["key"] == rule["target_product"])
    target_options = [
        {
            "sku": variant["sku"],
            "material": variant["material"],
            "color": variant["color"],
            "observed_price_minor": variant["observed_price_minor"],
            "currency": variant["currency"],
        }
        for variant in target_product["variants"]
    ]
    target_skus = {option["sku"] for option in target_options}
    nominal_value = min(option["observed_price_minor"] for option in target_options)
    maximum_value = max(option["observed_price_minor"] for option in target_options)
    currency = target_options[0]["currency"]
    checks = list(policies["operator_checks"]) + list(rule.get("operator_checks", []))
    evidence = []
    sources = []
    undated_source = False
    target_observed = False
    unknown_skus = False

    if not customer.get("history_complete", False):
        checks.append("Storico acquisti incompleto: verificare acquisti precedenti di Wave e Wave Pro.")
    if not customer.get("contact_history_complete", False):
        checks.append("Storico contatti incompleto: verificare i precedenti tentativi per questa proposta.")

    for purchase in _unique_records(customer.get("purchases", [])):
        validity = purchase.get("validity", "unknown")
        if validity not in {"valid", "unknown", "cancelled", "returned"}:
            raise ValueError("Validità della riga acquisto non riconosciuta.")
        purchased_on = _day(purchase["date"]) if purchase.get("date") else None
        if purchased_on and purchased_on > today:
            continue
        if validity in {"cancelled", "returned"}:
            continue
        if validity == "unknown":
            checks.append("Verificare validità, resi, annullamenti ed evasione delle righe con stato sconosciuto.")
        if not purchased_on:
            checks.append("Verificare la data delle righe acquisto prive di data.")
        sku = purchase.get("sku")
        if sku not in variants:
            unknown_skus = True
            checks.append("SKU non mappati: verificare gli acquisti del precedente Wave e di Wave Pro.")
            continue
        product, variant = variants[sku]
        if sku in target_skus:
            target_observed = True
            evidence.append({"id": purchase["id"], "kind": "target_purchase",
                             "sku": sku, "date": purchase.get("date"),
                             "validity": validity})
        if any(product["key"] == source["product"]
               and variant.get("configuration") == source["configuration"]
               for source in rule["sources"]):
            if purchased_on:
                sources.append((purchased_on, purchase["id"], sku, validity,
                                purchase.get("order_id", purchase["id"])))
            else:
                undated_source = True

    events = []
    for event in _unique_records(customer.get("events", [])):
        if event["rule_id"] != rule["id"]:
            continue
        if event["type"] not in {"contact", "reply", "rejection"}:
            raise ValueError("Tipo evento non riconosciuto.")
        event_day = _day(event["date"])
        if event_day <= today:
            events.append((event_day, event))
    contacts = sorted(day for day, event in events if event["type"] == "contact")
    for _, event in events:
        evidence.append({"id": event["id"], "kind": event["type"], "date": event["date"]})

    result = {
        "customer_id": customer["customer_id"],
        "opportunity_key": [customer["customer_id"], rule["id"]],
        "rule_id": rule["id"],
        "rule_version": rule["version"],
        "rules_version": definitions["version"],
        "catalog_version": catalog["version"],
        "evaluation_date": evaluation_date,
        "relationship_type": rule["relationship_type"],
        "commercial_track": rule["commercial_track"],
        "plan_rank": rule["plan_rank"],
        "plan_rank_reason": rule["plan_rank_reason"],
        "rationale": rule["rationale"],
        "benefit": rule["benefit"],
        "target_product_key": rule["target_product"],
        "target_options": target_options,
        "nominal_value_minor": nominal_value,
        "maximum_option_value_minor": maximum_value,
        "currency": currency,
        "price_basis": "minimum_catalog_observed_price_among_options",
        "operator_checks": checks,
        "evidence": evidence,
        "contact_count": len(contacts),
        "first_contact_date": contacts[0].isoformat() if contacts else None,
        "eligible_from_date": None,
    }

    def finish(status, reason, next_date=None):
        result.update(status=status, reason=reason,
                      next_contact_date=next_date.isoformat() if next_date else None)
        result["operator_checks"] = sorted(set(checks))
        result["evidence"] = sorted(evidence, key=lambda item: (item["id"], item["kind"]))
        return result

    if customer.get("do_not_contact", False):
        return finish("stopped", "Richiesta generale di non essere contattato.")
    if any(event["type"] == "rejection" for _, event in events):
        return finish("stopped", "Rifiuto esplicito della proposta.")
    if target_observed:
        return finish("excluded", "Wave Pro risulta già acquistato nello storico disponibile.")
    if len(contacts) >= policies["follow_up"]["maximum_contacts"]:
        return finish("stopped", "Numero massimo di tentativi raggiunto; nessuna riapertura automatica.")
    if not sources:
        if undated_source or unknown_skus or not customer.get("history_complete", False):
            return finish("insufficient_data", "Manca un acquisto datato e riconoscibile del precedente Wave.")
        return finish("no_action", "Nessun acquisto valido del precedente Wave nello storico fornito.")

    confirmed = [item for item in sources if item[3] == "valid"]
    purchased_on, purchase_id, sku, validity, source_order_id = min(confirmed or sources)
    available_on = purchased_on + timedelta(days=rule["timing"]["after_calendar_days"])
    result.update(
        source_purchase_id=purchase_id,
        source_order_id=source_order_id,
        source_purchase_date=purchased_on.isoformat(),
        days_since_purchase=(today - purchased_on).days,
        eligible_from_date=available_on.isoformat(),
    )
    evidence.append({"id": purchase_id, "kind": "source_purchase", "sku": sku,
                     "date": purchased_on.isoformat(), "validity": validity})
    if any(event["type"] == "reply" for _, event in events):
        return finish("operator_response", "Risposta ricevuta: l'operatore gestisce la conversazione.")
    if today < available_on:
        return finish("deferred", "Non sono ancora trascorsi i sei mesi richiesti dall'acquisto.",
                      available_on)
    if contacts:
        retry_on = contacts[0] + timedelta(days=policies["follow_up"]["retry_after_calendar_days"])
        if today < retry_on:
            return finish("deferred", "Attendere prima del secondo contatto.", retry_on)
        return finish("second_contact_review", "Secondo e ultimo tentativo valutabile.")
    return finish("first_contact_review", "Sostituzione con Wave Pro valutabile dopo sei mesi dall'acquisto del precedente Wave.")


def _evaluate(customer, evaluation_date, rule_id="magnetic_concentrator_completion", *, catalog=None, definitions=None):
    """Restituisce un esito spiegato; non salva dati e non invia messaggi."""
    root = SOURCE_DIR
    if catalog is None:
        catalog = json.loads((root / "catalog.json").read_text(encoding="utf-8"))
    if definitions is None:
        definitions = json.loads((root / "rules.json").read_text(encoding="utf-8"))
    rule = next((r for r in definitions["rules"] if r["id"] == rule_id), None)
    if rule is None:
        raise ValueError("Regola sconosciuta.")
    supported_relationships = {
        "ACCESSORY_COMPLETION", "USE_CASE_COMPLEMENT", "CATEGORY_EXPANSION",
        "REPLENISHMENT", "REPLACEMENT"
    }
    if rule["status"] != "approved_for_manual_pilot" or rule["relationship_type"] not in supported_relationships:
        raise ValueError("Regola non approvata o comportamento non supportato.")
    policies = definitions["shared_policies"]
    timing = rule.get("timing", policies["accessory_timing"])
    today = _day(evaluation_date)
    customer_id = customer["customer_id"]
    if not isinstance(customer_id, str) or not customer_id:
        raise ValueError("customer_id deve essere una stringa non vuota.")
    for field in ("history_complete", "contact_history_complete", "do_not_contact"):
        if field in customer and type(customer[field]) is not bool:
            raise ValueError(f"{field} deve essere booleano.")

    variants = {}
    for product in catalog["products"]:
        for variant in product["variants"]:
            if variant["sku"] in variants:
                raise ValueError("SKU duplicato nel catalogo.")
            variants[variant["sku"]] = (product, variant)
    if rule["relationship_type"] == "REPLENISHMENT":
        return _evaluate_replenishment(
            customer, evaluation_date, today, catalog, definitions,
            rule, policies, variants,
        )
    if rule["relationship_type"] == "REPLACEMENT":
        return _evaluate_replacement(
            customer, evaluation_date, today, catalog, definitions,
            rule, policies, variants,
        )
    target_skus = rule.get("target_skus", [rule.get("target_sku")])
    if not target_skus or any(sku not in variants for sku in target_skus):
        raise ValueError("SKU destinazione mancante dal catalogo.")
    target_product = variants[target_skus[0]][0]
    target_variant = min(
        (variants[sku][1] for sku in target_skus),
        key=lambda variant: (variant["observed_price_minor"], variant["sku"]),
    )
    component = rule["exclusions"]["target_component_in_known_purchased_configuration"]
    checks = list(policies["operator_checks"]) + list(rule.get("operator_checks", []))
    evidence = []
    result = {
        "customer_id": customer_id,
        "opportunity_key": [customer_id, rule["id"]],
        "rule_id": rule["id"],
        "rule_version": rule["version"],
        "rules_version": definitions["version"],
        "catalog_version": catalog["version"],
        "evaluation_date": evaluation_date,
        "target_sku": target_variant["sku"],
        "target_product": variants[target_variant["sku"]][0]["key"],
        "relationship_type": rule["relationship_type"],
        "commercial_track": rule["commercial_track"],
        "plan_rank": rule["plan_rank"],
        "plan_rank_reason": rule["plan_rank_reason"],
        "rationale": rule["rationale"],
        "benefit": target_product["declared_benefit"],
        "nominal_value_minor": target_variant["observed_price_minor"],
        "currency": target_variant["currency"],
        "price_basis": "catalog_observed_price",
        "operator_checks": checks,
        "evidence": evidence,
        "contact_count": 0,
        "first_contact_date": None,
        "eligible_from_date": None,
    }
    if len(target_skus) > 1:
        result["target_options"] = [
            {
                "sku": sku,
                "product_key": variants[sku][0]["key"],
                "product_name": variants[sku][0]["name"],
                "color": variants[sku][1].get("color"),
                "configuration": variants[sku][1].get("configuration"),
                "observed_price_minor": variants[sku][1]["observed_price_minor"],
                "currency": variants[sku][1]["currency"],
            }
            for sku in target_skus
        ]
        result["target_selection"] = rule["target_selection"]

    def finish(status, reason, next_date=None):
        result.update(status=status, reason=reason,
                      next_contact_date=next_date.isoformat() if next_date else None)
        result["operator_checks"] = sorted(set(checks))
        result["evidence"] = sorted(evidence, key=lambda item: (item["id"], item["kind"]))
        return result

    if not customer.get("history_complete", False):
        checks.append("Storico acquisti incompleto: verificare acquisti e dotazioni precedenti.")
    if not customer.get("contact_history_complete", False):
        checks.append("Storico contatti incompleto: verificare i precedenti tentativi per questa proposta.")

    sources = []
    undated_source = False
    target_observed = False
    target_category_observed = False
    excluded_target_category = rule["exclusions"].get("target_category_in_purchase_history")
    unknown_skus = False
    for purchase in _unique_records(customer.get("purchases", [])):
        validity = purchase.get("validity", "unknown")
        if validity not in {"valid", "unknown", "cancelled", "returned"}:
            raise ValueError("Validità della riga acquisto non riconosciuta.")
        purchased_on = _day(purchase["date"]) if purchase.get("date") else None
        if purchased_on and purchased_on > today:
            continue
        if validity in {"cancelled", "returned"}:
            continue
        if validity == "unknown":
            checks.append("Verificare validità, resi, annullamenti ed evasione delle righe con stato sconosciuto.")
        if not purchased_on:
            checks.append("Verificare la data delle righe acquisto prive di data.")
        sku = purchase.get("sku")
        if sku not in variants:
            unknown_skus = True
            checks.append("SKU non mappati: verificare prodotto acquistato e dotazione rispetto all'accessorio proposto.")
            continue
        product, variant = variants[sku]
        if excluded_target_category and product.get("category") == excluded_target_category:
            target_category_observed = True
            evidence.append({"id": purchase["id"], "kind": "target_category_purchase",
                             "sku": sku, "date": purchase.get("date"), "validity": validity})
        configuration = next((c for c in product.get("configurations", [])
                              if c["key"] == variant.get("configuration")), None)
        included = {c["key"] for c in configuration["included_components"]} if configuration else set()
        if product.get("provides_component"):
            included.add(product["provides_component"])
        if sku in target_skus or component in included:
            target_observed = True
            evidence.append({"id": purchase["id"], "kind": "target_purchase_or_included_component",
                             "sku": sku, "date": purchase.get("date"), "validity": validity})
        if any(product["key"] == source["product"]
               and variant.get("configuration") == source["configuration"]
               for source in rule["sources"]):
            if purchased_on:
                sources.append((purchased_on, purchase["id"], sku, validity,
                                purchase.get("order_id", purchase["id"])))
            else:
                undated_source = True

    events = []
    for event in _unique_records(customer.get("events", [])):
        if event["rule_id"] != rule["id"]:
            continue
        if event["type"] not in {"contact", "reply", "rejection"}:
            raise ValueError("Tipo evento non riconosciuto.")
        event_day = _day(event["date"])
        if event_day <= today:
            events.append((event_day, event))
    contacts = sorted(day for day, event in events if event["type"] == "contact")
    result["contact_count"] = len(contacts)
    result["first_contact_date"] = contacts[0].isoformat() if contacts else None
    for _, event in events:
        evidence.append({"id": event["id"], "kind": event["type"], "date": event["date"]})

    confirmed = [item for item in sources if item[3] == "valid"]
    selected_source = min(confirmed or sources) if sources else None
    if selected_source:
        result["source_order_id"] = selected_source[4]

    if customer.get("do_not_contact", False):
        return finish("stopped", "Richiesta generale di non essere contattato.")
    if any(event["type"] == "rejection" for _, event in events):
        return finish("stopped", "Rifiuto esplicito della proposta.")
    if target_observed or target_category_observed:
        return finish("excluded", "Prodotto o categoria proposti già presenti negli acquisti o nelle dotazioni osservate; eventuali dubbi vanno verificati.")
    if len(contacts) >= policies["follow_up"]["maximum_contacts"]:
        return finish("stopped", "Numero massimo di tentativi raggiunto; nessuna riapertura automatica.")
    if not sources:
        if undated_source or unknown_skus or not customer.get("history_complete", False):
            return finish("insufficient_data", "Manca un acquisto datato e riconoscibile della configurazione richiesta dalla regola.")
        return finish("no_action", "Nessun acquisto valido della configurazione richiesta dalla regola nello storico fornito.")

    # Preferire gli acquisti confermati validi; se mancano, usare un candidato
    # con validità sconosciuta solo sottoponendolo a verifica dell'operatore.
    purchased_on, purchase_id, sku, validity, source_order_id = selected_source
    result["source_purchase_id"] = purchase_id
    result["source_order_id"] = source_order_id
    result["source_purchase_date"] = purchased_on.isoformat()
    result["days_since_purchase"] = (today - purchased_on).days
    evidence.append({"id": purchase_id, "kind": "source_purchase", "sku": sku,
                     "date": purchased_on.isoformat(), "validity": validity})
    annual_windows = timing.get("annual_windows")
    available_on = (_next_annual_window_day(purchased_on, annual_windows)
                    if annual_windows else
                    purchased_on + timedelta(days=timing["minimum_days_inclusive"]))
    result["eligible_from_date"] = available_on.isoformat()
    if any(event["type"] == "reply" for _, event in events):
        return finish("operator_response", "Risposta ricevuta: l'operatore gestisce la conversazione, senza sollecito automatico.")
    if annual_windows:
        retry_on = (contacts[0] + timedelta(days=policies["follow_up"]["retry_after_calendar_days"])
                    if contacts else available_on)
        next_on = _next_annual_window_day(max(today, available_on, retry_on), annual_windows)
        if today < next_on:
            return finish("deferred", "Attendere la prossima finestra stagionale valida per il Mini.", next_on)
        if contacts:
            return finish("second_contact_review", "Secondo e ultimo tentativo valutabile nella finestra stagionale.")
        return finish("first_contact_review", "Primo contatto valutabile nella finestra stagionale.")
    if today < available_on:
        return finish("deferred", "Non sono ancora trascorsi i giorni richiesti dall'acquisto.", available_on)
    if contacts:
        retry_on = contacts[0] + timedelta(days=policies["follow_up"]["retry_after_calendar_days"])
        if today < retry_on:
            return finish("deferred", "Attendere prima del secondo contatto.", retry_on)
        return finish("second_contact_review", "Secondo e ultimo tentativo valutabile: nessuna risposta o acquisto osservato.")
    return finish("first_contact_review", "Primo contatto valutabile: timing raggiunto e accessorio proposto non osservato nello storico disponibile.")


def _visible_events(customer, evaluation_date):
    events = []
    for event in _unique_records(customer.get("events", [])):
        if event["type"] not in {
            "contact", "reply", "rejection", "product_interest", "product_rejection",
            "plan_rejection", "conversation_closed", "verified_purchase",
            "revenue_correction", "do_not_contact",
        }:
            raise ValueError("Tipo evento non riconosciuto.")
        if event["type"] in {"product_interest", "product_rejection",
                             "plan_rejection", "conversation_closed"}:
            if not event.get("plan_key"):
                raise ValueError("L'esito richiede il plan_key.")
            if event["type"].startswith("product_") and not event.get("product_key"):
                raise ValueError("L'esito prodotto richiede product_key.")
        if _day(event["date"]) <= _day(evaluation_date):
            events.append((_day(event["date"]), event))
    return sorted(events, key=lambda item: (item[0], item[1]["id"]))


def _commercial_snapshot(customer, events):
    """Gli esiti per prodotto/piano sono coordinati nel portafoglio."""
    closed = {}
    for day, event in events:
        if event["type"] == "conversation_closed":
            closed[tuple(event["plan_key"])] = day
    retained = []
    for day, event in events:
        if event["type"] not in {"contact", "reply", "rejection"}:
            continue
        if event["type"] == "reply" and day <= closed.get(tuple(event.get("plan_key", [])), date.min):
            continue
        retained.append(event)
    return {**customer, "events": retained,
            "do_not_contact": customer.get("do_not_contact", False) or any(event["type"] == "do_not_contact" for _, event in events)}


def _contact_permission(customer, *, definitions=None):
    if definitions is None:
        definitions = json.loads((SOURCE_DIR / "rules.json").read_text(encoding="utf-8"))
    policy = definitions["shared_policies"]["marketing_consent"]
    channel = customer.get("contact_channel")
    consent = customer.get("marketing_consent", {}).get(channel, {})
    status = consent.get("status", "unknown")
    allowed = bool(channel) and status == policy["accepted_status"] and not customer.get("do_not_contact", False)
    return {
        "channel": channel, "consent_status": status, "allowed": allowed,
        "reason": ("Consenso marketing valido; ricontrollare prima del contatto."
                   if allowed else "Contatto bloccato: consenso marketing mancante/non valido per il canale, oppure richiesta di non contatto."),
    }


def _apply_permission(result, permission):
    result["contact_permission"] = permission
    if not permission["allowed"] and result["status"] in {
        "first_contact_review", "second_contact_review", "deferred", "operator_response",
    }:
        result["commercial_status"] = result["status"]
        result["status"] = "blocked_consent"
        result["reason"] = permission["reason"]
        result["next_contact_date"] = None
    return result


def commercial_category(rule, definitions):
    """Natura commerciale approvata, distinta dall'attuabilità del contatto."""
    return ("targeted" if rule["relationship_type"] in
            definitions["operational_views"]["targeted_rule_types"] else "test")


def contact_sequence_delay(rule):
    """Attesa dal primo contatto accessori per il recupero degli ordini storici."""
    timing = rule.get("timing", {})
    if timing.get("reference") != "first_accessory_contact_or_source_purchase_without_applicable_accessories":
        return None
    return timing["minimum_days_inclusive"]


def evaluate(customer, evaluation_date, rule_id="magnetic_concentrator_completion"):
    """Diagnostica commerciale della regola, con blocco consenso per ogni canale."""
    events = _visible_events(customer, evaluation_date)
    snapshot = _commercial_snapshot(customer, events)
    return _apply_permission(_evaluate(snapshot, evaluation_date, rule_id), _contact_permission(snapshot))


def _contact_plan_closure(plan_events, contact_count, presented_results, maximum_contacts):
    """Unico criterio di chiusura dei piani contattati, anche per il monitoraggio."""
    if any(event["type"] == "verified_purchase" for _, event in plan_events):
        return "verified_purchase"
    if any(event["type"] in {"plan_rejection", "rejection"} for _, event in plan_events):
        return "plan_rejection"
    if contact_count >= maximum_contacts:
        return "attempts_exhausted"
    if any(result["status"] in {"excluded", "stopped"} for result in presented_results):
        return "not_eligible"
    return None


def evaluate_portfolio(customer, evaluation_date, *, catalog=None, definitions=None, promotions=None):
    """Costruisce piani di contatto e ne sceglie uno, senza inviare messaggi."""
    root = SOURCE_DIR
    if definitions is None:
        definitions = json.loads((root / "rules.json").read_text(encoding="utf-8"))
    if catalog is None:
        catalog = json.loads((root / "catalog.json").read_text(encoding="utf-8"))
    annual_windows_by_rule = {
        rule["id"]: rule.get("timing", {}).get("annual_windows")
        for rule in definitions["rules"]
    }
    promotions_version, active_promotions = _promotions_on(evaluation_date, definitions=promotions)
    policy = definitions["shared_policies"]["cross_opportunity_coordination"]
    today = _day(evaluation_date)
    visible_events = _visible_events(customer, evaluation_date)
    snapshot = _commercial_snapshot(customer, visible_events)
    results = [_evaluate(snapshot, evaluation_date, rule["id"], catalog=catalog, definitions=definitions)
               for rule in definitions["rules"]]
    rules_by_id = {rule["id"]: rule for rule in definitions["rules"]}
    for result in results:
        result["commercial_category"] = commercial_category(rules_by_id[result["rule_id"]], definitions)

    def opportunity_token(value):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))

    def plan_key(result):
        order_id = result.get("cycle_reference_order_id", result.get("source_order_id"))
        return [order_id, result["commercial_track"], result["eligible_from_date"]]

    def plan_token(value):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))

    def rank_key(result):
        return (result["commercial_category"] != "targeted", -result["promotion_active"], -result["nominal_value_minor"],
                -result["plan_rank"], result["rule_id"])

    contact_dates = [day for day, event in visible_events if event["type"] == "contact"]

    locked_primary_by_plan = {}
    presented_by_plan = {}
    for _, event in visible_events:
        if event["type"] != "contact" or not event.get("plan_key"):
            continue
        token = plan_token(event["plan_key"])
        primary_key = event.get("primary_opportunity_key")
        included_keys = event.get("included_opportunity_keys", [])
        if primary_key:
            locked_primary_by_plan.setdefault(token, opportunity_token(primary_key))
        presented_by_plan.setdefault(token, set()).update(
            opportunity_token(key) for key in included_keys
        )

    candidate_statuses = {
        "first_contact_review", "second_contact_review", "deferred", "operator_response"
    }
    grouped = {}
    for result in results:
        if result["status"] not in candidate_statuses or not result.get("eligible_from_date"):
            continue
        key = plan_key(result)
        grouped.setdefault(plan_token(key), {"key": key, "results": []})["results"].append(result)

    product_by_sku = {
        variant["sku"]: product["key"]
        for product in catalog["products"] for variant in product["variants"]
    }
    product_names = {product["key"]: product["name"] for product in catalog["products"]}
    plans = []
    suppressed_opportunities = []
    results_by_opportunity = {
        opportunity_token(result["opportunity_key"]): result for result in results
    }
    represented_keys = set()
    follow_up = definitions["shared_policies"]["follow_up"]
    for token, group in grouped.items():
        group_results = group["results"]
        presented = presented_by_plan.get(token, set())
        plan_events = [(day, event) for day, event in visible_events
                       if event.get("plan_key") == group["key"]]
        contacts = [day for day, event in plan_events if event["type"] == "contact"]
        closed_conversation = max(
            (day for day, event in plan_events if event["type"] == "conversation_closed"),
            default=date.min,
        )
        rejected_products = {
            event["product_key"] for _, event in plan_events
            if event["type"] == "product_rejection"
        }
        interests = [(day, event) for day, event in plan_events
                     if event["type"] == "product_interest"
                     and event["product_key"] not in rejected_products]
        focus_product = interests[-1][1]["product_key"] if interests else None
        plan_closed = _contact_plan_closure(
            plan_events, len(contacts),
            [results_by_opportunity[key] for key in presented if key in results_by_opportunity],
            follow_up["maximum_contacts"],
        ) is not None
        candidates = []
        for result in group_results:
            output = result.copy()
            options = result.get("target_options") or [{
                "sku": result["target_sku"],
                "product_key": product_by_sku[result["target_sku"]],
                "observed_price_minor": result["nominal_value_minor"],
            }]
            remaining = [option.copy() for option in options
                         if option.get("product_key", product_by_sku[option["sku"]]) not in rejected_products]
            if plan_closed or not remaining:
                output["coordination_status"] = (
                    "suppressed_after_contact_plan_closed" if plan_closed else "product_rejected"
                )
                output["coordination_reason"] = (
                    "Piano chiuso: le altre proposte presentate non avviano sequenze separate."
                    if plan_closed else "Prodotto rifiutato; le altre proposte del piano restano disponibili."
                )
                suppressed_opportunities.append(output)
                continue
            for option in remaining:
                if option["sku"] in active_promotions:
                    option["promotion"] = active_promotions[option["sku"]].copy()
            promoted = [option for option in remaining if "promotion" in option]
            output["promotion_active"] = bool(promoted)
            output["target_options"] = remaining
            if promoted:
                output["operator_checks"] = sorted(set([
                    *output["operator_checks"],
                    "Promozione pianificata: verificare che sia attiva e confermare il prezzo prima della proposta.",
                ]))
            preferred = promoted or remaining
            cheapest = min(preferred, key=lambda option: (
                option["promotion"]["price_minor"] if "promotion" in option
                else option["observed_price_minor"], option["sku"]))
            output["target_sku"] = cheapest["sku"]
            output["catalog_observed_price_minor"] = cheapest["observed_price_minor"]
            output["nominal_value_minor"] = (
                cheapest["promotion"]["price_minor"] if "promotion" in cheapest
                else cheapest["observed_price_minor"])
            output["price_basis"] = ("planned_promotion_price" if promoted
                                     else output["price_basis"])
            output["target_product"] = product_by_sku[cheapest["sku"]]
            candidates.append(output)
        represented_keys.update(opportunity_token(result["opportunity_key"]) for result in group_results)
        if not candidates:
            continue
        focused = [result for result in candidates if focus_product in {
            product_by_sku[option["sku"]]
            for option in result.get("target_options", [{"sku": result["target_sku"]}])
        }]
        locked = locked_primary_by_plan.get(token)
        primary = (min(focused, key=rank_key) if focused else
                   next((result for result in candidates
                         if opportunity_token(result["opportunity_key"]) == locked),
                        min(candidates, key=rank_key)))
        secondaries = sorted((result for result in candidates if result is not primary), key=rank_key)
        primary_output = primary.copy()
        primary_output["contact_role"] = "primary"
        if focused and "target_options" in primary_output:
            primary_output["target_options"] = [option for option in primary_output["target_options"]
                                                if product_by_sku[option["sku"]] == focus_product]
            preferred = [option for option in primary_output["target_options"]
                         if "promotion" in option] or primary_output["target_options"]
            cheapest = min(preferred, key=lambda option: (
                option["promotion"]["price_minor"] if "promotion" in option
                else option["observed_price_minor"], option["sku"]))
            primary_output.update(target_sku=cheapest["sku"], target_product=focus_product,
                                  nominal_value_minor=(cheapest["promotion"]["price_minor"]
                                                       if "promotion" in cheapest else
                                                       cheapest["observed_price_minor"]))
        for result in secondaries:
            result["contact_role"] = ("presented_secondary" if opportunity_token(result["opportunity_key"]) in presented
                                      else "secondary_suggestion")
        unresolved = any(day > closed_conversation and event["type"] in {
            "reply", "product_interest", "product_rejection"
        } for day, event in plan_events)
        raw_status = primary["status"]
        raw_next = primary["next_contact_date"]
        count = len(contacts) if contacts else primary["contact_count"]
        first_contact = min(contacts).isoformat() if contacts else primary["first_contact_date"]
        if unresolved:
            raw_status, raw_next = "operator_response", None
        elif contacts and raw_status != "operator_response":
            retry_on = max(contacts) + timedelta(days=follow_up["retry_after_calendar_days"])
            annual_windows = annual_windows_by_rule[primary["rule_id"]]
            if annual_windows:
                retry_on = _next_annual_window_day(max(today, retry_on), annual_windows)
            raw_status = "deferred" if today < retry_on else "second_contact_review"
            raw_next = retry_on.isoformat() if today < retry_on else None
        primary_output.update(status=raw_status, next_contact_date=raw_next,
                              contact_count=count, first_contact_date=first_contact)
        if unresolved:
            primary_output["reason"] = "Esito ricevuto: gestire la conversazione sul prodotto e registrarne la chiusura."
        elif contacts and raw_status == "deferred":
            primary_output["reason"] = "Attendere almeno 15 giorni dall'ultimo contatto del piano."
        elif contacts and raw_status == "second_contact_review":
            primary_output["reason"] = "Secondo e ultimo tentativo del piano, con i prodotti ancora pertinenti."
        source_dates = [_day(result.get("cycle_reference_purchase_date", result["source_purchase_date"]))
                        for result in group_results]
        plans.append({
            "plan_key": group["key"], "source_order_id": group["key"][0],
            "commercial_track": group["key"][1], "eligible_from_date": group["key"][2],
            "source_purchase_date": min(source_dates).isoformat(),
            "plan_rank": primary["plan_rank"], "primary_opportunity": primary_output,
            "secondary_opportunities": [] if focused else secondaries,
            "other_available_opportunities": secondaries if focused else [],
            "focus_product": focus_product if focused else None,
            "included_opportunity_keys": [result["opportunity_key"] for result in candidates],
            "raw_status": raw_status, "contact_count": count,
            "first_contact_date": first_contact, "raw_next_contact_date": raw_next,
            "blocking_plan_keys": [],
        })

    # La chiave resta quella originale: cambiare calendario non crea un nuovo piano.
    sequence = definitions["shared_policies"]["hair_dryer_contact_sequence"]["stages"]
    for plan in plans:
        ids = {key[1] for key in plan["included_opportunity_keys"]}
        stage = next((i for i, members in enumerate(sequence) if ids.intersection(members)), None)
        if stage is None or stage == 0:
            continue
        preceding = set(rule_id for members in sequence[:stage] for rule_id in members)
        blockers = [other for other in plans if other is not plan
                    and other["source_order_id"] == plan["source_order_id"]
                    and any(key[1] in preceding for key in other["included_opportunity_keys"])]
        anchor_contacts = [(day, event) for day, event in visible_events if event["type"] == "contact"
                           and event.get("plan_key", [None])[0] == plan["source_order_id"]
                           and any(key[1] in sequence[0] for key in
                                   event.get("included_opportunity_keys", [[None, event.get("rule_id")]]))]
        accessory_pending = any(any(key[1] in sequence[0] for key in other["included_opportunity_keys"])
                                for other in blockers)
        first_accessory_contact = min(anchor_contacts, key=lambda item: (item[0], item[1]["id"])) if anchor_contacts else None
        accessory_maturity = (_day(first_accessory_contact[1]["plan_key"][2]) if first_accessory_contact else
                              min((_day(other["eligible_from_date"]) for other in blockers
                                   if any(key[1] in sequence[0] for key in other["included_opportunity_keys"])), default=None))
        reference_day = first_accessory_contact[0] if first_accessory_contact else today
        recovery = bool(accessory_maturity and (reference_day - accessory_maturity).days >= definitions["overview_activity"]["recent_days"])
        anchor = first_accessory_contact[0].isoformat() if recovery and first_accessory_contact else None
        pending = recovery and not anchor and accessory_pending and not plan["contact_count"]
        for proposal in [plan["primary_opportunity"], *plan["secondary_opportunities"],
                         *plan["other_available_opportunities"]]:
            proposal["contact_timing"] = {"reference_date": anchor, "awaiting_first_contact": pending}
            if anchor:
                days = contact_sequence_delay(rules_by_id[proposal["rule_id"]])
                eligible = max(_day(proposal["eligible_from_date"]), _day(anchor) + timedelta(days=days))
                if plan["contact_count"] and _day(plan["first_contact_date"]) < eligible:
                    # Invio storico già avvenuto: non applicare il nuovo ritardo retroattivamente.
                    proposal["contact_timing"]["reference_date"] = None
                else:
                    proposal["eligible_from_date"] = eligible.isoformat()
        plan["eligible_from_date"] = plan["primary_opportunity"]["eligible_from_date"]
        if plan["contact_count"]:
            continue
        if anchor and today < _day(plan["eligible_from_date"]):
            plan["raw_status"] = "deferred"
            plan["raw_next_contact_date"] = plan["eligible_from_date"]
            plan["primary_opportunity"].update(status="deferred", next_contact_date=plan["eligible_from_date"],
                reason="Attendere la maturazione dal primo contatto accessori effettivamente registrato.")
        if blockers:
            plan["raw_status"] = "waiting_for_plan"
            plan["raw_next_contact_date"] = None
            plan["blocking_plan_keys"] = [other["plan_key"] for other in blockers]
            plan["primary_opportunity"].update(status="waiting_for_plan", next_contact_date=None,
                reason="Attendere la conclusione dei piani precedenti del percorso; non è obbligatorio un acquisto.")

    def contact_day(plan):
        return _day(plan["first_contact_date"]) if plan["first_contact_date"] else date.max

    def ready_key(plan):
        return (
            plan["primary_opportunity"]["commercial_category"] != "targeted",
            -plan["primary_opportunity"]["promotion_active"],
            -bool(annual_windows_by_rule[plan["primary_opportunity"]["rule_id"]]),
            -plan["primary_opportunity"]["nominal_value_minor"],
            _day(plan["eligible_from_date"]),
            -plan["plan_rank"],
            _day(plan["source_purchase_date"]),
            plan["primary_opportunity"]["rule_id"],
        )

    contacted_open = [
        plan for plan in plans
        if plan["raw_status"] == "operator_response"
        or (plan["contact_count"] > 0
            and plan["raw_status"] in {"deferred", "second_contact_review"})
    ] if policy["keep_contacted_opportunity_primary_until_resolved"] else []
    blocking_responses = [
        plan for plan in contacted_open if plan["raw_status"] == "operator_response"
    ] if policy["operator_response_blocks_other_proposals"] else []
    ready = [plan for plan in plans
             if plan["raw_status"] in {"first_contact_review", "second_contact_review"}]
    future = [plan for plan in plans
              if plan["raw_status"] == "deferred" and plan["contact_count"] == 0]

    primary_plan = None
    if blocking_responses:
        primary_plan = min(blocking_responses,
                           key=lambda plan: (contact_day(plan), ready_key(plan)))
    elif contacted_open:
        primary_plan = min(contacted_open,
                           key=lambda plan: (contact_day(plan), ready_key(plan)))
    elif ready:
        primary_plan = min(ready, key=ready_key)
    elif future:
        primary_plan = min(
            future,
            key=lambda plan: (
                _day(plan["raw_next_contact_date"]),
                -plan["plan_rank"],
                _day(plan["source_purchase_date"]),
                plan["primary_opportunity"]["rule_id"],
            ),
        )

    def queue_key(plan):
        if plan in contacted_open:
            return (0, contact_day(plan), -plan["plan_rank"],
                    _day(plan["source_purchase_date"]))
        if plan in ready:
            return (1, *ready_key(plan))
        if plan["raw_status"] == "waiting_for_plan":
            return (3, date.max, -plan["plan_rank"], _day(plan["source_purchase_date"]))
        return (2, _day(plan["raw_next_contact_date"]), -plan["plan_rank"],
                _day(plan["source_purchase_date"]))

    queued = [
        plan.copy() for plan in plans
        if plan is not primary_plan
    ]
    queued.sort(key=queue_key)
    for plan in queued:
        plan["plan_status"] = "queued"
        plan["plan_reason"] = ("Attendere la conclusione dei piani precedenti del percorso." if plan["blocking_plan_keys"]
                               else "Un altro piano di contatto ha la precedenza per questo cliente.")

    primary_output = primary_plan.copy() if primary_plan else None
    portfolio_status = "no_opportunity"
    next_contact_date = None
    if primary_output:
        raw_status = primary_output["raw_status"]
        if raw_status == "operator_response":
            portfolio_status = "operator_response"
            primary_output["plan_reason"] = (
                "Risposta in gestione: gli altri piani restano in coda fino alla risoluzione."
            )
        elif raw_status == "deferred":
            portfolio_status = "deferred"
            next_contact_date = primary_output["raw_next_contact_date"]
            primary_output["plan_reason"] = primary_output["primary_opportunity"]["reason"]
        else:
            portfolio_status = "contact_review"
            primary_output["plan_reason"] = (
                "Proseguire il piano già contattato, mantenendo il conteggio comune dei tentativi."
                if primary_output["contact_count"] else
                ("Piano maturo con promozione pianificata pertinente; verificarne l'attivazione."
                 if primary_output["primary_opportunity"]["promotion_active"] else
                 ("Piano maturo nella finestra viaggio in corso."
                  if annual_windows_by_rule[primary_output["primary_opportunity"]["rule_id"]] else
                  "Piano maturo selezionato per categoria commerciale e valore nominale."))
            )
            if not primary_output["contact_count"] and primary_output["primary_opportunity"]["commercial_category"] == "targeted":
                primary_output["plan_reason"] = "Proposta mirata attuabile: precede le proposte da testare, anche in promozione."

        if contact_dates and raw_status in {
            "first_contact_review", "second_contact_review", "deferred"
        }:
            global_allowed_on = max(contact_dates) + timedelta(
                days=policy["minimum_days_between_contacts"]
            )
            if today < global_allowed_on:
                portfolio_status = "deferred"
                rule_allowed_on = _day(next_contact_date) if next_contact_date else today
                if global_allowed_on >= rule_allowed_on:
                    annual_windows = annual_windows_by_rule[
                        primary_output["primary_opportunity"]["rule_id"]
                    ]
                    next_contact_date = (
                        _next_annual_window_day(global_allowed_on, annual_windows)
                        if annual_windows else global_allowed_on
                    ).isoformat()
                    primary_output["plan_reason"] = (
                        "Attendere il limite comune tra contatti relativi a qualsiasi piano."
                    )
        primary_output["plan_status"] = portfolio_status
        primary_output["plan_next_contact_date"] = next_contact_date

    permission = _contact_permission(snapshot, definitions=definitions)
    if not permission["allowed"]:
        portfolio_status = "blocked_consent"
        next_contact_date = None
        for plan in ([primary_output] if primary_output else []) + queued:
            plan["plan_status"] = "blocked_consent"
            plan["plan_reason"] = permission["reason"]
            plan["plan_next_contact_date"] = None
    timeline = []
    for plan in ([primary_output] if primary_output else []) + queued:
        earliest = max(_day(plan["eligible_from_date"]),
                       _day(plan["raw_next_contact_date"]) if plan["raw_next_contact_date"] else date.min,
                       max(contact_dates) + timedelta(days=policy["minimum_days_between_contacts"])
                       if contact_dates else date.min)
        annual_windows = annual_windows_by_rule[plan["primary_opportunity"]["rule_id"]]
        if annual_windows:
            earliest = _next_annual_window_day(earliest, annual_windows)
        blockers = list(plan["blocking_plan_keys"])
        if plan in queued and primary_output:
            blockers.append(primary_output["plan_key"])
        state = plan["plan_status"]
        known_date = (max(earliest, today).isoformat() if permission["allowed"] and not blockers
                      and state != "operator_response" else None)
        plan["earliest_contact_date"] = earliest.isoformat()
        plan["plan_next_contact_date"] = known_date
        plan["blocking_plan_keys"] = blockers
        proposals = [plan["primary_opportunity"], *plan["secondary_opportunities"]]
        for proposal in proposals + plan.get("other_available_opportunities", []):
            _apply_permission(proposal, permission)
        if plan["commercial_track"] == "hair_care":
            source_ids = {item["source_purchase_id"] for item in proposals}
            sources = []
            for purchase in customer["purchases"]:
                if purchase["id"] not in source_ids:
                    continue
                product = next(item for item in catalog["products"]
                               if item["key"] == product_by_sku[purchase["sku"]])
                variant = next(item for item in product["variants"]
                               if item["sku"] == purchase["sku"])
                configuration = next((item["label"] for item in product.get("configurations", [])
                                      if item["key"] == variant.get("configuration")), None)
                sources.append({"purchase_id": purchase["id"], "sku": purchase["sku"],
                                "product_name": product["name"], "configuration": configuration,
                                "purchase_date": purchase["date"],
                                "elapsed_days": (today - _day(purchase["date"])).days})
            sources.sort(key=lambda item: (item["purchase_date"], item["purchase_id"]))
            primary = plan["primary_opportunity"]
            if plan["focus_product"]:
                selection_reason = "Interesse esplicito del cliente per il prodotto."
            elif plan["contact_count"]:
                selection_reason = "Proposta del piano già contattato, mantenuta fino alla risoluzione."
            elif primary["commercial_category"] == "targeted":
                selection_reason = "Proposta mirata prima dei complementi da testare; poi promozione e valore nominale."
            elif primary["promotion_active"]:
                selection_reason = "Promozione pertinente; a parità prevalgono valore nominale e criteri di spareggio."
            elif len(proposals) == 1:
                selection_reason = "Unica proposta rimasta nel piano."
            else:
                selection_reason = "Valore nominale più alto; a parità prevalgono rango commerciale e ID della regola."
            plan["presentation"] = {
                "title": "Accessori da proporre", "layout": "uniform_product_list",
                "source_purchases": sources,
                "eligible_from_date": plan["eligible_from_date"],
                "minimum_days": definitions["shared_policies"]["accessory_timing"]["minimum_days_inclusive"],
                "instruction": "Presentali nella stessa email come opzioni acquistabili singolarmente.",
                "primary_selection_reason": selection_reason,
                "purchase_probability": None,
                "products": [{"rule_id": item["rule_id"], "role": item["contact_role"],
                              "product_name": product_names[product_by_sku[item["target_sku"]]],
                              "target_sku": item["target_sku"], "rationale": item["rationale"],
                              "nominal_value_minor": item["nominal_value_minor"],
                              "currency": item["currency"], "price_basis": item["price_basis"],
                              "promotion_active": item["promotion_active"]} for item in proposals],
            }
        awaiting_anchor = plan["primary_opportunity"].get("contact_timing", {}).get("awaiting_first_contact", False)
        timeline.append({
            "plan_key": plan["plan_key"], "state": state,
            "reason": plan["plan_reason"], "eligible_from_date": None if awaiting_anchor else plan["eligible_from_date"],
            "earliest_contact_date": None if awaiting_anchor else earliest.isoformat(), "next_contact_date": known_date,
            "blocking_plan_keys": blockers,
            "presentation": plan.get("presentation"),
            "proposals": [{"rule_id": item["rule_id"], "role": item["contact_role"],
                           "target_sku": item["target_sku"], "rationale": item["rationale"],
                           "target_product_name": product_names[product_by_sku[item["target_sku"]]],
                           "target_options": item.get("target_options", []),
                           "promotion_active": item["promotion_active"],
                           "operator_checks": item["operator_checks"]} for item in proposals],
        })
    timeline.sort(key=lambda item: (item["eligible_from_date"] or item["plan_key"][2], item["plan_key"]))
    for result in results + suppressed_opportunities:
        _apply_permission(result, permission)
    contacted_plans = []
    for token, presented in presented_by_plan.items():
        plan_events = [(day, event) for day, event in visible_events
                       if event.get("plan_key") and plan_token(event["plan_key"]) == token]
        contacts = [(day, event) for day, event in plan_events if event["type"] == "contact"]
        current = next((plan for plan in [primary_output, *queued]
                        if plan and plan_token(plan["plan_key"]) == token), None)
        closure = _contact_plan_closure(
            plan_events, len(contacts),
            [results_by_opportunity[key] for key in presented if key in results_by_opportunity],
            follow_up["maximum_contacts"],
        )
        if not closure and not current:
            closure = "not_eligible"
        contacted_plans.append({
            "plan_key": contacts[0][1]["plan_key"],
            "contact_count": len(contacts), "maximum_contacts": follow_up["maximum_contacts"],
            "last_contact_date": max(day for day, _ in contacts).isoformat(),
            "state": "closed" if closure else "in_progress", "outcome": closure,
            "current_plan": current,
            "primary_opportunity_key": contacts[0][1]["primary_opportunity_key"],
            "rule_id": contacts[0][1]["rule_id"],
            "events": [event for _, event in plan_events],
        })
    return {
        "customer_id": customer["customer_id"],
        "evaluation_date": evaluation_date,
        "rules_version": definitions["version"],
        "promotions_version": promotions_version,
        "contact_permission": permission,
        "operator_timeline": timeline,
        "contacted_plans": contacted_plans,
        "portfolio_status": portfolio_status,
        "last_contact_date": max(contact_dates).isoformat() if contact_dates else None,
        "next_contact_date": next_contact_date,
        "primary_contact_plan": primary_output,
        "queued_contact_plans": queued,
        "suppressed_opportunities": suppressed_opportunities,
        "other_results": [
            result for result in results
            if opportunity_token(result["opportunity_key"]) not in represented_keys
        ],
    }


def format_operator_view(portfolio):
    """Presentazione testuale dei risultati canonici; nessuna decisione commerciale."""
    permission = portfolio["contact_permission"]
    lines = [
        f"Cliente: {portfolio['customer_id']} | Valutazione: {portfolio['evaluation_date']}",
        f"Canale: {permission['channel'] or 'non specificato'} | Consenso: {permission['consent_status']}",
        permission["reason"],
        f"Ultimo contatto: {portfolio['last_contact_date'] or 'nessuno registrato'}",
        "", "| Dal | Stato | Prossimo contatto | Proposte | Motivo |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in portfolio["operator_timeline"]:
        names = []
        for proposal in item["proposals"]:
            labels = list(dict.fromkeys(option.get("product_name", option["sku"])
                                       for option in proposal["target_options"]))
            names.append(f"{proposal['role']}: {', '.join(labels) or proposal['target_product_name']}")
        cells = [item["eligible_from_date"] or "in attesa del primo contatto accessori", item["state"],
                 item["next_contact_date"] or "da rivalutare", "; ".join(names), item["reason"]]
        lines.append("| " + " | ".join(str(cell).replace("|", "/").replace("\n", " ") for cell in cells) + " |")
    for item in portfolio["operator_timeline"]:
        for proposal in item["proposals"]:
            for option in proposal["target_options"]:
                if "promotion" in option:
                    campaign = option["promotion"]
                    name = option.get("product_name", proposal["target_product_name"])
                    lines.append(
                        f"\nPromo {name} [{option['sku']}]: "
                        f"{campaign['price_minor'] / 100:.2f} {campaign['currency']} "
                        f"({campaign['starts_on']}–{campaign['ends_on']}, {campaign['status']}); "
                        f"catalogo {option['observed_price_minor'] / 100:.2f} {option['currency']}"
                    )
            lines.append(f"\nControlli per {proposal['target_product_name']}:")
            lines.extend(f"- {check}" for check in proposal["operator_checks"])
    for result in portfolio["suppressed_opportunities"]:
        lines.append(f"Esclusa dal piano: {result['rule_id']} - {result['coordination_reason']}")
    for result in portfolio["other_results"]:
        lines.append(f"{result['rule_id']}: {result['status']} - {result['reason']}")
    return "\n".join(lines)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("customer_json", type=Path)
    parser.add_argument("--as-of", required=True, help="Data locale Europe/Rome, YYYY-MM-DD")
    parser.add_argument("--rule", default="magnetic_concentrator_completion", help="ID della regola da valutare")
    parser.add_argument("--portfolio", action="store_true", help="Coordina tutte le proposte del cliente")
    parser.add_argument("--operator-view", action="store_true", help="Mostra il percorso operatore come tabella testuale")
    args = parser.parse_args()
    snapshot = json.loads(args.customer_json.read_text(encoding="utf-8-sig"))
    output = evaluate_portfolio(snapshot, args.as_of) if args.portfolio or args.operator_view else evaluate(snapshot, args.as_of, args.rule)
    print(format_operator_view(output) if args.operator_view else json.dumps(output, ensure_ascii=False, indent=2))
