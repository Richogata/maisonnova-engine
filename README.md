# 🏡 MaisonNova Engine v1

Moteur de **qualification de leads immobilier** en Streamlit + Gemini.
Deux interfaces dans une seule application `app.py` :

| Interface | Accès | Description |
|---|---|---|
| 🏢 **ADMIN** | page d'accueil | Protégée par mot de passe. Configure l'agence (nom, logo, ville, Calendly, seuil de score), tableau de bord des leads, alertes, snippet iframe. |
| 💬 **PROSPECT** | `/?agency=slug-agence` | Chat minimaliste « style Apple », IA qui pose 5 questions, scoring en temps réel, bouton doré Calendly si `score ≥ seuil`. |

---

## 🚀 Démarrage rapide

```bash
# 1. Installer les dépendances
pip install -r requirements.txt

# 2. Copier et compléter les variables
cp .env.example .env            # → renseigner GEMINI_API_KEY + changer ADMIN_PASSWORD

# 3. Lancer
streamlit run app.py
```

1. Ouvrez l'**admin** → configurez l'agence (le lien de qualification est généré automatiquement).
2. Ouvrez le lien `/?agency=…` en **navigation privée** → répondez au chat (l'IA qualifie, le lead est sauvegardé dans `leads.csv`, l'alerte mail est simulée dans `alerts.log`).
3. Retournez dans l'admin → onglet **Leads** : le prospect y est en temps réel.

> **Sans clé Gemini** : l'application fonctionne en mode dégradé (questions modèles + scoring par règles) — idéal pour tester le design.

## 🤖 Moteur IA (Gemini)

- Modèles essayés dans l'ordre : `gemini-flash-latest` (défaut, suit les modèles Google actuels) → `gemini-3.5-flash` → `gemini-3.1-flash-lite`.
- L'IA accueille le prospect **au nom de l'agence**, adapte ses 5 questions au profil, extrait les réponses en **JSON** et rédige la synthèse de clôture.
- En cas de panne API, un **scoring par règles** (regex français) prend le relais automatiquement.

## 📊 Scoring (max 100 pts)

| Question | Points |
|---|---|
| Type de projet (maison 20 · appartement 18 · investissement 16 · terrain 12) | 20 |
| Budget (≥600k → 25 … <150k → 5) | 25 |
| Ville (même ville que l'agence → 15, autre ville → 10) | 15 |
| Financement (prêt pré-accordé 25 · comptant 20 · à prévoir 12 · aucun 5) | 25 |
| Délai (<6 mois 15 · 6-12 → 12 · 12-24 → 8 · flexible 5) | 15 |

Seuil par défaut : **70** (modifiable dans l'admin, curseur 0–100).

## 🧩 Embed iframe (8.5 × 11)

Dans l'admin, onglet **Embed**, copiez le snippet :

```html
<iframe src="https://votre-app.fr/?agency=maisonnova-lyon&embed=1"
        width="460" height="620" style="border:none; border-radius:16px;"
        title="Qualification" loading="lazy"></iframe>
```

Le widget est optimisé pour le portrait (fond blanc, centrage, barres Streamlit masquées).

## 🗄️ Stockage

- **Par défaut** : CSV local — `leads.csv` (UTF-8 BOM, lisible dans Excel).
- **Optionnel** : Google Sheets via `gspread`.

### Configurer Google Sheets (2 min)

1. [Google Cloud Console](https://console.cloud.google.com) → activez l'API *Google Sheets* → **IAM & Admin → Comptes de service** → *Créer un compte* → *Créer une clé* → **JSON** (téléchargez le fichier).
2. Créez un spreadsheet vide, puis **Partagez** avec l'e-mail du service account (rôle *Éditeur*).
3. Dans l'**admin → onglet Google Sheets** : collez le contenu du fichier JSON + l'ID/URL du spreadsheet → **💾 Enregistrer** → **🔌 Tester la connexion**.

Dès lors, chaque lead est poussé **en temps réel** dans la feuille `Leads` (créée automatiquement avec les en-têtes).

> Alternative serveur : `GOOGLE_SHEETS_JSON` (chemin du fichier) + `GOOGLE_SHEETS_KEY` (ID) dans `.env`.

## 🚢 Déploiement (Streamlit Community Cloud, gratuit)

L'app est pensée pour être déployée depuis **GitHub** : chaque `git push` redéploie automatiquement.

### Étapes (une seule fois)

1. **Créer un dépôt GitHub** et pousser le projet :
   ```bash
   git init && git add . && git commit -m "Première version"
   git branch -M main
   git remote add origin https://github.com/<utilisateur>/<repo>.git
   git push -u origin main
   ```
2. **Créer le compte** sur [share.streamlit.io](https://share.streamlit.io) (connexion avec GitHub).
3. **New app** → sélectionner le dépôt → branche `main` → fichier principal `app.py` → **Deploy**.
4. **Configurer les secrets** : Settings → **Secrets** → coller le contenu TOML ci-dessous.
5. L'app est en ligne sur `https://<votre-app>.streamlit.app`.

### Secrets à saisir (Settings → Secrets)

```toml
# Même contenu que le .env local
ADMIN_PASSWORD = "changez-moi"
GEMINI_API_KEY = "AIza..."
APP_BASE_URL = "https://<votre-app>.streamlit.app"
# Optionnel : Google Sheets / SMTP…
# GOOGLE_SHEETS_JSON = "..."
# GOOGLE_SHEETS_KEY = "..."
```

> 💡 Chaque modification poussée sur `main` est déployée automatiquement en ~1 minute.
> Le CSV `leads.csv` est **local à l'instance** : pour un stockage durable multi-agences,
> activez Google Sheets (onglet admin) — recommandé pour la production.

## 🎨 Design premium

Typographie **Inter + Playfair Display**, fond blanc avec aurora dorée subtile, glassmorphism, bulles de chat animées, indicateur « l'assistant écrit… », pastilles de progression des 5 questions, barre de score lumineuse et CTA doré avec effet *shimmer*.

## 🔔 Notifications

Nouveau lead **qualifié** → alerte enregistrée dans `alerts.log` et affichée dans l'admin.
Pour un **vrai e-mail** : renseignez `SMTP_*` dans `.env`.

## ⚙️ Contraintes techniques respectées

- 100 % Python/Streamlit · `google-generativeai` · optimisé pour 8 Go de RAM (CSV léger, pas de pandas, tokens bornés, repli automatique).
- Design premium : typographie **Inter**, glassmorphism (`backdrop-filter`), fond blanc, CTA doré, bulles de chat façon iMessage.
