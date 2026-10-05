from django.db import migrations


def copier_classes_themes_vers_dossiers(apps, schema_editor):
    Dossier = apps.get_model('core', 'Dossier')
    through = Dossier.classes.through
    dossiers_configures = set(through.objects.values_list('dossier_id', flat=True).distinct())
    liens = []
    for dossier in Dossier.objects.select_related('theme').iterator():
        if dossier.pk in dossiers_configures:
            continue
        classe_ids = dossier.theme.classes.values_list('pk', flat=True)
        liens.extend(
            through(dossier_id=dossier.pk, classe_id=classe_id)
            for classe_id in classe_ids
        )
    through.objects.bulk_create(liens, ignore_conflicts=True)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0040_alter_theme_options_dossier_classes'),
    ]

    operations = [
        migrations.RunPython(copier_classes_themes_vers_dossiers, migrations.RunPython.noop),
    ]
