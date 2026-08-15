# -*- coding: utf-8 -*-
"""Configuration flexible du chatbot — parcours activables (Achat / Vente /
Location / Investissement), questions personnalisables (texte + ordre), points et
seuil par agence.

Valeurs par défaut == moteur existant (les 5 questions + tables de points
actuelles) : tout client sans configuration explicite garde exactement le
comportement actuel.
"""

import clients_store

JOURNEY_KEYS = ["achat", "vente", "location", "investissement"]
JOURNEY_LABELS = {"achat": "Achat", "vente": "Vente",
                  "location": "Location", "investissement": "Investissement"}

# (clé, label, template) — l'ordre ici est l'ordre par défaut
DEFAULT_QUESTIONS = [
    ("project_type", "Projet",
     "Quel type de projet envisagez-vous ? (maison individuelle, appartement, terrain, investissement locatif…)"),
    ("budget", "Budget",
     "Quel budget envisagez-vous pour ce projet ?"),
    ("city", "Ville",
     "Dans quelle ville ou quel secteur recherchez-vous ?"),
    ("financing", "Financement",
     "Comment comptez-vous financer ce projet ? (prêt pré-accordé, apport, financement à prévoir…)"),
    ("timeline", "Délai",
     "Quel est votre délai idéal pour concrétiser ce projet ?"),
]

# Tables de points par catégorie (max 100 au total)
DEFAULT_POINTS = {
    "project_type": {"maison": 20, "appartement": 18, "investissement": 16,
                     "terrain": 12, "autre": 10},
    "budget": {"600k+": 25, "400-600k": 22, "250-400k": 16, "150-250k": 10, "<150k": 5},
    "city": {"same": 15, "other": 10},
    "financing": {"preapproved": 25, "cash": 20, "pending": 12, "none": 5},
    "timeline": {"<6": 15, "6-12": 12, "12-24": 8, "flexible": 5},
}

MAX_SCORE = 100


def default_questions_dict() -> list[dict]:
    return [{"key": k, "label": lbl, "template": tmpl} for k, lbl, tmpl in DEFAULT_QUESTIONS]


def default_journeys() -> dict:
    """Parcours par défaut : TOUS les parcours activés avec les 5 questions du
    moteur actuel. Le chatbot d'un client est donc opérationnel immédiatement,
    sans aucune étape d'activation supplémentaire."""
    journeys = {}
    for jk in JOURNEY_KEYS:
        journeys[jk] = {
            "enabled": True,
            "questions": default_questions_dict(),
            "points": None,        # None → tables par défaut
            "threshold": None,     # None → seuil de l'agence
            "message": "",         # message d'accueil spécifique (optionnel)
        }
    return journeys


# ───────────────────────────────────────────────────────────────────────────────

def get_client(ref) -> dict | None:
    return clients_store.get_client(ref)


def client_chatbot(client: dict | None) -> dict:
    if not client:
        return {"default_journey": "achat", "journeys": {}}
    cb = client.get("chatbot") or {}
    journeys = cb.get("journeys") or {}
    if not journeys:
        return {"default_journey": cb.get("default_journey") or "achat", "journeys": {}}
    return cb


def _journey(client, journey=None) -> dict:
    cb = client_chatbot(client)
    if not client:
        return {"enabled": True, "questions": default_questions_dict(),
                "points": None, "threshold": None, "message": ""}
    jk = journey or cb.get("default_journey") or "achat"
    journeys = cb.get("journeys") or {}
    return journeys.get(jk) or {"enabled": True, "questions": default_questions_dict(),
                                "points": None, "threshold": None, "message": ""}


def _default_for(key: str) -> tuple[str, str]:
    for k, lbl, t in DEFAULT_QUESTIONS:
        if k == key:
            return lbl, t
    return key or "", ""


def questions_for(client: dict | None, journey: str | None = None) -> list[tuple]:
    """Retourne [(key, label, template)] pour le parcours donné (défaut : 5 questions).
    Un libellé ou texte vide retombe sur la valeur par défaut du moteur."""
    j = _journey(client, journey)
    qs = j.get("questions") or []
    if not qs:
        qs = default_questions_dict()
    out = []
    for q in qs:
        if isinstance(q, dict):
            key = q.get("key") or "autre"
            d_lbl, d_tmpl = _default_for(key)
            out.append((key, (q.get("label") or "").strip() or d_lbl or key,
                        (q.get("template") or "").strip() or d_tmpl))
        elif isinstance(q, (tuple, list)) and len(q) >= 3:
            out.append((q[0], q[1], q[2]))
    return out or [(k, lbl, t) for k, lbl, t in DEFAULT_QUESTIONS]


def points_for(client: dict | None, journey: str | None = None) -> dict:
    """Tables de points du parcours (fusion sur les défauts, jamais de trous)."""
    j = _journey(client, journey)
    custom = j.get("points") or {}
    merged = {}
    for cat, table in DEFAULT_POINTS.items():
        merged[cat] = {**table, **(custom.get(cat) or {})}
    return merged


def threshold_for(client: dict | None, agency: dict | None = None) -> int:
    j = _journey(client)
    thr = j.get("threshold")
    if thr:
        try:
            return int(thr)
        except (TypeError, ValueError):
            pass
    ag = client.get("agency") if client else None
    if ag and ag.get("threshold") is not None:
        return int(ag.get("threshold") or 70)
    if agency and agency.get("threshold") is not None:
        return int(agency.get("threshold") or 70)
    return 70


def assistant_for(client: dict | None) -> dict:
    if not client:
        return {"name": "", "welcome_message": "", "tone": "chaleureux"}
    ast = client.get("assistant") or {}
    return {"name": ast.get("name") or "", "welcome_message": ast.get("welcome_message") or "",
            "tone": ast.get("tone") or "chaleureux"}


def appearance_for(client: dict | None) -> dict:
    if not client:
        return {"primary_color": "", "secondary_color": ""}
    app = client.get("appearance") or {}
    return {"primary_color": app.get("primary_color") or "",
            "secondary_color": app.get("secondary_color") or ""}


def _effective_journey(client: dict | None) -> str:
    """Parcours effectif du chat : le parcours principal s'il est activé, sinon le
    premier parcours activé, sinon « achat » avec la configuration par défaut —
    le chatbot reste TOUJOURS fonctionnel, même si tous les parcours ont été
    désactivés par erreur."""
    cb = client_chatbot(client)
    default_journey = cb.get("default_journey") or "achat"
    journeys = cb.get("journeys") or {}
    if journeys.get(default_journey, {}).get("enabled"):
        return default_journey
    for jk in JOURNEY_KEYS:
        if journeys.get(jk, {}).get("enabled"):
            return jk
    return default_journey or "achat"


def get_config_for_agency(agency: dict | None, slug: str | None = None) -> dict:
    """Config complète utilisée par l'interface prospect (et la prévisualisation) :
    questions, points, seuil, couleurs, assistant. Repli complet si client introuvable."""
    client = None
    if slug:
        client = clients_store.get_client(slug)
    if client is None and agency:
        client = clients_store.get_client(agency.get("name", ""))
    journey = _effective_journey(client)
    return {
        "questions": questions_for(client, journey),
        "points": points_for(client, journey),
        "threshold": threshold_for(client, agency),
        "colors": appearance_for(client),
        "assistant": assistant_for(client),
        "journey": journey,
    }


# ───────────────────────────────────────────────────────────────────────────────
# Scoring (compatible score_profile existant)
# ───────────────────────────────────────────────────────────────────────────────

def apply_points(profile: dict, agency_city: str, points: dict | None = None) -> tuple[int, dict]:
    """Scoring déterministe sur 100. `points` optionnel : si absent, tables
    actuelles (comportement identique à score_profile original)."""
    pts, parts = 0, {}
    if not points:
        points = DEFAULT_POINTS

    pts += parts.setdefault("Projet", (points.get("project_type") or {}).get(profile.get("project_type"), 0))
    pts += parts.setdefault("Budget", (points.get("budget") or {}).get(profile.get("budget"), 0))

    city = (profile.get("city") or "").strip().lower()
    ag_city = (agency_city or "").strip().lower()
    city_tbl = points.get("city") or {}
    city_pts = (city_tbl.get("same", 15) if (city and city == ag_city)
                else city_tbl.get("other", 10) if city else 0)
    pts += parts.setdefault("Ville", city_pts)

    pts += parts.setdefault("Financement", (points.get("financing") or {}).get(profile.get("financing"), 0))
    pts += parts.setdefault("Délai", (points.get("timeline") or {}).get(profile.get("timeline"), 0))
    return min(MAX_SCORE, pts), parts
