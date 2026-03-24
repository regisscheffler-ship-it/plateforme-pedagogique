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


# === VUES D'ACCUEIL & AUTH ===
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
