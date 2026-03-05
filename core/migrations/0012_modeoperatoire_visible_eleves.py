from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_modeoperatoire_lignemodeoperatoire'),
    ]

    operations = [
        migrations.AddField(
            model_name='modeoperatoire',
            name='visible_eleves',
            field=models.BooleanField(default=False, verbose_name='Visible aux élèves'),
        ),
    ]
