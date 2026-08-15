# -*- coding: utf-8 -*-
"""Vues Streamlit des onglets ADMIN « nouvelle génération » :
🏢 Clients · 🛠 Configuration (parcours 8 étapes) · 🤖 Chatbots ·
📦 Installation · 📘 Guides · ⚙️ Paramètres.

Aucune importation d'app.py (pas d'import circulaire) : les fonctions
Google Sheets sont passées en paramètres depuis app.py.
"""

import datetime

import streamlit as st

import chatbot_config as cc
import client_kit as ck
import clients_store as cs
import guide_builder as gb
import guide_content as gc
import site_extractor as se
import widget_code as wc

WIZARD_STEPS = [
    ("agence", "Étape 1/8 — Agence"),
    ("activite", "Étape 2/8 — Activité"),
    ("parcours", "Étape 3/8 — Parcours clients"),
    ("qualification", "Étape 4/8 — Qualification"),
    ("assistant", "Étape 5/8 — Assistant"),
    ("rendezvous", "Étape 6/8 — Rendez-vous"),
    ("apparence", "Étape 7/8 — Apparence"),
    ("resume", "Étape 8/8 — Résumé"),
]

SERVICES_OPTIONS = ["Achat", "Vente", "Location", "Gestion locative",
                    "Estimation", "Investissement", "Neuf", "Programme immobilier"]
PROPERTY_OPTIONS = ["Maison", "Appartement", "Terrain", "Local commercial",
                    "Immeuble", "Résidence secondaire"]


# ───────────────────────────────────────────────────────────────────────────────
# Aide commune
# ───────────────────────────────────────────────────────────────────────────────

def _selected_client_id() -> str | None:
    return st.session_state.get("adm_client", None)


def _client_selector(key: str = "adm_sel_client", label: str = "Client") -> dict | None:
    clients = cs.load_clients()
    if not clients:
        st.info("Aucun client. Créez-en un dans l'onglet « 🏢 Clients ».")
        return None
    options = []
    for cid, cl in clients.items():
        ag = cl.get("agency") or {}
        name = ag.get("name") or cid
        options.append((cid, f"{name} — {cl.get('status') or 'DRAFT'}"))
    labels = [l for _, l in options]
    sel_label = st.selectbox(label, labels, key=key)
    cid = None
    for c, l in options:
        if l == sel_label:
            cid = c
            break
    if cid is None and options:
        cid = options[0][0]
    if cid:
        st.session_state["adm_client"] = cid
        return cs.load_clients().get(cid)
    return None


def _badge(status: str) -> str:
    ok = {"CONFIGURED", "PREVIEW_READY", "CODE_READY", "GUIDE_READY", "INSTALLED"}
    if status == "INSTALLED":
        return f"<span class='badge badge-ok'>✅ {status}</span>"
    if status in ok:
        return f"<span class='badge badge-ok'>{status}</span>"
    if status == "ERROR":
        return "<span class='badge badge-ko'>⚠️ ERROR</span>"
    return f"<span class='badge badge-ko'>{status}</span>"


def _step_done(client: dict, step: str) -> bool:
    ag = client.get("agency") or {}
    ac = client.get("activity") or {}
    ast = client.get("assistant") or {}
    app = client.get("appearance") or {}
    cb = client.get("chatbot") or {}
    if step == "agence":
        return bool(ag.get("name") and ag.get("city") and ag.get("email"))
    if step == "activite":
        return bool(ag.get("description") or (ac.get("services") or []))
    if step == "parcours":
        return bool(cb.get("journeys"))
    if step == "qualification":
        return ag.get("threshold") is not None
    if step == "assistant":
        return bool(ast.get("name"))
    if step == "rendezvous":
        return bool(ag.get("calendly_url"))
    if step == "apparence":
        return bool(app.get("primary_color"))
    return True


def _auto_status(client: dict) -> None:
    """Avance automatiquement DRAFT → CONFIGURED dès que l'essentiel est rempli."""
    if client.get("status") == "DRAFT":
        ag = client.get("agency") or {}
        if ag.get("name") and ag.get("city"):
            cs.set_status(client.get("id") or client.get("slug"), "CONFIGURED")


# ───────────────────────────────────────────────────────────────────────────────
# ⚡ Remplissage automatique depuis le site du client
# ───────────────────────────────────────────────────────────────────────────────

def _site_fill_block(client: dict, target: str, key_prefix: str) -> None:
    """Encart « Remplir automatiquement depuis le site » : collez l'URL, l'outil
    extrait les informations (nom, description, coordonnées, services…) et les
    applique au client (target = 'agence' | 'activite')."""
    ct = client.get("contact") or {}
    with st.form(f"site_fill_{key_prefix}"):
        c1, c2 = st.columns([3, 1])
        url = c1.text_input("Adresse du site web du client", value=ct.get("website", ""),
                            placeholder="https://www.mon-agence.fr", key=f"sf_{key_prefix}_url")
        use_ai = c2.checkbox("Affiner avec l'IA", value=True, key=f"sf_{key_prefix}_ai")
        if st.form_submit_button("🔍 Analyser le site et remplir automatiquement",
                                 use_container_width=True):
            if not (url or "").strip():
                st.warning("Entrez d'abord l'adresse du site du client.")
                return
            with st.spinner("Extraction des informations du site…"):
                info = se.extract_from_url(url, use_ai=bool(use_ai))
            if info.get("source") == "error" or not info.get("name"):
                st.error("Impossible de lire ce site. Vérifiez l'adresse "
                         "ou remplissez le formulaire à la main.")
                return
            fields: dict = {}
            if target in ("agence", "all"):
                ag = client.get("agency") or {}
                fields["agency"] = {
                    "name": info.get("name") or ag.get("name", ""),
                    "description": info.get("description") or "",
                    "email": info.get("email") or "",
                    "logo_url": info.get("logo_url") or "",
                    "city": info.get("city") or "",
                }
                fields["contact"] = {**ct,
                                      "website": info.get("website") or (url or "").strip(),
                                      "phone": info.get("phone") or "",
                                      "country": info.get("country") or ""}
            if target in ("activite", "all"):
                fields["slogan"] = info.get("slogan") or client.get("slogan", "")
                fields["activity"] = {**client.get("activity", {}),
                                       "services": info.get("services") or [],
                                       "zones": info.get("zones") or "",
                                       "property_types": info.get("property_types") or [],
                                       "hours": info.get("hours") or ""}
            cs.update_client(client.get("id") or client.get("slug"), **fields)
            st.success(f"✅ Site analysé — « {info.get('name')} » : informations pré-remplies.")
            st.rerun()


# ───────────────────────────────────────────────────────────────────────────────
# 🏢 CLIENTS
# ───────────────────────────────────────────────────────────────────────────────

def render_clients_tab(default_app_url: str) -> None:
    st.markdown("### 🏢 Clients")
    st.markdown("_Gérez vos clients : créez, configurez, suivez le statut de chaque dossier._")

    with st.expander("⚡ Création rapide depuis le site du client", expanded=False):
        st.markdown("_Collez l'adresse du site de votre client : l'outil extrait automatiquement "
                    "le nom, la description, les coordonnées, les services, la ville… "
                    "puis crée le dossier et pré-remplit la configuration._")
        with st.form("fast_create_site"):
            fast_url = st.text_input("Adresse du site web",
                                     placeholder="https://www.mon-agence.fr", key="fc_url")
            fast_ai = st.checkbox("Affiner avec l'IA (si Gemini configuré)", value=True, key="fc_ai")
            if st.form_submit_button("🔍 Analyser et créer le client", type="primary",
                                     use_container_width=True):
                if not (fast_url or "").strip():
                    st.warning("Entrez l'adresse du site d'abord.")
                else:
                    with st.spinner("Extraction des informations du site…"):
                        info = se.extract_from_url(fast_url, use_ai=bool(fast_ai))
                    if info.get("source") == "error" or not info.get("name"):
                        st.error("Impossible de lire ce site. Vérifiez l'adresse "
                                 "ou créez le client manuellement ci-dessous.")
                    else:
                        client = cs.create_client(name=info["name"], app_url=default_app_url,
                                                  email=info.get("email") or "")
                        cs.update_client(
                            client["id"],
                            agency={"description": info.get("description") or "",
                                    "city": info.get("city") or "",
                                    "email": info.get("email") or "",
                                    "logo_url": info.get("logo_url") or ""},
                            contact={"website": info.get("website") or (fast_url or "").strip(),
                                     "phone": info.get("phone") or "",
                                     "country": info.get("country") or ""},
                            slogan=info.get("slogan") or "",
                            activity={"services": info.get("services") or [],
                                      "zones": info.get("zones") or "",
                                      "property_types": info.get("property_types") or [],
                                      "hours": info.get("hours") or ""})
                        st.session_state["adm_client"] = client["id"]
                        st.session_state["goto_tab"] = "🛠 Configuration"
                        st.success(f"✅ Client créé depuis le site : {info.get('name')} — "
                                   f"{client.get('id')} (configuration pré-remplie)")
                        st.rerun()

    with st.expander("➕ Nouveau client (formulaire manuel)", expanded=False):
        with st.form("new_client_form"):
            name = st.text_input("Nom de l'agence *", key="nc_name")
            manager = st.text_input("Nom du responsable", key="nc_manager")
            email = st.text_input("Email", key="nc_email")
            if st.form_submit_button("Créer le client", type="primary", use_container_width=True):
                if (name or "").strip():
                    client = cs.create_client(name=name.strip(), app_url=default_app_url,
                                              manager=manager or "", email=email or "")
                    st.session_state["adm_client"] = client["id"]
                    st.session_state["goto_tab"] = "🛠 Configuration"
                    st.success(f"✅ Client créé : {client.get('slug')} — {client.get('id')}")
                    st.rerun()
                else:
                    st.error("Le nom de l'agence est obligatoire.")

    clients = cs.load_clients()
    if not clients:
        st.info("Aucun client pour le moment.")
        return

    st.markdown("#### Tableau de bord des clients")
    rows = []
    for cid, cl in clients.items():
        ag = cl.get("agency") or {}
        steps = cs.status_steps(cl)
        badges = " ".join(
            f"<span class='badge badge-ok'>{label}</span>" if ok
            else f"<span class='badge badge-ko'>🟡 {label}</span>"
            for label, ok in steps)
        demo_link = wc.public_url(cl)
        rows.append(
            f"<div class='glass' style='margin:8px 0;'>"
            f"<b>{ag.get('name') or cid}</b> · <span class='muted'>{cl.get('id') or ''}</span><br/>"
            f"{_badge(cl.get('status') or 'DRAFT')} &nbsp; {badges}"
            f"<div class='muted' style='margin-top:4px;'>Créé le {cl.get('created_at') or '—'} · "
            f"Slug : <code>{cl.get('slug') or '—'}</code></div>"
            f"<div style='margin-top:6px;'><a href='{demo_link}' target='_blank'>"
            f"🌐 Ouvrir le chatbot (démo / à partager)</a></div></div>")
    st.markdown("".join(rows), unsafe_allow_html=True)

    st.divider()
    selected = _client_selector(key="adm_sel_client")
    if not selected:
        return
    ag = selected.get("agency") or {}
    st.markdown(f"**Client sélectionné :** {ag.get('name') or ''} — {_badge(selected.get('status') or 'DRAFT')}",
                unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("✏️ Modifier (Configuration)", use_container_width=True):
        st.session_state["wiz_step_idx"] = 0
        st.session_state["goto_tab"] = "🛠 Configuration"
        st.rerun()
    if c2.button("📋 Statut suivant", use_container_width=True):
        cs.set_status(selected.get("id"), cs.next_status(selected.get("status") or "DRAFT"))
        st.rerun()
    if c3.button("⚠️ Marquer ERROR", use_container_width=True):
        cs.set_status(selected.get("id"), "ERROR")
        st.rerun()
    if c4.button("🗑️ Supprimer ce client", type="secondary", use_container_width=True):
        st.session_state["del_mode"] = True
        st.rerun()
    if st.session_state.get("del_mode"):
        st.warning("⚠️ Suppression définitive : le dossier du client et son accès chatbot "
                   "seront supprimés. Les leads déjà capturés sont conservés (traçabilité).")
        confirm = st.checkbox("Je confirme la suppression définitive", key="del_confirm")
        b1, b2 = st.columns(2)
        if b1.button("🗑️ Oui, supprimer définitivement", type="primary",
                     disabled=not confirm, use_container_width=True, key="del_btn"):
            name = (selected.get("agency") or {}).get("name") or ""
            ok = cs.delete_client(selected.get("id"))
            st.session_state.pop("adm_client", None)
            st.session_state.pop("del_mode", None)
            if ok:
                st.success(f"✅ Client « {name} » supprimé (accès chatbot retiré).")
            else:
                st.error("Suppression impossible.")
            st.rerun()
        if b2.button("Annuler", use_container_width=True, key="del_cancel"):
            st.session_state.pop("del_mode", None)
            st.rerun()


# ───────────────────────────────────────────────────────────────────────────────
# 🛠 CONFIGURATION — parcours en 8 étapes
# ───────────────────────────────────────────────────────────────────────────────

def render_wizard_tab(default_app_url: str) -> None:
    st.markdown("### 🛠 Configuration du client")
    st.markdown("_Parcours guidé en 8 étapes : chaque étape s'enregistre indépendamment, "
                "le dossier du client évolue à mesure._")
    client = _client_selector(key="adm_sel_wiz", label="Client à configurer")
    if not client:
        return

    # index d'étape piloté par une simple variable de session (pas de conflit de widget)
    idx = int(st.session_state.get("wiz_step_idx", 0) or 0)
    idx = max(0, min(idx, len(WIZARD_STEPS) - 1))

    # ── stepper : pastilles cliquables (✓ fait · ● étape en cours) ──
    short = ["Agence", "Activité", "Parcours", "Qualification",
             "Assistant", "Rendez-vous", "Apparence", "Résumé"]
    done_flags = [_step_done(client, k) for k, _ in WIZARD_STEPS]
    rows = [st.columns(4), st.columns(4)]
    for i, (key, _lbl) in enumerate(WIZARD_STEPS):
        with rows[i // 4][i % 4]:
            prefix = "● " if i == idx else ("✓ " if done_flags[i] else "")
            disp = f"{prefix}{i + 1} · {short[i]}"
            if st.button(disp, key=f"wiz_pill_{i}", help=WIZARD_STEPS[i][1],
                         use_container_width=True):
                st.session_state["wiz_step_idx"] = i
                st.rerun()

    # ── progression + titre de l'étape ──
    title = WIZARD_STEPS[idx][1].split("—")[-1].strip()
    pct = round(idx / (len(WIZARD_STEPS) - 1) * 100)
    st.markdown(
        f'<div class="wiz-progress"><div class="wiz-bar"><i style="width:{pct}%"></i></div>'
        f'<span class="muted"><b>Étape {idx + 1} / {len(WIZARD_STEPS)}</b> — {title}</span></div>',
        unsafe_allow_html=True)

    step = WIZARD_STEPS[idx][0]
    if step == "agence":
        _step_agence(client, default_app_url)
    elif step == "activite":
        _step_activite(client)
    elif step == "parcours":
        _step_parcours(client)
    elif step == "qualification":
        _step_qualification(client)
    elif step == "assistant":
        _step_assistant(client)
    elif step == "rendezvous":
        _step_rendezvous(client)
    elif step == "apparence":
        _step_apparence(client)
    else:
        _step_resume(client)

    # ── navigation ──
    c1, c2, c3 = st.columns(3)
    if idx > 0 and c1.button("← Précédent", use_container_width=True):
        st.session_state["wiz_step_idx"] = idx - 1
        st.rerun()
    if idx < len(WIZARD_STEPS) - 1 and c2.button("Étape suivante →", use_container_width=True):
        st.session_state["wiz_step_idx"] = idx + 1
        st.rerun()
    c3.caption("💾 Pensez à enregistrer chaque étape avec son bouton.")


def _save(client, **fields) -> None:
    cid = client.get("id") or client.get("slug")
    cs.update_client(cid, **fields)
    st.success("✅ Enregistré.")
    st.rerun()


def _step_agence(client, default_app_url: str) -> None:
    st.markdown("#### ⚡ Option : remplir automatiquement depuis le site du client")
    _site_fill_block(client, "agence", "ag")
    st.divider()
    ag = client.get("agency") or {}
    ct = client.get("contact") or {}
    with st.form("wiz_agence"):
        c1, c2 = st.columns(2)
        name = c1.text_input("Nom de l'agence *", value=ag.get("name", ""), key="w_ag_name")
        city = c2.text_input("Ville *", value=ag.get("city", ""), key="w_ag_city")
        c3, c4 = st.columns(2)
        country = c3.text_input("Pays", value=ct.get("country", ""), key="w_ag_country")
        address = c4.text_input("Adresse", value=ct.get("address", ""), key="w_ag_addr")
        c5, c6 = st.columns(2)
        email = c5.text_input("Email *", value=ag.get("email", ""), key="w_ag_email")
        phone = c6.text_input("Téléphone", value=ct.get("phone", ""), key="w_ag_phone")
        website = st.text_input("Site web", value=ct.get("website", ""),
                                placeholder="https://www.mon-agence.fr", key="w_ag_site")
        logo = st.text_input("URL du logo", value=ag.get("logo_url", ""),
                             placeholder="https://…/logo.png", key="w_ag_logo")
        if st.form_submit_button("💾 Enregistrer l'étape 1", type="primary", use_container_width=True):
            if not (name or "").strip():
                st.error("Le nom de l'agence est obligatoire.")
            else:
                _save(client, agency={"name": (name or "").strip(), "city": (city or "").strip(),
                                      "email": (email or "").strip(), "logo_url": (logo or "").strip(),
                                      "app_url": (ag.get("app_url") or default_app_url)},
                      contact={"country": (country or "").strip(), "address": (address or "").strip(),
                               "phone": (phone or "").strip(), "website": (website or "").strip()})


def _step_activite(client) -> None:
    st.markdown("#### ⚡ Option : remplir automatiquement depuis le site du client")
    _site_fill_block(client, "activite", "ac")
    st.divider()
    ag = client.get("agency") or {}
    ac = client.get("activity") or {}
    with st.form("wiz_activite"):
        desc = st.text_area("Description", value=ag.get("description", ""),
                            placeholder="Votre agence en quelques mots…", key="w_ac_desc")
        slogan = st.text_input("Slogan", value=client.get("slogan", ""), key="w_ac_slogan")
        services = st.multiselect("Services", SERVICES_OPTIONS, default=ac.get("services") or [], key="w_ac_serv")
        zones = st.text_input("Zones couvertes", value=ac.get("zones", ""),
                              placeholder="Lyon, Villeurbanne, Caluire…", key="w_ac_zones")
        props = st.multiselect("Types de biens", PROPERTY_OPTIONS, default=ac.get("property_types") or [], key="w_ac_props")
        hours = st.text_input("Horaires", value=ac.get("hours", ""),
                              placeholder="Lun–Sam · 9h–19h", key="w_ac_hours")
        if st.form_submit_button("💾 Enregistrer l'étape 2", type="primary", use_container_width=True):
            _save(client, agency={"description": (desc or "").strip()}, slogan=(slogan or "").strip(),
                  activity={"services": list(services or []), "zones": (zones or "").strip(),
                            "property_types": list(props or []), "hours": (hours or "").strip()})


def _step_parcours(client) -> None:
    cb = client.get("chatbot") or {}
    journeys = dict(cb.get("journeys") or {})
    if not journeys:
        journeys = cc.default_journeys()
    st.markdown("_Activez les parcours proposés à vos prospects et choisissez le parcours principal du chat._")
    with st.form("wiz_parcours"):
        enabled = {}
        for jk in cc.JOURNEY_KEYS:
            cur = journeys.get(jk) or {}
            enabled[jk] = st.checkbox(f"Parcours **{cc.JOURNEY_LABELS[jk]}**", value=bool(cur.get("enabled")),
                                      key=f"w_p_{jk}")
        default_journey = st.selectbox("Parcours principal (utilisé dans le chat)",
                                       [jk for jk in cc.JOURNEY_KEYS if enabled.get(jk)] or cc.JOURNEY_KEYS,
                                       index=0, key="w_p_default")
        if st.form_submit_button("💾 Enregistrer l'étape 3", type="primary", use_container_width=True):
            for jk in cc.JOURNEY_KEYS:
                cur = dict(journeys.get(jk) or {})
                cur["enabled"] = bool(enabled.get(jk))
                journeys[jk] = cur
            _save(client, chatbot={"default_journey": default_journey, "journeys": journeys})


def _step_qualification(client) -> None:
    ag = client.get("agency") or {}
    cb = client.get("chatbot") or {}
    journeys = dict(cb.get("journeys") or {})
    if not journeys:
        journeys = cc.default_journeys()
    jk = cb.get("default_journey") or "achat"
    j = journeys.get(jk) or {}
    threshold = ag.get("threshold", 70)
    st.markdown(f"_Scoring sur **100 points** pour le parcours « {cc.JOURNEY_LABELS.get(jk, jk)} ». "
                f"Seuil de qualification : score ≥ seuil → rendez-vous Calendly._")
    with st.form("wiz_qualif"):
        new_thr = st.slider("Seuil de qualification", 0, 100, int(threshold or 70), step=5, key="w_q_thr")
        points = _points_editor(j.get("points") or cc.points_for(client, jk), key_prefix="w_q")
        if st.form_submit_button("💾 Enregistrer l'étape 4", type="primary", use_container_width=True):
            journeys[jk] = {**j, "points": points}
            _save(client, agency={"threshold": int(new_thr)},
                  chatbot={"default_journey": jk, "journeys": journeys})


def _points_editor(current: dict, key_prefix: str) -> dict:
    st.markdown("**Points par critère** (max 100 au total)")
    labels = {"project_type": "Projet", "budget": "Budget", "city": "Ville",
              "financing": "Financement", "timeline": "Délai"}
    merged = cc.points_for(None) if not current else current
    out = {}
    for cat, table in merged.items():
        with st.expander(f"⚖️ {labels.get(cat, cat)}", expanded=False):
            out[cat] = {}
            if cat == "city":
                same = st.number_input("Même ville que l'agence", 0, 50,
                                       int(table.get("same", 15) or 15), key=f"{key_prefix}_city_same")
                other = st.number_input("Autre ville", 0, 50,
                                        int(table.get("other", 10) or 10), key=f"{key_prefix}_city_other")
                out[cat] = {"same": int(same or 0), "other": int(other or 0)}
            else:
                for opt, val in table.items():
                    v = st.number_input(f"{opt}", 0, 50, int(val or 0), key=f"{key_prefix}_{cat}_{opt}")
                    out[cat][opt] = int(v or 0)
    return out


def _step_assistant(client) -> None:
    ast = client.get("assistant") or {}
    with st.form("wiz_assistant"):
        name = st.text_input("Nom de l'assistant", value=ast.get("name", ""),
                             placeholder="Sophie, Maxime…", key="w_as_name")
        tone = st.selectbox("Ton", ["chaleureux", "professionnel", "premium", "dynamique"],
                            index=0, key="w_as_tone")
        welcome = st.text_area("Message d'accueil personnalisé (optionnel)",
                               value=ast.get("welcome_message", ""),
                               placeholder="Laisser vide = message généré par l'IA au nom de l'agence",
                               key="w_as_welcome")
        if st.form_submit_button("💾 Enregistrer l'étape 5", type="primary", use_container_width=True):
            _save(client, assistant={"name": (name or "").strip(), "tone": tone or "chaleureux",
                                     "welcome_message": (welcome or "").strip()})


def _step_rendezvous(client) -> None:
    ag = client.get("agency") or {}
    with st.form("wiz_rdv"):
        calendly = st.text_input("Lien Calendly", value=ag.get("calendly_url", ""),
                                 placeholder="https://calendly.com/…", key="w_rdv_cal")
        email = st.text_input("Email de l'agence (alertes)", value=ag.get("email", ""), key="w_rdv_email")
        st.caption("Le bouton doré « Réserver mon rendez-vous expert » apparaît si score ≥ seuil.")
        if st.form_submit_button("💾 Enregistrer l'étape 6", type="primary", use_container_width=True):
            _save(client, agency={"calendly_url": (calendly or "").strip(), "email": (email or "").strip()})


def _step_apparence(client) -> None:
    app = client.get("appearance") or {}
    with st.form("wiz_app"):
        c1, c2 = st.columns(2)
        primary = c1.color_picker("Couleur principale", value=app.get("primary_color") or "#C9A227", key="w_ap_p")
        secondary = c2.color_picker("Couleur secondaire", value=app.get("secondary_color") or "#9C7A14", key="w_ap_s")
        st.caption("Ces couleurs personnalisent le chat prospect (boutons, barre de score, CTA doré).")
        if st.form_submit_button("💾 Enregistrer l'étape 7", type="primary", use_container_width=True):
            _save(client, appearance={"primary_color": primary or "#C9A227",
                                      "secondary_color": secondary or "#9C7A14"})


def _step_resume(client) -> None:
    ag = client.get("agency") or {}
    ct = client.get("contact") or {}
    ac = client.get("activity") or {}
    ast = client.get("assistant") or {}
    app = client.get("appearance") or {}
    cb = client.get("chatbot") or {}
    st.markdown(
        f"<div class='glass'>"
        f"<b>{ag.get('name') or '—'}</b> · <code>{client.get('id') or ''}</code> · "
        f"slug <code>{client.get('slug') or ''}</code><br/><br/>"
        f"📍 {ag.get('city') or '—'} · 📧 {ag.get('email') or '—'} · 📞 {ct.get('phone') or '—'}<br/>"
        f"🌐 {ct.get('website') or '—'}<br/>"
        f"🛎️ Services : {', '.join(ac.get('services') or []) or '—'}<br/>"
        f"🎯 Seuil : <b>{ag.get('threshold', 70)}/100</b> · 📅 Calendly : {'oui' if ag.get('calendly_url') else 'non'}<br/>"
        f"🤖 Assistant : {ast.get('name') or '—'} · 🎨 Couleurs : {app.get('primary_color') or '—'}<br/>"
        f"💬 Parcours : {', '.join(cc.JOURNEY_LABELS[k] for k, v in (cb.get('journeys') or {}).items() if v.get('enabled')) or '—'}"
        f"</div>", unsafe_allow_html=True)
    if st.button("✅ Valider la configuration (statut CONFIGURED)", type="primary", use_container_width=True):
        cid = client.get("id") or client.get("slug")
        if not ag.get("name") or not ag.get("city"):
            st.error("Complétez au minimum l'étape 1 (nom + ville) avant de valider.")
        else:
            cs.set_status(cid, "CONFIGURED")
            st.rerun()


# ───────────────────────────────────────────────────────────────────────────────
# 🤖 CHATBOTS
# ───────────────────────────────────────────────────────────────────────────────

def render_chatbots_tab() -> None:
    st.markdown("### 🤖 Chatbots — configuration flexible")
    client = _client_selector(key="adm_sel_bot", label="Client")
    if not client:
        return
    cb = client.get("chatbot") or {}
    journeys = dict(cb.get("journeys") or {})
    if not journeys:
        journeys = cc.default_journeys()
    ag = client.get("agency") or {}
    ast = client.get("assistant") or {}

    with st.form("bot_save"):
        default_journey = st.selectbox(
            "Parcours principal du chat",
            cc.JOURNEY_KEYS,
            index=cc.JOURNEY_KEYS.index(cb.get("default_journey") or "achat"),
            format_func=lambda k: cc.JOURNEY_LABELS.get(k, k),
            key="bot_default")
        threshold = st.slider("Seuil de qualification (score /100)", 0, 100,
                              int(ag.get("threshold", 70) or 70), step=5, key="bot_thr")

        for jk in cc.JOURNEY_KEYS:
            cur = dict(journeys.get(jk) or {})
            with st.expander(f"{cc.JOURNEY_LABELS[jk]} — {'activé' if cur.get('enabled') else 'désactivé'}",
                             expanded=jk == (cb.get("default_journey") or "achat")):
                cur["enabled"] = st.checkbox("Activer ce parcours", value=bool(cur.get("enabled")),
                                             key=f"bot_en_{jk}")
                msg = st.text_input("Message d'accueil spécifique (optionnel)", value=cur.get("message") or "",
                                    key=f"bot_msg_{jk}")
                cur["message"] = (msg or "").strip()
                thr = st.number_input("Seuil spécifique (0 = seuil de l'agence)", 0, 100,
                                      int(cur.get("threshold") or 0), key=f"bot_thr_{jk}")
                cur["threshold"] = int(thr or 0) or None
                st.markdown("**Questions de ce parcours** (texte libre, ordre modifiable)")
                qs = cur.get("questions") or cc.default_questions_dict()
                new_qs = []
                for i, q in enumerate(qs):
                    c1, c2 = st.columns([2, 3])
                    key_q = f"bot_q_{jk}_{i}"
                    label = c1.text_input(f"Libellé {i+1}", value=(q.get("label") or ""), key=key_q + "_l")
                    tmpl = c2.text_input(f"Question {i+1}", value=(q.get("template") or ""), key=key_q + "_t")
                    new_qs.append({"key": q.get("key") or "autre", "label": (label or "").strip(),
                                   "template": (tmpl or "").strip()})
                cur["questions"] = new_qs
                journeys[jk] = cur

        c1, c2 = st.columns([1, 2])
        as_name = c1.text_input("Nom de l'assistant", value=ast.get("name", ""), key="bot_as_name")
        as_welcome = c2.text_input("Message d'accueil (personnalisé)", value=ast.get("welcome_message", ""),
                                   key="bot_as_welcome")

        if st.form_submit_button("💾 Enregistrer la configuration chatbot", type="primary",
                                 use_container_width=True):
            cid = client.get("id") or client.get("slug")
            cs.update_client(cid, chatbot={"default_journey": default_journey, "journeys": journeys},
                             agency={"threshold": int(threshold)},
                             assistant={"name": (as_name or "").strip(),
                                        "welcome_message": (as_welcome or "").strip(),
                                        "tone": ast.get("tone") or "chaleureux"})
            st.success("✅ Configuration chatbot enregistrée.")
            st.rerun()


# ───────────────────────────────────────────────────────────────────────────────
# 📦 INSTALLATION
# ───────────────────────────────────────────────────────────────────────────────

def render_install_tab() -> None:
    st.markdown("### 📦 Installation — code, identifiant, clé")
    client = _client_selector(key="adm_sel_inst", label="Client")
    if not client:
        return
    ag = client.get("agency") or {}
    install = wc.ensure_install(client)

    st.markdown(f"#### {ag.get('name') or ''} · <code>{client.get('id') or ''}</code>",
                unsafe_allow_html=True)

    # 0. Lien de démonstration à partager
    st.markdown("**🔗 Lien de démonstration à partager**")
    st.markdown("_Envoyez ce lien à votre client pour qu'il teste son assistant en conditions "
                "réelles (aucun mot de passe requis) — il vous sert aussi de démonstration._")
    st.code(wc.public_url(client), language=None)
    c_d1, c_d2 = st.columns(2)
    c_d1.link_button("🌐 Ouvrir / tester en ligne", wc.public_url(client), use_container_width=True)
    c_d2.download_button("💾 Télécharger le lien (.url)",
                         f"[InternetShortcut]\nURL={wc.public_url(client)}\n",
                         file_name=f"{client.get('slug')}_demo.url", mime="text/plain",
                         key="dl_demo_url")
    st.divider()

    # A. URL publique
    st.markdown("**A. URL publique**")
    st.code(wc.public_url(client), language=None)
    # B. iframe
    st.markdown("**B. iframe**")
    st.code(wc.iframe_snippet(client), language="html")
    st.download_button("⬇️ Télécharger l'iframe", wc.iframe_snippet(client),
                       file_name=f"{client.get('slug')}_iframe.html", mime="text/html",
                       key="dl_iframe")
    # C. code d'installation
    st.markdown("**C. Code d'installation** (div + script — WordPress, Wix, Webflow, site personnalisé)")
    st.code(wc.script_snippet(client), language="html")
    st.download_button("⬇️ Télécharger le code", wc.script_snippet(client),
                       file_name=f"{client.get('slug')}_code.html", mime="text/html",
                       key="dl_code")
    # D. identifiant + E. clé
    c1, c2 = st.columns(2)
    c1.markdown("**D. Identifiant agence**")
    c1.code(client.get("id") or "", language=None)
    c2.markdown("**E. Clé d'installation**")
    c2.code(install.get("key") or "", language=None)

    st.link_button("🌐 Prévisualiser le widget", wc.public_url(client, embed=True),
                   use_container_width=True)

    with st.expander("🤝 Instructions pour le webmaster"):
        wm = wc.webmaster_block(client)
        st.code(wm, language="text")
        st.download_button("⬇️ Télécharger les instructions webmaster", wm,
                           file_name=f"{client.get('slug')}_webmaster.txt",
                           mime="text/plain", key="dl_wm")

    st.divider()
    st.markdown("**Statut d'installation**")
    c1, c2, c3, c4 = st.columns(4)
    if c1.button("✅ Code prêt", use_container_width=True):
        cs.set_status(client.get("id"), "CODE_READY")
        st.rerun()
    if c2.button("📤 Installation en attente", use_container_width=True):
        cs.set_status(client.get("id"), "INSTALLATION_PENDING")
        st.rerun()
    if c3.button("✅ Installé", use_container_width=True):
        cs.set_status(client.get("id"), "INSTALLED")
        st.rerun()
    if c4.button("⚠️ Erreur", use_container_width=True):
        cs.set_status(client.get("id"), "ERROR")
        st.rerun()


# ───────────────────────────────────────────────────────────────────────────────
# 📘 GUIDES
# ───────────────────────────────────────────────────────────────────────────────

def render_guides_tab() -> None:
    st.markdown("### 📘 Guides — guide interactif personnalisé")
    client = _client_selector(key="adm_sel_guide", label="Client")
    if not client:
        return
    ag = client.get("agency") or {}
    install = wc.ensure_install(client)

    c1, c2 = st.columns(2)
    if c1.button("📘 Créer / régénérer le guide", type="primary", use_container_width=True):
        path = gb.generate_guide_file(client)
        cs.update_client(client.get("id"), guide={"generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
                                                  "filename": path})
        if client.get("status") in ("DRAFT", "CONFIGURED", "PREVIEW_READY"):
            cs.set_status(client.get("id"), "GUIDE_READY")
        st.success(f"✅ Guide généré : {path}")
        st.rerun()

    if c2.button("📦 Exporter le dossier client (ZIP)", use_container_width=True):
        html_str = gb.build_guide_html(client)
        kit = ck.build_kit_zip(client, html_str)
        st.download_button("⬇️ Télécharger " + ck.kit_filename(client), kit,
                           file_name=ck.kit_filename(client), mime="application/zip",
                           key="dl_kit")
        st.success("✅ Dossier client généré (aucun secret inclus).")

    guide = client.get("guide") or {}
    if guide.get("filename"):
        st.markdown(f"_Guide généré le {guide.get('generated_at') or '—'} — "
                    f"`{guide.get('filename') or ''}`_")
        try:
            with open(guide["filename"], "r", encoding="utf-8") as f:
                html_str = f.read()
        except OSError:
            html_str = gb.build_guide_html(client)
        st.download_button("⬇️ Télécharger le guide (HTML)", html_str,
                           file_name="client_guide.html", mime="text/html", key="dl_guide")
        _render_html_preview(html_str, height=760)
    else:
        st.info("Cliquez sur « Créer le guide » pour générer le guide interactif.")

    st.divider()
    st.markdown("#### ✏️ Instructions des plateformes (modifiables sans coder)")
    st.caption("Le contenu est enregistré dans guides_content.json — les modifications "
               "s'appliquent aux prochains guides générés.")
    content = gc.load_content()
    with st.expander("🔧 Modifier le contenu du guide", expanded=False):
        with st.form("guide_content_form"):
            platforms = dict(content.get("platforms") or {})
            for pkey in ("wordpress", "wix", "webflow", "custom"):
                pdata = dict(platforms.get(pkey) or {})
                with st.expander(f"{pdata.get('icon', '')} {pdata.get('title', pkey)}"):
                    steps = []
                    for i, s in enumerate(pdata.get("steps") or []):
                        s = dict(s)
                        c1, c2 = st.columns([1, 3])
                        t = c1.text_input(f"Titre {i+1}", value=s.get("t", ""), key=f"gc_{pkey}_{i}_t")
                        d = c2.text_area(f"Texte {i+1}", value=s.get("d", ""), key=f"gc_{pkey}_{i}_d")
                        steps.append({"t": (t or "").strip(), "d": (d or "").strip(),
                                      "help": s.get("help", ""), "code": s.get("code", False)})
                    pdata["steps"] = steps
                    platforms[pkey] = pdata
            if st.form_submit_button("💾 Enregistrer les instructions", type="primary",
                                     use_container_width=True):
                content["platforms"] = platforms
                gc.save_content(content)
                st.success("✅ Instructions enregistrées (guides_content.json).")
                st.rerun()


def _render_html_preview(html_str: str, height: int = 760) -> None:
    try:
        import streamlit.components.v1 as components
    except Exception:
        components = None
    if components is None:
        st.caption("(Prévisualisation indisponible dans cet environnement.)")
        return
    st.markdown("**Aperçu du guide :**")
    components.html(html_str, height=height, scrolling=True)


# ───────────────────────────────────────────────────────────────────────────────
# ⚙️ PARAMÈTRES (dont Google Sheets existant)
# ───────────────────────────────────────────────────────────────────────────────

def render_settings_tab(sheets_load_config, sheets_save_config, test_sheets_connection,
                        default_gdrive_key: str, admin_password_set: bool) -> None:
    st.markdown("### ⚙️ Paramètres")

    with st.expander("📗 Google Sheets (stockage optionnel des leads)", expanded=True):
        st.markdown("_Les leads sont **toujours** sauvegardés en local (`leads.csv`) et, si vous configurez "
                    "Google Sheets, **aussi** poussés en temps réel (feuille `Leads` créée automatiquement)._")
        s_cfg = sheets_load_config()
        with st.form("sheets_form_settings"):
            srv_json = st.text_area(
                "Clé JSON du service account (collez le contenu complet du fichier .json)",
                value=s_cfg.get("service_account", ""), height=140,
                help="Google Cloud Console → IAM & Admin → Comptes de service → Créer clé → JSON.")
            sh_key = st.text_input("ID ou URL du spreadsheet Google Sheets",
                                   value=s_cfg.get("spreadsheet", default_gdrive_key or ""),
                                   key="st_sh_key")
            c1, c2 = st.columns(2)
            save_b = c1.form_submit_button("💾 Enregistrer", use_container_width=True)
            test_b = c2.form_submit_button("🔌 Tester la connexion", use_container_width=True)
        if save_b or test_b:
            sheets_save_config({"service_account": (srv_json or "").strip(),
                                "spreadsheet": (sh_key or "").strip()})
        if save_b:
            st.success("✅ Configuration Google Sheets enregistrée.")
        if test_b:
            ok, msg = test_sheets_connection(service=(srv_json or "").strip(),
                                             sheet_ref=(sh_key or "").strip())
            (st.success if ok else st.error)(msg)

    with st.expander("🗄️ Stockage & fichiers", expanded=False):
        st.markdown(
            "**Fichiers de données :**\n"
            "- `clients.json` — dossiers clients (id, statut, config)\n"
            "- `agencies.json` — fiches agences (moteur existant, synchronisé automatiquement)\n"
            "- `leads.csv` — leads réels · `test_leads.csv` — leads de prévisualisation (TEST)\n"
            "- `alerts.log` — alertes · `guides_content.json` — contenu du guide\n"
            "- `guides/` — guides HTML générés par client")

    with st.expander("🔐 Sécurité", expanded=False):
        if admin_password_set:
            st.success("Le mot de passe admin est personnalisé.")
        else:
            st.error("⚠️ Le mot de passe admin est **encore la valeur par défaut** (`admin123`). "
                     "Changez `ADMIN_PASSWORD` dans `.env` ou les secrets Streamlit Cloud.")
        st.markdown("Le backend n'expose **jamais** de secrets : les exports clients et guides "
                    "ne contiennent ni mot de passe, ni clé API.")
