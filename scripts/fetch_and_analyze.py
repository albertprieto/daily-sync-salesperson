"""Pipeline nocturno: fetch Odoo → analyze → encrypt → escribe en docs/data/.

Variables de entorno:
  ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD  (acceso Odoo)
  GMAIL_APP_PASS                                (cifra el output)

Output:
  docs/data/YYYY-MM-DD.json.enc   (cifrado, expuesto vía Pages)
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from odoo_client import Odoo
from decide import analyze
from crypto import encrypt_json

# --- Config (idéntico al daily_sync.py original) ---
COMMERCIALS_ACTIVE   = [6, 9, 881, 3854, 845, 738, 4528]
COMMERCIALS_HISTORIC = [4307, 4308, 4309]
SDR                  = []
INTERNAL_PARTNERS    = [5, 102139]  # user web, FERIAS-MARKETING

WINDOW_HOURS = 28  # 24h + 4h margen


def m2o(v):
    return v[0] if isinstance(v, list) and v else (v or None)


def m2o_name(v):
    return v[1] if isinstance(v, list) and len(v) > 1 else ""


def fetch_window(odoo: Odoo, since: str, now: str):
    print(f"[fetch] window {since} -> {now}", flush=True)

    # Sale orders por write_date
    so_raw = odoo.search_read(
        "sale.order",
        [["write_date", ">=", since], ["write_date", "<=", now]],
        ["id", "name", "partner_id", "commercial_partner_id", "user_id",
         "create_uid", "state", "date_order", "create_date", "write_date",
         "amount_total", "team_id"],
        limit=1000,
    )
    print(f"[fetch] sale.order: {len(so_raw)}", flush=True)

    # CRM leads por write_date (sin commercial_partner_id, no existe)
    leads_raw = odoo.search_read(
        "crm.lead",
        [["write_date", ">=", since], ["write_date", "<=", now]],
        ["id", "name", "partner_id", "user_id", "create_uid",
         "stage_id", "create_date", "write_date", "team_id"],
        limit=1000,
    )
    print(f"[fetch] crm.lead: {len(leads_raw)}", flush=True)

    # Res partners por CREATE_date (solo nuevos)
    partners_raw = odoo.search_read(
        "res.partner",
        [["create_date", ">=", since], ["create_date", "<=", now]],
        ["id", "name", "is_company", "commercial_partner_id", "user_id",
         "create_uid", "create_date", "write_date", "parent_id"],
        limit=2000,
    )
    print(f"[fetch] res.partner (nuevos): {len(partners_raw)}", flush=True)

    # Normalizar
    new_sos = []
    for r in so_raw:
        new_sos.append({
            "id": r["id"], "name": r.get("name"),
            "partner_id": m2o(r.get("partner_id")),
            "partner_name": m2o_name(r.get("partner_id")),
            "commercial_partner_id": m2o(r.get("commercial_partner_id")),
            "user_id": m2o(r.get("user_id")),
            "create_uid": m2o(r.get("create_uid")),
            "state": r.get("state"),
            "create_date": r.get("create_date"),
            "write_date":  r.get("write_date"),
            "amount_total": r.get("amount_total"),
        })

    new_leads = []
    for r in leads_raw:
        new_leads.append({
            "id": r["id"], "name": r.get("name"),
            "partner_id": m2o(r.get("partner_id")),
            "partner_name": m2o_name(r.get("partner_id")),
            "commercial_partner_id": m2o(r.get("partner_id")),  # fallback (no hay CE en lead)
            "user_id": m2o(r.get("user_id")),
            "create_uid": m2o(r.get("create_uid")),
            "stage_name": m2o_name(r.get("stage_id")),
            "create_date": r.get("create_date"),
            "write_date":  r.get("write_date"),
        })

    new_partners = []
    for r in partners_raw:
        cd = r.get("create_date") or ""
        new_partners.append({
            "id": r["id"], "name": r.get("name"),
            "is_company": r.get("is_company"),
            "commercial_partner_id": m2o(r.get("commercial_partner_id")),
            "user_id": m2o(r.get("user_id")),
            "create_uid": m2o(r.get("create_uid")),
            "create_date": cd,
            "write_date":  r.get("write_date"),
            "parent_id": m2o(r.get("parent_id")),
            "_is_new": cd >= since,
        })

    return new_sos, new_leads, new_partners


def fetch_ce_history(odoo: Odoo, ce_ids: list):
    """Histórico de SOs (todas, no solo en ventana) para los CE involucrados."""
    if not ce_ids:
        return {}
    history = {}
    # Batch en lotes de 200
    for i in range(0, len(ce_ids), 200):
        batch = ce_ids[i:i+200]
        rows = odoo.search_read(
            "sale.order",
            [["commercial_partner_id", "in", batch]],
            ["id", "user_id", "state", "date_order", "amount_total", "commercial_partner_id"],
            limit=10000,
        )
        for r in rows:
            ce = m2o(r.get("commercial_partner_id"))
            if not ce:
                continue
            history.setdefault(str(ce), []).append({
                "so_id": r["id"],
                "user_id": m2o(r.get("user_id")),
                "state": r.get("state"),
                "amount": r.get("amount_total"),
                "date_order": r.get("date_order"),
            })
    print(f"[fetch] ce_history: {sum(len(v) for v in history.values())} entries for {len(history)} CEs",
          flush=True)
    return history


def fetch_lead_activity(odoo: Odoo, lead_ids: list):
    if not lead_ids:
        return {}
    rows = odoo.search_read(
        "mail.message",
        [["model", "=", "crm.lead"], ["res_id", "in", lead_ids]],
        ["id", "author_id", "message_type", "date", "subtype_id", "res_id"],
        limit=10000,
    )
    out = {}
    for r in rows:
        lid = r["res_id"]
        out.setdefault(str(lid), []).append({
            "author_uid": m2o(r.get("author_id")),
            "message_type": r.get("message_type"),
            "date": r.get("date"),
            "kind": "",
        })
    print(f"[fetch] lead_activity: {sum(len(v) for v in out.values())} messages", flush=True)
    return out


def main():
    now_dt = datetime.now(timezone.utc)
    since_dt = now_dt - timedelta(hours=WINDOW_HOURS)
    now = now_dt.strftime("%Y-%m-%d %H:%M:%S")
    since = since_dt.strftime("%Y-%m-%d %H:%M:%S")

    odoo = Odoo()
    print(f"[odoo] uid={odoo.uid}", flush=True)

    new_sos, new_leads, new_partners = fetch_window(odoo, since, now)

    # CEs involucrados (para ce_history)
    ces = set()
    for r in new_sos: ces.add(r.get("commercial_partner_id"))
    for r in new_leads: ces.add(r.get("commercial_partner_id"))
    for r in new_partners: ces.add(r.get("commercial_partner_id") or r["id"])
    ces.discard(None)
    ces.discard(False)
    ce_history = fetch_ce_history(odoo, list(ces))

    lead_ids = [r["id"] for r in new_leads]
    lead_activity = fetch_lead_activity(odoo, lead_ids)

    input_data = {
        "now": now, "since": since,
        "new_sale_orders": new_sos,
        "new_leads": new_leads,
        "new_partners": new_partners,
        "ce_history": ce_history,
        "lead_activity": lead_activity,
        "partner_messages": {},
        "commercials_active":   COMMERCIALS_ACTIVE,
        "commercials_historic": COMMERCIALS_HISTORIC,
        "sdr": SDR,
        "internal_partners": INTERNAL_PARTNERS,
    }

    proposals= analyze(input_data)
    s = proposals["summary"]["total_out"]
    print(f"[analyze] SO={s['sale_order']}  Lead={s['crm_lead']}  "
          f"Partner={s['res_partner']}  SKIP={s['sale_order']}", flush=True)

    # Encrypt y escribir
    pw = os.environ["DAILY_PASS_PHRASE"]
    blob = encrypt_json(proposals, pw)

    today = now_dt.strftime("%Y-%m-%d")
    out_path = Path("docs/data") / f"{today}.json.enc"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(blob, f, indent=2)
    print(f"[write] {out_path}", flush=True)

    meta_path = Path("docs/data") / "index.json"
    meta = {}
    if meta_path.exists():
        meta = json.loads(model_path.read_text())
    meta[today] = {
        "since": since, "now": now,
        "totals": s,
        "file": f"data/{today}.json.enc",
    }
    keys = sorted(meta.keys(), reverse=True)[:90]
    meta = {k: meta[k] for k in keys}
    meta_path.write_text(json.dumps(meta, indent=2))
    print(f"[write] {meta_path}", flush=True)


if __name__ == "__main__":
    main()
