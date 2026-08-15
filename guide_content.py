# -*- coding: utf-8 -*-
"""Contenu du guide interactif — 100 % data-driven.

Les instructions WordPress / Wix / Webflow / Site personnalisé, la FAQ et le
dépannage sont définis ici par défaut et peuvent être modifiés SANS réécrire le
code : ils sont enregistrés dans guides_content.json (éditable depuis l'admin,
onglet Guides).

Les procédures restent volontairement génériques et exactes (aucune étape
inventée) : on installe toujours le widget via un bloc HTML / Embed standard.
"""

import json
import os

DEFAULT_FILE = "guides_content.json"


def _file() -> str:
    return os.getenv("GUIDES_CONTENT_FILE", DEFAULT_FILE)


DEFAULT_PLATFORMS = {
    "wordpress": {
        "title": "WordPress",
        "icon": "🔵",
        "intro": "Votre site fonctionne avec WordPress. Suivez ces étapes, une par une :",
        "steps": [
            {"t": "Connectez-vous à votre site",
             "d": "Ouvrez votre navigateur internet (Chrome, Firefox, Edge…). Tapez l'adresse de votre site suivie de /wp-admin (exemple : votresite.fr/wp-admin) puis appuyez sur Entrée. Une page de connexion s'affiche : entrez votre identifiant et votre mot de passe, puis cliquez sur « Se connecter ».",
             "help": "Vos identifiants vous ont été envoyés par votre hébergeur ou par la personne qui a créé votre site. Si vous ne les avez pas, cliquez sur « Je suis bloqué »."},
            {"t": "Ouvrez la page où afficher l'assistant",
             "d": "Regardez le menu à gauche de l'écran. Cliquez sur « Pages ». Cliquez ensuite sur le nom de votre page d'accueil (souvent « Accueil ») pour l'ouvrir.",
             "help": "Vous pouvez aussi créer une nouvelle page en cliquant sur « Ajouter » en haut de la liste des pages."},
            {"t": "Ajoutez un bloc « HTML personnalisé »",
             "d": "Dans l'écran de modification de la page, cliquez sur le bouton « + » (en haut à gauche). Tapez le mot « HTML » dans la barre de recherche. Cliquez sur « HTML personnalisé » : un bloc vide apparaît sur la page.",
             "help": "Un « bloc » est un encart dans votre page. Ici on ajoute un bloc spécial qui accepte du code — c'est normal qu'il paraisse vide au départ."},
            {"t": "Collez le code",
             "d": "Cliquez sur le bouton « COPIER LE CODE » ci-dessous. Revenez sur votre page, faites un clic droit dans le bloc vide et choisissez « Coller ». Cliquez ensuite sur le bouton « Mettre à jour » (ou « Publier ») en haut à droite.",
             "help": "Le code est le bloc entre <!-- MaisonNova AI --> et </script>. Collez-le EN ENTIER, d'un seul coup, sans rien modifier."},
            {"t": "Vérifiez la clé d'installation",
             "d": "La clé d'installation est déjà incluse dans le code que vous avez collé : vous n'avez rien à saisir à la main.",
             "help": "Votre clé : %%KEY%%. Si la page affiche une erreur, recollez le code tel quel (il a peut-être été coupé)."},
            {"t": "Testez",
             "d": "Ouvrez votre site dans une nouvelle fenêtre (ou demandez à quelqu'un d'autre de l'ouvrir). Le chat doit apparaître et répondre à vos messages.",
             "help": "Le widget s'affiche et répond ? Passez à l'étape suivante. Sinon, cliquez sur « Je suis bloqué »."},
        ],
        "help_link": "Je n'arrive pas à trouver le bouton « + » ou « HTML »",
    },
    "wix": {
        "title": "Wix",
        "icon": "🟣",
        "intro": "Votre site est créé avec Wix. Suivez ces étapes, une par une :",
        "steps": [
            {"t": "Connectez-vous à votre compte Wix",
             "d": "Ouvrez votre navigateur et allez sur fr.wix.com. Cliquez sur « Connexion » en haut à droite, entrez votre adresse e-mail et votre mot de passe.",
             "help": "Si vous ne vous souvenez plus de votre mot de passe, cliquez sur « Mot de passe oublié » sur la page de connexion."},
            {"t": "Ouvrez l'éditeur de votre site",
             "d": "Dans votre tableau de bord Wix, trouvez votre site et cliquez sur « Modifier le site » (ou l'icône en forme de crayon). L'éditeur s'ouvre avec votre page à l'écran.",
             "help": "L'éditeur est l'écran où l'on modifie le site : on y voit la page et un menu à gauche."},
            {"t": "Ajoutez un élément « Code embarqué »",
             "d": "Dans le menu à gauche de l'éditeur, cliquez sur « + Ajouter ». Puis sur « Intégrations » (ou « Embarquer »), puis sur « Code embarqué ». Un encart apparaît sur la page.",
             "help": "Sur certains éditeurs Wix, le chemin est : « + » → « Autres » → « Code embarqué »."},
            {"t": "Collez le code",
             "d": "Cliquez sur « COPIER LE CODE » ci-dessous. Cliquez ensuite sur l'encart « Code embarqué », cliquez sur « Entrer le code », collez le code, puis cliquez sur « Mettre à jour ».",
             "help": "Collez le code EN ENTIER, entre <!-- MaisonNova AI --> et </script>, sans rien modifier."},
            {"t": "Publiez votre site",
             "d": "Cliquez sur « Publier » en haut à droite de l'éditeur, puis sur « Publier maintenant ».",
             "help": "Tant que vous ne publiez pas, vos changements ne sont pas visibles sur votre site en ligne. C'est l'étape qu'on oublie le plus souvent !"},
            {"t": "Testez",
             "d": "Ouvrez votre site en ligne : le chat doit apparaître et répondre à vos messages.",
             "help": "Besoin d'aide ? Cliquez sur « Je suis bloqué »."},
        ],
        "help_link": "Je ne trouve pas « Code embarqué »",
    },
    "webflow": {
        "title": "Webflow",
        "icon": "🔷",
        "intro": "Votre site est construit avec Webflow. Suivez ces étapes, une par une :",
        "steps": [
            {"t": "Connectez-vous au Designer",
             "d": "Ouvrez votre navigateur et allez sur webflow.com. Connectez-vous, puis ouvrez votre projet : l'éditeur visuel (le « Designer ») s'affiche.",
             "help": "Le Designer est l'écran où l'on modifie le site : la page au centre, les réglages à droite."},
            {"t": "Ouvrez la page concernée",
             "d": "Dans le panneau de gauche, cliquez sur « Pages » puis sur le nom de la page (Accueil, Contact…) où vous voulez l'assistant.",
             "help": "Cliquez sur « Pages » en haut à gauche si le panneau n'est pas visible."},
            {"t": "Ajoutez un élément « Embed »",
             "d": "Dans le panneau « Ajouter » (à gauche), tapez « Embed » dans la recherche, puis faites glisser l'élément « Embed » sur votre page.",
             "help": "L'élément s'appelle aussi « Embed Code » ou « Code embarqué »."},
            {"t": "Collez le code",
             "d": "Cliquez sur « COPIER LE CODE » ci-dessous. Cliquez ensuite dans l'élément « Embed » sur votre page, collez le code, puis cliquez en dehors pour valider.",
             "help": "Collez le code EN ENTIER, entre <!-- MaisonNova AI --> et </script>, sans rien modifier."},
            {"t": "Publiez votre site",
             "d": "Cliquez sur « Publish » (en haut à droite), puis sur « Publish to selected domain » pour mettre le site en ligne.",
             "help": "Sans cette étape de publication, le widget n'apparaîtra pas sur votre site en ligne."},
            {"t": "Testez",
             "d": "Ouvrez votre site en ligne : le chat doit apparaître et répondre à vos messages.",
             "help": "Besoin d'aide ? Cliquez sur « Je suis bloqué »."},
        ],
        "help_link": "Je ne trouve pas l'élément « Embed »",
    },
    "custom": {
        "title": "Site personnalisé",
        "icon": "🛠️",
        "intro": "Voici votre code. Copiez-le exactement tel qu'il apparaît, sans rien modifier.",
        "steps": [
            {"t": "Copiez votre code d'installation",
             "d": "Cliquez sur le bouton « COPIER LE CODE » ci-dessous : le code est copié dans votre presse-papiers. Ne modifiez rien, gardez-le tel quel.",
             "code": True,
             "help": "Ce code se retrouve aussi dans le dossier, dossier « code », fichier installation.txt, et dans le bloc « Instructions pour mon webmaster »."},
            {"t": "Collez-le dans votre page",
             "d": "Ouvrez le fichier de votre page (ou l'outil de votre site qui accepte le code) et collez le code juste avant la fin de la page, de préférence avant </body>.",
             "help": "« Je ne sais pas où le mettre » ? Cliquez sur « Je travaille avec un webmaster » : des instructions prêtes à envoyer s'afficheront."},
            {"t": "Vérifiez la clé d'installation",
             "d": "La clé est déjà incluse dans le code copié : vous n'avez rien à saisir. Votre clé : %%KEY%%.",
             "help": "Elle permet d'identifier votre installation ; gardez-la précieusement."},
            {"t": "Testez",
             "d": "Ouvrez la page en ligne : le chat doit apparaître et répondre à vos messages.",
             "help": "Besoin d'aide ? Cliquez sur « Je suis bloqué »."},
        ],
        "help_link": "Je ne sais pas où coller le code",
    },
}

DEFAULT_FAQ = [
    {"q": "Qu'est-ce qu'un widget ?",
     "a": "Un widget est un petit module affiché sur votre site. Ici, c'est la fenêtre de chat qui qualifie vos visiteurs. Elle apparaît dans un cadre intégré à votre page — vos visiteurs n'ont rien à installer."},
    {"q": "Qu'est-ce qu'un script / un code ?",
     "a": "C'est une petite portion de code (HTML + JavaScript) qui affiche le widget. Vous n'avez rien à comprendre : il suffit de le copier et de le coller là où le guide vous indique."},
    {"q": "Dois-je donner mon mot de passe ?",
     "a": "Non, jamais. Vous n'avez besoin que de vos identifiants de votre propre site (WordPress, Wix, Webflow…). Ne partagez jamais votre mot de passe avec qui que ce soit."},
    {"q": "Mon site va-t-il être modifié ?",
     "a": "Non. Le code ajoute uniquement le widget : il ne modifie pas vos pages, vos textes ni vos photos. Vous pouvez le retirer à tout moment en supprimant le bloc que vous avez collé."},
    {"q": "Le chatbot fonctionne-t-il sur mobile ?",
     "a": "Oui. Le widget s'adapte automatiquement à la taille de l'écran (ordinateur, tablette, téléphone)."},
    {"q": "Que faire si j'ai un webmaster ?",
     "a": "Transmettez-lui le bloc « Instructions pour mon webmaster » : il contient tout ce dont il a besoin (identifiant, code, emplacement recommandé, test attendu)."},
]

DEFAULT_ISSUES = {
    "not_visible": {
        "label": "Je ne vois pas le widget",
        "cause": "Le code n'a pas été enregistré / publié, ou il a été collé dans la mauvaise page.",
        "solution": "Vérifiez que vous avez bien cliqué sur « Mettre à jour » / « Publier ». Contrôlez que le bloc est sur la page que vous consultez.",
        "test": "Ouvrez la page dans un onglet privé (ou videz le cache) et rechargez.",
        "still": "Contactez votre conseiller en précisant : plateforme, page où le code a été collé, et si la page est publiée."},
    "code_not_working": {
        "label": "Le code ne fonctionne pas",
        "cause": "Le code a été modifié, coupé, ou collé en plusieurs morceaux.",
        "solution": "Supprimez le bloc et recollez le code d'installation complet, en une seule fois, exactement tel qu'il apparaît.",
        "test": "Rechargez la page et vérifiez que le widget apparaît.",
        "still": "Envoyez le bloc d'instructions webmaster à la personne qui gère votre site."},
    "where_to_paste": {
        "label": "Je ne trouve pas où coller le code",
        "cause": "Chaque plateforme a son emplacement (bloc HTML, Embed…).",
        "solution": "Revenez au guide et choisissez votre plateforme : les étapes indiquent l'emplacement exact. Si vous hésitez, transmettez les instructions à votre webmaster.",
        "test": "Après collage + publication, le widget doit apparaître.",
        "still": "Utilisez l'option « Je travaille avec un webmaster » et transmettez-lui le bloc technique."},
    "key_not_working": {
        "label": "La clé ne fonctionne pas",
        "cause": "La clé a été modifiée ou un ancien code est resté en cache.",
        "solution": "Recopiez le code d'installation depuis votre espace admin (onglet Installation) — la clé y est incluse automatiquement.",
        "test": "Rechargez la page après remplacement du bloc.",
        "still": "Contactez votre conseiller avec votre identifiant agence (agency_id)."},
    "widget_no_reply": {
        "label": "Le widget apparaît mais ne répond pas",
        "cause": "Connexion internet instable ou page non rechargée après publication.",
        "solution": "Rechargez la page (Ctrl+F5). Vérifiez que l'assistant est bien activé dans votre espace (statut INSTALLED).",
        "test": "Envoyez un message dans le chat : il doit répondre en quelques secondes.",
        "still": "Contactez votre conseiller avec votre identifiant agence."},
    "no_site_access": {
        "label": "Je n'ai pas accès à mon site",
        "cause": "Les identifiants sont détenus par votre webmaster ou votre agence de création.",
        "solution": "Utilisez l'option « Je travaille avec un webmaster » : transmettez-lui le bloc technique complet.",
        "test": "Le webmaster confirme que le widget est en ligne.",
        "still": "Demandez à votre conseiller de contacter le prestataire avec vous."},
    "other": {
        "label": "Autre problème",
        "cause": "Situation spécifique non couverte par le guide.",
        "solution": "Préparez : plateforme, page concernée, capture d'écran si possible.",
        "test": "—",
        "still": "Contactez votre conseiller (email en bas de cette page) en joignant la capture d'écran."},
}

VERIFY_CHECKLIST = [
    "Le widget apparaît sur ma page",
    "Le chatbot s'ouvre",
    "Les messages fonctionnent",
    "Les questions fonctionnent",
    "Le score fonctionne",
    "Le bouton de rendez-vous fonctionne",
]


# ───────────────────────────────────────────────────────────────────────────────

def load_content() -> dict:
    """Contenu = JSON (overrides) fusionné sur les défauts."""
    data = {"platforms": DEFAULT_PLATFORMS, "faq": DEFAULT_FAQ,
            "issues": DEFAULT_ISSUES, "verify": VERIFY_CHECKLIST}
    try:
        with open(_file(), "r", encoding="utf-8") as f:
            over = json.load(f)
        if isinstance(over, dict):
            for key in ("platforms", "faq", "issues", "verify"):
                if over.get(key):
                    data[key] = over[key]
    except Exception:
        pass
    return data


def save_content(data: dict) -> None:
    with open(_file(), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def reset_content() -> None:
    try:
        os.remove(_file())
    except OSError:
        pass
