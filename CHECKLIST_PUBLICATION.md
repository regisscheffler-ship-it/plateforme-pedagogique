# ✅ CHECKLIST DE PUBLICATION
## Lycée Louis Loucheur - Plateforme Pédagogique

### 🔒 **SÉCURITÉ (CRITIQUE)**

- [ ] `DEBUG = False` dans `settings.py`
- [ ] `SECRET_KEY` générée aléatoirement et gardée secrète
- [ ] `ALLOWED_HOSTS` configuré avec le domaine de production
- [ ] Supprimer tous les `print()` de debug dans `views.py`
- [ ] Aucun mot de passe en dur dans le code
- [ ] `.env` créé pour les variables sensibles (et `.env` dans `.gitignore`)

### 📦 **BASE DE DONNÉES**

- [ ] Toutes les migrations appliquées : `python manage.py migrate`
- [ ] Superuser créé : `python manage.py createsuperuser`
- [ ] Sauvegarde de la base de données effectuée
- [ ] Données de test supprimées (optionnel)

### 🎨 **FICHIERS STATIQUES**

- [ ] `python manage.py collectstatic` exécuté sans erreur
- [ ] Logo du lycée présent dans `/static/images/`
- [ ] Favicon configuré
- [ ] CSS de la charte graphique intégré dans `base.html`

### 🧪 **TESTS FONCTIONNELS (Sample à tester manuellement)**

**Professeur :**
- [ ] Connexion professeur fonctionne
- [ ] Création d'une classe
- [ ] Ajout d'un élève
- [ ] Création d'un thème
- [ ] Ajout d'un fichier (PDF, lien, iframe)
- [ ] Création d'une évaluation complète (Paramètres → Saisie → Impression)
- [ ] Archivage d'une évaluation
- [ ] Marquer un élève comme sorti

**Élève :**
- [ ] Inscription élève fonctionne
- [ ] Approbation professeur fonctionne
- [ ] Connexion élève fonctionne
- [ ] Dashboard élève affiche les cours
- [ ] Rendu d'un travail fonctionne
- [ ] Notifications reçues (évaluation archivée, travail corrigé)

### 📄 **PAGES CLÉS (vérifier qu'elles chargent sans erreur 500)**

- [ ] `/` (Accueil)
- [ ] `/login/professeur/`
- [ ] `/login/eleve/`
- [ ] `/dashboard/professeur/`
- [ ] `/dashboard/eleve/`
- [ ] `/gestion/classes/`
- [ ] `/gestion/eleves/`
- [ ] `/evaluations/`
- [ ] `/archives/`
- [ ] `/gestion/sorties/`

### 🎨 **COHÉRENCE VISUELLE**

- [ ] Toutes les pages utilisent `base.html`
- [ ] Couleur primaire (#20c997) appliquée partout
- [ ] Boutons homogènes (style, taille, couleurs)
- [ ] Polices cohérentes
- [ ] Espacements réguliers entre sections
- [ ] Responsive testé sur mobile

### 📝 **CONTENU & TEXTES**

- [ ] Aucun Lorem Ipsum ou texte de placeholder
- [ ] Messages d'erreur en français
- [ ] Emails de notification configurés (si applicable)
- [ ] Footer avec l'année 2025 et copyright
- [ ] Page de contact fonctionnelle

### 🚀 **PERFORMANCE**

- [ ] Images optimisées (< 500KB chacune)
- [ ] Aucune requête N+1 évidente (utiliser `select_related` / `prefetch_related`)
- [ ] Pagination activée sur les grandes listes (> 50 items)

### 📊 **MONITORING**

- [ ] Logs d'erreurs configurés
- [ ] Email d'admin configuré pour recevoir les erreurs 500
- [ ] Google Analytics ajouté (optionnel)

### 📚 **DOCUMENTATION**

- [ ] README.md créé avec instructions d'installation
- [ ] Liste des dépendances dans `requirements.txt`
- [ ] Variables d'environnement documentées

---

## 🚀 COMMANDES FINALES AVANT PUBLICATION

```bash
# 1. Tests automatiques
bash test_pre_publication.sh

# 2. Audit du code
python audit_code.py

# 3. Collecte des fichiers statiques
python manage.py collectstatic --noinput

# 4. Vérification finale
python manage.py check --deploy

# 5. Redémarrer le serveur
# (commande dépend de votre hébergement : gunicorn, uwsgi, etc.)
```

---

## ✅ PRÊT À PUBLIER !

Une fois toutes les cases cochées, votre site est prêt pour la production.

**Bon lancement ! 🎉**
