Déploiement sur Render — Playwright (Chromium) / WeasyPrint

Résumé
- Choix simple: `WeasyPrint` (plus léger, facile à déployer) — recommandé ici pour simplicité.
- Si vous avez besoin d'une fidélité parfaite au rendu navigateur, utilisez `Playwright` + Chromium (plus lourd).
Docker est la façon la plus fiable sur Render (installe les dépendances système requises).

Fichiers ajoutés
- `Dockerfile` (par défaut, WeasyPrint — plus simple)
- `Dockerfile.playwright` (identique au `Dockerfile`)
- `Dockerfile.weasyprint` (variante WeasyPrint)
- `requirements.txt` mis à jour (ajoute `playwright`, `weasyprint`, `cairocffi`)

Render — configuration Docker (recommandée)
1) Dans le dashboard Render, créez un nouveau service Web en choisissant "Docker".
2) Pointez vers votre repository et branche `main`.
3) Render utilisera automatiquement le `Dockerfile` à la racine.
4) Variables d'environnement recommandées:
   - `DJANGO_SETTINGS_MODULE=plateforme.settings`
   - `SECRET_KEY` (value secret)
   - `DATABASE_URL` (postgres)
   - `CLOUDINARY_URL` ou autres selon usage
5) CPU/mémoire: choisir au minimum 1 CPU / 1GB RAM; pour Playwright/Chromium préférez 2GB si possible (Chromium peut consommer mémoire lors de PDF).

Build commands (si vous n'utilisez pas Docker)
- Playwright path (nécessite apt install sur l'image):

```bash
pip install -r requirements.txt
python -m playwright install --with-deps chromium
```

- WeasyPrint path (nécessite apt install natif):

```bash
apt-get update && apt-get install -y libcairo2 libpango-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info fonts-dejavu-core
pip install -r requirements.txt
```

Tests locaux rapides
- Construire l'image Docker (Playwright):

```bash
docker build -t pp-playwright -f Dockerfile .
docker run --rm -p 8000:8000 pp-playwright
```

- Ou tester Playwright local sans Docker (après `pip install -r requirements.txt`):

```bash
python -m pip install -r requirements.txt
python -m playwright install chromium
python manage.py runserver
# appeler /core/evaluations/<id>/export-archive/ pour vérifier le ZIP et les PDFs
```

Dépannage
- Si l'archive contient encore `.html`:
  - vérifier les logs pour erreurs dans la fonction `html_to_pdf_bytes` (tracebacks indiquant e.g. `playwright` non installé ou `WeasyPrint` absent).
  - pour Playwright: vérifier que `python -m playwright install --with-deps chromium` a bien tourné pendant le build.
  - pour WeasyPrint: vérifier la présence des bibliothèques natives (`cairo`, `pango`).

Alternatives
- Si Render impose des limites, utiliser un service externe pour la génération PDF (ex: un petit service Docker sur un VPS ou un worker Heroku/Render dédié avec plus de mémoire).

Souhaitez-vous que je :
- génère une PR contenant ces fichiers et un `render.md` plus détaillé (avec captures d'écran de la console Render) ?
- ou que je lance localement un build Docker ici et teste l'endpoint (si votre machine autorise Docker) ?
