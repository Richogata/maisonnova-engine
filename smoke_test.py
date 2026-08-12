# -*- coding: utf-8 -*-
"""Smoke test MaisonNova Engine v1 — teste le moteur sans navigateur.
Simule le module streamlit pour importer app.py, vérifie :
  - le boot complet du script (routing prospect inclus, aucune exception)
  - slugify, extraction par règles, scoring (>= seuil attendu)
  - l'écriture du lead CSV et la notification (alerts.log)
"""
import sys
import types
import os
import traceback

# repart d'un état propre (fichiers générés par les runs précédents)
for _f in ("leads.csv", "alerts.log", "sheets_config.json"):
    if os.path.exists(_f):
        os.remove(_f)

# ── Stub streamlit ─────────────────────────────────────────────────────────────
stub = types.ModuleType("streamlit")


class _SS(dict):
    def __getattr__(self, k):
        return self.get(k, None)

    def __setattr__(self, k, v):
        self[k] = v


class _Ctx:
    def __init__(self, *a, **k):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def __getattr__(self, name):
        return lambda *a, **k: None


def _noop(*a, **k):
    return None


def _ctx(*a, **k):
    return _Ctx()


def _query_params():
    # route vers l'interface prospect avec l'agence de démo (test du boot prospect)
    return {"agency": "maisonnova-lyon"}


def _mod_getattr(name):
    """Repli générique : tout widget st.* non listé devient un no-op."""
    return lambda *a, **k: None

stub.__getattr__ = _mod_getattr

for _n in ("set_page_config", "markdown", "text_input", "button", "error", "warning",
           "info", "success", "tabs", "selectbox", "slider", "form_submit_button",
           "text_area", "divider", "dataframe", "download_button", "metric",
           "link_button", "code", "write", "rerun", "stop", "spinner", "container",
           "chat_input", "chat_message", "toast", "radio"):
    setattr(stub, _n, _noop)
stub.chat_message = _ctx
stub.form = _ctx
stub.columns = lambda *a, **k: tuple(_Ctx() for _ in range(a[0] if a and isinstance(a[0], int) else 2))
stub.tabs = lambda *a, **k: [_Ctx() for _ in range(len(a[0]) if a else 4)]
stub.selectbox = lambda label, options, *a, **k: (options[0] if isinstance(options, list) and options else None)
stub.session_state = _SS()
stub.query_params = types.SimpleNamespace(get=lambda k, d=None: d if k not in _query_params() else _query_params()[k])
stub.set_page_config = _noop
sys.modules["streamlit"] = stub

import app  # noqa: E402  (importe et EXÉCUTE le script complet : boot testé)

print("✅ 1. Boot complet du script (routing prospect) : AUCUNE exception")

# ── 2. slugify ─────────────────────────────────────────────────────────────────
assert app.slugify("MaisonNova Lyon") == "maisonnova-lyon"
got = app.slugify("Agence L'Immobilière!")
assert got == "agence-l-immobiliere", got
print("✅ 2. slugify OK")

# ── 3. Extraction par règles + scoring (parcours prospect complet) ─────────────
convo = [
    {"role": "user", "content": "Je m'appelle Jean Dupont"},
    {"role": "user", "content": "une maison individuelle"},
    {"role": "user", "content": "400 000 euros"},
    {"role": "user", "content": "Lyon"},
    {"role": "user", "content": "un prêt pré-accordé"},
    {"role": "user", "content": "dès que possible"},
]
prof = app.extract_profile_rules(convo, "Lyon")
print("   profil extrait :", prof)
assert prof["name"] == "Jean Dupont", prof
assert prof["project_type"] == "maison", prof
assert prof["budget"] == "400-600k", prof
assert prof["city"] == "Lyon", prof
assert prof["financing"] == "preapproved", prof
assert prof["timeline"] == "<6", prof

score, parts = app.score_profile(prof, "Lyon")
print("   score :", score, "| détail :", parts)
assert score == 20 + 22 + 15 + 25 + 15, score  # maison20 + 400k22 + Lyon15 + pré-accordé25 + <6mois15
assert score >= 90
print("✅ 3. Extraction + scoring OK (score attendu = 97/100)")

# ── 4. Lead non qualifié (seuil non atteint) ───────────────────────────────────
prof_weak = {"name": "Marie", "project_type": None, "budget": "<150k",
             "city": "Bordeaux", "financing": "none", "timeline": "flexible"}
score_weak, _ = app.score_profile(prof_weak, "Lyon")
assert score_weak < 70
print(f"✅ 4. Profil faible scoré {score_weak}/100 → NON qualifié (OK)")

# ── 5. Sauvegarde CSV + notification ───────────────────────────────────────────
agency = {"name": "MaisonNova Lyon", "threshold": 70, "email": "test@maisonnova.fr"}
app.save_lead(agency, "maisonnova-lyon", prof, score, True, "Résumé de test", "smoke-1")
app.notify_agency(agency, "Jean Dupont", score, True)

with open("leads.csv", encoding="utf-8-sig") as f:
    rows = list(__import__("csv").DictReader(f))
assert len(rows) == 1, rows
assert rows[0]["score"] == "97"
assert rows[0]["qualified"] == "oui"
assert rows[0]["name"] == "Jean Dupont"

with open("alerts.log", encoding="utf-8") as f:
    log = f.read()
assert "Jean Dupont" in log and "97" in log
print("✅ 5. Lead CSV + alerte email simulée OK")

# ── 6. Boot de l'interface ADMIN (routing sans ?agency=) ───────────────────────
import importlib
stub.query_params = types.SimpleNamespace(get=lambda k, d=None: d)
importlib.reload(app)
print("✅ 6. Boot de l'interface ADMIN : AUCUNE exception")

# ── 7. Google Sheets : chemins d'erreur sans crash ─────────────────────────────
ok, msg = app.test_sheets_connection()
assert ok is False and "incomplète" in msg, msg
app.sheets_save_config({"service_account": "not-json{{{]", "spreadsheet": "abc"})
ok, msg = app.test_sheets_connection(service="not-json", sheet_ref="abc")
assert ok is False and "Connexion impossible" in msg, msg
os.remove("sheets_config.json")
print("✅ 7. Google Sheets : connexion/tests gérés sans crash (pas de clé fournie)")

print("\n🎉 TOUS LES TESTS PASSENT (moteur + boot admin + Google Sheets)")
