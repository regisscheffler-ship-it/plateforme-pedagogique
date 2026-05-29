"""
Migration de données : ajout des connaissances ORGO 2026 aux compétences
du référentiel "Compétences communes PFMP - 2BTP".

Correspondance établie entre les domaines de connaissances du référentiel
Bac Pro ORGO 2026 et les 15 CompétencesProfessionnelles du référentiel 2BTP.
"""

from django.db import migrations

REFERENTIEL_NOM = "Compétences communes PFMP - 2BTP"

# Mapping : code CP 2BTP → liste de (code_connaissance, libellé, ordre)
# Domaines de connaissances ORGO 2026 :
#   K-INF  : Les sources d'information et les supports de communication
#   K-DOC  : Les pièces écrites et graphiques d'un dossier d'exécution
#   K-INT  : Les intervenants et le phasage d'un projet de construction
#   K-ECO  : La transition écologique dans la construction
#   K-PRP  : La prévention des risques professionnels
#   K-EQP  : La gestion d'une équipe sur chantier
#   K-SYS  : Les systèmes constructifs
#   K-MAT  : Les matériaux
#   K-MEL  : Les matériels
#   K-REL  : Le relevé et l'implantation des ouvrages
#   K-QUA  : La démarche qualité sur chantier

CONNAISSANCES_2BTP = {
    # ---- C1 : S'INFORMER ----
    "C1.1": [   # Collecter et classer des informations
        ("C1.1-K1", "Les sources d'information et les supports de communication", 1),
        ("C1.1-K2", "Les pièces écrites et graphiques d'un dossier d'exécution", 2),
        ("C1.1-K3", "Les intervenants et le phasage d'un projet de construction", 3),
        ("C1.1-K4", "La démarche qualité sur chantier", 4),
    ],
    "C1.2": [   # Décoder des documents
        ("C1.2-K1", "Les sources d'information et les supports de communication", 1),
        ("C1.2-K2", "Les pièces écrites et graphiques d'un dossier d'exécution", 2),
        ("C1.2-K3", "Les systèmes constructifs", 3),
        ("C1.2-K4", "Les matériaux", 4),
    ],

    # ---- C2 : TRAITER, DÉCIDER, COMMUNIQUER ----
    "C2.1": [   # Organiser le chantier
        ("C2.1-K1", "Les pièces écrites et graphiques d'un dossier d'exécution", 1),
        ("C2.1-K2", "Les intervenants et le phasage d'un projet de construction", 2),
        ("C2.1-K3", "La prévention des risques professionnels", 3),
        ("C2.1-K4", "Les matériaux", 4),
        ("C2.1-K5", "Les matériels", 5),
        ("C2.1-K6", "La démarche qualité sur chantier", 6),
    ],
    "C2.2": [   # Quantifier les besoins
        ("C2.2-K1", "Les pièces écrites et graphiques d'un dossier d'exécution", 1),
        ("C2.2-K2", "Les systèmes constructifs", 2),
        ("C2.2-K3", "Les matériaux", 3),
        ("C2.2-K4", "Les matériels", 4),
    ],
    "C2.3": [   # Proposer des méthodes d'exécution et produire les documents associés
        ("C2.3-K1", "Les sources d'information et les supports de communication", 1),
        ("C2.3-K2", "Les pièces écrites et graphiques d'un dossier d'exécution", 2),
        ("C2.3-K3", "Les systèmes constructifs", 3),
        ("C2.3-K4", "Les matériaux", 4),
        ("C2.3-K5", "Les matériels", 5),
        ("C2.3-K6", "La démarche qualité sur chantier", 6),
    ],
    "C2.4": [   # Communiquer, rendre compte
        ("C2.4-K1", "Les sources d'information et les supports de communication", 1),
        ("C2.4-K2", "Les intervenants et le phasage d'un projet de construction", 2),
        ("C2.4-K3", "La démarche qualité sur chantier", 3),
    ],
    "C2.5": [   # Animer une petite équipe
        ("C2.5-K1", "La gestion d'une équipe sur chantier", 1),
        ("C2.5-K2", "La prévention des risques professionnels", 2),
        ("C2.5-K3", "Les intervenants et le phasage d'un projet de construction", 3),
    ],

    # ---- C3 : METTRE EN ŒUVRE - RÉALISER ----
    "C3.1": [   # Organiser le poste de travail
        ("C3.1-K1", "La prévention des risques professionnels", 1),
        ("C3.1-K2", "Les matériaux", 2),
        ("C3.1-K3", "Les matériels", 3),
        ("C3.1-K4", "La démarche qualité sur chantier", 4),
    ],
    "C3.2": [   # Mettre en œuvre les moyens de protection
        ("C3.2-K1", "La prévention des risques professionnels", 1),
        ("C3.2-K2", "La transition écologique dans la construction", 2),
        ("C3.2-K3", "Les matériels", 3),
    ],
    "C3.3": [   # Monter et démonter un échafaudage, un étaiement
        ("C3.3-K1", "La prévention des risques professionnels", 1),
        ("C3.3-K2", "Les matériels", 2),
        ("C3.3-K3", "Les systèmes constructifs", 3),
    ],
    "C3.4": [   # Traiter les déchets et protéger l'environnement
        ("C3.4-K1", "La transition écologique dans la construction", 1),
        ("C3.4-K2", "La prévention des risques professionnels", 2),
        ("C3.4-K3", "Les matériaux", 3),
    ],
    "C3.5": [   # Repérer, implanter et tracer des ouvrages
        ("C3.5-K1", "Le relevé et l'implantation des ouvrages", 1),
        ("C3.5-K2", "Les pièces écrites et graphiques d'un dossier d'exécution", 2),
        ("C3.5-K3", "Les matériels", 3),
        ("C3.5-K4", "Les systèmes constructifs", 4),
    ],
    "C3.6": [   # Réaliser, poser, modifier une partie d'ouvrage
        ("C3.6-K1", "Les systèmes constructifs", 1),
        ("C3.6-K2", "Les matériaux", 2),
        ("C3.6-K3", "Les matériels", 3),
        ("C3.6-K4", "La prévention des risques professionnels", 4),
        ("C3.6-K5", "La démarche qualité sur chantier", 5),
        ("C3.6-K6", "Le relevé et l'implantation des ouvrages", 6),
    ],

    # ---- C4 : CONTRÔLER, RÉCEPTIONNER ----
    "C4.1": [   # Réceptionner les matériels et matériaux
        ("C4.1-K1", "Les matériaux", 1),
        ("C4.1-K2", "Les matériels", 2),
        ("C4.1-K3", "Les pièces écrites et graphiques d'un dossier d'exécution", 3),
        ("C4.1-K4", "La démarche qualité sur chantier", 4),
    ],
    "C4.2": [   # Contrôler les ouvrages
        ("C4.2-K1", "La démarche qualité sur chantier", 1),
        ("C4.2-K2", "Les systèmes constructifs", 2),
        ("C4.2-K3", "Les matériaux", 3),
        ("C4.2-K4", "Les pièces écrites et graphiques d'un dossier d'exécution", 4),
    ],
}


def ajouter_connaissances(apps, schema_editor):
    Referentiel = apps.get_model("core", "Referentiel")
    CompetenceProfessionnelle = apps.get_model("core", "CompetenceProfessionnelle")
    Connaissance = apps.get_model("core", "Connaissance")

    try:
        ref = Referentiel.objects.get(nom=REFERENTIEL_NOM)
    except Referentiel.DoesNotExist:
        print(f"  [SKIP] Référentiel '{REFERENTIEL_NOM}' introuvable.")
        return

    total = 0
    for cp_code, connaissances in CONNAISSANCES_2BTP.items():
        # Chercher la CP dans ce référentiel (via blocs → compétences → CP)
        cp_qs = CompetenceProfessionnelle.objects.filter(
            code=cp_code,
            competence__bloc__referentiel=ref
        )
        if not cp_qs.exists():
            print(f"  [WARN] CompétencePro '{cp_code}' introuvable dans {REFERENTIEL_NOM}")
            continue
        cp = cp_qs.first()
        # Supprimer les connaissances existantes pour idempotence
        Connaissance.objects.filter(competence_pro=cp).delete()
        for code, nom, ordre in connaissances:
            Connaissance.objects.create(
                competence_pro=cp,
                code=code,
                nom=nom,
                ordre=ordre
            )
            total += 1

    print(f"  [OK] {total} connaissances créées pour le référentiel '{REFERENTIEL_NOM}'.")


def supprimer_connaissances(apps, schema_editor):
    Referentiel = apps.get_model("core", "Referentiel")
    CompetenceProfessionnelle = apps.get_model("core", "CompetenceProfessionnelle")
    Connaissance = apps.get_model("core", "Connaissance")

    try:
        ref = Referentiel.objects.get(nom=REFERENTIEL_NOM)
    except Referentiel.DoesNotExist:
        return

    codes = list(CONNAISSANCES_2BTP.keys())
    Connaissance.objects.filter(
        competence_pro__code__in=codes,
        competence_pro__competence__bloc__referentiel=ref
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0032_referentiel_2btp_criteres"),
    ]

    operations = [
        migrations.RunPython(
            ajouter_connaissances,
            reverse_code=supprimer_connaissances,
        ),
    ]
