# Script pour créer les données de base
# À exécuter avec : python manage.py shell

from core.models import Niveau, TypeRessource

print("=" * 80)
print("CRÉATION DES DONNÉES DE BASE")
print("=" * 80)
print()

# 1. CRÉER LE NIVEAU UNIQUE
print("1. Création du niveau...")
niveau, created = Niveau.objects.get_or_create(
    nom="Lycée Professionnel",
    defaults={'actif': True}
)
if created:
    print("   ✅ Niveau 'Lycée Professionnel' créé")
else:
    print("   ℹ️  Niveau 'Lycée Professionnel' existe déjà")
print()

# 2. CRÉER LES TYPES DE RESSOURCES
print("2. Création des types de ressources...")
types_ressources = [
    "PDF",
    "Vidéo",
    "Lien Web",
    "Image",
    "Document Word",
    "Document Excel",
    "Présentation PowerPoint",
    "Exercice",
    "Cours",
    "TP",
]

for nom in types_ressources:
    type_res, created = TypeRessource.objects.get_or_create(
        nom=nom,
        defaults={'actif': True}
    )
    if created:
        print(f"   ✅ Type '{nom}' créé")
    else:
        print(f"   ℹ️  Type '{nom}' existe déjà")

print()
print("=" * 80)
print("✅ DONNÉES DE BASE CRÉÉES AVEC SUCCÈS !")
print("=" * 80)
print()
print("🚀 PROCHAINE ÉTAPE :")
print("   1. Lancez le serveur : python manage.py runserver")
print("   2. Connectez-vous : http://127.0.0.1:8000/login/")
print("   3. Username : admin")
print("   4. Créez vos classes, élèves, thèmes...")
print()
