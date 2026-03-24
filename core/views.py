from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
import base64
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
try:
    from xhtml2pdf import pisa
except Exception:
    pisa = None
from django.conf import settings
import os
# ── VUE ÉLÈVE : liste ses messages + formulaire envoi ──
@login_required
def communication_eleve(request):
    """Page principale communication côté élève"""
    profil = request.user.profil
    if profil.type_utilisateur != 'eleve':
        return redirect('core:dashboard_professeur')
    
    # Trouve le prof principal de la classe de l'élève
    classe = profil.classe
    # Trouve le prof de la classe de l'élève
    professeur = None
    if classe:
        # Cherche un prof lié à la classe via les thèmes ou directement
        professeur = ProfilUtilisateur.objects.filter(
            type_utilisateur='professeur'
        ).first()

    if not professeur:
        messages.error(request, 
            'Aucun professeur disponible. Contactez votre établissement.')
        return redirect('core:dashboard_eleve')
    
    messages_liste = MessageEleve.objects.filter(
        eleve=profil
    ).prefetch_related('reponses').order_by('-date_envoi')
    
    if request.method == 'POST':
        texte = request.POST.get('texte', '').strip()
        image_annotee_data = request.POST.get('image_annotee_data', '')
        image_fichier = request.FILES.get('image')
        
        if not texte and not image_fichier and not image_annotee_data:
            messages.error(request, 'Veuillez ajouter un message ou une image.')
            return redirect('core:communication_eleve')
        
        msg = MessageEleve(eleve=profil, professeur=professeur)
        msg.texte = texte
        
        # Image originale uploadée
        if image_fichier:
            msg.image = image_fichier
        
        # Image annotée (canvas base64 → fichier)
        if image_annotee_data and image_annotee_data.startswith('data:image'):
            format, imgstr = image_annotee_data.split(';base64,')
            ext = format.split('/')[-1]
            nom_fichier = f"annotation_{profil.id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
            msg.image_annotee = ContentFile(
                base64.b64decode(imgstr),
                name=nom_fichier
            )
        
        msg.save()
        messages.success(request, 'Message envoyé au professeur !')
        return redirect('core:communication_eleve')
    
    context = {
        'messages_liste': messages_liste,
        'professeur': professeur,
    }
    return render(request, 'core/communication_eleve.html', context)


# ── VUE PROF : boîte de réception ──
@login_required
def communication_prof(request):
    """Page principale communication côté professeur"""
    profil = request.user.profil
    if profil.type_utilisateur != 'professeur':
        return redirect('core:dashboard_professeur')
    
    messages_liste = MessageEleve.objects.filter(
        professeur=profil
    ).prefetch_related('reponses', 'eleve__user').order_by('-date_envoi')
    
    # Ne plus marquer automatiquement comme lus — le professeur choisira
    
    nb_non_lus = MessageEleve.objects.filter(
        professeur=profil, lu=False
    ).count()
    
    context = {
        'messages_liste': messages_liste,
        'nb_non_lus': nb_non_lus,
    }
    return redirect('core:communications_list')


# ── VUE PROF : répondre à un message ──
@login_required
@require_POST
def communication_repondre(request, message_id):
    """Le prof répond à un message élève"""
    profil = request.user.profil
    if profil.type_utilisateur != 'professeur':
        return redirect('core:dashboard_professeur')
    
    msg = get_object_or_404(MessageEleve, id=message_id)
    texte = request.POST.get('texte', '').strip()
    
    if texte:
        ReponseProf.objects.create(
            message=msg,
            professeur=profil,
            texte=texte
        )
        # Quand le professeur répond, on marque le message comme lu
        msg.lu = True
        msg.save()
        messages.success(request, 'Réponse envoyée !')
    
    return redirect('core:communication_prof')


# ── VUE PROF : supprimer un message ──
@login_required
@require_POST
def communication_supprimer(request, message_id):
    """Le prof supprime un message"""
    profil = request.user.profil
    if profil.type_utilisateur != 'professeur':
        return redirect('core:dashboard_professeur')
    
    msg = get_object_or_404(MessageEleve, id=message_id)
    msg.delete()
    messages.success(request, 'Message supprimé.')
    return redirect('core:communication_prof')
# core/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Count, Q
from django.db.models.functions import ExtractYear
from django.db import connection
from django.utils import timezone
from django.http import JsonResponse, HttpResponse, FileResponse
from django.urls import reverse
from django.conf import settings
from django.db import transaction
import zipfile
import os
from django.views.decorators.http import require_http_methods
from datetime import date, datetime, timedelta
from collections import OrderedDict
from itertools import groupby
from django.db.models import Count, Q, Avg, Sum
from django.db.models.functions import ExtractYear, TruncDate
from operator import attrgetter
from .forms import PFMPForm
import json
import traceback
import csv
import io

from .models import (
    ProfilUtilisateur, Niveau, Classe, Theme, Dossier,
    Fichier, TypeRessource, TravailARendre, RenduEleve,
    Notification, Archive, EtablissementOrigine,
    Referentiel, BlocCompetence, Competence,
    CompetenceProfessionnelle, SousCompetence,
    CritereEvaluation, IndicateurPerformance, Connaissance,
    FicheContrat, LigneContrat, FicheEvaluation, EvaluationLigne,
    PFMP, Atelier, DossierPFMP, FichierPFMP,
    DossierAtelier, FichierAtelier,
    FicheRevision, CarteRevision,
    SuiviPFMP, HistoriqueClasse,
    QCM, QuestionQCM, SessionQCM,
    ModeOperatoire, LigneModeOperatoire,
    MessageEleve, ReponseProf,  # ← AJOUTER CETTE LIGNE
)
import io
import fitz
from PIL import Image

try:
    from .forms import FormulaireSortie, ThemeForm
except ImportError:
    FormulaireSortie = None
    ThemeForm = None


# ================================
# FONCTIONS UTILITAIRES
# ✅ UNE SEULE définition — gère prof, staff, superuser
# ================================

def est_professeur(user):
    if user.is_superuser or user.is_staff:
        return True
    try:
        return user.profil.est_prof()
    except Exception:
        return False

def keepalive(request):
    """Ping keep-alive pour éviter la mise en veille de Supabase."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    return JsonResponse({'status': 'ok'})


def health(request):
    """Simple health endpoint returning 200 without DB dependency."""
    return HttpResponse('ok', status=200)

def est_eleve(user):
    return hasattr(user, 'profil') and user.profil.type_utilisateur == 'eleve'


def _render_fiche_contrat_pdf_bytes(fiche_contrat, evaluations):
    """Génère un PDF lisible (bytes) pour une fiche_contrat et sa liste d'évaluations.
    Utilise PyMuPDF (fitz) si disponible. Retourne None en cas d'erreur.
    """
    try:
        import fitz
    except Exception:
        return None

    try:
        doc = fitz.open()
        # A4 page
        page = doc.new_page(width=595, height=842)

        titre = getattr(fiche_contrat, 'titre', getattr(fiche_contrat, 'titre_tp', ''))
        classe_nom = fiche_contrat.classe.nom if getattr(fiche_contrat, 'classe', None) else ''
        createur = fiche_contrat.createur.get_full_name() if getattr(fiche_contrat, 'createur', None) else ''
        date_creation = fiche_contrat.date_creation.isoformat() if getattr(fiche_contrat, 'date_creation', None) else ''

        header = f"{titre}\nClasse: {classe_nom}\nCréateur: {createur}\nDate: {date_creation}\n\n"
        # Header box
        try:
            page.insert_textbox(fitz.Rect(50, 50, 545, 140), header, fontsize=14, fontname="helv", align=0)
        except Exception:
            page.insert_text((50, 50), header, fontsize=14)

        # Body: consigne, problématique, savoirs associés
        body_parts = []
        if getattr(fiche_contrat, 'consigne', None):
            body_parts.append("Consigne:\n" + fiche_contrat.consigne + "\n\n")
        if getattr(fiche_contrat, 'problematique', None):
            body_parts.append("Problématique:\n" + fiche_contrat.problematique + "\n\n")
        if getattr(fiche_contrat, 'savoirs_associes', None):
            body_parts.append("Savoirs associés:\n" + fiche_contrat.savoirs_associes + "\n\n")

        # Liste des évaluations (nom - note)
        body_parts.append("Évaluations:\n")
        for ev in evaluations:
            nom = ev.eleve.user.get_full_name() if getattr(ev, 'eleve', None) and getattr(ev.eleve, 'user', None) else ''
            note = ev.note_sur_20 if getattr(ev, 'note_sur_20', None) is not None else '\u2014'
            body_parts.append(f"- {nom}: {note}\n")

        body = "".join(body_parts)
        try:
            page.insert_textbox(fitz.Rect(50, 150, 545, 800), body, fontsize=11, fontname="helv", align=0)
        except Exception:
            page.insert_text((50, 150), body, fontsize=11)

        try:
            pdf_bytes = doc.write()
        except Exception:
            try:
                pdf_bytes = doc.tobytes()
            except Exception:
                pdf_bytes = None
        doc.close()
        return pdf_bytes
    except Exception:
        try:
            doc.close()
        except Exception:
            pass
        return None


def _render_fiche_evaluation_pdf_bytes(fiche_eval):
    """Génère un PDF (bytes) pour une FicheEvaluation individuelle.
    Contient les informations de la fiche contrat, élève, note et la liste des lignes d'évaluation.
    Retourne None si PyMuPDF absent ou erreur.
    """
    try:
        import fitz
    except Exception:
        return None

    try:
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)

        fc = fiche_eval.fiche_contrat
        titre = getattr(fc, 'titre', getattr(fc, 'titre_tp', ''))
        classe_nom = fc.classe.nom if getattr(fc, 'classe', None) else ''
        eleve_nom = fiche_eval.eleve.user.get_full_name() if getattr(fiche_eval, 'eleve', None) and getattr(fiche_eval.eleve, 'user', None) else ''
        note = fiche_eval.note_sur_20 if getattr(fiche_eval, 'note_sur_20', None) is not None else '\u2014'

        header = f"{titre}\nClasse: {classe_nom}\nÉlève: {eleve_nom}\nNote /20: {note}\nDate validation: {fiche_eval.date_validation.isoformat() if fiche_eval.date_validation else ''}\n\n"
        try:
            page.insert_textbox(fitz.Rect(50, 50, 545, 140), header, fontsize=13, fontname='helv')
        except Exception:
            page.insert_text((50, 50), header, fontsize=13)

        # Lignes d'évaluation
        lignes = fiche_eval.lignes_evaluation.select_related('ligne_contrat', 'ligne_contrat__indicateur').all()
        y = 150
        for ln in lignes:
            texte = f"- {ln.ligne_contrat.indicateur.nom if ln.ligne_contrat and ln.ligne_contrat.indicateur else str(ln.ligne_contrat)} : {ln.get_note_display()}"
            try:
                page.insert_textbox(fitz.Rect(60, y, 540, y+20), texte, fontsize=11, fontname='helv')
            except Exception:
                page.insert_text((60, y), texte, fontsize=11)
            y += 18
            if y > 780:
                page = doc.new_page()
                y = 50

        # Compte-rendu
        if fiche_eval.compte_rendu:
            try:
                page.insert_textbox(fitz.Rect(50, y+10, 545, 800), "Compte-rendu:\n" + fiche_eval.compte_rendu, fontsize=11, fontname='helv')
            except Exception:
                page.insert_text((50, y+10), "Compte-rendu:\n" + fiche_eval.compte_rendu, fontsize=11)

        try:
            pdf_bytes = doc.write()
        except Exception:
            try:
                pdf_bytes = doc.tobytes()
            except Exception:
                pdf_bytes = None
        doc.close()
        return pdf_bytes
    except Exception:
        try:
            doc.close()
        except Exception:
            pass
        return None


@login_required
@user_passes_test(est_professeur)
def fiche_revision_update(request, pk):
    fiche = get_object_or_404(FicheRevision, id=pk)
    if request.method == 'POST':
        titre = request.POST.get('titre', '').strip()
        if titre:
            fiche.titre = titre
            fiche.save()
            messages.success(request, '✅ Fiche de révision modifiée !')
            return redirect('core:fiche_revision_detail', pk=fiche.id)
        else:
            messages.error(request, '❌ Le titre est obligatoire.')
    return render(request, 'core/fiche_revision_update.html', {'fiche': fiche})


# =====================================================
# PAGE D'ACCUEIL & AUTH
# =====================================================

def home(request):
    context = {
        'total_classes': Classe.objects.count(),
        'total_themes': Theme.objects.count(),
        'total_fichiers': Fichier.objects.count(),
    }
    return render(request, 'core/home.html', context)


def login_prof_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            try:
                if user.profil.est_prof():
                    login(request, user)
                    messages.success(request, f'✅ Bienvenue {user.first_name} !')
                    return redirect('core:dashboard_professeur')
                else:
                    messages.error(request, '❌ Cet accès est réservé aux professeurs.')
            except ProfilUtilisateur.DoesNotExist:
                if user.is_staff or user.is_superuser:
                    login(request, user)
                    messages.success(request, f'✅ Bienvenue {user.username} !')
                    return redirect('core:dashboard_professeur')
                else:
                    messages.error(request, '❌ Profil non configuré.')
        else:
            messages.error(request, '❌ Identifiant ou mot de passe incorrect.')
    return render(request, 'core/login_prof.html')


def choix_eleve(request):
    return render(request, 'core/choix_eleve.html')


def login_eleve_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        try:
            user_check = User.objects.get(username=username)
            if not user_check.is_active:
                try:
                    if user_check.profil.est_eleve() and not user_check.profil.compte_approuve:
                        messages.warning(request, "⏳ Votre compte est en attente d'approbation.")
                        return render(request, 'core/login_eleve.html')
                except ProfilUtilisateur.DoesNotExist:
                    pass
        except User.DoesNotExist:
            pass
        user = authenticate(request, username=username, password=password)
        if user is not None:
            try:
                if user.profil.est_eleve():
                    login(request, user)
                    messages.success(request, f"✅ Bienvenue {user.first_name} !")
                    return redirect('core:dashboard_eleve')
                else:
                    messages.error(request, "❌ Cet accès est réservé aux élèves.")
            except ProfilUtilisateur.DoesNotExist:
                messages.error(request, "❌ Profil non configuré.")
        else:
            messages.error(request, "❌ Identifiant ou mot de passe incorrect.")
    return render(request, 'core/login_eleve.html')


def inscription_eleve(request):
    classes = Classe.objects.all()
    if request.method == 'POST':
        nom = request.POST.get('nom')
        prenom = request.POST.get('prenom')
        date_naissance = request.POST.get('date_naissance')
        classe_id = request.POST.get('classe')
        username = request.POST.get('username')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        if password1 != password2:
            messages.error(request, '❌ Les mots de passe ne correspondent pas.')
            return render(request, 'core/inscription_eleve.html', {'classes': classes})
        if User.objects.filter(username=username).exists():
            messages.error(request, '❌ Cet identifiant est déjà utilisé.')
            return render(request, 'core/inscription_eleve.html', {'classes': classes})
        if not classe_id:
            messages.error(request, '❌ Veuillez sélectionner une classe.')
            return render(request, 'core/inscription_eleve.html', {'classes': classes})
        try:
            user = User.objects.create_user(
                username=username, password=password1,
                first_name=prenom, last_name=nom, is_active=False
            )
            classe = Classe.objects.get(id=classe_id)
            ProfilUtilisateur.objects.create(
                user=user, type_utilisateur='eleve', classe=classe,
                date_naissance=date_naissance if date_naissance else None,
                compte_approuve=False, annee_entree=str(datetime.now().year)
            )
            messages.success(request, "✅ Demande d'inscription envoyée !")
            return redirect('core:home')
        except Exception as e:
            messages.error(request, f'❌ Erreur : {str(e)}')
    return render(request, 'core/inscription_eleve.html', {'classes': classes})


def logout_view(request):
    logout(request)
    messages.success(request, '✅ Vous êtes déconnecté.')
    return redirect('core:home')


# =====================================================
# DASHBOARDS
# =====================================================

@login_required(login_url='core:login_prof')
@user_passes_test(est_professeur)
def dashboard_professeur(request):
    nb_messages_non_lus = MessageEleve.objects.filter(
        professeur=request.user.profil, lu=False
    ).count()
    context = {
        'nb_classes':            Classe.objects.count(),
        'nb_eleves':             ProfilUtilisateur.objects.filter(type_utilisateur='eleve', compte_approuve=True, est_sorti=False).count(),
        'nb_garcons':            ProfilUtilisateur.objects.filter(type_utilisateur='eleve', compte_approuve=True, est_sorti=False, sexe='M').count(),
        'nb_filles':             ProfilUtilisateur.objects.filter(type_utilisateur='eleve', compte_approuve=True, est_sorti=False, sexe='F').count(),
        'nb_themes':             Theme.objects.count(),
        'nb_travaux_a_corriger': RenduEleve.objects.filter(corrige=False, rendu=True).count(),
        'nb_travaux_publies':    TravailARendre.objects.filter(actif=True).count(),
        'nb_notifications':      Notification.objects.filter(destinataire=request.user, lue=False).count(),
        'nb_pfmp':               PFMP.objects.filter(actif=True).count(),
        'nb_ateliers':           Atelier.objects.filter(actif=True).count(),
        'nb_evaluations':        FicheContrat.objects.filter(createur=request.user, actif=True).count(),
        'nb_archives':           Archive.objects.filter(actif=True).count(),
        'nb_sorties':            ProfilUtilisateur.objects.filter(type_utilisateur='eleve', est_sorti=True).count(),
        'nb_qcm':                QCM.objects.filter(actif=True).count(),
        'nb_modes_operatoires':  ModeOperatoire.objects.filter(actif=True).count(),
        'classes_list':          Classe.objects.all().order_by('nom'),
        'themes_list':           Theme.objects.all().order_by('nom'),
        'nb_messages_non_lus':   nb_messages_non_lus,
    }

    # Rebuild fiches_par_theme as a proper dict of lists
    # On passe par le dossier pour retrouver l'ID du thème
    fiches_map = {}
    for f in FicheRevision.objects.select_related('dossier__theme').annotate(nb_cartes=Count('cartes')).order_by('titre'):
        if f.dossier and f.dossier.theme_id:  # On vérifie que la fiche a bien un dossier
            tid = str(f.dossier.theme_id)
            if tid not in fiches_map:
                fiches_map[tid] = []
            fiches_map[tid].append({'id': f.id, 'titre': f.titre, 'nb': f.nb_cartes})
            
    context['fiches_par_theme_json'] = json.dumps(fiches_map)
    
    total_sexe = context['nb_garcons'] + context['nb_filles']
    context['pc_garcons'] = f"{context['nb_garcons']*100/total_sexe:.0f}" if total_sexe else '0'
    context['pc_filles'] = f"{context['nb_filles']*100/total_sexe:.0f}" if total_sexe else '0'
    
    return render(request, 'core/dashboard_professeur.html', context)


@login_required
@user_passes_test(est_professeur)
def communications_list(request):
    """Liste les messages d'élèves destinés au professeur connecté."""
    communications = MessageEleve.objects.filter(
        professeur=request.user.profil
    ).select_related(
        'eleve__user', 'eleve__classe'
    ).order_by('-date_envoi')
    context = {'communications': communications}
    return render(request, 'core/communications_list.html', context)


@login_required(login_url='core:login_eleve')
def dashboard_eleve(request):
    try:
        profil = request.user.profil
        if profil.est_prof():
            return redirect('core:dashboard_professeur')
        classe = profil.classe
        if not classe:
            messages.warning(request, "⚠️ Vous n'êtes pas encore assigné à une classe.")
            return render(request, 'core/dashboard_eleve.html', {'classe': None})
        # limiter les travaux affichés : garder les travaux actifs non rendus,
        # et ne pas afficher les travaux dont la date_limite est passée depuis plus de 3 jours
        seuil_retention = date.today() - timedelta(days=3)
        travaux_qs = TravailARendre.objects.filter(classe=classe, actif=True).exclude(rendus__eleve=profil)
        from django.db.models import Q
        travaux_qs = travaux_qs.filter(Q(date_limite__isnull=True) | Q(date_limite__gte=seuil_retention)).order_by('date_limite')

        context = {
            'ma_classe': classe,
            'themes': Theme.objects.filter(classes=classe, visible_eleves=True).order_by('ordre', 'nom'),
            'travaux_a_faire': travaux_qs,
            'mes_rendus': RenduEleve.objects.filter(eleve=profil).select_related('travail').order_by('-date_rendu'),
            'notifications': Notification.objects.filter(destinataire=request.user, lue=False).order_by('-date_creation'),
            'ateliers': Atelier.objects.filter(classe=classe, actif=True, visible_eleves=True).order_by('ordre', 'titre'),
            'mes_pfmp': PFMP.objects.filter(classe=classe, actif=True).order_by('date_debut'),
            # n'afficher que les 6 dernières évaluations validées
            'mes_evaluations': FicheEvaluation.objects.filter(eleve=profil, validee=True).select_related('fiche_contrat').order_by('-date_validation')[:6],
            'today': date.today(),
        }
        # QCM actifs annotés avec la session de l'élève
        sessions_map = {s.qcm_id: s for s in SessionQCM.objects.filter(qcm__classe=classe, eleve=profil, termine=True)}
        qcms_actifs = [
            {'qcm': q, 'session': sessions_map.get(q.id)}
            for q in QCM.objects.filter(classe=classe, actif=True).annotate(nb_q=Count('questions')).order_by('date_limite')
        ]
        context['qcms_actifs'] = qcms_actifs
        context['total_a_faire'] = context['travaux_a_faire'].count() + len(qcms_actifs)
        # Modes opératoires visibles aux élèves (via atelier de la classe)
        context['modes_operatoires_eleve'] = ModeOperatoire.objects.filter(
            actif=True, visible_eleves=True,
            atelier__classe=classe
        ).select_related('atelier').order_by('-date_creation')
        return render(request, 'core/dashboard_eleve.html', context)
    except ProfilUtilisateur.DoesNotExist:
        messages.error(request, "⛔ Profil non configuré.")
        return redirect('core:home')


@login_required
@user_passes_test(est_professeur)
def communications_export_pdf(request):
    """Génère un PDF réunissant les communications des élèves pour le professeur connecté."""
    try:
        import fitz
    except Exception:
        return HttpResponse('PyMuPDF non disponible', status=501)

    communications = MessageEleve.objects.filter(
        professeur=request.user.profil
    ).select_related('eleve__user', 'eleve__classe').order_by('-date_envoi')

    doc = fitz.open()
    for c in communications:
        # prefer annotated image, otherwise original image
        img_url = None
        if getattr(c, 'image_annotee', None):
            try:
                img_url = c.image_annotee.url
            except Exception:
                img_url = None
        if not img_url and getattr(c, 'image', None):
            try:
                img_url = c.image.url
            except Exception:
                img_url = None

        if img_url:
            try:
                import requests
                resp = requests.get(img_url, timeout=10)
                resp.raise_for_status()
                img_bytes = resp.content
                pil = Image.open(io.BytesIO(img_bytes)).convert('RGB')
                w, h = pil.size
                # create page sized to image (limit to A4 width)
                max_w = 595; max_h = 842  # points for A4 at 72dpi
                scale = min(max_w / w, max_h / h, 1)
                pw = int(w * scale); ph = int(h * scale)
                page = doc.new_page(width=pw, height=ph)
                img_buf = io.BytesIO()
                pil.save(img_buf, format='PNG')
                img_buf.seek(0)
                page.insert_image(fitz.Rect(0, 0, pw, ph), stream=img_buf.read())
            except Exception:
                # fallback: page with text only
                page = doc.new_page()
                classe_nom = c.eleve.classe.nom if getattr(c.eleve, 'classe', None) else ''
                page.insert_text((72, 72), f"{c.eleve.user.get_full_name()} - {classe_nom}\n(Erreur image)")
        else:
            page = doc.new_page()
            classe_nom = c.eleve.classe.nom if getattr(c.eleve, 'classe', None) else ''
            page.insert_text((72, 72), f"{c.eleve.user.get_full_name()} - {classe_nom}\n(Aucune image)")

        # add a second small page with the texte
        if c.texte:
            tpage = doc.new_page()
            classe_nom = c.eleve.classe.nom if getattr(c.eleve, 'classe', None) else ''
            text = f"{c.eleve.user.get_full_name()} — {classe_nom}\n\n{c.texte}"
            tpage.insert_textbox(fitz.Rect(72,72,523,770), text, fontsize=12)

    pdf_bytes = doc.write()
    doc.close()
    return HttpResponse(pdf_bytes, content_type='application/pdf')

# (file continues...)

VILLES_ORIGINE = [
    'Roubaix', 'Tourcoing', 'Hem', 'Croix', 'Halluin', 'Wasquehal',
    "Villeneuve d'Ascq", 'Marcq en Baroeul', 'Lille', 'Mons en Baroeul',
    'Lys lez Lannoy', 'Leers', 'Saint André', 'Marquette-lez-Lille',
    'Linselles', 'Wattrelos', 'Mouvaux', 'Roncq', 'Lambersart', 'Ronchin', 'Cysoing',
]


@login_required
@user_passes_test(est_professeur)
def completer_profil_eleve(request, profil_id):
    profil = get_object_or_404(ProfilUtilisateur, id=profil_id)
    if request.method == 'POST':
        profil.date_naissance = request.POST.get('date_naissance') or None
        profil.annee_entree = request.POST.get('annee_entree', '')
        if request.POST.get('etablissement_origine'):
            profil.etablissement_origine = EtablissementOrigine.objects.get(id=request.POST.get('etablissement_origine'))
        profil.etablissement_origine_autre = request.POST.get('etablissement_origine_autre', '')
        profil.classe_origine = request.POST.get('classe_origine', '')
        if request.POST.get('classe'):
            profil.classe = Classe.objects.get(id=request.POST.get('classe'))
        profil.diplome_obtenu = request.POST.get('diplome_obtenu', '')
        profil.save()
        messages.success(request, '✅ Profil complété !')
        return redirect('core:gestion_eleves')

    # Ajout automatique du lycée si absent
    if not EtablissementOrigine.objects.filter(nom="Lycée Louis Loucheur").exists():
        EtablissementOrigine.objects.create(nom="Lycée Louis Loucheur", ville="Roubaix", actif=True)

    return render(request, 'core/completer_profil_eleve.html', {
        'profil': profil,
        'etablissements': EtablissementOrigine.objects.all().order_by('nom'),
        'classes': Classe.objects.all().order_by('nom'),
        'villes': VILLES_ORIGINE,
    })
