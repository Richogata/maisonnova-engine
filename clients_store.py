# -*- coding: utf-8 -*-
"""Dossier clients — données client enrichies (clients.json), synchronisées avec
agencies.json pour rester 100 % compatible avec le moteur existant (routing
prospect, leads, alertes, iframe).

Chaque client possède :
  - un identifiant unique (agency_XXXXX) ;
  - un slug (URL de qualification) ;
  - un statut (DRAFT → … → INSTALLED / ERROR) ;
  - une fiche agence compatible moteur (clé "agency") ;
  - contact, activité, apparence, assistant, chatbot, installation, guide.
"""

import datetime
import json
import logging
import os
import re
import uuid

DEFAULT_CLIENTS_FILE = "clients.json"

STATUSES = ["DRAFT", "CONFIGURED", "PREVIEW_READY", "CODE_READY", "GUIDE_READY",
            "INSTALLATION_PENDING", "INSTALLED", "ERROR"]
STATUS_FLOW = ["DRAFT", "CONFIGURED", "PREVIEW_READY", "CODE_READY", "GUIDE_READY",
               "INSTALLATION_PENDING", "INSTALLED"]

ACCENTS = {"à": "a", "â": "a", "ä": "a", "á": "a", "ã": "a",
           "é": "e", "è": "e", "ê": "e", "ë": "e",
           "î": "i", "ï": "i", "í": "i", "ì": "i",
           "ô": "o", "ö": "o", "ó": "o", "ò": "o",
           "ù": "u", "û": "u", "ü": "u", "ú": "u",
           "ç": "c", "ñ": "n", "ÿ": "y", "œ": "oe",
           "'": "-", "’": "-", "`": "", ".": ""}


def slugify(text: str) -> str:
    """Slug URL simple, accents français gérés."""
    text = (text or "").lower().strip()
    for k, v in ACCENTS.items():
        text = text.replace(k, v)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "agence"


def _clients_file() -> str:
    return os.getenv("CLIENTS_FILE", DEFAULT_CLIENTS_FILE)


def _agencies_file() -> str:
    return os.getenv("AGENCY_FILE", "agencies.json")


def now_iso() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def new_agency_id() -> str:
    return "agency_" + uuid.uuid4().hex[:5].upper()


# ───────────────────────────────────────────────────────────────────────────────
# Chargement / sauvegarde
# ───────────────────────────────────────────────────────────────────────────────

def load_clients() -> dict:
    """Charge clients.json et RÉPARE automatiquement les anciens dossiers dont la
    clé du dict diffère de l'id du client (bug historique qui rendait la
    suppression impossible). La clé devient toujours l'id."""
    try:
        with open(_clients_file(), "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        repaired = False
        for cid in [c for c in data
                    if isinstance(data.get(c), dict) and (data[c].get("id") or c) != c]:
            cl = data.pop(cid)
            data[cl["id"]] = cl
            repaired = True
        if repaired:
            try:
                with open(_clients_file(), "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
        return data
    except Exception:
        return {}


def save_clients(clients: dict) -> None:
    """Écrit clients.json puis resynchronise agencies.json (compat moteur)."""
    try:
        with open(_clients_file(), "w", encoding="utf-8") as f:
            json.dump(clients, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        raise RuntimeError(f"Écriture {_clients_file()} impossible : {exc}") from exc
    _sync_agencies(clients)


def _load_legacy_agencies() -> dict:
    try:
        with open(_agencies_file(), "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _sync_agencies(clients: dict) -> None:
    """Régénère agencies.json depuis les clients (source de vérité). Les entrées
    legacy sont abandonnées : au premier lancement, la migration les a toutes
    converties en clients — ainsi, la SUPPRESSION d'un client retire bien son
    agence de agencies.json (le lien prospect cesse de fonctionner)."""
    agencies = {}
    for cid, client in clients.items():
        ag = client.get("agency") or {}
        agencies[client.get("slug") or cid] = ag
    try:
        with open(_agencies_file(), "w", encoding="utf-8") as f:
            json.dump(agencies, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        logging.warning("Resync agencies.json impossible : %s", exc)


def all_agencies() -> dict:
    """Dictionnaire slug → fiche agence (format moteur) avec les clés
    d'apparence/assistant ajoutées pour la prévisualisation personnalisée."""
    agencies = {}
    for cid, client in load_clients().items():
        ag = dict(client.get("agency") or {})
        app = client.get("appearance") or {}
        ast = client.get("assistant") or {}
        ag["primary_color"] = app.get("primary_color") or ""
        ag["secondary_color"] = app.get("secondary_color") or ""
        ag["assistant_name"] = ast.get("name") or ""
        agencies[client.get("slug") or cid] = ag
    return agencies


def client_agency(client: dict) -> dict:
    return dict(client.get("agency") or {})


# ───────────────────────────────────────────────────────────────────────────────
# Migration & démo
# ───────────────────────────────────────────────────────────────────────────────

def migrate_from_agencies() -> None:
    """Premier lancement : si clients.json est vide mais que agencies.json contient
    des agences, on les convertit en clients (statut CONFIGURED) — rien n'est perdu."""
    clients = load_clients()
    if clients:
        return
    legacy = _load_legacy_agencies()
    if not legacy:
        return
    migrated = False
    for slug, ag in legacy.items():
        if not isinstance(ag, dict) or not ag.get("name"):
            continue
        client = _blank_client(
            name=ag.get("name", ""), app_url=ag.get("app_url", ""),
            city=ag.get("city", ""), email=ag.get("email", ""),
            agency=ag, slug=slug, status="CONFIGURED",
            created_at=ag.get("created_at") or now_iso(),
        )
        clients[client["id"]] = client  # clé du dict == id du client
        migrated = True
    if migrated:
        save_clients(clients)


def _default_journeys() -> dict:
    """Parcours chatbot pré-activés à la création (import paresseux pour éviter
    l'import circulaire clients_store ↔ chatbot_config)."""
    try:
        import chatbot_config as cc
        return cc.default_journeys()
    except Exception:
        return {}


def _blank_client(name="", app_url="", city="", email="", agency=None,
                  slug=None, status="DRAFT", created_at=None) -> dict:
    return {
        "id": new_agency_id(),
        "slug": slug or slugify(name) or "agence",
        "status": status,
        "created_at": created_at or now_iso(),
        "updated_at": now_iso(),
        "agency": agency or {
            "name": name, "logo_url": "", "city": city, "email": email,
            "calendly_url": "", "threshold": 70, "description": "",
            "app_url": app_url, "created_at": created_at or now_iso(),
        },
        "contact": {"manager_name": "", "phone": "", "website": "",
                    "address": "", "country": ""},
        "activity": {"services": [], "zones": "", "property_types": [], "hours": ""},
        "slogan": "",
        "appearance": {"primary_color": "#C9A227", "secondary_color": "#9C7A14"},
        "assistant": {"name": "", "welcome_message": "", "tone": "chaleureux"},
        "chatbot": {
            "default_journey": "achat",
            "journeys": _default_journeys(),
        },
        "install": {"key": "", "generated_at": ""},
        "guide": {"generated_at": "", "filename": ""},
        "notes": "",
    }


def ensure_default_client(app_url: str) -> None:
    """Crée un client de démonstration au TOUT PREMIER lancement uniquement (URL
    testable tout de suite). Si tous les clients ont été supprimés volontairement
    (agencies.json existe déjà), on ne le recrée PAS."""
    migrate_from_agencies()
    clients = load_clients()
    if clients:
        return
    # le fichier agences a déjà été créé → ce n'est pas un premier lancement
    if os.path.exists(_agencies_file()):
        return
    slug = "maisonnova-lyon"
    client = _blank_client(
        name="MaisonNova Lyon", app_url=app_url, city="Lyon",
        email="contact@maisonnova.fr", slug=slug, status="CONFIGURED",
        agency={
            "name": "MaisonNova Lyon", "logo_url": "", "city": "Lyon",
            "email": "contact@maisonnova.fr",
            "calendly_url": "https://calendly.com/maisonnova/rendezvous-expert",
            "threshold": 70, "description": "Votre conseiller immobilier de confiance à Lyon",
            "app_url": app_url, "created_at": now_iso(),
        },
    )
    clients[client["id"]] = client  # clé du dict == id du client
    save_clients(clients)


# ───────────────────────────────────────────────────────────────────────────────
# Accès
# ───────────────────────────────────────────────────────────────────────────────

def get_client(ref: str) -> dict | None:
    """Retrouve un client par id, slug ou nom exact."""
    if not ref:
        return None
    ref = str(ref).strip().lower()
    for cid, client in load_clients().items():
        if cid.lower() == ref:
            return client
        if (client.get("slug") or "").lower() == ref:
            return client
        if (client.get("agency") or {}).get("name", "").strip().lower() == ref:
            return client
    return None


def get_client_id(ref: str) -> str | None:
    for cid, client in load_clients().items():
        if cid.lower() == str(ref).lower():
            return cid
        if (client.get("slug") or "").lower() == str(ref).lower():
            return cid
    return None


# ───────────────────────────────────────────────────────────────────────────────
# CRUD
# ───────────────────────────────────────────────────────────────────────────────

def create_client(name: str, app_url: str = "", manager: str = "",
                  email: str = "") -> dict:
    name = (name or "").strip()
    if not name:
        raise ValueError("Le nom de l'agence est obligatoire.")
    clients = load_clients()
    slug = slugify(name)
    if get_client(slug) and not get_client(slug).get("slug") == slug:
        slug = f"{slug}-{uuid.uuid4().hex[:4]}"
    client = _blank_client(name=name, app_url=app_url, email=email)
    client["slug"] = slug
    client["contact"]["manager_name"] = manager.strip()
    client["contact"]["website"] = ""
    client["agency"]["email"] = email.strip()
    clients[client["id"]] = client
    save_clients(clients)
    return client


def update_client(ref: str, **fields) -> dict | None:
    """Met à jour un client (fusion niveau 2) et retourne le client.
    Un changement de nom d'agence recalcule automatiquement le slug (comme
    l'ancien admin) et vérifie les collisions."""
    clients = load_clients()
    cid = get_client_id(ref)
    if cid is None or cid not in clients:
        return None
    client = clients[cid]

    if fields.get("agency") and isinstance(fields["agency"], dict):
        old_name = (client.get("agency") or {}).get("name") or ""
        new_name = (fields["agency"].get("name") or "").strip()
        if new_name and new_name != old_name:
            new_slug = slugify(new_name)
            for other_id, other in clients.items():
                if other_id != cid and (other.get("slug") or "") == new_slug:
                    new_slug = f"{new_slug}-{uuid.uuid4().hex[:4]}"
                    break
            fields["slug"] = new_slug

    for key, value in fields.items():
        if isinstance(value, dict) and isinstance(client.get(key), dict):
            client[key] = {**client.get(key), **value}
        elif key == "agency" and isinstance(value, dict):
            client["agency"] = {**client.get("agency", {}), **value}
        else:
            client[key] = value
    client["updated_at"] = now_iso()
    clients[cid] = client
    save_clients(clients)
    return client


def set_status(ref: str, status: str) -> None:
    if status not in STATUSES:
        raise ValueError(f"Statut inconnu : {status}")
    update_client(ref, status=status)


def status_index(status: str) -> int:
    try:
        return STATUS_FLOW.index(status)
    except ValueError:
        return -1


def next_status(status: str) -> str:
    """Avance d'un cran dans le parcours (ERROR exclu)."""
    idx = status_index(status)
    if 0 <= idx < len(STATUS_FLOW) - 1:
        return STATUS_FLOW[idx + 1]
    return status


def delete_client(ref: str) -> bool:
    """Supprime définitivement un client (dossier + agence resynchronisée + guide
    généré). Les leads déjà capturés sont conservés (traçabilité)."""
    clients = load_clients()
    cid = get_client_id(ref)
    if not cid or cid not in clients:
        return False
    client = clients.pop(cid)
    save_clients(clients)
    # retire le(s) guide(s) généré(s) pour ce client (best-effort)
    try:
        g = (client.get("guide") or {}).get("filename") or ""
        gdir = os.getenv("GUIDES_DIR", "guides")
        for cand in (g, os.path.join(gdir, f"{cid}_guide.html")):
            if cand and os.path.isfile(cand):
                os.remove(cand)
    except Exception:
        pass
    return True


# ───────────────────────────────────────────────────────────────────────────────
# Aide au dashboard
# ───────────────────────────────────────────────────────────────────────────────

def status_steps(client: dict) -> list[tuple[str, bool]]:
    """[(label, fait ?)] — Configuration, Chatbot, Code, Guide, Installation."""
    ag = client.get("agency") or {}
    chatbot = client.get("chatbot") or {}
    install = client.get("install") or {}
    guide = client.get("guide") or {}
    conf_ok = bool(ag.get("name") and ag.get("city"))
    chatbot_ok = bool(chatbot.get("journeys")) or bool(ag.get("threshold"))
    code_ok = bool(install.get("key"))
    guide_ok = bool(guide.get("filename") or guide.get("generated_at"))
    status = client.get("status") or "DRAFT"
    install_ok = status == "INSTALLED"
    return [("Configuration", conf_ok), ("Chatbot", chatbot_ok), ("Code", code_ok),
            ("Guide", guide_ok), ("Installation", install_ok)]
