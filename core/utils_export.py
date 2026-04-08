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
            .defer('atelier')
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

            # C) Atelier lié ?
            try:
                if getattr(fc, 'atelier_id', None):
                    nb += _ajouter_atelier_au_zip(zf, fc.atelier, base, erreurs)
            except Exception as e:
                logger.warning("Atelier lié à FC %s : %s", fc.pk, e)

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
  01_Evaluations/   → Notes par compétence (CSV) + ateliers liés
  02_Travaux_Eleves/ → Fichiers rendus par les élèves
  03_Archives/       → Documents archivés
  04_QCM/            → Résultats des QCM (CSV)
  05_Cours/          → Fichiers de cours (PDF…)

Quand un TP est lié à un atelier, celui-ci est exporté dans
un sous-dossier Atelier_<nom>/ avec un récap PDF et un fichier
liens_integres.txt contenant les URLs intégrées.

Les fichiers CSV s'ouvrent avec Excel / LibreOffice Calc.
Séparateur : point-virgule (;)
"""
        if erreurs:
            readme += f"\n\nFICHIERS NON LISIBLES ({len(erreurs)}) :\n"
            readme += '\n'.join(f"  • {e}" for e in erreurs)

        zf.writestr('_LISEZ_MOI.txt', readme)

    buf.seek(0)
    return buf.getvalue(), nb, erreurs


# ───────────────────────────────────────────────
# GÉNÉRATION PDF (WeasyPrint) — fiche complète
# ───────────────────────────────────────────────

def _render_fiche_complete_pdf(fiche_eval):
    """
    Génère un PDF A4 (bytes) de la fiche complète d'un élève
    (fiche contrat page 1 + fiche évaluation page 2).
    Essaie WeasyPrint en premier, puis xhtml2pdf en fallback.
    Retourne None en cas d'erreur.
    """
    _weasyprint_available = False
    try:
        from weasyprint import HTML as _WeasyHTML
        _weasyprint_available = True
    except ImportError:
        logger.warning("WeasyPrint non disponible — tentative xhtml2pdf")

    from django.template.loader import render_to_string
    from itertools import groupby as _groupby

    html_string = None
    try:
        fc = fiche_eval.fiche_contrat
        eleve = fiche_eval.eleve

        # Calcul note si absente
        if fiche_eval.note_sur_20 is None:
            try:
                fiche_eval.calculer_note_sur_20()
            except Exception:
                pass

        # ── Page 1 : données contrat ──
        lignes_contrat = fc.lignes.select_related(
            'competence_pro', 'sous_competence', 'critere', 'indicateur'
        ).order_by('ordre')

        cps_vus = set()
        competences_vises = []
        for ligne in lignes_contrat:
            if ligne.competence_pro and ligne.competence_pro.id not in cps_vus:
                cps_vus.add(ligne.competence_pro.id)
                competences_vises.append(ligne.competence_pro)
        competences_vises.sort(key=lambda x: x.code)

        savoirs_bruts = fc.savoirs_associes or ""
        savoirs_dedupliques = list(dict.fromkeys(
            l.strip() for l in savoirs_bruts.splitlines() if l.strip()
        ))

        # ── Page 2 : données évaluation ──
        from core.models import EvaluationLigne
        nb_lignes_total = fc.lignes.count()
        poids_auto = round(100 / nb_lignes_total, 2) if nb_lignes_total > 0 else 10.0

        def get_cp(l):
            return l.ligne_contrat.competence_pro

        def get_sc(l):
            return l.ligne_contrat.sous_competence

        lignes_eval = EvaluationLigne.objects.filter(
            fiche_evaluation=fiche_eval
        ).select_related(
            'ligne_contrat__competence_pro',
            'ligne_contrat__sous_competence',
            'ligne_contrat__critere',
            'ligne_contrat__indicateur'
        ).order_by(
            'ligne_contrat__competence_pro__code',
            'ligne_contrat__sous_competence__ordre',
            'ligne_contrat__ordre'
        )

        for le in lignes_eval:
            if not le.ligne_contrat.poids or le.ligne_contrat.poids == 0:
                le.ligne_contrat.poids = poids_auto

        groupes_competences = []
        for cp, lignes_cp in _groupby(lignes_eval, key=get_cp):
            lignes_cp_list = list(lignes_cp)
            sous_competences = []
            for sc, lignes_sc in _groupby(lignes_cp_list, key=get_sc):
                sous_competences.append({
                    'sous_competence': sc,
                    'lignes': list(lignes_sc)
                })
            groupes_competences.append({
                'competence_pro': cp,
                'lignes': lignes_cp_list,
                'sous_competences': sous_competences,
            })

        html_string = render_to_string('core/fiche_complete_pdf.html', {
            'fiche_contrat': fc,
            'fiche_eval': fiche_eval,
            'eleve': eleve,
            'competences_vises': competences_vises,
            'savoirs_dedupliques': savoirs_dedupliques,
            'groupes_competences': groupes_competences,
            'poids_auto': poids_auto,
        })

        if _weasyprint_available:
            try:
                return _WeasyHTML(string=html_string).write_pdf()
            except Exception as e:
                logger.warning("WeasyPrint échoué (%s) — fallback xhtml2pdf", e)

        # Fallback xhtml2pdf (pisa)
        from xhtml2pdf import pisa as _pisa
        buf_pisa = io.BytesIO()
        status = _pisa.CreatePDF(io.BytesIO(html_string.encode('utf-8')), dest=buf_pisa)
        if not status.err:
            return buf_pisa.getvalue()
        logger.error("xhtml2pdf a aussi échoué pour fiche complète")
        return None

    except Exception as e2:
        logger.error("Erreur génération PDF fiche complète : %s", e2)
        return None


# ───────────────────────────────────────────────
# ATELIERS : extraction URLs + PDF récap + liens.txt
# ───────────────────────────────────────────────

_RE_SRC = re.compile(r'(?:src|href)\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE)


def _extraire_urls_iframe(code_iframe):
    """Extrait toutes les URLs (src=, href=) d'un code HTML iframe/embed."""
    if not code_iframe:
        return []
    urls = _RE_SRC.findall(code_iframe)
    # Normaliser
    result = []
    for u in urls:
        u = u.strip()
        if u.startswith('//'):
            u = 'https:' + u
        if u.startswith('http'):
            result.append(u)
    return result


def _collecter_urls_atelier(atelier):
    """
    Collecte toutes les URLs liées à un atelier :
    lien principal, iframes principal, fichiers de dossiers.
    Retourne une liste de (source, url).
    """
    urls = []
    # Lien principal
    if atelier.lien_externe:
        urls.append(('Lien principal', atelier.lien_externe))
    # Iframe principal
    for u in _extraire_urls_iframe(atelier.code_iframe):
        urls.append(('Iframe principal', u))
    # Fichiers dans les dossiers
    from core.models import DossierAtelier, FichierAtelier
    for dossier in DossierAtelier.objects.filter(atelier=atelier, actif=True):
        for fic in FichierAtelier.objects.filter(dossier=dossier, actif=True):
            if fic.lien_externe:
                urls.append((f'Dossier "{dossier.nom}" / {fic.nom}', fic.lien_externe))
            for u in _extraire_urls_iframe(fic.code_iframe):
                urls.append((f'Dossier "{dossier.nom}" / {fic.nom} (iframe)', u))
    return urls


def _generer_liens_txt(atelier):
    """Génère le contenu texte d'un fichier liens_integres.txt pour un atelier."""
    urls = _collecter_urls_atelier(atelier)
    if not urls:
        return None
    lines = [f"LIENS INTÉGRÉS — Atelier : {atelier.titre}", f"Classe : {atelier.classe.nom}", "=" * 50, ""]
    for source, url in urls:
        lines.append(f"[{source}]")
        lines.append(f"  {url}")
        lines.append("")
    return '\n'.join(lines)


def _render_atelier_recap_pdf(atelier):
    """
    Génère un PDF A4 (bytes) récapitulatif d'un atelier.
    Essaie WeasyPrint en premier, puis xhtml2pdf en fallback.
    Retourne None en cas d'erreur.
    """
    _weasyprint_available = False
    try:
        from weasyprint import HTML as _WeasyHTML
        _weasyprint_available = True
    except ImportError:
        logger.warning("WeasyPrint non disponible pour récap atelier — tentative xhtml2pdf")

    from django.template.loader import render_to_string
    from core.models import DossierAtelier, FichierAtelier, ModeOperatoire

    html_string = None
    try:
        # Dossiers + fichiers
        dossiers = DossierAtelier.objects.filter(atelier=atelier, actif=True).order_by('ordre', 'nom')
        dossiers_data = []
        for d in dossiers:
            fichiers = list(FichierAtelier.objects.filter(dossier=d, actif=True).order_by('ordre', 'nom'))
            d.fichiers_list = fichiers
            dossiers_data.append(d)

        # URLs extraites
        all_urls = []
        for u in _extraire_urls_iframe(atelier.code_iframe):
            all_urls.append(u)
        for d in dossiers:
            for fic in FichierAtelier.objects.filter(dossier=d, actif=True):
                for u in _extraire_urls_iframe(fic.code_iframe):
                    all_urls.append(u)

        # Modes opératoires
        modes = ModeOperatoire.objects.filter(atelier=atelier, actif=True)
        for mo in modes:
            mo.lignes_list = list(mo.lignes.order_by('ordre'))

        html_string = render_to_string('core/atelier_recap_pdf.html', {
            'atelier': atelier,
            'dossiers': dossiers_data,
            'urls': all_urls,
            'modes_operatoires': modes,
        })

        if _weasyprint_available:
            try:
                return _WeasyHTML(string=html_string).write_pdf()
            except Exception as e:
                logger.warning("WeasyPrint échoué récap atelier (%s) — fallback xhtml2pdf", e)

        # Fallback xhtml2pdf
        from xhtml2pdf import pisa as _pisa
        buf_pisa = io.BytesIO()
        status = _pisa.CreatePDF(io.BytesIO(html_string.encode('utf-8')), dest=buf_pisa)
        if not status.err:
            return buf_pisa.getvalue()
        logger.error("xhtml2pdf a aussi échoué pour récap atelier %s", atelier.pk)
        return None

    except Exception as e:
        logger.error("Erreur PDF récap atelier %s : %s", atelier.pk, e)
        return None


def _ajouter_atelier_au_zip(zf, atelier, base_path, erreurs):
    """
    Ajoute au ZIP le récap PDF + liens.txt + fichiers téléchargeables
    d'un atelier sous base_path/Atelier_<titre>/.
    Retourne le nombre de fichiers ajoutés.
    """
    from core.models import DossierAtelier, FichierAtelier

    nb = 0
    atelier_dir = f"{base_path}/Atelier_{safe(atelier.titre)}"

    # 1) PDF récapitulatif
    pdf = _render_atelier_recap_pdf(atelier)
    if pdf:
        zf.writestr(uniq(zf, f"{atelier_dir}/recap_atelier.pdf"), pdf)
        nb += 1

    # 2) Liens intégrés (texte)
    liens = _generer_liens_txt(atelier)
    if liens:
        zf.writestr(uniq(zf, f"{atelier_dir}/liens_integres.txt"), liens)
        nb += 1

    # 3) Fichiers téléchargeables dans les dossiers
    for dossier in DossierAtelier.objects.filter(atelier=atelier, actif=True):
        for fic in FichierAtelier.objects.filter(dossier=dossier, actif=True, type_contenu='fichier'):
            if fic.fichier and fic.fichier.name:
                path = f"{atelier_dir}/{safe(dossier.nom)}/{safe(fic.nom)}{ext_of(fic.fichier)}"
                if ajouter(zf, fic.fichier, path, erreurs):
                    nb += 1

    # 4) Fichier principal de l'atelier
    if atelier.type_contenu == 'fichier' and atelier.fichier and atelier.fichier.name:
        path = f"{atelier_dir}/{safe(atelier.titre)}{ext_of(atelier.fichier)}"
        if ajouter(zf, atelier.fichier, path, erreurs):
            nb += 1

    return nb


# ───────────────────────────────────────────────
# EXPORT ZIP AVANCÉ avec tri : par classe / élève / catégorie
# ───────────────────────────────────────────────

def generer_zip_avance(annee, tri='par_classe', classes_ids=None, eleves_ids=None, categories=None):
    """
    Génère un ZIP structuré selon le tri choisi.

    tri : 'par_classe' | 'par_eleve' | 'par_categorie'

    Structure par_classe :
        <Classe>/Evaluations/<TP>/<Eleve>.pdf
        <Classe>/<Catégorie>/<fichier>

    Structure par_eleve :
        <Eleve> (<Classe>)/Evaluations/<TP>.pdf
        _Documents_generaux/<Catégorie>/<fichier>

    Structure par_categorie :
        Evaluations/<Classe>/<TP>/<Eleve>.pdf
        <Catégorie>/<fichier>

    Retourne (zip_bytes, nb_fichiers, liste_erreurs).
    """
    from core.models import (
        Archive, Classe, FicheContrat, FicheEvaluation,
        ProfilUtilisateur, Atelier,
    )

    d1, d2 = annee_dates(annee)
    q_annee = Q(classe__annee_scolaire=annee)
    q_dates = Q(date_creation__date__range=(d1, d2))

    erreurs = []
    nb = 0
    buf = io.BytesIO()

    # ── Filtrer les évaluations ──
    fiches_qs = (
        FicheContrat.objects
        .filter(q_annee | q_dates)  # actif=True retiré : les fiches archivées ont actif=False
        .select_related('classe', 'referentiel', 'createur')
        .defer('atelier')
        .distinct()
    )
    if classes_ids:
        fiches_qs = fiches_qs.filter(classe_id__in=classes_ids)

    # ── Filtrer les archives manuelles ──
    archives_qs = Archive.objects.filter(actif=True, annee_scolaire=annee)
    if categories:
        archives_qs = archives_qs.filter(categorie__in=categories)

    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:

        # ════════════════════════════════════════
        # A) ÉVALUATIONS → PDF fiche complète par élève
        # ════════════════════════════════════════
        for fc in fiches_qs:
            cl_nom = safe(fc.classe.nom) if fc.classe else 'Sans_classe'
            tp_nom = safe(fc.titre_tp)

            evals_qs = (
                FicheEvaluation.objects
                .filter(fiche_contrat=fc)
                .select_related('eleve__user', 'eleve__classe')
                .order_by('eleve__user__last_name')
            )
            if eleves_ids:
                evals_qs = evals_qs.filter(eleve_id__in=eleves_ids)

            for fiche_eval in evals_qs:
                eleve = fiche_eval.eleve
                if not eleve or not eleve.user:
                    continue

                nom_eleve = safe(f"{eleve.user.last_name}_{eleve.user.first_name}")

                # Générer le PDF de la fiche complète
                pdf_data = _render_fiche_complete_pdf(fiche_eval)
                if not pdf_data:
                    erreurs.append(f"PDF échoué : {nom_eleve} / {tp_nom}")
                    continue

                # Selon le tri, déterminer le chemin dans le ZIP
                if tri == 'par_classe':
                    path = f"{cl_nom}/Evaluations/{tp_nom}/{nom_eleve}.pdf"
                elif tri == 'par_eleve':
                    path = f"{nom_eleve} ({cl_nom})/Evaluations/{tp_nom}.pdf"
                elif tri == 'par_categorie':
                    path = f"Evaluations/{cl_nom}/{tp_nom}/{nom_eleve}.pdf"
                else:
                    path = f"{cl_nom}/Evaluations/{tp_nom}/{nom_eleve}.pdf"

                zf.writestr(uniq(zf, path), pdf_data)
                nb += 1

            # ── Atelier lié à cette fiche contrat ? ──
            try:
                if getattr(fc, 'atelier_id', None):
                    atelier = fc.atelier
                    if tri == 'par_classe':
                        atelier_base = f"{cl_nom}/Evaluations/{tp_nom}"
                    elif tri == 'par_categorie':
                        atelier_base = f"Evaluations/{cl_nom}/{tp_nom}"
                    else:
                        atelier_base = f"_Ateliers/{cl_nom}/{tp_nom}"
                    nb += _ajouter_atelier_au_zip(zf, atelier, atelier_base, erreurs)
            except Exception as e:
                logger.warning("Atelier lié à FC %s : %s", fc.pk, e)

        # ════════════════════════════════════════
        # B) ARCHIVES MANUELLES (examens, administratif, ressources, autre)
        # ════════════════════════════════════════
        for arc in archives_qs.order_by('categorie', 'titre'):
            if not arc.fichier or not arc.fichier.name:
                continue

            cat_label = safe(arc.get_categorie_display())
            titre = safe(arc.titre)
            ext = ext_of(arc.fichier)

            # Déterminer la classe si possible via fiche_contrat_id
            arc_classe = ''
            fc_id = extract_id(arc.description, 'fiche_contrat_id:')
            if fc_id:
                try:
                    fc_obj = FicheContrat.objects.select_related('classe').get(id=fc_id)
                    if fc_obj.classe:
                        arc_classe = safe(fc_obj.classe.nom)
                except FicheContrat.DoesNotExist:
                    pass

            if tri == 'par_classe':
                base = f"{arc_classe or '_General'}/{cat_label}"
            elif tri == 'par_eleve':
                base = f"_Documents_generaux/{cat_label}"
            elif tri == 'par_categorie':
                if arc_classe:
                    base = f"{cat_label}/{arc_classe}"
                else:
                    base = cat_label
            else:
                base = cat_label

            path = f"{base}/{titre}{ext}"
            if ajouter(zf, arc.fichier, path, erreurs):
                nb += 1

        # ════════════════════════════════════════
        # C) QCM — résultats par élève (CSV)
        # ════════════════════════════════════════
        from core.models import QCM, SessionQCM
        qcms_qs = (
            QCM.objects
            .filter(q_annee | q_dates)  # actif=True retiré : cohérence avec FicheContrat
            .select_related('classe')
            .distinct()
        )
        if classes_ids:
            qcms_qs = qcms_qs.filter(classe_id__in=classes_ids)

        for qcm in qcms_qs:
            cl_nom = safe(qcm.classe.nom) if qcm.classe else 'Sans_classe'
            qcm_nom = safe(qcm.titre)

            sessions = (
                SessionQCM.objects
                .filter(qcm=qcm, termine=True)
                .select_related('eleve__user')
                .order_by('eleve__user__last_name')
            )
            if eleves_ids:
                sessions = sessions.filter(eleve_id__in=eleves_ids)
            if not sessions.exists():
                continue

            rows = []
            for s in sessions:
                nom = s.eleve.user.get_full_name() if s.eleve and s.eleve.user else '?'
                rows.append([
                    nom,
                    str(s.note_sur_20) if s.note_sur_20 is not None else '',
                    str(s.nb_bonnes_reponses) if hasattr(s, 'nb_bonnes_reponses') else '',
                    s.date_debut.strftime('%d/%m/%Y %H:%M') if hasattr(s, 'date_debut') and s.date_debut else '',
                ])

            if tri == 'par_classe':
                path = f"{cl_nom}/QCM/{qcm_nom}_resultats.csv"
            elif tri == 'par_eleve':
                path = f"_QCM/{cl_nom}/{qcm_nom}_resultats.csv"
            else:  # par_categorie
                path = f"QCM/{cl_nom}/{qcm_nom}_resultats.csv"

            zf.writestr(
                uniq(zf, path),
                make_csv(rows, ['Élève', 'Note /20', 'Bonnes réponses', 'Date']),
            )
            nb += 1

        # ════════════════════════════════════════
        # LISEZ-MOI
        # ════════════════════════════════════════
        tri_labels = {
            'par_classe': 'Par classe',
            'par_eleve': 'Par élève',
            'par_categorie': 'Par catégorie',
        }
        readme = f"""EXPORT ARCHIVES AVANCÉ — {annee}
{'=' * 45}
Tri : {tri_labels.get(tri, tri)}
Fichiers exportés : {nb}
Erreurs : {len(erreurs)}

Les fiches d'évaluation complètes sont au format PDF (2 pages A4).
Les résultats de QCM sont au format CSV (tableur).
Les documents manuels (examens, administratif, ressources) sont
inclus dans leur format d'origine.
Quand un TP est lié à un atelier, un sous-dossier Atelier_<nom>/
contient un récap PDF et un fichier liens_integres.txt.
"""
        if erreurs:
            readme += f"\n\nERREURS ({len(erreurs)}) :\n"
            readme += '\n'.join(f"  • {e}" for e in erreurs)
        zf.writestr('_LISEZ_MOI.txt', readme)

    buf.seek(0)
    return buf.getvalue(), nb, erreurs
