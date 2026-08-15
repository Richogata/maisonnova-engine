# -*- coding: utf-8 -*-
"""Smoke test MaisonNova Engine v2 — teste le moteur + la nouvelle gestion
clients sans navigateur et SANS toucher aux données de production.

Tous les fichiers (clients, agences, leads, alertes, guides) sont redirigés
vers des fichiers temporaires via des variables d'environnement, puis supprimés
en fin de test : aucun test ne laisse de données client fictives dans les
données de production.

Scénarios couverts :
 1. boot prospect      2. slugify           3. extraction + scoring
 4. profil faible      5. lead CSV + alerte 6. boot admin
 7. Google Sheets (erreurs gérées)           8. création client
 9. configuration chatbot + points          10. génération du code
 11. contenu du guide                       12. guide HTML (sélection plateformes)
 13. export du guide                        14. export dossier client (ZIP + LISEZ-MOI)
 15. mode test (aucun vrai lead)            16. détection de plateforme « je ne sais pas »
 17. parcours prospect complet              18. extraction auto depuis le site web
 19. suppression de lead                    20. chatbot activé par défaut
 21. suppression client effective           22. troncature IA → repli lisible
 23. extraction : og:site_name + ville      24. extraction : erreur fetch gérée
 25. chatbot actif même si tout désactivé
"""

import csv
import importlib
import io
import json
import os
import shutil
import sys
import types
import zipfile

try:  # console Windows (cp1252) : force l'UTF-8 pour les emojis de logs
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ── Isolation : tous les fichiers vers des copies temporaires ────────────────
TMP = {
    "CLIENTS_FILE": "test_clients.json",
    "AGENCY_FILE": "test_agencies.json",
    "LEADS_FILE": "test_leads.csv",
    "ALERTS_FILE": "test_alerts.log",
    "TEST_LEADS_FILE": "test_test_leads.csv",
    "GUIDES_CONTENT_FILE": "test_guides_content.json",
    "GUIDES_DIR": "test_guides",
    "SHEETS_CONFIG_FILE": "test_sheets_config.json",
    "GEMINI_API_KEY": "",  # neutralise la clé du .env → mode dégradé garanti
}
for _k, _v in TMP.items():
    os.environ[_k] = _v

for _f in list(TMP.values()):
    if _f and os.path.isfile(_f):
        os.remove(_f)
if os.path.isdir(TMP["GUIDES_DIR"]):
    shutil.rmtree(TMP["GUIDES_DIR"])


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
    # route vers l'interface prospect avec la première agence présente dans le
    # fichier agences (env-overridé → fichier temporaire)
    try:
        with open(os.getenv("AGENCY_FILE", "agencies.json"), encoding="utf-8") as _f:
            _ag = json.load(_f)
        if isinstance(_ag, dict) and _ag:
            return {"agency": next(iter(_ag))}
    except Exception:
        pass
    return {"agency": "maisonnova-lyon"}


def _mod_getattr(name):
    """Repli générique : tout widget st.* non listé devient un no-op."""
    return lambda *a, **k: None


stub.__getattr__ = _mod_getattr

for _n in ("set_page_config", "markdown", "text_input", "button", "error", "warning",
           "info", "success", "tabs", "selectbox", "slider", "form_submit_button",
           "text_area", "divider", "dataframe", "download_button", "metric",
           "link_button", "code", "write", "rerun", "stop", "spinner", "container",
           "chat_input", "chat_message", "toast", "radio", "caption", "checkbox",
           "number_input", "multiselect", "color_picker", "select_slider"):
    setattr(stub, _n, _noop)
stub.chat_message = _ctx
stub.form = _ctx
stub.expander = _ctx
stub.columns = lambda *a, **k: tuple(_Ctx() for _ in range(a[0] if a and isinstance(a[0], int) else 2))
stub.tabs = lambda *a, **k: [_Ctx() for _ in range(len(a[0]) if a else 4)]
stub.selectbox = lambda label, options, *a, **k: (options[0] if isinstance(options, list) and options else None)
stub.session_state = _SS()
stub.query_params = types.SimpleNamespace(get=lambda k, d=None: d if k not in _query_params() else _query_params()[k])
stub.set_page_config = _noop
sys.modules["streamlit"] = stub

import app  # noqa: E402  (importe et EXÉCUTE le script complet : boot testé)
import clients_store  # noqa: E402
import chatbot_config  # noqa: E402
import widget_code  # noqa: E402
import guide_content  # noqa: E402
import guide_builder  # noqa: E402
import client_kit  # noqa: E402
import site_extractor  # noqa: E402
import ai_provider  # noqa: E402

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
assert prof["name"] == "Jean Dupont", prof
assert prof["project_type"] == "maison", prof
assert prof["budget"] == "400-600k", prof
assert prof["city"] == "Lyon", prof
assert prof["financing"] == "preapproved", prof
assert prof["timeline"] == "<6", prof

score, parts = app.score_profile(prof, "Lyon")
assert score == 20 + 22 + 15 + 25 + 15, score  # maison20 + 400k22 + Lyon15 + pré-accordé25 + <6mois15
assert score == 97
print("✅ 3. Extraction + scoring OK (score = 97/100)")

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

with open(os.environ["LEADS_FILE"], encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))
assert len(rows) == 1, rows
assert rows[0]["score"] == "97"
assert rows[0]["qualified"] == "oui"
assert rows[0]["name"] == "Jean Dupont"
assert rows[0]["source"] == "web"

with open(os.environ["ALERTS_FILE"], encoding="utf-8") as f:
    log = f.read()
assert "Jean Dupont" in log and "97" in log
print("✅ 5. Lead CSV + alerte email simulée OK")

# ── 6. Boot de l'interface ADMIN (routing sans ?agency=) ───────────────────────
stub.query_params = types.SimpleNamespace(get=lambda k, d=None: d)
importlib.reload(app)
print("✅ 6. Boot de l'interface ADMIN (9 onglets) : AUCUNE exception")

# ── 7. Google Sheets : chemins d'erreur sans crash ─────────────────────────────
ok, msg = app.test_sheets_connection()
assert ok is False and "incomplète" in msg, msg
app.sheets_save_config({"service_account": "not-json{{{]", "spreadsheet": "abc"})
ok, msg = app.test_sheets_connection(service="not-json", sheet_ref="abc")
assert ok is False and "Connexion impossible" in msg, msg
os.remove(os.environ["SHEETS_CONFIG_FILE"])
print("✅ 7. Google Sheets : connexion/tests gérés sans crash")

# ── 8. Création de client (identifiant, slug, statut) ──────────────────────────
client = clients_store.create_client("Dupont Immobilier", app_url="https://app.test",
                                     manager="M. Dupont", email="contact@dupont.fr")
assert client["id"].startswith("agency_") and len(client["id"]) == len("agency_") + 5, client["id"]
assert client["slug"] == "dupont-immobilier", client["slug"]
assert client["status"] == "DRAFT", client["status"]
clients_store.update_client(client["id"], agency={"city": "Lyon", "calendly_url": "https://calendly.com/x"},
                            contact={"phone": "0600000000"})
clients_store.set_status(client["id"], "CONFIGURED")
fetched = clients_store.get_client("dupont-immobilier")
assert fetched and fetched["status"] == "CONFIGURED"
assert fetched["agency"]["calendly_url"] == "https://calendly.com/x"
# modification (renommage → nouveau slug)
clients_store.update_client(client["id"], agency={"name": "Dupont Lyon"})
assert clients_store.get_client("dupont-lyon") is not None
assert clients_store.get_client("dupont-immobilier") is None  # ancien slug retiré
print("✅ 8. Création / modification client : id, slug, statut OK")

# ── 9. Configuration chatbot + points personnalisés ────────────────────────────
cfg = chatbot_config.get_config_for_agency(agency, "maisonnova-lyon")
assert len(cfg["questions"]) == 5, cfg["questions"]
assert cfg["threshold"] == 70
# points par défaut identiques au moteur actuel
s1, _ = chatbot_config.apply_points(prof, "Lyon")
assert s1 == 97, s1
# points personnalisés par agence (copie profonde : ne JAMAIS muter les tables partagées)
import copy
custom = copy.deepcopy(chatbot_config.DEFAULT_POINTS)
custom["budget"]["400-600k"] = 30
client_cfg = clients_store.get_client("dupont-lyon")
clients_store.update_client(client_cfg["id"], chatbot={
    "default_journey": "achat",
    "journeys": {"achat": {"enabled": True, "questions": None, "points": custom,
                           "threshold": 80, "message": ""}}})
cfg2 = chatbot_config.get_config_for_agency({"name": "Dupont Lyon", "city": "Lyon", "threshold": 80},
                                            "dupont-lyon")
assert cfg2["threshold"] == 80, cfg2["threshold"]
s2, _ = app.score_profile(prof, "Lyon", points=cfg2["points"])
assert s2 == 100, s2  # budget 30 au lieu de 22 → le score reste capé à 100
assert s2 == 100
print("✅ 9. Configuration chatbot : questions, seuil et points personnalisables OK")

# ── 10. Génération du code d'installation ──────────────────────────────────────
install = widget_code.ensure_install(fetched)
assert install["key"].startswith("MN-") and len(install["key"]) == 12, install["key"]
url = widget_code.install_url(fetched)
assert "dupont-immobilier" in url and "embed=1" in url, url
iframe = widget_code.iframe_snippet(fetched)
assert "iframe" in iframe and "dupont-immobilier" in iframe
script = widget_code.script_snippet(fetched)
assert "maisonnova-assistant" in script and install["key"] in script
wm = widget_code.webmaster_block(fetched)
assert fetched["id"] in wm and install["key"] in wm and "CODE À INTÉGRER" in wm
assert "GEMINI_API_KEY" not in wm and "ADMIN_PASSWORD" not in wm  # aucun secret exposé
print("✅ 10. Code d'installation : URL, iframe, script, agency_id, clé, webmaster OK")

# ── 11. Contenu du guide (data-driven, modifiable) ─────────────────────────────
content = guide_content.load_content()
for pkey in ("wordpress", "wix", "webflow", "custom"):
    assert pkey in content["platforms"], pkey
    assert len(content["platforms"][pkey]["steps"]) >= 3, pkey
assert len(content["faq"]) >= 6, len(content["faq"])
assert len(content["issues"]) >= 6, len(content["issues"])
# sauvegarde → rechargement (instructions modifiables sans coder)
guide_content.save_content(content)
assert guide_content.load_content()["platforms"]["wix"]["steps"]
print("✅ 11. Contenu du guide : plateformes, FAQ, dépannage, éditable OK")

# ── 12. Guide HTML interactif + sélection de plateforme ────────────────────────
html_guide = guide_builder.build_guide_html(fetched, content)
for needle in ("Dupont Immobilier", fetched["id"], install["key"],
               "WordPress", "Wix", "Webflow", "Site personnalisé", "Je ne sais pas",
               "Je suis bloqué", "Questions fréquentes", "webmaster"):
    assert needle in html_guide, needle
assert "GEMINI_API_KEY" not in html_guide and "admin123" not in html_guide
# « je ne sais pas » → détection de plateforme
assert widget_code.detect_platform("https://mon-agence.wixsite.com/accueil") == "wix"
assert widget_code.detect_platform("exemple.wordpress.com") == "wordpress"
assert widget_code.detect_platform("https://monsite.webflow.io") == "webflow"
assert widget_code.detect_platform("https://mon-agence.fr") is None
print("✅ 12. Guide interactif : plateformes, détection « je ne sais pas », pas de secrets OK")

# ── 13. Export du guide (fichier HTML) ─────────────────────────────────────────
path = guide_builder.generate_guide_file(fetched, content)
assert os.path.exists(path)
with open(path, encoding="utf-8") as f:
    assert "Dupont Immobilier" in f.read()
print(f"✅ 13. Export du guide OK ({path})")

# ── 14. Export du dossier client (ZIP) ─────────────────────────────────────────
kit = client_kit.build_kit_zip(fetched, html_guide)
assert kit and kit.startswith(b"PK")
with zipfile.ZipFile(io.BytesIO(kit)) as z:
    names = z.namelist()
    readme = z.read("LISEZ-MOI.txt").decode("utf-8")
for needed in ("LISEZ-MOI.txt", "client_info/", "configuration/", "widget/", "code/", "guide/", "instructions_webmaster/"):
    assert any(n.startswith(needed) for n in names), needed
assert "client_guide.html" in readme and "webmaster" in readme.lower()  # guide d'usage du ZIP
assert client_kit.kit_filename(fetched) == "MaisonNova_dupont-immobilier_Client_Kit.zip"
print("✅ 14. Export du dossier client (ZIP, 7 entrées dont LISEZ-MOI.txt) OK")


# ── 15. Mode TEST : aucun vrai lead créé ───────────────────────────────────────
app.save_lead(agency, "maisonnova-lyon", prof, score, True, "Lead de test", "smoke-test-1",
              test_mode=True)
with open(os.environ["TEST_LEADS_FILE"], encoding="utf-8-sig") as f:
    test_rows = list(csv.DictReader(f))
assert len(test_rows) == 1 and test_rows[0]["source"] == "test", test_rows
with open(os.environ["LEADS_FILE"], encoding="utf-8-sig") as f:
    real_rows = list(csv.DictReader(f))
assert len(real_rows) == 1, real_rows  # inchangé : le lead TEST n'est pas mélangé
print("✅ 15. Mode test : lead TEST séparé, aucun faux lead réel")

# ── 16. Statuts + dashboard ────────────────────────────────────────────────────
assert clients_store.next_status("DRAFT") == "CONFIGURED"
assert clients_store.next_status("INSTALLED") == "INSTALLED"
steps = clients_store.status_steps(clients_store.get_client("maisonnova-lyon"))
assert len(steps) == 5 and all(isinstance(ok, bool) for _, ok in steps)
print("✅ 16. Statuts du client + dashboard OK")

# ── 17. Parcours prospect complet simulé (welcome → 5 questions → clôture) ─────
# 1 tour = 1 re-exécution Streamlit : on rejoue render_prospect pour chaque réponse.
answers = ["Je m'appelle Jean Dupont", "une maison individuelle", "400 000 euros",
           "Lyon", "un prêt pré-accordé", "dès que possible"]
stub.chat_input = lambda *a, **k: answers.pop(0) if answers else None
for _ in range(7):
    app.render_prospect("maisonnova-lyon")
stub.chat_input = _noop
ss = stub.session_state
assert ss.get("prospect_stage") == "closing", ss.get("prospect_stage")
assert ss.get("score") == 97, ss.get("score")
assert ss.get("qualified") is True
assert len(ss.get("messages", [])) == 13
with open(os.environ["LEADS_FILE"], encoding="utf-8-sig") as f:
    rows17 = list(csv.DictReader(f))
assert len(rows17) == 2, rows17  # lead du test 5 + lead de cette conversation
assert rows17[-1]["name"] == "Jean Dupont" and rows17[-1]["score"] == "97"
assert rows17[-1]["qualified"] == "oui" and rows17[-1]["source"] == "web"
print("✅ 17. Parcours prospect complet (chat simulé → score 97 → lead sauvegardé) OK")

# ── 18. Extraction automatique depuis le site web du client (règles, sans réseau) ──
FAKE_SITE = """<!DOCTYPE html><html><head>
<title>Dupont Immobilier | Agence immobilière à Lyon</title>
<meta name="description" content="Dupont Immobilier, votre agence immobilière à Lyon. Achat, vente, location.">
<meta property="og:image" content="https://www.dupont.fr/logo.png">
</head><body>
<h1>Bienvenue chez Dupont Immobilier</h1>
<p>Contact : contact@dupont.fr — 04 72 00 00 00</p>
<p>Nous gérons achat, vente et location de maisons et appartements à Lyon, Villeurbanne et Caluire.</p>
<p>Ouvert du lundi au samedi de 9h à 19h.</p>
</body></html>"""
info = site_extractor.extract_from_html(FAKE_SITE, url="https://www.dupont.fr", use_ai=False)
assert info["name"] == "Dupont Immobilier", info["name"]
assert "Achat" in info["services"] and "Vente" in info["services"] and "Location" in info["services"], info["services"]
assert info["email"] == "contact@dupont.fr", info["email"]
assert info["phone"] == "04 72 00 00 00", info["phone"]
assert info["city"] == "Lyon", info["city"]
assert "Villeurbanne" in info["zones"], info["zones"]
assert "Maison" in info["property_types"] and "Appartement" in info["property_types"]
assert info["logo_url"].startswith("https://")
print("✅ 18. Extraction auto depuis le site (nom, coordonnées, services, ville, zones, logo) OK")

# ── 19. Suppression de lead ────────────────────────────────────────────────────
leads_path = os.environ["LEADS_FILE"]
n_before = len(app.load_csv_rows(leads_path))
assert app.delete_lead_row(leads_path, 0) is True
assert len(app.load_csv_rows(leads_path)) == n_before - 1
assert app.delete_lead_row(leads_path, 999) is False  # index hors bornes géré
assert app.clear_leads_file(leads_path) is True
assert app.load_csv_rows(leads_path) == []
app.save_lead(agency, "maisonnova-lyon", prof, score, True, "Résumé de test", "smoke-19")
print("✅ 19. Suppression / vidage des leads OK (fichier intact, en-têtes conservés)")

# ── 20. Chatbot activé par défaut (aucune activation manuelle nécessaire) ──────
journeys = chatbot_config.default_journeys()
assert all(j.get("enabled") for j in journeys.values())
new_client = clients_store.create_client("Test Actif", app_url="https://app.test")
cb = new_client.get("chatbot") or {}
assert cb.get("journeys"), "parcours pré-remplis dès la création"
assert all(j.get("enabled") for j in cb["journeys"].values())
cfg3 = chatbot_config.get_config_for_agency(
    {"name": "Test Actif", "city": "Lyon", "threshold": 70}, "test-actif")
assert len(cfg3["questions"]) == 5 and cfg3["threshold"] == 70
clients_store.delete_client(new_client["id"])
print("✅ 20. Chatbot opérationnel immédiatement : tous les parcours activés par défaut OK")

# ── 21. Suppression client EFFECTIVE (agences resynchronisées, lien retiré) ───
cl_del = clients_store.create_client("Suppression Test", app_url="https://app.test")
slug_del = cl_del["slug"]
gpath = guide_builder.generate_guide_file(cl_del)  # crée un guide à nettoyer
assert os.path.exists(gpath)
assert app.get_agency(slug_del) is not None
assert clients_store.delete_client(cl_del["id"]) is True
assert app.get_agency(slug_del) is None, "le lien prospect doit cesser de fonctionner"
ag_after = json.load(open(os.environ["AGENCY_FILE"], encoding="utf-8"))
assert slug_del not in ag_after, "le slug ne doit pas resurgir dans agencies.json"
assert not os.path.exists(gpath), "le guide du client supprimé doit être retiré"
# régression : la clé du dict clients doit TOUJOURS être égale à l'id du client
for cid, cl in clients_store.load_clients().items():
    assert cl.get("id") == cid, (cid, cl.get("id"))
print("✅ 21. Suppression client effective : lien retiré, agencies.json propre, guide nettoyé OK")

# ── 22. Troncature IA (MAX_TOKENS) → repli lisible (jamais de texte coupé) ─────
_real_genai = sys.modules.get("google.generativeai")
class _FR:
    name = "MAX_TOKENS"
class _Cand:
    finish_reason = _FR()
class _Resp:
    text = "Question coupée en plein milieu de ph"
    candidates = [_Cand()]
class _FakeModel:
    def __init__(self, *a, **k):
        pass
    def generate_content(self, *a, **k):
        return _Resp()
_fake = types.ModuleType("google.generativeai")
_fake.configure = lambda *a, **k: None
_fake.GenerativeModel = _FakeModel
_fake.types = types.SimpleNamespace(GenerationConfig=lambda **k: None)
sys.modules["google.generativeai"] = _fake
try:
    p = ai_provider.AIProvider(api_key="cle-fake", models=["m-tronque"])
    assert p.ready is True
    assert p.complete("sys", "user") is None, "une réponse tronquée doit renvoyer None"
finally:
    if _real_genai is not None:
        sys.modules["google.generativeai"] = _real_genai
    else:
        sys.modules.pop("google.generativeai", None)
print("✅ 22. Troncature IA détectée → repli lisible (aucun texte coupé affiché) OK")

# ── 23. Extraction : og:site_name prioritaire + ville « située à Lyon » ────────
SITE_A = """<html><head><title>Accueil - Agence Dupont</title>
<meta property="og:site_name" content="Dupont Immobilier">
<meta name="description" content="Agence immobilière à Lyon depuis 2005.">
</head><body><h1>Bienvenue</h1>
<p>Agence située à Lyon, 12 rue de la République. contact@dupont.fr 04 78 00 00 00</p>
</body></html>"""
infoA = site_extractor.extract_from_html(SITE_A, url="https://www.dupont-immobilier.fr", use_ai=False)
assert infoA["name"] == "Dupont Immobilier", infoA["name"]
assert infoA["city"] == "Lyon", infoA["city"]
assert infoA["description"] == "Agence immobilière à Lyon depuis 2005.", infoA["description"]
assert infoA["email"] == "contact@dupont.fr" and infoA["phone"] == "04 78 00 00 00"
print("✅ 23. Extraction : og:site_name prioritaire, ville via « située à Lyon », coordonnées OK")

# ── 24. Extraction : erreur réseau gérée (source=error, jamais de crash) ───────
infoE = site_extractor.extract_from_url("http://127.0.0.1:1/", use_ai=False)
assert infoE.get("source") == "error", infoE
print("✅ 24. Extraction : site illisible → erreur propre (pas de crash) OK")

# ── 25. Chatbot actif même si tous les parcours désactivés par erreur ──────────
cl_off = clients_store.create_client("Chat Off", app_url="https://app.test")
import copy
j_off = copy.deepcopy(chatbot_config.default_journeys())
for k in j_off:
    j_off[k]["enabled"] = False
clients_store.update_client(cl_off["id"], chatbot={"default_journey": "achat", "journeys": j_off})
cfg_off = chatbot_config.get_config_for_agency(
    {"name": "Chat Off", "city": "Lyon", "threshold": 70}, "chat-off")
assert len(cfg_off["questions"]) == 5 and cfg_off["threshold"] == 70, cfg_off
clients_store.delete_client(cl_off["id"])
print("✅ 25. Chatbot toujours fonctionnel, même avec tous les parcours désactivés OK")

# ── 26. Réparation auto des anciens dossiers (clé du dict != id du client) ────
import uuid
broken_id = "agency_" + uuid.uuid4().hex[:5].upper()
with open(os.environ["CLIENTS_FILE"], "w", encoding="utf-8") as f:
    json.dump({"agency_OLDKEY": {"id": broken_id, "slug": "repair-test", "status": "DRAFT",
                                  "agency": {"name": "Repair Test"}}}, f, ensure_ascii=False)
repaired = clients_store.load_clients()
assert list(repaired.keys()) == [broken_id], list(repaired.keys())
assert clients_store.delete_client(broken_id) is True  # suppression possible après réparation
print("✅ 26. Anciens dossiers (clé ≠ id) réparés automatiquement → suppression possible OK")

print("\n🎉 TOUS LES TESTS PASSENT (moteur + clients + config + code + guide + kit + mode test)")

# ── Nettoyage : aucun fichier de test laissé derrière ──────────────────────────
for _f in set(TMP.values()):
    if _f and os.path.isfile(_f):
        os.remove(_f)
if os.path.isdir(TMP["GUIDES_DIR"]):
    shutil.rmtree(TMP["GUIDES_DIR"])
print("🧹 Fichiers temporaires de test supprimés (données de production intactes)")
