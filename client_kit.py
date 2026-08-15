# -*- coding: utf-8 -*-
"""Export du DOSSIER CLIENT en ZIP (MaisonNova_{slug}_Client_Kit.zip).

Contenu :
  /client_info              → résumé non sensible + fiche agence
  /configuration            → configuration chatbot (questions, points, seuil)
  /widget                   → iframe + code d'installation
  /code                     → code complet + clé + identifiant
  /guide                    → client_guide.html (guide interactif)
  /instructions_webmaster   → bloc technique webmaster

Jamais inclus : mots de passe, clés API, secrets serveur, identifiants sensibles.
"""

import io
import json
import zipfile

import clients_store
import widget_code


def kit_filename(client: dict) -> str:
    slug = client.get("slug") or "client"
    return f"MaisonNova_{slug}_Client_Kit.zip"


def build_kit_zip(client: dict, guide_html: str, code: str | None = None,
                  webmaster: str | None = None) -> bytes:
    code = code or widget_code.full_install_code(client)
    webmaster = webmaster or widget_code.webmaster_block(client)
    ag = client.get("agency") or {}
    chatbot = client.get("chatbot") or {}

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        # 0. guide de démarrage (à lire en premier, langage non technique)
        z.writestr("LISEZ-MOI.txt", _readme_txt(client, code, webmaster))

        # 1. informations client (non sensibles)
        z.writestr("client_info/fiche.json",
                   json.dumps(widget_code.kit_summary(client), ensure_ascii=False, indent=2))
        z.writestr("client_info/agence.txt",
                   f"Agence        : {ag.get('name') or ''}\n"
                   f"Ville         : {ag.get('city') or ''}\n"
                   f"Email         : {ag.get('email') or ''}\n"
                   f"Identifiant   : {client.get('id') or ''}\n"
                   f"Slug          : {client.get('slug') or ''}\n"
                   f"Statut        : {client.get('status') or ''}\n"
                   f"URL publique  : {widget_code.public_url(client)}\n")

        # 2. configuration
        z.writestr("configuration/chatbot.json",
                   json.dumps(chatbot, ensure_ascii=False, indent=2))
        z.writestr("configuration/seuil.txt",
                   f"Seuil de qualification : {ag.get('threshold', 70)}/100\n"
                   f"Calendly               : {ag.get('calendly_url') or ''}\n")

        # 3. widget
        z.writestr("widget/iframe.txt", widget_code.iframe_snippet(client))
        z.writestr("widget/script.txt", widget_code.script_snippet(client))

        # 4. code + identifiants
        z.writestr("code/installation.txt", code)
        z.writestr("code/identifiants.txt",
                   f"Identifiant agence     : {client.get('id') or ''}\n"
                   f"Clé d'installation     : {(client.get('install') or {}).get('key') or ''}\n"
                   f"URL du widget          : {widget_code.install_url(client)}\n")

        # 5. guide interactif
        z.writestr("guide/client_guide.html", guide_html)

        # 6. instructions webmaster
        z.writestr("instructions_webmaster/webmaster.txt", webmaster)
    return buf.getvalue()


def _readme_txt(client: dict, code: str, webmaster: str) -> str:
    """Guide d'utilisation du dossier (LISEZ-MOI.txt), rédigé pour une personne
    sans aucune connaissance technique."""
    ag = client.get("agency") or {}
    slug = client.get("slug") or "client"
    return (
        "════════════════════════════════════════════════════════════════════\n"
        "  BIENVENUE DANS VOTRE DOSSIER MAISONNOVA AI\n"
        "  Agence : " + (ag.get("name") or "") + "\n"
        "════════════════════════════════════════════════════════════════════\n\n"
        "Ce dossier contient tout ce qu'il faut pour mettre en ligne votre\n"
        "assistant de qualification immobilière. Pas besoin de connaissances\n"
        "techniques : suivez simplement les étapes ci-dessous.\n\n"
        "━━━ COMMENT FAIRE (en 3 étapes) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "1. OUVREZ LE GUIDE INTERACTIF\n"
        "   Double-cliquez sur le fichier :\n"
        "       guide\\client_guide.html\n"
        "   Il s'ouvre dans votre navigateur internet. C'est un guide pas à pas\n"
        "   qui vous montre EXACTEMENT quoi faire, avec des boutons à cliquer.\n\n"
        "2. CHOISISSEZ VOTRE PLATEFORME\n"
        "   Le guide vous demande sur quel site votre assistant doit apparaître\n"
        "   (WordPress, Wix, Webflow, site personnalisé…). Cliquez sur votre\n"
        "   plateforme : seules les étapes utiles s'affichent.\n"
        "   • Vous ne savez pas ? Cliquez sur « Je ne sais pas » : le guide vous\n"
        "     aide à le découvrir, ou choisissez « Mon site est géré par un\n"
        "     webmaster » pour confier l'installation.\n\n"
        "3. SUIVEZ LES ÉTAPES ET TESTEZ\n"
        "   Chaque étape a un bouton « J'ai fait cette étape » : votre progression\n"
        "   est sauvegardée automatiquement, vous pouvez fermer et reprendre.\n"
        "   À la fin, le guide vérifie avec vous que tout fonctionne.\n\n"
        "━━━ CONTENU DU DOSSIER ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "  • LISEZ-MOI.txt ....... ce fichier (à lire en premier)\n"
        "  • guide/ .............. le guide interactif à ouvrir (client_guide.html)\n"
        "  • code/ ............... le code d'installation + vos identifiants\n"
        "  • widget/ ............. le code simple (iframe) pour vos équipes\n"
        "  • configuration/ ...... votre configuration (seuil, questions)\n"
        "  • client_info/ ........ une fiche récapitulative de votre dossier\n"
        "  • instructions_webmaster/ .... à transmettre à la personne qui gère\n"
        "        votre site si vous ne le gérez pas vous-même\n\n"
        "━━━ SI VOUS ÊTES BLOQUÉ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "  • Dans le guide, cliquez sur « Je suis bloqué » : les problèmes les\n"
        "    plus courants y sont expliqués simplement.\n"
        "  • Vous travaillez avec un webmaster ? Ouvrez le guide, choisissez\n"
        "    « Je travaille avec un webmaster », puis cliquez sur\n"
        "    « COPIER LES INSTRUCTIONS POUR MON WEBMASTER » et envoyez-les-lui.\n"
        "  • Besoin d'aide ? Écrivez à : " + (ag.get("email") or "votre conseiller") + "\n\n"
        "━━━ SÉCURITÉ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "  • Ne partagez JAMAIS votre mot de passe de site avec qui que ce soit.\n"
        "  • Votre identifiant agence (" + (client.get("id") or "") + ") et votre clé\n"
        "    d'installation sont à vous : le code les contient déjà, vous n'avez\n"
        "    rien à saisir à la main.\n\n"
        "  Bonne installation ! 🎉\n"
    )
