# 🏡 MaisonNova Engine v2

Moteur de **qualification de leads immobilier** en Streamlit + Gemini, devenu un
**outil interne professionnel de création et de préparation de chatbots immobiliers**
pour vos clients.

| Interface | Accès | Description |
|---|---|---|
| 🏢 **ADMIN** | page d'accueil (protégée) | Gestion **clients** (dossier complet, statut), configuration en 8 étapes, chatbots, prévisualisation (mode TEST), installation, guide interactif, leads, alertes, paramètres. |
| 💬 **PROSPECT** | `/?agency=slug-agence` | Chat « style Apple » : IA, 5 questions personnalisables, scoring en temps réel, bouton doré Calendly si `score ≥ seuil`. |

> ✅ **Rien n'a été supprimé** : scoring déterministe, Gemini (+ repli), fallback
> sans IA, Calendly, Google Sheets, CSV, iframe et smoke tests sont conservés.
> La v2 est une **évolution progressive** : les agences existantes sont migrées
> automatiquement vers le dossier clients (`clients.json`), et `agencies.json`
> reste synchronisé pour ne jamais casser le moteur.

---

## 🚀 Démarrage rapide

```bash
pip install -r requirements.txt
cp .env.example .env            # → renseigner GEMINI_API_KEY + changer ADMIN_PASSWORD
streamlit run app.py
```

1. **Admin → 🏢 Clients** → « Nouveau client » (nom, responsable, email).
2. **🛠 Configuration** : parcours en 8 étapes (Agence → Activité → Parcours →
   Qualification → Assistant → Rendez-vous → Apparence → Résumé).
3. **🤖 Chatbots** : activez Achat / Vente / Location / Investissement, personnalisez
   questions, points et seuil.
4. **👁 Prévisualisation** : testez le chat (les leads sont marqués **TEST**, jamais
   mélangés aux leads réels).
5. **📦 Installation** : URL, iframe, code d'installation, identifiant, clé.
6. **📘 Guides** : générez le **guide interactif** du client + exportez son dossier (ZIP).
7. **📊 Leads / 🔔 Alertes** : suivi en temps réel (comme avant).

> **Sans clé Gemini** : l'application fonctionne en mode dégradé (messages modèles +
> scoring par règles) — l'admin et le guide restent 100 % utilisables.

---

## 🗂️ Nouvelle structure (v2)

```
app.py                 # moteur + interfaces (routing, prospect, admin)
clients_store.py       # dossier clients (clients.json, statuts, migration, sync agencies.json)
chatbot_config.py      # parcours, questions, points, seuil par client (défaut = moteur actuel)
ai_provider.py         # couche IA (Gemini + repli + mode dégradé)
widget_code.py         # URL, iframe, code d'installation, identifiant, clé, bloc webmaster
guide_content.py       # instructions plateformes / FAQ / dépannage — modifiables sans coder
guide_builder.py       # génération du guide interactif HTML (client_guide.html)
client_kit.py          # export du dossier client (MaisonNova_<slug>_Client_Kit.zip)
admin_views.py         # nouveaux onglets admin (UI Streamlit)
site_extractor.py      # extraction auto des infos depuis l'URL du site client
send_client_kit.py     # CLI : génère le kit de livraison d'un client (guide + ZIP + email)
smoke_test.py          # 26 scénarios, fichiers temporaires isolés
```

Fichiers de données : `clients.json` (nouveau, source maître) · `agencies.json`
(synchronisé) · `leads.csv` (réels) · `test_leads.csv` (TEST) · `alerts.log` ·
`guides_content.json` · `guides/` (guides HTML générés).

---

## 🏢 Clients & statuts

Chaque client possède : `agency_id` (ex. `agency_8F29A`), **slug** (`/?agency=…`),
statut et date de création.

Parcours de statuts :
`DRAFT → CONFIGURED → PREVIEW_READY → CODE_READY → GUIDE_READY → INSTALLATION_PENDING → INSTALLED` (+ `ERROR`).

Le dashboard affiche les étapes du dossier :
`Dupont Immobilier · ✅ Configuration ✅ Chatbot ✅ Code ✅ Guide 🟡 Installation`.

## 🛠 Configuration en 8 étapes

1. **Agence** (nom, ville, pays, adresse, email, téléphone, site, logo)
2. **Activité** (description, slogan, services, zones, types de biens, horaires)
3. **Parcours clients** (Achat / Vente / Location / Investissement + parcours principal)
4. **Qualification** (seuil + points par critère, par agence)
5. **Assistant** (nom, ton, message d'accueil personnalisé)
6. **Rendez-vous** (Calendly, email d'alerte)
7. **Apparence** (couleurs principale / secondaire — thème du chat prospect)
8. **Résumé** (validation → statut CONFIGURED)

Chaque étape s'enregistre indépendamment (pas de formulaire géant) et l'admin voit
d'un coup d'œil ce qui est fait (✅ / ⬜).

## 🤖 Chatbots flexibles

- **Activés par défaut** : à la création d'un client, les parcours Achat / Vente /
  Location / Investissement sont **tous activés** avec les 5 questions du moteur —
  le chatbot est opérationnel immédiatement, sans aucune étape d'activation.
- Par parcours : questions (texte + libellé, ordre), points, seuil, message.
- Le parcours principal pilote le chat prospect ; sans configuration, le moteur
  actuel (5 questions, tables de points, seuil 70) s'applique — **aucune régression**.

## ⚡ Création rapide depuis le site du client

Au lieu de faire remplir un formulaire au client, collez **l'URL de son site** :

- **🏢 Clients → « ⚡ Création rapide depuis le site »** : l'outil télécharge la page
  et extrait automatiquement nom, description, coordonnées (email/tél), ville,
  services (Achat/Vente/Location…), types de biens, zones, horaires et logo
  (og:image) → crée le dossier et pré-remplit la configuration.
- **🛠 Configuration (étapes 1 et 2)** : bouton « 🔍 Analyser le site et remplir »
  pour compléter l'agence ou l'activité en un clic.
- Extraction par **règles** (instantanée, sans réseau externe requis côté client)
  + **affinage IA** (Gemini) si une clé est configurée (`site_extractor.py`).

## 🗑️ Leads : suppression facile

**📊 Leads** → section « Supprimer un lead » : choisissez le lead dans la liste et
supprimez-le (avec confirmation). Les **leads de TEST** ont leur propre liste et un
bouton « Tout effacer ». Le fichier CSV reste propre (en-têtes conservés).

## 📊 Scoring (max 100 pts — conservé)

| Question | Points par défaut (personnalisables) |
|---|---|
| Projet | maison 20 · appartement 18 · investissement 16 · terrain 12 · autre 10 |
| Budget | ≥600k → 25 · 400-600k → 22 · 250-400k → 16 · 150-250k → 10 · <150k → 5 |
| Ville | même ville que l'agence → 15 · autre ville → 10 |
| Financement | prêt pré-accordé 25 · comptant 20 · à prévoir 12 · aucun 5 |
| Délai | <6 mois 15 · 6-12 → 12 · 12-24 → 8 · flexible 5 |

`score_profile()` et le fallback déterministe sont intacts ; chaque agence peut
avoir ses propres points et seuil.

## 👁 Prévisualisation (mode TEST)

Sélectionnez une agence → le chat s'affiche dans l'admin. **Mode test activé par
défaut** : les leads de test sont écrits dans `test_leads.csv` avec `source=test`,
jamais poussés vers Google Sheets, jamais notifiés. Bouton « 🔄 Nouvelle conversation ».

## 📦 Installation (kit de code)

Pour chaque agence, généré automatiquement :
- **A.** URL publique · **B.** iframe · **C.** code d'installation (div + script)
- **D.** identifiant agence · **E.** clé d'installation

Boutons COPIER (intégrés), TÉLÉCHARGER et PRÉVISUALISER. Le bloc
« Instructions pour mon webmaster » (agence, site, identifiant, code, emplacement,
test attendu) est aussi téléchargeable. **Le backend n'expose jamais de secrets.**

**🔗 Lien de démonstration à partager** : en tête de l'onglet Installation, l'URL
publique du chatbot avec « 🌐 Ouvrir / tester en ligne » et un fichier `.url`
prêt à envoyer — parfait pour la démo ou la validation client (aucun mot de passe).
Le dashboard 🏢 Clients affiche aussi « 🌐 Ouvrir le chatbot » sur chaque fiche.

## 📘 Guide d'installation interactif (⭐ nouveauté majeure)

Un **vrai guide web interactif** (HTML autonome, CSS/JS inclus), généré depuis les
infos de l'agence :

- écran d'accueil personnalisé (logo, agence, site, progression %) ;
- choix de plateforme : **WordPress / Wix / Webflow / Site personnalisé / Je ne sais pas** ;
- « Je ne sais pas » → détection automatique (heuristique URL) → sinon
  « géré par un webmaster » ou « site personnalisé » ;
- étapes par plateforme, numérotées, avec aide contextuelle et bouton
  **« Je suis bloqué »** ;
- dépannage interactif : problème → cause → solution → test → si ça ne marche toujours pas ;
- FAQ en accordéons (sans jargon) ;
- bloc **webmaster** copiable ;
- checklist finale « Tester mon installation » → **Installation terminée ✅** ;
- progression sauvegardée localement (localStorage) → reprise où on s'est arrêté.

Le contenu des instructions (plateformes, FAQ, dépannage) est **data-driven**
(`guide_content.py` + `guides_content.json`) : modifiable depuis l'admin, onglet
**Guides**, sans réécrire le code. Le guide se télécharge (`client_guide.html`),
se partage et se prévisualise dans l'admin.

Les textes sont rédigés pour une personne **sans aucune connaissance technique**
(clic par clic, exemples, « c'est l'étape qu'on oublie le plus souvent », aide
contextuelle) et le **ZIP du dossier client contient un `LISEZ-MOI.txt`** : il
explique en langage simple ce que contient le dossier, par où commencer (ouvrir
`guide/client_guide.html`), que faire si on est bloqué et les règles de sécurité.

## 📦 Export du dossier client

`📦 Exporter dossier client` → **`MaisonNova_<slug>_Client_Kit.zip`** contenant :
`client_info/` · `configuration/` · `widget/` · `code/` · `guide/` ·
`instructions_webmaster/`. **Jamais** de mots de passe, clés API ou secrets serveur.

## 🤖 Moteur IA (Gemini — conservé)

- Modèles essayés dans l'ordre : `gemini-flash-latest` (défaut) → `gemini-3.5-flash`
  → `gemini-3.1-flash-lite` → `gemini-flash-lite-latest` (repli automatique).
- Couche propre **AIProvider** (`ai_provider.py`) : si `GEMINI_API_KEY` est absent,
  l'application continue en mode dégradé — elle n'est jamais inutilisable.
- Accueil, questions adaptées, extraction JSON du profil, synthèse de clôture.
- Repli 100 % règles (regex françaises) si l'API est indisponible.

## 🧩 Embed iframe (conservé)

Dans l'admin, onglet **📦 Installation** → « B. iframe » :

```html
<iframe src="https://votre-app.fr/?agency=maisonnova-lyon&embed=1"
        width="460" height="620" style="border:none; border-radius:16px;"
        title="Qualification" loading="lazy"></iframe>
```

## 🗄️ Stockage

- **Par défaut** : CSV local — `leads.csv` (UTF-8 BOM, Excel) + `test_leads.csv` (TEST).
- **Optionnel** : Google Sheets via `gspread` (onglet **⚙️ Paramètres** — fonctionnalité
  existante conservée) ; chaque lead réel est poussé en temps réel dans la feuille `Leads`.

## 🔔 Notifications (conservées)

Lead **qualifié** → alerte dans `alerts.log` + affichage admin. Vrai e-mail si
`SMTP_*` renseigné. Les leads de prévisualisation (TEST) ne déclenchent rien.

## 🚢 Déploiement (Streamlit Community Cloud)

Même procédure qu'avant : dépôt GitHub → New app (`app.py`) → Secrets TOML
(`ADMIN_PASSWORD`, `GEMINI_API_KEY`, `APP_BASE_URL`, optionnellement Google Sheets / SMTP).

> ⚠️ `leads.csv` / `clients.json` sont **locaux à l'instance** : activez Google Sheets
> pour un stockage durable en production.

## 🧪 Tests

```bash
python smoke_test.py
```

26 scénarios : boot prospect + admin, slugify, extraction/scoring (97/100), profil
faible, lead CSV + alerte, Google Sheets, création/modification client, config
chatbot (points/seuil), code d'installation, contenu du guide, guide interactif
(WordPress/Wix/Webflow/custom + « je ne sais pas »), export guide, export ZIP
(+ `LISEZ-MOI.txt`), **mode test sans vrai lead**, statuts, parcours prospect
complet, **extraction auto depuis le site web** (règles + og:site_name + ville +
erreurs réseau), **suppression de lead**, **chatbot activé par défaut**, **suppression
client effective** (agencies.json resynchronisé, guide nettoyé), **troncature IA
→ repli lisible**, **chatbot actif même si tout est désactivé**, **réparation auto
des dossiers (clé ≠ id)**. Tous les tests s'exécutent sur des fichiers temporaires
isolés : **aucune donnée fictive n'est laissée dans la production**.

## 🎨 Design & expérience

Identité premium conservée : **Inter + Playfair Display**, fond blanc, aurora dorée,
glassmorphism, chat iMessage, CTA doré shimmer. Nouveautés :

- **Zéro filigrane Streamlit** : menu, footer « Made with Streamlit », toolbar et
  bouton Deploy sont entièrement masqués côté prospect (et admin) — rendu 100 % propre.
- **Avatar robot humanisé** : petit robot souriant doré (SVG embarqué, aucune
  dépendance) remplace l'emoji 🤖 — chaleureux, sans être une personne.
- **Réponses plus rapides** : un seul appel IA par tour de conversation (l'extraction
  de profil est faite par règles instantanées ; l'appel IA unique n'a lieu qu'à la
  clôture) et **textes complets** : limites de tokens relevées + consignes
  « jamais tronqué » dans les prompts.
- **Discussions humanisées** : les prompts d'accueil, questions et clôture ont un
  ton plus naturel et bienveillant (prénom cité, formulation adaptée).
- Les couleurs de chaque client personnalisent son chat (via variables CSS, sans
  régression).
