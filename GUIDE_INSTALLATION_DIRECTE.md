# 🛠️ GUIDE D'INSTALLATION DIRECTE — MaisonNova AI
### Installer toi-même l'assistant sur le site du client (WordPress, Wix, Webflow, site personnalisé)

> À utiliser quand le client te demande de faire l'installation **à sa place**.
> Le client ne touche à rien : tu récupères l'accès au site, tu colles le code,
> tu testes, tu lui rends un site avec l'assistant actif.

---

## ⏱️ Avant de commencer (5 min de préparation)

### 1. Ce qu'il te faut
- [ ] L'**URL du site** du client
- [ ] La **plateforme** du site (WordPress, Wix, Webflow, autre…)
- [ ] Un **accès au site** :
  - WordPress → identifiants `wp-admin` (ou un compte « Éditeur »)
  - Wix → accès au compte Wix (ou invite « Collaborateur »)
  - Webflow → accès au Designer (ou invite « Editor »)
  - Custom → accès FTP / cPanel / l'outil de l'hébergeur
- [ ] Ton **admin MaisonNova** ouvert → onglet **📦 Installation**

> 🔐 **Sécurité** : ne garde jamais les identifiants du client en clair dans un
> fichier. Recommande-lui de **changer son mot de passe** après l'installation
> si tu as utilisé le sien (ou crée un compte temporaire que tu supprimes ensuite).

### 2. Récupérer le code d'installation
1. Ouvre ton admin MaisonNova → **📦 Installation**.
2. Sélectionne le client.
3. Copie **« C. Code d'installation »** (le bloc `div + script`).
   - *Tu peux aussi télécharger le fichier `<slug>_code.html`*.
4. Note son **identifiant agence** (D) et sa **clé** (E) — pour vérifier que l'installation est bonne.

> ✅ Vérifie que l'**URL publique** (A) pointe bien vers **ton app déployée**
> (`https://maisonnova-engine-…streamlit.app/?agency=…`) et pas vers localhost.
> Si besoin, mets à jour `app_url` du client dans l'admin (Configuration → Étape 1).

---

## 🔵 Installation sur WORDPRESS

### Connexion
1. Va sur `https://[site-du-client]/wp-admin`.
2. Connecte-toi avec les identifiants fournis.

### Ajouter le code (méthode rapide — bloc HTML)
1. Menu gauche → **Pages** → ouvre la page d'accueil (ou **Apparence → Widgets** → ajoute un « Bloc HTML » dans la sidebar).
2. Clique sur **« + »** (ajouter un bloc) → cherche **« HTML »** → clique sur **« HTML personnalisé »**.
3. Colle le **code d'installation** complet (le bloc `div + script`) dans le bloc.
4. Clique sur **« Mettre à jour »** (en haut à droite).
5. Ouvre le site en navigation privée → **teste** (voir la checklist en bas).

### Méthode avancée (si le thème le permet)
- **Apparence → Éditeur de thème → footer.php** : colle le code juste avant `</body>`.
- **Plugin** : si le client a un plugin « Header & Footer » (ex : WPCode), colle le code dans la section « Footer ».

### ⚠️ Pièges WordPress
- **Cache** : si le widget n'apparaît pas, vide le cache (plugin cache + navigateur).
- **Page pas publiée** : vérifie que la page est bien **publiée** et pas en « brouillon ».
- **Thème bloquant** : certains thèmes filtrent le HTML des blocs → utilise la méthode « footer » ou le plugin WPCode.

---

## 🟣 Installation sur WIX

### Connexion
1. Va sur `https://fr.wix.com` → **Connexion** (ou ouvre le lien d'invitation collaborateur).
2. Dans le tableau de bord, clique sur **« Modifier le site »** (icône crayon).

### Ajouter le code
1. Dans l'éditeur : clique sur **« + Ajouter »** (menu de gauche).
2. **« Intégrations »** (ou « Embarquer ») → **« Code embarqué »**.
3. Un encart apparaît : clique dessus → **« Entrer le code »** (ou « Ajouter le code »).
4. Colle le **code d'installation** complet → **« Mettre à jour »**.
5. Redimensionne l'encart (le widget fait 460 × 620 px) et positionne-le où tu veux (page d'accueil ou page Contact).
6. **« Publier »** → **« Publier maintenant »** (étape obligatoire !).

### ⚠️ Pièges Wix
- **Oubli de publication** : c'est l'erreur n°1 — sans « Publier », rien n'apparaît.
- **Encart trop petit** : si le widget est coupé, agrandis l'encart.
- **Ancien éditeur** : sur l'ancien éditeur Wix, le chemin est « + » → « Autres » → « Code embarqué ».

---

## 🔷 Installation sur WEBFLOW

### Connexion
1. Va sur `https://webflow.com` → connecte-toi (ou ouvre l'invitation Editor).
2. Ouvre le projet → le **Designer** s'affiche.

### Ajouter le code
1. Panneau gauche : **« Pages »** → ouvre la page souhaitée.
2. Panneau **« Ajouter »** (à gauche) → cherche **« Embed »**.
3. Fais glisser l'élément **« Embed »** sur la page.
4. Clique dans l'élément → colle le **code d'installation** complet.
5. Clique en dehors de l'élément pour valider.
6. **« Publish »** (en haut à droite) → **« Publish to selected domain »**.

### ⚠️ Pièges Webflow
- **Le widget est-il dans un container trop petit ?** Vérifie que l'élément Embed n'est pas limité en largeur par son parent.
- **Oubli de publier** : les changements du Designer ne sont pas en ligne tant que tu n'as pas cliqué sur Publish.
- **Page d'accueil = page « / »** : publie bien le domaine de production.

---

## 🛠️ Installation sur SITE PERSONNALISÉ (HTML / CMS autre)

### Si tu as un accès FTP / cPanel / hébergeur
1. Récupère le fichier de la page d'accueil (ex : `index.html`) ou le fichier `footer.php` / modèle commun.
2. Ouvre-le dans un éditeur (VS Code, Notepad++).
3. Colle le **code d'installation** **juste avant `</body>`** (à la fin de la page).
4. Enregistre et **recharge le site** (vide le cache).

### Si c'est un CMS (PrestaShop, Shopify, Jimdo, etc.)
- Utilise le **bloc HTML / Embed / Code** de la plateforme :
  - **Shopify** : Boutique en ligne → Préférences → Code du moteur de recherche → section footer
  - **PrestaShop** : Modules → module « Code HTML personnalisé »
  - **Jimdo / Carrd / Strikingly** : section « Code embarqué » ou « HTML »
- Colle le code complet → publie → teste.

### ⚠️ Pièges site personnalisé
- **`</body>` introuvable** : colle le code juste avant la fin du fichier, ça fonctionne aussi.
- **Minification** : si le site est généré par un outil, vérifie que le code n'est pas modifié automatiquement.
- **Sous-page vs toutes les pages** : pour un site codé main, mets le code dans le fichier **commun à toutes les pages** (header/footer inclus), pas seulement la page d'accueil.

---

## ✅ CHECKLIST DE TEST (à faire TOUJOURS après installation)

Ouvre le site **en navigation privée** (Ctrl+Shift+N) :

- [ ] Le **widget apparaît** sur la page
- [ ] Le **chatbot s'ouvre** quand on clique
- [ ] L'**accueil** s'affiche au nom du client (logo + message)
- [ ] **1 message envoyé → réponse** en quelques secondes
- [ ] Les **5 questions** défilent
- [ ] Le **score** s'affiche en fin de parcours
- [ ] Le **bouton de rendez-vous** (Calendly) fonctionne si score ≥ seuil
- [ ] Le lead apparaît dans ton admin → **Leads** (envoie un message test)

> 💡 **Mode TEST** : dans ton admin (👁 Prévisualisation), active le **mode TEST**
> avant d'envoyer tes messages de test — ils iront dans `test_leads.csv` et ne
> pollueront pas les vrais leads. Passe en mode réel pour les vrais tests finaux.

### Après le test
1. Dans ton admin → **📦 Installation** → clique **« ✅ Installé »** (statut → INSTALLED).
2. Envoie au client un message type :
   ```
   ✅ C'est fait ! Votre assistant est en ligne sur [URL].
   Testez-le ici : [LIEN DE DÉMO]
   Il accueille vos visiteurs, pose 5 questions et réserve un rendez-vous
   aux projets sérieux. Vous suivez tout depuis votre tableau de bord.
   Je reste disponible si besoin. Bonne mise en ligne !
   ```
3. Si tu as utilisé les identifiants du client → **conseille-lui de changer son mot de passe**.

---

## 🆘 DÉPANNAGE RAPIDE

| Problème | Cause probable | Solution |
|---|---|---|
| Widget invisible | Page non publiée / cache | Vérifie « Publier », vide le cache (Ctrl+F5 ou navigation privée) |
| Code collé mais rien | Bloc coupé/modifié | Recolle le code complet d'un seul coup (entre `<!-- MaisonNova AI -->` et `</script>`) |
| Widget coupé | Conteneur trop petit | Agrandis le bloc / l'embed (le widget fait 460×620) |
| Le chat ne répond pas | Site en cache, ou clé absente | Recharge ; vérifie que la clé est dans le code (elle y est incluse automatiquement) |
| Erreur affichée | Ancien code / mauvaise URL | Recopie le code depuis l'onglet Installation de l'admin |
| Le site du client est géré par un tiers | Accès limité | Envoie `instructions_webmaster/webmaster.txt` au prestataire |

---

## 📦 À REMETTRE AU CLIENT APRÈS INSTALLATION

- [ ] Son **lien de démo** (URL publique — aucun mot de passe requis)
- [ ] Son **dossier client ZIP** (guide interactif + LISEZ-MOI) — même si tu as installé toi-même, ça lui sert de documentation
- [ ] Ses **accès admin** (s'il veut suivre ses leads lui-même)
- [ ] Le rappel : « Vous n'avez rien à faire, tout est en ligne. »

---

*MaisonNova AI — Installation directe, résultat professionnel.*
