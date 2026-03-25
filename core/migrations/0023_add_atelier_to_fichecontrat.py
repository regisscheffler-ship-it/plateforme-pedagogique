from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0022_alter_evaluationligne_note'),
    ]

    operations = [
        migrations.AddField(
            model_name='fichecontrat',
            name='atelier',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='fiches_contrat',
                to='core.atelier',
                verbose_name='Atelier lié',
            ),
        ),
    ]
