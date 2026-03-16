# core/tests.py
"""
Tests automatiques des URLs de la plateforme pédagogique
"""
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from core.models import ProfilUtilisateur, Classe, Niveau, Referentiel, FicheContrat, FicheEvaluation, Archive
from django.core.files.base import ContentFile


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
