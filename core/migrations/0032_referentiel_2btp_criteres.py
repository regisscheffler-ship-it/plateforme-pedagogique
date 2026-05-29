"""
Migration de données : correction du référentiel 2BTP
Chaque CompétenceProfessionnelle doit avoir PLUSIEURS CritèresEvaluation
(un par ligne de la grille, évalués 0-3), chacun avec un IndicateurPerformance.
"""

from django.db import migrations


DATA = [
    {
        'bloc_code': 'C1', 'bloc_nom': "S'INFORMER",
        'competences_pro': [
            {
                'code': 'C1.1', 'nom': "Collecter et classer des informations",
                'criteres': [
                    "Rechercher les informations nécessaires à la résolution d'un problème posé",
                    "Classer les informations retenues",
                ],
            },
            {
                'code': 'C1.2', 'nom': "Décoder des documents",
                'criteres': [
                    "Localiser le lieu de l'intervention et identifier le contexte de l'intervention",
                    "Identifier un ouvrage ou un élément d'ouvrage sur les pièces graphiques et écrites",
                    "Identifier les principales caractéristiques d'un ouvrage",
                ],
            },
        ],
    },
    {
        'bloc_code': 'C2', 'bloc_nom': "TRAITER, DÉCIDER, COMMUNIQUER",
        'competences_pro': [
            {
                'code': 'C2.1', 'nom': "Organiser le chantier",
                'criteres': [
                    "Inventorier les tâches ou les opérations",
                    "Affecter les tâches aux différents membres de l'équipe",
                    "Simuler différents scénarios",
                ],
            },
            {
                'code': 'C2.2', 'nom': "Quantifier les besoins",
                'criteres': [
                    "Identifier et comparer les caractéristiques des matériels, des matériaux et des outillages",
                    "Quantifier les matériaux et matériels",
                ],
            },
            {
                'code': 'C2.3', 'nom': "Proposer des méthodes d'exécution et produire les documents associés",
                'criteres': [
                    "Analyser et choisir un mode opératoire",
                    "Établir des croquis, des schémas et des tracés",
                    "Prendre en compte les interfaces pluri-métiers",
                    "Produire des documents graphiques",
                ],
            },
            {
                'code': 'C2.4', 'nom': "Communiquer, rendre compte",
                'criteres': [
                    "Établir un compte rendu oral, écrit ou graphique seul ou en collaboration",
                    "Travailler en équipe et adopter les postures d'écoute, de discussion, de prise en compte d'avis, de participation",
                ],
            },
            {
                'code': 'C2.5', 'nom': "Animer une petite équipe",
                'criteres': [
                    "Indiquer les tâches et consignes aux membres de l'équipe",
                    "Exposer une situation",
                    "Suivre et contrôler l'avancée des activités",
                ],
            },
        ],
    },
    {
        'bloc_code': 'C3', 'bloc_nom': "METTRE EN ŒUVRE - RÉALISER",
        'competences_pro': [
            {
                'code': 'C3.1', 'nom': "Organiser le poste de travail",
                'criteres': [
                    "Organiser l'environnement des postes de travail",
                    "Vérifier la disponibilité des matériels et outillages et leur fonctionnement",
                ],
            },
            {
                'code': 'C3.2', 'nom': "Mettre en œuvre les moyens de protection",
                'criteres': [
                    "Repérer les risques liés à l'activité",
                    "S'assurer de l'utilisation réglementaire des moyens de protection individuels et collectifs",
                ],
            },
            {
                'code': 'C3.3', 'nom': "Monter et démonter un échafaudage, un étaiement",
                'criteres': [
                    "Mettre en place et stabiliser un échafaudage",
                    "Utiliser rationnellement les planchers de travail",
                ],
            },
            {
                'code': 'C3.4', 'nom': "Traiter les déchets et protéger l'environnement",
                'criteres': [
                    "Trier les déchets selon leur catégorie",
                ],
            },
            {
                'code': 'C3.5', 'nom': "Repérer, implanter et tracer des ouvrages",
                'criteres': [
                    "Réaliser une implantation planimétrique et altimétrique",
                    "Tracer des lignes et niveaux de référence",
                ],
            },
            {
                'code': 'C3.6', 'nom': "Réaliser, poser, modifier une partie d'ouvrage",
                'criteres': [
                    "Mettre en œuvre un mode opératoire, un processus d'exécution",
                    "Intervenir en co activité",
                    "Prendre en compte et respecter les interventions des autres corps d'état en aval et amont",
                ],
            },
        ],
    },
    {
        'bloc_code': 'C4', 'bloc_nom': "CONTRÔLER, RÉCEPTIONNER",
        'competences_pro': [
            {
                'code': 'C4.1', 'nom': "Réceptionner les matériels et matériaux",
                'criteres': [
                    "Contrôler les quantités et la conformité des commandes réceptionnées",
                ],
            },
            {
                'code': 'C4.2', 'nom': "Contrôler les ouvrages",
                'criteres': [
                    "Contrôler la conformité de l'ouvrage",
                    "Respecter une procédure de contrôle établie",
                ],
            },
        ],
    },
]

REFERENTIEL_NOM = "Compétences communes PFMP - 2BTP"
TOTAL_CRITERES = sum(len(cp['criteres']) for b in DATA for cp in b['competences_pro'])
POIDS = round(100.0 / TOTAL_CRITERES, 2)


def rebuild_referentiel(apps, schema_editor):
    Referentiel = apps.get_model('core', 'Referentiel')
    BlocCompetence = apps.get_model('core', 'BlocCompetence')
    Competence = apps.get_model('core', 'Competence')
    CompetenceProfessionnelle = apps.get_model('core', 'CompetenceProfessionnelle')
    SousCompetence = apps.get_model('core', 'SousCompetence')
    CritereEvaluation = apps.get_model('core', 'CritereEvaluation')
    IndicateurPerformance = apps.get_model('core', 'IndicateurPerformance')

    # Supprimer l'ancienne version (créée par 0031) pour repartir proprement
    Referentiel.objects.filter(nom=REFERENTIEL_NOM).delete()

    ref = Referentiel.objects.create(
        nom=REFERENTIEL_NOM,
        description="Grille d'évaluation des compétences communes PFMP - Secondes Bac Pro BTP",
        actif=True,
    )

    for ordre_bloc, bloc_data in enumerate(DATA, start=1):
        bloc = BlocCompetence.objects.create(
            referentiel=ref,
            code=bloc_data['bloc_code'],
            nom=bloc_data['bloc_nom'],
            ordre=ordre_bloc,
        )
        comp = Competence.objects.create(
            bloc=bloc,
            code=bloc_data['bloc_code'],
            nom=bloc_data['bloc_nom'],
            ordre=1,
        )
        for ordre_cp, cp_data in enumerate(bloc_data['competences_pro'], start=1):
            cp = CompetenceProfessionnelle.objects.create(
                competence=comp,
                code=cp_data['code'],
                nom=cp_data['nom'],
                ordre=ordre_cp,
            )
            # Une SousCompétence pivot par CompétencePro
            sc = SousCompetence.objects.create(
                competence_pro=cp,
                code=cp_data['code'],
                nom=cp_data['nom'],
                ordre=1,
            )
            # UN CritèreEvaluation par ligne de la grille (plusieurs par CompétencePro)
            for ordre_crit, crit_nom in enumerate(cp_data['criteres'], start=1):
                crit_code = f"{cp_data['code']}.{ordre_crit}"
                crit = CritereEvaluation.objects.create(
                    sous_competence=sc,
                    code=crit_code,
                    nom=crit_nom,
                    ordre=ordre_crit,
                )
                # Un IndicateurPerformance pivot par critère (support de la note 0-3)
                IndicateurPerformance.objects.create(
                    critere=crit,
                    nom=crit_nom,
                    poids=POIDS,
                    ordre=1,
                )


def remove_referentiel(apps, schema_editor):
    Referentiel = apps.get_model('core', 'Referentiel')
    Referentiel.objects.filter(nom=REFERENTIEL_NOM).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0031_referentiel_2btp'),
    ]

    operations = [
        migrations.RunPython(rebuild_referentiel, remove_referentiel),
    ]
