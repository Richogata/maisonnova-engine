# ═══════════════════════════════════════════════════════════════════════════════
#   MAISONNOVA ENGINE v1  —  Moteur de qualification de leads immobilier
#   Stack : 100% Python · Streamlit · Google Gemini (google-generativeai)
#   Design : Premium, fond blanc, typographie Inter, glassmorphism "style Apple"
# ═══════════════════════════════════════════════════════════════════════════════
#   🏢 INTERFACE ADMIN      → page d'accueil (protégée par mot de passe)
#   💬 INTERFACE PROSPECT   →  /?agency=slug-de-l-agence
#
#   Lancement :  streamlit run app.py
#   Clé API    :  GEMINI_API_KEY (Google AI Studio) — sans clé, l'app fonctionne
#                 en mode "template" (démo dégradée, scoring par règles).
# ═══════════════════════════════════════════════════════════════════════════════

import os
import re
import csv
import json
import html
import uuid
import logging
import datetime

import streamlit as st

# Modules "nouvelle génération" (dossier clients, config chatbot, guide, kit…)
import clients_store
import chatbot_config
import ai_provider
import widget_code
import guide_content
import guide_builder
import client_kit
import admin_views

# ───────────────────────────────────────────────────────────────────────────────
# 1. ENVIRONNEMENT & CONFIGURATION
# ───────────────────────────────────────────────────────────────────────────────

try:  # support optionnel d'un fichier .env
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


def _cfg(name: str, default: str = "") -> str:
    """Valeur de configuration : secret Streamlit Cloud (st.secrets) > .env > défaut.
    Permet de déployer sur Streamlit Community Cloud sans fichier .env :
    les mêmes variables sont saisies dans Settings → Secrets du tableau de bord."""
    try:
        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        pass
    return os.getenv(name, default)


# --- Variables d'environnement (voir .env.example) -----------------------------
ADMIN_PASSWORD      = _cfg("ADMIN_PASSWORD", "admin123")              # ⚠️ à changer
GEMINI_API_KEY      = _cfg("GEMINI_API_KEY", "")
GEMINI_MODELS       = [m for m in _cfg("GEMINI_MODEL", "gemini-flash-latest").split(",") if m]
GEMINI_MODELS      += ["gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-flash-lite-latest"]  # replis auto

AGENCY_FILE         = _cfg("AGENCY_FILE", "agencies.json")
LEADS_FILE          = _cfg("LEADS_FILE", "leads.csv")
ALERTS_FILE         = _cfg("ALERTS_FILE", "alerts.log")

# Google Sheets (optionnel — si configuré, les leads sont AUSSI poussés dessus)
GDRIVE_JSON         = _cfg("GOOGLE_SHEETS_JSON", "")                   # chemin service-account.json
GDRIVE_KEY          = _cfg("GOOGLE_SHEETS_KEY", "")                    # ID du spreadsheet

# SMTP réel (optionnel — sinon l'alerte mail est simulée dans alerts.log)
SMTP_HOST           = _cfg("SMTP_HOST", "")
SMTP_PORT           = int(_cfg("SMTP_PORT", "587"))
SMTP_USER           = _cfg("SMTP_USER", "")
SMTP_PASSWORD       = _cfg("SMTP_PASSWORD", "")

# Nouveaux fichiers (dossiers clients, leads de test, guides)
CLIENTS_FILE        = _cfg("CLIENTS_FILE", "clients.json")
TEST_LEADS_FILE     = _cfg("TEST_LEADS_FILE", "test_leads.csv")
GUIDES_DIR          = _cfg("GUIDES_DIR", "guides")

APP_BASE_URL        = _cfg("APP_BASE_URL", "http://localhost:8501")

GOLD      = "#C9A227"
GOLD_DARK = "#9C7A14"
INK       = "#1C1C1E"
GRAY_BG   = "#F2F2F7"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ───────────────────────────────────────────────────────────────────────────────
# 2. OUTILS — MODÈLES & GEMINI
# ───────────────────────────────────────────────────────────────────────────────

# Couche d'abstraction IA (Gemini existant + repli automatique + mode dégradé)
AI_PROVIDER = ai_provider.AIProvider(api_key=GEMINI_API_KEY, models=GEMINI_MODELS)
GEMINI_READY = AI_PROVIDER.ready


def ai_complete(system_prompt: str, user_text: str, temperature: float = 0.6,
                json_mode: bool = False, max_tokens: int = 700) -> str | None:
    """Appelle l'IA via AIProvider (Gemini + repli de modèle). None si indisponible."""
    return AI_PROVIDER.complete(system_prompt, user_text, temperature=temperature,
                                json_mode=json_mode, max_tokens=max_tokens)


def ai_json(system_prompt: str, user_text: str, max_tokens: int = 800) -> dict | None:
    """Version 'mode JSON' avec nettoyage robuste des réponses (déléguée à AIProvider)."""
    return AI_PROVIDER.json(system_prompt, user_text, max_tokens=max_tokens)

# ───────────────────────────────────────────────────────────────────────────────
# 3. AGENCES — CONFIGURATION LOCALE (agencies.json)
# ───────────────────────────────────────────────────────────────────────────────

ACCENTS = {"à": "a", "â": "a", "ä": "a", "á": "a", "ã": "a",
           "é": "e", "è": "e", "ê": "e", "ë": "e",
           "î": "i", "ï": "i", "í": "i", "ì": "i",
           "ô": "o", "ö": "o", "ó": "o", "ò": "o",
           "ù": "u", "û": "u", "ü": "u", "ú": "u",
           "ç": "c", "ñ": "n", "ÿ": "y", "œ": "oe",
           "'": "-", "’": "-", "`": "", ".": ""}


def slugify(text: str) -> str:
    """Slug URL simple, accents français gérés : 'Agence L'Immobilière' -> 'agence-immobiliere'."""
    text = text.lower().strip()
    for k, v in ACCENTS.items():
        text = text.replace(k, v)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "agence"


def load_agencies() -> dict:
    """Fiches agences = clients (source maître, clients.json) + fichier legacy
    agencies.json (jamais cassé : les clients sont resynchronisés dessus)."""
    agencies = {}
    try:
        agencies.update(clients_store.all_agencies())
    except Exception:
        pass
    try:
        with open(AGENCY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                for k, v in data.items():
                    agencies.setdefault(k, v)
    except Exception:
        pass
    return agencies


def save_agencies(data: dict):
    with open(AGENCY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def ensure_default_agencies():
    """Crée un client de démonstration au premier lancement (délégué au dossier
    clients, qui resynchronise agencies.json — le moteur existant n'est pas touché)."""
    clients_store.ensure_default_client(APP_BASE_URL)


def get_agency(slug: str) -> dict | None:
    agencies = load_agencies()
    # tolérance : accepte aussi le nom exact de l'agence
    if slug in agencies:
        return agencies[slug]
    for key, val in agencies.items():
        if val.get("name", "").strip().lower() == slug.strip().lower():
            return val
    return None

# ───────────────────────────────────────────────────────────────────────────────
# 4. STOCKAGE DES LEADS — CSV (local) + GOOGLE SHEETS (optionnel via gspread)
# ───────────────────────────────────────────────────────────────────────────────

LEAD_COLUMNS = [
    "timestamp", "agency_slug", "agency_name", "session_id", "name",
    "project_type", "budget", "city", "financing", "timeline",
    "score", "threshold", "qualified", "summary", "source",
]

def _csv_path_exists():
    return os.path.exists(LEADS_FILE)


def init_leads_csv():
    if not _csv_path_exists():
        try:
            with open(LEADS_FILE, "w", encoding="utf-8-sig", newline="") as f:
                csv.DictWriter(f, fieldnames=LEAD_COLUMNS).writeheader()
        except Exception as exc:
            logging.error("Création du CSV impossible : %s", exc)


def load_leads() -> list[dict]:
    if not _csv_path_exists():
        return []
    try:
        with open(LEADS_FILE, "r", encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))
    except Exception as exc:
        logging.error("Lecture CSV impossible : %s", exc)
        return []


def load_csv_rows(path: str) -> list[dict]:
    """Lit n'importe quel CSV de leads (réels ou de test)."""
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))
    except Exception as exc:
        logging.error("Lecture CSV impossible (%s) : %s", path, exc)
        return []


def delete_lead_row(path: str, index: int) -> bool:
    """Supprime la ligne `index` d'un CSV de leads et réécrit le fichier.
    (N'affecte pas Google Sheets — la copie Sheets reste intacte.)"""
    rows = load_csv_rows(path)
    if not 0 <= index < len(rows):
        return False
    del rows[index]
    try:
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=LEAD_COLUMNS)
            w.writeheader()
            w.writerows(rows)
        return True
    except Exception as exc:
        logging.error("Suppression du lead impossible : %s", exc)
        return False


def clear_leads_file(path: str) -> bool:
    """Vide entièrement un CSV de leads (garde les en-têtes)."""
    try:
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            csv.DictWriter(f, fieldnames=LEAD_COLUMNS).writeheader()
        return True
    except Exception as exc:
        logging.error("Vidage du CSV impossible : %s", exc)
        return False


SHEETS_SCOPE = ["https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"]
SHEETS_CONFIG_FILE = _cfg("SHEETS_CONFIG_FILE", "sheets_config.json")


def sheets_load_config() -> dict:
    """Charge la configuration Google Sheets (écrite depuis l'admin ou via .env)."""
    try:
        with open(SHEETS_CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            return cfg if isinstance(cfg, dict) else {}
    except Exception:
        return {}


def sheets_save_config(cfg: dict):
    with open(SHEETS_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def _sheets_params() -> tuple[str | None, str | None]:
    """Retourne (service_account_json_ou_chemin, spreadsheet_id_ou_url)."""
    cfg = sheets_load_config()
    service = cfg.get("service_account") or GDRIVE_JSON or None
    sheet_ref = cfg.get("spreadsheet") or GDRIVE_KEY or None
    return service, sheet_ref


def _sheets_spreadsheet_id(ref: str) -> str:
    """Extrait l'ID depuis une URL Google Sheets (sinon renvoie l'ID tel quel)."""
    if ref.startswith("http"):
        m = re.search(r"/d/([a-zA-Z0-9-_]+)", ref)
        if m:
            return m.group(1)
    return ref


def _sheets_open(service: str | None = None, sheet_ref: str | None = None):
    """Ouvre le spreadsheet via gspread. Retourne (client, worksheet 'Leads' | None).
    La feuille 'Leads' est créée automatiquement avec les en-têtes si absente.
    Peut recevoir service/sheet_ref en paramètres (formulaire admin) sinon config sauvegardée."""
    if service is None or sheet_ref is None:
        service, sheet_ref = _sheets_params()
    if not (service and sheet_ref):
        return None, None
    import gspread
    from google.oauth2.service_account import Credentials
    if os.path.exists(service):
        creds = Credentials.from_service_account_file(service, scopes=SHEETS_SCOPE)
    else:
        payload = service.strip()
        payload = re.sub(r"^```(?:json)?\s*", "", payload)   # tolère les fences markdown
        payload = re.sub(r"\s*```$", "", payload)
        creds = Credentials.from_service_account_info(json.loads(payload), scopes=SHEETS_SCOPE)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(_sheets_spreadsheet_id(sheet_ref))
    try:
        ws = sheet.worksheet("Leads")
    except Exception:
        ws = sheet.add_worksheet(title="Leads", rows="100", cols=str(len(LEAD_COLUMNS)))
        ws.append_row(LEAD_COLUMNS)
    return client, ws


def test_sheets_connection(service: str | None = None, sheet_ref: str | None = None) -> tuple[bool, str]:
    """Test de connexion Google Sheets, utilisé par l'admin (bouton « Tester »)."""
    try:
        client, ws = _sheets_open(service=service, sheet_ref=sheet_ref)
        if ws is None:
            return False, "Configuration incomplète : service account ou spreadsheet manquant."
        email = getattr(getattr(client, "auth", None), "service_account_email", None) or "inconnu"
        n_rows = len(ws.get_all_values())
        return True, (f"✅ Connecté en tant que {email} — feuille « {ws.title} » prête "
                      f"({n_rows} ligne(s)). Les nouveaux leads y seront ajoutés en temps réel.")
    except Exception as exc:
        return False, f"❌ Connexion impossible : {exc}"


def _push_to_sheets(row: dict) -> bool:
    """Pousse le lead vers Google Sheets (optionnel — silencieux si non configuré)."""
    try:
        _, ws = _sheets_open()
        if ws is None:
            return False
        ws.append_row([row.get(c, "") for c in LEAD_COLUMNS])
        logging.info("Lead poussé vers Google Sheets (%s lignes)", len(ws.get_all_values()))
        return True
    except Exception as exc:
        logging.warning("Push Google Sheets impossible : %s", exc)
        return False


def _init_csv(path: str):
    if not os.path.exists(path):
        try:
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                csv.DictWriter(f, fieldnames=LEAD_COLUMNS).writeheader()
        except Exception as exc:
            logging.error("Création du CSV impossible : %s", exc)


def save_lead(agency: dict, slug: str, profile: dict, score: int, qualified: bool,
              summary: str, session_id: str, test_mode: bool = False) -> None:
    row = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "agency_slug": slug,
        "agency_name": agency.get("name", slug),
        "session_id": session_id,
        "name": profile.get("name", ""),
        "project_type": profile.get("project_type", ""),
        "budget": profile.get("budget", ""),
        "city": profile.get("city", ""),
        "financing": profile.get("financing", ""),
        "timeline": profile.get("timeline", ""),
        "score": score,
        "threshold": agency.get("threshold", 70),
        "qualified": "oui" if qualified else "non",
        "summary": summary,
        "source": "test" if test_mode else "web",
    }
    if test_mode:
        # Prévisualisation : fichier dédié TEST — jamais mélangé aux leads réels,
        # jamais poussé vers Google Sheets, jamais d'alerte.
        _init_csv(TEST_LEADS_FILE)
        try:
            with open(TEST_LEADS_FILE, "a", encoding="utf-8", newline="") as f:
                csv.DictWriter(f, fieldnames=LEAD_COLUMNS).writerow(row)
        except Exception as exc:
            logging.error("Écriture du lead TEST impossible : %s", exc)
        return
    init_leads_csv()
    try:
        with open(LEADS_FILE, "a", encoding="utf-8", newline="") as f:
            csv.DictWriter(f, fieldnames=LEAD_COLUMNS).writerow(row)
    except Exception as exc:
        logging.error("Écriture du lead CSV impossible : %s", exc)
    _push_to_sheets(row)


# ───────────────────────────────────────────────────────────────────────────────
# 5. NOTIFICATIONS — Alerte mail (simulée par défaut, SMTP réel optionnel)
# ───────────────────────────────────────────────────────────────────────────────

def notify_agency(agency: dict, lead_name: str, score: int, qualified: bool):
    """Simule l'envoi d'un e-mail d'alerte à l'agence sur un nouveau lead qualifié.
    Écrit dans alerts.log ; envoie un vrai e-mail si SMTP_* est configuré."""
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    subject = f"🏆 Nouveau lead qualifié — {agency.get('name','')} ({score}/100)"
    body = (f"Bonjour,\n\nUn nouveau prospect qualifié vient d'être capturé :\n\n"
            f"  • Nom       : {lead_name or 'Non renseigné'}\n"
            f"  • Score     : {score}/100 (seuil {agency.get('threshold',70)})\n"
            f"  • Qualifié  : {'OUI ✅' if qualified else 'NON'}\n"
            f"  • Horodatage: {ts}\n\nCordialement,\nMaisonNova Engine v1")

    try:
        with open(ALERTS_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {subject}\n  {body.replace(chr(10), '  ' + chr(10))}\n{'-'*72}\n")
    except Exception as exc:
        logging.warning("Écriture alerts.log impossible : %s", exc)

    if qualified and SMTP_HOST and SMTP_USER and SMTP_PASSWORD:
        try:
            import smtplib
            from email.mime.text import MIMEText
            msg = MIMEText(body, "plain", "utf-8")
            msg["Subject"] = subject
            msg["From"] = SMTP_USER
            msg["To"] = agency.get("email", SMTP_USER)
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as srv:
                srv.starttls()
                srv.login(SMTP_USER, SMTP_PASSWORD)
                srv.send_message(msg)
            logging.info("E-mail réel envoyé à %s", agency.get("email"))
        except Exception as exc:
            logging.warning("Envoi SMTP impossible : %s", exc)

# ───────────────────────────────────────────────────────────────────────────────
# 6. MOTEUR DE QUALIFICATION — Questionnaire, scoring & extraction
# ───────────────────────────────────────────────────────────────────────────────

# Les 5 questions posées par l'IA (ordre du brief). Le wording est généré par
# Gemini ; ces textes servent de repli si l'API est indisponible.
QUESTIONS = [
    ("project_type", "Quel type de projet envisagez-vous ? (maison individuelle, appartement, terrain, investissement locatif…)"),
    ("budget",       "Quel budget envisagez-vous pour ce projet ?"),
    ("city",         "Dans quelle ville ou quel secteur recherchez-vous ?"),
    ("financing",    "Comment comptez-vous financer ce projet ? (prêt pré-accordé, apport, financement à prévoir…)"),
    ("timeline",     "Quel est votre délai idéal pour concrétiser ce projet ?"),
]

PROJECT_POINTS  = {"maison": 20, "appartement": 18, "investissement": 16, "terrain": 12, "autre": 10}
BUDGET_POINTS   = {"600k+": 25, "400-600k": 22, "250-400k": 16, "150-250k": 10, "<150k": 5}
FINANCE_POINTS  = {"preapproved": 25, "cash": 20, "pending": 12, "none": 5}
TIMELINE_POINTS = {"<6": 15, "6-12": 12, "12-24": 8, "flexible": 5}

MAX_SCORE = 100

SYSTEM_EXTRACT = """Tu es un assistant d'extraction de données pour une agence immobilière.
À partir de la conversation (prospect + assistant), extrais le profil du prospect.
Réponds UNIQUEMENT en JSON valide avec ces clés exactes :
{
  "name": string|null,           // prénom et/ou nom du prospect
  "project_type": "maison"|"appartement"|"investissement"|"terrain"|"autre"|null,
  "budget": "600k+"|"400-600k"|"250-400k"|"150-250k"|"<150k"|null,
  "city": string|null,           // ville/secteur recherché
  "financing": "preapproved"|"cash"|"pending"|"none"|null,
  "timeline": "<6"|"6-12"|"12-24"|"flexible"|null
}
Règles : budget exprimé en euros (k = millier, M = million) ; financing :
"preapproved" si le prêt est déjà accordé/pré-accordé, "cash" si paiement comptant/apport,
"pending" si financement à prévoir, "none" si aucun financement.
Mets "null" pour toute donnée absente. Ne mets JAMAIS de texte hors JSON."""

SYSTEM_QUESTION = """Tu es {assistant_name}, conseiller immobilier premium et chaleureux pour l'agence « {agency_name} » à {city}.
Ton ton : humain, bienveillant, naturel — comme un conseiller de confiance qui discute, jamais robotique.
Parle en français, sans markdown ni emojis excessifs. Sois bref : 1 à 2 phrases maximum, TOUJOURS complètes, jamais coupées.
Contexte du prospect : {context}
Ton rôle : poser UNE seule question pour qualifier le projet (question {n}/5, catégorie « {label} »).
QUESTION À POSER MAINTENANT :
{template}
Adapte la formulation au profil connu du prospect (cite son prénom ou son projet si tu les connais), de façon naturelle.
Ne pose JAMAIS une autre question et ne réponds pas à sa place.
Réponds UNIQUEMENT avec la question, directement : aucun titre, aucune étiquette,
aucun préfixe ("Question :", "Ask for..."), aucune apostrophe de formatage, aucune note.
Termine TOUJOURS ta phrase (jamais de texte tronqué)."""

SYSTEM_CLOSING = """Tu es un expert immobilier chaleureux. À partir de la conversation, réponds UNIQUEMENT en JSON valide :
{
  "profile": {
    "name": string|null,
    "project_type": "maison"|"appartement"|"investissement"|"terrain"|"autre"|null,
    "budget": "600k+"|"400-600k"|"250-400k"|"150-250k"|"<150k"|null,
    "city": string|null,
    "financing": "preapproved"|"cash"|"pending"|"none"|null,
    "timeline": "<6"|"6-12"|"12-24"|"flexible"|null
  },
  "summary": "résumé de 2-3 phrases du projet (type, budget, ville, financement, délai, maturité)",
  "message": "message de clôture humain et premium, 2 phrases maximum, en français, COMPLET (jamais coupé) :
     - si qualifié : félicite chaleureusement le prospect et invite à réserver le rendez-vous expert ;
     - sinon : remercie et annonce qu'un conseiller le recontactera très vite."
}
Règles : budget exprimé en euros (k = millier, M = million) ; financing : "preapproved" si prêt déjà accordé,
"cash" si comptant/apport, "pending" si financement à prévoir, "none" si aucun.
Ne mets JAMAIS de texte hors JSON."""


def build_context(profile: dict) -> str:
    parts = []
    if profile.get("name"):
        parts.append(f"prénom : {profile['name']}")
    if profile.get("project_type"):
        parts.append(f"projet : {profile['project_type']}")
    if profile.get("budget"):
        parts.append(f"budget : {profile['budget']}")
    if profile.get("city"):
        parts.append(f"ville : {profile['city']}")
    if profile.get("financing"):
        parts.append(f"financement : {profile['financing']}")
    if profile.get("timeline"):
        parts.append(f"délai : {profile['timeline']}")
    return "; ".join(parts) if parts else "aucune information pour l'instant"


def score_profile(profile: dict, agency_city: str, points: dict | None = None) -> tuple[int, dict]:
    """Scoring déterministe : chaque réponse ajoute des points (max 100).
    `points` optionnel = tables personnalisées du client (défaut = tables actuelles).
    Le fallback déterministe et les règles existantes sont conservés."""
    return chatbot_config.apply_points(profile, agency_city, points)


# ---- Extraction de secours par règles (sans Gemini) ---------------------------
def extract_profile_rules(messages: list[dict], agency_city: str) -> dict:
    text = " ".join(m["content"] for m in messages if m["role"] == "user").lower()
    prof = {"name": None, "project_type": None, "budget": None,
            "city": None, "financing": None, "timeline": None}

    # le prénom est demandé dans le tout premier échange : on le cherche uniquement
    # dans le premier message utilisateur (évite de déborder sur le reste du chat)
    first_user = next((m["content"] for m in messages if m["role"] == "user"), "").lower()
    m = re.search(r"je m['’]appelle\s+([a-zà-ÿ][a-zà-ÿ\-\s']{0,40})", first_user)
    if m:
        name = re.split(r"\s+(?:et|mais|je|mon|notre|nous|un|une|dans|pour|sur|avec)\s+",
                        m.group(1))[0]
        prof["name"] = name.strip().title()
    if any(k in text for k in ["maison", "construction", "faire construire"]):
        prof["project_type"] = "maison"
    elif "appartement" in text:
        prof["project_type"] = "appartement"
    elif any(k in text for k in ["locatif", "investissement", "secondaire"]):
        prof["project_type"] = "investissement"
    elif "terrain" in text:
        prof["project_type"] = "terrain"

    # budget : extrait un montant en euros (ex: 350000, 350 k, 350 000 €)
    mb = re.search(r"(\d[\d\s.]{1,9})\s*(k|m|millions?)?\s*(?:€|euros?)?", text)
    if mb:
        num = float(re.sub(r"[^\d]", "", mb.group(1)))
        unit = (mb.group(2) or "").lower()
        if unit == "k":
            num *= 1_000
        elif unit == "m":
            num *= 1_000_000
        if num >= 10_000:  # évite les faux positifs (années, téléphones…)
            prof["budget"] = ("600k+" if num >= 600_000 else
                              "400-600k" if num >= 400_000 else
                              "250-400k" if num >= 250_000 else
                              "150-250k" if num >= 150_000 else "<150k")

    if agency_city and agency_city.lower() in text:
        prof["city"] = agency_city.title()
    elif any(k in text for k in ["ville", "secteur", "à ", "sur "]):
        mc = re.search(r"(?:à|sur|vers|autour de)\s+([a-zà-ÿ][a-zà-ÿ\-\s]{2,30})", text)
        if mc and " " not in mc.group(1).strip():
            prof["city"] = mc.group(1).strip().title()

    if any(k in text for k in ["pré-accordé", "preaccord", "accordé", "déjà accordé"]):
        prof["financing"] = "preapproved"
    elif any(k in text for k in ["comptant", "cash", "apport", "sans crédit"]):
        prof["financing"] = "cash"
    elif any(k in text for k in ["prêt", "credit", "financement", "emprunt"]):
        prof["financing"] = "pending"
    elif any(k in text for k in ["aucun", "pas de financement", "rien"]):
        prof["financing"] = "none"

    if any(k in text for k in ["urgent", "dès que possible", "au plus vite", "le plus tôt possible", "rapide", "rapidement", "3 mois", "6 mois"]):
        prof["timeline"] = "<6" if "12" not in text else "6-12"
    elif any(k in text for k in ["6 à 12", "6-12", "un an", "1 an", "12 mois"]):
        prof["timeline"] = "6-12"
    elif any(k in text for k in ["2 ans", "deux ans", "24 mois"]):
        prof["timeline"] = "12-24"
    elif any(k in text for k in ["flexible", "pas pressé", "aucune urgence", "ne sait pas"]):
        prof["timeline"] = "flexible"
    return prof


def extract_profile(messages: list[dict], agency_city: str) -> dict:
    """Extraction IA du profil (JSON) avec repli 100% règles."""
    convo = "\n".join(f"{'Prospect' if m['role']=='user' else 'Assistant'}: {m['content']}"
                      for m in messages[-12:])
    data = ai_json(SYSTEM_EXTRACT, convo)
    if data and isinstance(data, dict):
        cleaned = {k: (data.get(k) or None) for k in
                   ("name", "project_type", "budget", "city", "financing", "timeline")}
        return cleaned
    return extract_profile_rules(messages, agency_city)


def generate_welcome(agency: dict, assistant_name: str | None = None,
                     welcome_message: str | None = None, tone: str = "chaleureux") -> str:
    """Message d'accueil de l'assistant, au nom de l'agence.
    Si `welcome_message` est défini (config client), il est utilisé tel quel."""
    if welcome_message:
        return welcome_message.strip()
    a_name = assistant_name or agency.get("name")
    sys_p = (f"Tu es {a_name}, conseiller immobilier premium et humain de l'agence {agency.get('name')} à "
             f"{agency.get('city','')}. Ton ton : {tone}, chaleureux, naturel, très concis (2-3 phrases). "
             f"En français uniquement, sans markdown ni emoji excessif. Accueille le visiteur au nom de "
             f"l'agence, présente-toi en quelques mots et pose UNE seule question : son prénom. "
             f"Termine TOUJOURS ta phrase (jamais de texte coupé). Message : « {agency.get('description','')} »\n"
             f"Réponds UNIQUEMENT avec le message d'accueil lui-même : aucun titre, aucune étiquette, "
             f"aucun préfixe (\"Message :\", \"Ask for...\", \"Accueil :\"), aucune apostrophe de formatage.")
    msg = ai_complete(sys_p, "Présente-toi et demande le prénom du prospect.", temperature=0.8, max_tokens=350)
    if msg:
        return msg.strip()
    return (f"Bonjour et bienvenue chez {agency.get('name')} 👋 "
            f"Je suis votre conseiller virtuel, ravi de vous accompagner pour votre projet "
            f"immobilier à {agency.get('city', 'votre région')}. "
            f"Puis-je connaître votre prénom ?")


def generate_question(agency: dict, profile: dict, index: int,
                      questions: list | None = None) -> str:
    qs = questions or QUESTIONS
    item = qs[index]
    if isinstance(item, dict):
        key, label, template = item.get("key", "autre"), item.get("label", ""), item.get("template", "")
    elif len(item) >= 3:
        key, label, template = item[0], item[1], item[2]
    else:
        key, label, template = item[0], "", item[1]
    sys_p = SYSTEM_QUESTION.format(
        assistant_name=agency.get("assistant_name") or agency.get("name", "l'agence"),
        agency_name=agency.get("name", ""),
        city=agency.get("city", ""),
        context=build_context(profile),
        n=index + 1, label=label or key, template=template,
    )
    msg = ai_complete(sys_p, "Pose la question.", temperature=0.6, max_tokens=300)
    if msg:
        return msg.strip()
    return f"{template}"


def generate_closing(agency: dict, profile: dict, messages: list[dict],
                     score: int, qualified: bool) -> tuple[dict, str, str]:
    """Clôture en UN SEUL appel IA (profil final + résumé + message) pour la
    rapidité. Retourne (profil_final, summary, message). Repli : profil courant
    (déjà fusionné par règles) + messages modèles."""
    convo = "\n".join(f"{'Prospect' if m['role']=='user' else 'Assistant'}: {m['content']}"
                      for m in messages[-12:])
    ctx = (f"Profil actuel : {build_context(profile)} | score={score}/100 | "
           f"qualifié={'oui' if qualified else 'non'}")
    data = ai_json(SYSTEM_CLOSING, f"{ctx}\n\nConversation :\n{convo}", max_tokens=1200)
    if data and isinstance(data, dict):
        p = data.get("profile") or {}
        cleaned = {k: (p.get(k) or None) for k in
                   ("name", "project_type", "budget", "city", "financing", "timeline")}
        merged = {**profile, **{k: v for k, v in cleaned.items() if v}}
        return merged, data.get("summary", ""), data.get("message", "")
    if qualified:
        return (profile,
                f"Projet de type {profile.get('project_type') or 'immobilier'}, budget "
                f"{profile.get('budget') or 'à définir'}, secteur {profile.get('city') or 'à préciser'} — "
                f"profil mature et qualifié.",
                f"Excellent, {profile.get('name') or 'cher visiteur'}! Votre projet est très "
                f"prometteur. Réservez dès maintenant votre rendez-vous expert, on s'occupe de tout.")
    return (profile,
            f"Profil à maturité variable (budget {profile.get('budget') or 'à préciser'}, "
            f"financement {profile.get('financing') or 'à confirmer'}).",
            f"Merci {profile.get('name') or 'pour votre confiance'}, un conseiller de "
            f"{agency.get('name')} reviendra vers vous très rapidement pour étudier votre projet.")


# ───────────────────────────────────────────────────────────────────────────────
# 7. DESIGN SYSTEM — CSS premium (Inter, glassmorphism, Apple-like, gold CTA)
# ───────────────────────────────────────────────────────────────────────────────

# Avatar de l'assistant : petit robot souriant humanisé (SVG embarqué, aucune
# dépendance externe). Streamlit convertit automatiquement ce SVG en image.
ROBOT_AVATAR_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
<defs><linearGradient id="mng" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#F0D48A"/><stop offset="1" stop-color="#C9A227"/></linearGradient></defs>
<rect x="7" y="22" width="7" height="14" rx="3.5" fill="#9C7A14"/>
<rect x="50" y="22" width="7" height="14" rx="3.5" fill="#9C7A14"/>
<rect x="13" y="12" width="38" height="34" rx="13" fill="url(#mng)"/>
<rect x="29" y="3" width="6" height="9" rx="3" fill="#9C7A14"/>
<circle cx="32" cy="3" r="4.5" fill="#C9A227"/>
<circle cx="24" cy="27" r="5" fill="#221A04"/>
<circle cx="40" cy="27" r="5" fill="#221A04"/>
<circle cx="25.6" cy="25.4" r="1.7" fill="#fff"/>
<circle cx="41.6" cy="25.4" r="1.7" fill="#fff"/>
<circle cx="17" cy="32" r="2.6" fill="#fff" opacity="0.55"/>
<circle cx="47" cy="32" r="2.6" fill="#fff" opacity="0.55"/>
<path d="M22.5 38 Q32 46.5 41.5 38" stroke="#221A04" stroke-width="3.2" fill="none" stroke-linecap="round"/>
</svg>"""

APP_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Playfair+Display:ital,wght@0,500;0,600;0,700;0,800;1,600&display=swap');

:root {
  --gold: #C9A227; --gold-dark: #9C7A14; --gold-soft: #F3E5B8; --gold-pale: #FBF6E5;
  --ink: #161616; --gray: #8E8E93; --bubble: #F4F4F6;
}

html, body, [class*="css"], [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

.stApp { background: #FFFFFF; }
[data-testid="stHeader"] { background: transparent; }

/* fond léger dégradé pour révéler le glassmorphism (reste quasi blanc) */
.stApp::before {
  content:""; position: fixed; inset: 0; z-index: 0; pointer-events: none;
  background:
    radial-gradient(900px 500px at 90% -15%, rgba(201,162,39,.12), transparent 55%),
    radial-gradient(800px 600px at -15% 115%, rgba(201,162,39,.09), transparent 55%),
    radial-gradient(600px 400px at 115% 60%, rgba(28,28,30,.04), transparent 55%);
  animation: aurora 16s ease-in-out infinite alternate;
}
@keyframes aurora {
  0%   { transform: translateY(0) scale(1); }
  100% { transform: translateY(-16px) scale(1.04); }
}

/* scrollbar raffinée */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(201,162,39,.35); border-radius: 8px; }
::-webkit-scrollbar-thumb:hover { background: rgba(201,162,39,.55); }
[data-testid="stVerticalBlock"] { position: relative; z-index: 1; }

/* masquer 100 % du chrome Streamlit (menu, footer « Made with Streamlit »,
   bouton Deploy, indicateur d'exécution, toolbar) — zéro filigrane */
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"],
[data-testid="stStatusWidget"], [data-testid="stFooter"], [data-testid="stAppDeployButton"],
[data-testid="stSidebarNav"], [data-testid="stPopoverMenu"], .stDeployButton {
  display: none !important; visibility: hidden !important; height: 0 !important;
}
[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stAppViewContainer"] { max-width: 100vw; }

/* ---------- typographie & titres ---------- */
h1, h2, h3, h4 { font-family: 'Playfair Display', serif; letter-spacing: -0.01em; }
h1 { font-weight: 800; }
p, li, label, span { font-family: 'Inter', sans-serif; }

/* ---------- verre dépoli générique (glass card) ---------- */
.glass {
  background: linear-gradient(145deg, rgba(255,255,255,.88), rgba(255,255,255,.64));
  backdrop-filter: blur(22px) saturate(170%);
  -webkit-backdrop-filter: blur(22px) saturate(170%);
  border: 1px solid rgba(255,255,255,.7);
  outline: 1px solid rgba(0,0,0,.05);
  border-radius: 24px;
  box-shadow: 0 8px 32px rgba(31,38,66,.08);
  padding: 22px 26px; margin: 10px 0;
}

/* ---------- en-tête agence ---------- */
.agency-header { display:flex; align-items:center; gap:18px; margin: 14px 0 6px; }
.agency-logo-ring { position:relative; width:68px; height:68px; flex:0 0 auto; padding:3px;
  border-radius:22px; background:linear-gradient(135deg,#F0D48A,#C9A227 55%,#8F6E10);
  box-shadow: 0 8px 22px rgba(201,162,39,.35); }
.agency-logo { width:100%; height:100%; border-radius:19px; object-fit:cover; background:#fff; display:block; }
.agency-logo-fallback { width:100%; height:100%; border-radius:19px; display:flex; align-items:center;
  justify-content:center; font-size:30px; background:rgba(255,255,255,.92); }
.agency-name { font-family:'Playfair Display', serif; font-size:26px; font-weight:700; color:var(--ink); line-height:1.12; }
.agency-tag { font-size:13.5px; color:var(--gray); font-weight:500; margin-top:2px; }
.agency-pill { display:inline-flex; align-items:center; gap:6px; margin-top:8px; font-size:10.5px; font-weight:700;
  letter-spacing:.09em; text-transform:uppercase; color:var(--gold-dark);
  background:linear-gradient(135deg,#FBF3D9,#F3E5B8); border:1px solid rgba(201,162,39,.25);
  padding:5px 12px; border-radius:999px; }

/* ---------- progression des 5 questions ---------- */
.q-progress { display:flex; gap:8px; margin:14px 0 2px; }
.q-dot { width:26px; height:6px; border-radius:999px; background:#E7E7EA; transition:all .4s ease; }
.q-dot.done { background:linear-gradient(90deg,#E8CE7E,#C9A227); box-shadow:0 0 10px rgba(201,162,39,.45); }

/* ---------- barre de score ---------- */
.score-wrap { margin: 16px 0 4px; }
.score-head { display:flex; justify-content:space-between; align-items:baseline; margin-bottom:9px; }
.score-label { font-size:11px; font-weight:700; letter-spacing:.1em; text-transform:uppercase; color:var(--gray); }
.score-val { font-size:30px; font-weight:800; font-family:'Playfair Display', serif; color:var(--ink); line-height:1; }
.score-val small { font-size:13px; font-weight:600; color:var(--gray); font-family:'Inter',sans-serif; }
.score-track { position:relative; height:14px; border-radius:999px;
  background:linear-gradient(90deg,#F1F1F4,#ECECEF); overflow:visible; box-shadow:inset 0 1px 3px rgba(0,0,0,.06); }
.score-fill { position:absolute; top:0; left:0; height:100%; border-radius:999px;
  background:linear-gradient(90deg,#F0D48A,#C9A227 60%,#A8821A);
  box-shadow:0 0 14px rgba(201,162,39,.5); transition: width .7s cubic-bezier(.2,.8,.2,1); }
.score-threshold { position:absolute; top:-5px; width:3px; height:24px; border-radius:3px;
  background:var(--ink); opacity:.5; }
.score-foot { display:flex; justify-content:space-between; margin-top:8px; font-size:11.5px; color:var(--gray); font-weight:500; }

/* ---------- chat (bulles style iMessage/Apple) ---------- */
[data-testid="stChatMessage"] { max-width: 640px; margin-left:auto; margin-right:auto;
  overflow: visible !important; }
@keyframes msgIn { from { opacity:0; } to { opacity:1; } }
[data-testid="stChatMessage"] { animation: msgIn .25s ease-out; }
[data-testid="stChatMessageAvatar"], [data-testid^="stChatMessageAvatar"] {
  width: 38px; height: 38px; min-width: 38px; min-height: 38px;
  display: flex; align-items: center; justify-content: center;
  font-size: 18px; line-height: 1; overflow: visible !important; border-radius: 50%;
}
[data-testid="stChatMessageAvatar"] img {
  width: 100% !important; height: 100% !important; object-fit: cover;
  border-radius: 50%; box-shadow: 0 3px 10px rgba(201,162,39,.35);
}
[data-testid="stChatMessageContent"] {
  padding: 12px 16px; border-radius: 20px; overflow: visible !important;
  background: #FFFFFF; border: 1px solid rgba(0,0,0,.06);
  box-shadow: 0 2px 12px rgba(31,38,66,.06);
  min-width: 0; max-width: 100%;
  overflow-wrap: break-word; word-break: break-word;
}
[data-testid="stChatMessageContent"] * {
  overflow-wrap: break-word; word-break: break-word; white-space: normal;
}
[data-testid="stChatMessageContent"] p {
  font-size: 15.5px; line-height: 1.65; color: var(--ink); margin: 0;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) [data-testid="stChatMessageContent"] {
  background: var(--bubble); border: 1px solid rgba(0,0,0,.04);
  border-bottom-right-radius: 6px;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) [data-testid="stChatMessageContent"] {
  border-bottom-left-radius: 6px;
}

/* indicateur "l'assistant écrit…" (3 points dorés animés) */
.typing { display:inline-flex; align-items:center; gap:5px; padding:4px 2px; }
.typing span { width:8px; height:8px; border-radius:50%; background:#C9A227; animation: blink 1.2s infinite; }
.typing span:nth-child(2) { animation-delay:.2s; }
.typing span:nth-child(3) { animation-delay:.4s; }
@keyframes blink { 0%,60%,100% { opacity:.25; transform:translateY(0);} 30% { opacity:1; transform:translateY(-3px);} }

/* ---------- input de chat (pilule flottante) ---------- */
div[data-testid="stChatInput"] { max-width: 620px; margin-left:auto; margin-right:auto;
  background: rgba(255,255,255,.9); backdrop-filter: blur(18px);
  border: 1px solid rgba(0,0,0,.08); border-radius: 32px;
  box-shadow: 0 10px 30px rgba(31,38,66,.12); padding: 7px 9px;
  transition: border-color .2s, box-shadow .2s; }
div[data-testid="stChatInput"]:focus-within {
  border-color: rgba(201,162,39,.55);
  box-shadow: 0 12px 34px rgba(31,38,66,.14), 0 0 0 4px rgba(201,162,39,.12);
}
div[data-testid="stChatInput"] textarea { border-radius: 26px !important; font-family:'Inter',sans-serif; }
div[data-testid="stChatInput"] button {
  background: linear-gradient(135deg,#F0D48A,#C9A227) !important;
  border-radius: 50% !important; width: 40px !important; height: 40px !important;
  box-shadow: 0 4px 12px rgba(201,162,39,.4) !important;
}

/* ---------- CTA doré (rendez-vous / actions) ---------- */
div[data-testid="stLinkButton"] a, div[data-testid="stButton"] button {
  font-family: 'Inter', sans-serif; font-weight: 800; letter-spacing: .01em;
  border: none; border-radius: 18px !important; color: #221A04 !important;
  position: relative; overflow: hidden;
  background: linear-gradient(135deg, #F0D48A 0%, #D4AF37 45%, #B8860B 100%) !important;
  box-shadow: 0 12px 30px rgba(184,134,11,.4), inset 0 1px 0 rgba(255,255,255,.55) !important;
  transition: transform .18s ease, box-shadow .18s ease !important;
}
div[data-testid="stLinkButton"] a::after, div[data-testid="stButton"] button::after {
  content:""; position: absolute; top: 0; left: -80%; width: 50%; height: 100%;
  background: linear-gradient(120deg, transparent, rgba(255,255,255,.55), transparent);
  transform: skewX(-20deg); animation: shimmer 3.2s ease-in-out infinite;
}
@keyframes shimmer { 0% { left: -80%; } 55% { left: 130%; } 100% { left: 130%; } }
div[data-testid="stLinkButton"] a:hover, div[data-testid="stButton"] button:hover {
  transform: translateY(-2px) scale(1.015);
  box-shadow: 0 18px 40px rgba(184,134,11,.5), inset 0 1px 0 rgba(255,255,255,.55) !important;
}
div[data-testid="stLinkButton"] a:active, div[data-testid="stButton"] button:active { transform: translateY(0); }
div[data-testid="stButton"] button[kind="secondary"] {
  background: var(--bubble) !important; color: var(--ink) !important;
  box-shadow: none !important; border: 1px solid rgba(0,0,0,.07) !important;
}
div[data-testid="stButton"] button[kind="secondary"]::after { display: none; }

/* ---------- formulaires admin ---------- */
[data-testid="stTextInput"] input, [data-testid="stNumberInput"] input, [data-testid="stTextArea"] textarea,
[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
  border-radius: 14px !important; font-family:'Inter',sans-serif;
  background: rgba(255,255,255,.85); border: 1px solid rgba(0,0,0,.09);
}
[data-testid="stTextInput"] input:focus, [data-testid="stTextArea"] textarea:focus {
  border-color: var(--gold) !important; box-shadow: 0 0 0 3px rgba(201,162,39,.18) !important;
}
[data-testid="stSlider"] div[data-baseweb="slider"] div[role="slider"] { background: var(--gold) !important; }
[data-testid="stSlider"] div[data-baseweb="slider"] div { background: var(--gold-soft); }

/* ---------- tableaux ---------- */
[data-testid="stDataFrame"] { border-radius: 18px; overflow: hidden;
  border: 1px solid rgba(0,0,0,.06); box-shadow: 0 6px 24px rgba(31,38,66,.07); }

/* ---------- onglets (pills) ---------- */
[data-testid="stTabs"] { gap: 8px; }
[data-testid="stTabs"] button { font-family:'Inter',sans-serif; font-weight:600; border-radius:12px !important; }
[data-testid="stTabs"] button[aria-selected="true"] {
  background: linear-gradient(135deg, rgba(240,212,138,.4), rgba(201,162,39,.2)) !important;
  color: var(--gold-dark) !important;
}

/* ---------- métriques ---------- */
[data-testid="stMetric"] {
  background: linear-gradient(145deg, rgba(255,255,255,.92), rgba(250,246,235,.8));
  border: 1px solid rgba(0,0,0,.05); border-radius: 18px; padding: 14px 16px;
  box-shadow: 0 8px 32px rgba(31,38,66,.08);
}
[data-testid="stMetricLabel"] { font-size:11px !important; font-weight:700 !important;
  letter-spacing:.06em; text-transform:uppercase; color:var(--gray) !important; }
[data-testid="stMetricValue"] { font-family:'Playfair Display', serif !important;
  font-size:26px !important; font-weight:700 !important; color:var(--ink) !important; }

/* ---------- badges / tags ---------- */
.badge { display:inline-block; padding:3px 12px; border-radius:999px; font-size:12px; font-weight:700; }
.badge-ok  { background:#E8F5E9; color:#1B5E20; }
.badge-ko  { background:#FFF3E0; color:#B26A00; }
.muted { color: var(--gray); font-size: 13px; }

/* ---------- assistant de configuration (stepper 8 étapes) ---------- */
.wiz-progress { margin: 14px 0 4px; display:flex; align-items:center; gap:12px; }
.wiz-progress .wiz-bar { flex:1; height:10px; border-radius:999px; background:#ECECEF; overflow:hidden;
  box-shadow: inset 0 1px 3px rgba(0,0,0,.06); }
.wiz-progress .wiz-bar i { display:block; height:100%; border-radius:999px;
  background:linear-gradient(90deg,#F0D48A,#C9A227 60%,#A8821A);
  box-shadow:0 0 12px rgba(201,162,39,.45); transition: width .5s cubic-bezier(.2,.8,.2,1); }

</style>
"""


def inject_css():
    st.markdown(APP_CSS, unsafe_allow_html=True)


def render_agency_header(agency: dict):
    logo = agency.get("logo_url", "").strip()
    logo_html = (f'<img class="agency-logo" src="{html.escape(logo)}" onerror="this.style.display=\'none\'"/>'
                 if logo else '<div class="agency-logo-fallback">🏡</div>')
    st.markdown(
        f"""
        <div class="agency-header">
          <div class="agency-logo-ring">{logo_html}</div>
          <div>
            <div class="agency-name">{html.escape(agency.get('name',''))}</div>
            <div class="agency-tag">{html.escape(agency.get('description','') or 'Agence immobilière')}</div>
            <span class="agency-pill">✦ Qualification immobilière</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_question_progress(done: int, labels: list[str] | None = None):
    """Pastille de progression des questions (dot doré = question validée)."""
    if not labels:
        labels = [q[1] for q in QUESTIONS]
    dots = "".join(
        f'<span class="q-dot {"done" if i < done else ""}" title="{labels[i]}"></span>'
        for i in range(len(labels)))
    st.markdown(f'<div class="q-progress">{dots}</div>', unsafe_allow_html=True)


def score_bar(score: int, threshold: int):
    pct = max(0, min(100, score))
    pct_t = max(0, min(100, threshold))
    st.markdown(
        f"""
        <div class="score-wrap">
          <div class="score-head">
            <span class="score-label">Niveau de qualification</span>
            <span class="score-val">{pct}<small>/100</small></span>
          </div>
          <div class="score-track">
            <div class="score-fill" style="width:{pct}%"></div>
            <div class="score-threshold" style="left:{pct_t}%"></div>
          </div>
          <div class="score-foot"><span>Seuil de l'agence : {threshold}</span>
            <span>{'✅ Qualifié' if pct >= threshold else 'En cours…'}</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ───────────────────────────────────────────────────────────────────────────────
# 8. INTERFACE PROSPECT — la conversation de qualification
# ───────────────────────────────────────────────────────────────────────────────

def render_prospect(slug: str, test_mode: bool = False):
    agency = get_agency(slug)
    if agency is None:
        st.markdown(
            """
            <div class="glass" style="text-align:center; padding:48px 28px;">
              <div style="font-size:52px;">🏠</div>
              <h2 style="margin:10px 0 6px;">Agence introuvable</h2>
              <p class="muted">Le lien de qualification est invalide ou l'agence n'existe plus.<br/>
              Contactez votre conseiller immobilier pour obtenir un lien valide.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.stop()

    # ---- configuration client (questions, points, seuil, assistant, thème) ----
    cfg = chatbot_config.get_config_for_agency(agency, slug)
    questions = cfg["questions"]
    points = cfg["points"]
    threshold = cfg["threshold"]
    assistant = cfg["assistant"]

    # ---- session de conversation ----------------------------------------------
    ss = st.session_state
    if "prospect_stage" not in ss:
        ss.prospect_stage = "welcome"        # welcome → chat (5 questions) → closing
        ss.messages = []
        ss.q_index = 0
        ss.answers = {}                       # dernière valeur connue par catégorie
        ss.profile = {"name": None, "project_type": None, "budget": None,
                      "city": None, "financing": None, "timeline": None}
        ss.score = 0
        ss.summary = ""
        ss.session_id = uuid.uuid4().hex[:10]
        ss.qualified = False
        ss.final_msg = ""
        ss.thinking = False                   # vrai pendant que l'assistant "écrit"
        # message d'accueil généré par l'IA au nom de l'agence (ou message client)
        ss.messages.append({"role": "assistant", "content": generate_welcome(
            agency, assistant_name=assistant.get("name") or None,
            welcome_message=assistant.get("welcome_message") or None,
            tone=assistant.get("tone") or "chaleureux")})

    render_agency_header(agency)
    inject_agency_theme(agency)

    if ss.prospect_stage != "welcome":
        q_done = len(questions) if ss.prospect_stage == "closing" else ss.q_index
        render_question_progress(q_done, labels=[q[1] for q in questions])
        score_bar(ss.score, threshold)

    # ---- historique du chat ----------------------------------------------------
    for msg in ss.messages:
        with st.chat_message(msg["role"],
                             avatar=ROBOT_AVATAR_SVG if msg["role"] == "assistant" else "👤"):
            st.markdown(msg["content"])

    # indicateur "l'assistant écrit…" (3 points animés)
    if ss.thinking:
        with st.chat_message("assistant", avatar=ROBOT_AVATAR_SVG):
            st.markdown('<div class="typing"><span></span><span></span><span></span></div>',
                        unsafe_allow_html=True)

    # ---- logique : réponse prospect en attente ? (pendant l'indicateur "écrit…") --
    if ss.thinking:
        # 1) extraction du profil PAR RÈGLES (instantanée, zéro appel IA) et mise à
        #    jour cumulée — l'appel IA unique n'a lieu qu'à la clôture. Résultat :
        #    une seule requête Gemini par tour, donc des réponses ~2× plus rapides.
        extracted = extract_profile_rules(ss.messages, agency.get("city", ""))
        for key, val in extracted.items():
            if val and not ss.answers.get(key):
                ss.answers[key] = val
        ss.profile = {**ss.profile, **ss.answers}
        ss.score, _ = score_profile(ss.profile, agency.get("city", ""), points=points)

        if ss.prospect_stage == "welcome":
            # on connaît le prénom → on démarre le questionnaire
            ss.prospect_stage = "chat"
            ss.messages.append({"role": "assistant",
                                "content": generate_question(agency, ss.profile, 0, questions=questions)})
        elif ss.q_index < len(questions) - 1:
            ss.q_index += 1
            ss.messages.append({"role": "assistant",
                                "content": generate_question(agency, ss.profile, ss.q_index, questions=questions)})
        else:
            # ---- CLOSING : UN seul appel IA (profil final + résumé + message) ----
            try:
                qualified = ss.score >= threshold
                final_profile, summary, closing = generate_closing(
                    agency, ss.profile, ss.messages, ss.score, qualified)
                ss.profile = {**ss.profile, **{k: v for k, v in final_profile.items() if v}}
                ss.score, _ = score_profile(ss.profile, agency.get("city", ""), points=points)
                qualified = ss.score >= threshold
                ss.summary, ss.qualified, ss.final_msg = summary, qualified, closing
                save_lead(agency, slug, ss.profile, ss.score, qualified, summary, ss.session_id,
                          test_mode=test_mode)
                if not test_mode:
                    notify_agency(agency, ss.profile.get("name", ""), ss.score, qualified)
                st.toast("🧪 Profil TEST enregistré (séparé des leads réels)" if test_mode
                         else ("📩 Profil enregistré — l'agence a été notifiée" if qualified
                                else "📩 Profil enregistré"))
            except Exception as exc:
                # la clôture doit TOUJOURS aboutir (pas de doublon, pas d'écran d'erreur)
                logging.error("Clôture impossible : %s", exc)
                summary = ss.summary or "Profil qualifié."
                closing = ss.final_msg or ("Merci, un conseiller reviendra vers vous.")
                ss.qualified = ss.score >= threshold
            ss.messages.append({"role": "assistant", "content": closing})
            ss.prospect_stage = "closing"

        ss.thinking = False
        st.rerun()

    # ---- saisie ----------------------------------------------------------------
    if ss.prospect_stage in ("welcome", "chat") and not ss.thinking:
        prompt = st.chat_input("Écrivez votre réponse…", key="chat_prospect")
        if prompt and prompt.strip():
            ss.messages.append({"role": "user", "content": prompt.strip()})
            ss.thinking = True
            st.rerun()

    # ---- écran final (score >= seuil → bouton doré Calendly) --------------------
    if ss.prospect_stage == "closing":
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        parts = score_profile(ss.profile, agency.get("city", ""), points=points)[1]
        parts_html = "".join(
            f"<span class='badge badge-ok'>{html.escape(k)} : {v} pts</span> " for k, v in parts.items()
        )
        if ss.qualified:
            st.markdown(
                f"""
                <div class="glass" style="text-align:center;">
                  <div style="font-size:44px;">🏆</div>
                  <h3 style="margin:4px 0 2px;">Projet éligible !</h3>
                  <p class="muted">Score <b>{ss.score}/100</b> — seuil requis {threshold}</p>
                  <div style="margin:8px 0 14px;">{parts_html}</div>
                  <p style="font-size:14.5px; color:var(--ink); line-height:1.6;">
                    Votre profil correspond parfaitement aux critères de {html.escape(agency.get('name',''))}.
                    Un expert vous attend pour concrétiser votre projet.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.link_button("✦  Réserver mon rendez-vous expert",
                           agency.get("calendly_url", "#"), use_container_width=True)
            st.markdown(
                "<div style='text-align:center' class='muted'>"
                "✨ Prise de rendez-vous 100% sécurisée · Réponse sous 24h</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <div class="glass" style="text-align:center;">
                  <div style="font-size:44px;">🤝</div>
                  <h3 style="margin:4px 0 2px;">Merci pour votre confiance</h3>
                  <p class="muted">Score <b>{ss.score}/100</b> — seuil requis {threshold}</p>
                  <div style="margin:8px 0 14px;">{parts_html}</div>
                  <p style="font-size:14.5px; color:var(--ink); line-height:1.6;">
                    Un conseiller {html.escape(agency.get('name',''))} reviendra vers vous
                    très rapidement pour étudier votre projet.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("<div style='text-align:center; margin-top:26px;' class='muted'>"
                "Propulsé par <b>MaisonNova Engine</b> · Qualification assistée par IA</div>",
                unsafe_allow_html=True)


# ───────────────────────────────────────────────────────────────────────────────
# 8bis. THÈME CLIENT (couleurs) + PRÉVISUALISATION ADMIN (mode TEST)
# ───────────────────────────────────────────────────────────────────────────────

def _hex_to_rgb(h: str) -> tuple | None:
    h = (h or "").strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        return None
    try:
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return None


def _mix_hex(h: str, white: int, factor: float) -> str:
    rgb = _hex_to_rgb(h)
    if not rgb:
        return h
    out = tuple(round(c + (white - c) * factor) for c in rgb)
    return "#{:02X}{:02X}{:02X}".format(*out)


def inject_agency_theme(agency: dict):
    """Surcharge les variables dorées du design par les couleurs du client
    (les classes existantes utilisent var(--gold…) → aucune régression CSS)."""
    primary = (agency or {}).get("primary_color") or ""
    secondary = (agency or {}).get("secondary_color") or ""
    if not primary and not secondary:
        return
    p = primary or "#C9A227"
    s = secondary or "#9C7A14"
    soft = _mix_hex(p, 255, 0.75)
    pale = _mix_hex(p, 255, 0.92)
    st.markdown(
        f"<style>:root{{--gold:{p};--gold-dark:{s};--gold-soft:{soft};--gold-pale:{pale};}}</style>",
        unsafe_allow_html=True,
    )


def _reset_prospect_state():
    for k in ("prospect_stage", "messages", "q_index", "answers", "profile",
              "score", "summary", "session_id", "qualified", "final_msg", "thinking"):
        st.session_state.pop(k, None)


def render_admin_preview():
    """Onglet 👁 Prévisualisation : choisir une agence puis tester le chat.
    Mode test par défaut → leads marqués TEST, séparés des leads réels."""
    st.markdown("### 👁 Prévisualiser le chatbot")
    clients = clients_store.load_clients()
    if not clients:
        st.info("Aucun client. Créez-en un dans l'onglet « 🏢 Clients ».")
        return
    options = [(ag.get("name") or cid, cl.get("slug") or cid)
               for cid, cl in clients.items()
               for ag in [cl.get("agency") or {}]]
    labels = [n for n, _ in options]
    sel = st.selectbox("Agence à prévisualiser", labels, key="pv_sel")
    slug = next((s for n, s in options if n == sel), options[0][1] if options else None)
    test_mode = st.checkbox("Mode test — les leads sont marqués TEST et séparés des leads réels",
                            value=True, key="pv_test")
    if st.button("🔄 Nouvelle conversation", key="pv_reset"):
        _reset_prospect_state()
        st.rerun()
    if slug:
        st.caption(f"Prévisualisation de « {sel} » · mode {'TEST' if test_mode else 'RÉEL'} · "
                   "le lead est sauvegardé à la fin de la conversation")
        render_prospect(slug, test_mode=bool(test_mode))


# ───────────────────────────────────────────────────────────────────────────────
# 9. INTERFACE ADMIN — clients, configuration, chatbots, preview, install, guides, leads, alertes, paramètres
# ───────────────────────────────────────────────────────────────────────────────

def render_admin():
    ss = st.session_state

    # ---------- connexion ----------
    if not ss.get("admin_auth", False):
        st.markdown(
            f"""
            <div style="max-width:420px; margin:6vh auto 0;">
              <div class="glass" style="text-align:center; padding:38px 30px;">
                <div style="font-size:46px; margin-bottom:6px;">🔐</div>
                <h2 style="margin:4px 0;">MaisonNova Engine</h2>
                <p class="muted" style="margin-bottom:20px;">Espace administrateur — réservé à votre agence</p>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        pwd = st.text_input("Mot de passe administrateur", type="password",
                            placeholder="••••••••", key="admin_pwd")
        if st.button("Se connecter", use_container_width=True, type="primary"):
            if pwd == ADMIN_PASSWORD:
                ss.admin_auth = True
                st.rerun()
            else:
                st.error("Mot de passe incorrect.")
        st.stop()

    ensure_default_agencies()
    st.markdown(
        f"""
        <div style="display:flex; align-items:center; justify-content:space-between; margin-top:6px;">
          <div style="display:flex; align-items:center; gap:14px;">
            <div class="agency-logo-fallback" style="width:46px;height:46px;font-size:22px;">🏛️</div>
            <div>
              <h1 style="font-size:26px; margin:0;">MaisonNova Engine</h1>
              <div class="muted">Console d'administration · qualification de leads</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if not GEMINI_READY:
        st.warning("⚠️ **Clé Gemini non configurée** — définissez `GEMINI_API_KEY` dans `.env` "
                   "pour activer l'IA. L'application fonctionne en mode dégradé (messages modèles).")

    # navigation programmatique entre onglets (boutons internes, ex. « Modifier »)
    goto = st.session_state.pop("goto_tab", None)
    if goto:
        st.session_state["admin_tabs"] = goto

    tab_clients, tab_wizard, tab_bots, tab_preview, tab_install, tab_guides, tab_leads, tab_alertes, tab_params = st.tabs(
        ["🏢 Clients", "🛠 Configuration", "🤖 Chatbots", "👁 Prévisualisation",
         "📦 Installation", "📘 Guides", "📊 Leads", "🔔 Alertes", "⚙️ Paramètres"],
        key="admin_tabs")

    # ============ Onglet CLIENTS ============
    with tab_clients:
        admin_views.render_clients_tab(APP_BASE_URL)

    # ============ Onglet CONFIGURATION (parcours 8 étapes) ============
    with tab_wizard:
        admin_views.render_wizard_tab(APP_BASE_URL)

    # ============ Onglet CHATBOTS ============
    with tab_bots:
        admin_views.render_chatbots_tab()

    # ============ Onglet PRÉVISUALISATION (mode TEST) ============
    with tab_preview:
        render_admin_preview()

    # ============ Onglet INSTALLATION (code, iframe, identifiant, clé) ============
    with tab_install:
        admin_views.render_install_tab()

    # ============ Onglet GUIDES (guide interactif + exports) ============
    with tab_guides:
        admin_views.render_guides_tab()

    # ============ Onglet LEADS ============
    with tab_leads:
        st.markdown("### Tableau de bord des prospects")
        with st.expander("🧪 Leads de TEST (prévisualisation)", expanded=False):
            test_rows = load_csv_rows(TEST_LEADS_FILE) if os.path.exists(TEST_LEADS_FILE) else []
            st.caption(f"{len(test_rows)} lead(s) de test — jamais mélangés aux leads réels.")
            if test_rows:
                st.dataframe(test_rows, use_container_width=True, hide_index=True, height=220)
                del_sel = st.selectbox(
                    "🗑️ Supprimer un lead de test",
                    [f"{i + 1}. {r.get('timestamp', '')} — {r.get('name') or 'anonyme'} — "
                     f"{r.get('agency_name') or r.get('agency_slug') or ''} (score {r.get('score') or 0})"
                     for i, r in enumerate(test_rows)], key="del_test_sel")
                c1, c2 = st.columns(2)
                if c1.button("Supprimer ce lead de test", use_container_width=True, key="del_test_one"):
                    idx = [f"{i + 1}. {r.get('timestamp', '')} — {r.get('name') or 'anonyme'} — "
                           f"{r.get('agency_name') or r.get('agency_slug') or ''} (score {r.get('score') or 0})"
                           for i, r in enumerate(test_rows)].index(del_sel)
                    delete_lead_row(TEST_LEADS_FILE, idx)
                    st.rerun()
                if c2.button("🧹 Tout effacer", use_container_width=True, key="del_test_all"):
                    clear_leads_file(TEST_LEADS_FILE)
                    st.rerun()
            else:
                st.caption("Aucun lead de test pour l'instant.")
        leads = load_leads()
        if not leads:
            st.info("Aucun lead capturé pour le moment. Partagez une URL de qualification "
                    "et les prospects apparaîtront ici en temps réel.")
        else:
            slugs_all = sorted({l.get("agency_slug", "") for l in leads})
            filt = st.selectbox("Filtrer par agence", ["Toutes"] + slugs_all)
            if filt != "Toutes":
                leads = [l for l in leads if l.get("agency_slug") == filt]

            total = len(leads)
            n_qual = sum(1 for l in leads if l.get("qualified") == "oui")
            avg = round(sum(int(l.get("score") or 0) for l in leads) / total, 1)
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Prospects capturés", total)
            m2.metric("Qualifiés", n_qual)
            m3.metric("Taux de qualification", f"{round(n_qual / total * 100)}%")
            m4.metric("Score moyen", f"{avg}/100")

            for l in leads:
                l["__score"] = int(l.get("score") or 0)
                l["__badge"] = "🟢 Qualifié" if l.get("qualified") == "oui" else "🟠 En cours"
            display = [{k: v for k, v in l.items() if k not in ("__score", "__badge", "score")} | {
                "Score": l["__score"], "Statut": l["__badge"]} for l in leads]
            st.dataframe(display, use_container_width=True, hide_index=True, height=360)

            import io
            buf = io.StringIO()
            wr = csv.DictWriter(buf, fieldnames=LEAD_COLUMNS)
            wr.writeheader()
            wr.writerows(load_leads())
            st.download_button("⬇️ Exporter tous les leads (CSV)", buf.getvalue(),
                               file_name="maisonnova-leads.csv", mime="text/csv")

            with st.expander("🗑️ Supprimer un lead", expanded=False):
                st.caption("La suppression retire le lead du fichier CSV local. "
                           "(La copie éventuelle dans Google Sheets n'est pas modifiée.)")
                del_sel2 = st.selectbox(
                    "Lead à supprimer",
                    [f"{i + 1}. {l.get('timestamp', '')} — {l.get('name') or 'anonyme'} — "
                     f"{l.get('agency_name') or l.get('agency_slug') or ''} (score {l.get('score') or 0})"
                     for i, l in enumerate(leads)], key="del_real_sel")
                confirm2 = st.checkbox("Je confirme la suppression de ce lead", key="del_real_confirm")
                if st.button("🗑️ Supprimer définitivement", type="secondary", disabled=not confirm2,
                             use_container_width=True, key="del_real_btn"):
                    idx2 = [f"{i + 1}. {l.get('timestamp', '')} — {l.get('name') or 'anonyme'} — "
                            f"{l.get('agency_name') or l.get('agency_slug') or ''} (score {l.get('score') or 0})"
                            for i, l in enumerate(leads)].index(del_sel2)
                    delete_lead_row(LEADS_FILE, idx2)
                    st.rerun()

    # ============ Onglet ALERTES ============
    with tab_alertes:
        st.markdown("### Notifications d'alerte")
        st.markdown("_Chaque nouveau lead **qualifié** déclenche un e-mail à l'agence "
                    "(simulé dans `alerts.log` — SMTP réel si `SMTP_*` est renseigné). Réponse < 24h._")
        if os.path.exists(ALERTS_FILE):
            with open(ALERTS_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
            st.code("".join(lines[-60:]), language="text")
        else:
            st.info("Aucune alerte émise pour l'instant.")

    # ============ Onglet PARAMÈTRES (Google Sheets + fichiers + sécurité) ============
    with tab_params:
        admin_views.render_settings_tab(
            sheets_load_config, sheets_save_config, test_sheets_connection,
            default_gdrive_key=GDRIVE_KEY,
            admin_password_set=ADMIN_PASSWORD not in ("admin123", "", "changez-moi"))

    if st.button("Déconnexion", key="logout"):
        ss.admin_auth = False
        st.rerun()


# ───────────────────────────────────────────────────────────────────────────────
# 10. ROUTAGE PRINCIPAL
# ───────────────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="MaisonNova Engine", page_icon="🏡",
                   layout="centered", initial_sidebar_state="collapsed")
inject_css()

# Agence de démonstration au premier lancement (disponible avant même le login admin)
ensure_default_agencies()

# Routage : /?agency=slug → interface prospect, sinon interface admin
agency_param = st.query_params.get("agency", None)
if agency_param:
    slug = str(agency_param)
    render_prospect(slug)
else:
    render_admin()
