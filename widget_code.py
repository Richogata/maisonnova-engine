# -*- coding: utf-8 -*-
"""Génération du kit d'installation pour chaque client :
  A. URL publique            B. iframe
  C. code d'installation     D. identifiant agence (agency_id)
  E. clé d'installation      + bloc webmaster + détection de plateforme.

Aucun secret (mot de passe, clé API…) n'est exposé : le kit ne contient que des
informations destinées au client final.
"""

import re
import uuid

import clients_store


def new_install_key() -> str:
    return "MN-" + uuid.uuid4().hex[:4].upper() + "-" + uuid.uuid4().hex[:4].upper()


def ensure_install(client: dict) -> dict:
    """Garantit une clé d'installation pour le client (créée une seule fois)."""
    install = dict(client.get("install") or {})
    if not install.get("key"):
        install["key"] = new_install_key()
        install["generated_at"] = clients_store.now_iso()
        clients_store.update_client(client.get("id") or client.get("slug"), install=install)
        client["install"] = install
    return install


def _app_url(client: dict) -> str:
    ag = client.get("agency") or {}
    return (ag.get("app_url") or "").rstrip("/") or "http://localhost:8501"


def public_url(client: dict, embed: bool = False) -> str:
    slug = client.get("slug") or "agence"
    return f"{_app_url(client)}/?agency={slug}" + ("&embed=1" if embed else "")


def install_url(client: dict) -> str:
    """URL utilisée par le widget (iframe / script)."""
    return public_url(client, embed=True)


def iframe_snippet(client: dict) -> str:
    name = (client.get("agency") or {}).get("name") or "Assistant"
    url = install_url(client)
    return (f'<iframe src="{url}" width="460" height="620" '
            f'style="border:none; border-radius:16px;" '
            f'title="Qualification {name}" loading="lazy"></iframe>')


def script_snippet(client: dict) -> str:
    """Code d'installation autonome (div + script) — fonctionne partout où on
    peut coller du HTML (WordPress bloc HTML, Wix, Webflow, site personnalisé)."""
    key = (client.get("install") or {}).get("key") or ""
    url = install_url(client)
    key_param = f"&key={key}" if key else ""
    return (
        '<!-- MaisonNova AI — assistant de qualification -->\n'
        '<div id="maisonnova-assistant"></div>\n'
        '<script>\n'
        '(function() {\n'
        '  var d = document, w = 460, h = 620;\n'
        '  var host = window.location.hostname || "";\n'
        '  var src = "' + url + key_param + '&site=" + encodeURIComponent(host);\n'
        '  var f = d.createElement("iframe");\n'
        '  f.src = src; f.width = w; f.height = h; f.style.border = "none";\n'
        '  f.style.borderRadius = "16px"; f.style.maxWidth = "100%";\n'
        '  f.title = "MaisonNova AI"; f.loading = "lazy";\n'
        '  var box = d.getElementById("maisonnova-assistant");\n'
        '  if (box) { box.appendChild(f); } else { d.body.appendChild(f); }\n'
        '})();\n'
        '</script>'
    )


def full_install_code(client: dict) -> str:
    """Code d'installation complet à copier-coller (le seul élément nécessaire)."""
    return (
        "<!-- ============================================================\n"
        "  MaisonNova AI — code d'installation\n"
        "  Agence : {name} · Identifiant : {agency_id}\n"
        "  Collez ce bloc tel quel, de préférence juste avant la fin de la\n"
        "  page (avant </body>) ou dans un bloc HTML/Embed.\n"
        "============================================================= -->\n"
        "{snippet}"
    ).format(
        name=(client.get("agency") or {}).get("name") or "",
        agency_id=client.get("id") or "",
        snippet=script_snippet(client),
    )


def webmaster_block(client: dict) -> str:
    """Bloc technique destiné à la personne qui gère le site du client."""
    ag = client.get("agency") or {}
    ct = client.get("contact") or {}
    key = (client.get("install") or {}).get("key") or ""
    site = ct.get("website") or ag.get("app_url") or ""
    return (
        "INSTRUCTIONS TECHNIQUES — INSTALLATION DE L'ASSISTANT MAISONNOVA AI\n"
        + "-" * 68 + "\n"
        f"Agence          : {ag.get('name') or ''}\n"
        f"Site            : {site}\n"
        f"Identifiant     : {client.get('id') or ''}\n"
        f"Clé d'installation : {key}\n"
        "Emplacement recommandé : juste avant la fermeture </body> (ou dans un\n"
        "bloc HTML / Embed / widget de la page souhaitée).\n\n"
        "CODE À INTÉGRER (tel quel) :\n"
        + "-" * 68 + "\n"
        + full_install_code(client) + "\n"
        + "-" * 68 + "\n"
        "TEST ATTENDU : le widget (chat de qualification) doit apparaître et\n"
        "répondre. La page se charge sans erreur, le widget reste responsive.\n"
    )


def kit_summary(client: dict) -> dict:
    """Résumé non sensible du client (inclus dans le dossier exporté)."""
    ag = client.get("agency") or {}
    ct = client.get("contact") or {}
    ac = client.get("activity") or {}
    return {
        "id": client.get("id"),
        "slug": client.get("slug"),
        "status": client.get("status"),
        "agence": ag.get("name"),
        "ville": ag.get("city"),
        "email": ag.get("email"),
        "site": ct.get("website"),
        "responsable": ct.get("manager_name"),
        "telephone": ct.get("phone"),
        "adresse": ct.get("address"),
        "pays": ct.get("country"),
        "services": ac.get("services") or [],
        "zones": ac.get("zones"),
        "types_de_biens": ac.get("property_types") or [],
        "horaires": ac.get("hours"),
        "calendly": ag.get("calendly_url"),
        "seuil": ag.get("threshold"),
        "assistant": (client.get("assistant") or {}).get("name"),
        "couleur_principale": (client.get("appearance") or {}).get("primary_color"),
    }


# ───────────────────────────────────────────────────────────────────────────────
# Détection de plateforme (guide "Je ne sais pas")
# ───────────────────────────────────────────────────────────────────────────────

def detect_platform(url: str) -> str | None:
    """Heuristique simple sur l'URL. Retourne 'wordpress', 'wix', 'webflow'
    ou None si indétectable. (Le guide fait la même détection côté client.)"""
    if not url:
        return None
    u = str(url).strip().lower()
    if not u.startswith(("http://", "https://", "www.")):
        u = "https://" + u
    if re.search(r"(wixsite\.com|\.wix\.com|editor\.wix|wix\.com)", u):
        return "wix"
    if re.search(r"(webflow\.io|webflow\.com|\.webflow)", u):
        return "webflow"
    if re.search(r"(wordpress\.com|wp-admin|wp-content|/wp-|\.wordpress\.org)", u):
        return "wordpress"
    return None
