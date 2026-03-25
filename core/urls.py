# core/urls.py — VERSION CORRIGÉE
from django.urls import path
from . import views_lazy as views
from .views_signed import download_fichier_atelier_signed

app_name = 'core'

urlpatterns = [


    # ═══════════════════════════════════════
    # PAGE D'ACCUEIL
    # ═══════════════════════════════════════
    path('', views.home, name='home'),

    # ═══════════════════════════════════════
    # AUTHENTIFICATION
    # ═══════════════════════════════════════
    path('login/professeur/', views.login_prof_view,  name='login_prof'),
    path('login/eleve/',      views.login_eleve_view, name='login_eleve'),
    path('logout/',           views.logout_view,       name='logout'),

    # ═══════════════════════════════════════
    # INSCRIPTION ÉLÈVES
    # ═══════════════════════════════════════
    path('inscription/',                                   views.inscription_eleve,      name='inscription_eleve'),
    path('inscription/choix/',                             views.choix_eleve,            name='choix_eleve'),
    path('inscription/completer-profil/<int:profil_id>/', views.completer_profil_eleve, name='completer_profil_eleve'),

    # ═══════════════════════════════════════
    # DASHBOARDS
    # ═══════════════════════════════════════
    path('dashboard/professeur/', views.dashboard_professeur, name='dashboard_professeur'),
    path('dashboard/eleve/',      views.dashboard_eleve,      name='dashboard_eleve'),

    # ═══════════════════════════════════════
    # GESTION CLASSES
    # ═══════════════════════════════════════
    path('gestion/classes/',                    views.gestion_classes,  name='gestion_classes'),
    path('gestion/classes/liste/',              views.classe_list,       name='classe_list'),
    path('gestion/classes/<int:pk>/',           views.classe_detail,     name='classe_detail'),
    path('gestion/classes/<int:pk>/modifier/',  views.classe_update,     name='classe_update'),
    path('gestion/classes/<int:pk>/supprimer/', views.supprimer_classe,  name='supprimer_classe'),

    # ═══════════════════════════════════════
    # GESTION ÉLÈVES
    # ═══════════════════════════════════════
    path('gestion/eleves/',                        views.gestion_eleves,       name='gestion_eleves'),
    path('gestion/eleves/<int:pk>/modifier/',      views.modifier_eleve,       name='modifier_eleve'),
    path('gestion/eleves/<int:pk>/supprimer/',     views.supprimer_eleve,      name='supprimer_eleve'),
    path('gestion/eleves/<int:pk>/reactiver/',     views.reactiver_eleve,      name='reactiver_eleve'),
    path('gestion/eleves/approbations/',           views.gestion_approbations, name='gestion_approbations'),
    path('gestion/eleves/<int:pk>/approuver/',     views.approuver_eleve,      name='approuver_eleve'),
    path('gestion/eleves/<int:pk>/refuser/',       views.refuser_eleve,        name='refuser_eleve'),
    path('eleves/<int:pk>/muter/',                 views.muter_eleve,          name='muter_eleve'),
    # ═══════════════════════════════════════
    # GESTION SORTIES
    # ═══════════════════════════════════════
    path('gestion/sorties/',                  views.gestion_sorties, name='gestion_sorties'),
    path('gestion/sorties/<int:pk>/marquer/', views.marquer_sortie,  name='marquer_sortie'),
    path('gestion/sorties/<int:pk>/modifier/', views.modifier_sortie, name='modifier_sortie'),
    path('gestion/eleves/<int:eleve_id>/passer-classe/', views.passer_en_classe_superieure, name='passer_en_classe_superieure'),

    # ═══════════════════════════════════════
    # THÈMES
    # ═══════════════════════════════════════
    path('gestion/themes/',                    views.gestion_themes,          name='gestion_themes'),
    path('themes/creer/',                      views.theme_create,            name='theme_create'),
    path('themes/<int:pk>/',                   views.theme_detail,            name='theme_detail'),
    path('themes/<int:pk>/modifier/',          views.theme_update,            name='theme_update'),
    path('themes/<int:pk>/editer/',            views.theme_edit,              name='theme_edit'),
    path('themes/<int:pk>/supprimer/',         views.theme_delete,            name='theme_delete'),
    path('themes/<int:pk>/toggle-visibilite/', views.theme_toggle_visibilite, name='theme_toggle_visibilite'),

    # ═══════════════════════════════════════
    # FICHES DE RÉVISION
    # ═══════════════════════════════════════
    path('dossiers/<int:dossier_id>/fiche/create/',     views.fiche_revision_create,      name='fiche_revision_create'),
    path('fiches-revision/<int:pk>/',                   views.fiche_revision_detail,      name='fiche_revision_detail'),
    path('fiches-revision/<int:fiche_id>/import-csv/',  views.fiche_revision_import_csv,  name='fiche_revision_import_csv'),
    path('fiches-revision/<int:pk>/supprimer/',         views.fiche_revision_delete,      name='fiche_revision_delete'),
    path('fiches-revision/<int:pk>/modifier/',          views.fiche_revision_update,      name='fiche_revision_update'),
    path('cartes-revision/<int:pk>/supprimer/',         views.carte_revision_delete,      name='carte_revision_delete'),

    # ═══════════════════════════════════════
    # QCM
    # ═══════════════════════════════════════
    path('qcm/',                            views.qcm_gestion,                  name='qcm_gestion'),
    path('qcm/creer/<int:theme_id>/',       views.qcm_create,                   name='qcm_create'),
    path('qcm/creer/',                      views.qcm_creer_depuis_dashboard,   name='qcm_creer_depuis_dashboard'),
    path('qcm/<int:pk>/editer/',            views.qcm_edit,                     name='qcm_edit'),
    path('qcm/<int:pk>/activer/',           views.qcm_toggle_actif,             name='qcm_toggle_actif'),
    path('qcm/<int:pk>/supprimer/',         views.qcm_delete,                   name='qcm_delete'),
    path('questions/<int:pk>/supprimer/',   views.question_delete,              name='question_delete'),
    path('questions/<int:pk>/editer/',      views.question_edit,                name='question_edit'),
    path('questions/<int:pk>/regenerer/',   views.question_regenerer,           name='question_regenerer'),
    path('qcm/<int:pk>/passer/',            views.qcm_passer,                   name='qcm_passer'),
    path('qcm/session/<int:pk>/resultats/', views.qcm_resultats,                name='qcm_resultats'),
    path('qcm/<int:pk>/resultats-classe/',  views.qcm_resultats_prof,           name='qcm_resultats_prof'),
    path('qcm/<int:pk>/archiver/',          views.qcm_archiver,                 name='qcm_archiver'),

    # ═══════════════════════════════════════
    # DOSSIERS
    # ═══════════════════════════════════════
    path('dossiers/creer/<int:theme_id>/',       views.dossier_create,            name='dossier_create'),
    path('dossiers/<int:pk>/',                   views.dossier_detail,            name='dossier_detail'),
    path('dossiers/<int:pk>/modifier/',          views.dossier_update,            name='dossier_update'),
    path('dossiers/<int:pk>/supprimer/',         views.dossier_delete,            name='dossier_delete'),
    path('dossiers/<int:pk>/toggle-visibilite/', views.dossier_toggle_visibilite, name='dossier_toggle_visibilite'),

    # ═══════════════════════════════════════
    # FICHIERS
    # ═══════════════════════════════════════
    path('fichiers/upload/<int:dossier_id>/', views.fichier_upload, name='fichier_upload'),
    path('fichiers/<int:pk>/modifier/',       views.fichier_update, name='fichier_update'),
    path('fichiers/<int:pk>/supprimer/',         views.fichier_delete,             name='fichier_delete'),
    path('fichiers/<int:pk>/toggle-visibilite/', views.fichier_toggle_visibilite,   name='fichier_toggle_visibilite'),

    # ═══════════════════════════════════════
    # ÉVALUATIONS
    # ═══════════════════════════════════════
    path('evaluations/',                                              views.evaluations_home,              name='evaluations_home'),
    path('evaluations/parametres/',                                   views.evaluation_parametres,          name='evaluation_parametres'),
    path('evaluations/creer/',                                        views.creer_evaluation,               name='creer_evaluation'),
    path('evaluations/detail/<int:pk>/',                              views.evaluation_detail,              name='evaluation_detail'),
    path('evaluations/select-eleves/<int:fiche_contrat_id>/',         views.fiche_evaluation_select_eleves, name='fiche_evaluation_select_eleves'),
    path('evaluations/saisie/<int:fiche_contrat_id>/<int:eleve_id>/', views.fiche_evaluation_saisie,        name='fiche_evaluation_saisie'),
    path('evaluations/deverrouiller/<int:fiche_eval_id>/',            views.deverrouiller_fiche_evaluation, name='deverrouiller_fiche_evaluation'),
    path('evaluations/creer-absent/<int:fiche_contrat_id>/<int:eleve_id>/', views.creer_fiche_absent,       name='creer_fiche_absent'),
    path('evaluations/<int:pk>/supprimer/',                           views.fiche_contrat_supprimer,        name='fiche_contrat_supprimer'),
    path('evaluations/<int:pk>/archiver/',                            views.fiche_contrat_archiver,         name='fiche_contrat_archiver'),
    path('evaluations/<int:pk>/lier-atelier/',                          views.evaluation_lier_atelier,        name='evaluation_lier_atelier'),
    path('evaluations/<int:pk>/export-archive/',                        views.export_fiche_contrat_archive,   name='export_fiche_contrat_archive'),

    # Impression
    path('evaluations/print-contrat/<int:fiche_contrat_id>/',    views.generer_fiches_eleves,     name='generer_fiches_eleves'),
    path('evaluations/print-eval/<int:fiche_contrat_id>/',       views.generer_fiches_evaluation, name='generer_fiches_evaluation'),

    # Validation
    path('evaluation/valider-contrat/<int:pk>/',     views.valider_contrat,          name='valider_contrat'),
    path('evaluation/valider-fiches-eval/<int:pk>/', views.valider_fiches_evaluation, name='valider_fiches_evaluation'),

    # Vue élève
    path('eleve/fiche-contrat/<int:pk>/',    views.eleve_voir_fiche_contrat,    name='eleve_voir_fiche_contrat'),
    path('eleve/fiche-evaluation/<int:pk>/', views.eleve_voir_fiche_evaluation, name='eleve_voir_fiche_evaluation'),
    path('eleve/fiche-complete/<int:pk>/',   views.eleve_fiche_complete,        name='eleve_fiche_complete'),

    # ═══════════════════════════════════════
    # TRAVAUX
    # ✅ CORRECTION PRINCIPALE du dashboard :
    #    Le dashboard appelle {% url 'core:travaux_par_classe' %} SANS argument.
    #    Ancienne route : path('travaux/par-classe/<int:classe_id>/') → exige classe_id → NoReverseMatch
    #    Nouvelle route sans paramètre ajoutée sous le nom 'travaux_par_classe'
    #    L'ancienne route avec classe_id renommée 'travaux_par_classe_id'
    # ═══════════════════════════════════════
    path('travaux/creer/',                        views.travaux_creer,      name='travaux_creer'),
    path('travaux/corriger/',                     views.travaux_corriger,   name='travaux_corriger'),
    path('travaux/classes/',                      views.travaux_par_classe, name='travaux_par_classe'),       # ✅ sans classe_id — utilisé par le dashboard
    path('travaux/par-classe/<int:classe_id>/',   views.travaux_par_classe, name='travaux_par_classe_id'),    # avec classe_id — utilisé dans les listes
    path('travaux/creer-nouveau/<int:classe_id>/', views.travail_create,    name='travail_create'),
    path('travaux/<int:pk>/',                     views.travail_detail,     name='travail_detail'),
    path('travaux/<int:pk>/supprimer/',           views.travail_delete,     name='travail_delete'),

    # ═══════════════════════════════════════
    # TRAVAUX ÉLÈVES
    # ═══════════════════════════════════════
    path('mes-travaux/',                      views.mes_travaux_eleve, name='mes_travaux_eleve'),
    path('travaux/<int:pk>/rendre/',          views.rendre_travail,    name='rendre_travail'),
    path('travaux/<int:pk>/corriger/',        views.corriger_rendu,    name='corriger_rendu'),
    path('travaux/<int:pk>/marquer-corrige/', views.marquer_corrige,   name='marquer_corrige'),

    # COMMUNICATIONS (ÉLÈVE → PROFESSEUR)
    path('communication/',                                views.communication_eleve,  name='communication_eleve'),
    path('communication/prof/',                           views.communication_prof,   name='communication_prof'),
    path('communication/repondre/<int:message_id>/',     views.communication_repondre, name='communication_repondre'),
    path('communication/supprimer/<int:message_id>/',    views.communication_supprimer, name='communication_supprimer'),
    path('communications/',                               views.communications_list,  name='communications_list'),
    path('communications/export-pdf/',                   views.communications_export_pdf, name='communications_export_pdf'),

    # ═══════════════════════════════════════
    # NOTIFICATIONS
    # ═══════════════════════════════════════
    path('mes-notifications/',               views.mes_notifications,        name='mes_notifications'),
    path('notifications/<int:pk>/lue/',      views.marquer_notification_lue, name='marquer_notification_lue'),
    path('notifications/toutes-lues/',       views.marquer_toutes_lues,      name='marquer_toutes_lues'),

    # ═══════════════════════════════════════
    # ARCHIVES & STATS
    # ═══════════════════════════════════════
    path('archives/',                    views.archives,          name='archives'),
    path('archives/export/',             views.archives_export,   name='archives_export'),
    path('archives/export-complet/',     views.export_annuel_complet,  name='export_annuel_complet'),  # ← NOUVEAU
    path('archives/<int:pk>/supprimer/', views.supprimer_archive, name='supprimer_archive'),
    path('archives/<int:pk>/',           views.archive_detail,    name='archive_detail'),
    path('statistiques/',                views.statistiques,      name='statistiques'),

    # ═══════════════════════════════════════
    # API AJAX
    # ═══════════════════════════════════════
    path('api/eleves/',      views.api_eleves_par_classe,           name='api_eleves'),
    path('api/competences/', views.api_competences_par_referentiel,  name='api_competences'),

    # ═══════════════════════════════════════
    # CONTACT
    # ═══════════════════════════════════════
    path('contact/', views.contact, name='contact'),

    # ═══════════════════════════════════════
    # PFMP
    # ═══════════════════════════════════════
    path('gestion/pfmp/',                  views.gestion_pfmp,  name='gestion_pfmp'),
    path('gestion/pfmp/creer/',            views.pfmp_create,   name='pfmp_create'),
    path('gestion/pfmp/<int:pk>/',         views.pfmp_detail,   name='pfmp_detail'),
    path('gestion/pfmp/<int:pk>/modifier/',  views.pfmp_update,   name='pfmp_update'),
    path('pfmp/<int:pk>/supprimer/',          views.pfmp_supprimer, name='pfmp_supprimer'),
    path('gestion/pfmp/<int:pfmp_id>/suivi/',   views.saisie_suivi_pfmp, name='saisie_suivi_pfmp'),

    # PFMP — dossiers et fichiers
    path('gestion/pfmp/<int:pfmp_id>/dossier/creer/',           views.pfmp_dossier_create, name='pfmp_dossier_create'),
    path('gestion/pfmp/dossier/<int:pk>/modifier/',              views.pfmp_dossier_update, name='pfmp_dossier_update'),
    path('gestion/pfmp/dossier/<int:pk>/supprimer/',             views.pfmp_dossier_delete, name='pfmp_dossier_delete'),
    path('gestion/pfmp/dossier/<int:dossier_id>/fichier/creer/', views.pfmp_fichier_create, name='pfmp_fichier_create'),
    path('gestion/pfmp/fichier/<int:pk>/modifier/',              views.pfmp_fichier_update, name='pfmp_fichier_update'),
    path('gestion/pfmp/fichier/<int:pk>/supprimer/',             views.pfmp_fichier_delete, name='pfmp_fichier_delete'),

    # ═══════════════════════════════════════
    # ATELIERS
    # ═══════════════════════════════════════
    path('gestion/ateliers/',              views.gestion_ateliers,         name='gestion_ateliers'),
    path('ateliers/creer/',                views.atelier_create,           name='atelier_create'),
    path('ateliers/<int:pk>/',             views.atelier_detail,           name='atelier_detail'),
    path('ateliers/<int:pk>/modifier/',    views.atelier_update,           name='atelier_update'),
    path('ateliers/<int:pk>/supprimer/',   views.atelier_delete,           name='atelier_delete'),
    path('ateliers/<int:pk>/toggle-visibilite/', views.atelier_toggle_visibilite, name='atelier_toggle_visibilite'),

    # Ateliers — dossiers et fichiers
    path('gestion/atelier/<int:atelier_id>/dossier/creer/',          views.atelier_dossier_create, name='atelier_dossier_create'),
    path('gestion/atelier/dossier/<int:pk>/modifier/',                views.atelier_dossier_update, name='atelier_dossier_update'),
    path('gestion/atelier/dossier/<int:pk>/supprimer/',               views.atelier_dossier_delete, name='atelier_dossier_delete'),
    path('gestion/atelier/dossier/<int:pk>/toggle-visibilite/',       views.atelier_dossier_toggle_visibilite, name='atelier_dossier_toggle_visibilite'),
    path('gestion/atelier/dossier/<int:dossier_id>/fichier/creer/',   views.atelier_fichier_create, name='atelier_fichier_create'),
    path('gestion/atelier/fichier/<int:pk>/modifier/',                views.atelier_fichier_update, name='atelier_fichier_update'),
    path('gestion/atelier/fichier/<int:pk>/supprimer/',               views.atelier_fichier_delete, name='atelier_fichier_delete'),
    path('gestion/atelier/fichier/<int:pk>/toggle-visibilite/',       views.atelier_fichier_toggle_visibilite, name='atelier_fichier_toggle_visibilite'),
    path('ateliers/fichier/<int:pk>/telecharger/',                    views.atelier_fichier_download, name='atelier_fichier_download'),

    # ═══════════════════════════════════════
    # MODES OPÉRATOIRES
    # ═══════════════════════════════════════
    path('modes-operatoires/creer/theme/<int:theme_id>/',   views.mo_create,        name='mo_create_theme'),
    path('modes-operatoires/creer/atelier/<int:atelier_id>/', views.mo_create,      name='mo_create_atelier'),
    path('modes-operatoires/<int:pk>/editer/',               views.mo_edit,          name='mo_edit'),
    path('modes-operatoires/<int:pk>/voir/',                 views.mo_view,          name='mo_view'),
    path('modes-operatoires/<int:pk>/sauvegarder/',          views.mo_update,        name='mo_update'),
    path('modes-operatoires/<int:pk>/visibilite/',           views.mo_toggle_visible_eleves, name='mo_toggle_visible_eleves'),
    path('modes-operatoires/<int:pk>/supprimer/',            views.mo_delete,        name='mo_delete'),
    path('lignes/<int:pk>/modifier/',                        views.ligne_update,     name='ligne_update'),
    path('lignes/<int:pk>/regenerer/<str:colonne>/',         views.ligne_regenerer,  name='ligne_regenerer'),
    path('lignes/<int:mo_id>/ajouter/',                      views.ligne_add,        name='ligne_add'),
    path('lignes/<int:pk>/supprimer/',                       views.ligne_delete,     name='ligne_delete'),
    path('modes-operatoires/',                               views.gestion_modes_operatoires, name='gestion_modes_operatoires'),

    # ═══════════════════════════════════════
    # ASSISTANT IA
    # ═══════════════════════════════════════
    path('assistant/',         views.assistant_ia,       name='assistant_ia'),
    path('assistant/query/',   views.assistant_ia_query, name='assistant_ia_query'),
    path('assistant/tts/', views.assistant_tts, name='assistant_tts'),
    path('keepalive/', views.keepalive, name='keepalive'),
    path('health/', views.health, name='health'),
    # Route de test : redirection vers une URL Cloudinary signée pour un FichierAtelier
    path('test-download/<int:pk>/', download_fichier_atelier_signed, name='test_download_fichier_signed'),
]