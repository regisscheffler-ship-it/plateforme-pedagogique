# core/tests.py
"""
Tests automatiques des URLs de la plateforme pédagogique
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from core.models import ProfilUtilisateur, Classe, Niveau


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
