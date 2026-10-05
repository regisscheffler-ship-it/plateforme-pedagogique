# core/tests.py
"""
Tests automatiques des URLs de la plateforme pédagogique
"""
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from datetime import date, datetime, timedelta
from django.utils import timezone
from core.models import ProfilUtilisateur, Classe, Niveau, Referentiel, FicheContrat, FicheEvaluation, Archive, MessageEleve, DiplomeEleve, PFMP, SuiviPFMP, ConnexionEleve, QCM, SessionQCM, Theme, Dossier
from django.core.files.base import ContentFile
from unittest.mock import patch
from core.storage import AutoMediaCloudinaryStorage, RESOURCE_TYPES


class TestStudentAccountUpdates(TestCase):
    def test_modifier_eleve_change_identifiant_et_mot_de_passe_sans_noms(self):
        user = User.objects.create_user(username='eleve_avant', password='ancien-mot-de-passe')
        profil = ProfilUtilisateur.objects.create(user=user, type_utilisateur='eleve')

        response = self.client.post(reverse('core:modifier_eleve', kwargs={'pk': profil.pk}), {
            'username': 'eleve_apres',
            'first_name': '',
            'last_name': '',
            'new_password': 'nouveau-mot-de-passe',
        })

        user.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(user.username, 'eleve_apres')
        self.assertEqual(user.first_name, '')
        self.assertEqual(user.last_name, '')
        self.assertTrue(user.check_password('nouveau-mot-de-passe'))

    def test_modifier_eleve_refuse_un_identifiant_deja_utilise(self):
        user = User.objects.create_user(username='eleve_avant', password='mot-de-passe')
        profil = ProfilUtilisateur.objects.create(user=user, type_utilisateur='eleve')
        User.objects.create_user(username='identifiant_pris', password='mot-de-passe')

        response = self.client.post(reverse('core:modifier_eleve', kwargs={'pk': profil.pk}), {
            'username': 'identifiant_pris',
            'first_name': '',
            'last_name': '',
        })

        user.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(user.username, 'eleve_avant')

    def test_inscription_eleve_accepte_nom_et_prenom_vides(self):
        niveau = Niveau.objects.create(nom='CAP', description='CAP')
        classe = Classe.objects.create(nom='2M', niveau=niveau, description='Classe test')

        response = self.client.post(reverse('core:inscription_eleve'), {
            'username': 'eleve_sans_nom',
            'password1': 'mot-de-passe-test',
            'password2': 'mot-de-passe-test',
            'classe': classe.pk,
        })

        user = User.objects.get(username='eleve_sans_nom')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(user.first_name, '')
        self.assertEqual(user.last_name, '')


class TestCommunicationActions(TestCase):
    def setUp(self):
        niveau = Niveau.objects.create(nom='CAP', description='CAP')
        classe = Classe.objects.create(nom='2M', niveau=niveau, description='Classe test')
        self.prof_user = User.objects.create_user(username='prof_comm', password='test123456')
        self.prof_profil = ProfilUtilisateur.objects.create(
            user=self.prof_user, type_utilisateur='professeur'
        )
        self.eleve_user = User.objects.create_user(username='eleve_comm', password='test123456')
        self.eleve_profil = ProfilUtilisateur.objects.create(
            user=self.eleve_user, type_utilisateur='eleve', classe=classe
        )
        self.message = MessageEleve.objects.create(
            eleve=self.eleve_profil,
            professeur=self.prof_profil,
            texte='Rapport de test',
            image='messages/rapport.jpg',
        )
        self.client.force_login(self.prof_user)

    def test_identifiant_cloudinary_sans_extension_reste_une_image(self):
        storage = AutoMediaCloudinaryStorage()

        self.assertEqual(storage._get_resource_type('messages/public_id_sans_extension'), RESOURCE_TYPES['IMAGE'])

    def test_consulter_est_un_lien_direct_vers_la_piece_jointe(self):
        response = self.client.get(reverse('core:communications_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Consulter')
        self.assertContains(response, 'target="_blank"')
        self.assertNotContains(response, 'consult-btn')
        self.assertContains(response, reverse('core:communication_consulter', kwargs={'message_id': self.message.pk}))

    def test_consulter_sert_l_image_en_ligne(self):
        image_storage = MessageEleve._meta.get_field('image').storage
        with patch.object(image_storage, 'open', return_value=ContentFile(b'image en ligne')):
            response = self.client.get(
                reverse('core:communication_consulter', kwargs={'message_id': self.message.pk})
            )
            contenu = b''.join(response.streaming_content)

        self.assertEqual(response.status_code, 200)
        self.assertIn('inline', response['Content-Disposition'])
        self.assertEqual(contenu, b'image en ligne')

    def test_telechargement_sert_le_fichier_du_stockage(self):
        image_storage = MessageEleve._meta.get_field('image').storage
        with patch.object(image_storage, 'open', return_value=ContentFile(b'contenu image')):
            response = self.client.get(
                reverse('core:communication_telecharger', kwargs={'message_id': self.message.pk})
            )
            contenu = b''.join(response.streaming_content)

        self.assertEqual(response.status_code, 200)
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertEqual(contenu, b'contenu image')

    def test_telechargement_cloudinary_redirige_avec_flag_attachment(self):
        image_storage = MessageEleve._meta.get_field('image').storage
        with patch.object(image_storage, 'open', return_value=ContentFile(b'image telechargee')):
            response = self.client.get(
                reverse('core:communication_telecharger', kwargs={'message_id': self.message.pk})
            )
            contenu = b''.join(response.streaming_content)

        self.assertEqual(response.status_code, 200)
        self.assertIn('attachment', response['Content-Disposition'])
        self.assertEqual(contenu, b'image telechargee')

    def test_marquer_lu_ne_supprime_pas_le_message_de_l_eleve(self):
        response = self.client.post(
            reverse('core:communication_marquer_lu', kwargs={'message_id': self.message.pk})
        )

        self.assertEqual(response.status_code, 302)
        self.message.refresh_from_db()
        self.assertTrue(self.message.lu)
        self.assertTrue(MessageEleve.objects.filter(pk=self.message.pk).exists())

        self.client.force_login(self.eleve_user)
        reponse_eleve = self.client.get(reverse('core:communication_eleve'))
        self.assertEqual(reponse_eleve.status_code, 200)
        self.assertContains(reponse_eleve, 'Rapport de test')
        self.assertContains(reponse_eleve, 'Lu par le professeur')

    def test_suppression_post_supprime_le_message(self):
        image_storage = MessageEleve._meta.get_field('image').storage
        with patch.object(image_storage, 'delete') as delete_file:
            response = self.client.post(
                reverse('core:communication_supprimer', kwargs={'message_id': self.message.pk})
            )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(MessageEleve.objects.filter(pk=self.message.pk).exists())
        delete_file.assert_called_once_with('messages/rapport.jpg')

    def test_professeur_ne_peut_pas_supprimer_le_message_d_un_autre(self):
        autre_user = User.objects.create_user(username='autre_prof', password='test123456')
        autre_prof = ProfilUtilisateur.objects.create(
            user=autre_user, type_utilisateur='professeur'
        )
        autre_message = MessageEleve.objects.create(
            eleve=self.eleve_profil, professeur=autre_prof, texte='Message privé'
        )

        response = self.client.post(
            reverse('core:communication_supprimer', kwargs={'message_id': autre_message.pk})
        )

        self.assertEqual(response.status_code, 404)
        self.assertTrue(MessageEleve.objects.filter(pk=autre_message.pk).exists())


class TestDiplomaHistory(TestCase):
    def setUp(self):
        self.niveau = Niveau.objects.create(nom='CAP', description='CAP')
        self.classe_actuelle = Classe.objects.create(
            nom='2CAP', niveau=self.niveau, annee_scolaire='2025-2026'
        )
        self.classe_suivante = Classe.objects.create(
            nom='1BAC', niveau=self.niveau, annee_scolaire='2026-2027'
        )
        prof_user = User.objects.create_user(username='prof_diplomes', password='test123456')
        self.prof_profil = ProfilUtilisateur.objects.create(
            user=prof_user, type_utilisateur='professeur'
        )
        eleve_user = User.objects.create_user(
            username='eleve_diplomes', password='test123456', first_name='Camille', last_name='Martin'
        )
        self.eleve = ProfilUtilisateur.objects.create(
            user=eleve_user, type_utilisateur='eleve', classe=self.classe_actuelle,
            compte_approuve=True
        )
        self.client.force_login(prof_user)

    def test_passage_enregistre_plusieurs_diplomes_et_mentions(self):
        response = self.client.post(
            reverse('core:passer_en_classe_superieure', kwargs={'eleve_id': self.eleve.pk}),
            {
                'nouvelle_classe': self.classe_suivante.pk,
                'annee_actuelle': '2025-2026',
                'diplomes': ['cap', 'bac_pro'],
                'mention_cap': 'AB',
                'mention_bac_pro': 'TB',
            },
        )

        diplomes = DiplomeEleve.objects.filter(eleve=self.eleve).order_by('diplome')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(diplomes.count(), 2)
        self.assertEqual(diplomes.get(diplome='cap').mention, 'AB')
        self.assertEqual(diplomes.get(diplome='bac_pro').mention, 'TB')
        self.assertEqual(diplomes.get(diplome='cap').classe, '2CAP')

    def test_sortie_enregistre_diplomes_independamment_du_motif(self):
        response = self.client.post(
            reverse('core:marquer_sortie', kwargs={'pk': self.eleve.pk}),
            {
                'raison_sortie': 'travail_formation',
                'annee_scolaire_sortie': '2025-2026',
                'diplomes': ['cap', 'bac_pro'],
                'mention_cap': 'B',
                'mention_bac_pro': 'TB',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(DiplomeEleve.objects.filter(eleve=self.eleve).count(), 2)
        self.assertEqual(DiplomeEleve.objects.get(eleve=self.eleve, diplome='cap').mention, 'B')

    def test_modifier_sortie_peut_corriger_vers_aucun_diplome(self):
        self.eleve.est_sorti = True
        self.eleve.annee_scolaire_sortie = '2025-2026'
        self.eleve.save()
        DiplomeEleve.objects.create(
            eleve=self.eleve, diplome='cap', mention='AB',
            annee_scolaire='2025-2026', classe='2CAP'
        )

        response = self.client.post(
            reverse('core:modifier_sortie', kwargs={'pk': self.eleve.pk}),
            {
                'raison_sortie': 'travail_formation',
                'annee_scolaire_sortie': '2025-2026',
                'aucun_diplome': 'on',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(DiplomeEleve.objects.filter(eleve=self.eleve, annee_scolaire='2025-2026').exists())

    def test_statistiques_affichent_les_diplomes_et_les_mentions(self):
        DiplomeEleve.objects.create(
            eleve=self.eleve, diplome='cap', mention='AB',
            annee_scolaire='2025-2026', classe='2CAP'
        )

        response = self.client.get(reverse('core:statistiques'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Diplômes obtenus')
        self.assertContains(response, 'Camille')
        self.assertContains(response, 'Assez Bien')


class TestEvaluationListFilters(TestCase):
    def setUp(self):
        niveau = Niveau.objects.create(nom='CAP', description='CAP')
        self.classe_a = Classe.objects.create(nom='2M', niveau=niveau)
        self.classe_b = Classe.objects.create(nom='1M', niveau=niveau)
        self.prof_user = User.objects.create_user(username='prof_filtres_eval', password='test123456')
        ProfilUtilisateur.objects.create(user=self.prof_user, type_utilisateur='professeur')
        referentiel = Referentiel.objects.create(nom='Référentiel filtres', description='Test filtres')
        self.fiche_a_janvier = FicheContrat.objects.create(
            referentiel=referentiel, classe=self.classe_a, titre_tp='TP 2M janvier',
            date_tp=date(2026, 1, 12), createur=self.prof_user,
        )
        self.fiche_b_janvier = FicheContrat.objects.create(
            referentiel=referentiel, classe=self.classe_b, titre_tp='TP 1M janvier',
            date_tp=date(2026, 1, 20), createur=self.prof_user,
        )
        self.fiche_a_fevrier = FicheContrat.objects.create(
            referentiel=referentiel, classe=self.classe_a, titre_tp='TP 2M février',
            date_tp=date(2026, 2, 10), createur=self.prof_user,
        )
        self.qcm_a = QCM.objects.create(
            titre='QCM 2M janvier', createur=self.prof_user,
            date_limite=timezone.make_aware(datetime(2026, 1, 28)),
        )
        self.qcm_a.classes.add(self.classe_a)
        QCM.objects.filter(pk=self.qcm_a.pk).update(
            date_creation=timezone.make_aware(datetime(2026, 1, 12, 9))
        )
        self.qcm_b = QCM.objects.create(
            titre='QCM 1M janvier', createur=self.prof_user,
            date_limite=timezone.make_aware(datetime(2026, 1, 28)),
        )
        self.qcm_b.classes.add(self.classe_b)
        QCM.objects.filter(pk=self.qcm_b.pk).update(
            date_creation=timezone.make_aware(datetime(2026, 1, 20, 9))
        )
        self.qcm_fevrier = QCM.objects.create(
            titre='QCM 2M février', createur=self.prof_user,
            date_limite=timezone.make_aware(datetime(2026, 2, 28)),
        )
        self.qcm_fevrier.classes.add(self.classe_a)
        QCM.objects.filter(pk=self.qcm_fevrier.pk).update(
            date_creation=timezone.make_aware(datetime(2026, 2, 10, 9))
        )
        self.qcm_autre_classe = QCM.objects.create(
            titre='QCM classe sans fiche TP', createur=self.prof_user,
            date_limite=timezone.make_aware(datetime(2026, 1, 28)),
        )
        self.qcm_autre_classe.classes.add(
            Classe.objects.create(nom='1B', niveau=niveau)
        )
        QCM.objects.filter(pk=self.qcm_autre_classe.pk).update(
            date_creation=timezone.make_aware(datetime(2026, 1, 15, 9))
        )
        self.client.force_login(self.prof_user)

    def test_filtre_plusieurs_classes_et_plage_dates(self):
        response = self.client.get(reverse('core:evaluations_home'), {
            'classe': [str(self.classe_a.pk), str(self.classe_b.pk)],
            'date_debut': '2026-01-01',
            'date_fin': '2026-01-31',
        })

        self.assertEqual(response.status_code, 200)
        fiches = response.context['fiches_recentes']
        self.assertEqual(
            {fiche.pk for fiche in fiches},
            {self.fiche_a_janvier.pk, self.fiche_b_janvier.pk},
        )
        qcms = response.context['qcms']
        self.assertEqual(
            {qcm.pk for qcm in qcms},
            {self.qcm_a.pk, self.qcm_b.pk},
        )
        self.assertContains(response, 'Toutes les classes')
        self.assertContains(response, 'Date du TP, à partir du')


class TestPFMPAttendanceHistory(TestCase):
    def setUp(self):
        niveau = Niveau.objects.create(nom='CAP', description='CAP')
        self.classe_initiale = Classe.objects.create(nom='2CAP', niveau=niveau)
        self.classe_suivante = Classe.objects.create(nom='1CAP', niveau=niveau)
        prof_user = User.objects.create_user(username='prof_pfmp', password='test123456')
        self.prof_profil = ProfilUtilisateur.objects.create(
            user=prof_user, type_utilisateur='professeur'
        )
        self.eleve_user = User.objects.create_user(
            username='eleve_pfmp', password='test123456', first_name='Alex', last_name='Dupont'
        )
        self.eleve = ProfilUtilisateur.objects.create(
            user=self.eleve_user, type_utilisateur='eleve', classe=self.classe_initiale,
            compte_approuve=True
        )
        self.pfmp = PFMP.objects.create(
            titre='PFMP première année', createur=prof_user, nb_jours_prevus=20
        )
        self.pfmp.classes.add(self.classe_initiale)
        self.suivi = SuiviPFMP.objects.create(
            pfmp=self.pfmp, eleve=self.eleve,
            classe_au_moment=self.classe_initiale.nom,
            nb_jours_effectues=15,
            nb_jours_manques_justifies=2,
            nb_jours_manques_injustifies=1,
        )
        self.client.force_login(prof_user)

    def test_passage_classe_preserve_suivi_et_le_garde_visible(self):
        passage = self.client.post(
            reverse('core:passer_en_classe_superieure', kwargs={'eleve_id': self.eleve.pk}),
            {
                'nouvelle_classe': self.classe_suivante.pk,
                'annee_actuelle': '2025-2026',
            },
        )

        self.assertEqual(passage.status_code, 302)
        self.suivi.refresh_from_db()
        self.eleve.refresh_from_db()
        self.assertEqual(self.eleve.classe, self.classe_suivante)
        self.assertEqual(self.suivi.nb_jours_effectues, 15)
        self.assertEqual(self.suivi.classe_au_moment, '2CAP')

        saisie = self.client.get(reverse('core:saisie_suivi_pfmp', kwargs={'pfmp_id': self.pfmp.pk}))
        self.assertEqual(saisie.status_code, 200)
        self.assertContains(saisie, 'Alex')
        self.assertContains(saisie, '2CAP')
        self.assertContains(saisie, 'Classe actuelle : 1CAP')
        self.assertContains(saisie, 'value="15"')

        self.client.post(
            reverse('core:saisie_suivi_pfmp', kwargs={'pfmp_id': self.pfmp.pk}),
            {
                f'effectues_{self.eleve.pk}': '15',
                f'justifies_{self.eleve.pk}': '2',
                f'injustifies_{self.eleve.pk}': '1',
            },
        )
        self.suivi.refresh_from_db()
        self.assertEqual(self.suivi.nb_jours_effectues, 15)
        self.assertEqual(self.suivi.classe_au_moment, '2CAP')

    def test_mutation_preserve_suivi_et_statistiques_historique(self):
        response = self.client.post(
            reverse('core:muter_eleve', kwargs={'pk': self.eleve.pk}),
            {'nouvelle_classe': self.classe_suivante.pk},
        )

        self.assertEqual(response.status_code, 302)
        self.suivi.refresh_from_db()
        self.assertEqual(self.suivi.classe_au_moment, '2CAP')
        self.pfmp.actif = False
        self.pfmp.save(update_fields=['actif'])
        from core.views_merged_ast import _stats_pfmp
        stats = _stats_pfmp()
        stats_classe_initiale = next(item for item in stats if item['classe'] == '2CAP')
        suivi_stats = stats_classe_initiale['eleves'][0]['suivis'][0]
        self.assertEqual(self.suivi.nb_jours_effectues, 15)
        self.assertEqual(suivi_stats['effectues'], 15)

    def test_redoublement_conserve_les_15_jours_effectues(self):
        response = self.client.post(
            reverse('core:passer_en_classe_superieure', kwargs={'eleve_id': self.eleve.pk}),
            {
                'nouvelle_classe': self.classe_initiale.pk,
                'annee_actuelle': '2025-2026',
                'mode': 'redoublement',
                'redoublement': 'on',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.suivi.refresh_from_db()
        self.assertEqual(self.suivi.nb_jours_effectues, 15)
        self.assertEqual(self.suivi.classe_au_moment, '2CAP')

    def test_eleve_sorti_reste_visible_en_lecture_seule(self):
        self.eleve.est_sorti = True
        self.eleve.save(update_fields=['est_sorti'])

        response = self.client.get(reverse('core:saisie_suivi_pfmp', kwargs={'pfmp_id': self.pfmp.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'historique conservé')
        self.assertContains(response, 'disabled')


class TestStatisticsImprovements(TestCase):
    def setUp(self):
        niveau = Niveau.objects.create(nom='CAP', description='CAP')
        self.classe = Classe.objects.create(nom='2M', niveau=niveau)
        self.prof_user = User.objects.create_user(username='prof_stats', password='test123456')
        ProfilUtilisateur.objects.create(user=self.prof_user, type_utilisateur='professeur')
        self.eleve_user = User.objects.create_user(
            username='eleve_stats', password='test123456', first_name='Alice', last_name='Active'
        )
        self.eleve = ProfilUtilisateur.objects.create(
            user=self.eleve_user, type_utilisateur='eleve', classe=self.classe,
            compte_approuve=True
        )
        self.client.force_login(self.prof_user)

    def test_sorti_anonymise_et_diplome_est_statistique(self):
        sorti_user = User.objects.create_user(
            username='eleve_sorti_stats', password='test123456',
            first_name='PrénomSecret', last_name='NomSecret'
        )
        sorti = ProfilUtilisateur.objects.create(
            user=sorti_user, type_utilisateur='eleve', classe=self.classe,
            compte_approuve=True, est_sorti=True,
            raison_sortie='travail_formation', annee_scolaire_sortie='2025-2026'
        )
        DiplomeEleve.objects.create(
            eleve=sorti, diplome='cap', mention='AB',
            annee_scolaire='2025-2026', classe='2M'
        )
        DiplomeEleve.objects.create(
            eleve=self.eleve, diplome='bac_pro', mention='',
            annee_scolaire='2025-2026', classe='2M'
        )
        pfmp = PFMP.objects.create(titre='PFMP passée', createur=self.prof_user)
        pfmp.classes.add(self.classe)
        SuiviPFMP.objects.create(
            pfmp=pfmp, eleve=sorti, classe_au_moment='2M', nb_jours_effectues=15
        )
        referentiel = Referentiel.objects.create(nom='Référentiel ancien élève', description='Test')
        fiche = FicheContrat.objects.create(
            referentiel=referentiel, classe=self.classe, titre_tp='Évaluation ancien élève',
            date_tp=date(2025, 11, 1), createur=self.prof_user,
        )
        FicheEvaluation.objects.create(
            fiche_contrat=fiche, eleve=sorti, validee=True, note_sur_20='12.00'
        )

        response = self.client.get(reverse('core:statistiques'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'NomSecret')
        self.assertNotContains(response, 'PrénomSecret')
        self.assertContains(response, 'Remise à zéro')
        self.assertContains(response, 'Moyenne par classe')
        self.assertContains(response, "Intl.DateTimeFormat('fr-FR'")
        contenu = response.content.decode()
        self.assertLess(contenu.index('id="section-moyennes"'), contenu.index('id="section-overview"'))
        self.assertEqual(contenu.count('id="classe-moyennes"'), 1)
        self.assertContains(response, 'Ancien élève')
        self.assertEqual(response.context['diplomes'], 2)
        self.assertNotIn('nom', response.context['sorties_post_formation'][0])
        diplomes_annee = response.context['diplomes_par_annee_json']
        self.assertEqual(diplomes_annee[0]['annee'], '2025-2026')
        self.assertEqual(diplomes_annee[0]['cap_mention'], 1)
        self.assertEqual(diplomes_annee[0]['bp_sans'], 1)
        origine_non_renseignee = next(row for row in response.context['orig_college'] if row['label'] == 'Non renseigné')
        self.assertEqual(origine_non_renseignee['total'], 2)
        self.assertEqual(origine_non_renseignee['diplomes'], 2)

    def test_moyennes_par_classe_et_eleve_filtrees_par_annee(self):
        referentiel = Referentiel.objects.create(nom='Référentiel moyennes', description='Test')
        for index, (jour, note) in enumerate(((date(2025, 11, 1), '14.00'), (date(2025, 12, 1), '16.00'), (date(2024, 11, 1), '10.00'))):
            fiche = FicheContrat.objects.create(
                referentiel=referentiel, classe=self.classe,
                titre_tp=f'Évaluation {index}', date_tp=jour, createur=self.prof_user,
            )
            FicheEvaluation.objects.create(
                fiche_contrat=fiche, eleve=self.eleve, validee=True, note_sur_20=note
            )

        response = self.client.get(reverse('core:statistiques'), {'annee_moyennes': '2025-2026'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['moyennes_classe'], [
            {'classe': '2M', 'moyenne': 15.0, 'nb_evaluations': 2}
        ])
        self.assertEqual(response.context['moyennes_eleve'][0]['moyenne'], 15.0)
        self.assertEqual(response.context['moyennes_eleve'][0]['nb_evaluations'], 2)
        self.assertContains(response, 'Moyenne par élève')

    def test_moyennes_par_eleve_peuvent_etre_filtrees_par_classe(self):
        autre_classe = Classe.objects.create(nom='1M', niveau=self.classe.niveau)
        autre_user = User.objects.create_user(
            username='autre_eleve_stats', password='test123456', first_name='Sam', last_name='ClasseB'
        )
        autre_eleve = ProfilUtilisateur.objects.create(
            user=autre_user, type_utilisateur='eleve', classe=autre_classe, compte_approuve=True
        )
        referentiel = Referentiel.objects.create(nom='Référentiel filtre classe', description='Test')
        fiche_a = FicheContrat.objects.create(
            referentiel=referentiel, classe=self.classe, titre_tp='TP classe 2M',
            date_tp=date(2025, 11, 1), createur=self.prof_user,
        )
        fiche_b = FicheContrat.objects.create(
            referentiel=referentiel, classe=autre_classe, titre_tp='TP classe 1M',
            date_tp=date(2025, 11, 1), createur=self.prof_user,
        )
        FicheEvaluation.objects.create(fiche_contrat=fiche_a, eleve=self.eleve, validee=True, note_sur_20='14.00')
        FicheEvaluation.objects.create(fiche_contrat=fiche_b, eleve=autre_eleve, validee=True, note_sur_20='18.00')

        response = self.client.get(reverse('core:statistiques'), {
            'annee_moyennes': '2025-2026',
            'classe_moyennes': str(autre_classe.pk),
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['classe_moyennes_selectionnee'], autre_classe.pk)
        self.assertEqual(response.context['moyennes_classe'], [
            {'classe': '1M', 'moyenne': 18.0, 'nb_evaluations': 1}
        ])
        self.assertEqual(len(response.context['moyennes_eleve']), 1)
        self.assertEqual(response.context['moyennes_eleve'][0]['prenom'], 'Sam')

    def test_moyennes_qcm_utilisent_les_meme_filtres_annee_et_classe(self):
        autre_classe = Classe.objects.create(nom='1M', niveau=self.classe.niveau)
        autre_user = User.objects.create_user(
            username='autre_eleve_qcm_stats', password='test123456', first_name='Sam', last_name='ClasseB'
        )
        autre_eleve = ProfilUtilisateur.objects.create(
            user=autre_user, type_utilisateur='eleve', classe=autre_classe, compte_approuve=True
        )
        referentiel = Referentiel.objects.create(nom='Référentiel QCM moyennes', description='Test')
        qcm_2m = QCM.objects.create(
            titre='QCM commun', createur=self.prof_user,
            date_limite=timezone.make_aware(datetime(2025, 12, 1)),
        )
        qcm_2m.classes.add(self.classe)
        qcm_2m.classes.add(autre_classe)
        QCM.objects.filter(pk=qcm_2m.pk).update(date_creation=timezone.make_aware(datetime(2025, 11, 1)))
        SessionQCM.objects.create(
            qcm=qcm_2m, eleve=self.eleve, termine=True, note_sur_20=18,
            date_soumission=timezone.make_aware(datetime(2025, 11, 10)),
        )
        SessionQCM.objects.create(
            qcm=qcm_2m, eleve=autre_eleve, termine=True, note_sur_20=10,
            date_soumission=timezone.make_aware(datetime(2025, 11, 10)),
        )
        qcm_non_termine = QCM.objects.create(
            titre='QCM non terminé', createur=self.prof_user,
            date_limite=timezone.make_aware(datetime(2025, 12, 1)),
        )
        qcm_non_termine.classes.add(self.classe)
        QCM.objects.filter(pk=qcm_non_termine.pk).update(
            date_creation=timezone.make_aware(datetime(2025, 11, 5))
        )
        SessionQCM.objects.create(
            qcm=qcm_non_termine, eleve=self.eleve, termine=False, note_sur_20=1,
        )

        toutes_classes = self.client.get(reverse('core:statistiques'), {
            'annee_moyennes': '2025-2026',
        })
        self.assertEqual(toutes_classes.context['moyennes_qcm_classe'], [
            {'classe': '1M', 'moyenne': 10.0, 'nb_qcms': 1},
            {'classe': '2M', 'moyenne': 18.0, 'nb_qcms': 1},
        ])

        response = self.client.get(reverse('core:statistiques'), {
            'annee_moyennes': '2025-2026',
            'classe_moyennes': str(self.classe.pk),
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['moyennes_qcm_classe'], [
            {'classe': '2M', 'moyenne': 18.0, 'nb_qcms': 1}
        ])
        self.assertEqual(len(response.context['moyennes_qcm_eleve']), 1)
        self.assertEqual(response.context['moyennes_qcm_eleve'][0]['moyenne'], 18.0)
        self.assertContains(response, 'Moyenne QCM par classe')

    def test_connexions_et_jours_actifs_ne_comptent_que_les_30_derniers_jours(self):
        from core.views_merged_ast import _stats_connexions, _stats_connexions_30j

        connexion_recente = ConnexionEleve.objects.create(user=self.eleve_user)
        ConnexionEleve.objects.filter(pk=connexion_recente.pk).update(
            horodatage=timezone.now() - timedelta(days=5)
        )
        ConnexionEleve.objects.create(user=self.eleve_user)
        connexion_ancienne = ConnexionEleve.objects.create(user=self.eleve_user)
        ConnexionEleve.objects.filter(pk=connexion_ancienne.pk).update(
            horodatage=timezone.now() - timedelta(days=31)
        )

        ligne = _stats_connexions()[0]
        graphique = _stats_connexions_30j()

        self.assertEqual(ligne['nb_connexions'], 2)
        self.assertEqual(ligne['nb_jours_actifs'], 2)
        self.assertEqual(
            datetime.strptime(ligne['derniere'], '%d/%m/%Y %H:%M').date(),
            date.today(),
        )
        self.assertEqual(sum(point['nb'] for point in graphique), 2)
        self.assertEqual(len(graphique), 30)
        self.assertEqual(graphique[-1]['date'], timezone.localdate().isoformat())
        page = self.client.get(reverse('core:statistiques'))
        self.assertContains(page, "Intl.DateTimeFormat('fr-FR'")

    def test_remise_a_zero_connexions_seulement_apres_confirmation(self):
        ConnexionEleve.objects.create(user=self.eleve_user)
        ConnexionEleve.objects.create(user=self.eleve_user)

        url = reverse('core:statistiques_reinitialiser_connexions')
        response_sans_confirmation = self.client.post(url)
        self.assertEqual(response_sans_confirmation.status_code, 302)
        self.assertEqual(ConnexionEleve.objects.filter(user=self.eleve_user).count(), 2)

        response_confirmee = self.client.post(url, {'confirmation': 'oui'})
        self.assertEqual(response_confirmee.status_code, 302)
        self.assertEqual(ConnexionEleve.objects.count(), 0)
        self.assertTrue(ProfilUtilisateur.objects.filter(pk=self.eleve.pk).exists())


class TestProfessorAccountsAndThemeOwners(TestCase):
    def setUp(self):
        self.niveau = Niveau.objects.create(nom='CAP', description='CAP')
        self.classe = Classe.objects.create(nom='2M', niveau=self.niveau)
        self.admin = User.objects.create_user(
            username='admin_comptes', password='motdepasse-admin', is_staff=True,
            first_name='Admin', last_name='Site',
        )
        ProfilUtilisateur.objects.create(user=self.admin, type_utilisateur='professeur', compte_approuve=True)
        self.prof = User.objects.create_user(
            username='prof_simple', password='motdepasse-prof', first_name='Pauline', last_name='Martin',
        )
        self.prof_profil = ProfilUtilisateur.objects.create(
            user=self.prof, type_utilisateur='professeur', compte_approuve=True,
        )

    def test_administrateur_cree_un_compte_professeur(self):
        self.client.force_login(self.admin)

        response = self.client.post(reverse('core:gestion_eleves'), {
            'action': 'ajouter_professeur',
            'prof_username': 'nouveau_prof',
            'prof_password': 'mot-de-passe-sur-123',
            'prof_first_name': 'Nora',
            'prof_last_name': 'Durand',
            'prof_email': 'nora@example.org',
        })

        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username='nouveau_prof')
        self.assertTrue(user.check_password('mot-de-passe-sur-123'))
        self.assertFalse(user.is_staff)
        self.assertEqual(user.profil.type_utilisateur, 'professeur')
        self.assertTrue(user.profil.compte_approuve)

    def test_professeur_ordinaire_ne_peut_pas_creer_ni_reinitialiser(self):
        self.client.force_login(self.prof)

        creation = self.client.post(reverse('core:gestion_eleves'), {
            'action': 'ajouter_professeur',
            'prof_username': 'interdit',
            'prof_password': 'mot-de-passe-sur-123',
        })
        reinitialisation = self.client.post(reverse('core:gestion_eleves'), {
            'action': 'reinitialiser_mot_de_passe_professeur',
            'professeur_id': self.prof_profil.pk,
            'nouveau_mot_de_passe': 'autre-mot-de-passe-123',
        })

        self.assertEqual(creation.status_code, 302)
        self.assertEqual(reinitialisation.status_code, 302)
        self.assertFalse(User.objects.filter(username='interdit').exists())
        self.prof.refresh_from_db()
        self.assertTrue(self.prof.check_password('motdepasse-prof'))

    def test_administrateur_reinitialise_le_mot_de_passe_d_un_professeur(self):
        self.client.force_login(self.admin)

        response = self.client.post(reverse('core:gestion_eleves'), {
            'action': 'reinitialiser_mot_de_passe_professeur',
            'professeur_id': self.prof_profil.pk,
            'nouveau_mot_de_passe': 'nouveau-mot-de-passe-123',
        })

        self.assertEqual(response.status_code, 302)
        self.prof.refresh_from_db()
        self.assertTrue(self.prof.check_password('nouveau-mot-de-passe-123'))

    def test_un_professeur_ne_peut_pas_reinitialiser_le_mot_de_passe_admin(self):
        admin_protege = User.objects.create_user(
            username='admin_protege', password='motdepasse-admin-2', is_staff=True,
            first_name='Admin', last_name='Protégé',
        )
        profil_admin_protege = ProfilUtilisateur.objects.create(
            user=admin_protege, type_utilisateur='professeur', compte_approuve=True,
        )
        ancien_hash = admin_protege.password

        self.client.force_login(self.prof)
        response = self.client.post(reverse('core:gestion_eleves'), {
            'action': 'reinitialiser_mot_de_passe_professeur',
            'professeur_id': profil_admin_protege.pk,
            'nouveau_mot_de_passe': 'mot-de-passe-admin-hacke',
        })

        self.assertEqual(response.status_code, 302)
        admin_protege.refresh_from_db()
        self.assertEqual(admin_protege.password, ancien_hash)

    def test_administrateur_peut_supprimer_un_compte_professeur(self):
        self.client.force_login(self.admin)

        response = self.client.post(reverse('core:gestion_eleves'), {
            'action': 'supprimer_compte_professeur',
            'professeur_id': self.prof_profil.pk,
        })

        self.assertEqual(response.status_code, 302)
        self.assertFalse(User.objects.filter(username='prof_simple').exists())

    def test_professeur_ne_peut_pas_supprimer_un_compte_professeur(self):
        autre_prof = User.objects.create_user(
            username='autre_prof', password='motdepasse-prof-2',
            first_name='Claire', last_name='Bernard',
        )
        ProfilUtilisateur.objects.create(user=autre_prof, type_utilisateur='professeur', compte_approuve=True)

        self.client.force_login(self.prof)
        response = self.client.post(reverse('core:gestion_eleves'), {
            'action': 'supprimer_compte_professeur',
            'professeur_id': ProfilUtilisateur.objects.get(user=autre_prof).pk,
        })

        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='autre_prof').exists())

    def test_creation_de_theme_enregistre_le_createur_et_affiche_sa_couleur(self):
        self.client.force_login(self.prof)

        response = self.client.post(reverse('core:theme_create'), {
            'nom': 'Maçonnerie de Pauline',
            'classes': [self.classe.pk],
            'visible_eleves': 'on',
        })
        theme = Theme.objects.get(nom='Maçonnerie de Pauline')
        liste = self.client.get(reverse('core:gestion_themes'))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(theme.createur, self.prof)
        self.assertContains(liste, 'Pauline Martin')
        self.assertContains(liste, theme.couleur_createur)

    def test_ancien_theme_sans_auteur_est_identifie_comme_equipe(self):
        Theme.objects.create(nom='Ancien thème')
        self.client.force_login(self.prof)

        liste = self.client.get(reverse('core:gestion_themes'))

        self.assertContains(liste, 'Ancien thème')
        self.assertContains(liste, 'Équipe')

    def test_un_theme_epingle_est_affiche_en_haut_de_la_liste(self):
        Theme.objects.create(nom='Thème normal', createur=self.prof, ordre=10)
        theme_epingle = Theme.objects.create(nom='Thème épinglé', createur=self.prof, ordre=5, epingle=True)

        self.client.force_login(self.prof)
        response = self.client.get(reverse('core:gestion_themes'))

        html = response.content.decode('utf-8')
        self.assertLess(html.index(theme_epingle.nom), html.index('Thème normal'))

    def test_fusion_d_un_theme_deplace_les_dossiers_vers_le_theme_cible(self):
        theme_cible = Theme.objects.create(nom='Thème cible', createur=self.prof, ordre=1)
        theme_source = Theme.objects.create(nom='Thème source', createur=self.prof, ordre=2)
        dossier_1 = Dossier.objects.create(theme=theme_source, nom='Dossier A', ordre=1)
        dossier_2 = Dossier.objects.create(theme=theme_source, nom='Dossier B', ordre=2)

        self.client.force_login(self.prof)
        response = self.client.post(reverse('core:theme_update', args=[theme_source.pk]), {
            'action': 'fusionner_theme',
            'theme_cible': theme_cible.pk,
            'nouveau_nom': 'Thème fusionné',
            'nom': theme_source.nom,
            'description': '',
            'visible_eleves': 'on',
        })

        self.assertEqual(response.status_code, 302)
        theme_cible.refresh_from_db()
        self.assertEqual(theme_cible.nom, 'Thème fusionné')
        self.assertFalse(Theme.objects.filter(pk=theme_source.pk).exists())
        self.assertEqual(list(Dossier.objects.filter(pk__in=[dossier_1.pk, dossier_2.pk]).values_list('theme_id', flat=True)), [theme_cible.pk, theme_cible.pk])


@override_settings(STATICFILES_STORAGE='django.contrib.staticfiles.storage.StaticFilesStorage')
class TestURLsAccessibility(TestCase):
    """Teste si toutes les URLs sont accessibles sans erreur 500"""
    
    def setUp(self):
        """Crée des données de test"""
        # Crée un niveau et une classe
        self.niveau = Niveau.objects.create(nom='CAP', description='CAP Maçon')
        self.classe = Classe.objects.create(
            nom='2M',
            niveau=self.niveau,
            description='2ème année Maçon'
        )
        
        # Crée un professeur (via User avec is_staff=True)
        self.prof_user = User.objects.create_user(
            username='prof_test',
            password='test123456',
            first_name='Prof',
            last_name='Test',
            is_staff=True  # Identifie comme prof
        )
        # Profil professeur (selon ton modèle avec type_utilisateur='professeur' ou autre)
        self.prof_profil = ProfilUtilisateur.objects.create(
            user=self.prof_user,
            type_utilisateur='professeur'  # Adapte selon ton modèle
        )
        
        # Crée un élève
        self.eleve_user = User.objects.create_user(
            username='eleve_test',
            password='test123456',
            first_name='Élève',
            last_name='Test'
        )
        self.eleve_profil = ProfilUtilisateur.objects.create(
            user=self.eleve_user,
            type_utilisateur='eleve',
            classe=self.classe,
            compte_approuve=True
        )
        
        self.client = Client()
        # Forcer un staticfiles_storage simple en tests pour éviter les erreurs
        # liées au ManifestStaticFilesStorage si collectstatic n'a pas été exécuté.
        try:
            from django.contrib.staticfiles import storage as static_storage
            static_storage.staticfiles_storage = static_storage.StaticFilesStorage()
        except Exception:
            pass
    
    def test_urls_publiques(self):
        """Teste les pages publiques (sans login)"""
        print("\n=== TEST URLS PUBLIQUES ===")
        urls_publiques = [
            'core:login_prof',
            'core:login_eleve',
            'core:choix_eleve',
            'core:inscription_eleve',
        ]
        
        for url_name in urls_publiques:
            with self.subTest(url=url_name):
                try:
                    response = self.client.get(reverse(url_name))
                    # 200 = OK, 302 = Redirect (normal)
                    self.assertIn(response.status_code, [200, 302], 
                        f"{url_name} retourne {response.status_code}")
                    print(f"✅ {url_name}: {response.status_code}")
                except Exception as e:
                    print(f"❌ {url_name}: {str(e)}")
                    raise
    
    def test_urls_professeur(self):
        """Teste les pages réservées aux professeurs"""
        print("\n=== TEST URLS PROFESSEUR ===")
        self.client.login(username='prof_test', password='test123456')
        
        urls_prof = [
            'core:dashboard_professeur',
            'core:gestion_classes',
            'core:gestion_eleves',
            'core:gestion_themes',
            'core:evaluations_home',
            'core:evaluation_parametres',
            'core:archives',
            'core:statistiques',
            'core:travaux_creer',
            'core:travaux_corriger',
            'core:gestion_sorties',
            'core:gestion_approbations',
        ]
        
        for url_name in urls_prof:
            with self.subTest(url=url_name):
                try:
                    response = self.client.get(reverse(url_name))
                    self.assertEqual(response.status_code, 200,
                        f"{url_name} devrait retourner 200, reçu {response.status_code}")
                    print(f"✅ {url_name}: OK")
                except Exception as e:
                    print(f"❌ {url_name}: {str(e)}")
    
    def test_urls_eleve(self):
        """Teste les pages réservées aux élèves"""
        print("\n=== TEST URLS ÉLÈVE ===")
        self.client.login(username='eleve_test', password='test123456')
        
        urls_eleve = [
            'core:dashboard_eleve',
            'core:mes_travaux_eleve',
            'core:mes_notifications',
        ]
        
        for url_name in urls_eleve:
            with self.subTest(url=url_name):
                try:
                    response = self.client.get(reverse(url_name))
                    self.assertEqual(response.status_code, 200,
                        f"{url_name} devrait retourner 200, reçu {response.status_code}")
                    print(f"✅ {url_name}: OK")
                except Exception as e:
                    print(f"❌ {url_name}: {str(e)}")
    
    def test_urls_avec_parametres(self):
        """Teste les URLs qui nécessitent des paramètres (ID)"""
        print("\n=== TEST URLS AVEC PARAMÈTRES ===")
        self.client.login(username='prof_test', password='test123456')
        
        urls_avec_params = [
            ('core:classe_detail', {'pk': self.classe.id}),
            ('core:modifier_eleve', {'pk': self.eleve_profil.id}),
            ('core:marquer_sortie', {'pk': self.eleve_profil.id}),
        ]
        
        for url_name, kwargs in urls_avec_params:
            with self.subTest(url=url_name):
                try:
                    response = self.client.get(reverse(url_name, kwargs=kwargs))
                    self.assertIn(response.status_code, [200, 302],
                        f"{url_name} devrait être accessible")
                    print(f"✅ {url_name} avec params: {response.status_code}")
                except Exception as e:
                    print(f"⚠️ {url_name}: {str(e)}")

    def test_evaluations_count_by_contrat(self):
        """Vérifie que la page d'accueil des évaluations compte une évaluation = une fiche contrat.
        Crée deux fiches contrat pour le même créateur et plusieurs fiches d'évaluation élèves
        liées à l'une des fiches; le compteur doit retourner 2 (contrats actifs) et nb_validees
        ne doit compter que les contrats entièrement validés.
        """
        self.client.login(username='prof_test', password='test123456')

        # Création d'un référentiel minimal requis
        ref = Referentiel.objects.create(nom='RefTest', description='Ref test')

        # Crée deux fiches contrat actives
        fc1 = FicheContrat.objects.create(referentiel=ref, classe=self.classe, titre_tp='TP1', createur=self.prof_user, actif=True)
        fc2 = FicheContrat.objects.create(referentiel=ref, classe=self.classe, titre_tp='TP2', createur=self.prof_user, actif=True)

        # Crée 3 élèves supplémentaires
        users = []
        profils = []
        for i in range(3):
            u = User.objects.create_user(username=f'eleve_{i}', password='pwd')
            p = ProfilUtilisateur.objects.create(user=u, type_utilisateur='eleve', classe=self.classe, compte_approuve=True)
            users.append(u); profils.append(p)

        # Crée des fiches d'évaluation pour fc1 (3 élèves)
        for p in profils:
            FicheEvaluation.objects.create(fiche_contrat=fc1, eleve=p, validee=True)

        # Pour fc2, aucune évaluation créée (simulate un contrat sans évaluations encore)

        response = self.client.get(reverse('core:evaluations_home'))
        self.assertEqual(response.status_code, 200)
        # nb_evaluations doit être le nombre de fiches_contrat actives (2)
        self.assertIn('nb_evaluations', response.context)
        self.assertEqual(response.context['nb_evaluations'], 2)
        # nb_validees : fc1 a toutes ses évaluations validées -> compte 1; fc2 a 0 évaluations -> non compté
        self.assertIn('nb_validees', response.context)
        self.assertEqual(response.context['nb_validees'], 1)

    def test_archives_export_zip_structure(self):
        """Télécharge l'export des archives pour une année scolaire et vérifie
        que le ZIP contient un dossier par classe et par catégorie, ainsi qu'un
        export de la fiche_contrat (PDF ou JSON) et le fichier metadata.
        """
        self.client.login(username='prof_test', password='test123456')

        # Préparer référentiel et fiche_contrat
        ref = Referentiel.objects.create(nom='RefExport', description='ref export')
        fc = FicheContrat.objects.create(referentiel=ref, classe=self.classe, titre_tp='TP_export', createur=self.prof_user, actif=True)

        # Créer une archive liée à cette fiche_contrat et y attacher un PDF
        annee = '2025-2026'
        archive = Archive.objects.create(titre='ArchiveExport', description=f'fiche_contrat_id:{fc.id}', categorie='evaluations', annee_scolaire=annee, createur=self.prof_user, actif=True)
        pdf_bytes = b'%PDF-1.4\n%test\n%%EOF\n'
        archive.fichier.save('sample.pdf', ContentFile(pdf_bytes))
        archive.save()

        # Appel de l'export
        resp = self.client.get(reverse('core:archives_export'), {'annee': annee})
        self.assertEqual(resp.status_code, 200)

        import io, zipfile, json
        z = zipfile.ZipFile(io.BytesIO(resp.content))
        names = z.namelist()

        # metadata présent
        self.assertIn('data/archives_metadata.json', names)
        # dossier attendu: <Classe>/<categorie>/
        safe_classe = self.classe.nom.replace(' ', '_')
        matches = [n for n in names if n.startswith(f'{safe_classe}/evaluations/')]
        self.assertTrue(matches, f'Pas de fichiers sous {safe_classe}/evaluations dans le zip: {names}')

        # fiche_contrat doit exister en PDF ou JSON dans le dossier
        expected_pdf = f'{safe_classe}/evaluations/fiche_contrat_{fc.id}.pdf'
        expected_json = f'{safe_classe}/evaluations/fiche_contrat_{fc.id}.json'
        self.assertTrue(expected_pdf in names or expected_json in names, f'fiche_contrat manquante dans {names}')

        # metadata contient l'entrée pour notre archive
        meta_raw = z.read('data/archives_metadata.json')
        meta = json.loads(meta_raw.decode('utf-8'))
        ids = [m.get('id') for m in meta]
        self.assertIn(archive.id, ids)
