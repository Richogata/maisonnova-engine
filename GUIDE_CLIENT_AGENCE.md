# 🏡 Votre assistant de qualification est prêt !
### Guide d'installation et d'utilisation — [NOM DE L'AGENCE]

---

## ✅ Ce que vous recevez

Un **assistant de qualification intelligent** qui accueille vos prospects sur votre site, leur pose **5 questions ciblées** et **score leur projet en temps réel** (de 0 à 100 points).

- 🔢 **Score automatique** : projet, budget, ville, financement, délai
- 🎯 **Seuil de qualification** : au-dessus du seuil → le prospect peut **réserver un rendez-vous** directement (Calendly)
- 📥 **Leads centralisés** : chaque conversation est enregistrée et consultable
- 📧 **Alertes** : vous êtes notifié à chaque lead qualifié
- 🧩 **Personnalisation** : votre logo, vos couleurs, le nom de votre assistant
- 🌍 **4 parcours possibles** : Achat, Vente, Location, Investissement

Votre **dossier client** (`MaisonNova_<votre-agence>_Client_Kit.zip`) contient tout, y compris un **guide d'installation interactif** qui vous accompagne clic par clic.

---

## 📦 1. Contenu de votre dossier

| Élément | Où le trouver | À quoi ça sert |
|---|---|---|
| **Guide interactif** | `guide/client_guide.html` | ⭐ À ouvrir en premier : il vous guide pas à pas pour installer l'assistant (sans aucune connaissance technique) |
| **LISEZ-MOI.txt** | racine du dossier | Le point de départ, expliqué simplement |
| **Code d'installation** | `code/installation.txt` | Le code à coller sur votre site |
| **Identifiants** | `code/identifiants.txt` | Votre identifiant agence + votre clé d'installation |
| **Code simple (iframe)** | `widget/iframe.txt` | Une alternative plus simple pour vos équipes |
| **Instructions webmaster** | `instructions_webmaster/webmaster.txt` | À transmettre si votre site est géré par un tiers |
| **Configuration** | `configuration/` | Votre seuil de score, vos questions, vos parcours |

---

## 🚀 2. Le guide interactif (à faire en premier)

Double-cliquez sur **`guide/client_guide.html`** : il s'ouvre dans votre navigateur.

1. **Choisissez votre plateforme** : WordPress, Wix, Webflow, site personnalisé…
   - *Vous ne savez pas* ? Cliquez sur **« Je ne sais pas »** : le guide vous aide à le découvrir.
2. **Suivez les étapes** : chaque étape a une explication simple et un bouton **« J'ai fait cette étape »**.
3. **Votre progression est sauvegardée** : vous pouvez fermer le guide et reprendre plus tard exactement où vous vous étiez arrêté.
4. **Bloqué ?** Cliquez sur **« Je suis bloqué »** : les problèmes les plus courants sont expliqués avec la solution (cause → solution → test → si ça ne marche toujours pas).
5. **Vous avez un webmaster ?** Choisissez **« Je travaille avec un webmaster »** : le guide génère des instructions techniques prêtes à lui envoyer (bouton **« COPIER LES INSTRUCTIONS POUR MON WEBMASTER »**).

À la fin, le guide vous fait **vérifier** que tout fonctionne (le widget apparaît, le chat répond, le score s'affiche, le bouton de rendez-vous est là).

---

## 🔗 3. Votre lien de qualification

Ouvrez ce lien dans votre navigateur (ou en navigation privée pour tester) :

```
[VOTRE LIEN ICI — ex : https://votre-app.streamlit.app/?agency=maisonnova-lyon]
```

C'est la page que verront vos prospects : un chat épuré « style Apple », au nom de votre agence, avec votre logo.

> 💡 Testez-la vous-même : répondez comme le ferait un vrai acheteur. Vous verrez le score évoluer question après question et le bouton de rendez-vous apparaître.

Ce lien vous sert aussi de **démonstration** : vous pouvez l'envoyer à n'importe qui pour montrer l'assistant en conditions réelles, sans mot de passe.

---

## 🧩 4. Installer l'assistant sur votre site

### Option A — Suivre le guide interactif (recommandé)

Ouvrez `guide/client_guide.html` et suivez les étapes pour **votre** plateforme. Le guide vous montre exactement où cliquer, avec les bons mots à l'écran.

### Option B — WordPress (ou tout CMS avec un bloc HTML)

1. Créez un **bloc HTML personnalisé** sur la page de votre choix (accueil ou page « Contact »).
2. Collez ce code :

```html
<iframe src="[VOTRE LIEN ICI]&embed=1"
        width="460" height="620" style="border:none; border-radius:16px;"
        title="Qualification" loading="lazy"></iframe>
```

3. Publiez. L'assistant apparaît encadré, prêt à l'emploi.

### Option C — Page dédiée (lien direct)

Ajoutez un bouton qui ouvre le lien de qualification dans un nouvel onglet :

```html
<a href="[VOTRE LIEN ICI]" target="_blank"
   style="background:#C9A227; color:#fff; padding:14px 24px; border-radius:10px;
          text-decoration:none; font-weight:600;">
  🏡 Être recontacté par un conseiller
</a>
```

> 🔑 **Votre clé d'installation** est déjà incluse dans le code : vous n'avez **rien** à saisir à la main.

---

## 📊 5. Suivre vos prospects (leads)

Vos leads sont consultables dans le **tableau de bord** (onglet **Leads**) :

- Nom, téléphone, email du prospect
- Type de projet et budget annoncés
- **Score** (0–100) et statut : ✅ qualifié / ⏳ à suivre
- Lien de rendez-vous réservé (Calendly) si applicable

### Export

- Par défaut, tout est enregistré dans un **CSV** (lisible dans Excel).
- Optionnel : synchronisation **Google Sheets** en temps réel.

---

## 📧 6. Notifications

- **Nouveau lead qualifié** → alerte dans le tableau de bord.
- **Email réel** : possible (SMTP) — demandez l'activation pour recevoir chaque lead dans votre boîte mail.

---

## 🎯 7. Bien utiliser votre seuil de score

Le score mesure la **maturité du projet** :

| Critère | Points |
|---|---|
| Type de projet (maison, appartement, investissement, terrain) | 20 |
| Budget annoncé | 25 |
| Ville (même ville que l'agence → bonus) | 15 |
| Financement (prêt pré-accordé → max) | 25 |
| Délai du projet | 15 |

- **Seuil conseillé : 70/100** — au-delà, le prospect a un projet sérieux et finançable.
- Ajustable à tout moment (un seuil bas = plus de rendez-vous mais moins qualifiés ; un seuil haut = l'inverse).

---

## ❓ 8. Questions fréquentes

**Mes prospects doivent-ils installer quelque chose ?**
Non. Tout se passe dans le navigateur, sur votre site.

**L'assistant fonctionne-t-il sur mobile ?**
Oui, il est optimisé pour mobile (la majorité de vos prospects).

**Et si le prospect ne veut pas discuter ?**
Il peut à tout moment cliquer sur le bouton de rendez-vous si son score le permet.

**Combien de prospects puis-je traiter ?**
Illimité. Chaque conversation est indépendante et instantanée.

**Le chatbot peut-il parler d'achat, vente, location ?**
Oui : votre assistant est configuré pour les parcours actifs de votre agence (les questions s'adaptent).

---

## 🛟 9. Besoin d'aide ?

- 📧 Contact : **[EMAIL DE L'AGENCE]**
- 🗓️ Prise en main accompagnée : **[LIEN CALENDRY DE L'AGENCE]**
- 📘 Dans le guide interactif : bouton **« Je suis bloqué »** → dépannage pas à pas

*MaisonNova Engine — Votre assistant de qualification de leads immobilier.*
