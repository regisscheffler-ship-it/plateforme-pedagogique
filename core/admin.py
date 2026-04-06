from django.contrib import admin
from .models import (
    ProfilUtilisateur, Niveau, Classe, Theme, Dossier,
    Fichier, TypeRessource, TravailARendre, RenduEleve,
    Notification, Archive, EtablissementOrigine,
    MessageEleve, ReponseProf,
    Referentiel, BlocCompetence, Competence, CompetenceProfessionnelle,
    SousCompetence, CritereEvaluation, IndicateurPerformance,
    FicheContrat, LigneContrat, FicheEvaluation, EvaluationLigne,
    DossierPFMP, FichierPFMP, DossierAtelier, FichierAtelier,
    FicheRevision, CarteRevision, QCM, QuestionQCM, SessionQCM,
    SuiviPFMP, HistoriqueClasse,
    ModeOperatoire, LigneModeOperatoire,
)


# ================================
# MODÈLES EXISTANTS
# ================================

admin.site.register(Niveau)
admin.site.register(Classe)
admin.site.register(TypeRessource)


@admin.register(SuiviPFMP)
class SuiviPFMPAdmin(admin.ModelAdmin):
    list_display = ['pfmp', 'eleve', 'nb_jours_effectues', 'nb_jours_manques_justifies', 'nb_jours_manques_injustifies', 'date_maj']
    list_filter  = ['pfmp__classes']
    search_fields = ['eleve__user__last_name', 'pfmp__titre']
    autocomplete_fields = []


@admin.register(HistoriqueClasse)
class HistoriqueClasseAdmin(admin.ModelAdmin):
    list_display  = ['eleve', 'classe', 'annee', 'date_debut', 'date_fin']
    list_filter   = ['annee', 'classe']
    search_fields = ['eleve__user__last_name', 'eleve__user__first_name']


# ================================
# MODÈLES ÉVALUATIONS (NOUVEAU)
# ================================

@admin.register(Referentiel)
class ReferentielAdmin(admin.ModelAdmin):
    list_display = ['nom', 'actif', 'date_creation']
    list_filter = ['actif']
    search_fields = ['nom']
    list_editable = ['actif']


@admin.register(BlocCompetence)
class BlocCompetenceAdmin(admin.ModelAdmin):
    list_display = ['nom', 'referentiel', 'ordre']
    list_filter = ['referentiel']
    search_fields = ['nom']


@admin.register(Competence)
class CompetenceAdmin(admin.ModelAdmin):
    list_display = ['nom', 'code', 'bloc', 'ordre']
    list_filter = ['bloc__referentiel']
    search_fields = ['nom', 'code']


@admin.register(CompetenceProfessionnelle)
class CompetenceProfessionnelleAdmin(admin.ModelAdmin):
    list_display = ['nom', 'code', 'competence', 'ordre']
    list_filter = ['competence__bloc__referentiel']
    search_fields = ['nom', 'code']


@admin.register(SousCompetence)
class SousCompetenceAdmin(admin.ModelAdmin):
    list_display = ['nom', 'competence_pro', 'ordre']
    search_fields = ['nom']


@admin.register(CritereEvaluation)
class CritereEvaluationAdmin(admin.ModelAdmin):
    list_display = ['nom', 'sous_competence', 'ordre']
    search_fields = ['nom']


@admin.register(IndicateurPerformance)
class IndicateurPerformanceAdmin(admin.ModelAdmin):
    list_display = ['nom', 'critere', 'poids', 'ordre']
    search_fields = ['nom']
    list_filter = ['critere__sous_competence__competence_pro']


@admin.register(FicheContrat)
class FicheContratAdmin(admin.ModelAdmin):
    list_display = ['titre_tp', 'classe', 'referentiel', 'type_evaluation', 'createur', 'date_creation', 'actif']
    list_filter = ['classe', 'referentiel', 'type_evaluation', 'actif', 'date_creation']
    search_fields = ['titre_tp', 'problematique']
    readonly_fields = ['date_creation']


@admin.register(LigneContrat)
class LigneContratAdmin(admin.ModelAdmin):
    list_display = ['fiche', 'competence_pro', 'indicateur', 'poids', 'ordre']
    list_filter = ['fiche']
    search_fields = ['indicateur__nom']


@admin.register(FicheEvaluation)
class FicheEvaluationAdmin(admin.ModelAdmin):
    list_display = ['fiche_contrat', 'eleve', 'validee', 'note_sur_20', 'date_creation', 'date_validation']
    list_filter = ['validee', 'date_creation', 'date_validation']
    search_fields = ['eleve__user__last_name', 'eleve__user__first_name', 'fiche_contrat__titre_tp']
    readonly_fields = ['date_creation', 'note_sur_20']  # ✅ CORRIGÉ : supprimé 'date_modification'


@admin.register(EvaluationLigne)
class EvaluationLigneAdmin(admin.ModelAdmin):
    list_display = ['fiche_evaluation', 'ligne_contrat', 'note']
    list_filter = ['note', 'fiche_evaluation__validee']
    search_fields = ['fiche_evaluation__eleve__user__last_name']


# ================================
# FICHES DE RÉVISION & QCM
# ================================

@admin.register(FicheRevision)
class FicheRevisionAdmin(admin.ModelAdmin):
    list_display = ('titre', 'dossier', 'actif') # <-- J'ai retiré 'nb_cartes' ici
    list_filter = ('dossier',)
    search_fields = ['titre']
    list_editable = ['actif']
    readonly_fields = ['date_creation']


@admin.register(CarteRevision)
class CarteRevisionAdmin(admin.ModelAdmin):
    list_display = ['fiche', 'question', 'ordre']
    list_filter = ['fiche']
    search_fields = ['question', 'reponse']


@admin.register(QCM)
class QCMAdmin(admin.ModelAdmin):
    list_display = ['titre', 'classe', 'theme', 'createur', 'date_limite', 'actif', 'date_creation']
    list_filter = ['actif', 'classe', 'theme']
    search_fields = ['titre']
    list_editable = ['actif']
    readonly_fields = ['date_creation']


@admin.register(QuestionQCM)
class QuestionQCMAdmin(admin.ModelAdmin):
    list_display = ['qcm', 'enonce', 'bonne_reponse', 'ordre']
    list_filter = ['qcm', 'bonne_reponse']
    search_fields = ['enonce']


@admin.register(SessionQCM)
class SessionQCMAdmin(admin.ModelAdmin):
    list_display = ['qcm', 'eleve', 'note_sur_20', 'nb_bonnes_reponses', 'termine', 'date_soumission']
    list_filter = ['termine', 'qcm']
    search_fields = ['eleve__user__last_name', 'eleve__user__first_name']
    readonly_fields = ['date_soumission']


class LigneModeOperatoireInline(admin.TabularInline):
    model = LigneModeOperatoire
    extra = 1
    fields = ['ordre', 'phase', 'schema_image', 'operations', 'materiels', 'controle', 'risques_sante', 'risques_environnement']


@admin.register(ModeOperatoire)
class ModeOperatoireAdmin(admin.ModelAdmin):
    list_display = ['titre', 'theme', 'atelier', 'createur', 'actif', 'date_creation']
    list_filter = ['actif', 'theme', 'atelier']
    search_fields = ['titre', 'description']
    list_editable = ['actif']
    readonly_fields = ['date_creation', 'date_modification']
    inlines = [LigneModeOperatoireInline]


@admin.register(LigneModeOperatoire)
class LigneModeOperatoireAdmin(admin.ModelAdmin):
    list_display = ['mode_operatoire', 'ordre', 'phase']
    list_filter = ['mode_operatoire']
    search_fields = ['phase', 'operations']
    ordering = ['mode_operatoire', 'ordre']


@admin.register(ProfilUtilisateur)
class ProfilUtilisateurAdmin(admin.ModelAdmin):
    list_display = ['user', 'type_utilisateur', 'classe', 'compte_approuve', 'est_sorti']
    list_filter = ['type_utilisateur', 'compte_approuve', 'est_sorti']
    search_fields = ['user__username', 'user__first_name', 'user__last_name']
    list_editable = ['type_utilisateur', 'compte_approuve']


@admin.register(MessageEleve)
class MessageEleveAdmin(admin.ModelAdmin):
    list_display = ['eleve', 'professeur', 'date_envoi', 'lu']
    list_filter = ['lu']

