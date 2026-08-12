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
GEMINI_MODELS       = [m for m in _cfg("GEMINI_MODEL", "gemini-2.0-flash").split(",") if m]
GEMINI_MODELS      += ["gemini-2.5-flash", "gemini-1.5-flash"]          # replis auto

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

APP_BASE_URL        = _cfg("APP_BASE_URL", "http://localhost:8501")

GOLD      = "#C9A227"
GOLD_DARK = "#9C7A14"
INK       = "#1C1C1E"
GRAY_BG   = "#F2F2F7"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ───────────────────────────────────────────────────────────────────────────────
# 2. OUTILS — MODÈLES & GEMINI
# ───────────────────────────────────────────────────────────────────────────────

def _init_genai():
    """Initialise le SDK Gemini si la clé est présente. Retourne True si OK."""
    if not GEMINI_API_KEY:
        return False
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        return True
    except Exception as exc:
        logging.warning("Gemini indisponible : %s", exc)
        return False

GEMINI_READY = _init_genai()


def ai_complete(system_prompt: str, user_text: str, temperature: float = 0.6,
                json_mode: bool = False, max_tokens: int = 700) -> str | None:
    """Appelle Gemini (legacy SDK) avec repli automatique de modèle.
    Retourne le texte brut, ou None en cas d'échec total."""
    if not GEMINI_READY:
        return None
    import google.generativeai as genai
    for name in GEMINI_MODELS:
        try:
            genai.GenerativeModel(model_name=name)
            cfg = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                **( {"response_mime_type": "application/json"} if json_mode else {} ),
            )
            model = genai.GenerativeModel(model_name=name, system_instruction=system_prompt)
            resp = model.generate_content(user_text, generation_config=cfg,
                                          request_options={"timeout": 60})
            return resp.text
        except Exception as exc:
            logging.debug("Modèle %s en échec : %s", name, exc)
            continue
    return None


def ai_json(system_prompt: str, user_text: str, max_tokens: int = 800) -> dict | None:
    """Version 'mode JSON' avec nettoyage robuste des réponses."""
    raw = ai_complete(system_prompt, user_text, temperature=0.2, json_mode=True, max_tokens=max_tokens)
    if not raw:
        return None
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        return json.loads(raw[start:end + 1])
    except Exception:
        return None

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
    try:
        with open(AGENCY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_agencies(data: dict):
    with open(AGENCY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def ensure_default_agencies():
    """Crée une agence de démonstration au premier lancement (URL testable tout de suite)."""
    agencies = load_agencies()
    if not agencies:
        slug = "maisonnova-lyon"
        agencies[slug] = {
            "name": "MaisonNova Lyon",
            "logo_url": "",
            "city": "Lyon",
            "email": "contact@maisonnova.fr",
            "calendly_url": "https://calendly.com/maisonnova/rendezvous-expert",
            "threshold": 70,
            "description": "Votre conseiller immobilier de confiance à Lyon",
            "app_url": APP_BASE_URL,
            "created_at": datetime.datetime.now().isoformat(timespec="seconds"),
        }
        save_agencies(agencies)


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


def save_lead(agency: dict, slug: str, profile: dict, score: int, qualified: bool,
              summary: str, session_id: str) -> None:
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
        "source": "web",
    }
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

SYSTEM_QUESTION = """Tu es {assistant_name}, conseiller immobilier premium pour l'agence « {agency_name} » à {city}.
Ton ton : chaleureux, professionnel, concis (2 à 3 phrases max), toujours en français, sans markdown ni emoji excessifs.
Contexte du prospect : {context}
Ton rôle est de poser UNE question à la fois pour qualifier le projet.
QUESTION À POSER MAINTENANT ({n}/5, catégorie « {label} ») :
{template}
Adapte légèrement la formulation au profil déjà connu du prospect (par ex. cite son prénom ou son projet),
mais ne pose JAMAIS une autre question et ne réponds pas à sa place."""

SYSTEM_SUMMARY = """Tu es un expert immobilier. Rédige une synthèse de qualification pour un prospect.
Réponds UNIQUEMENT en JSON valide :
{
  "summary": "résumé de 2-3 phrases du projet (type, budget, ville, financement, délai, niveau de maturité)",
  "message": "message de clôture personnalisé (2 phrases max, ton premium, français), qui :
     - si qualifié : félicite le prospect et l'invite à réserver son rendez-vous expert ;
     - sinon : le remercie chaleureusement et annonce qu'un conseiller le recontactera."
}"""


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


def score_profile(profile: dict, agency_city: str) -> tuple[int, dict]:
    """Scoring déterministe : chaque réponse ajoute des points (max 100)."""
    pts, parts = 0, {}
    pts += parts.setdefault("Projet", PROJECT_POINTS.get(profile.get("project_type"), 0))
    pts += parts.setdefault("Budget", BUDGET_POINTS.get(profile.get("budget"), 0))

    city = (profile.get("city") or "").strip().lower()
    ag_city = (agency_city or "").strip().lower()
    city_pts = 15 if (city and city == ag_city) else (10 if city else 0)
    pts += parts.setdefault("Ville", city_pts)

    pts += parts.setdefault("Financement", FINANCE_POINTS.get(profile.get("financing"), 0))
    pts += parts.setdefault("Délai", TIMELINE_POINTS.get(profile.get("timeline"), 0))
    return min(MAX_SCORE, pts), parts


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


def generate_welcome(agency: dict) -> str:
    """Message d'accueil de l'assistant, au nom de l'agence."""
    sys_p = (f"Tu es {agency.get('name')} assistant virtuel, conseiller immobilier premium à "
             f"{agency.get('city','')}. Ton ton : chaleureux, élégant, très concis (2-3 phrases). "
             f"En français, sans markdown, sans emoji excessif. Accueille le visiteur au nom de "
             f"l'agence, présente-toi et demande-lui son prénom. Message : « {agency.get('description','')} »")
    msg = ai_complete(sys_p, "Présente-toi et demande le prénom du prospect.", temperature=0.8, max_tokens=250)
    if msg:
        return msg.strip()
    return (f"Bonjour et bienvenue chez {agency.get('name')} 👋 "
            f"Je suis votre conseiller virtuel, ravi de vous accompagner pour votre projet "
            f"immobilier à {agency.get('city', 'votre région')}. "
            f"Puis-je connaître votre prénom ?")


def generate_question(agency: dict, profile: dict, index: int) -> str:
    key, template = QUESTIONS[index]
    sys_p = SYSTEM_QUESTION.format(
        assistant_name=agency.get("name", "l'agence"),
        agency_name=agency.get("name", ""),
        city=agency.get("city", ""),
        context=build_context(profile),
        n=index + 1, label=key, template=template,
    )
    msg = ai_complete(sys_p, "Pose la question.", temperature=0.7, max_tokens=200)
    if msg:
        return msg.strip()
    return f"{template}"


def generate_closing(agency: dict, profile: dict, score: int, qualified: bool) -> tuple[str, str]:
    """Retourne (summary, message_de_cloture)."""
    ctx = build_context(profile) + f" | score={score}/100 | qualifié={'oui' if qualified else 'non'}"
    data = ai_json(SYSTEM_SUMMARY, ctx, max_tokens=500)
    if data and isinstance(data, dict):
        return data.get("summary", ""), data.get("message", "")
    if qualified:
        return (f"Projet de type {profile.get('project_type') or 'immobilier'}, budget "
                f"{profile.get('budget') or 'à définir'}, secteur {profile.get('city') or 'à préciser'} — "
                f"profil mature et qualifié.", f"Excellent, {profile.get('name') or ''}! Votre projet "
                f"est très prometteur. Réservez dès maintenant votre rendez-vous expert.")
    return (f"Profil à maturité variable (budget {profile.get('budget') or 'à préciser'}, "
            f"financement {profile.get('financing') or 'à confirmer'}).",
            f"Merci {profile.get('name') or ''}, un conseiller de {agency.get('name')} "
            f"reviendra vers vous très rapidement.")


# ───────────────────────────────────────────────────────────────────────────────
# 7. DESIGN SYSTEM — CSS premium (Inter, glassmorphism, Apple-like, gold CTA)
# ───────────────────────────────────────────────────────────────────────────────

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

/* masquer chrome Streamlit (menu, footer, deploy) */
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"], .stDeployButton { visibility: hidden; height: 0; }

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
[data-testid="stChatMessage"] { max-width: 620px; margin-left:auto; margin-right:auto;
  animation: msgIn .28s cubic-bezier(.2,.8,.2,1) both; }
@keyframes msgIn { from { opacity:0; transform: translateY(6px); } to { opacity:1; transform:none; } }
[data-testid="stChatMessageAvatarUser"], [data-testid="stChatMessageAvatarAssistant"] {
  font-size: 17px; background: transparent; border-radius: 50%;
}
[data-testid="stChatMessage"] [data-testid="stChatMessageContent"] p {
  font-size: 15px; line-height: 1.6; color: var(--ink); margin: 0;
}
[data-testid="stChatMessageContent"] {
  padding: 13px 18px; border-radius: 20px;
  background: #FFFFFF; border: 1px solid rgba(0,0,0,.06);
  box-shadow: 0 2px 12px rgba(31,38,66,.06);
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


def render_question_progress(done: int):
    """Pastille de progression des 5 questions (dot doré = question validée)."""
    labels = ["Projet", "Budget", "Ville", "Financement", "Délai"]
    dots = "".join(
        f'<span class="q-dot {"done" if i < done else ""}" title="{labels[i]}"></span>'
        for i in range(len(QUESTIONS)))
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

def render_prospect(slug: str):
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
        # message d'accueil généré par l'IA au nom de l'agence
        ss.messages.append({"role": "assistant", "content": generate_welcome(agency)})

    render_agency_header(agency)

    if ss.prospect_stage != "welcome":
        q_done = len(QUESTIONS) if ss.prospect_stage == "closing" else ss.q_index
        render_question_progress(q_done)
        score_bar(ss.score, agency.get("threshold", 70))

    # ---- historique du chat ----------------------------------------------------
    for msg in ss.messages:
        with st.chat_message(msg["role"], avatar="🤖" if msg["role"] == "assistant" else "👤"):
            st.markdown(msg["content"])

    # indicateur "l'assistant écrit…" (3 points animés)
    if ss.thinking:
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown('<div class="typing"><span></span><span></span><span></span></div>',
                        unsafe_allow_html=True)

    # ---- logique : réponse prospect en attente ? (pendant l'indicateur "écrit…") --
    if ss.thinking:
        # 1) extraction du profil (IA + repli règles) et mise à jour cumulée
        extracted = extract_profile(ss.messages, agency.get("city", ""))
        for key, val in extracted.items():
            if val and not ss.answers.get(key):
                ss.answers[key] = val
        ss.profile = {**ss.profile, **ss.answers}
        ss.score, _ = score_profile(ss.profile, agency.get("city", ""))

        if ss.prospect_stage == "welcome":
            # on connaît le prénom → on démarre le questionnaire
            ss.prospect_stage = "chat"
            ss.messages.append({"role": "assistant",
                                "content": generate_question(agency, ss.profile, 0)})
        elif ss.q_index < len(QUESTIONS) - 1:
            ss.q_index += 1
            ss.messages.append({"role": "assistant",
                                "content": generate_question(agency, ss.profile, ss.q_index)})
        else:
            # ---- CLOSING : score final, synthèse IA, sauvegarde, notification ----
            try:
                qualified = ss.score >= agency.get("threshold", 70)
                summary, closing = generate_closing(agency, ss.profile, ss.score, qualified)
                ss.summary, ss.qualified, ss.final_msg = summary, qualified, closing
                save_lead(agency, slug, ss.profile, ss.score, qualified, summary, ss.session_id)
                notify_agency(agency, ss.profile.get("name", ""), ss.score, qualified)
                st.toast("📩 Profil enregistré — l'agence a été notifiée" if qualified
                         else "📩 Profil enregistré")
            except Exception as exc:
                # la clôture doit TOUJOURS aboutir (pas de doublon, pas d'écran d'erreur)
                logging.error("Clôture impossible : %s", exc)
                summary = ss.summary or "Profil qualifié."
                closing = ss.final_msg or ("Merci, un conseiller reviendra vers vous.")
                ss.qualified = ss.score >= agency.get("threshold", 70)
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
        threshold = agency.get("threshold", 70)
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        parts = score_profile(ss.profile, agency.get("city", ""))[1]
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
# 9. INTERFACE ADMIN — configuration, tableau de bord, alertes, embed
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

    tab_agences, tab_sheets, tab_leads, tab_alertes, tab_embed = st.tabs(
        ["🏢 Agences", "📗 Google Sheets", "📊 Leads", "🔔 Alertes", "🔌 Embed"])

    agencies = load_agencies()
    slugs = list(agencies.keys())

    # ============ Onglet AGENCES ============
    with tab_agences:
        st.markdown("### Configuration de l'agence")
        if slugs:
            sel = st.selectbox("Agence à configurer", slugs,
                               format_func=lambda s: f"{agencies[s].get('name', s)} — {s}",
                               key="adm_sel")
            a = agencies[sel]
        else:
            sel, a = None, {}

        with st.form("agency_form", clear_on_submit=False):
            # Clés liées au slug : évite que Streamlit garde les valeurs d'une autre agence
            c1, c2 = st.columns(2)
            name = c1.text_input("Nom de l'agence", a.get("name", ""), key=f"f_name_{sel}")
            city = c2.text_input("Ville", a.get("city", ""), key=f"f_city_{sel}")
            c3, c4 = st.columns(2)
            logo = c3.text_input("URL du logo", a.get("logo_url", ""),
                                 placeholder="https://…/logo.png", key=f"f_logo_{sel}")
            email = c4.text_input("Email de l'agence (alertes)", a.get("email", ""),
                                  key=f"f_email_{sel}")
            calendly = st.text_input("Lien Calendly", a.get("calendly_url", ""),
                                     placeholder="https://calendly.com/…", key=f"f_cal_{sel}")
            desc = st.text_input("Description / slogan", a.get("description", ""),
                                 key=f"f_desc_{sel}")
            threshold = st.slider("Seuil de qualification (score minimal)", 0, 100,
                                  int(a.get("threshold", 70)), step=5, key=f"f_thr_{sel}")
            app_url = st.text_input("URL publique de l'application", a.get("app_url", APP_BASE_URL),
                                    help="Sert à générer le lien de qualification et le code iframe.",
                                    key=f"f_url_{sel}")
            submitted = st.form_submit_button("💾 Enregistrer l'agence",
                                              use_container_width=True, type="primary")

        if submitted and name.strip():
            slug = slugify(name)
            agencies[slug] = {
                "name": name.strip(), "logo_url": logo.strip(), "city": city.strip(),
                "email": email.strip(), "calendly_url": calendly.strip(),
                "threshold": int(threshold), "description": desc.strip(),
                "app_url": (app_url.strip() or APP_BASE_URL),
                "created_at": a.get("created_at") or datetime.datetime.now().isoformat(timespec="seconds"),
            }
            if sel and sel != slug:
                agencies.pop(sel, None)
            save_agencies(agencies)
            st.success(f"✅ Agence « {name} » enregistrée.")
            st.rerun()

        if slugs:
            base = (a.get("app_url") or APP_BASE_URL).rstrip("/")
            qualify_url = f"{base}/?agency={sel}"
            st.divider()
            st.markdown("### 🔗 URL de qualification générée")
            st.text_input("Lien à intégrer sur votre site / à partager",
                          value=qualify_url, key="adm_qualify_url", disabled=True)
            st.markdown("_Ouvrez ce lien dans un **nouvel onglet privé** pour vivre "
                        "l'expérience prospect (score, bouton doré, sauvegarde du lead)._")

    # ============ Onglet GOOGLE SHEETS ============
    with tab_sheets:
        st.markdown("### 📗 Stockage Google Sheets")
        st.markdown(
            "_Les leads sont **toujours** sauvegardés en local (`leads.csv`) et, si vous configurez "
            "Google Sheets ci-dessous, **aussi** poussés en temps réel dans votre spreadsheet "
            "(feuille `Leads` créée automatiquement)._")
        s_cfg = sheets_load_config()
        with st.form("sheets_form", clear_on_submit=False):
            srv_json = st.text_area(
                "Clé JSON du service account (collez le contenu complet du fichier .json)",
                value=s_cfg.get("service_account", ""), height=170,
                help="Google Cloud Console → IAM & Admin → Comptes de service → Créer clé → JSON. "
                     "Ou chemin local du fichier dans GOOGLE_SHEETS_JSON.")
            sh_key = st.text_input(
                "ID ou URL du spreadsheet Google Sheets",
                value=s_cfg.get("spreadsheet", GDRIVE_KEY or ""),
                placeholder="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
                help="Partagez le spreadsheet avec l'e-mail du service account (rôle Éditeur).")
            c_s1, c_s2 = st.columns(2)
            save_sheets = c_s1.form_submit_button("💾 Enregistrer", use_container_width=True)
            test_sheets = c_s2.form_submit_button("🔌 Tester la connexion", use_container_width=True)
        if save_sheets or test_sheets:
            # on sauvegarde d'abord (le test utilise alors les valeurs du formulaire)
            sheets_save_config({"service_account": srv_json.strip(),
                                "spreadsheet": sh_key.strip()})
        if save_sheets:
            st.success("✅ Configuration Google Sheets enregistrée.")
        if test_sheets:
            ok, msg = test_sheets_connection(service=srv_json.strip(), sheet_ref=sh_key.strip())
            (st.success if ok else st.error)(msg)

    # ============ Onglet LEADS ============
    with tab_leads:
        st.markdown("### Tableau de bord des prospects")
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

    # ============ Onglet EMBED ============
    with tab_embed:
        st.markdown("### Intégration iframe (8.5 × 11)")
        st.markdown(
            "_Collez ce snippet sur votre site externe. Le widget est optimisé pour le format "
            "portrait lettre (8.5 × 11) : fond blanc, centrage, aucune barre Streamlit._")
        if slugs:
            sel_e = st.selectbox("Agence à embarquer", slugs, key="adm_embed_sel")
            a_e = agencies[sel_e]
            base = (a_e.get("app_url") or APP_BASE_URL).rstrip("/")
            url = f"{base}/?agency={sel_e}&embed=1"
            snippet = (
                f'<iframe src="{html.escape(url)}" width="460" height="620" '
                f'style="border:none; border-radius:16px; box-shadow:0 12px 40px rgba(31,38,66,.15);" '
                f'title="Qualification {html.escape(a_e.get("name",""))}" loading="lazy"></iframe>'
            )
            st.code(snippet, language="html")
            st.link_button("🌐 Prévisualiser le widget", url)
        else:
            st.info("Créez d'abord une agence dans l'onglet « Agences ».")

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
