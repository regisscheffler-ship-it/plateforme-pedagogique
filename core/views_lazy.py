"""Wrappers paresseux pour différer l'import de `core.views` au premier appel.

Les vues listées dans `VIEW_NAMES` sont exposées ici comme petites fonctions
qui importent `core.views` uniquement lorsqu'elles sont invoquées, réduisant
la charge à l'import du module `core.urls` (initialisation serveur).
"""
from typing import Callable, Any

VIEW_NAMES = [
    'home', 'login_prof_view', 'login_eleve_view', 'logout_view',
    'inscription_eleve', 'choix_eleve', 'completer_profil_eleve',
    'dashboard_professeur', 'dashboard_eleve',
    'gestion_classes', 'classe_list', 'classe_detail', 'classe_update', 'supprimer_classe',
    'gestion_eleves', 'modifier_eleve', 'supprimer_eleve', 'reactiver_eleve',
    'gestion_approbations', 'approuver_eleve', 'refuser_eleve', 'muter_eleve',
    'gestion_sorties', 'marquer_sortie', 'modifier_sortie', 'passer_en_classe_superieure',
    'gestion_themes', 'theme_create', 'theme_detail', 'theme_update', 'theme_edit', 'theme_delete', 'theme_toggle_visibilite',
    'fiche_revision_create', 'fiche_revision_detail', 'fiche_revision_import_csv', 'fiche_revision_delete', 'fiche_revision_update', 'carte_revision_delete',
    'qcm_gestion', 'qcm_create', 'qcm_creer_depuis_dashboard', 'qcm_edit', 'qcm_toggle_actif', 'qcm_delete',
    'question_delete', 'question_edit', 'question_regenerer', 'qcm_passer', 'qcm_resultats', 'qcm_resultats_prof', 'qcm_archiver',
    'dossier_create', 'dossier_detail', 'dossier_update', 'dossier_delete', 'dossier_toggle_visibilite',
    'fichier_upload', 'fichier_update', 'fichier_delete', 'fichier_toggle_visibilite',
    'evaluations_home', 'evaluation_parametres', 'creer_evaluation', 'evaluation_detail',
    'fiche_evaluation_select_eleves', 'fiche_evaluation_saisie', 'deverrouiller_fiche_evaluation', 'creer_fiche_absent',
    'fiche_contrat_supprimer', 'fiche_contrat_archiver', 'generer_fiches_eleves', 'generer_fiches_evaluation',
    'valider_contrat', 'valider_fiches_evaluation', 'eleve_voir_fiche_contrat', 'eleve_voir_fiche_evaluation', 'eleve_fiche_complete',
    'travaux_creer', 'travaux_corriger', 'travaux_par_classe', 'travail_create', 'travail_detail', 'travail_delete',
    'mes_travaux_eleve', 'rendre_travail', 'corriger_rendu', 'marquer_corrige',
    'communication_eleve', 'communication_prof', 'communication_repondre', 'communication_supprimer', 'communications_list', 'communications_export_pdf',
    'mes_notifications', 'marquer_notification_lue', 'marquer_toutes_lues',
    'archives', 'archives_export', 'export_annuel_complet', 'supprimer_archive', 'archive_detail', 'statistiques',
    'api_eleves_par_classe', 'api_competences_par_referentiel', 'contact',
    'gestion_portfolio',
    'portfolio_detail', 'fiche_portfolio_create', 'fiche_portfolio_update',
    'fiche_portfolio_delete', 'fiche_portfolio_valider',
    'mon_portfolio', 'fiche_portfolio_eleve_update', 'fiche_portfolio_pdf_export',
    'gestion_pfmp', 'pfmp_create', 'pfmp_detail', 'pfmp_update', 'pfmp_supprimer', 'saisie_suivi_pfmp',
    'pfmp_dossier_create', 'pfmp_dossier_update', 'pfmp_dossier_delete', 'pfmp_fichier_create', 'pfmp_fichier_update', 'pfmp_fichier_delete',
    'gestion_ateliers', 'atelier_create', 'atelier_detail', 'atelier_update', 'atelier_delete', 'atelier_toggle_visibilite',
    'atelier_dossier_create', 'atelier_dossier_update', 'atelier_dossier_delete', 'atelier_dossier_toggle_visibilite',
    'atelier_fichier_create', 'atelier_fichier_update', 'atelier_fichier_delete', 'atelier_fichier_toggle_visibilite', 'atelier_fichier_download',
    'mo_create', 'mo_edit', 'mo_view', 'mo_update', 'mo_toggle_visible_eleves',
    'ligne_update', 'ligne_regenerer', 'ligne_add', 'ligne_delete', 'gestion_modes_operatoires',
    'assistant_ia', 'assistant_ia_query', 'assistant_tts', 'keepalive', 'health',
]


def _make_lazy(name: str) -> Callable[..., Any]:
    def _wrapper(*args, **kwargs):
        from . import views as _real_views
        try:
            view = getattr(_real_views, name)
        except AttributeError:
            raise AttributeError(f"Attribut '{name}' introuvable dans core.views")
        return view(*args, **kwargs)

    _wrapper.__name__ = name
    return _wrapper


for _name in VIEW_NAMES:
    globals()[_name] = _make_lazy(_name)

__all__ = VIEW_NAMES


def __getattr__(name: str):
    # Fournit dynamiquement un wrapper paresseux pour n'importe quel nom
    # référencé comme `views.<name>` dans `core/urls.py`. Le wrapper est
    # créé sans importer `core.views` ; l'import réel se produit seulement
    # au moment de l'appel de la vue.
    if name in globals():
        return globals()[name]
    wrapper = _make_lazy(name)
    globals()[name] = wrapper
    return wrapper
