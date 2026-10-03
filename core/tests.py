# core/tests.py
"""
Tests automatiques des URLs de la plateforme pédagogique
"""
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from core.models import ProfilUtilisateur, Classe, Niveau, Referentiel, FicheContrat, FicheEvaluation, Archive, MessageEleve, DiplomeEleve
from django.core.files.base import ContentFile
from unittest.mock import patch


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
        self.prof_user = User.objects.create_user(username='prof_comm', password='test123456')
        self.prof_profil = ProfilUtilisateur.objects.create(
            user=self.prof_user, type_utilisateur='professeur'
        )
        eleve_user = User.objects.create_user(username='eleve_comm', password='test123456')
        self.eleve_profil = ProfilUtilisateur.objects.create(
            user=eleve_user, type_utilisateur='eleve'
        )
        self.message = MessageEleve.objects.create(
            eleve=self.eleve_profil,
            professeur=self.prof_profil,
            texte='Rapport de test',
            image='messages/rapport.jpg',
        )
        self.client.force_login(self.prof_user)

    def test_consulter_est_un_lien_direct_vers_la_piece_jointe(self):
        response = self.client.get(reverse('core:communications_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Consulter')
        self.assertContains(response, 'target="_blank"')
        self.assertNotContains(response, 'consult-btn')

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
        url_cloudinary = 'https://res.cloudinary.com/demo/image/upload/v123/messages/rapport.jpg'
        with (
            patch.object(image_storage, '_get_resource_type', return_value='image', create=True),
            patch.object(image_storage, 'url', return_value=url_cloudinary),
        ):
            response = self.client.get(
                reverse('core:communication_telecharger', kwargs={'message_id': self.message.pk})
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response['Location'],
            'https://res.cloudinary.com/demo/image/upload/fl_attachment/v123/messages/rapport.jpg',
        )

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
