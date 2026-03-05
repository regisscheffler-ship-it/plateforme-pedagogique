#!/bin/bash
# Script de vérification pré-publication
# Usage: bash test_pre_publication.sh dans le dossier du projet Django

echo "========================================="
echo "🔍 VÉRIFICATION PRÉ-PUBLICATION"
echo "========================================="
echo ""

# 1. Vérification de la structure Django
echo "📋 1/5 - Vérification de la configuration Django..."
python manage.py check --deploy
if [ $? -eq 0 ]; then
    echo "✅ Configuration OK"
else
    echo "❌ Erreurs de configuration détectées"
    exit 1
fi
echo ""

# 2. Vérification des migrations
echo "📋 2/5 - Vérification des migrations..."
python manage.py makemigrations --check --dry-run
if [ $? -eq 0 ]; then
    echo "✅ Migrations à jour"
else
    echo "⚠️ Migrations manquantes détectées"
fi
echo ""

# 3. Vérification des URLs
echo "📋 3/5 - Vérification des URLs..."
python manage.py show_urls > /dev/null 2>&1 || python manage.py validate_templates > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ URLs OK"
else
    echo "⚠️ Certaines URLs pourraient être invalides"
fi
echo ""

# 4. Vérification des fichiers statiques
echo "📋 4/5 - Collecte des fichiers statiques (test)..."
python manage.py collectstatic --noinput --dry-run > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Fichiers statiques OK"
else
    echo "⚠️ Problème avec les fichiers statiques"
fi
echo ""

# 5. Vérification des templates
echo "📋 5/5 - Vérification des templates..."
python -c "
from django.template.loader import get_template
from django.conf import settings
import os

errors = []
template_dirs = settings.TEMPLATES[0]['DIRS']
for template_dir in template_dirs:
    if os.path.exists(template_dir):
        for root, dirs, files in os.walk(template_dir):
            for file in files:
                if file.endswith('.html'):
                    template_path = os.path.join(root, file).replace(template_dir + '/', '')
                    try:
                        get_template(template_path)
                    except Exception as e:
                        errors.append(f'{template_path}: {str(e)}')

if errors:
    print('❌ Erreurs dans les templates:')
    for err in errors[:10]:  # Limite à 10 erreurs
        print(f'  - {err}')
else:
    print('✅ Templates OK')
" 2>&1
echo ""

echo "========================================="
echo "✅ VÉRIFICATION TERMINÉE"
echo "========================================="