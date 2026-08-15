# 📘 PLAYBOOK DE VENTE & ONBOARDING — MaisonNova Engine v2
### Ton processus complet pour vendre ton service de qualification de leads aux agences immobilières — et l'installer sans accroc, à chaque fois.

---

## 🎯 Ce que tu vends

Un **assistant de qualification intelligent** que l'agence installe sur son site. Il accueille les prospects, leur pose des questions adaptées (achat, vente, location, investissement), **score chaque lead de 0 à 100** et déclenche automatiquement un **rendez-vous Calendly** pour les projets sérieux.

**Le bénéfice que tu vends n'est pas « un chat » — c'est :**
> « Vous ne perdez plus un seul prospect. Vous ne passez plus votre temps avec des curieux. Seuls les acheteurs sérieux réservent un rendez-vous. »

**Tes outils v2 :**
- 🏢 Gestion des **clients** (dossiers complets, statuts DRAFT → INSTALLED)
- 🤖 **4 parcours** configurables (Achat / Vente / Location / Investissement)
- ⚡ **Extraction automatique** des infos depuis le site du client
- 👁 **Prévisualisation** + **mode TEST** (teste sans polluer les vrais leads)
- 📦 **Code d'installation**, identifiant agence, clé — générés automatiquement
- 📘 **Guide interactif** personnalisé (client_guide.html) + **dossier client ZIP**
- 🧩 Guide **LISEZ-MOI** dans le ZIP, instructions **webmaster** prêtes à envoyer

---

## 🔁 PHASE 1 — PROSPECTION (jour 0)

### Cibles
- Agences immobilières **3 à 20 employés** (ICP)
- Villes : Lyon, Paris et toute la France (adaptable Belgique, Suisse, Québec…)
- Canaux : LinkedIn (décideurs), emailing, bouche-à-oreille

### Script de premier contact (email / LinkedIn)
```
Bonjour [Prénom],

Je m'appelle [Nom], fondateur de MaisonNova.

J'ai vu [Agence] sur Google Maps. Je suppose que comme toutes les
agences, vous recevez des demandes par téléphone, par email, par
Instagram… et qu'il est difficile de savoir qui est vraiment
acheteur.

On a construit un assistant qui qualifie chaque demande en
quelques secondes (budget, financement, délai) et qui réserve
directement un rendez-vous aux acheteurs sérieux.

Ça vous dirait de le voir en action ? 3 minutes, sans engagement.

[Lien de démo : https://votre-app.streamlit.app/?agency=maisonnova-lyon]
```

---

## 🎬 PHASE 2 — LA DÉMO (jour 1–3)

### Déroulé (15 min max)
1. **Ouvre la démo** sur le lien de l'agence (ou crée un client de démo « test » dans ton admin → onglet **Prévisualisation**).
2. Laisse l'assistant accueillir « au nom de l'agence ».
3. Réponds en jouant un **acheteur sérieux** (budget élevé, prêt pré-accordé) → montre le **score 85+** et le **bouton doré de rendez-vous** qui apparaît.
4. Réponds en jouant un **curieux** (budget faible, délai flexible) → montre qu'il est **filtré**.
5. Montre le **tableau de bord admin** : le lead apparaît en temps réel, avec son score.
6. **Killer feature** : « Collez simplement l'adresse du site de l'agence : l'outil extrait automatiquement les infos et configure l'assistant tout seul. »

### 💡 Le lien de démonstration
Chaque client a un **lien de démo partageable** (onglet **📦 Installation**) : URL publique + fichier `.url` à envoyer. **Aucun mot de passe requis** pour le visiteur. Utilise-le aussi comme démo pour les prospects suivants.

### Les 3 objections classiques

| Objection | Réponse |
|---|---|
| « Mes clients préfèrent appeler. » | L'assistant ne remplace pas le téléphone : il le **pré-qualifie**. Vous n'appelez que les acheteurs sérieux. |
| « On a déjà un formulaire. » | Un formulaire est une **corvée** (le prospect part). Ici c'est une **conversation** : 3x plus de complétion, et vous avez le **score** en plus. |
| « C'est combien ? » | Donne un tarif d'appel (ex : mise en place + abonnement mensuel) puis **renvoie vers la valeur** : « Combien vaut un rendez-vous signé ? Un seul rendez-vous qualifié couvre l'année. » |

---

## 📋 PHASE 3 — COLLECTE DES INFOS CLIENT

> ⚠️ **Avant de créer le dossier**, envoie le formulaire d'infos au client :
> → **`FORMULAIRE_CLIENT.md`** (à copier-coller dans ton email / à envoyer tel quel)

**Le minimum indispensable :**
- [ ] **Nom de l'agence** + **ville principale**
- [ ] **Site web** (URL) → *permet l'extraction automatique des infos !*
- [ ] **Email de contact** (pour les alertes)
- [ ] **Lien Calendly** du conseiller (ou créer un compte)
- [ ] **Logo** (URL ou fichier image)
- [ ] **Seuil de score** souhaité (conseil : 70/100)
- [ ] **Nom de l'assistant** (ex : « Léa, votre conseillère ») + message d'accueil souhaité
- [ ] **Parcours à activer** : Achat / Vente / Location / Investissement
- [ ] Couleurs (ou on garde le doré premium par défaut)

> 💡 **Astuce :** si le client te donne juste son **site web**, l'extraction automatique remplit déjà la majorité des champs (nom, ville, services, email, téléphone, logo…). Le formulaire sert à compléter ce qui manque (Calendly, seuil, nom de l'assistant).

---

## 🛠️ PHASE 4 — CRÉATION & CONFIGURATION (30 min)

### Étape A — Créer le client (onglet 🏢 Clients)
1. **« ⚡ Création rapide depuis le site »** : colle l'URL du site du client → l'outil extrait automatiquement nom, ville, email, services, zones, types de biens, logo…
   - *Ou* « ➕ Nouveau client » si pas de site.
2. Vérifie les infos extraites, complète ce qui manque.

### Étape B — Parcours de configuration (onglet 🛠 Configuration)
Un **stepper en 8 étapes** (les pastilles indiquent ce qui est fait ✓) :
1. **Agence** — nom, ville, logo, email, couleurs
2. **Activité** — services, zones, types de biens, horaires
3. **Parcours clients** — active/désactive Achat, Vente, Location, Investissement
4. **Qualification** — seuil de score, points par critère
5. **Assistant** — nom, message d'accueil, ton
6. **Rendez-vous** — lien Calendly
7. **Apparence** — couleurs principale/secondaire, logo
8. **Résumé** — vérifie tout, ajuste le statut

> 💡 Le statut du client monte automatiquement (CONFIGURED, PREVIEW_READY…) au fil des étapes.

### Étape C — Vérifier le chatbot (onglet 🤖 Chatbots)
- Les 4 parcours sont **activés par défaut** : le chatbot fonctionne immédiatement, aucun backup nécessaire.
- Personnalise questions, ordre, points, seuil **par client** si besoin.

### Étape D — Prévisualiser (onglet 👁 Prévisualisation)
- Sélectionne le client → vois le chat, les couleurs, le message, le score, l'écran final, le bouton Calendly.
- **Mode TEST** : discute avec le vrai chatbot. Les leads de test vont dans `test_leads.csv` (identifiés TEST) et **ne polluent pas** les vrais leads (ni Sheets, ni alertes).

### Étape E — Installer (onglet 📦 Installation)
- Copie **A. URL publique**, **B. iframe**, **C. code d'installation**, **D. identifiant agence**, **E. clé**.
- Boutons **COPIER / TÉLÉCHARGER / PRÉVISUALISER** pour chaque élément.
- Télécharge les **instructions webmaster** si le client a un prestataire.
- Change le **statut** : Code prêt → Installation en attente → Installé.

---

## 📦 PHASE 5 — GÉNÉRER LE KIT & ENVOYER LE GUIDE (livraison)

### 1. Générer le guide (onglet 📘 Guides)
- Clique **« 📘 Créer / régénérer le guide »** → génère `guides/<client>_guide.html`.
- Clique **« 📦 Exporter le dossier client (ZIP) »** → télécharge `MaisonNova_<slug>_Client_Kit.zip`.

### 2. Que contient le ZIP ?
```
LISEZ-MOI.txt                 ← à lire en premier (langage non technique)
client_info/                  ← fiche récapitulative (sans secret)
configuration/                ← seuil, questions, parcours
widget/                       ← iframe + script
code/                         ← code d'installation + identifiants + clé
guide/client_guide.html       ← ⭐ le guide interactif (à ouvrir dans le navigateur)
instructions_webmaster/       ← bloc technique pour le webmaster
```
**Aucun secret** : pas de mot de passe, pas de clé API, pas de données sensibles.

### 3. Email d'envoi type
```
Objet : 🎉 Votre assistant est prêt, [Agence] !

Bonjour [Prénom],

Votre assistant de qualification est prêt. Tout est dans votre dossier :

📎 En pièce jointe : MaisonNova_[Agence]_Client_Kit.zip

COMMENT FAIRE (3 étapes) :
1️⃣ Dézippez le dossier (clic droit → Extraire tout).
2️⃣ Double-cliquez sur guide/client_guide.html : le guide interactif
   s'ouvre dans votre navigateur et vous accompagne pas à pas.
3️⃣ Suivez les étapes pour votre plateforme (WordPress, Wix, Webflow…).
   Votre progression est sauvegardée : vous pouvez reprendre plus tard.

🔗 Vous pouvez aussi tester tout de suite votre assistant ici :
[LIEN DE DÉMO]

💬 Votre identifiant : [agency_id] — votre clé est déjà dans le code,
   vous n'avez rien à saisir.

Bloqué ? Le guide a un bouton « Je suis bloqué » avec les solutions,
et je reste disponible à [TON EMAIL].

Bonne mise en ligne !
```

### 4. Selon le client
- **Le client installe lui-même** → il suit le guide interactif (`client_guide.html`). C'est prévu pour une personne **sans aucune connaissance technique**.
- **Le client a un webmaster** → il clique « Je travaille avec un webmaster » dans le guide, ou tu lui transmets `instructions_webmaster/webmaster.txt`.
- **Le client veut que TU installes** → suis **`GUIDE_INSTALLATION_DIRECTE.md`** (le guide pas-à-pas pour installer sur son site toi-même).

---

## 🔄 PHASE 6 — VÉRIFICATION FINALE & SUIVI

### Checklist à valider avec le client
- [ ] Le widget est **visible sur le site** (test mobile + desktop)
- [ ] Le **chatbot répond** et pose les questions
- [ ] Le **score** s'affiche en fin de parcours
- [ ] Le **Calendly** reçoit les rendez-vous (faire un test)
- [ ] Le lead apparaît dans l'admin → **Leads** (ou son email)
- [ ] Statut du client passé à **INSTALLED** (onglet Installation)

### J+7 — prise en main
- « Combien de prospects ont discuté avec l'assistant cette semaine ? »
- Vérifie que les alertes arrivent bien, ajuste le seuil de score si besoin.

### J+30 — preuve & développement
- Envoie un **récap chiffré** : nombre de conversations, de qualifiés, de rendez-vous pris.
- Propose la suite :
  - 📊 **Multi-sites** (plusieurs agences du même groupe)
  - 🧩 **Relance automatique** des leads non qualifiés
  - 🏢 **Élargissement** à leurs autres villes

---

## 🚫 LES ERREURS À ÉVITER

- ❌ Ne pas tester le lien avant de le livrer (toujours vérifier en navigation privée)
- ❌ Oublier de configurer l'**email d'alerte** → l'agence ne voit rien arriver
- ❌ Livrer le ZIP sans dire d'ouvrir **`guide/client_guide.html`** en premier
- ❌ Promettre le « clé en main » sans le faire → tu es le support n°1 la première semaine, c'est normal, assume-le
- ❌ Mélanger les leads de TEST avec les vrais (le mode TEST isole automatiquement — vérifie quand même)

---

## ✅ CHECKLIST FINALE D'INSTALLATION

- [ ] Client créé (nom, ville, email, logo, description, Calendly, seuil)
- [ ] Infos **extraites du site** ou complétées manuellement
- [ ] Parcours chatbot **activés** (Achat/Vente/Location/Investissement)
- [ ] Assistant nommé + message d'accueil personnalisé
- [ ] Lien de qualification **testé en navigation privée** (score + bouton Calendly)
- [ ] **Kit ZIP généré** (guide interactif + LISEZ-MOI + code + webmaster)
- [ ] **Guide envoyé** avec les 3 étapes expliquées dans l'email
- [ ] Installation effectuée (client, webmaster, ou toi → GUIDE_INSTALLATION_DIRECTE.md)
- [ ] Statut client : **INSTALLED**
- [ ] Accès admin transmis (si prévu)
- [ ] Rappel J+7 programmé

---

## 🗂️ Les fichiers de ton arsenal

| Fichier | Usage |
|---|---|
| `GUIDE_CLIENT_AGENCE.md` | Guide client à personnaliser et envoyer |
| `FORMULAIRE_CLIENT.md` | Infos à demander au client avant de créer son dossier |
| `GUIDE_INSTALLATION_DIRECTE.md` | Installation par TES SOINS sur le site du client |
| `EXPLICATION_PROGRAMME.md` | Explication technique complète du programme |

---

*MaisonNova Engine v2 — Vendez la qualification, livrez la sérénité.*
