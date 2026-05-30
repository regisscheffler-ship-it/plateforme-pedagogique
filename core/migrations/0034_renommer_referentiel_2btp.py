"""
Migration de données : renommage du référentiel 2BTP
"Compétences communes PFMP - 2BTP" → "Compétences communes - 2BTP"
"""

from django.db import migrations

ANCIEN_NOM = "Compétences communes PFMP - 2BTP"
NOUVEAU_NOM = "Compétences communes - 2BTP"


def renommer(apps, schema_editor):
    Referentiel = apps.get_model("core", "Referentiel")
    updated = Referentiel.objects.filter(nom=ANCIEN_NOM).update(nom=NOUVEAU_NOM)
    if updated:
        print(f"  [OK] Référentiel renommé : '{NOUVEAU_NOM}'")
    else:
        print(f"  [SKIP] Référentiel '{ANCIEN_NOM}' introuvable (déjà renommé ?)")


def annuler(apps, schema_editor):
    Referentiel = apps.get_model("core", "Referentiel")
    Referentiel.objects.filter(nom=NOUVEAU_NOM).update(nom=ANCIEN_NOM)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0033_referentiel_2btp_connaissances"),
    ]

    operations = [
        migrations.RunPython(renommer, reverse_code=annuler),
    ]
