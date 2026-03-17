# core/models.py — VERSION CORRIGÉE (doublon Connaissance supprimé)

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse  # ← ajouté ici


# =====================================================
# NIVEAU SCOLAIRE
# =====================================================
class Niveau(models.Model):
    CHOIX_NIVEAU = [
        ('CAP', 'CAP'),
        ('BAC_PRO', 'Baccalauréat Professionnel'),
        ('BTS', 'BTS'),
    ]

    nom = models.CharField(max_length=50, choices=CHOIX_NIVEAU, unique=True)
    description = models.TextField(blank=True)
    actif = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Niveau"
        verbose_name_plural = "Niveaux"
        ordering = ['nom']

    def __str__(self):
        return self.get_nom_display()


# =====================================================
# ÉTABLISSEMENT D'ORIGINE
# =====================================================
class EtablissementOrigine(models.Model):
    nom = models.CharField(max_length=200, unique=True)
    ville = models.CharField(max_length=100, blank=True)
    actif = models.BooleanField(default=True)
    ordre_affichage = models.IntegerField(default=0)

    class Meta:
        ordering = ['nom']
        verbose_name = "Établissement d'origine"
        verbose_name_plural = "Établissements d'origine"

    def __str__(self):
        return self.nom


# =====================================================
# CLASSE
# =====================================================
class Classe(models.Model):
    nom = models.CharField(max_length=100)
    niveau = models.ForeignKey(Niveau, on_delete=models.CASCADE, related_name='classes')
    description = models.TextField(blank=True)
    annee_scolaire = models.CharField(max_length=20, blank=True)
    actif = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Classe"
        verbose_name_plural = "Classes"
        ordering = ['nom']

    def __str__(self):
        return f"{self.nom} ({self.niveau})"


# =====================================================
# PROFIL UTILISATEUR
# =====================================================
class ProfilUtilisateur(models.Model):
    TYPE_UTILISATEUR = [
        ('eleve', 'Élève'),
        ('professeur', 'Professeur'),
        ('admin', 'Administrateur'),
    ]

    RAISON_SORTIE = [
        # --- Diplômés & Post-Formation ---
        ('cap_mention', 'Obtention CAP (avec mention)'),
        ('cap_sans_mention', 'Obtention CAP (sans mention)'),
        ('bac_pro_mention', 'Obtention Bac Pro (avec mention)'),
        ('bac_pro_sans_mention', 'Obtention Bac Pro (sans mention)'),
        ('poursuite_bac_pro', 'Poursuite en Bac Pro (Post-Formation)'),
        ('poursuite_bts', 'Poursuite en BTS (Post-Formation)'),
        ('poursuite_autre', "Autre poursuite d'études (Post-Formation)"),
        ('travail_formation', 'Travaille dans le BTP (Post-Formation)'),
        ('travail_hors_formation', 'Travaille hors BTP (Post-Formation)'),
        ('apprentissage', 'Apprentissage / Alternance (Post-Formation)'),
        
        # --- Changement de section (Fin de 2nde BTP) ---
        ('orientation_afb', 'Orientation en 1ère AFB (Reste au lycée)'),
        
        # --- Réorientations pures ---
        ('reorientation_interne', 'Réorientation interne (Autre filière)'),
        ('reorientation_externe', 'Réorientation externe (Autre lycée/CFA)'),
        
        # --- Échecs & Décrochages ---
        ('echec_cap', 'Échec au CAP'),
        ('echec_bac_pro', 'Échec au Bac Pro'),
        ('decrocheur', 'Décrocheur (abandon en cours d\'année)'),
        ('sans_emploi', 'Sans emploi (Sorti du système)'),
        ('exclusion', 'Exclusion définitive'),
        ('retour_pays', "Retour dans le pays d'origine"),
        ('deces', 'Décès'),
        ('raison_inconnue', 'Raison inconnue'),
    ]

    TYPE_DIPLOME_OBTENU = [
        ('cap', 'CAP'),
        ('bac_pro', 'Bac Pro'),
    ]

    MENTION = [
        ('', 'Sans mention'),
        ('AB', 'Assez Bien'),
        ('B', 'Bien'),
        ('TB', 'Très Bien'),
    ]

    POURSUITE_ETUDES = [
        ('bac_pro', 'Bac Pro'),
        ('bts', 'BTS'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profil')
    type_utilisateur = models.CharField(max_length=20, choices=TYPE_UTILISATEUR, default='eleve')
    classe = models.ForeignKey('Classe', on_delete=models.SET_NULL, null=True, blank=True, related_name='eleves')
    SEXE_CHOICES = [('M', 'Garçon'), ('F', 'Fille')]

    date_naissance = models.DateField(null=True, blank=True)
    photo = models.ImageField(upload_to='photos_profils/', null=True, blank=True)
    sexe = models.CharField(max_length=1, choices=SEXE_CHOICES, null=True, blank=True, verbose_name='Sexe')

    compte_approuve = models.BooleanField(default=False)
    date_inscription = models.DateTimeField(auto_now_add=True)
    date_approbation = models.DateTimeField(null=True, blank=True)

    etablissement_origine = models.ForeignKey(
        'EtablissementOrigine',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='eleves'
    )
    etablissement_origine_autre = models.CharField(max_length=200, blank=True)
    classe_origine = models.CharField(max_length=100, blank=True)
    diplome_obtenu = models.CharField(max_length=50, blank=True)
    annee_entree = models.CharField(max_length=9, blank=True, default='')

    est_sorti = models.BooleanField(default=False)
    date_sortie = models.DateField(null=True, blank=True)
    annee_scolaire_sortie = models.CharField(max_length=20, blank=True, default='')
    raison_sortie = models.CharField(max_length=50, choices=RAISON_SORTIE, blank=True, default='')
    commentaire_sortie = models.TextField(blank=True, default='')
    # Ajout pour la gestion avancée des sorties
    type_sortie = models.CharField(
        max_length=30,
        blank=True,
        default='',
        choices=[
            ('', 'Non renseigné'),
            ('poursuite_etudes', 'Poursuite d\'études'),
            ('reorientation_interne', 'Réorientation interne'),
            ('reorientation_externe', 'Réorientation externe'),
            ('passage_classe_sup', 'Passage en classe supérieure'),
            ('autre', 'Autre'),
        ]
    )
    formation_choisie = models.CharField(max_length=100, blank=True, default='')

    type_diplome_obtenu = models.CharField(max_length=20, choices=TYPE_DIPLOME_OBTENU, blank=True, default='')
    mention_obtenue = models.CharField(max_length=50, choices=MENTION, blank=True, default='')

    poursuite_etudes = models.BooleanField(default=False)
    type_poursuite = models.CharField(max_length=20, choices=POURSUITE_ETUDES, blank=True, default='')

    # Parcours spécifique pour filières 2BTP : ORGO (gros-oeuvre) ou AFB (autre)
    PARCOURS_CHOICES = [
        ('ORGO', 'ORGO'),
        ('AFB', 'AFB'),
    ]
    parcours = models.CharField(max_length=10, choices=PARCOURS_CHOICES, null=True, blank=True)

    class Meta:
        verbose_name = "Profil Utilisateur"
        verbose_name_plural = "Profils Utilisateurs"
        ordering = ['user__last_name', 'user__first_name']

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.get_type_utilisateur_display()})"

    def est_prof(self):
        return self.type_utilisateur == 'professeur'

    def est_eleve(self):
        return self.type_utilisateur == 'eleve'

    def est_diplome(self):
        return self.raison_sortie in {
            'cap_mention', 'cap_sans_mention',
            'bac_pro_mention', 'bac_pro_sans_mention',
        }


# =====================================================
# THÈME
# =====================================================
class Theme(models.Model):
    nom = models.CharField(max_length=200)
    classes = models.ManyToManyField(Classe, related_name='themes', blank=True)
    description = models.TextField(blank=True, null=True)
    ressources_html = models.TextField(blank=True, null=True, verbose_name="Ressources intégrées (HTML)")
    ordre = models.IntegerField(default=0)
    couleur = models.CharField(max_length=7, default='#20c997')
    visible_eleves = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    actif = models.BooleanField(default=True, verbose_name="Actif")

    class Meta:
        ordering = ['ordre', 'nom']
        verbose_name = "Thème"
        verbose_name_plural = "Thèmes"

    def __str__(self):
        classes_str = ", ".join(c.nom for c in self.classes.all()) or "Sans classe"
        return f"{self.nom} - {classes_str}"


# =====================================================
# DOSSIER
# =====================================================
class Dossier(models.Model):
    theme = models.ForeignKey(Theme, on_delete=models.CASCADE, related_name='dossiers')
    nom = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    ordre = models.IntegerField(default=0)
    visible_eleves = models.BooleanField(default=False, help_text="Cochez pour rendre visible aux élèves")
    actif = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Dossier"
        verbose_name_plural = "Dossiers"
        ordering = ['ordre', 'nom']

    def __str__(self):
        visible = "V" if self.visible_eleves else "X"
        return f"[{visible}] {self.nom}"

    def nb_fichiers(self):
        return self.fichiers.filter(actif=True).count()


# =====================================================
# TYPE DE RESSOURCE
# =====================================================
class TypeRessource(models.Model):
    nom = models.CharField(max_length=100)
    icone = models.CharField(max_length=50, blank=True)
    actif = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Type de ressource"
        verbose_name_plural = "Types de ressources"

    def __str__(self):
        return self.nom


# =====================================================
# FICHIER / LIEN
# =====================================================
class Fichier(models.Model):
    TYPE_RESSOURCE_CHOICES = [
        ('fichier', 'Fichier (PDF, Word, Image...)'),
        ('lien', 'Lien externe'),
        ('iframe', 'Integration (YouTube, Genially...)'),
    ]

    dossier = models.ForeignKey(Dossier, on_delete=models.CASCADE, related_name='fichiers')
    nom = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    type_contenu = models.CharField(max_length=20, choices=TYPE_RESSOURCE_CHOICES, default='fichier')

    fichier = models.FileField(upload_to='fichiers/', blank=True, null=True)
    lien_externe = models.URLField(blank=True, null=True)
    code_iframe = models.TextField(blank=True, null=True, help_text="Code d'integration iframe")

    type_ressource = models.ForeignKey('TypeRessource', on_delete=models.SET_NULL, null=True, blank=True)
    ordre = models.PositiveIntegerField(default=0)
    actif = models.BooleanField(default=True)
    visible_eleves = models.BooleanField(default=True, verbose_name='Visible par les élèves')
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    createur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['ordre', 'nom']
        verbose_name = "Fichier"
        verbose_name_plural = "Fichiers"

    def __str__(self):
        return self.nom

    def get_icon(self):
        icons = {'fichier': 'F', 'lien': 'L', 'iframe': 'I'}
        return icons.get(self.type_contenu, 'F')

    def est_fichier(self):
        return self.type_contenu == 'fichier' and self.fichier

    def est_lien(self):
        return self.type_contenu == 'lien' and self.lien_externe

    def est_iframe(self):
        return self.type_contenu == 'iframe' and self.code_iframe


# =====================================================
# TRAVAIL À RENDRE
# =====================================================
class TravailARendre(models.Model):
    classe = models.ForeignKey(Classe, on_delete=models.CASCADE, related_name='travaux')
    titre = models.CharField(max_length=200)
    description = models.TextField()
    date_limite = models.DateTimeField()

    dossier = models.ForeignKey(Dossier, on_delete=models.SET_NULL, null=True, blank=True, related_name='travaux')
    fichier_consigne = models.FileField(upload_to='consignes/', blank=True, null=True)

    createur = models.ForeignKey(User, on_delete=models.CASCADE)
    date_creation = models.DateTimeField(auto_now_add=True)
    actif = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Travail a rendre"
        verbose_name_plural = "Travaux a rendre"
        ordering = ['-date_limite']

    def __str__(self):
        return f"{self.titre} - {self.classe}"

    def est_en_retard(self):
        return timezone.now() > self.date_limite

    def nb_rendus(self):
        return self.rendus.filter(rendu=True).count()

    def nb_eleves_classe(self):
        return self.classe.eleves.filter(type_utilisateur='eleve', compte_approuve=True, est_sorti=False).count()


# =====================================================
# RENDU ÉLÈVE
# =====================================================
class RenduEleve(models.Model):
    travail = models.ForeignKey(TravailARendre, on_delete=models.CASCADE, related_name='rendus')
    eleve = models.ForeignKey(ProfilUtilisateur, on_delete=models.CASCADE, related_name='mes_rendus')

    fichier_rendu = models.FileField(upload_to='rendus/')
    commentaire = models.TextField(blank=True)

    date_rendu = models.DateTimeField(auto_now_add=True)
    rendu = models.BooleanField(default=True)

    corrige = models.BooleanField(default=False)
    note = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    appreciation = models.TextField(blank=True)
    date_correction = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Rendu eleve"
        verbose_name_plural = "Rendus eleves"
        unique_together = ['travail', 'eleve']

    def __str__(self):
        return f"{self.eleve.user.get_full_name()} - {self.travail.titre}"

    def est_en_retard(self):
        return self.date_rendu > self.travail.date_limite


# =====================================================
# NOTIFICATION
# =====================================================
class Notification(models.Model):
    destinataire = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    titre = models.CharField(max_length=200)
    message = models.TextField()
    type_notification = models.CharField(max_length=50, default='general')
    lien = models.CharField(max_length=255, blank=True, null=True)
    lue = models.BooleanField(default=False)  # ← IMPORTANT: "lue" pas "est_lue"
    date_creation = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date_creation']


# =====================================================
# COMMUNICATIONS ÉLÈVE → PROFESSEUR
# =====================================================

class MessageEleve(models.Model):
    """Message envoyé par un élève au professeur"""
    eleve = models.ForeignKey(
        'ProfilUtilisateur',
        on_delete=models.CASCADE,
        related_name='messages_envoyes',
        limit_choices_to={'type_utilisateur': 'eleve'}
    )
    professeur = models.ForeignKey(
        'ProfilUtilisateur',
        on_delete=models.CASCADE,
        related_name='messages_recus',
        limit_choices_to={'type_utilisateur': 'professeur'}
    )
    texte = models.TextField(blank=True)
    image = models.ImageField(
        upload_to='messages/',
        blank=True,
        null=True
    )
    image_annotee = models.ImageField(
        upload_to='messages/annotees/',
        blank=True,
        null=True
    )
    date_envoi = models.DateTimeField(auto_now_add=True)
    lu = models.BooleanField(default=False)

    class Meta:
        ordering = ['-date_envoi']
        verbose_name = "Message élève"

    def __str__(self):
        return f"Message de {self.eleve} - {self.date_envoi.strftime('%d/%m/%Y %H:%M')}"


class ReponseProf(models.Model):
    """Réponse du professeur à un message élève"""
    message = models.ForeignKey(
        MessageEleve,
        on_delete=models.CASCADE,
        related_name='reponses'
    )
    professeur = models.ForeignKey(
        'ProfilUtilisateur',
        on_delete=models.CASCADE,
        related_name='reponses_envoyees'
    )
    texte = models.TextField()
    date_envoi = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['date_envoi']
        verbose_name = "Réponse professeur"

    def __str__(self):
        return f"Réponse de {self.professeur} - {self.date_envoi.strftime('%d/%m/%Y %H:%M')}"



# =====================================================
# ARCHIVE
# =====================================================
class Archive(models.Model):
    CATEGORIE_CHOICES = [
        ('evaluations', 'Evaluations'),
        ('examens', 'Examens'),
        ('administratif', 'Documents administratifs'),
        ('ressources', 'Ressources pedagogiques'),
        ('autre', 'Autre'),
    ]

    titre = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    fichier = models.FileField(upload_to='archives/', blank=True, null=True)
    categorie = models.CharField(max_length=50, choices=CATEGORIE_CHOICES, default='autre')
    dossier = models.CharField(max_length=200, blank=True)
    annee_scolaire = models.CharField(max_length=20)

    createur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    actif = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Archive"
        verbose_name_plural = "Archives"
        ordering = ['-annee_scolaire', '-date_creation']

    def __str__(self):
        return f"{self.titre} ({self.annee_scolaire})"
    
    def description_parts(self):
        # Vérifie si une description existe pour éviter une erreur
        if self.description:
            return self.description.split("|")
        return []

# ================================================================
# RÉFÉRENTIELS ET COMPÉTENCES
# ================================================================

class Referentiel(models.Model):
    nom = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    actif = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Referentiel"
        verbose_name_plural = "Referentiels"
        ordering = ['nom']

    def __str__(self):
        return self.nom


class BlocCompetence(models.Model):
    referentiel = models.ForeignKey(Referentiel, on_delete=models.CASCADE, related_name='blocs')
    nom = models.CharField(max_length=200)
    code = models.CharField(max_length=20, blank=True)
    ordre = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Bloc de competence"
        verbose_name_plural = "Blocs de competences"
        ordering = ['ordre', 'code']
        unique_together = ['referentiel', 'code']

    def __str__(self):
        return f"{self.code} - {self.nom}"


class Competence(models.Model):
    bloc = models.ForeignKey(BlocCompetence, on_delete=models.CASCADE, related_name='competences')
    code = models.CharField(max_length=20)
    nom = models.CharField(max_length=300)
    ordre = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Competence"
        verbose_name_plural = "Competences"
        ordering = ['ordre', 'code']

    def __str__(self):
        return f"{self.code} - {self.nom}"


class CompetenceProfessionnelle(models.Model):
    competence = models.ForeignKey(Competence, on_delete=models.CASCADE, related_name='competences_pro')
    code = models.CharField(max_length=20)
    nom = models.CharField(max_length=300)
    ordre = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Competence professionnelle"
        verbose_name_plural = "Competences professionnelles"
        ordering = ['ordre', 'code']

    def __str__(self):
        return f"{self.code} - {self.nom}"


# CORRIGÉ ✅
class SousCompetence(models.Model):
    competence_pro = models.ForeignKey(
        CompetenceProfessionnelle, 
        on_delete=models.CASCADE, 
        related_name='sous_competences'
    )
    code = models.CharField(max_length=50, blank=True, default='')  # ← AJOUTÉ
    nom = models.CharField(max_length=500)
    ordre = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Sous-competence"
        verbose_name_plural = "Sous-competences"
        ordering = ['ordre']

    def __str__(self):
        if self.code:
            return f"{self.code} - {self.nom}"
        return self.nom


class CritereEvaluation(models.Model):
    sous_competence = models.ForeignKey(SousCompetence, on_delete=models.CASCADE, related_name='criteres')
    code = models.CharField(max_length=50, blank=True, default='')
    nom = models.CharField(max_length=500)
    ordre = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Critere d'evaluation"
        verbose_name_plural = "Criteres d'evaluation"
        ordering = ['ordre']

    def __str__(self):
        return self.nom


class IndicateurPerformance(models.Model):
    critere = models.ForeignKey(CritereEvaluation, on_delete=models.CASCADE, related_name='indicateurs')
    nom = models.CharField(max_length=500)
    poids = models.DecimalField(max_digits=5, decimal_places=2, default=10.0, help_text="Poids par defaut en %")
    ordre = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Indicateur de performance"
        verbose_name_plural = "Indicateurs de performance"
        ordering = ['ordre']

    def __str__(self):
        return self.nom


class Connaissance(models.Model):
    """Connaissance associee a une competence professionnelle — VERSION UNIQUE"""
    competence_pro = models.ForeignKey(
        CompetenceProfessionnelle,
        on_delete=models.CASCADE,
        related_name='connaissances'
    )
    code = models.CharField(max_length=50)
    nom = models.CharField(max_length=500)
    ordre = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Connaissance"
        verbose_name_plural = "Connaissances"
        ordering = ['ordre', 'code']

    def __str__(self):
        return f"{self.code} - {self.nom}"
    
# ================================================================
# SYSTÈME D'ÉVALUATION PAR COMPÉTENCES
# ================================================================


class FicheContrat(models.Model):
    referentiel = models.ForeignKey(
        'Referentiel',
        on_delete=models.CASCADE,
        related_name='fiches_contrat',
        verbose_name='Référentiel'
    )
    classe = models.ForeignKey(
        'Classe',
        on_delete=models.CASCADE,
        related_name='fiches_contrat',
        verbose_name='Classe'
    )
    titre_tp = models.CharField(
        max_length=300,
        verbose_name='Titre du TP'
    )
    problematique = models.TextField(
        blank=True,
        verbose_name='Problématique'
    )
    contexte = models.TextField(
        blank=True,
        verbose_name='Contexte professionnel'
    )
    date_tp = models.DateField(
        null=True,
        blank=True,
        verbose_name='Date du TP'
    )
    TYPE_EVALUATION_CHOICES = [
        ('formative', 'Formative'),
        ('sommative', 'Sommative'),
        ('certificative', 'Certificative'),
    ]

    type_evaluation = models.CharField(
        max_length=20,
        choices=TYPE_EVALUATION_CHOICES,
        default='formative',
        verbose_name="Type d'évaluation"
    )

    savoirs_associes = models.TextField(
        blank=True,
        verbose_name='Savoirs associés',
        help_text='Liste des savoirs S1, S2, etc.'
    )
    consigne = models.TextField(
        blank=True,
        verbose_name='Consigne pour les élèves',
        help_text='En atelier, vous devez...'
    )
    observation_environnement = models.TextField(
        blank=True,
        verbose_name='Observation de l\'environnement de travail',
        help_text='En atelier, je dois veiller à ce que...'
    )
    materiels = models.TextField(
        blank=True,
        verbose_name='Matériels à disposition',
        help_text='Je disposerais de...'
    )
    risques_epi = models.TextField(
        blank=True,
        verbose_name='Risques et EPI',
        help_text='Risques identifiés et EPI nécessaires'
    )

    createur = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='fiches_contrat_créées',
        verbose_name='Créateur'
    )
    date_creation = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Date de création'
    )
    date_modification = models.DateTimeField(
        auto_now=True,
        verbose_name='Date de modification'
    )
    actif = models.BooleanField(
        default=True,
        verbose_name='Actif'
    )

    # --- NOUVEAUX CHAMPS DE VALIDATION ---
    contrat_valide = models.BooleanField(default=False)
    fiches_eval_valide = models.BooleanField(default=False)
    # ------------------------------------

    class Meta:
        verbose_name = 'Fiche contrat'
        verbose_name_plural = 'Fiches contrat'
        ordering = ['-date_creation']

    def __str__(self):
        return f'{self.titre_tp} ({self.classe.nom})'

    # --- COLLEZ LE CODE ICI (DANS FicheContrat) ---
    @property
    def savoirs_uniques(self):
        if not self.savoirs_associes:
            return []
        
        # 1. On découpe ligne par ligne
        lignes = self.savoirs_associes.splitlines()
        
        # 2. On nettoie (enlève les espaces vides) et on filtre les lignes vides
        lignes_propres = [l.strip() for l in lignes if l.strip()]
        
        # 3. On enlève les doublons
        return list(dict.fromkeys(lignes_propres))
    def get_absolute_url(self):
        return reverse('core:evaluation_detail', kwargs={'pk': self.pk})

    def calculer_poids_total(self):
        from django.db.models import Sum
        total = self.lignes.aggregate(Sum('poids'))['poids__sum']
        return float(total) if total else 0.0


class LigneContrat(models.Model):
    fiche = models.ForeignKey(
        'FicheContrat',
        on_delete=models.CASCADE,
        related_name='lignes',
        verbose_name='Fiche contrat'
    )
    competence_pro = models.ForeignKey(
        'CompetenceProfessionnelle',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Compétence professionnelle'
    )
    sous_competence = models.ForeignKey(
        'SousCompetence',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Sous-compétence'
    )
    critere = models.ForeignKey(
        'CritereEvaluation',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Critère d\'évaluation'
    )
    indicateur = models.ForeignKey('IndicateurPerformance', 
        on_delete=models.SET_NULL, null=True, 
        blank=True, 
        verbose_name='Indicateur de performance'
    )

    poids = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=10.0,
        verbose_name='Poids (%)',
        help_text='Poids de cet indicateur dans l\'évaluation'
    )

    ordre = models.PositiveIntegerField(
        default=0,
        verbose_name='Ordre'
    )

    class Meta:
        verbose_name = 'Ligne de contrat'
        verbose_name_plural = 'Lignes de contrat'
        ordering = ['fiche', 'ordre']
        unique_together = ['fiche', 'indicateur']

    def __str__(self):
        return f'{self.indicateur.nom} ({self.poids}%)'


class FicheEvaluation(models.Model):
    fiche_contrat = models.ForeignKey(FicheContrat, on_delete=models.CASCADE, related_name='evaluations')
    eleve = models.ForeignKey('ProfilUtilisateur', on_delete=models.CASCADE) # Assurez-vous que 'ProfilUtilisateur' est bien le nom de votre modèle de profil d'utilisateur
    validee = models.BooleanField(default=False) # Validation de l'évaluation INDIVIDUELLE de l'élève
    date_validation = models.DateTimeField(null=True, blank=True)
    compte_rendu = models.TextField(blank=True)
    note_sur_20 = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="Note /20")
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('fiche_contrat', 'eleve')
        verbose_name = "Fiche d'évaluation"
        verbose_name_plural = "Fiches d'évaluation"

    def __str__(self):
        return f'{self.eleve.user.get_full_name()} - {self.fiche_contrat.titre_tp}'

    def calculer_note_sur_20(self):
        lignes = self.lignes_evaluation.exclude(
            note='NE'
        ).select_related('ligne_contrat')

        if not lignes.exists():
            self.note_sur_20 = 0.0 # Mettre 0.0 plutôt que None si pas de notes pour éviter des erreurs
            self.save(update_fields=['note_sur_20'])
            return 0.0

        total_pondere = 0.0
        poids_total = 0.0

        for ligne in lignes:
            try:
                note_int = int(ligne.note)
                poids = float(ligne.ligne_contrat.poids)
                total_pondere += (note_int / 4.0) * poids
                poids_total += poids
            except (ValueError, AttributeError):
                continue

        if poids_total == 0:
            self.note_sur_20 = 0.0
            self.save(update_fields=['note_sur_20'])
            return 0.0

        note = round((total_pondere / poids_total) * 20, 2)
        self.note_sur_20 = note
        self.save(update_fields=['note_sur_20'])
        return note

    def get_progression(self):
        total = self.lignes_evaluation.count()
        if total == 0:
            return 0
        evalues = self.lignes_evaluation.exclude(note='NE').count()
        return int((evalues / total) * 100)

    def get_detail_calcul(self):
        lignes = self.lignes_evaluation.select_related(
            'ligne_contrat',
            'ligne_contrat__indicateur',
            'ligne_contrat__competence_pro'
        ).order_by('ligne_contrat__ordre')

        details = []
        total_pondere = 0.0
        poids_evalues = 0.0
        poids_total_fiche = 0.0

        for ligne in lignes:
            poids = float(ligne.ligne_contrat.poids)
            poids_total_fiche += poids

            if ligne.note != 'NE':
                note_int = int(ligne.note)
                contribution = (note_int / 4.0) * poids
                total_pondere += contribution
                poids_evalues += poids
            else:
                note_int = None
                contribution = None

            details.append({
                'indicateur': ligne.ligne_contrat.indicateur.nom,
                'poids': poids,
                'note': ligne.note,
                'note_int': note_int,
                'contribution': round(contribution, 2) if contribution is not None else None,
            })

        note_20 = round((total_pondere / poids_evalues) * 20, 2) if poids_evalues > 0 else 0

        return {
            'details': details,
            'total_pondere': round(total_pondere, 2),
            'poids_evalues': round(poids_evalues, 2),
            'poids_total_fiche': round(poids_total_fiche, 2),
            'note_sur_20': note_20,
        }


class EvaluationLigne(models.Model):
    NOTES_CHOICES = [
        ('NE', 'Non évalué'), # Renommé pour cohérence
        ('0', '0 - Insuffisant'),
        ('1', '1 - Fragile'),
        ('2', '2 - Satisfaisant'),
        ('3', '3 - Très satisfaisant'), # Accent sur 'Très'
        ('4', '4 - Excellent'),
    ]

    fiche_evaluation = models.ForeignKey(
        'FicheEvaluation',
        on_delete=models.CASCADE,
        related_name='lignes_evaluation',
        verbose_name='Fiche d\'évaluation'
    )
    ligne_contrat = models.ForeignKey(
        'LigneContrat',
        on_delete=models.CASCADE,
        verbose_name='Ligne de contrat'
    )
    note = models.CharField(
        max_length=2,
        choices=NOTES_CHOICES,
        default='NE',
        verbose_name='Note'
    )

    class Meta:
        verbose_name = 'Ligne d\'évaluation'
        verbose_name_plural = 'Lignes d\'évaluation'
        ordering = ['ligne_contrat__ordre']
        unique_together = ['fiche_evaluation', 'ligne_contrat']

    def __str__(self):
        return f'{self.ligne_contrat.indicateur.nom} : {self.get_note_display()}'
    
# =====================================================
# PFMP - Périodes de Formation en Milieu Professionnel
# =====================================================
class PFMP(models.Model):
    TYPE_CONTENU_CHOICES = [
        ('fichier', 'Fichier (PDF, Word...)'),
        ('lien', 'Lien externe'),
        ('iframe', 'Intégration (iframe)'),
    ]

    classe = models.ForeignKey(
        Classe, on_delete=models.CASCADE, 
        related_name='pfmp', verbose_name='Classe'
    )
    titre = models.CharField(
        max_length=200, verbose_name='Titre',
        help_text='Ex: PFMP 1 - Période du 06/01 au 31/01'
    )
    description = models.TextField(
        blank=True, verbose_name='Description / Consignes'
    )
    date_debut = models.DateField(
        verbose_name='Date de début', null=True, blank=True
    )
    date_fin = models.DateField(
        verbose_name='Date de fin', null=True, blank=True
    )

    type_contenu = models.CharField(
        max_length=20, choices=TYPE_CONTENU_CHOICES,
        default='fichier', verbose_name='Type de ressource'
    )
    fichier = models.FileField(
        upload_to='pfmp/', blank=True, null=True, verbose_name='Document PDF'
    )
    lien_externe = models.URLField(
        blank=True, null=True, verbose_name='Lien externe'
    )
    code_iframe = models.TextField(
        blank=True, null=True, verbose_name="Code d'intégration iframe"
    )

    createur = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='pfmp_creees'
    )
    actif = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "PFMP"
        verbose_name_plural = "PFMP"
        ordering = ['classe__nom', 'date_debut']

    def __str__(self):
        return f"{self.titre} - {self.classe.nom}"

    def est_en_cours(self):
        from datetime import date
        today = date.today()
        if self.date_debut and self.date_fin:
            return self.date_debut <= today <= self.date_fin
        return False

    def est_a_venir(self):
        from datetime import date
        if self.date_debut:
            return date.today() < self.date_debut
        return False

    def est_passee(self):
        from datetime import date
        if self.date_fin:
            return date.today() > self.date_fin
        return False

    def est_fichier(self):
        return self.type_contenu == 'fichier' and self.fichier

    def est_lien(self):
        return self.type_contenu == 'lien' and self.lien_externe

    def est_iframe(self):
        return self.type_contenu == 'iframe' and self.code_iframe

    def est_periode(self):
        return self.date_debut is not None and self.date_fin is not None
    
# ═══════════════════════════════════════════════════════════
# AJOUTER CE CODE DANS models.py
# ═══════════════════════════════════════════════════════════

class Atelier(models.Model):
    """
    Ateliers pratiques pour les élèves
    (vidéos, tutoriels, exercices, ressources externes, etc.)
    """
    classe = models.ForeignKey(
        'Classe',
        on_delete=models.CASCADE,
        related_name='ateliers',
        verbose_name='Classe'
    )
    
    titre = models.CharField(
        max_length=200,
        verbose_name='Titre de l\'atelier'
    )
    
    description = models.TextField(
        blank=True,
        verbose_name='Description'
    )
    
    ordre = models.IntegerField(
        default=0,
        verbose_name='Ordre d\'affichage'
    )
    
    visible_eleves = models.BooleanField(
        default=True,
        verbose_name='Visible par les élèves'
    )
    
    actif = models.BooleanField(
        default=True,
        verbose_name='Actif'
    )
    
    # Type de contenu
    TYPE_CONTENU_CHOICES = [
        ('', 'Aucun'),
        ('fichier', 'Fichier'),
        ('lien', 'Lien externe'),
        ('iframe', 'Code intégré (iframe)'),
    ]
    
    type_contenu = models.CharField(
        max_length=20,
        choices=TYPE_CONTENU_CHOICES,
        blank=True,
        verbose_name='Type de contenu'
    )
    
    fichier = models.FileField(
        upload_to='ateliers/',
        blank=True,
        null=True,
        verbose_name='Fichier'
    )
    
    lien_externe = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name='Lien externe'
    )
    
    code_iframe = models.TextField(
        blank=True,
        null=True,
        verbose_name='Code d\'intégration (iframe)'
    )
    
    createur = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Créé par'
    )
    
    date_creation = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Date de création'
    )
    
    date_modification = models.DateTimeField(
        auto_now=True,
        verbose_name='Dernière modification'
    )
    
    class Meta:
        verbose_name = 'Atelier'
        verbose_name_plural = 'Ateliers'
        ordering = ['ordre', 'titre']
    
    def __str__(self):
        return f"{self.titre} - {self.classe.nom}"

# ═══════════════════════════════════════════════════════════
# À AJOUTER À LA FIN DE votre models.py
# APRÈS le modèle Atelier existant
# ═══════════════════════════════════════════════════════════

class DossierPFMP(models.Model):
    """Dossier contenant des fichiers pour une PFMP (comme Dossier pour Theme)"""
    pfmp = models.ForeignKey(
        'PFMP',
        on_delete=models.CASCADE,
        related_name='dossiers',
        verbose_name='PFMP'
    )
    nom = models.CharField(max_length=200, verbose_name='Nom du dossier')
    description = models.TextField(blank=True, verbose_name='Description')
    ordre = models.IntegerField(default=0, verbose_name='Ordre')
    visible_eleves = models.BooleanField(default=True, verbose_name='Visible par les élèves')
    actif = models.BooleanField(default=True, verbose_name='Actif')
    date_creation = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Dossier PFMP'
        verbose_name_plural = 'Dossiers PFMP'
        ordering = ['ordre', 'nom']
    
    def __str__(self):
        return f"{self.nom} - {self.pfmp.titre}"


class FichierPFMP(models.Model):
    """Fichier dans un dossier PFMP"""
    dossier = models.ForeignKey(
        'DossierPFMP',
        on_delete=models.CASCADE,
        related_name='fichiers',
        verbose_name='Dossier'
    )
    nom = models.CharField(max_length=200, verbose_name='Nom')
    
    TYPE_CONTENU_CHOICES = [
        ('fichier', 'Fichier'),
        ('lien', 'Lien externe'),
        ('iframe', 'Code intégré'),
    ]
    type_contenu = models.CharField(max_length=20, choices=TYPE_CONTENU_CHOICES, default='fichier')
    fichier = models.FileField(upload_to='pfmp/fichiers/', blank=True, null=True)
    lien_externe = models.URLField(max_length=500, blank=True, null=True)
    code_iframe = models.TextField(blank=True, null=True)
    ordre = models.IntegerField(default=0)
    visible_eleves = models.BooleanField(default=True)
    actif = models.BooleanField(default=True)
    createur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Fichier PFMP'
        verbose_name_plural = 'Fichiers PFMP'
        ordering = ['ordre', 'nom']
    
    def __str__(self):
        return f"{self.nom} - {self.dossier.nom}"


class DossierAtelier(models.Model):
    """Dossier contenant des fichiers pour un atelier"""
    atelier = models.ForeignKey(
        'Atelier',
        on_delete=models.CASCADE,
        related_name='dossiers',
        verbose_name='Atelier'
    )
    nom = models.CharField(max_length=200, verbose_name='Nom du dossier')
    description = models.TextField(blank=True, default='')
    ordre = models.IntegerField(default=0, verbose_name='Ordre')
    visible_eleves = models.BooleanField(default=True, verbose_name='Visible')
    actif = models.BooleanField(default=True, verbose_name='Actif')
    date_creation = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Dossier Atelier'
        verbose_name_plural = 'Dossiers Atelier'
        ordering = ['ordre', 'nom']
    
    def __str__(self):
        return f"{self.nom} - {self.atelier.titre}"


class FichierAtelier(models.Model):
    """Fichier dans un dossier d'atelier"""
    dossier = models.ForeignKey(
        'DossierAtelier',
        on_delete=models.CASCADE,
        related_name='fichiers',
        verbose_name='Dossier'
    )
    nom = models.CharField(max_length=200, verbose_name='Nom')
    
    TYPE_CONTENU_CHOICES = [
        ('fichier', 'Fichier'),
        ('lien', 'Lien externe'),
        ('iframe', 'Code intégré'),
    ]
    type_contenu = models.CharField(max_length=20, choices=TYPE_CONTENU_CHOICES, default='fichier')
    fichier = models.FileField(upload_to='ateliers/fichiers/', blank=True, null=True)
    lien_externe = models.URLField(max_length=500, blank=True, null=True)
    code_iframe = models.TextField(blank=True, null=True)
    ordre = models.IntegerField(default=0)
    visible_eleves = models.BooleanField(default=True)
    actif = models.BooleanField(default=True)
    createur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Fichier Atelier'
        verbose_name_plural = 'Fichiers Atelier'
        ordering = ['ordre', 'nom']
    
    def __str__(self):
        return f"{self.nom} - {self.dossier.nom}"


# =====================================================
# SUIVI DES CONNEXIONS ÉLÈVES
# =====================================================

class ConnexionEleve(models.Model):
    """Enregistre chaque connexion d'un élève (signal user_logged_in)."""
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='connexions')
    horodatage = models.DateTimeField(auto_now_add=True)
    adresse_ip = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        verbose_name = 'Connexion élève'
        verbose_name_plural = 'Connexions élèves'
        ordering = ['-horodatage']

    def __str__(self):
        return f"{self.user.get_full_name()} — {self.horodatage:%d/%m/%Y %H:%M}"


# =====================================================
# FICHES DE RÉVISION (FLASHCARDS)
# =====================================================

class FicheRevision(models.Model):
    
    dossier = models.ForeignKey(Dossier, on_delete=models.CASCADE, related_name='fiches_revision', null=True, blank=True)
    titre = models.CharField(max_length=200)
    createur = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='fiches_revision_creees'
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    actif = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Fiche de révision"
        verbose_name_plural = "Fiches de révision"
        ordering = ['titre']

    def __str__(self):
        return self.titre


class CarteRevision(models.Model):
    fiche = models.ForeignKey(
        FicheRevision,
        on_delete=models.CASCADE,
        related_name='cartes'
    )
    question = models.TextField()
    reponse = models.TextField()
    image_url = models.URLField(blank=True)
    ordre = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Carte de révision"
        verbose_name_plural = "Cartes de révision"
        ordering = ['ordre']


# =====================================================
# QCM
# =====================================================

class QCM(models.Model):
    theme = models.ForeignKey(
        'Theme',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='qcms'
    )
    titre = models.CharField(max_length=200)
    classe = models.ForeignKey(
        'Classe',
        on_delete=models.CASCADE,
        related_name='qcms'
    )
    createur = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='qcms_crees'
    )
    date_limite = models.DateTimeField()
    melange_questions = models.BooleanField(default=True)
    actif = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "QCM"
        verbose_name_plural = "QCM"
        ordering = ['-date_creation']

    def __str__(self):
        return self.titre


class QuestionQCM(models.Model):
    CHOIX_REPONSE = [
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
        ('D', 'D'),
    ]

    qcm = models.ForeignKey(
        QCM,
        on_delete=models.CASCADE,
        related_name='questions'
    )
    enonce = models.TextField()
    image_url = models.URLField(blank=True)
    choix_a = models.CharField(max_length=300)
    choix_b = models.CharField(max_length=300)
    choix_c = models.CharField(max_length=300, blank=True)
    choix_d = models.CharField(max_length=300, blank=True)
    bonne_reponse = models.CharField(max_length=1, choices=CHOIX_REPONSE)
    ordre = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Question QCM"
        verbose_name_plural = "Questions QCM"
        ordering = ['ordre']


class SessionQCM(models.Model):
    qcm = models.ForeignKey(
        QCM,
        on_delete=models.CASCADE,
        related_name='sessions'
    )
    eleve = models.ForeignKey(
        'ProfilUtilisateur',
        on_delete=models.CASCADE,
        related_name='sessions_qcm'
    )
    reponses = models.JSONField(default=dict)
    note_sur_20 = models.FloatField(null=True, blank=True)
    nb_bonnes_reponses = models.IntegerField(default=0)
    date_soumission = models.DateTimeField(null=True, blank=True)
    termine = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Session QCM"
        verbose_name_plural = "Sessions QCM"
        unique_together = ['qcm', 'eleve']


# =====================================================
# SUIVI PFMP PAR ÉLÈVE
# =====================================================
class SuiviPFMP(models.Model):
    """Suivi des jours effectués / manqués d'un élève sur une PFMP."""
    pfmp = models.ForeignKey(
        'PFMP', on_delete=models.CASCADE, related_name='suivis',
        verbose_name='PFMP'
    )
    eleve = models.ForeignKey(
        'ProfilUtilisateur', on_delete=models.CASCADE, related_name='suivis_pfmp',
        verbose_name='Élève'
    )
    nb_jours_effectues = models.PositiveIntegerField(
        default=0, verbose_name='Jours effectués'
    )
    nb_jours_manques_justifies = models.PositiveIntegerField(
        default=0, verbose_name='Absences justifiées (j)'
    )
    nb_jours_manques_injustifies = models.PositiveIntegerField(
        default=0, verbose_name='Absences injustifiées (j)'
    )
    commentaire = models.TextField(blank=True, default='', verbose_name='Commentaire')
    date_maj = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['pfmp', 'eleve']
        verbose_name = "Suivi PFMP élève"
        verbose_name_plural = "Suivis PFMP élèves"
        ordering = ['pfmp', 'eleve__user__last_name']

    def __str__(self):
        return f"{self.eleve} – {self.pfmp.titre}"

    @property
    def nb_jours_manques_total(self):
        return self.nb_jours_manques_justifies + self.nb_jours_manques_injustifies

    @property
    def nb_jours_total(self):
        return self.nb_jours_effectues + self.nb_jours_manques_total

    @property
    def taux_presence(self):
        total = self.nb_jours_total
        return round(self.nb_jours_effectues * 100 / total, 1) if total > 0 else None


# =====================================================
# HISTORIQUE DES CLASSES D'UN ÉLÈVE
# =====================================================
class HistoriqueClasse(models.Model):
    """Trace le passage d'un élève dans chaque classe au fil des années."""
    eleve = models.ForeignKey(
        'ProfilUtilisateur', on_delete=models.CASCADE,
        related_name='historique_classes', verbose_name='Élève'
    )
    classe = models.ForeignKey(
        'Classe', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='historique_eleves', verbose_name='Classe'
    )
    annee = models.CharField(
        max_length=9, verbose_name='Année scolaire',
        help_text='Ex : 2024-2025'
    )
    date_debut = models.DateField(verbose_name='Date de début')
    date_fin = models.DateField(null=True, blank=True, verbose_name='Date de fin')
    redoublement = models.BooleanField(default=False, verbose_name='Redoublement')

    class Meta:
        verbose_name = "Historique classe"
        verbose_name_plural = "Historiques classes"
        ordering = ['eleve', 'date_debut']

    def __str__(self):
        classe_nom = self.classe.nom if self.classe else '—'
        return f"{self.eleve} — {classe_nom} ({self.annee})"


# =====================================================
# MODES OPÉRATOIRES
# =====================================================
class ModeOperatoire(models.Model):
    """Mode opératoire lié à un thème ou un atelier."""
    theme = models.ForeignKey(
        'Theme', on_delete=models.SET_NULL,
        related_name='modes_operatoires',
        null=True, blank=True,
        verbose_name='Thème'
    )
    atelier = models.ForeignKey(
        'Atelier', on_delete=models.SET_NULL,
        related_name='modes_operatoires',
        null=True, blank=True,
        verbose_name='Atelier'
    )
    titre = models.CharField(max_length=200, verbose_name='Titre')
    description = models.TextField(blank=True, verbose_name='Description')
    createur = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='modes_operatoires',
        verbose_name='Créateur'
    )
    date_creation = models.DateTimeField(auto_now_add=True, verbose_name='Date de création')
    date_modification = models.DateTimeField(auto_now=True, verbose_name='Date de modification')
    actif = models.BooleanField(default=True, verbose_name='Actif')
    visible_eleves = models.BooleanField(default=False, verbose_name='Visible aux élèves')

    class Meta:
        verbose_name = "Mode opératoire"
        verbose_name_plural = "Modes opératoires"
        ordering = ['-date_creation']

    def __str__(self):
        return self.titre


class LigneModeOperatoire(models.Model):
    """Ligne (phase) d'un mode opératoire."""
    mode_operatoire = models.ForeignKey(
        ModeOperatoire, on_delete=models.CASCADE,
        related_name='lignes',
        verbose_name='Mode opératoire'
    )
    ordre = models.PositiveIntegerField(default=0, verbose_name='Ordre')
    phase = models.CharField(
        max_length=200,
        verbose_name='Phase',
        help_text='Ex : "Approvisionnement des matériaux"'
    )
    schema_image = models.ImageField(
        upload_to='modes_operatoires/schemas/',
        blank=True, null=True,
        verbose_name='Schéma / image'
    )
    operations = models.TextField(verbose_name='Opérations détaillées')
    materiels = models.TextField(verbose_name='Matériels et outils')
    controle = models.TextField(verbose_name='Points de contrôle')
    risques_sante = models.TextField(
        verbose_name='Risques santé et prévention'
    )
    risques_environnement = models.TextField(
        verbose_name='Risques environnement et prévention'
    )

    class Meta:
        ordering = ['ordre']
        verbose_name = "Ligne mode opératoire"
        verbose_name_plural = "Lignes mode opératoire"

    def __str__(self):
        return f"{self.mode_operatoire.titre} – phase {self.ordre} : {self.phase}"
