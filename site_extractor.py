# -*- coding: utf-8 -*-
"""Extraction automatique des informations du site web d'un client.

Étant donné l'URL du site d'une agence, ce module :
  1. télécharge la page (stdlib urllib, timeout court, User-Agent propre) ;
  2. extrait par règles : nom, description, slogan, email, téléphone, ville,
     pays, services, zones, types de biens, horaires, logo (og:image) ;
  3. affine avec l'IA (Gemini, optionnel) si une clé est disponible ;
  4. renvoie un dict directement compatible avec le schéma du dossier client.

Aucune nouvelle dépendance, aucun service payant : uniquement la bibliothèque
standard + le provider Gemini existant (utilisé seulement si configuré).
"""

import html as html_mod
import gzip
import json
import logging
import os
import re
import urllib.error
import urllib.parse
import urllib.request

TIMEOUT = 20
MAX_BYTES = 400_000
# Plusieurs User-Agents « navigateur » : beaucoup de sites bloquent les robots
USER_AGENTS = [
    ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
     "Chrome/126.0.0.0 Safari/537.36"),
    ("Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0"),
    ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
     "(KHTML, like Gecko) Version/17.4 Safari/605.1.15"),
    ("Mozilla/5.0 (compatible; MaisonNovaEngine/1.0; +https://maisonnova.example)"),
]

GENERIC_NAME_WORDS = {"accueil", "home", "bienvenue", "welcome", "contact", "menu",
                       "nos biens", "nos annonces", "nos services", "nos offres",
                       "nos ventes", "nos locations", "vente", "location", "achat",
                       "annonces", "qui sommes-nous", "qui sommes nous"}

SERVICE_KEYWORDS = [
    ("Achat", ["achat", "acquisition", "acheter", "achetez"]),
    ("Vente", ["vente", "vendre", "vendons", "vendez"]),
    ("Location", ["location", "locatif", "louer", "louez"]),
    ("Gestion locative", ["gestion locative", "gestion de biens", "gestion immobiliere", "gestion immobilière"]),
    ("Estimation", ["estimation", "estimer", "diagnostic", "expertise"]),
    ("Investissement", ["investissement", "investir", "placement", "rentabilite", "rentabilité", "lmnp", "pinel"]),
    ("Neuf", ["programme neuf", "programme neuf", "immobilier neuf", "residence neuve", "résidence neuve"]),
    ("Programme immobilier", ["programme immobilier", "programmes immobiliers"]),
]

PROPERTY_KEYWORDS = [
    ("Maison", ["maison", "villa", "pavillon"]),
    ("Appartement", ["appartement", "appart"]),
    ("Terrain", ["terrain", "terrains"]),
    ("Local commercial", ["local commercial", "locaux commerciaux", "boutique", "commerce"]),
    ("Immeuble", ["immeuble", "immeubles"]),
    ("Résidence secondaire", ["residence secondaire", "résidence secondaire", "pied-a-terre", "pied-à-terre"]),
]

CITIES_FR = [
    "Paris", "Marseille", "Lyon", "Toulouse", "Nice", "Nantes", "Montpellier",
    "Strasbourg", "Bordeaux", "Lille", "Rennes", "Reims", "Toulon",
    "Saint-Étienne", "Le Havre", "Grenoble", "Dijon", "Angers", "Nîmes",
    "Clermont-Ferrand", "Le Mans", "Aix-en-Provence", "Brest", "Tours",
    "Amiens", "Limoges", "Annecy", "Perpignan", "Béziers", "Orléans",
    "Metz", "Besançon", "Cannes", "Antibes", "Colmar", "Chambéry",
    "Ajaccio", "Bastia", "La Rochelle", "Bayonne", "Villeurbanne",
    "Caluire-et-Cuire", "Vénissieux", "Boulogne-Billancourt", "Nanterre",
    "Versailles", "Saint-Denis", "Créteil", "Montreuil", "Courbevoie",
]
CITIES_FR_LOWER = {c.lower() for c in CITIES_FR}


# ───────────────────────────────────────────────────────────────────────────────
# Téléchargement
# ───────────────────────────────────────────────────────────────────────────────

def normalize_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def _url_variants(u: str) -> list[str]:
    """Variantes d'URL à essayer en cas d'échec (www / sans www, http / https)."""
    variants = [u]
    parsed = urllib.parse.urlsplit(u)
    host = parsed.netloc
    if host.startswith("www."):
        variants.append(urllib.parse.urlunsplit((parsed.scheme, host[4:], parsed.path, parsed.query, "")))
    else:
        variants.append(urllib.parse.urlunsplit((parsed.scheme, "www." + host, parsed.path, parsed.query, "")))
    alt_scheme = "http" if parsed.scheme == "https" else "https"
    variants.append(urllib.parse.urlunsplit((alt_scheme, host, parsed.path, parsed.query, "")))
    return variants


def _http_get(u: str, headers: dict) -> bytes | None:
    req = urllib.request.Request(u, headers=headers)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        raw = resp.read(MAX_BYTES)
        if resp.headers.get("Content-Encoding", "").lower() == "gzip":
            try:
                raw = gzip.decompress(raw)
            except Exception:
                pass
        return raw


def fetch_site(url: str) -> str | None:
    """Télécharge une page HTML (essai multi User-Agent + variantes d'URL) et
    retourne son texte avec scripts/styles retirés. None si totalement échec."""
    u = normalize_url(url)
    if not u:
        return None
    base_headers = {"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
                    "Accept-Encoding": "gzip, deflate",
                    "Connection": "keep-alive"}
    for variant in _url_variants(u):
        for ua in USER_AGENTS:
            try:
                headers = dict(base_headers)
                headers["User-Agent"] = ua
                raw = _http_get(variant, headers)
                if raw:
                    ctype_guess = ""
                    charset = "utf-8"
                    m = re.search(rb"charset=[\"']?([\w-]+)", raw[:2000], re.I)
                    if m:
                        charset = m.group(1).decode("ascii", "replace")
                    html_text = raw.decode(charset, errors="replace")
                    html_text = re.sub(r"(?is)<script.*?</script>", " ", html_text)
                    html_text = re.sub(r"(?is)<style.*?</style>", " ", html_text)
                    html_text = re.sub(r"(?is)<(iframe|svg|template|form|select|option).*?</\1>", " ", html_text)
                    return html_text
            except urllib.error.HTTPError as exc:
                logging.debug("Extraction site — HTTP %s sur %s", exc.code, variant)
            except Exception as exc:
                logging.debug("Extraction site — échec %s : %s", variant, exc)
    logging.warning("Extraction site — téléchargement impossible : %s", u)
    return None


# ───────────────────────────────────────────────────────────────────────────────
# Extraction par règles (aucune IA, instantanée)
# ───────────────────────────────────────────────────────────────────────────────

def _strip_tags(html_text: str) -> str:
    text = re.sub(r"(?s)<[^>]+>", " ", html_text)
    return html_mod.unescape(text)


def _meta_content(html_text: str, names: list[str]) -> str | None:
    for name in names:
        m = re.search(r'<meta[^>]+(?:name|property)=["\']%s["\'][^>]*content=["\']([^"\']*)["\']' % re.escape(name),
                      html_text, re.I)
        if not m:
            m = re.search(r'<meta[^>]+content=["\']([^"\']*)["\'][^>]*(?:name|property)=["\']%s["\']' % re.escape(name),
                          html_text, re.I)
        if m and m.group(1).strip():
            return html_mod.unescape(m.group(1).strip())
    return None


def _clean_name(raw: str) -> str:
    """Nettoie un titre de page en nom d'agence, en ignorant les segments
    génériques ('Accueil - Agence Dupont' → 'Agence Dupont')."""
    raw = (raw or "").strip()
    if not raw:
        return ""
    parts = re.split(r"\s+[|\-–—·•:]+\s+", raw)
    # on préfère un segment qui ressemble à un nom (pas un mot générique)
    best = ""
    for seg in parts:
        s = seg.strip()
        if not s:
            continue
        # retire uniquement les suffixes du type « agence immobilière » restés
        # dans le segment (on garde « Dupont Immobilier » tel quel)
        core = re.sub(r"(?i)\s+(agence immobiliere|agence immobilière)$", "", s)
        core = re.sub(r"^[^\wÀ-ÿ]+\s*", "", core)  # retire emoji/icônes en tête
        key = core.strip().lower()
        if key in GENERIC_NAME_WORDS or len(key) < 3:
            continue
        # un segment trop long est rarement un nom
        if len(core) > 60:
            continue
        best = core.strip()
        break
    return best


def _find_cities(text: str) -> list[str]:
    """Villes présentes dans le texte, classées par ordre d'apparition (pas par
    ordre de la liste — évite de choisir la ville du pied de page au hasard)."""
    lower = text.lower()
    hits = []
    for city in CITIES_FR:
        c = city.lower()
        pos = lower.find(c)
        if pos >= 0:
            hits.append((pos, city))
    hits.sort(key=lambda x: x[0])
    return [city for _, city in hits[:5]]


def _main_city(text: str) -> str:
    """Ville principale : celle annoncée avec « à », « basée à », « située à »,
    « agence à »… sinon la première ville présente dans le texte."""
    lower = text.lower()
    for city in CITIES_FR:
        c = city.lower()
        if re.search(r"(?:agence|basée|basée|située|implantée|installée|localisée)\s+(?:à|a)\s+" + re.escape(c) + r"(?:[\s.,;:)]|$)", lower):
            return city
        if re.search(r"(?:à|a)\s+" + re.escape(c) + r"(?:[\s.,;:)]|$)", lower):
            return city
    cities = _find_cities(text)
    return cities[0] if cities else ""


def extract_rules(html_text: str, url: str = "") -> dict:
    """Extraction 100 % règles — rapide, sans IA. Retourne un dict de config client."""
    text = _strip_tags(html_text)
    text_flat = re.sub(r"\s+", " ", text)
    lower = text_flat.lower()

    # ── nom : og:site_name > og:title > <title> (segments génériques ignorés) ──
    og_site = _meta_content(html_text, ["og:site_name"])
    og_title = _meta_content(html_text, ["og:title"])
    title_m = re.search(r"(?is)<title[^>]*>(.*?)</title>", html_text)
    raw_title = _strip_tags(title_m.group(1)) if title_m else ""
    name = _clean_name(og_site) or _clean_name(og_title) or _clean_name(raw_title)
    if not name:
        name = urllib.parse.urlparse(url).netloc.replace("www.", "") if url else ""

    # ── description / slogan ──
    desc = (_meta_content(html_text, ["description", "og:description"])
            or _meta_content(html_text, ["twitter:description"])
            or "")
    description = (desc or "").strip()
    if not description:
        # première phrase longue trouvée dans les titres / paragraphes
        for tag in ("h1", "h2", "p"):
            for m in re.finditer(r"(?is)<%s[^>]*>(.*?)</%s>" % (tag, tag), html_text):
                t = _strip_tags(m.group(1)).strip()
                t = re.sub(r"\s+", " ", t)
                if 30 <= len(t) <= 300:
                    description = t
                    break
            if description:
                break
    slogan = (desc or og_title or "")[:160]

    # ── coordonnées ──
    emails = re.findall(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", text_flat)
    emails = [e for e in dict.fromkeys(emails) if not e.lower().endswith((".png", ".jpg", ".webp", ".gif"))]
    email = emails[0] if emails else ""

    phones = re.findall(r"(?:\+33|0)[1-9](?:[ .\-]?\d{2}){4}", text_flat)
    phone = phones[0] if phones else ""

    # ── ville / zones / pays ──
    city = _main_city(text_flat)
    cities = _find_cities(text_flat)
    other = [c for c in cities if c != city]
    zones = ", ".join(other[:3]) if other else (city or "")
    country = ""
    if re.search(r"\bfrance\b|\ben france\b|république française", lower):
        country = "France"

    # ── services ──
    services = [label for label, kws in SERVICE_KEYWORDS if any(k in lower for k in kws)]

    # ── types de biens ──
    props = [label for label, kws in PROPERTY_KEYWORDS if any(k in lower for k in kws)]

    # ── horaires ──
    hours = ""
    m = re.search(r"(?i)\b(?:lun|mar|mer|jeu|ven|sam|dim)[a-zéû.]*\s*[–\-à/]\s*[a-zéû.]+\s*[·:]\s*\d{1,2}h[0-9]{0,2}[–\-à]\d{1,2}h[0-9]{0,2}", text_flat)
    if not m:
        m = re.search(r"\d{1,2}h[0-9]{0,2}\s*(?:–|-|à)\s*\d{1,2}h[0-9]{0,2}", text_flat)
    if m:
        hours = re.sub(r"\s+", " ", m.group(0)).strip()

    # ── logo (og:image / twitter:image) ──
    logo = _meta_content(html_text, ["og:image"]) or _meta_content(html_text, ["twitter:image"])
    if logo and not logo.startswith(("http://", "https://", "data:")):
        logo = urllib.parse.urljoin(url, logo) if url else ""

    return {
        "name": name, "description": description, "slogan": slogan,
        "email": email, "phone": phone, "website": normalize_url(url),
        "city": city, "country": country, "zones": zones,
        "services": services, "property_types": props, "hours": hours,
        "logo_url": logo or "", "source": "site",
    }


# ───────────────────────────────────────────────────────────────────────────────
# Affinage IA (optionnel)
# ───────────────────────────────────────────────────────────────────────────────

SYSTEM_EXTRACT_SITE = """Tu es un assistant qui lit la page d'accueil d'une agence immobilière.
Extrais les informations structurées de cette agence. Réponds UNIQUEMENT en JSON valide avec ces clés exactes :
{
  "name": string|null, "description": string|null, "slogan": string|null,
  "email": string|null, "phone": string|null, "city": string|null, "country": string|null,
  "zones": string|null, "hours": string|null,
  "services": ["Achat","Vente","Location","Gestion locative","Estimation","Investissement","Neuf","Programme immobilier"],
  "property_types": ["Maison","Appartement","Terrain","Local commercial","Immeuble","Résidence secondaire"]
}
Règles : ne jamais inventer une information absente de la page (null si absente) ;
les tableaux ne contiennent que des valeurs de la liste proposée ; city = ville où se situe l'agence ;
zones = secteurs couverts (texte court). Aucun texte hors JSON."""


def _ai_refine(text: str) -> dict:
    try:
        import ai_provider
        key = os.getenv("GEMINI_API_KEY", "")
        if not key:
            return {}
        provider = ai_provider.AIProvider(api_key=key, timeout=35)
        if not provider.ready:
            return {}
        sample = re.sub(r"\s+", " ", text)[:4000]
        data = provider.json(SYSTEM_EXTRACT_SITE, sample, max_tokens=700)
        if data and isinstance(data, dict):
            return data
    except Exception as exc:
        logging.warning("Affinage IA du site impossible : %s", exc)
    return {}


# ───────────────────────────────────────────────────────────────────────────────
# API publique
# ───────────────────────────────────────────────────────────────────────────────

def _normalize_list(values, allowed: list[str]) -> list[str]:
    """Ne garde que les valeurs connues d'une liste (évite les inventions IA)."""
    allowed_lower = {v.lower() for v in allowed}
    out = []
    for v in values or []:
        s = str(v).strip()
        if not s:
            continue
        # accepte la valeur telle quelle ou une correspondance insensible à la casse
        match = next((a for a in allowed if a.lower() == s.lower()), None)
        if match and match not in out:
            out.append(match)
    return out


def extract_from_html(html_text: str, url: str = "", use_ai: bool = True) -> dict:
    """Extrait la config client depuis un HTML brut (testable sans réseau).
    L'IA (si configurée) fait foi sur les champs qu'elle remplit ; les règles
    comblent les vides."""
    info = extract_rules(html_text, url)
    if use_ai and os.getenv("GEMINI_API_KEY", ""):
        ai = _ai_refine(html_text)
        if ai:
            for k in ("name", "description", "slogan", "email", "phone", "city",
                      "country", "zones", "hours"):
                if ai.get(k):
                    info[k] = str(ai[k]).strip()
            allowed_services = [label for label, _ in SERVICE_KEYWORDS]
            allowed_props = [label for label, _ in PROPERTY_KEYWORDS]
            if ai.get("services"):
                norm = _normalize_list(ai.get("services"), allowed_services)
                info["services"] = norm or info.get("services") or []
            if ai.get("property_types"):
                norm = _normalize_list(ai.get("property_types"), allowed_props)
                info["property_types"] = norm or info.get("property_types") or []
    return info


def extract_from_url(url: str, use_ai: bool = True) -> dict:
    """Point d'entrée admin : télécharge le site puis extrait la config."""
    html_text = fetch_site(url)
    if html_text is None:
        return {"source": "error"}
    info = extract_from_html(html_text, url=url, use_ai=use_ai)
    info["website"] = normalize_url(url)
    return info
