"""Aplica decisiones aprobadas a Odoo.

Trigger: GitHub Actions detecta nuevo fichero en `decisions/YYYY-MM-DD-HHMMSS.json.enc`
y lanza este script.

Variables de entorno:
  ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD
  GMAIL_APP_PASS  (descifra el fichero)

Args:
  python apply.py <path/to/decisions.json.enc>
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from odoo_client import Odoo
from crypto import decrypt_json

MAX_PER_RUN = 100  # safety cap


def apply_decisions(odoo: Odoo, decisions: dict):
    """Aplica una lista de cambios. Estructura esperada:
       {"date": "2026-04-29",
        "items": [
            {"model": "sale.order|crm.lead|res.partner", "id": 123,
             "new_user_id": 9, "current_user_id": 6, "reason": "..."},
            ...
        ]}
    """
    items = decisions.get("items", [])
    if len(items) > MAX_PER_RUN:
        raise RuntimeError(f"Más de {MAX_PER_RUN} cambios ({len(items)}) - aborto por seguridad")

    results = {"ok": [], "skipped": [], "failed": []}

    for it in items:
        model = it["model"]
        rec_id = int(it["id"])
        new_uid = int(it["new_user_id"])
        try:
            cur = odoo.read(model, [rec_id], ["user_id", "name"])
            if not cur:
                results["skipped"].append({**it, "reason_skip": "record no existe"})
                continue
            cur_uid = cur[0].get("user_id")
            cur_uid_id = cur_uid[0] if isinstance(cur_uid, list) else cur_uid
            if cur_uid_id == new_uid:
                results["skipped"].append({**it, "reason_skip": "ya está asignado"})
                continue
            odoo.write(model, [rec_id], {"user_id": new_uid})
            results["ok"].append({
                **it,
                "applied_at": datetime.now(timezone.utc).isoformat(),
                "previous_user_id": cur_uid_id,
                "name": cur[0].get("name"),
            })
            print(f"[apply] OK {model} {rec_id}: {cur_uid_id} -> {new_uid}", flush=True)
        except Exception as e:
            results["failed"].append({**it, "error": str(e)})
            print(f"[apply] FAIL {model} {rec_id}: {e}", flush=True)

    return results


def main():
    if len(sys.argv) < 2:
        print("Uso: python apply.py <decisions.json.enc>", file=sys.stderr)
        sys.exit(2)
    enc_path = Path(sys.argv[1])
    blob = json.loads(enc_path.read_text())
    pw = os.environ["GMAIL_APP_PASS"]
    decisions = decrypt_json(blob, pw)
    print(f"[apply] decisions de {decisions.get('date')}, {len(decisions.get('items', []))} items",
          flush=True)

    odoo = Odoo()
    print(f"[odoo] uid={odoo.uid}", flush=True)

    results = apply_decisions(odoo, decisions)

    # Guardar resultados (sin cifrar, contiene info útil para auditoría sin secretos)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    out_path = Path("results") / f"{today}-{enc_path.stem}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    summary = {
        "decision_file": str(enc_path),
        "applied_at": datetime.now(timezone.utc).isoformat(),
        "totals": {
            "ok": len(results["ok"]),
            "skipped": len(results["skipped"]),
            "failed": len(results["failed"]),
        },
        "results": results,
    }
    out_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"[apply] OK={summary['totals']['ok']}  "
          f"SKIP={summary['totals']['skipped']}  "
          f"FAIL={summary['totals']['failed']}", flush=True)
    print(f"[write] {out_path}", flush=True)

    if "GITHUB_OUTPUT" in os.environ:
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"ok={summary['totals']['ok']}\n")
            f.write(f"skipped={summary['totals']['skipped']}\n")
            f.write(f"failed={summary['totals']['failed']}\n")
            f.write(f"results_file={out_path}\n")


if __name__ == "__main__":
    main()
