from django.db import migrations, transaction


def forward(apps, schema_editor):
    EvaluationLigne = apps.get_model('core', 'EvaluationLigne')
    FicheEvaluation = apps.get_model('core', 'FicheEvaluation')

    with transaction.atomic():
        EvaluationLigne.objects.all().update(note='NE')

        FicheEvaluation.objects.all().update(
            note_sur_20=None,
            validee=False,
            date_validation=None
        )


def reverse(apps, schema_editor):
    # restauration non triviale — noop
    return


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0020_add_messageeleve_reponseprof'),
    ]

    operations = [
        migrations.RunPython(forward, reverse_code=reverse),
    ]
