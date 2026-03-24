"""
Export ZIP de fin d'année.
Compatible stockage local + Cloudinary.
Zéro dépendance externe (uniquement stdlib + Django).
"""

import io
import os
import re
import csv
import zipfile
import logging
from datetime import date
from urllib.request import urlopen

from django.db.models import Q

logger = logging.getLogger(__name__)


# ───────────────────────────────────────────────
# UTILITAIRES
# ───────────────────────────────────────────────

def safe(name, max_len=100):
    """Nettoie un nom pour l'utiliser dans un chemin ZIP."""
    if not name:
        return 'sans_nom'
    s = str(name).strip()
    s = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '_', s)
    s = re.sub(r'\s+', '_', s)
    s = re.sub(r'_+', '_', s)
    s = s.strip('_.')
    return s[:max_len] or 'sans_nom'


def uniq(zf, path):
    """Retourne un chemin unique dans le ZIP."""
    names = set(zf.namelist())
    if path not in names:
        return path
    base, ext = os.path.splitext(path)
    n = 2
    while f"{base}_{n}{ext}" in names:
        n += 1
    return f"{base}_{n}{ext}"


def ext_of(ff):
    """Extension d'un FileField (ex: '.pdf')."""
    if ff and ff.name:
        return os.path.splitext(ff.name)[1].lower() or '.bin'
    return '.bin'


def lire(file_field):
    """
    Lit le contenu binaire d'un FileField.
    Essaie dans l'ordre :
      1) storage.open()      — local + Cloudinary
      2) download via URL    — Cloudinary / S3
      3) chemin local direct — local seulement
    """
    if not file_field or not file_field.name:
        return None

    # ① storage.open()
    try:
        file_field.open('rb')
        data = file_field.read()
        file_field.close()
        if data:
            return data
    except Exception:
        pass

    # ② URL (Cloudinary, S3…)
    try:
        url = file_field.url
        if url.startswith('//'):
            url = 'https:' + url
        if url.startswith('http'):
            return urlopen(url, timeout=60).read()
    except Exception:
        pass

    # ③ path local
    try:
        with open(file_field.path, 'rb') as f:
            return f.read()
    except Exception:
        pass

    return None


def ajouter(zf, file_field, chemin, erreurs):
    """Ajoute un fichier au ZIP. Retourne True si succès."""
    data = lire(file_field)
    if data:
        zf.writestr(uniq(zf, chemin), data)
        return True
    erreurs.append(chemin)
    return False


def annee_dates(annee_str):
    """'2024-2025' → (date(2024,9,1), date(2025,8,31))."""
    try:
        parts = annee_str.split('-')
        y1 = int(parts[0])
        y2 = int(parts[1]) if len(parts) > 1 else y1 + 1
        return date(y1, 9, 1), date(y2, 8, 31)
    except Exception:
        y = date.today().year
        return date(y - 1, 9, 1), date(y, 8, 31)


def extract_id(desc, prefix):
    """'fiche_contrat_id:42|…' → 42."""
    if not desc or prefix not in desc:
        return None
    try:
        raw = desc.split(prefix)[1].split('|')[0].split('\n')[0].strip()
        return int(raw)
    except (ValueError, IndexError):
        return None


def make_csv(rows, headers):
    """Génère une chaîne CSV (séparateur ;, BOM UTF-8 pour Excel)."""
    buf = io.StringIO()
    buf.write('\ufeff')  # BOM pour qu'Excel détecte l'UTF-8
    w = csv.writer(buf, delimiter=';', quoting=csv.QUOTE_MINIMAL)
    w.writerow(headers)
    for row in rows:
        w.writerow(row)
    return buf.getvalue()


# ───────────────────────────────────────────────
# EXPORT ARCHIVES (simple)
# ───────────────────────────────────────────────

def generer_zip_archives(annee, categorie=None):
    """
    ZIP des archives organisé par Classe / Catégorie.
    Inclut les CSV de notes (évaluations) et résultats (QCM)
    quand la description contient fiche_contrat_id: ou qcm_id:.

    Retourne (zip_bytes, nb_fichiers, liste_erreurs).
    """
    from core.models import (
        Archive, FicheContrat, FicheEvaluation,
        QCM, SessionQCM,
    )

    qs = Archive.objects.filter(actif=True, annee_scolaire=annee)
    if categorie and categorie != 'all':
        qs = qs.filter(categorie=categorie)

    erreurs = []
    nb = 0
    buf = io.BytesIO()

    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:

        for arc in qs.order_by('categorie', 'titre'):
            cat = safe(arc.get_categorie_display())
            titre = safe(arc.titre)
            classe_nom = ''

            # ── Évaluation liée ? ──
            fc_id = extract_id(arc.description, 'fiche_contrat_id:')
            if fc_id:
                try:
                    fc = FicheContrat.objects.select_related('classe').get(id=fc_id)
                    if fc.classe:
                        classe_nom = safe(fc.classe.nom)
                    evals = (
                        FicheEvaluation.objects
                        .filter(fiche_contrat=fc)
                        .select_related('eleve__user')
                        .order_by('eleve__user__last_name')
                    )
                    if evals.exists():
                        rows = []
                        for ev in evals:
                            nom = ev.eleve.user.get_full_name() if ev.eleve and ev.eleve.user else '?'
                            note = ev.note_sur_20 if ev.note_sur_20 is not None else ''
                            rows.append([nom, note, 'Oui' if ev.validee else 'Non',
                                         ev.compte_rendu or ''])
                        base = f"{classe_nom}/{cat}" if classe_nom else cat
                        zf.writestr(
                            uniq(zf, f"{base}/{titre}_notes.csv"),
                            make_csv(rows, ['Élève', 'Note /20', 'Validée', 'Compte-rendu']),
                        )
                        nb += 1
                except FicheContrat.DoesNotExist:
                    pass

            # ── QCM lié ? ──
            qcm_id = extract_id(arc.description, 'qcm_id:')
            if qcm_id:
                try:
                    qcm_obj = QCM.objects.select_related('classe').get(id=qcm_id)
                    if qcm_obj.classe and not classe_nom:
                        classe_nom = safe(qcm_obj.classe.nom)
                    sessions = (
                        SessionQCM.objects
                        .filter(qcm=qcm_obj, termine=True)
                        .select_related('eleve__user')
                        .order_by('eleve__user__last_name')
                    )
                    if sessions.exists():
                        rows = [[
                            s.eleve.user.get_full_name() if s.eleve and s.eleve.user else '?',
                            s.note_sur_20 or '', s.nb_bonnes_reponses,
                        ] for s in sessions]
                        base = f"{classe_nom}/{cat}" if classe_nom else cat
                        zf.writestr(
                            uniq(zf, f"{base}/{titre}_qcm.csv"),
                            make_csv(rows, ['Élève', 'Note /20', 'Bonnes réponses']),
                        )
                        nb += 1
                except QCM.DoesNotExist:
                    pass

            # ── Fichier attaché ──
            if arc.fichier and arc.fichier.name:
                ext = ext_of(arc.fichier)
                if classe_nom:
                    path = f"{classe_nom}/{cat}/{titre}{ext}"
                else:
                    path = f"{cat}/{titre}{ext}"
                if ajouter(zf, arc.fichier, path, erreurs):
                    nb += 1

        # ── Erreurs éventuelles ──
        if erreurs:
            zf.writestr('_ERREURS.txt',
                         f"Fichiers impossibles à lire ({len(erreurs)}) :\n" +
                         '\n'.join(erreurs))

    buf.seek(0)
    return buf.getvalue(), nb, erreurs


# ───────────────────────────────────────────────
# EXPORT ANNUEL COMPLET
# ───────────────────────────────────────────────

def generer_zip_complet(annee):
    """
    ZIP complet de fin d'année : évaluations, travaux rendus,
    archives, QCM, cours.

    Structure :
        01_Evaluations/<Classe>/<TP>/recap_notes.csv
        01_Evaluations/<Classe>/<TP>/detail_indicateurs.csv
        02_Travaux_Eleves/<Classe>/<Devoir>/consigne.ext
        02_Travaux_Eleves/<Classe>/<Devoir>/<Eleve>.ext
        02_Travaux_Eleves/<Classe>/<Devoir>/recap.csv
        03_Archives/<Categorie>/<titre>.ext
        04_QCM/<Classe>/<QCM>/resultats.csv
        05_Cours/<Classe>/<Theme>/<Dossier>/<fichier>.ext

    Retourne (zip_bytes, nb_fichiers, liste_erreurs).
    """
    from core.models import (
        Archive, Classe, Theme, Dossier, Fichier,
        FicheContrat, FicheEvaluation, EvaluationLigne,
        TravailARendre, RenduEleve,
        QCM, SessionQCM,
    )

    d1, d2 = annee_dates(annee)
    q_annee = Q(classe__annee_scolaire=annee)
    q_dates = Q(date_creation__date__range=(d1, d2))

    erreurs = []
    nb = 0
    buf = io.BytesIO()

    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:

        # ════════════════════════════════════
        # 1. ÉVALUATIONS PAR COMPÉTENCES
        # ════════════════════════════════════
        fiches = (
            FicheContrat.objects
            .filter(actif=True).filter(q_annee | q_dates)
            .select_related('classe', 'referentiel', 'createur')
            .distinct()
        )

        for fc in fiches:
            cl = safe(fc.classe.nom) if fc.classe else 'Sans_classe'
            base = f"01_Evaluations/{cl}/{safe(fc.titre_tp)}"

            evals = (
                FicheEvaluation.objects
                .filter(fiche_contrat=fc)
                .select_related('eleve__user')
                .order_by('eleve__user__last_name')
            )
            if not evals.exists():
                continue

            # A) Récap des notes
            recap_rows = []
            for ev in evals:
                nom = ev.eleve.user.get_full_name() if ev.eleve and ev.eleve.user else '?'
                note = ev.note_sur_20 if ev.note_sur_20 is not None else ''
                recap_rows.append([nom, note, 'Oui' if ev.validee else 'Non',
                                   ev.compte_rendu or ''])
            zf.writestr(
                uniq(zf, f"{base}/recap_notes.csv"),
                make_csv(recap_rows, ['Élève', 'Note /20', 'Validée', 'Compte-rendu']),
            )
            nb += 1

            # B) Détail par indicateur
            detail_rows = []
            for ev in evals:
                nom = ev.eleve.user.get_full_name() if ev.eleve and ev.eleve.user else '?'
                lignes_ev = (
                    EvaluationLigne.objects
                    .filter(fiche_evaluation=ev)
                    .select_related(
                        'ligne_contrat__competence_pro',
                        'ligne_contrat__sous_competence',
                        'ligne_contrat__indicateur',
                    )
                    .order_by('ligne_contrat__ordre')
                )
                for el in lignes_ev:
                    lc = el.ligne_contrat
                    cp = f"{lc.competence_pro.code} - {lc.competence_pro.nom}" if lc.competence_pro else ''
                    sc = lc.sous_competence.nom if lc.sous_competence else ''
                    ind = lc.indicateur.nom if lc.indicateur else ''
                    detail_rows.append([
                        nom, cp, sc, ind,
                        float(lc.poids),
                        el.note,
                        el.get_note_display(),
                    ])
            if detail_rows:
                zf.writestr(
                    uniq(zf, f"{base}/detail_indicateurs.csv"),
                    make_csv(detail_rows, [
                        'Élève', 'Compétence', 'Sous-compétence',
                        'Indicateur', 'Poids (%)', 'Code', 'Note détaillée',
                    ]),
                )
                nb += 1

        # ════════════════════════════════════
        # 2. TRAVAUX RENDUS
        # ════════════════════════════════════
        travaux = (
            TravailARendre.objects
            .filter(actif=True).filter(q_annee | q_dates)
            .select_related('classe')
            .distinct()
        )

        for tr in travaux:
            cl = safe(tr.classe.nom) if tr.classe else 'Sans_classe'
            base = f"02_Travaux_Eleves/{cl}/{safe(tr.titre)}"

            # Consigne
            if tr.fichier_consigne and tr.fichier_consigne.name:
                if ajouter(zf, tr.fichier_consigne,
                           f"{base}/consigne{ext_of(tr.fichier_consigne)}", erreurs):
                    nb += 1

            # Fichiers rendus
            rendus = (
                RenduEleve.objects
                .filter(travail=tr, rendu=True)
                .select_related('eleve__user')
                .order_by('eleve__user__last_name')
            )
            recap_rows = []
            for r in rendus:
                nom = r.eleve.user.get_full_name() if r.eleve and r.eleve.user else '?'
                # Fichier
                if r.fichier_rendu and r.fichier_rendu.name:
                    if ajouter(zf, r.fichier_rendu,
                               f"{base}/{safe(nom)}{ext_of(r.fichier_rendu)}", erreurs):
                        nb += 1
                recap_rows.append([
                    nom,
                    r.date_rendu.strftime('%d/%m/%Y %H:%M') if r.date_rendu else '',
                    'Oui' if r.est_en_retard() else 'Non',
                    str(r.note) if r.note is not None else '',
                    r.appreciation or '',
                    'Oui' if r.corrige else 'Non',
                ])

            if recap_rows:
                zf.writestr(
                    uniq(zf, f"{base}/recap_rendus.csv"),
                    make_csv(recap_rows, [
                        'Élève', 'Date rendu', 'En retard',
                        'Note', 'Appréciation', 'Corrigé',
                    ]),
                )
                nb += 1

        # ════════════════════════════════════
        # 3. ARCHIVES
        # ════════════════════════════════════
        for arc in Archive.objects.filter(actif=True, annee_scolaire=annee):
            if arc.fichier and arc.fichier.name:
                cat = safe(arc.get_categorie_display())
                titre = safe(arc.titre)
                if ajouter(zf, arc.fichier,
                           f"03_Archives/{cat}/{titre}{ext_of(arc.fichier)}", erreurs):
                    nb += 1

        # ════════════════════════════════════
        # 4. QCM
        # ════════════════════════════════════
        qcms = (
            QCM.objects
            .filter(actif=True).filter(q_annee | q_dates)
            .select_related('classe')
            .distinct()
        )
        for qcm in qcms:
            cl = safe(qcm.classe.nom) if qcm.classe else 'Sans_classe'
            base = f"04_QCM/{cl}/{safe(qcm.titre)}"
            sessions = (
                SessionQCM.objects
                .filter(qcm=qcm, termine=True)
                .select_related('eleve__user')
                .order_by('eleve__user__last_name')
            )
            if sessions.exists():
                rows = [[
                    s.eleve.user.get_full_name() if s.eleve and s.eleve.user else '?',
                    s.note_sur_20 or '', s.nb_bonnes_reponses,
                ] for s in sessions]
                zf.writestr(
                    uniq(zf, f"{base}/resultats.csv"),
                    make_csv(rows, ['Élève', 'Note /20', 'Bonnes réponses']),
                )
                nb += 1

        # ════════════════════════════════════
        # 5. COURS (fichiers des thèmes)
        # ════════════════════════════════════
        classes_ids = set(
            Classe.objects
            .filter(Q(annee_scolaire=annee) | Q(actif=True))
            .values_list('id', flat=True)
        )
        # Ajouter les classes vues dans les évaluations
        for fc in fiches:
            if fc.classe_id:
                classes_ids.add(fc.classe_id)

        if classes_ids:
            themes = (
                Theme.objects
                .filter(actif=True, classes__id__in=classes_ids)
                .distinct()
                .prefetch_related('classes')
            )
            for theme in themes:
                classes_str = '_'.join(sorted(safe(c.nom) for c in theme.classes.all()))
                theme_base = f"05_Cours/{classes_str or 'Global'}/{safe(theme.nom)}"

                for dossier in Dossier.objects.filter(theme=theme, actif=True):
                    dossier_path = f"{theme_base}/{safe(dossier.nom)}"
                    fichiers = Fichier.objects.filter(
                        dossier=dossier, actif=True, type_contenu='fichier',
                    )
                    for fic in fichiers:
                        if fic.fichier and fic.fichier.name:
                            if ajouter(zf, fic.fichier,
                                       f"{dossier_path}/{safe(fic.nom)}{ext_of(fic.fichier)}",
                                       erreurs):
                                nb += 1

        # ════════════════════════════════════
        # LISEZ-MOI
        # ════════════════════════════════════
        readme = f"""EXPORT ANNUEL COMPLET — {annee}
{'=' * 45}
Fichiers exportés : {nb}
Erreurs de lecture : {len(erreurs)}

STRUCTURE DES DOSSIERS :
  01_Evaluations/   → Notes par compétence (CSV)
  02_Travaux_Eleves/ → Fichiers rendus par les élèves
  03_Archives/       → Documents archivés
  04_QCM/            → Résultats des QCM (CSV)
  05_Cours/          → Fichiers de cours (PDF…)

Les fichiers CSV s'ouvrent avec Excel / LibreOffice Calc.
Séparateur : point-virgule (;)
"""
        if erreurs:
            readme += f"\n\nFICHIERS NON LISIBLES ({len(erreurs)}) :\n"
            readme += '\n'.join(f"  • {e}" for e in erreurs)

        zf.writestr('_LISEZ_MOI.txt', readme)

    buf.seek(0)
    return buf.getvalue(), nb, erreurs
