import os
from datetime import date
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Exporte un ZIP complet de fin d'année sur le bureau"

    def add_arguments(self, parser):
        parser.add_argument(
            '--annee',
            type=str,
            default='',
            help='Année scolaire (ex: 2024-2025). Auto-détectée si vide.',
        )
        parser.add_argument(
            '--output',
            type=str,
            default='',
            help='Chemin du fichier ZIP de sortie. Par défaut: Bureau.',
        )
        parser.add_argument(
            '--archives-only',
            action='store_true',
            help='Exporter uniquement les archives (plus rapide).',
        )

    def handle(self, *args, **options):
        from core.utils_export import generer_zip_complet, generer_zip_archives

        # ── Déterminer l'année ──
        annee = options.get('annee')
        if not annee:
            today = date.today()
            if today.month >= 9:
                annee = f"{today.year}-{today.year + 1}"
            else:
                annee = f"{today.year - 1}-{today.year}"

        self.stdout.write(f"\n{'=' * 50}")
        self.stdout.write(f"  EXPORT ANNUEL — {annee}")
        self.stdout.write(f"{'=' * 50}\n")

        # ── Déterminer le chemin de sortie ──
        output = options.get('output')
        if not output:
            # Bureau Windows / Linux / Mac
            desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
            if not os.path.isdir(desktop):
                desktop = os.path.join(os.path.expanduser('~'), 'Bureau')
            if not os.path.isdir(desktop):
                desktop = os.getcwd()
            if options.get('archives_only'):
                output = os.path.join(desktop, f'archives_{annee}.zip')
            else:
                output = os.path.join(desktop, f'export_complet_{annee}.zip')

        # ── Générer le ZIP ──
        self.stdout.write("⏳ Génération en cours...\n")

        if options.get('archives_only'):
            self.stdout.write("   Mode : archives uniquement\n")
            zip_bytes, nb, errs = generer_zip_archives(annee)
        else:
            self.stdout.write("   Mode : export COMPLET\n")
            zip_bytes, nb, errs = generer_zip_complet(annee)

        if (nb == 0 and not zip_bytes) or zip_bytes is None:
            raise CommandError(f"Aucun document trouvé pour {annee}.")

        # ── Écrire le fichier ──
        with open(output, 'wb') as f:
            f.write(zip_bytes)

        # ── Résumé ──
        size_mb = len(zip_bytes) / (1024 * 1024)
        self.stdout.write(self.style.SUCCESS(f"\n✅ Export terminé !"))
        self.stdout.write(f"   📁 Fichier  : {output}")
        self.stdout.write(f"   📊 Contenu  : {nb} fichiers")
        self.stdout.write(f"   💾 Taille   : {size_mb:.1f} Mo")

        if errs:
            self.stdout.write(self.style.WARNING(
                f"\n⚠️  {len(errs)} fichier(s) impossible(s) à lire :"
            ))
            for e in errs:
                self.stdout.write(f"   • {e}")

        self.stdout.write("")


# Utilisation :
#
# Export complet sur le Bureau
# python manage.py export_annuel
#
# Avec une année précise
# python manage.py export_annuel --annee 2024-2025
#
# Archives seules (plus rapide)
# python manage.py export_annuel --annee 2024-2025 --archives-only
#
# Vers un dossier spécifique
# python manage.py export_annuel --output C:\\Users\\regis\\Documents\\export.zip
#
# Remarque : la commande se connecte à la base et au stockage (Cloudinary) —
# fournissez votre fichier .env avec les variables de prod si nécessaire.
