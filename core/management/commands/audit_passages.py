from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import timedelta

from core.models import HistoriqueClasse, ProfilUtilisateur


class Command(BaseCommand):
    help = 'Lister les passages de classes récents et (optionnel) annuler le dernier passage pour un élève.'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=7, help='Nombre de jours à remonter (défaut: 7)')
        parser.add_argument('--eleve', type=int, help='ID de l\'élève pour lequel annuler le dernier passage')
        parser.add_argument('--revert', action='store_true', help='Si présent avec --eleve, applique le revert')

    def handle(self, *args, **options):
        days = options['days']
        eleve_id = options.get('eleve')
        do_revert = options.get('revert')

        since = timezone.now().date() - timedelta(days=days)
        qs = HistoriqueClasse.objects.filter(date_debut__gte=since).order_by('-date_debut')

        if not qs.exists():
            self.stdout.write(self.style.NOTICE(f'Aucun historique de passage trouvé depuis {days} jours.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Historique des passages depuis {since} (ordre récent → ancien):'))
            for h in qs.select_related('eleve', 'classe')[:200]:
                eleve = h.eleve
                classe = h.classe.nom if h.classe else '—'
                self.stdout.write(f'  id={eleve.id} — {eleve.user.get_full_name()} : {classe} — {h.date_debut} (redoublement={h.redoublement})')

        if eleve_id:
            try:
                profil = ProfilUtilisateur.objects.get(pk=eleve_id)
            except ProfilUtilisateur.DoesNotExist:
                raise CommandError(f"Profil élève id={eleve_id} introuvable")

            hist = HistoriqueClasse.objects.filter(eleve=profil).order_by('-date_debut')
            if not hist.exists():
                self.stdout.write(self.style.ERROR('Aucun historique pour cet élève.'))
                return

            last = hist[0]
            prev = hist[1] if hist.count() > 1 else None

            self.stdout.write(self.style.NOTICE(f'Dernier passage: {last.date_debut} → classe: {last.classe}'))
            if prev:
                self.stdout.write(self.style.NOTICE(f'Classe précédente: {prev.date_debut} → {prev.classe}'))
            else:
                self.stdout.write(self.style.NOTICE('Pas de classe précédente disponible (aucun historique antérieur).'))

            if do_revert:
                if not prev or prev.classe is None:
                    self.stdout.write(self.style.ERROR('Impossible de revert : classe précédente introuvable.'))
                    return
                # Appliquer revert : remettre la classe précédente
                profil.classe = prev.classe
                profil.save()
                self.stdout.write(self.style.SUCCESS(f'✔ Élève id={profil.id} remis dans la classe {prev.classe}'))
            else:
                self.stdout.write(self.style.NOTICE('Pour appliquer le revert, relancer avec --eleve <id> --revert'))
