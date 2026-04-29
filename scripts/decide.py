"""Lógica de decisión del Salesperson.

Idéntica a /Users/pc02/Downloads/sales_analysis/daily_sync.py — replicada aquí
para que el repo sea autocontenido. Si cambias la lógica, sincroniza ambos.
"""
from collections import defaultdict


def _set(lst):
    return set(lst or [])


def _decide_by_ce_history(ce_id, ctx):
    active = ctx["commercials_active"]
    historic = ctx["commercials_historic"]
    votes_active = defaultdict(int)
    votes_historic = defaultdict(int)
    for so in ctx["ce_history"].get(str(ce_id), []):
        state = so.get("state")
        uid = so.get("user_id")
        if not uid:
            continue
        w = 3 if state in ("sale", "done") else 1
        if uid in active:
            votes_active[uid] += w
        elif uid in historic:
            votes_historic[uid] += w

    if votes_active:
        best_uid, best_w = max(votes_active.items(), key=lambda x: (x[1], -x[0]))
        total = sum(votes_active.values())
        dominance = best_w / total if total else 0
        return best_uid, votes_active, dominance, "active"

    if votes_historic:
        best_uid, best_w = max(votes_historic.items(), key=lambda x: (x[1], -x[0]))
        return best_uid, votes_historic, 1.0, "historic"

    return None, {}, 0.0, None


def _has_real_activity(uid, events):
    for ev in events or []:
        if ev.get("author_uid") != uid:
            continue
        mt = ev.get("message_type") or ""
        kind = ev.get("kind") or ""
        if mt in ("email", "comment") or kind in ("activity", "activity_done"):
            return True
    return False


def _commercial_with_activity(); (events, commercials_active):
    counts = defaultdict(int)
    for ev in events or []:
        uid = ev.get("author_uid")
        if uid in commercials_active:
            mt = ev.get("message_type") or ""
            kind = ev.get("kind") or ""
            if mt in ("email", "comment") or kind in ("activity", "activity_done"):
                counts[uid] += 1
    if not counts:
        return None, 0
    best = max(counts.items(), key=lambda x: (x[1], -x[0]))
    return best[0], best[1]
