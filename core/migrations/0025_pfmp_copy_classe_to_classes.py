"""
Data migration : copie PFMP.classe (FK) → PFMP.classes (M2M).
"""
from django.db import migrations


def forwards(apps, schema_editor):
    PFMP = apps.get_model('core', 'PFMP')
    for pfmp in PFMP.objects.all():
        if pfmp.classe_id:
            pfmp.classes.add(pfmp.classe_id)


def backwards(apps, schema_editor):
    PFMP = apps.get_model('core', 'PFMP')
    for pfmp in PFMP.objects.all():
        first = pfmp.classes.first()
        if first:
            pfmp.classe_id = first.id
            pfmp.save(update_fields=['classe_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0024_pfmp_add_classes_m2m'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
