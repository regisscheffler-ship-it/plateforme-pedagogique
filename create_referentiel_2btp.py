"""
Création du référentiel "Compétences communes PFMP - 2BTP"
Source : grille d'évaluation des compétences communes PFMP (photo transmise)

Lancer depuis la racine du projet :
    .venv\\Scripts\\python.exe create_referentiel_2btp.py
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'plateforme.settings')
django.setup()

from django.db import transaction
from core.models import (
    Referentiel, BlocCompetence, Competence,
    CompetenceProfessionnelle, SousCompetence,
    CritereEvaluation, IndicateurPerformance,
)

REFERENTIEL_NOM = "Compétences communes - 2BTP"

# ─────────────────────────────────────────────────────────────
# Données extraites de la grille (photo)
# Structure : bloc → compétence pro (gras) → indicateurs (lignes scorables 0-3)
# ─────────────────────────────────────────────────────────────
DATA = [
    {
        'bloc_code': 'C1',
        'bloc_nom': "S'INFORMER",
        'competences_pro': [
            {
                'code': 'C1.1',
                'nom': "Collecter et classer des informations",
                'indicateurs': [
                    "Rechercher les informations nécessaires à la résolution d'un problème posé",
                    "Classer les informations retenues",
                ],
            },
            {
                'code': 'C1.2',
                'nom': "Décoder des documents",
                'indicateurs': [
                    "Localiser le lieu de l'intervention et identifier le contexte de l'intervention",
                    "Identifier un ouvrage ou un élément d'ouvrage sur les pièces graphiques et écrites",
                    "Identifier les principales caractéristiques d'un ouvrage",
                ],
            },
        ],
    },
    {
        'bloc_code': 'C2',
        'bloc_nom': "TRAITER, DÉCIDER, COMMUNIQUER",
        'competences_pro': [
            {
                'code': 'C2.1',
                'nom': "Organiser le chantier",
                'indicateurs': [
                    "Inventorier les tâches ou les opérations",
                    "Affecter les tâches aux différents membres de l'équipe",
                    "Simuler différents scénarios",
                ],
            },
            {
                'code': 'C2.2',
                'nom': "Quantifier les besoins",
                'indicateurs': [
                    "Identifier et comparer les caractéristiques des matériels, des matériaux et des outillages",
                    "Quantifier les matériaux et matériels",
                ],
            },
            {
                'code': 'C2.3',
                'nom': "Proposer des méthodes d'exécution et produire les documents associés",
                'indicateurs': [
                    "Analyser et choisir un mode opératoire",
                    "Établir des croquis, des schémas et des tracés",
                    "Prendre en compte les interfaces pluri-métiers",
                    "Produire des documents graphiques",
                ],
            },
            {
                'code': 'C2.4',
                'nom': "Communiquer, rendre compte",
                'indicateurs': [
                    "Établir un compte rendu oral, écrit ou graphique seul ou en collaboration",
                    "Travailler en équipe et adopter les postures d'écoute, de discussion, de prise en compte d'avis, de participation",
                ],
            },
            {
                'code': 'C2.5',
                'nom': "Animer une petite équipe",
                'indicateurs': [
                    "Indiquer les tâches et consignes aux membres de l'équipe",
                    "Exposer une situation",
                    "Suivre et contrôler l'avancée des activités",
                ],
            },
        ],
    },
    {
        'bloc_code': 'C3',
        'bloc_nom': "METTRE EN ŒUVRE - RÉALISER",
        'competences_pro': [
            {
                'code': 'C3.1',
                'nom': "Organiser le poste de travail",
                'indicateurs': [
                    "Organiser l'environnement des postes de travail",
                    "Vérifier la disponibilité des matériels et outillages et leur fonctionnement",
                ],
            },
            {
                'code': 'C3.2',
                'nom': "Mettre en œuvre les moyens de protection",
                'indicateurs': [
                    "Repérer les risques liés à l'activité",
                    "S'assurer de l'utilisation réglementaire des moyens de protection individuels et collectifs",
                ],
            },
            {
                'code': 'C3.3',
                'nom': "Monter et démonter un échafaudage, un étaiement",
                'indicateurs': [
                    "Mettre en place et stabiliser un échafaudage",
                    "Utiliser rationnellement les planchers de travail",
                ],
            },
            {
                'code': 'C3.4',
                'nom': "Traiter les déchets et protéger l'environnement",
                'indicateurs': [
                    "Trier les déchets selon leur catégorie",
                ],
            },
            {
                'code': 'C3.5',
                'nom': "Repérer, implanter et tracer des ouvrages",
                'indicateurs': [
                    "Réaliser une implantation planimétrique et altimétrique",
                    "Tracer des lignes et niveaux de référence",
                ],
            },
            {
                'code': 'C3.6',
                'nom': "Réaliser, poser, modifier une partie d'ouvrage",
                'indicateurs': [
                    "Mettre en œuvre un mode opératoire, un processus d'exécution",
                    "Intervenir en co activité",
                    "Prendre en compte et respecter les interventions des autres corps d'état en aval et amont",
                ],
            },
        ],
    },
    {
        'bloc_code': 'C4',
        'bloc_nom': "CONTRÔLER, RÉCEPTIONNER",
        'competences_pro': [
            {
                'code': 'C4.1',
                'nom': "Réceptionner les matériels et matériaux",
                'indicateurs': [
                    "Contrôler les quantités et la conformité des commandes réceptionnées",
                ],
            },
            {
                'code': 'C4.2',
                'nom': "Contrôler les ouvrages",
                'indicateurs': [
                    "Contrôler la conformité de l'ouvrage",
                    "Respecter une procédure de contrôle établie",
                ],
            },
        ],
    },
]


@transaction.atomic
def create():
    # Compter total indicateurs pour poids équilibrés
    total_indicateurs = sum(
        len(cp['indicateurs'])
        for bloc in DATA
        for cp in bloc['competences_pro']
    )
    poids = round(100.0 / total_indicateurs, 2)
    print(f"→ {total_indicateurs} indicateurs, poids unitaire : {poids}%")

    # Référentiel
    ref, created = Referentiel.objects.get_or_create(
        nom=REFERENTIEL_NOM,
        defaults={'description': "Grille d'évaluation des compétences communes PFMP - Secondes Bac Pro BTP", 'actif': True},
    )
    action = "créé" if created else "déjà existant (mis à jour)"
    print(f"\n✅ Référentiel « {ref.nom} » {action}")

    if not created:
        # Supprimer l'existant pour repartir proprement
        ref.blocs.all().delete()
        print("   ↪ Blocs existants supprimés pour recréation propre")

    ordre_bloc = 0
    for bloc_data in DATA:
        ordre_bloc += 1
        bloc, _ = BlocCompetence.objects.get_or_create(
            referentiel=ref,
            code=bloc_data['bloc_code'],
            defaults={'nom': bloc_data['bloc_nom'], 'ordre': ordre_bloc},
        )
        print(f"\n  📦 Bloc {bloc.code} – {bloc.nom}")

        # Une Compétence par bloc (niveau intermédiaire)
        comp, _ = Competence.objects.get_or_create(
            bloc=bloc,
            code=bloc_data['bloc_code'],
            defaults={'nom': bloc_data['bloc_nom'], 'ordre': 1},
        )

        ordre_cp = 0
        for cp_data in bloc_data['competences_pro']:
            ordre_cp += 1
            cp, _ = CompetenceProfessionnelle.objects.get_or_create(
                competence=comp,
                code=cp_data['code'],
                defaults={'nom': cp_data['nom'], 'ordre': ordre_cp},
            )
            print(f"     🔹 {cp.code} {cp.nom}")

            # SousCompétence pivot (même nom que la compétence pro)
            sc, _ = SousCompetence.objects.get_or_create(
                competence_pro=cp,
                code=cp_data['code'],
                defaults={'nom': cp_data['nom'], 'ordre': 1},
            )

            # CritèreEvaluation pivot
            crit, _ = CritereEvaluation.objects.get_or_create(
                sous_competence=sc,
                code=cp_data['code'],
                defaults={'nom': cp_data['nom'], 'ordre': 1},
            )

            ordre_ind = 0
            for ind_nom in cp_data['indicateurs']:
                ordre_ind += 1
                ind, ind_created = IndicateurPerformance.objects.get_or_create(
                    critere=crit,
                    nom=ind_nom,
                    defaults={'poids': poids, 'ordre': ordre_ind},
                )
                status = "✚" if ind_created else "="
                print(f"          {status} {ind_nom[:80]}")

    print(f"\n{'─'*60}")
    print(f"✅ Import terminé — référentiel « {REFERENTIEL_NOM} » prêt.")
    print(f"   {total_indicateurs} indicateurs importés, poids unitaire {poids}% chacun.")


if __name__ == '__main__':
    create()
