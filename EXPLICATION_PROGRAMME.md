# 🏡 MaisonNova Engine v1 — Explication complète du programme

> Document rédigé le 14/08/2026. Il décrit précisément ce que fait le programme,
> tous les outils utilisés, et le fonctionnement détaillé de chaque partie.

---

## 1. Vue d'ensemble

**MaisonNova Engine v1** est un **moteur de qualification de leads immobiliers** :
une application web qui fait discuter un prospect avec un assistant IA (Google Gemini),
lui pose **5 questions ciblées**, **score son projet en temps réel (0 à 100 points)**
et déclenche automatiquement un **rendez-vous Calendly** si le score atteint le seuil
de l'agence. Chaque conversation est sauvegardée comme **lead** (CSV local + option
Google Sheets) et notifiée à l'agence (log + e-mail SMTP optionnel).

- **Langage** : 100 % Python.
- **Framework** : Streamlit (application web dans un seul fichier).
- **IA** : Google Gemini via le SDK `google-generativeai`.
- **Fichier principal** : `app.py` (1 282 lignes).

Il existe **deux interfaces**, routées par l'URL :

| Interface | Accès | Description |
|---|---|---|
| 🏢 **ADMIN** | page d'accueil (sans paramètre) | Protégée par mot de passe. Configure l'agence (nom, logo, ville, Calendly, seuil de score), tableau de bord des leads, alertes, Google Sheets, snippet iframe. |
| 💬 **PROSPECT** | `/?agency=slug-de-l-agence` | Chat minimaliste « style Apple », IA qui pose 5 questions, scoring en temps réel, bouton doré Calendly si `score ≥ seuil`. |

---

## 2. Tous les outils utilisés

### 2.1 Langage & bibliothèque standard Python

| Outil | Usage précis |
|---|---|
| `streamlit` (>= 1.37, < 2.0) | Framework web : `st.session_state`, `st.chat_message`, `st.chat_input`, `st.tabs`, `st.dataframe`, `st.query_params`, `st.form`, `st.metric`, `st.link_button`, `st.toast`, `st.rerun`, etc. |
| `google-generativeai` (>= 0.7.2) | Appels à l'IA Gemini : `genai.configure`, `genai.GenerativeModel`, `model.generate_content`, `genai.types.GenerationConfig` (temperature, max_output_tokens, response_mime_type JSON), timeout 60 s. |
| `python-dotenv` (>= 1.0.0) | Chargement optionnel du fichier `.env` (`load_dotenv`). |
| `gspread` (>= 6.0) — **optionnel** | Push des leads vers Google Sheets : `gspread.authorize`, `client.open_by_key`, `worksheet`, `append_row`. |
| `google-auth` (>= 2.0) — **optionnel** | Authentification du compte de service Google : `Credentials.from_service_account_file` / `from_service_account_info` avec 3 scopes (feeds, spreadsheets, drive). |
| `csv` | Lecture/écriture de `leads.csv` (`DictWriter`, `DictReader`), encodage UTF-8 avec BOM (`utf-8-sig`) pour Excel. |
| `json` | `agencies.json`, config Google Sheets (`sheets_config.json`), parsing des réponses JSON de l'IA. |
| `re` | Regex françaises de l'extraction de secours, slugification, nettoyage des fences markdown des réponses IA, extraction d'un ID depuis une URL Google Sheets. |
| `os` | Chemins de fichiers, existence de fichiers. |
| `datetime` | Horodatage des leads (`%Y-%m-%d %H:%M:%S`) et date de création des agences (ISO). |
| `uuid` | ID de session unique du prospect (`uuid.uuid4().hex[:10]`). |
| `logging` | Logs (`logging.basicConfig` niveau INFO, format horodaté). |
| `html` | Échappement (`html.escape`) des données avant injection dans le HTML. |
| `smtplib` + `email.mime.text` — **optionnels** | Vrai e-mail d'alerte si `SMTP_*` configuré : `SMTP`, `starttls()`, `login`, `send_message`, `MIMEText`. |
| `io` | Export CSV en mémoire (`io.StringIO`) pour `st.download_button`. |

### 2.2 Services externes

| Service | Rôle |
|---|---|
| **Google Gemini** (API, clé `GEMINI_API_KEY`) | L'IA qui anime le chat. Modèles essayés dans l'ordre avec repli automatique : `gemini-flash-latest` (défaut, suit les modèles Google actuels) → `gemini-3.5-flash` → `gemini-3.1-flash-lite` → `gemini-flash-lite-latest`. |
| **Google Sheets API** (optionnel) | Stockage secondaire des leads dans la feuille `Leads` (créée automatiquement avec les en-têtes). |
| **Calendly** (optionnel) | Simple lien externe pour le bouton doré de rendez-vous (`calendly_url` de l'agence). |
| **SMTP** (optionnel) | Envoi d'e-mails réels d'alerte si `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` sont renseignés. |
| **Google Fonts** | Typographie **Inter** (texte) + **Playfair Display** (titres), importées par CSS. |

### 2.3 Fichiers du projet

| Fichier | Rôle |
|---|---|
| `app.py` | Toute l'application : config, IA, scoring, interface admin + prospect. |
| `agencies.json` | Configuration des agences (slugs → nom, logo, ville, email, Calendly, seuil, description, URL publique, date de création). Contient actuellement 2 agences : **MaisonNova Immobilier** (Lyon) et **MaisonSilas** (Paris). |
| `leads.csv` | Stockage des leads (généré automatiquement au premier lead). |
| `alerts.log` | Alertes mail simulées (chaque lead qualifié y est écrit). |
| `sheets_config.json` | Configuration Google Sheets (créé si configuré depuis l'admin). |
| `.env` / `.env.example` | Variables d'environnement (mot de passe admin, clé Gemini, modèles, chemins de fichiers, URL publique, SMTP, Google Sheets). |
| `.streamlit/config.toml` | Thème clair premium : fond blanc `#FFFFFF`, accent doré `#C9A227`, polices, `headless = true`, statistiques désactivées, toolbar minimale. |
| `smoke_test.py` | Tests automatiques sans navigateur : crée un **stub du module streamlit**, importe et exécute `app.py` (boot prospect + admin), teste slugify, extraction par règles, scoring, écriture CSV, alerte, chemins d'erreur Google Sheets. |
| `demo-widget.html` | Page de démo qui simule le site d'une agence (ex. MaisonSilas à Paris) avec le **widget iframe** intégré, pour tester l'expérience prospect. |
| `README.md` | Documentation technique : démarrage rapide, scoring, embed, stockage, déploiement Streamlit Cloud, design. |
| `GUIDE_CLIENT_AGENCE.md` | Guide client : mise en service, installation du widget sur WordPress/CMS, utilisation. |
| `GUIDE_VENTE_ONBOARDING.md` | Playbook de vente et d'onboarding pour vendre le service aux agences. |

---

## 3. Fonctionnement détaillé

### 3.1 Démarrage & configuration

1. **Chargement de la config** via la fonction `_cfg()` : priorité **secrets Streamlit Cloud** (`st.secrets`) > fichier **`.env`** > valeur par défaut. Cela permet de déployer sur Streamlit Community Cloud sans fichier `.env`.
2. **Variables lues** : `ADMIN_PASSWORD` (défaut `admin123`, à changer), `GEMINI_API_KEY`, `GEMINI_MODEL` (liste de modèles avec replis), `AGENCY_FILE`, `LEADS_FILE`, `ALERTS_FILE`, `GOOGLE_SHEETS_JSON`/`GOOGLE_SHEETS_KEY`, `SMTP_*`, `APP_BASE_URL`, `SHEETS_CONFIG_FILE`.
3. **Initialisation Gemini** : si la clé est présente, `genai.configure(api_key=…)` → `GEMINI_READY = True`. Sans clé, l'app fonctionne en **mode dégradé** (questions modèles + scoring par règles).
4. **Agence de démonstration** : `ensure_default_agencies()` crée l'agence `maisonnova-lyon` au premier lancement si le fichier est vide.
5. **Routage** (`st.query_params.get("agency")`) : paramètre présent → `render_prospect(slug)`, sinon → `render_admin()`.
6. **CSS injecté** : `inject_css()` → `st.markdown(APP_CSS, unsafe_allow_html=True)`.

### 3.2 Le moteur IA (Gemini)

Quatre types de génération, tous avec repli automatique de modèle et repli texte si l'API échoue :

| Fonction | Rôle | Prompt système | Paramètres |
|---|---|---|---|
| `generate_welcome` | Message d'accueil au nom de l'agence + demande du prénom | Prompt inline (ton, agence, ville, description) | temperature 0.8, max 250 tokens |
| `generate_question` | Pose UNE question adaptée au profil (question n° n/5) | `SYSTEM_QUESTION` (contexte du prospect, catégorie, template) | temperature 0.7, max 200 tokens |
| `extract_profile` (via `ai_json`) | Extrait le profil en JSON : name, project_type, budget, city, financing, timeline | `SYSTEM_EXTRACT` (clés exactes, règles de valeurs) | temperature 0.2, mode JSON, max 800 tokens |
| `generate_closing` (via `ai_json`) | Synthèse 2-3 phrases + message de clôture personnalisé | `SYSTEM_SUMMARY` (JSON : `summary`, `message`) | temperature 0.2, mode JSON, max 500 tokens |

- `ai_complete()` : boucle sur `GEMINI_MODELS` ; en cas d'échec d'un modèle (exception), passe au suivant ; `request_options={"timeout": 60}`.
- `ai_json()` : active `response_mime_type="application/json"`, nettoie les fences markdown (` ```json `), extrait le bloc `{…}` et `json.loads`.
- **Mode dégradé sans IA** : l'extraction tombe sur `extract_profile_rules()` (regex françaises : « je m'appelle… », montants en euros avec k/M, mots-clés projet/ville/financement/délai) et les messages tombent sur les templates `QUESTIONS`/replis texte.

### 3.3 Le scoring (déterministe, max 100 points)

Fonction `score_profile(profile, agency_city)` :

| Question | Critères | Points |
|---|---|---|
| Projet | maison · appartement · investissement · terrain · autre | 20 · 18 · 16 · 12 · 10 |
| Budget | ≥ 600 k · 400–600 k · 250–400 k · 150–250 k · < 150 k | 25 · 22 · 16 · 10 · 5 |
| Ville | même ville que l'agence · autre ville · non renseignée | 15 · 10 · 0 |
| Financement | prêt pré-accordé · comptant/apport · à prévoir · aucun | 25 · 20 · 12 · 5 |
| Délai | < 6 mois · 6–12 mois · 12–24 mois · flexible | 15 · 12 · 8 · 5 |

- **Seuil par défaut : 70** (modifiable par agence, curseur 0–100 dans l'admin).
- `score >= seuil` → **qualifié** → bouton doré Calendly + alerte « Nouveau lead qualifié ».

### 3.4 Parcours prospect (le chat) — `render_prospect(slug)`

État dans `st.session_state` avec un **id de session UUID**. Étapes : `welcome → chat (5 questions) → closing`.

1. **Vérification agence** : `get_agency(slug)` ; si introuvable → carte « Agence introuvable » + `st.stop()`.
2. **Initialisation de session** : `prospect_stage`, `messages`, `q_index`, `answers`, `profile`, `score`, `summary`, `session_id`, `qualified`, `final_msg`, `thinking`. Le premier message assistant est généré par `generate_welcome(agency)`.
3. **En-tête agence** : logo (avec repli 🏡), nom, description, pastille « Qualification immobilière ».
4. **Progression + score** : 5 pastilles dorées (projet, budget, ville, financement, délai) + barre de score lumineuse avec repère du seuil.
5. **Historique du chat** : chaque message affiché avec `st.chat_message` (avatar 🤖/👤).
6. **Indicateur « l'assistant écrit… »** : 3 points dorés animés pendant `thinking`.
7. **À chaque réponse du prospect** (`st.chat_input`) :
   - `extract_profile()` (IA + repli règles) → mise à jour cumulée de `profile` et `score`.
   - Stade `welcome` → on a le prénom → démarre le questionnaire (question 1).
   - Stade `chat`, question < 5 → question suivante.
   - Stade `chat`, dernière question → **CLOSING** :
     - `generate_closing()` → synthèse + message de clôture ;
     - `save_lead()` → écriture dans `leads.csv` (et push Google Sheets si configuré) ;
     - `notify_agency()` → écriture dans `alerts.log` (+ e-mail SMTP réel si configuré et lead qualifié) ;
     - `st.toast("📩 Profil enregistré…")` ;
     - tout est entouré d'un `try/except` : la clôture **aboutit toujours** (pas de doublon, pas d'écran d'erreur).
8. **Écran final** :
   - **Qualifié** (score ≥ seuil) → carte « Projet éligible 🏆 » avec détail des points par catégorie + **bouton doré « ✦ Réserver mon rendez-vous expert »** (lien Calendly) + mention « Réponse sous 24h ».
   - **Non qualifié** → carte « Merci pour votre confiance 🤝 » + détail des points + message « un conseiller reviendra vers vous ».
9. **Pied de page** : « Propulsé par MaisonNova Engine · Qualification assistée par IA ».

### 3.5 Stockage des leads

- **`leads.csv`** (toujours) — colonnes : `timestamp, agency_slug, agency_name, session_id, name, project_type, budget, city, financing, timeline, score, threshold, qualified, summary, source`. Encodage UTF-8 avec BOM (lisible dans Excel).
- **Google Sheets** (optionnel) — si configuré, chaque lead est **aussi** poussé en temps réel (`_push_to_sheets`) dans la feuille `Leads`, créée automatiquement avec les en-têtes (`add_worksheet` + `append_row`). L'admin peut tester la connexion avec le bouton « 🔌 Tester la connexion » (`test_sheets_connection`).
- Config Google Sheets possible via `.env` (`GOOGLE_SHEETS_JSON` chemin du fichier + `GOOGLE_SHEETS_KEY`) **ou** depuis l'admin (collage du JSON du service account + ID/URL du spreadsheet).

### 3.6 Notifications

`notify_agency(agency, lead_name, score, qualified)` :
1. **Toujours** : écrit un e-mail formaté dans `alerts.log` (sujet « 🏆 Nouveau lead qualifié — … (score/100) », corps avec nom, score, seuil, qualifié, horodatage).
2. **Si SMTP configuré ET lead qualifié** : envoi d'un **vrai e-mail** via `smtplib` (STARTTLS, login, `send_message`) à l'adresse email de l'agence.

### 3.7 Interface admin — `render_admin()`

**Connexion** : mot de passe (`st.text_input` type password) comparé à `ADMIN_PASSWORD` ; succès → `ss.admin_auth = True` en session ; échec → `st.error("Mot de passe incorrect.")`. Avertissement affiché si la clé Gemini n'est pas configurée.

Cinq onglets :

1. **🏢 Agences**
   - Formulaire : nom, ville, URL du logo, email (alertes), lien Calendly, description/slogan, **seuil de qualification** (curseur 0–100), URL publique de l'app.
   - À l'enregistrement : `slugify(name)` (accents français gérés, ex. « Agence L'Immobilière » → `agence-l-immobiliere`), sauvegarde dans `agencies.json` (l'ancien slug est supprimé s'il change).
   - Génère et affiche l'**URL de qualification** : `{app_url}/?agency={slug}`.
2. **📗 Google Sheets**
   - Zone de texte pour le JSON du service account + champ ID/URL du spreadsheet.
   - Boutons « 💾 Enregistrer » et « 🔌 Tester la connexion » (le test utilise les valeurs du formulaire, sauvegardées d'abord).
3. **📊 Leads**
   - KPIs : prospects capturés, qualifiés, taux de qualification, score moyen.
   - Filtre par agence, tableau `st.dataframe` (score + badge 🟢/🟠), **export CSV** (`st.download_button`).
4. **🔔 Alertes**
   - Affiche les 60 dernières lignes d'`alerts.log` dans un bloc `st.code`.
5. **🔌 Embed**
   - Sélecteur d'agence → génère le **snippet iframe** (460×620, bordure arrondie, `loading="lazy"`) : `<iframe src="{app_url}/?agency={slug}&embed=1" …>`.
   - Bouton « 🌐 Prévisualiser le widget » (`st.link_button`).

Bouton « Déconnexion » : `ss.admin_auth = False` + `st.rerun()`.

### 3.8 Design premium

CSS personnalisé (`APP_CSS`, injecté avec `unsafe_allow_html=True`) :
- Typographies **Inter** (texte) et **Playfair Display** (titres) via Google Fonts.
- Fond blanc avec **aurora dorée** animée (radial-gradients + `@keyframes aurora`, 16 s).
- **Glassmorphism** : cartes `.glass` avec `backdrop-filter: blur(22px) saturate(170%)`.
- Chat style **iMessage** : bulles arrondies, avatars ronds, animation d'apparition, coins asymétriques.
- Indicateur « l'assistant écrit… » : 3 points dorés animés (`@keyframes blink`).
- Input de chat en **pilule flottante** avec halo doré au focus, bouton d'envoi rond doré.
- **CTA doré** avec effet *shimmer* (reflet qui balaie le bouton, `@keyframes shimmer`).
- Barre de score lumineuse avec transition de largeur et **repère du seuil**.
- Pastilles de progression des 5 questions (dot doré = question validée).
- Chrome Streamlit masqué (menu principal, footer, toolbar, bouton deploy).
- Scrollbar raffinée dorée, formulaires admin arrondis, onglets en « pills », métriques en cartes glass.

### 3.9 Tests — `smoke_test.py`

Teste le moteur **sans navigateur** en créant un stub du module `streamlit` :
1. Boot complet du script (routing prospect) sans exception.
2. `slugify` (accents et ponctuation).
3. Extraction par règles + scoring : conversation type « Jean Dupont, maison, 400 000 €, Lyon, prêt pré-accordé, dès que possible » → profil extrait correct + **score 97/100**.
4. Profil faible (< 150 k, aucun financement, flexible, autre ville) → score < 70 → non qualifié.
5. Sauvegarde CSV + alerte : vérifie `leads.csv` (1 ligne, score 97, qualifié oui) et `alerts.log` (nom + score présents).
6. Boot de l'interface admin (sans `?agency=`) sans exception.
7. Google Sheets : chemins d'erreur gérés sans crash (config incomplète, JSON invalide).

### 3.10 Déploiement

- Pensé pour **Streamlit Community Cloud** (gratuit) depuis GitHub : chaque `git push` sur `main` redéploie automatiquement (~1 min).
- Secrets saisis dans Settings → Secrets (format TOML) : `ADMIN_PASSWORD`, `GEMINI_API_KEY`, `APP_BASE_URL`, et optionnellement Google Sheets / SMTP.
- ⚠️ `leads.csv` est **local à l'instance** : pour un stockage durable multi-agences, activer **Google Sheets** (recommandé en production).

---

## 4. Résumé en une phrase

**L'agence installe un lien/iframe sur son site → le prospect discute avec l'IA (5 questions) → le projet est noté sur 100 → les profils sérieux réservent un rendez-vous Calendly → l'agence reçoit le lead (CSV/Google Sheets) et l'alerte, et suit tout dans son tableau de bord admin.**
