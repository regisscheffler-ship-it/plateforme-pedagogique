from django.views.decorators.http import require_POST


from django.contrib.auth.decorators import login_required


import base64


from django.core.files.base import ContentFile


from django.template.loader import render_to_string


from django.conf import settings


import os


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


from django.db import transaction


import zipfile


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
import logging


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
    MessageEleve, ReponseProf,
    Portfolio, FichePortfolio, PhotoPortfolio,
)


import fitz


from PIL import Image


from django.http import JsonResponse, HttpResponse


from django.views.decorators.csrf import csrf_exempt


from .services import assistant_recherche, synthetiser_voix


from datetime import date, timedelta, datetime


try:
    from xhtml2pdf import pisa
except Exception:
    pisa = None


# Utilitaire global pour convertir HTML -> PDF bytes (Playwright -> WeasyPrint -> pisa)
def html_to_pdf_bytes(html, request=None):
    """Retourne (pdf_bytes, '.pdf') ou (html_bytes, '.html') en fallback.
    Essaie Playwright, puis WeasyPrint, puis xhtml2pdf.
    """
    # 1) Playwright (headless Chromium) - render HTML string directly
    try:
        from playwright.sync_api import sync_playwright
        base_url = request.build_absolute_uri('/') if request is not None else 'about:blank'
        with sync_playwright() as p:
            # set timeouts and no-sandbox for restricted containers
            browser = p.chromium.launch(timeout=15000, args=['--no-sandbox'])
            try:
                page = browser.new_page()
                page.set_content(html, wait_until='networkidle', base_url=base_url, timeout=15000)
                pdf_bytes = page.pdf(format='A4', timeout=30000)
                return pdf_bytes, '.pdf'
            finally:
                try:
                    browser.close()
                except Exception:
                    pass
    except Exception:
        pass

    # 2) WeasyPrint
    try:
        from weasyprint import HTML
        try:
            base_url = request.build_absolute_uri('/') if request is not None else None
            html_obj = HTML(string=html, base_url=base_url)
            pdf = html_obj.write_pdf()
            return pdf, '.pdf'
        except Exception:
            pass
    except Exception:
        pass

    # 3) xhtml2pdf (pisa)
    if 'pisa' in globals() and pisa is not None:
        try:
            out = io.BytesIO()
            from django.contrib.staticfiles import finders

            def link_callback(uri, rel):
                if uri.startswith('http://') or uri.startswith('https://'):
                    return uri
                if settings.STATIC_URL and uri.startswith(settings.STATIC_URL):
                    path = uri.replace(settings.STATIC_URL, '')
                    found = finders.find(path)
                    if found:
                        return found
                if settings.MEDIA_URL and uri.startswith(settings.MEDIA_URL):
                    path = uri.replace(settings.MEDIA_URL, '')
                    return os.path.join(settings.MEDIA_ROOT, path)
                found = finders.find(uri)
                if found:
                    return found
                return uri

            pisa_status = pisa.CreatePDF(io.BytesIO(html.encode('utf-8')), dest=out, encoding='utf-8', link_callback=link_callback)
            if not pisa_status.err:
                return out.getvalue(), '.pdf'
        except Exception:
            pass

    # Fallback : return HTML bytes
    return html.encode('utf-8'), '.html'


try:
    from .forms import FormulaireSortie, ThemeForm
except ImportError:
    FormulaireSortie = None
    ThemeForm = None


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


def communication_supprimer(request, message_id):
    """Le prof supprime un message"""
    profil = request.user.profil
    if profil.type_utilisateur != 'professeur':
        return redirect('core:dashboard_professeur')
    
    msg = get_object_or_404(MessageEleve, id=message_id)
    msg.delete()
    messages.success(request, 'Message supprimé.')
    return redirect('core:communication_prof')


try:
    from .forms import FormulaireSortie, ThemeForm
except ImportError:
    FormulaireSortie = None
    ThemeForm = None


def est_professeur(user):
    if user.is_superuser or user.is_staff:
        return True
    try:
        return user.profil.est_prof()
    except Exception:
        return False


def keepalive(request):
    """Ping keep-alive minimal — ne dépend pas de la base pour éviter les blocages.
    Anciennement la vue exécutait une requête SQL; si la base est indisponible
    cela peut bloquer ou enchaîner des erreurs côté hébergeur. Retourne simplement
    un statut OK pour vérifier que l'app répond.
    """
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


def gestion_classes(request):
    if request.method == 'POST':
        nom = request.POST.get('nom')
        description = request.POST.get('description', '')
        niveau_id = request.POST.get('niveau')
        if nom:
            niveau = Niveau.objects.get(id=niveau_id) if niveau_id else None
            if not niveau:
                niveau, _ = Niveau.objects.get_or_create(nom='BAC_PRO', defaults={'description': 'Baccalauréat Professionnel'})
            Classe.objects.create(nom=nom, niveau=niveau, description=description)
            messages.success(request, f'✅ Classe "{nom}" créée !')
            return redirect('core:gestion_classes')
    classes = Classe.objects.annotate(
        nb_eleves=Count('eleves', filter=Q(eleves__type_utilisateur='eleve', eleves__compte_approuve=True, eleves__est_sorti=False))
    ).order_by('nom')
    return render(request, 'core/gestion_classes.html', {'classes': classes, 'niveaux': Niveau.objects.all()})


def supprimer_classe(request, pk):
    classe = get_object_or_404(Classe, id=pk)
    if request.method == 'POST':
        nom = classe.nom
        classe.delete()
        messages.success(request, f'✅ Classe "{nom}" supprimée !')
    return redirect('core:gestion_classes')


def classe_update(request, pk):
    classe = get_object_or_404(Classe, id=pk)
    if request.method == 'POST':
        classe.nom = request.POST.get('nom')
        classe.description = request.POST.get('description', '')
        if request.POST.get('niveau'):
            classe.niveau = Niveau.objects.get(id=request.POST.get('niveau'))
        classe.save()
        messages.success(request, '✅ Classe modifiée !')
        return redirect('core:gestion_classes')
    return render(request, 'core/classe_update.html', {'classe': classe, 'niveaux': Niveau.objects.all()})


def classe_list(request):
    return render(request, 'core/classe_list.html', {'classes': Classe.objects.all().order_by('nom')})


def classe_detail(request, pk):
    classe = get_object_or_404(Classe, pk=pk)
    return render(request, 'core/classe_detail.html', {
        'classe': classe,
        'themes': Theme.objects.filter(classes=classe),
        'eleves': ProfilUtilisateur.objects.filter(classe=classe, type_utilisateur='eleve', compte_approuve=True, est_sorti=False)
    })


def gestion_eleves(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        if User.objects.filter(username=username).exists():
            messages.error(request, f"❌ L'utilisateur {username} existe déjà !")
        else:
            user = User.objects.create_user(
                username=username,
                password=request.POST.get('password'),
                first_name=request.POST.get('firstname'),
                last_name=request.POST.get('lastname'),
                email=request.POST.get('email', '')
            )
            classe = Classe.objects.get(id=request.POST.get('classe')) if request.POST.get('classe') else None
            ProfilUtilisateur.objects.create(user=user, type_utilisateur='eleve', classe=classe, compte_approuve=True, sexe=request.POST.get('sexe') or None)
            messages.success(request, "✅ Élève créé !")
            return redirect('core:gestion_eleves')
    eleves = ProfilUtilisateur.objects.filter(type_utilisateur='eleve', compte_approuve=True, est_sorti=False)\
        .select_related('user', 'classe').order_by('classe__nom', 'user__last_name')
    nb_eleves_sortis = ProfilUtilisateur.objects.filter(type_utilisateur='eleve', est_sorti=True).count()
    nb_garcons = eleves.filter(sexe='M').count()
    nb_filles  = eleves.filter(sexe='F').count()
    total = nb_garcons + nb_filles
    pc_filles = f"{nb_filles*100/total:.0f}" if total else '0'
    pc_garcons = f"{nb_garcons*100/total:.0f}" if total else '0'

    # Statistiques parcours ORGO / AFB
    total_orgo = ProfilUtilisateur.objects.filter(type_utilisateur='eleve', parcours='ORGO', est_sorti=False).count()
    total_afb  = ProfilUtilisateur.objects.filter(type_utilisateur='eleve', parcours='AFB', est_sorti=False).count()
    total_parcours = total_orgo + total_afb
    pc_orgo = f"{total_orgo*100/total_parcours:.0f}" if total_parcours else '0'
    pc_afb  = f"{total_afb*100/total_parcours:.0f}" if total_parcours else '0'

    # Par classe breakdown (nom -> {'orgo':n,'afb':m})
    parcours_by_class = {}
    for c in Classe.objects.all():
        o = ProfilUtilisateur.objects.filter(classe=c, parcours='ORGO', type_utilisateur='eleve', est_sorti=False).count()
        a = ProfilUtilisateur.objects.filter(classe=c, parcours='AFB', type_utilisateur='eleve', est_sorti=False).count()
        if o or a:
            parcours_by_class[c.nom] = {'orgo': o, 'afb': a}

    # Statistiques spécifiques Seconde Pro (niveau Bac Pro)
    bacpro_active_qs = ProfilUtilisateur.objects.filter(
        type_utilisateur='eleve', classe__niveau__nom='BAC_PRO', compte_approuve=True, est_sorti=False
    )
    bacpro_sortis_qs = ProfilUtilisateur.objects.filter(
        type_utilisateur='eleve', classe__niveau__nom='BAC_PRO', est_sorti=True
    )
    inscrits_bacpro = bacpro_active_qs.count()
    abandons_bacpro = bacpro_sortis_qs.filter(raison_sortie='decrocheur').count()
    reorientation_interne_bacpro = bacpro_sortis_qs.filter(raison_sortie='reorientation_interne').count()
    reorientation_externe_bacpro = bacpro_sortis_qs.filter(raison_sortie='reorientation_externe').count()
    passage_afb_bacpro = bacpro_active_qs.filter(parcours='AFB').count()
    passage_orgo_bacpro = bacpro_active_qs.filter(parcours='ORGO').count()

    # Détail par classe pour la Seconde Pro
    bacpro_by_class = {}
    for c in Classe.objects.filter(niveau__nom='BAC_PRO').order_by('nom'):
        inscrit = ProfilUtilisateur.objects.filter(classe=c, type_utilisateur='eleve', compte_approuve=True, est_sorti=False).count()
        aband = ProfilUtilisateur.objects.filter(classe=c, type_utilisateur='eleve', est_sorti=True, raison_sortie='decrocheur').count()
        reint = ProfilUtilisateur.objects.filter(classe=c, type_utilisateur='eleve', est_sorti=True, raison_sortie='reorientation_interne').count()
        reext = ProfilUtilisateur.objects.filter(classe=c, type_utilisateur='eleve', est_sorti=True, raison_sortie='reorientation_externe').count()
        afb = ProfilUtilisateur.objects.filter(classe=c, parcours='AFB', type_utilisateur='eleve', est_sorti=False).count()
        orgo = ProfilUtilisateur.objects.filter(classe=c, parcours='ORGO', type_utilisateur='eleve', est_sorti=False).count()
        bacpro_by_class[c.nom] = {'inscrits': inscrit, 'abandons': aband, 'reint': reint, 'reext': reext, 'afb': afb, 'orgo': orgo}

    return render(request, 'core/gestion_eleves.html', {
        'eleves': eleves,
        'classes': Classe.objects.all().order_by('nom'),
        'nb_eleves_sortis': nb_eleves_sortis,
        'nb_garcons': nb_garcons,
        'nb_filles': nb_filles,
        'pc_filles': pc_filles,
        'pc_garcons': pc_garcons,
        'total_orgo': total_orgo,
        'total_afb': total_afb,
        'pc_orgo': pc_orgo,
        'pc_afb': pc_afb,
        'parcours_by_class': parcours_by_class,
        'inscrits_bacpro': inscrits_bacpro,
        'abandons_bacpro': abandons_bacpro,
        'reorientation_interne_bacpro': reorientation_interne_bacpro,
        'reorientation_externe_bacpro': reorientation_externe_bacpro,
        'passage_afb_bacpro': passage_afb_bacpro,
        'passage_orgo_bacpro': passage_orgo_bacpro,
        'bacpro_by_class': bacpro_by_class,
    })


def muter_eleve(request, pk):
    profil = get_object_or_404(ProfilUtilisateur, id=pk)
    anciennes_classes = profil.classe.nom if profil.classe else ''
    if request.method == 'POST':
        nouvelle_classe_id = request.POST.get('nouvelle_classe')
        if nouvelle_classe_id:
            # Comportement normal : mutation vers une classe existante
            try:
                nouvelle_classe = Classe.objects.get(id=nouvelle_classe_id)
            except (Classe.DoesNotExist, ValueError):
                messages.error(request, "❌ Classe de destination invalide.")
                return redirect('core:muter_eleve', pk=profil.id)

            # Historique mutation (à adapter pour statistiques)
            profil.commentaire_sortie += f"\nMutation: {profil.classe.nom if profil.classe else ''} -> {nouvelle_classe.nom} le {timezone.now().strftime('%d/%m/%Y')}"
            profil.classe = nouvelle_classe
            profil.save()
            messages.success(request, f"✅ Élève muté vers {nouvelle_classe.nom} !")
            return redirect('core:gestion_eleves')
    return render(request, 'core/muter_eleve.html', {
        'profil': profil,
        'classes': Classe.objects.all().order_by('nom'),
        'anciennes_classes': anciennes_classes,
    })


def modifier_eleve(request, pk):
    profil = get_object_or_404(ProfilUtilisateur, id=pk)
    if request.method == 'POST':
        profil.user.first_name = request.POST.get('first_name') or request.POST.get('firstname', '')
        profil.user.last_name  = request.POST.get('last_name')  or request.POST.get('lastname', '')
        profil.user.email      = request.POST.get('email', '')
        if request.POST.get('new_password'):
            profil.user.set_password(request.POST.get('new_password'))
        profil.user.save()
        if request.POST.get('classe'):
            profil.classe = Classe.objects.get(id=request.POST.get('classe'))
        # Scolarité & inscription
        profil.annee_entree = request.POST.get('annee_entree', '').strip()
        if request.POST.get('date_inscription'):
            from datetime import datetime
            try:
                profil.user.date_joined = datetime.strptime(request.POST.get('date_inscription'), '%Y-%m-%d')
                profil.user.save()
            except ValueError:
                pass
        # Champs post-sortie (si élève sorti)
        if profil.est_sorti:
            raison = request.POST.get('raison_sortie', profil.raison_sortie or '')
            profil.raison_sortie       = raison
            profil.annee_scolaire_sortie = request.POST.get('annee_scolaire_sortie', profil.annee_scolaire_sortie or '').strip()
            profil.commentaire_sortie  = request.POST.get('commentaire_sortie', '').strip()
            profil.mention_obtenue     = request.POST.get('mention_obtenue', '')
            profil.poursuite_etudes    = request.POST.get('poursuite_etudes') == 'on'
            profil.type_poursuite      = request.POST.get('type_poursuite', '') if profil.poursuite_etudes else ''
            if raison in ('cap_mention', 'cap_sans_mention', 'echec_cap'):
                profil.type_diplome_obtenu = 'cap'
            elif raison in ('bac_pro_mention', 'bac_pro_sans_mention', 'echec_bac_pro'):
                profil.type_diplome_obtenu = 'bac_pro'
        profil.sexe = request.POST.get('sexe') or None
        profil.save()
        messages.success(request, '✅ Élève modifié !')
        return redirect('core:gestion_eleves')
    return render(request, 'core/modifier_eleve.html', {'profil': profil, 'classes': Classe.objects.all().order_by('nom')})


def supprimer_eleve(request, pk):
    profil = get_object_or_404(ProfilUtilisateur, id=pk)
    if request.method == 'POST':
        nom = profil.user.get_full_name()
        profil.user.delete()
        messages.success(request, f'✅ Élève {nom} supprimé !')
    return redirect('core:gestion_eleves')


VILLES_ORIGINE = [
    'Roubaix', 'Tourcoing', 'Hem', 'Croix', 'Halluin', 'Wasquehal',
    "Villeneuve d'Ascq", 'Marcq en Baroeul', 'Lille', 'Mons en Baroeul',
    'Lys lez Lannoy', 'Leers', 'Saint André', 'Marquette-lez-Lille',
    'Linselles', 'Wattrelos', 'Mouvaux', 'Roncq', 'Lambersart', 'Ronchin', 'Cysoing',
]


def gestion_themes(request):
    classes = Classe.objects.all().order_by('nom')
    classe_selectionnee = request.GET.get('classe')
    if classe_selectionnee:
        themes = Theme.objects.filter(classes__id=classe_selectionnee).annotate(nb_dossiers=Count('dossiers'))
    else:
        themes = Theme.objects.all().annotate(nb_dossiers=Count('dossiers'))
    return render(request, 'core/gestion_themes.html', {'classes': classes, 'themes': themes, 'classe_selectionnee': classe_selectionnee})


def theme_create(request):
    if request.method == 'POST':
        nom = request.POST.get('nom')
        classe_ids = request.POST.getlist('classes')
        if not nom:
            messages.error(request, '❌ Le nom du thème est obligatoire.')
            return render(request, 'core/theme_create.html', {'classes': Classe.objects.all()})
        theme = Theme.objects.create(
            nom=nom,
            description=request.POST.get('description', ''),
            visible_eleves=request.POST.get('visible_eleves') == 'on',
            ordre=request.POST.get('ordre', 0)
        )
        if classe_ids:
            theme.classes.set(Classe.objects.filter(id__in=classe_ids))
        messages.success(request, f'✅ Thème "{theme.nom}" créé !')
        dossier = None
        if request.POST.get('creer_dossier') == 'on':
            dossier_nom = request.POST.get('dossier_nom', '').strip()
            if dossier_nom:
                dossier = Dossier.objects.create(
                    theme=theme, nom=dossier_nom,
                    description=request.POST.get('dossier_description', ''),
                    ordre=request.POST.get('dossier_ordre', 0),
                    visible_eleves=request.POST.get('dossier_visible') == 'on'
                )
                messages.success(request, f'📂 Dossier "{dossier.nom}" créé !')
        if dossier and request.POST.get('ajouter_fichier') == 'on':
            fichier_nom = request.POST.get('fichier_nom', '').strip()
            type_contenu = request.POST.get('type_fichier', 'fichier')
            if fichier_nom:
                fichier = Fichier.objects.create(
                    dossier=dossier, nom=fichier_nom,
                    description=request.POST.get('fichier_description', ''),
                    type_contenu=type_contenu, ordre=0, createur=request.user
                )
                if type_contenu == 'fichier' and request.FILES.get('fichier_upload'):
                    fichier.fichier = request.FILES['fichier_upload']
                elif type_contenu == 'lien':
                    fichier.lien_externe = request.POST.get('fichier_lien', '').strip()
                elif type_contenu == 'iframe':
                    fichier.code_iframe = request.POST.get('fichier_iframe', '').strip()
                fichier.save()
                messages.success(request, f'📄 Ressource "{fichier.nom}" ajoutée !')
        return redirect('core:theme_detail', pk=theme.id)
    return render(request, 'core/theme_create.html', {'classes': Classe.objects.all().order_by('nom')})


def theme_detail(request, pk):
    theme = get_object_or_404(Theme, id=pk)
    is_prof = est_professeur(request.user)
    
    if hasattr(request.user, 'profil') and request.user.profil.est_eleve():
        if request.user.profil.classe and not theme.classes.filter(pk=request.user.profil.classe_id).exists():
            messages.error(request, "❌ Vous n'avez pas accès à ce thème.")
            return redirect('core:dashboard_eleve')
        dossiers = Dossier.objects.filter(theme=theme, actif=True, visible_eleves=True).order_by('ordre', 'nom')
    else:
        dossiers = Dossier.objects.filter(theme=theme, actif=True).order_by('ordre', 'nom')
        
    dossiers_avec_fichiers = []
    for dossier in dossiers:
        fichiers = Fichier.objects.filter(dossier=dossier, actif=True).order_by('ordre', 'nom')
        # On peut pré-charger les fiches de révision directement dans le dossier_avec_fichiers
        dossiers_avec_fichiers.append({'dossier': dossier, 'fichiers': fichiers})
        
    qcms = theme.qcms.annotate(nb_questions=Count('questions')).order_by('-date_creation')
    modes_operatoires = ModeOperatoire.objects.filter(theme=theme, actif=True).order_by('-date_creation')
    
    return render(request, 'core/theme_detail.html', {
        'theme': theme,
        'dossiers_avec_fichiers': dossiers_avec_fichiers,
        'is_prof': is_prof,
        'qcms': qcms,
        'modes_operatoires': modes_operatoires,
    })


def theme_update(request, pk):
    theme = get_object_or_404(Theme, pk=pk)
    classes = Classe.objects.all().order_by('nom')
    if request.method == 'POST':
        nom = request.POST.get('nom')
        if not nom:
            messages.error(request, '❌ Le nom du thème est obligatoire.')
        else:
            theme.nom = nom
            theme.description = request.POST.get('description', '')
            theme.visible_eleves = request.POST.get('visible_eleves') == 'on'
            classe_ids = request.POST.getlist('classes')
            theme.classes.set(Classe.objects.filter(id__in=classe_ids))
            theme.save()
            messages.success(request, f'✅ Thème "{theme.nom}" modifié.')
            if request.POST.get('ajouter_ressource') == 'on':
                dossier_id = request.POST.get('dossier_cible')
                res_nom = request.POST.get('ressource_nom')
                type_contenu = request.POST.get('type_ressource', 'fichier')
                if dossier_id and res_nom:
                    try:
                        dossier_cible = Dossier.objects.get(id=dossier_id)
                        fichier = Fichier.objects.create(
                            dossier=dossier_cible, nom=res_nom,
                            description=request.POST.get('ressource_description', ''),
                            type_contenu=type_contenu, ordre=0, createur=request.user
                        )
                        if type_contenu == 'fichier' and request.FILES.get('ressource_fichier'):
                            fichier.fichier = request.FILES.get('ressource_fichier')
                        elif type_contenu == 'lien':
                            fichier.lien_externe = request.POST.get('ressource_lien')
                        elif type_contenu == 'iframe':
                            fichier.code_iframe = request.POST.get('ressource_iframe')
                        fichier.save()
                        messages.success(request, f'⚡ Ressource "{res_nom}" ajoutée !')
                    except Dossier.DoesNotExist:
                        messages.error(request, "❌ Dossier introuvable.")
                    except Exception as e:
                        messages.error(request, f"❌ Erreur : {str(e)}")
                else:
                    messages.warning(request, "⚠️ Sélectionnez un dossier et un nom.")
            return redirect('core:theme_detail', pk=theme.id)
    dossiers = Dossier.objects.filter(theme=theme).order_by('ordre', 'nom')
    return render(request, 'core/theme_update.html', {'theme': theme, 'classes': classes, 'dossiers': dossiers})


def theme_delete(request, pk):
    theme = get_object_or_404(Theme, pk=pk)
    if request.method == 'POST':
        theme.delete()
        messages.success(request, '✅ Thème supprimé !')
        return redirect('core:gestion_themes')
    return render(request, 'core/theme_confirm_delete.html', {'theme': theme})


def theme_toggle_visibilite(request, pk):
    theme = get_object_or_404(Theme, pk=pk)
    theme.visible_eleves = not theme.visible_eleves
    theme.save()
    messages.success(request, f'Thème {"visible" if theme.visible_eleves else "masqué"} !')
    return redirect('core:theme_detail', pk=pk)


theme_edit = theme_update


def dossier_create(request, theme_id):
    theme = get_object_or_404(Theme, id=theme_id)
    if request.method == 'POST':
        nom = request.POST.get('nom')
        if nom:
            Dossier.objects.create(
                theme=theme, nom=nom,
                description=request.POST.get('description', ''),
                ordre=request.POST.get('ordre', 0),
                visible_eleves=request.POST.get('visible_eleves') == 'on'
            )
            messages.success(request, f'✅ Dossier "{nom}" créé !')
            return redirect('core:theme_detail', pk=theme_id)
    return render(request, 'core/dossier_create.html', {'theme': theme})


def dossier_detail(request, pk):
    dossier = get_object_or_404(Dossier, pk=pk)
    try:
        if not request.user.profil.est_prof():
            if not dossier.visible_eleves or not dossier.theme.visible_eleves:
                messages.error(request, "❌ Ce dossier n'est pas accessible.")
                return redirect('core:dashboard_eleve')
    except ProfilUtilisateur.DoesNotExist:
        pass
    fichiers = dossier.fichiers.filter(actif=True).order_by('ordre', 'nom')
    travaux = TravailARendre.objects.filter(dossier=dossier, actif=True)
    return render(request, 'core/dossier_detail.html', {
        'dossier': dossier, 'fichiers': fichiers, 'travaux': travaux, 'theme': dossier.theme,
    })


def dossier_update(request, pk):
    dossier = get_object_or_404(Dossier, id=pk)
    if request.method == 'POST':
        dossier.nom = request.POST.get('nom')
        dossier.description = request.POST.get('description', '')
        dossier.ordre = request.POST.get('ordre', 0)
        dossier.visible_eleves = request.POST.get('visible_eleves') == 'on'
        dossier.save()
        messages.success(request, '✅ Dossier modifié !')
        return redirect('core:theme_detail', pk=dossier.theme.id)
    return render(request, 'core/dossier_update.html', {'dossier': dossier})


def dossier_delete(request, pk):
    dossier = get_object_or_404(Dossier, id=pk)
    theme_id = dossier.theme.id
    if request.method == 'POST':
        nom = dossier.nom
        dossier.delete()
        messages.success(request, f'✅ Dossier "{nom}" supprimé !')
    return redirect('core:theme_detail', pk=theme_id)


def dossier_toggle_visibilite(request, pk):
    dossier = get_object_or_404(Dossier, pk=pk)
    dossier.visible_eleves = not dossier.visible_eleves
    dossier.save()
    statut = "visible" if dossier.visible_eleves else "masqué"
    messages.success(request, f'Dossier {statut} !')
    return redirect('core:theme_detail', pk=dossier.theme.id)


def fichier_upload(request, dossier_id):
    dossier = get_object_or_404(Dossier, id=dossier_id)
    types_ressources = TypeRessource.objects.all()
    if request.method == 'POST':
        nom = request.POST.get('nom')
        description = request.POST.get('description', '')
        type_contenu = request.POST.get('type_contenu', 'fichier')
        type_ressource_id = request.POST.get('type_ressource')
        ordre = request.POST.get('ordre', 0)
        fichier_file = request.FILES.get('fichier')
        lien_externe = request.POST.get('lien_externe', '').strip()
        code_iframe = request.POST.get('code_iframe', '').strip()
        if not nom:
            messages.error(request, '❌ Le nom est obligatoire.')
        elif type_contenu == 'fichier' and not fichier_file:
            messages.error(request, '❌ Veuillez sélectionner un fichier.')
        elif type_contenu == 'lien' and not lien_externe:
            messages.error(request, '❌ Veuillez entrer une URL.')
        elif type_contenu == 'iframe' and not code_iframe:
            messages.error(request, "❌ Veuillez entrer le code d'intégration.")
        else:
            type_ressource = TypeRessource.objects.get(id=type_ressource_id) if type_ressource_id else None
            fichier = Fichier.objects.create(
                dossier=dossier, nom=nom, description=description,
                type_contenu=type_contenu, type_ressource=type_ressource,
                ordre=ordre, createur=request.user
            )
            if type_contenu == 'fichier' and fichier_file:
                fichier.fichier = fichier_file
            elif type_contenu == 'lien' and lien_externe:
                fichier.lien_externe = lien_externe
            elif type_contenu == 'iframe' and code_iframe:
                fichier.code_iframe = code_iframe
            fichier.save()
            messages.success(request, f'✅ Ressource "{nom}" ajoutée !')
            return redirect('core:dossier_detail', pk=dossier_id)
    return render(request, 'core/fichier_upload.html', {'dossier': dossier, 'types_ressources': types_ressources})


def fichier_update(request, pk):
    fichier = get_object_or_404(Fichier, id=pk)
    types_ressources = TypeRessource.objects.all()
    if request.method == 'POST':
        fichier.nom = request.POST.get('nom')
        fichier.description = request.POST.get('description', '')
        fichier.type_contenu = request.POST.get('type_contenu', fichier.type_contenu)
        fichier.ordre = request.POST.get('ordre', 0)
        type_ressource_id = request.POST.get('type_ressource')
        fichier.type_ressource = TypeRessource.objects.get(id=type_ressource_id) if type_ressource_id else None
        nouveau_fichier = request.FILES.get('fichier')
        lien_externe = request.POST.get('lien_externe', '').strip()
        code_iframe = request.POST.get('code_iframe', '').strip()
        if fichier.type_contenu == 'fichier':
            if nouveau_fichier:
                fichier.fichier = nouveau_fichier
            fichier.lien_externe = None
            fichier.code_iframe = None
        elif fichier.type_contenu == 'lien':
            fichier.lien_externe = lien_externe if lien_externe else None
            fichier.code_iframe = None
        elif fichier.type_contenu == 'iframe':
            fichier.code_iframe = code_iframe if code_iframe else None
            fichier.lien_externe = None
        fichier.save()
        messages.success(request, '✅ Ressource modifiée !')
        return redirect('core:dossier_detail', pk=fichier.dossier.id)
    return render(request, 'core/fichier_update.html', {
        'fichier': fichier, 'types_ressources': types_ressources, 'dossier': fichier.dossier,
    })


def fichier_toggle_visibilite(request, pk):
    fichier = get_object_or_404(Fichier, pk=pk)
    fichier.visible_eleves = not fichier.visible_eleves
    fichier.save()
    statut = "visible" if fichier.visible_eleves else "masqué"
    messages.success(request, f'Fichier « {fichier.nom} » {statut} !')
    return redirect('core:theme_detail', pk=fichier.dossier.theme.id)


def fichier_delete(request, pk):
    fichier = get_object_or_404(Fichier, id=pk)
    dossier_id = fichier.dossier.id
    if request.method == 'POST':
        nom = fichier.nom
        fichier.delete()
        messages.success(request, f'✅ Fichier "{nom}" supprimé !')
    return redirect('core:dossier_detail', pk=dossier_id)


def travaux_par_classe(request, classe_id=None):
    classes = Classe.objects.filter(actif=True).order_by('nom')

    if classe_id:
        return redirect('core:travaux_par_classe')

    classes_avec_travaux = []
    for classe in classes:
        travaux = TravailARendre.objects.filter(
            classe=classe,
            createur=request.user
        ).order_by('-date_creation')

        for t in travaux:
            t.nb_rendus = t.rendus.count() if hasattr(t, 'rendus') else 0
            t.nb_eleves_classe = classe.eleves.filter(
                compte_approuve=True, est_sorti=False
            ).count()

        classes_avec_travaux.append({
            'classe':    classe,
            'travaux':   travaux,
            'nb':        travaux.count(),
            'nb_eleves': classe.eleves.filter(compte_approuve=True, est_sorti=False).count(),
        })

    return render(request, 'core/travaux_par_classe.html', {
        'classes_avec_travaux': classes_avec_travaux,
    })


def travail_create(request, classe_id):
    classe = get_object_or_404(Classe, pk=classe_id)

    if request.method == 'POST':
        from datetime import datetime
        titre           = request.POST.get('titre', '').strip()
        description     = request.POST.get('description', '').strip()
        date_limite_str = request.POST.get('date_limite')
        fichier         = request.FILES.get('fichier_consigne')

        if titre and date_limite_str:
            try:
                date_limite = datetime.strptime(date_limite_str, "%Y-%m-%dT%H:%M")
            except (ValueError, TypeError):
                date_limite = date_limite_str

            travail = TravailARendre.objects.create(
                titre=titre,
                description=description,
                date_limite=date_limite,
                classe=classe,
                createur=request.user,
                fichier_consigne=fichier,
            )
            # ✅ Notification à chaque élève de la classe
            eleves = ProfilUtilisateur.objects.filter(
                classe=classe, type_utilisateur='eleve',
                compte_approuve=True, est_sorti=False
            )
            dl_str = date_limite.strftime("%d/%m/%Y") if hasattr(date_limite, 'strftime') else date_limite_str
            for eleve in eleves:
                Notification.objects.create(
                    destinataire=eleve.user,
                    type_notification='nouveau_cours',
                    titre=f'Nouveau travail : {titre}',
                    message=f'Un nouveau travail vous a été attribué pour le {dl_str}.',
                    lien=reverse('core:rendre_travail', args=[travail.id])
                )
            messages.success(request, f'Travail « {titre} » publié et {eleves.count()} élève(s) notifié(s).')
            return redirect('core:travaux_par_classe')

    return render(request, 'core/travail_create.html', {'classe': classe})


def travail_detail(request, pk):
    travail = get_object_or_404(TravailARendre, pk=pk, createur=request.user)
    rendus  = travail.rendus.select_related('eleve__user').order_by('date_rendu')
    
    # Élèves de la classe
    eleves_classe = ProfilUtilisateur.objects.filter(
        classe=travail.classe, type_utilisateur='eleve',
        compte_approuve=True, est_sorti=False
    ).select_related('user')
    
    # Élèves sans rendu
    eleves_ayant_rendu = set(rendus.values_list('eleve_id', flat=True))
    eleves_sans_rendu = [e for e in eleves_classe if e.id not in eleves_ayant_rendu]
    
    return render(request, 'core/travail_detail.html', {
        'travail':            travail,
        'rendus':             rendus,
        'nb_eleves_classe':   eleves_classe.count(),
        'eleves_sans_rendu':  eleves_sans_rendu,
        'nb_manquants':       len(eleves_sans_rendu),
        'nb_corriges':        rendus.filter(corrige=True).count(),
    })


def travail_delete(request, pk):
    travail = get_object_or_404(TravailARendre, pk=pk, createur=request.user)
    if request.method == 'POST':
        travail.delete()
        messages.success(request, 'Travail supprimé.')
    return redirect('core:travaux_par_classe')


def rendre_travail(request, pk):
    travail = get_object_or_404(TravailARendre, id=pk, actif=True)
    profil = request.user.profil
    if profil.classe != travail.classe:
        return redirect('core:dashboard_eleve')
    
    # Vérifier si déjà rendu
    deja_rendu = RenduEleve.objects.filter(travail=travail, eleve=profil).first()
    
    if request.method == 'POST' and not deja_rendu:
        fichier_rendu = request.FILES.get('fichier_rendu')
        if fichier_rendu:
            RenduEleve.objects.create(
                travail=travail, eleve=profil,
                fichier_rendu=fichier_rendu,
                commentaire=request.POST.get('commentaire', ''), rendu=True
            )
            Notification.objects.create(
                destinataire=travail.createur, type_notification='rendu',
                titre=f'📥 Travail rendu : {travail.titre}',
                message=f'{request.user.get_full_name()} a rendu le travail "{travail.titre}".',
                lien=f'/travaux/detail/{travail.id}/'
            )
            messages.success(request, '✅ Travail envoyé à votre professeur !')
            return redirect('core:mes_travaux_eleve')
        else:
            messages.error(request, '❌ Veuillez sélectionner un fichier.')
    
    return render(request, 'core/rendre_travail.html', {
        'travail':    travail,
        'deja_rendu': deja_rendu,
    })


def mes_travaux_eleve(request):
    try:
        if not request.user.profil.est_eleve():
            return redirect('core:home')
    except Exception:
        return redirect('core:home')
    ma_classe = request.user.profil.classe
    travaux_a_faire = []
    mes_rendus = []
    if ma_classe:
        travaux_a_faire = TravailARendre.objects.filter(classe=ma_classe, actif=True)\
            .exclude(rendus__eleve=request.user.profil).order_by('date_limite')
        mes_rendus = RenduEleve.objects.filter(eleve=request.user.profil)\
            .select_related('travail').order_by('-date_rendu')
    return render(request, 'core/mes_travaux_eleve.html', {
        'travaux_a_faire': travaux_a_faire, 'mes_rendus': mes_rendus,
    })


def travaux_creer(request):
    """Page choix de classe avant de créer un travail."""
    classes = Classe.objects.filter(actif=True).order_by('nom')

    classes_par_niveau = {}
    for classe in classes:
        niveau = classe.niveau if hasattr(classe, 'niveau') and classe.niveau else 'Autres'
        if niveau not in classes_par_niveau:
            classes_par_niveau[niveau] = []
        classes_par_niveau[niveau].append(classe)
        classe.nb_eleves = classe.eleves.filter(
            compte_approuve=True, est_sorti=False
        ).count()

    return render(request, 'core/travaux_creer.html', {
        'classes_par_niveau': classes_par_niveau,
    })


def travaux_corriger(request):
    """Liste des rendus à corriger."""
    rendus = RenduEleve.objects.filter(
        travail__createur=request.user,
        corrige=False
    ).select_related('travail', 'eleve__user').order_by('date_rendu')

    nb_messages_non_lus = MessageEleve.objects.filter(
        professeur=request.user.profil, lu=False
    ).count()
    return render(request, 'core/travaux_corriger.html', {
        'rendus': rendus,
        'nb_messages_non_lus': nb_messages_non_lus,
    })


def corriger_rendu(request, pk):
    rendu = get_object_or_404(RenduEleve, id=pk)
    if request.method == 'POST':
        rendu.note = request.POST.get('note')
        rendu.appreciation = request.POST.get('appreciation', '')
        rendu.corrige = True
        rendu.date_correction = timezone.now()
        rendu.save()
        Notification.objects.create(
            destinataire=rendu.eleve.user, type_notification='correction',
            titre=f"Travail corrigé : {rendu.travail.titre}",
            message=f"Note : {rendu.note}/20" if rendu.note else "Travail vérifié",
            lien='/dashboard/eleve/'
        )
        messages.success(request, '✅ Travail corrigé !')
        return redirect('core:travaux_corriger')

    # Élèves de la classe n'ayant pas rendu
    travail = rendu.travail
    eleves_classe = ProfilUtilisateur.objects.filter(
        classe=travail.classe, type_utilisateur='eleve',
        compte_approuve=True, est_sorti=False
    ).select_related('user')
    eleves_ayant_rendu = set(travail.rendus.values_list('eleve_id', flat=True))
    eleves_sans_rendu = [e for e in eleves_classe if e.id not in eleves_ayant_rendu]

    return render(request, 'core/corriger_rendu.html', {
        'rendu': rendu,
        'eleves_sans_rendu': eleves_sans_rendu,
        'nb_manquants': len(eleves_sans_rendu),
        'nb_rendus': travail.rendus.count(),
        'nb_eleves_classe': eleves_classe.count(),
    })


def marquer_corrige(request, pk):
    rendu = get_object_or_404(RenduEleve, id=pk)
    rendu.corrige = True
    rendu.date_correction = timezone.now()
    rendu.save()
    Notification.objects.filter(destinataire=request.user, type_notification='rendu', lue=False).update(lue=True)
    messages.success(request, '✅ Travail marqué comme corrigé.')
    return redirect('core:travaux_corriger')


def mes_notifications(request):
    filtre = request.GET.get('filtre', 'non_lues')
    if filtre == 'historique':
        notifications = Notification.objects.filter(destinataire=request.user).order_by('-date_creation')
    else:
        notifications = Notification.objects.filter(destinataire=request.user, lue=False).order_by('-date_creation')
    nb_non_lues = Notification.objects.filter(destinataire=request.user, lue=False).count()
    return render(request, 'core/mes_notifications.html', {
        'notifications': notifications, 'filtre_actif': filtre, 'nb_non_lues': nb_non_lues,
    })


def marquer_notification_lue(request, pk):
    notification = get_object_or_404(Notification, id=pk, destinataire=request.user)
    notification.lue = True
    notification.save()
    if notification.lien:
        return redirect(notification.lien)
    return redirect('core:mes_notifications')


def marquer_toutes_lues(request):
    Notification.objects.filter(destinataire=request.user, lue=False).update(lue=True)
    messages.success(request, '✅ Toutes les notifications ont été marquées comme lues !')
    return redirect('core:mes_notifications')


def gestion_approbations(request):
    eleves_en_attente = ProfilUtilisateur.objects.filter(
        type_utilisateur='eleve', compte_approuve=False, user__is_active=False
    ).select_related('user', 'classe').order_by('-date_inscription')
    return render(request, 'core/gestion_approbations.html', {'eleves_en_attente': eleves_en_attente})


def approuver_eleve(request, pk):
    profil = get_object_or_404(ProfilUtilisateur, id=pk)
    if request.method == 'POST':
        classe_id = request.POST.get('classe')
        if classe_id:
            profil.classe = Classe.objects.get(id=classe_id)
        profil.compte_approuve = True
        profil.date_approbation = timezone.now()
        profil.save()
        profil.user.is_active = True
        profil.user.save()
        Notification.objects.create(
            destinataire=profil.user, type_notification='nouveau_cours',
            titre='✅ Compte approuvé !', message='Votre compte a été approuvé.', lien='/login/eleve/'
        )
        messages.success(request, '✅ Élève approuvé !')
        return redirect('core:gestion_approbations')
    return render(request, 'core/approuver_eleve.html', {
        'profil': profil,
        'etablissements': EtablissementOrigine.objects.all().order_by('nom'),
        'classes': Classe.objects.all().order_by('nom'),
    })


def refuser_eleve(request, pk):
    profil = get_object_or_404(ProfilUtilisateur, id=pk)
    if request.method == 'POST':
        profil.user.delete()
        messages.success(request, '❌ Demande refusée.')
    return redirect('core:gestion_approbations')


def _annee_scolaire_courante():
    """Retourne l'année scolaire courante au format 'YYYY-YYYY'."""
    from datetime import date as _date
    today = _date.today()
    if today.month >= 9:
        return f"{today.year}-{today.year + 1}"
    return f"{today.year - 1}-{today.year}"


def gestion_sorties(request):
    eleves_actifs = ProfilUtilisateur.objects.filter(
        type_utilisateur='eleve', est_sorti=False, compte_approuve=True
    ).select_related('user', 'classe').order_by('classe__nom', 'user__last_name')
    eleves_sortis = ProfilUtilisateur.objects.filter(
        type_utilisateur='eleve', est_sorti=True
    ).select_related('user', 'classe').order_by('-date_sortie')
    return render(request, 'core/gestion_sorties.html', {
        'eleves_actifs': eleves_actifs, 'eleves_sortis': eleves_sortis,
    })


def marquer_sortie(request, pk):
    profil = get_object_or_404(ProfilUtilisateur, id=pk)
    annee_defaut = _annee_scolaire_courante()
    if request.method == 'POST':
        raison     = request.POST.get('raison_sortie', '')
        commentaire= request.POST.get('commentaire_sortie', '').strip()
        annee      = request.POST.get('annee_scolaire_sortie', annee_defaut).strip() or annee_defaut
        mention    = request.POST.get('mention_obtenue', '')
        poursuite  = request.POST.get('poursuite_etudes') == 'on'
        type_pours = request.POST.get('type_poursuite', '')
        # Inférer le type de diplôme
        if raison in ('cap_mention', 'cap_sans_mention', 'echec_cap'):
            type_diplome = 'cap'
        elif raison in ('bac_pro_mention', 'bac_pro_sans_mention', 'echec_bac_pro'):
            type_diplome = 'bac_pro'
        else:
            type_diplome = ''
        profil.est_sorti           = True
        profil.date_sortie         = timezone.now()
        profil.raison_sortie       = raison
        profil.annee_scolaire_sortie = annee
        profil.commentaire_sortie  = commentaire
        profil.mention_obtenue     = mention
        profil.type_diplome_obtenu = type_diplome
        profil.poursuite_etudes    = poursuite
        profil.type_poursuite      = type_pours if poursuite else ''
        profil.user.is_active = False
        profil.user.save()
        profil.save()
        messages.success(request, f'✅ {profil.user.get_full_name()} marqué comme sorti ({raison}) — {annee}.')
        return redirect('core:gestion_sorties')
    return render(request, 'core/marquer_sortie.html', {
        'profil': profil,
        'annee_defaut': annee_defaut,
    })


def reactiver_eleve(request, pk):
    profil = get_object_or_404(ProfilUtilisateur, id=pk)
    profil.est_sorti = False
    profil.date_sortie = None
    profil.save()
    profil.user.is_active = True
    profil.user.save()
    messages.success(request, '✅ Élève réactivé.')
    return redirect('core:gestion_sorties')


def modifier_sortie(request, pk):
    """Permet de compléter / corriger les infos post-sortie d'un élève."""
    profil = get_object_or_404(ProfilUtilisateur, id=pk, est_sorti=True)
    annee_defaut = profil.annee_scolaire_sortie or _annee_scolaire_courante()
    if request.method == 'POST':
        raison     = request.POST.get('raison_sortie', profil.raison_sortie or '')
        commentaire= request.POST.get('commentaire_sortie', '').strip()
        annee      = request.POST.get('annee_scolaire_sortie', annee_defaut).strip() or annee_defaut
        mention    = request.POST.get('mention_obtenue', '')
        poursuite  = request.POST.get('poursuite_etudes') == 'on'
        type_pours = request.POST.get('type_poursuite', '')
        if raison in ('cap_mention', 'cap_sans_mention', 'echec_cap'):
            type_diplome = 'cap'
        elif raison in ('bac_pro_mention', 'bac_pro_sans_mention', 'echec_bac_pro'):
            type_diplome = 'bac_pro'
        else:
            type_diplome = ''
        profil.raison_sortie       = raison
        profil.annee_scolaire_sortie = annee
        profil.commentaire_sortie  = commentaire
        profil.mention_obtenue     = mention
        profil.type_diplome_obtenu = type_diplome
        profil.poursuite_etudes    = poursuite
        profil.type_poursuite      = type_pours if poursuite else ''
        profil.save()
        messages.success(request, f'✅ Informations de sortie mises à jour pour {profil.user.get_full_name()}.')
        return redirect('core:gestion_sorties')
    return render(request, 'core/modifier_sortie.html', {
        'profil': profil,
        'annee_defaut': annee_defaut,
    })


def archives(request):
    if request.method == 'POST':
        titre = request.POST.get('titre')
        if titre:
            Archive.objects.create(
                titre=titre,
                description=request.POST.get('description', ''),
                fichier=request.FILES.get('fichier') or None,
                categorie=request.POST.get('categorie'),
                annee_scolaire=request.POST.get('annee_scolaire', '2024-2025'),
                createur=request.user
            )
            messages.success(request, '✅ Archive ajoutée !')
        else:
            messages.error(request, '❌ Le titre est obligatoire.')
        return redirect('core:archives')
    toutes_archives = Archive.objects.filter(actif=True).order_by('-annee_scolaire', '-date_creation')
    LABELS = {
        'evaluations': 'Évaluations', 'examens': 'Examens',
        'administratif': 'Documents administratifs', 'ressources': 'Ressources pédagogiques', 'autre': 'Autre',
    }
    archives_par_categorie = {}
    for archive in toutes_archives:
        label = LABELS.get(archive.categorie, archive.categorie or 'Autre')
        if label not in archives_par_categorie:
            archives_par_categorie[label] = []
        archives_par_categorie[label].append(archive)
    stats = {
        'total': toutes_archives.count(),
        'evaluations': toutes_archives.filter(categorie='evaluations').count(),
        'examens': toutes_archives.filter(categorie='examens').count(),
        'administratif': toutes_archives.filter(categorie='administratif').count(),
    }
    # Liste d'années présentes dans les archives (descendante)
    annees_disponibles = list(Archive.objects.filter(actif=True).values_list('annee_scolaire', flat=True).distinct())
    # Trier en ordre descendant si les années sont au format 'YYYY-YYYY'
    try:
        annees_disponibles = sorted(annees_disponibles, reverse=True)
    except Exception:
        pass

    return render(request, 'core/archives.html', {
        'archives_par_categorie': archives_par_categorie,
        'stats': stats,
        'annees_disponibles': annees_disponibles,
    })


def archives_export(request):
    """Génère un ZIP téléchargeable contenant les archives filtrées par année scolaire
    et optionnellement par catégorie. Inclut les fichiers liés et des JSON décrivant
    les archives et les objets référencés (fiche_contrat / qcm) lorsque présents.
    """
    annee = request.GET.get('annee') or request.GET.get('annee_scolaire')
    categorie = request.GET.get('categorie') or None
    if not annee:
        messages.error(request, '❌ Indiquez une année scolaire pour l’export.')
        return redirect('core:archives')

    qs = Archive.objects.filter(actif=True, annee_scolaire=annee)
    if categorie and categorie != 'all':
        qs = qs.filter(categorie=categorie)

    if not qs.exists():
        messages.warning(request, '⚠️ Aucun document trouvé pour ces critères.')
        return redirect('core:archives')

    bio = io.BytesIO()
    with zipfile.ZipFile(bio, 'w', zipfile.ZIP_DEFLATED) as z:
        meta_list = []
        for idx, archive in enumerate(qs.order_by('categorie', '-date_creation')):
            meta = {
                'id': archive.id,
                'titre': archive.titre,
                'description': archive.description,
                'categorie': archive.categorie,
                'annee_scolaire': archive.annee_scolaire,
                'createur': archive.createur.get_full_name() if archive.createur else None,
                'date_creation': archive.date_creation.isoformat() if archive.date_creation else None,
            }
            # Déterminer la classe cible pour cet archive (par défaut Sans_classe)
            safe_classe = 'Sans_classe'
            # Tentative: extraire fiche_contrat_id pour associer la classe
            try:
                if archive.description and 'fiche_contrat_id:' in archive.description:
                    part_try = archive.description.split('fiche_contrat_id:')[1].split('|')[0].strip()
                    fc_try = int(part_try)
                    fc_obj_try = FicheContrat.objects.filter(id=fc_try).first()
                    if fc_obj_try and fc_obj_try.classe:
                        safe_classe = fc_obj_try.classe.nom.replace(' ', '_')
            except Exception:
                pass

            # Inclure le fichier si présent
            if archive.fichier:
                try:
                    filename = os.path.basename(archive.fichier.name)
                    # Placer dans <Classe>/<categorie>/
                    cat = archive.categorie or 'autre'
                    arc_folder = f"{safe_classe}/{cat}"
                    # Essayez d'ouvrir via storage
                    try:
                        with archive.fichier.open('rb') as fh:
                            data = fh.read()
                    except Exception:
                        # Fallback sur path si disponible
                        try:
                            with open(archive.fichier.path, 'rb') as fh:
                                data = fh.read()
                        except Exception:
                            data = None
                    if data:
                        # Si déjà PDF, laisser tel quel
                        lower = filename.lower()
                        try:
                            if data[:4] == b'%PDF':
                                out_name = f"{arc_folder}/{idx}_{os.path.splitext(filename)[0]}.pdf"
                                z.writestr(out_name, data)
                            elif lower.endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                                try:
                                    import fitz
                                    img_stream = data
                                    doc_img = fitz.open()
                                    # Créer page à taille de l'image
                                    img = fitz.Pixmap(fitz.open('png' if lower.endswith('.png') else 'jpeg', img_stream))
                                    rect = fitz.Rect(0, 0, img.width, img.height)
                                    page = doc_img.new_page(width=img.width, height=img.height)
                                    page.insert_image(rect, stream=img_stream)
                                    try:
                                        pdf_bytes = doc_img.write()
                                    except Exception:
                                        try:
                                            pdf_bytes = doc_img.tobytes()
                                        except Exception:
                                            pdf_bytes = None
                                    doc_img.close()
                                    if pdf_bytes:
                                        out_name = f"{arc_folder}/{idx}_{os.path.splitext(filename)[0]}.pdf"
                                        z.writestr(out_name, pdf_bytes)
                                    else:
                                        # fallback: write original file
                                        out_name = f"{arc_folder}/{idx}_{filename}"
                                        z.writestr(out_name, data)
                                except Exception:
                                    out_name = f"{arc_folder}/{idx}_{filename}"
                                    z.writestr(out_name, data)
                            else:
                                # Autres types: on essaye d'inclure tel quel (métadonnées indiquent non-PDF)
                                out_name = f"{arc_folder}/{idx}_{filename}"
                                z.writestr(out_name, data)
                        except Exception:
                            meta['fichier_inclus'] = False
                            meta['fichier_nom'] = archive.fichier.name
                        else:
                            meta['fichier_inclus'] = True
                            meta['fichier_nom'] = out_name
                except Exception:
                    meta['fichier_inclus'] = False
            else:
                meta['fichier_inclus'] = False

            # Si la description référence une fiche_contrat ou un qcm, joindre leur export.
            if archive.description and 'fiche_contrat_id:' in archive.description:
                try:
                    part = archive.description.split('fiche_contrat_id:')[1].split('|')[0].strip()
                    fc_id = int(part)
                    try:
                        fc = FicheContrat.objects.get(id=fc_id)
                        # Sérialisation simplifiée
                        fc_data = {
                            'id': fc.id,
                            'titre': getattr(fc, 'titre', getattr(fc, 'titre_tp', '')),
                            'createur': fc.createur.get_full_name() if fc.createur else None,
                        }
                        # Organiser par dossier de classe dans le ZIP
                        classe_nom = fc.classe.nom if fc.classe else 'Sans_classe'
                        safe_classe = classe_nom.replace(' ', '_')
                        # Tentative de générer un PDF résumé via PyMuPDF (si disponible)
                        try:
                            import fitz
                            doc = fitz.open()
                            page = doc.new_page()
                            ftitre = getattr(fc, 'titre', getattr(fc, 'titre_tp', ''))
                            header = f"Fiche contrat: {ftitre}\nClasse: {classe_nom}\nCreateur: {fc.createur.get_full_name() if fc.createur else ''}\n\n"
                            evs = FicheEvaluation.objects.filter(fiche_contrat=fc).select_related('eleve__user')
                            body = json.dumps({
                                'fiche': fc_data,
                                'evaluations': [
                                    {'id': ev.id, 'eleve': ev.eleve.user.get_full_name() if ev.eleve and ev.eleve.user else None, 'note': ev.note_sur_20}
                                    for ev in evs
                                ]
                            }, ensure_ascii=False, indent=2)
                            # Générer un PDF plus lisible via le helper
                            evs = FicheEvaluation.objects.filter(fiche_contrat=fc).select_related('eleve__user')
                            pdf_bytes = _render_fiche_contrat_pdf_bytes(fc, evs)
                            if not pdf_bytes:
                                # fallback: render print template to HTML then to PDF (xhtml2pdf)
                                try:
                                    lignes_contrat = fc.lignes.select_related('competence_pro', 'sous_competence', 'critere', 'indicateur').order_by('ordre')
                                    cps_vus = set()
                                    competences_vises = []
                                    for ligne in lignes_contrat:
                                        if ligne.competence_pro and ligne.competence_pro.id not in cps_vus:
                                            cps_vus.add(ligne.competence_pro.id)
                                            competences_vises.append(ligne.competence_pro)
                                    competences_vises.sort(key=lambda x: getattr(x, 'code', ''))
                                    nb_lignes = lignes_contrat.count()
                                    poids_auto = round(100 / nb_lignes, 2) if nb_lignes > 0 else 10.0
                                    savoirs_bruts = getattr(fc, 'savoirs_associes', '') or ''
                                    savoirs_dedupliques = list(dict.fromkeys(l.strip() for l in savoirs_bruts.splitlines() if l.strip()))
                                    html = render_to_string('core/fiche_contrat_print.html', {
                                        'fiche_contrat': fc,
                                        'eleves': evs,
                                        'competences_vises': competences_vises,
                                        'poids_auto': poids_auto,
                                        'savoirs_dedupliques': savoirs_dedupliques,
                                    })
                                    buf = io.BytesIO()
                                    pisa_status = pisa.CreatePDF(io.BytesIO(html.encode('utf-8')), dest=buf, encoding='utf-8')
                                    if not pisa_status.err:
                                        pdf_bytes = buf.getvalue()
                                except Exception:
                                    pdf_bytes = None
                            if pdf_bytes:
                                z.writestr(f'{safe_classe}/{archive.categorie}/fiche_contrat_{fc.id}.pdf', pdf_bytes)
                            else:
                                # Fallback JSON for fiche_contrat
                                ev_list = []
                                for ev in evs:
                                    ev_list.append({'id': ev.id, 'eleve': ev.eleve.user.get_full_name() if ev.eleve and ev.eleve.user else None, 'note': ev.note_sur_20})
                                z.writestr(f'{safe_classe}/{archive.categorie}/fiche_contrat_{fc.id}.json', json.dumps(fc_data, ensure_ascii=False, indent=2))
                                # Tenter de générer un PDF par élève; sinon écrire JSON
                                for ev in evs:
                                    pdf_ev = _render_fiche_evaluation_pdf_bytes(ev)
                                    if not pdf_ev:
                                        # fallback: render evaluation print template to PDF
                                        try:
                                            # build context similar to generer_fiches_evaluation
                                            lignes = ev.lignes_evaluation.select_related('ligne_contrat__competence_pro', 'ligne_contrat__sous_competence', 'ligne_contrat__critere', 'ligne_contrat__indicateur').order_by('ligne_contrat__ordre')
                                            from itertools import groupby
                                            def get_cp(l): return l.ligne_contrat.competence_pro
                                            def get_sc(l): return l.ligne_contrat.sous_competence
                                            groupes_competences = []
                                            for cp, lignes_cp in groupby(lignes, key=get_cp):
                                                lignes_cp_list = list(lignes_cp)
                                                sous_competences = []
                                                for sc, lignes_sc in groupby(lignes_cp_list, key=get_sc):
                                                    sous_competences.append({'sous_competence': sc, 'lignes': list(lignes_sc)})
                                                groupes_competences.append({'competence_pro': cp, 'lignes': lignes_cp_list, 'sous_competences': sous_competences})
                                            html = render_to_string('core/fiche_evaluation_print.html', {
                                                'fiche_contrat': fc,
                                                'donnees_impression': [{'eleve': ev.eleve, 'evaluation': ev, 'groupes_competences': groupes_competences}],
                                                'poids_auto': round(100 / max(1, fc.lignes.count()), 2),
                                            })
                                            buf = io.BytesIO()
                                            pisa_status = pisa.CreatePDF(io.BytesIO(html.encode('utf-8')), dest=buf, encoding='utf-8')
                                            if not pisa_status.err:
                                                pdf_ev = buf.getvalue()
                                        except Exception:
                                            pdf_ev = None
                                    safe_nom = (ev.eleve.user.get_full_name() if ev.eleve and ev.eleve.user else f'eleve_{ev.id}').replace(' ', '_')
                                    if pdf_ev:
                                        z.writestr(f'{safe_classe}/{archive.categorie}/fiche_evaluation_{ev.id}_{safe_nom}.pdf', pdf_ev)
                                    else:
                                        z.writestr(f'{safe_classe}/{archive.categorie}/fiche_evaluation_{ev.id}_{safe_nom}.json', json.dumps({'id': ev.id, 'eleve': safe_nom, 'note': ev.note_sur_20}, ensure_ascii=False, indent=2))
                        except Exception:
                            # Si PyMuPDF absent ou erreur, écrire JSON dans le dossier de la classe
                            evs = FicheEvaluation.objects.filter(fiche_contrat=fc).select_related('eleve__user')
                            ev_list = []
                            for ev in evs:
                                ev_list.append({'id': ev.id, 'eleve': ev.eleve.user.get_full_name() if ev.eleve and ev.eleve.user else None, 'note': ev.note_sur_20})
                            z.writestr(f'{safe_classe}/{archive.categorie}/fiche_contrat_{fc.id}.json', json.dumps(fc_data, ensure_ascii=False, indent=2))
                            # Générer PDF individuel par élève si possible
                            for ev in evs:
                                pdf_ev = _render_fiche_evaluation_pdf_bytes(ev)
                                safe_nom = (ev.eleve.user.get_full_name() if ev.eleve and ev.eleve.user else f'eleve_{ev.id}').replace(' ', '_')
                                if pdf_ev:
                                    z.writestr(f'{safe_classe}/{archive.categorie}/fiche_evaluation_{ev.id}_{safe_nom}.pdf', pdf_ev)
                                else:
                                    z.writestr(f'{safe_classe}/{archive.categorie}/fiche_evaluation_{ev.id}_{safe_nom}.json', json.dumps({'id': ev.id, 'eleve': safe_nom, 'note': ev.note_sur_20}, ensure_ascii=False, indent=2))
                        meta['fiche_contrat_inclus'] = True
                        meta['fiche_contrat_id'] = fc.id
                    except FicheContrat.DoesNotExist:
                        meta['fiche_contrat_inclus'] = False
                except Exception:
                    meta['fiche_contrat_inclus'] = False

            if archive.description and 'qcm_id:' in archive.description:
                try:
                    raw = archive.description.split('qcm_id:')[1].split('|')[0].strip()
                    qcm_id_val = int(raw)
                    try:
                        qcm_obj = QCM.objects.get(id=qcm_id_val)
                        qcm_data = {'id': qcm_obj.id, 'titre': qcm_obj.titre, 'date_creation': qcm_obj.date_creation.isoformat() if qcm_obj.date_creation else None}
                        z.writestr(f'data/qcm_{qcm_obj.id}.json', json.dumps(qcm_data, ensure_ascii=False, indent=2))
                        # Sessions terminées
                        sessions = SessionQCM.objects.filter(qcm=qcm_obj, termine=True).select_related('eleve__user')
                        sessions_list = []
                        for s in sessions:
                            sessions_list.append({'id': s.id, 'eleve': s.eleve.user.get_full_name() if s.eleve and s.eleve.user else None, 'score': s.score})
                        z.writestr(f'data/qcm_sessions_{qcm_obj.id}.json', json.dumps(sessions_list, ensure_ascii=False, indent=2))
                        meta['qcm_inclus'] = True
                        meta['qcm_id'] = qcm_obj.id
                    except QCM.DoesNotExist:
                        meta['qcm_inclus'] = False
                except Exception:
                    meta['qcm_inclus'] = False

            meta_list.append(meta)

        # Écrire le fichier de métadonnées
        z.writestr('data/archives_metadata.json', json.dumps(meta_list, ensure_ascii=False, indent=2))

    bio.seek(0)
    filename = f'archives_{annee}.zip'
    resp = HttpResponse(bio.read(), content_type='application/zip')
    resp['Content-Disposition'] = f'attachment; filename="{filename}"'
    return resp


def supprimer_archive(request, pk):
    # Allow the creator or staff/superuser to delete an archive. If the user is
    # not authorised, show a friendly error instead of raising 404.
    archive = get_object_or_404(Archive, pk=pk)
    user = request.user
    if not (archive.createur == user or getattr(user, 'is_staff', False) or getattr(user, 'is_superuser', False)):
        messages.error(request, "❌ Vous n'avez pas les droits pour supprimer cette archive.")
        return redirect('core:archives')

    # Accept GET and POST (the archives list uses a GET link with JS confirm)
    archive.delete()
    messages.success(request, f'Archive « {archive.titre} » supprimée.')
    return redirect('core:archives')


def archive_detail(request, pk):
    archive = get_object_or_404(Archive, id=pk)
    if request.method == 'POST' and request.POST.get('action') == 'change_categorie':
        nouvelle_categorie = request.POST.get('categorie', '').strip()
        CATS_VALIDES = ('evaluations', 'examens', 'administratif', 'ressources', 'autre')
        if nouvelle_categorie in CATS_VALIDES:
            archive.categorie = nouvelle_categorie
            archive.save()
            messages.success(request, '✅ Catégorie mise à jour.')
        return redirect('core:archive_detail', pk=pk)
    fiche_contrat = None
    evaluations = []
    fiche_contrat_id = None
    qcm_obj = None
    qcm_sessions = []
    if archive.description and 'fiche_contrat_id:' in archive.description:
        try:
            part = archive.description.split('fiche_contrat_id:')[1].split('|')[0].strip()
            fiche_contrat_id = int(part)
        except (ValueError, IndexError):
            pass
    if fiche_contrat_id:
        try:
            fiche_contrat = FicheContrat.objects.get(id=fiche_contrat_id)
            evaluations = FicheEvaluation.objects.filter(fiche_contrat=fiche_contrat)\
                .select_related('eleve__user').order_by('eleve__user__last_name')
            for ev in evaluations:
                if ev.note_sur_20 is None:
                    ev.calculer_note_sur_20()
        except FicheContrat.DoesNotExist:
            pass
    if archive.description and 'qcm_id:' in archive.description and not fiche_contrat:
        try:
            raw = archive.description.split('qcm_id:')[1].split('|')[0].strip()
            qcm_id_val = int(raw)
            qcm_obj = QCM.objects.get(id=qcm_id_val)
            sessions_qs = (
                SessionQCM.objects
                .filter(qcm=qcm_obj, termine=True)
                .select_related('eleve__user')
                .order_by('eleve__user__last_name')
            )
            questions_list = list(qcm_obj.questions.all())
            for s in sessions_qs:
                reponses = s.reponses or {}
                detail = []
                for q in questions_list:
                    rep = reponses.get(str(q.id), '')
                    correct = bool(rep) and rep.upper() == q.bonne_reponse.upper()
                    choix_map = {
                        'A': q.choix_a, 'B': q.choix_b,
                        'C': q.choix_c or '', 'D': q.choix_d or '',
                    }
                    detail.append({
                        'enonce':      q.enonce,
                        'rep_eleve':   rep.upper() if rep else '\u2014',
                        'rep_texte':   choix_map.get(rep.upper(), '\u2014') if rep else 'Sans r\u00e9ponse',
                        'bonne_rep':   q.bonne_reponse,
                        'bonne_texte': choix_map.get(q.bonne_reponse, ''),
                        'correct':     correct,
                    })
                qcm_sessions.append({'session': s, 'detail': detail})
        except (ValueError, IndexError, QCM.DoesNotExist):
            pass
    return render(request, 'core/archive_detail.html', {
        'archive':          archive,
        'fiche_contrat':    fiche_contrat,
        'fiche_contrat_id': fiche_contrat_id,
        'evaluations':      evaluations,
        'qcm':              qcm_obj,
        'qcm_sessions':     qcm_sessions,
    })


@login_required
def archives_export_avance(request):
    """
    Export ZIP avancé avec choix du tri (par classe / élève / catégorie),
    filtres optionnels (classe, élève, catégorie).
    GET sans paramètre 'go' → affiche le formulaire.
    GET avec 'go' → génère et télécharge le ZIP.
    """
    from core.models import Classe, ProfilUtilisateur, Archive

    # Données pour le formulaire
    annees_disponibles = sorted(
        Archive.objects.filter(actif=True)
        .values_list('annee_scolaire', flat=True).distinct(),
        reverse=True
    )
    # Inclure aussi les années depuis les FicheContrat
    annees_fc = sorted(
        Classe.objects.filter(actif=True)
        .values_list('annee_scolaire', flat=True).distinct(),
        reverse=True
    )
    annees_all = sorted(set(list(annees_disponibles) + [a for a in annees_fc if a]), reverse=True)

    classes = Classe.objects.filter(actif=True).order_by('nom')
    eleves = (
        ProfilUtilisateur.objects
        .filter(type_utilisateur='eleve', compte_approuve=True)
        .select_related('user', 'classe')
        .order_by('user__last_name', 'user__first_name')
    )

    CATEGORIES = [
        ('evaluations', 'Évaluations'),
        ('examens', 'Examens'),
        ('administratif', 'Administratif'),
        ('ressources', 'Ressources'),
        ('autre', 'Autre'),
    ]

    # ── SI DEMANDE DE TÉLÉCHARGEMENT ──
    if request.GET.get('go'):
        annee = request.GET.get('annee', '2025-2026')
        tri = request.GET.get('tri', 'par_classe')
        if tri not in ('par_classe', 'par_eleve', 'par_categorie'):
            tri = 'par_classe'

        classes_ids = request.GET.getlist('classes')
        classes_ids = [int(c) for c in classes_ids if c.isdigit()] or None

        eleves_ids = request.GET.getlist('eleves')
        eleves_ids = [int(e) for e in eleves_ids if e.isdigit()] or None

        cats = request.GET.getlist('categories')
        cats = [c for c in cats if c] or None

        from core.utils_export import generer_zip_avance
        try:
            zip_bytes, nb_fichiers, erreurs_list = generer_zip_avance(
                annee=annee,
                tri=tri,
                classes_ids=classes_ids,
                eleves_ids=eleves_ids,
                categories=cats,
            )
        except Exception as exc:
            import logging
            logging.getLogger(__name__).error('Export avancé échoué : %s', exc, exc_info=True)
            messages.error(request, f'Erreur lors de la génération : {exc}')
            return redirect('core:archives_export_avance')

        if nb_fichiers == 0:
            messages.warning(request, 'Aucun fichier trouvé pour ces critères.')
            return redirect('core:archives_export_avance')

        tri_label = {'par_classe': 'classe', 'par_eleve': 'eleve', 'par_categorie': 'categorie'}.get(tri, tri)
        filename = f'archives_{annee}_{tri_label}.zip'
        response = HttpResponse(zip_bytes, content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    return render(request, 'core/archives_export_avance.html', {
        'annees_disponibles': annees_all,
        'classes': classes,
        'eleves': eleves,
        'categories': CATEGORIES,
    })


def _stats_compteurs_eleves():
    """
    Retourne les compteurs globaux d'élèves (total, actifs, sortis, diplômés).
    """
    total_eleves  = ProfilUtilisateur.objects.filter(type_utilisateur='eleve', compte_approuve=True).count()
    eleves_actifs = ProfilUtilisateur.objects.filter(type_utilisateur='eleve', compte_approuve=True, est_sorti=False).count()
    eleves_sortis = ProfilUtilisateur.objects.filter(type_utilisateur='eleve', est_sorti=True).count()
    nb_diplomes   = ProfilUtilisateur.objects.filter(
        type_utilisateur='eleve', est_sorti=True,
        raison_sortie__in=['cap_mention', 'cap_sans_mention', 'bac_pro_mention', 'bac_pro_sans_mention']
    ).count()
    
    # 💥 LA LIGNE MAGIQUE POUR CORRIGER LE CRASH :
    return total_eleves, eleves_actifs, eleves_sortis, nb_diplomes


def _stats_repartition_classes():
    """
    Calcule la répartition des élèves actifs par classe
    et le nombre d'inscriptions par année scolaire.
    Retourne (eleves_par_classe_data, inscriptions_data).
    """
    classes_qs = Classe.objects.annotate(
        nb=Count('eleves', filter=Q(eleves__type_utilisateur='eleve', eleves__compte_approuve=True, eleves__est_sorti=False))
    ).filter(nb__gt=0).order_by('-nb')
    eleves_par_classe_data = [{'nom': c.nom, 'nb': c.nb} for c in classes_qs]

    inscriptions_qs = ProfilUtilisateur.objects.filter(type_utilisateur='eleve', compte_approuve=True)\
        .exclude(annee_entree__isnull=True).exclude(annee_entree='')\
        .values('annee_entree').annotate(nb=Count('id')).order_by('annee_entree')
    inscriptions_data = [{'annee': i['annee_entree'], 'nb': i['nb']} for i in inscriptions_qs]

    return eleves_par_classe_data, inscriptions_data


def _stats_etablissements_raisons_niveaux():
    """
    Calcule le top des établissements d'origine, les raisons de sortie
    et la répartition par niveau.
    Retourne (top_etablissements_data, raisons_data, niveaux_data).
    """
    etab_qs = ProfilUtilisateur.objects.filter(type_utilisateur='eleve', compte_approuve=True, etablissement_origine__isnull=False)\
        .values('etablissement_origine__nom').annotate(nb=Count('id')).order_by('-nb')[:5]
    top_etablissements_data = [{'nom': e['etablissement_origine__nom'] or 'Inconnu', 'nb': e['nb']} for e in etab_qs]

    raison_labels = dict(ProfilUtilisateur.RAISON_SORTIE)
    raison_qs = ProfilUtilisateur.objects.filter(type_utilisateur='eleve', est_sorti=True)\
        .exclude(raison_sortie='').exclude(raison_sortie__isnull=True)\
        .values('raison_sortie').annotate(nb=Count('id')).order_by('-nb')
    raisons_data = [{'type': raison_labels.get(r['raison_sortie'], r['raison_sortie']), 'nb': r['nb']} for r in raison_qs]

    niveaux_qs = Niveau.objects.annotate(
        nb=Count('classes__eleves', filter=Q(
            classes__eleves__type_utilisateur='eleve',
            classes__eleves__compte_approuve=True, classes__eleves__est_sorti=False
        ))
    ).filter(nb__gt=0).order_by('nom')
    niveaux_data = [{'mention': n.get_nom_display(), 'nb': n.nb} for n in niveaux_qs]

    return top_etablissements_data, raisons_data, niveaux_data


def _stats_ages_par_classe(today):
    """
    Calcule l'âge moyen des élèves actifs par classe (avec gestion des anniversaires).
    Retourne ages_data liste de dicts {classe, age_moyen}.
    """
    ages_data = []
    for classe in Classe.objects.all().order_by('nom'):
        eleves_avec_dn = ProfilUtilisateur.objects.filter(
            classe=classe, type_utilisateur='eleve', compte_approuve=True,
            est_sorti=False, date_naissance__isnull=False)
        if eleves_avec_dn.exists():
            ages = []
            for e in eleves_avec_dn:
                try:
                    dn = e.date_naissance
                    age = today.year - dn.year
                    if (today.month, today.day) < (dn.month, dn.day):
                        age -= 1
                    ages.append(age)
                except Exception:
                    pass
            if ages:
                ages_data.append({'classe': classe.nom, 'age_moyen': round(sum(ages) / len(ages), 1)})
    return ages_data


def _stats_rendus_travaux():
    """
    Calcule le total de rendus attendus vs effectifs pour tous les travaux actifs.
    Retourne travaux_data dict {rendus, manquants}.
    """
    total_attendus = 0
    rendus_count = 0
    for travail in TravailARendre.objects.filter(actif=True).select_related('classe'):
        nb_eleves_classe = ProfilUtilisateur.objects.filter(
            classe=travail.classe, type_utilisateur='eleve', compte_approuve=True, est_sorti=False).count()
        total_attendus += nb_eleves_classe
        rendus_count += RenduEleve.objects.filter(travail=travail, rendu=True).count()
    return {'rendus': rendus_count, 'manquants': max(0, total_attendus - rendus_count)}


def _stats_taux_rendu_par_classe():
    """
    Pour chaque classe ayant des travaux actifs, calcule le taux de rendu (%).
    Retourne liste de dicts {classe, nb_travaux, nb_eleves, nb_rendus, nb_attendus, taux}.
    """
    from core.models import Classe as ClasModel
    result = []
    for classe in ClasModel.objects.all().order_by('nom'):
        travaux = TravailARendre.objects.filter(classe=classe, actif=True)
        nb_travaux = travaux.count()
        if nb_travaux == 0:
            continue
        nb_eleves = ProfilUtilisateur.objects.filter(
            classe=classe, type_utilisateur='eleve', compte_approuve=True, est_sorti=False
        ).count()
        if nb_eleves == 0:
            continue
        nb_attendus = nb_eleves * nb_travaux
        nb_rendus = RenduEleve.objects.filter(travail__in=travaux, rendu=True).count()
        taux = round(nb_rendus * 100 / nb_attendus, 1) if nb_attendus > 0 else 0
        result.append({
            'classe': classe.nom,
            'nb_travaux': nb_travaux,
            'nb_eleves': nb_eleves,
            'nb_rendus': nb_rendus,
            'nb_attendus': nb_attendus,
            'taux': taux,
        })
    return result


def _stats_notes_par_travail():
    """
    Pour chaque travail actif ayant des rendus notés, calcule la note moyenne.
    Retourne liste de dicts {titre, classe, nb_notes, note_moy}.
    """
    from django.db.models import Avg
    result = []
    for travail in TravailARendre.objects.filter(actif=True).select_related('classe').order_by('classe__nom', 'titre'):
        agg = RenduEleve.objects.filter(travail=travail, rendu=True, note__isnull=False).aggregate(
            moy=Avg('note'), nb=Count('id')
        )
        nb_notes = agg['nb'] or 0
        moy = round(agg['moy'], 1) if agg['moy'] is not None else None
        result.append({
            'titre': travail.titre,
            'classe': travail.classe.nom if travail.classe else '—',
            'nb_notes': nb_notes,
            'note_moy': moy,
        })
    return result


def _stats_eleves_a_risque():
    """
    Élèves actifs avec 0 connexion ET 0 rendu.
    Retourne liste de dicts {nom, prenom, classe}.
    """
    from core.models import ConnexionEleve
    eleves = ProfilUtilisateur.objects.filter(
        type_utilisateur='eleve', compte_approuve=True, est_sorti=False
    ).select_related('user', 'classe')
    result = []
    for eleve in eleves:
        nb_cx = ConnexionEleve.objects.filter(user=eleve.user).count()
        nb_rendus = RenduEleve.objects.filter(eleve=eleve, rendu=True).count()
        if nb_cx == 0 and nb_rendus == 0:
            result.append({
                'nom': eleve.user.last_name.upper(),
                'prenom': eleve.user.first_name,
                'classe': eleve.classe.nom if eleve.classe else '—',
            })
    result.sort(key=lambda x: (x['classe'], x['nom']))
    return result


def _stats_connexions_30j():
    """
    Nombre de connexions par jour sur les 30 derniers jours (pour courbe).
    Retourne liste de dicts {date, nb} triée chronologiquement.
    """
    from core.models import ConnexionEleve
    from django.db.models.functions import TruncDate
    today = date.today()
    start = today - timedelta(days=29)
    qs = ConnexionEleve.objects.filter(horodatage__date__gte=start)\
        .annotate(jour=TruncDate('horodatage'))\
        .values('jour').annotate(nb=Count('id')).order_by('jour')
    data = {(start + timedelta(days=i)).isoformat(): 0 for i in range(30)}
    for row in qs:
        data[row['jour'].isoformat()] = row['nb']
    return [{'date': k, 'nb': v} for k, v in sorted(data.items())]


def _stats_sorties_par_annee():
    """
    Calcule le nombre de sorties d'élèves par année.
    Retourne sorties_data liste de dicts {annee, nb}.
    """
    sorties_qs = ProfilUtilisateur.objects.filter(type_utilisateur='eleve', est_sorti=True, date_sortie__isnull=False)\
        .annotate(annee=ExtractYear('date_sortie')).values('annee').annotate(nb=Count('id')).order_by('annee')
    return [{'annee': str(s['annee']), 'nb': s['nb']} for s in sorties_qs if s['annee']]


def _stats_connexions():
    """
    Retourne les stats de connexion des élèves :
    - liste par élève : nb total de connexions + dernière connexion + jours distincts
    - jamais connectés
    """
    from core.models import ConnexionEleve
    from django.db.models.functions import TruncDate
    from django.db.models import Count as DjCount
    eleves = ProfilUtilisateur.objects.filter(
        type_utilisateur='eleve', compte_approuve=True, est_sorti=False
    ).select_related('user').order_by('user__last_name', 'user__first_name')

    data = []
    for eleve in eleves:
        nb = ConnexionEleve.objects.filter(user=eleve.user).count()
        derniere = ConnexionEleve.objects.filter(user=eleve.user).order_by('-horodatage').first()
        nb_jours = ConnexionEleve.objects.filter(user=eleve.user)\
            .annotate(jour=TruncDate('horodatage'))\
            .values('jour').distinct().count()
        data.append({
            'nom': eleve.user.last_name.upper(),
            'prenom': eleve.user.first_name,
            'classe': eleve.classe.nom if eleve.classe else '—',
            'nb_connexions': nb,
            'nb_jours_actifs': nb_jours,
            'derniere': derniere.horodatage.strftime('%d/%m/%Y %H:%M') if derniere else None,
        })
    data.sort(key=lambda x: -x['nb_connexions'])
    return data



    """
    Retourne QUATRE listes d'élèves sortis catégorisés :
    - sorties_decrocheurs    : décrocheurs, exclus, échecs, décès, sans emploi
    - sorties_diplomes       : diplômes obtenus
    - sorties_post_formation : post-formation (poursuite BTS/Bac, travail)
    - sorties_reorientation  : orientation AFB, réorientation interne/externe
    """
    LABELS = dict(ProfilUtilisateur.RAISON_SORTIE)
    
    # Nouvelles catégories strictes
    DIPLOMES = {'cap_mention', 'cap_sans_mention', 'bac_pro_mention', 'bac_pro_sans_mention'}
    DECROCHEURS = {'decrocheur', 'exclusion', 'echec_cap', 'echec_bac_pro', 'deces', 'raison_inconnue', 'sans_emploi'}
    REORIENTATIONS = {'reorientation_interne', 'reorientation_externe', 'orientation_afb', 'retour_pays'}
    # Tout ce qui n'est pas dans ces 3 listes sera considéré comme "Post-formation" (travail, bts, etc.)

    sortis = ProfilUtilisateur.objects.filter(
        type_utilisateur='eleve', est_sorti=True
    ).select_related('user', 'classe', 'etablissement_origine').order_by('-date_sortie', 'user__last_name')

    MENTION_LABELS = {'AB': 'Assez Bien', 'B': 'Bien', 'TB': 'Très Bien'}

    decrocheurs, diplomes, post_formation, reorientations = [], [], [], []
    
    for p in sortis:
        r = p.raison_sortie or ''
        etab_orig = p.etablissement_origine.nom if p.etablissement_origine else getattr(p, 'etablissement_origine_autre', '')
        
        entry = {
            'nom': p.user.last_name.upper(),
            'prenom': p.user.first_name,
            'classe': p.classe.nom if p.classe else '—',
            'annee': p.annee_scolaire_sortie or '—',
            'raison': LABELS.get(r, r or '—'),
            'commentaire': getattr(p, 'commentaire_sortie', '') or '',
            'mention': MENTION_LABELS.get(getattr(p, 'mention_obtenue', '') or '', ''),
            'etablissement_orig': etab_orig or 'Non renseigné',
        }
        
        if r in DIPLOMES:
            diplomes.append(entry)
        elif r in REORIENTATIONS:
            reorientations.append(entry)
        elif r in DECROCHEURS:
            decrocheurs.append(entry)
        else: # Post-formation
            post_formation.append(entry)

    return decrocheurs, diplomes, post_formation, reorientations


def _stats_sorties_detail():
    """Retourne 4 listes catégorisées pour les statistiques."""
    LABELS = dict(ProfilUtilisateur.RAISON_SORTIE)
    DIPLOMES = {'cap_mention', 'cap_sans_mention', 'bac_pro_mention', 'bac_pro_sans_mention'}
    DECROCHEURS = {'decrocheur', 'exclusion', 'echec_cap', 'echec_bac_pro', 'deces', 'raison_inconnue', 'sans_emploi'}
    REORIENTATIONS = {'reorientation_interne', 'reorientation_externe', 'orientation_afb', 'retour_pays'}

    sortis = ProfilUtilisateur.objects.filter(type_utilisateur='eleve', est_sorti=True).select_related('user', 'classe', 'etablissement_origine').order_by('-date_sortie', 'user__last_name')
    MENTION_LABELS = {'AB': 'Assez Bien', 'B': 'Bien', 'TB': 'Très Bien'}

    decrocheurs, diplomes, post_formation, reorientations = [], [], [], []
    
    for p in sortis:
        r = p.raison_sortie or ''
        etab_orig = p.etablissement_origine.nom if p.etablissement_origine else getattr(p, 'etablissement_origine_autre', '')
        entry = {
            'nom': p.user.last_name.upper(),
            'prenom': p.user.first_name,
            'classe': p.classe.nom if p.classe else '—',
            'annee': p.annee_scolaire_sortie or '—',
            'raison': LABELS.get(r, r or '—'),
            'commentaire': getattr(p, 'commentaire_sortie', '') or '',
            'mention': MENTION_LABELS.get(getattr(p, 'mention_obtenue', '') or '', ''),
            'etablissement_orig': etab_orig or 'Non renseigné',
        }
        if r in DIPLOMES: diplomes.append(entry)
        elif r in REORIENTATIONS: reorientations.append(entry)
        elif r in DECROCHEURS: decrocheurs.append(entry)
        else: post_formation.append(entry)

    return decrocheurs, diplomes, post_formation, reorientations


def _stats_sorties_charts():
    """
    Retourne les données pour les graphiques de suivi des sorties.
    """
    from core.models import ProfilUtilisateur
    
    DECROCHEURS = {'decrocheur', 'exclusion', 'echec_cap', 'echec_bac_pro', 'deces', 'raison_inconnue', 'sans_emploi'}
    DIPLOMES = {'cap_mention', 'cap_sans_mention', 'bac_pro_mention', 'bac_pro_sans_mention'}

    sortis = ProfilUtilisateur.objects.filter(
        type_utilisateur='eleve', est_sorti=True, date_sortie__isnull=False
    ).values('raison_sortie', 'annee_scolaire_sortie')

    dec_by_year = {}
    dipl_by_year = {}
    postform_totals = {}

    POSTFORM_LABELS = {
        'poursuite_bac_pro': 'Poursuite Bac Pro',
        'poursuite_bts': 'Poursuite BTS',
        'poursuite_autre': "Autre poursuite",
        'travail_formation': 'Travaille (formation)',
        'travail_hors_formation': 'Travaille (autre)',
        'apprentissage': 'Apprentissage',
        'reorientation_interne': 'Réorientation',
        'reorientation_externe': 'Réorientation',
        'orientation_afb': '1ère AFB',
    }

    for s in sortis:
        r = s['raison_sortie'] or ''
        annee = s['annee_scolaire_sortie'] or 'Inconnue'
        
        if r in DECROCHEURS:
            dec_by_year[annee] = dec_by_year.get(annee, 0) + 1
        elif r in DIPLOMES:
            if annee not in dipl_by_year:
                dipl_by_year[annee] = {'cap_mention': 0, 'cap_sans': 0, 'bp_mention': 0, 'bp_sans': 0}
            if r == 'cap_mention':        dipl_by_year[annee]['cap_mention'] += 1
            elif r == 'cap_sans_mention': dipl_by_year[annee]['cap_sans'] += 1
            elif r == 'bac_pro_mention':  dipl_by_year[annee]['bp_mention'] += 1
            elif r == 'bac_pro_sans_mention': dipl_by_year[annee]['bp_sans'] += 1
        elif r in POSTFORM_LABELS:
            lbl = POSTFORM_LABELS[r]
            postform_totals[lbl] = postform_totals.get(lbl, 0) + 1

    all_years = sorted(set(list(dec_by_year.keys()) + list(dipl_by_year.keys())))

    decrocheurs_par_annee = [{'annee': y, 'nb': dec_by_year.get(y, 0)} for y in all_years]
    diplomes_par_annee    = [{'annee': y,
                              'cap_mention': dipl_by_year.get(y, {}).get('cap_mention', 0),
                              'cap_sans':    dipl_by_year.get(y, {}).get('cap_sans', 0),
                              'bp_mention':  dipl_by_year.get(y, {}).get('bp_mention', 0),
                              'bp_sans':     dipl_by_year.get(y, {}).get('bp_sans', 0)}
                             for y in all_years]
    postformation_cats    = [{'label': k, 'nb': v} for k, v in sorted(postform_totals.items(), key=lambda x: -x[1])]

    return decrocheurs_par_annee, diplomes_par_annee, postformation_cats


def _stats_sortis_enriched():
    """
    Stats enrichies sur les sortis :
    - annees                 : liste des années scolaires disponibles (tri desc)
    - top_etabs_diplomes_json: top établissements d'origine des diplômés [{nom, nb}]
    - poursuite_json         : [{label, nb}] Bac Pro / BTS poursuite
    """
    DIPLOMES = {'cap_mention', 'cap_sans_mention', 'bac_pro_mention', 'bac_pro_sans_mention'}
    sortis = ProfilUtilisateur.objects.filter(
        type_utilisateur='eleve', est_sorti=True
    ).select_related('etablissement_origine')

    annees = sorted(
        {p.annee_scolaire_sortie for p in sortis if p.annee_scolaire_sortie},
        reverse=True
    )

    # Top collèges / lycées d'origine parmi les diplômés
    etabs = {}
    for p in sortis:
        if p.raison_sortie not in DIPLOMES:
            continue
        nom = (
            p.etablissement_origine.nom
            if p.etablissement_origine
            else getattr(p, 'etablissement_origine_autre', '') or 'Non renseigné'
        )
        etabs[nom] = etabs.get(nom, 0) + 1
    top_etabs_json = [
        {'nom': k, 'nb': v}
        for k, v in sorted(etabs.items(), key=lambda x: -x[1])[:10]
    ]

    # Répartition poursuite (Bac Pro après CAP / BTS après Bac Pro)
    poursuite_bac = sum(
        1 for p in sortis
        if p.raison_sortie == 'poursuite_bac_pro'
        or getattr(p, 'type_poursuite', '') == 'bac_pro'
    )
    poursuite_bts = sum(
        1 for p in sortis
        if p.raison_sortie == 'poursuite_bts'
        or getattr(p, 'type_poursuite', '') == 'bts'
    )
    poursuite_json = [
        {'label': 'Poursuite Bac Pro', 'nb': poursuite_bac},
        {'label': 'Poursuite BTS',     'nb': poursuite_bts},
    ]

    return annees, top_etabs_json, poursuite_json


def _stats_pfmp():
    """
    Pour chaque classe ayant des PFMP, retourne par élève et par PFMP
    les jours effectués / manqués (justifiés + injustifiés).
    Retourne : liste de dicts {classe, pfmps, eleves_suivis} par classe.
    """
    from django.db.models import Sum
    result = []
    for classe in Classe.objects.order_by('nom'):
        pfmps = list(PFMP.objects.filter(classes=classe, actif=True).order_by('date_debut'))
        if not pfmps:
            continue
        eleves = list(ProfilUtilisateur.objects.filter(
            classe=classe, type_utilisateur='eleve', compte_approuve=True, est_sorti=False
        ).select_related('user').order_by('user__last_name', 'user__first_name'))
        if not eleves:
            continue

        # pré-charger tous les suivis pour cette classe d'un coup
        suivis = {
            (s.pfmp_id, s.eleve_id): s
            for s in SuiviPFMP.objects.filter(pfmp__in=pfmps, eleve__in=eleves)
        }

        eleves_data = []
        for eleve in eleves:
            ligne = {
                'nom': eleve.user.last_name.upper(),
                'prenom': eleve.user.first_name,
                'suivis': [],
                'total_effectues': 0,
                'total_justifies': 0,
                'total_injustifies': 0,
            }
            for pfmp in pfmps:
                s = suivis.get((pfmp.id, eleve.id))
                if s:
                    ligne['suivis'].append({
                        'pfmp_id': pfmp.id,
                        'effectues': s.nb_jours_effectues,
                        'justifies': s.nb_jours_manques_justifies,
                        'injustifies': s.nb_jours_manques_injustifies,
                        'total': s.nb_jours_total,
                        'taux': s.taux_presence,
                    })
                    ligne['total_effectues'] += s.nb_jours_effectues
                    ligne['total_justifies'] += s.nb_jours_manques_justifies
                    ligne['total_injustifies'] += s.nb_jours_manques_injustifies
                else:
                    ligne['suivis'].append(None)
            eleves_data.append(ligne)

        result.append({
            'classe': classe.nom,
            'pfmps': [{'id': p.id, 'titre': p.titre} for p in pfmps],
            'eleves': eleves_data,
        })
    return result


def _stats_profil_origine():
    """
    Corrélations entre le profil d'entrée de l'élève et ses résultats à la sortie.
    Retourne 4 listes : par collège, par classe d'origine, par diplôme d'entrée, par ville.
    Chaque entrée : {label, total, diplomes, mention, decrocheurs, taux_reussite}
    """
    DIPLOMES    = {'cap_mention', 'cap_sans_mention', 'bac_pro_mention', 'bac_pro_sans_mention'}
    MENTIONS    = {'cap_mention', 'bac_pro_mention'}
    DECROCHEURS = {'decrocheur', 'echec_cap', 'echec_bac_pro', 'exclusion'}

    sortis = ProfilUtilisateur.objects.filter(
        type_utilisateur='eleve', est_sorti=True
    ).select_related('etablissement_origine')

    def agréger(keyfn):
        data = {}
        for p in sortis:
            key = keyfn(p) or 'Non renseigné'
            if key not in data:
                data[key] = {'total': 0, 'diplomes': 0, 'mention': 0, 'decrocheurs': 0}
            data[key]['total'] += 1
            if p.raison_sortie in DIPLOMES:    data[key]['diplomes'] += 1
            if p.raison_sortie in MENTIONS:    data[key]['mention'] += 1
            if p.raison_sortie in DECROCHEURS: data[key]['decrocheurs'] += 1
        result = []
        for k, v in sorted(data.items(), key=lambda x: -x[1]['total']):
            t = v['total']
            result.append({
                'label':          k,
                'total':          t,
                'diplomes':       v['diplomes'],
                'mention':        v['mention'],
                'decrocheurs':    v['decrocheurs'],
                'taux_reussite':  round(v['diplomes'] / t * 100) if t else 0,
                'taux_decroch':   round(v['decrocheurs'] / t * 100) if t else 0,
                'taux_mention':   round(v['mention'] / v['diplomes'] * 100) if v['diplomes'] else 0,
            })
        # Ajouter les couleurs calculées en Python (évite les {% if %} dans style="")
        for row in result:
            tr = row['taux_reussite']
            if tr >= 70:
                row['barre_color'] = '#10b981'; row['texte_color'] = '#059669'
            elif tr >= 40:
                row['barre_color'] = '#f59e0b'; row['texte_color'] = '#d97706'
            else:
                row['barre_color'] = '#e74c3c'; row['texte_color'] = '#dc2626'
        return result

    par_college       = agréger(lambda p: (
        p.etablissement_origine.nom if p.etablissement_origine else p.etablissement_origine_autre or None
    ))
    par_classe_orig   = agréger(lambda p: p.classe_origine or None)
    par_diplome_entre = agréger(lambda p: p.diplome_obtenu or None)
    par_ville         = agréger(lambda p: p.etablissement_origine_autre or None)

    return par_college, par_classe_orig, par_diplome_entre, par_ville


def statistiques(request):
    today = date.today()

    total_eleves, eleves_actifs, eleves_sortis, nb_diplomes = _stats_compteurs_eleves()
    eleves_par_classe_data, inscriptions_data               = _stats_repartition_classes()
    top_etablissements_data, raisons_data, niveaux_data     = _stats_etablissements_raisons_niveaux()
    ages_data    = _stats_ages_par_classe(today)
    sorties_data = _stats_sorties_par_annee()
    connexions_data = _stats_connexions()
    decrocheurs_data, diplomes_data, postformation_data, reorientation_data = _stats_sorties_detail()
    dec_annee_data, dipl_annee_data, postform_cats_data = _stats_sorties_charts()
    taux_rendu_data    = _stats_taux_rendu_par_classe()
    notes_travaux_data = _stats_notes_par_travail()
    eleves_risque_data = _stats_eleves_a_risque()
    connexions_30j     = _stats_connexions_30j()
    pfmp_stats         = _stats_pfmp()
    annees_sortis, top_etabs_diplomes_json, poursuite_json = _stats_sortis_enriched()
    orig_college, orig_classe, orig_diplome, orig_ville = _stats_profil_origine()
    # gender stats
    nb_garcons = ProfilUtilisateur.objects.filter(type_utilisateur='eleve', compte_approuve=True, est_sorti=False, sexe='M').count()
    nb_filles  = ProfilUtilisateur.objects.filter(type_utilisateur='eleve', compte_approuve=True, est_sorti=False, sexe='F').count()
    total_gender = nb_garcons + nb_filles
    pc_garcons = f"{nb_garcons*100/total_gender:.0f}" if total_gender else '0'
    pc_filles  = f"{nb_filles*100/total_gender:.0f}" if total_gender else '0'

    # Statistiques spécifiques Seconde Pro (niveau Bac Pro)
    bacpro_active_qs = ProfilUtilisateur.objects.filter(
        type_utilisateur='eleve', classe__niveau__nom='BAC_PRO', compte_approuve=True, est_sorti=False
    )
    bacpro_sortis_qs = ProfilUtilisateur.objects.filter(
        type_utilisateur='eleve', classe__niveau__nom='BAC_PRO', est_sorti=True
    )
    inscrits_bacpro = bacpro_active_qs.count()
    abandons_bacpro = bacpro_sortis_qs.filter(raison_sortie='decrocheur').count()
    reorientation_interne_bacpro = bacpro_sortis_qs.filter(raison_sortie='reorientation_interne').count()
    reorientation_externe_bacpro = bacpro_sortis_qs.filter(raison_sortie='reorientation_externe').count()
    passage_afb_bacpro = bacpro_active_qs.filter(parcours='AFB').count()
    passage_orgo_bacpro = bacpro_active_qs.filter(parcours='ORGO').count()

    # Détail par classe pour la Seconde Pro
    bacpro_by_class = {}
    for c in Classe.objects.filter(niveau__nom='BAC_PRO').order_by('nom'):
        inscrit = ProfilUtilisateur.objects.filter(classe=c, type_utilisateur='eleve', compte_approuve=True, est_sorti=False).count()
        aband = ProfilUtilisateur.objects.filter(classe=c, type_utilisateur='eleve', est_sorti=True, raison_sortie='decrocheur').count()
        reint = ProfilUtilisateur.objects.filter(classe=c, type_utilisateur='eleve', est_sorti=True, raison_sortie='reorientation_interne').count()
        reext = ProfilUtilisateur.objects.filter(classe=c, type_utilisateur='eleve', est_sorti=True, raison_sortie='reorientation_externe').count()
        afb = ProfilUtilisateur.objects.filter(classe=c, parcours='AFB', type_utilisateur='eleve', est_sorti=False).count()
        orgo = ProfilUtilisateur.objects.filter(classe=c, parcours='ORGO', type_utilisateur='eleve', est_sorti=False).count()
        bacpro_by_class[c.nom] = {'inscrits': inscrit, 'abandons': aband, 'reint': reint, 'reext': reext, 'afb': afb, 'orgo': orgo}

    context = {
        'total_eleves': total_eleves, 'eleves_actifs': eleves_actifs,
        'eleves_sortis': eleves_sortis, 'diplomes': nb_diplomes,
        'eleves_par_classe_json': eleves_par_classe_data,
        'inscriptions_par_annee_json': inscriptions_data,
        'top_etablissements_json': top_etablissements_data,
        'diplomes_par_type_json': raisons_data,
        'niveaux_json': niveaux_data,
        'ages_par_classe_json': ages_data,
        'abandons_par_annee_json': sorties_data,
        'connexions_eleves': connexions_data,
        'nb_jamais_connectes': sum(1 for c in connexions_data if c['nb_connexions'] == 0),
        'sorties_decrocheurs': decrocheurs_data,
        'sorties_diplomes': diplomes_data,
        'sorties_post_formation': postformation_data,
        'sorties_reorientation': reorientation_data,
        'decrocheurs_par_annee_json': dec_annee_data,
        'diplomes_par_annee_json': dipl_annee_data,
        'postformation_cats_json': postform_cats_data,
        'taux_rendu_data': taux_rendu_data,
        'taux_rendu_json': [{'classe': d['classe'], 'taux': d['taux']} for d in taux_rendu_data],
        'notes_travaux_data': notes_travaux_data,
        'eleves_risque_data': eleves_risque_data,
        'connexions_30j_json': connexions_30j,
        'pfmp_stats': pfmp_stats,
        # Stats sortis enrichies
        'annees_sortis': annees_sortis,
        'top_etabs_diplomes_json': top_etabs_diplomes_json,
        'poursuite_json': poursuite_json,
        # Corrélations profil d'origine → résultats
        'orig_college':       orig_college,
        'orig_classe':        orig_classe,
        'orig_diplome':       orig_diplome,
        'orig_ville':         orig_ville,
        'orig_college_json':  json.dumps(orig_college,  ensure_ascii=False),
        # gender metrics
        'nb_garcons': nb_garcons,
        'nb_filles': nb_filles,
        'pc_garcons': pc_garcons,
        'pc_filles': pc_filles,
        # Seconde Pro (camembert + détail par classe)
        'inscrits_bacpro': inscrits_bacpro,
        'abandons_bacpro': abandons_bacpro,
        'reorientation_interne_bacpro': reorientation_interne_bacpro,
        'reorientation_externe_bacpro': reorientation_externe_bacpro,
        'passage_afb_bacpro': passage_afb_bacpro,
        'passage_orgo_bacpro': passage_orgo_bacpro,
        'bacpro_by_class': bacpro_by_class,
        'orig_classe_json':   json.dumps(orig_classe,   ensure_ascii=False),
        'orig_diplome_json':  json.dumps(orig_diplome,  ensure_ascii=False),
        'orig_ville_json':    json.dumps(orig_ville,    ensure_ascii=False),
    }
    return render(request, 'core/statistiques.html', context)


def gestion_ateliers(request):
    ateliers = Atelier.objects.filter(actif=True).select_related('classe').order_by('classe__nom', 'ordre')
    classe_id = request.GET.get('classe')
    if classe_id:
        ateliers = ateliers.filter(classe_id=classe_id)
    return render(request, 'core/gestion_ateliers.html', {
        'ateliers': ateliers,
        'classes': Classe.objects.all(),
        'classe_selectionnee': classe_id,
    })


def atelier_create(request):
    if request.method == 'POST':
        titre = request.POST.get('titre')
        classe_id = request.POST.get('classe')
        if not titre or not classe_id:
            messages.error(request, '❌ Le titre et la classe sont obligatoires.')
            return render(request, 'core/atelier_create.html', {'classes': Classe.objects.all().order_by('nom')})
        atelier = Atelier.objects.create(
            titre=titre, classe=Classe.objects.get(id=classe_id),
            description=request.POST.get('description', ''),
            visible_eleves=request.POST.get('visible_eleves') == 'on',
            ordre=request.POST.get('ordre', 0)
        )
        messages.success(request, f'✅ Atelier "{atelier.titre}" créé !')
        dossier = None
        if request.POST.get('creer_dossier') == 'on':
            dossier_nom = request.POST.get('dossier_nom', '').strip()
            if dossier_nom:
                dossier = DossierAtelier.objects.create(
                    atelier=atelier, nom=dossier_nom,
                    ordre=request.POST.get('dossier_ordre', 0),
                    visible_eleves=request.POST.get('dossier_visible') == 'on'
                )
                messages.success(request, f'📂 Dossier "{dossier.nom}" créé !')
        if dossier and request.POST.get('ajouter_fichier') == 'on':
            fichier_nom = request.POST.get('fichier_nom', '').strip()
            type_contenu = request.POST.get('type_fichier', 'fichier')
            if fichier_nom:
                fichier = FichierAtelier.objects.create(
                    dossier=dossier, nom=fichier_nom, type_contenu=type_contenu, ordre=0, createur=request.user)
                if type_contenu == 'fichier' and request.FILES.get('fichier_upload'):
                    fichier.fichier = request.FILES['fichier_upload']
                elif type_contenu == 'lien':
                    fichier.lien_externe = request.POST.get('fichier_lien', '').strip()
                elif type_contenu == 'iframe':
                    fichier.code_iframe = request.POST.get('fichier_iframe', '').strip()
                fichier.save()
                messages.success(request, f'📄 Ressource "{fichier.nom}" ajoutée !')
        return redirect('core:atelier_detail', pk=atelier.id)
    return render(request, 'core/atelier_create.html', {'classes': Classe.objects.all().order_by('nom')})


def atelier_detail(request, pk):
    atelier = get_object_or_404(Atelier, pk=pk)
    is_eleve = hasattr(request.user, 'profil') and request.user.profil.est_eleve()
    if is_eleve:
        if atelier.classe != request.user.profil.classe:
            messages.error(request, "❌ Vous n'avez pas accès à cet atelier.")
            return redirect('core:dashboard_eleve')
        dossiers = DossierAtelier.objects.filter(atelier=atelier, actif=True, visible_eleves=True).order_by('ordre', 'nom')
    else:
        dossiers = DossierAtelier.objects.filter(atelier=atelier).order_by('ordre', 'nom')
    dossiers_avec_fichiers = []
    for dossier in dossiers:
        fichiers = FichierAtelier.objects.filter(dossier=dossier, actif=True if is_eleve else dossier.actif).order_by('ordre', 'nom')
        dossiers_avec_fichiers.append({'dossier': dossier, 'fichiers': fichiers})
    nb_eleves = ProfilUtilisateur.objects.filter(
        classe=atelier.classe, type_utilisateur='eleve', compte_approuve=True, est_sorti=False).count()
    modes_operatoires = ModeOperatoire.objects.filter(
        atelier=atelier, actif=True,
        **({'visible_eleves': True} if is_eleve else {})
    ).order_by('-date_creation')
    return render(request, 'core/atelier_detail.html', {
        'atelier': atelier, 'dossiers_avec_fichiers': dossiers_avec_fichiers,
        'nb_eleves': nb_eleves, 'is_eleve': is_eleve,
        'modes_operatoires': modes_operatoires,
    })


def atelier_fichier_download(request, pk):
    fichier = get_object_or_404(FichierAtelier, pk=pk)
    is_eleve = hasattr(request.user, 'profil') and request.user.profil.est_eleve()
    # Permission checks for élèves
    if is_eleve:
        if not fichier.visible_eleves or fichier.dossier.atelier.classe != request.user.profil.classe:
            messages.error(request, "❌ Vous n'avez pas accès à ce fichier.")
            return redirect('core:atelier_detail', pk=fichier.dossier.atelier.id)

    # External link
    if fichier.type_contenu == 'lien' and fichier.lien_externe:
        return redirect(fichier.lien_externe)

    # Iframe: redirect back to detail (iframe is displayed in page)
    if fichier.type_contenu == 'iframe' and fichier.code_iframe:
        return redirect('core:atelier_detail', pk=fichier.dossier.atelier.id)

    # File stored in storage
    if fichier.type_contenu == 'fichier' and fichier.fichier:
        storage = fichier.fichier.storage
        name = fichier.fichier.name
        try:
            if hasattr(storage, 'url'):
                url = storage.url(name)
                return redirect(url)
            else:
                # Fallback: try local MEDIA_ROOT
                file_path = os.path.join(settings.MEDIA_ROOT, name)
                if os.path.exists(file_path):
                    return FileResponse(open(file_path, 'rb'), as_attachment=True, filename=os.path.basename(name))
                messages.error(request, "❌ Fichier introuvable sur le serveur.")
                return redirect('core:atelier_detail', pk=fichier.dossier.atelier.id)
        except Exception:
            messages.error(request, "❌ Impossible d'accéder au fichier.")
            return redirect('core:atelier_detail', pk=fichier.dossier.atelier.id)

    messages.error(request, "❌ Fichier invalide.")
    return redirect('core:atelier_detail', pk=fichier.dossier.atelier.id)


def atelier_update(request, pk):
    atelier = get_object_or_404(Atelier, id=pk)
    if request.method == 'POST':
        atelier.titre = request.POST.get('titre')
        atelier.description = request.POST.get('description', '')
        atelier.visible_eleves = request.POST.get('visible_eleves') == 'on'
        # Permettre de changer la classe associée à l'atelier
        classe_id = request.POST.get('classe')
        if classe_id:
            try:
                atelier.classe = Classe.objects.get(id=classe_id)
            except Classe.DoesNotExist:
                pass
        atelier.save()
        messages.success(request, '✅ Atelier modifié !')
        return redirect('core:gestion_ateliers')
    return render(request, 'core/atelier_update.html', {'atelier': atelier, 'classes': Classe.objects.all()})


def atelier_delete(request, pk):
    if request.method == 'POST':
        get_object_or_404(Atelier, id=pk).delete()
        messages.success(request, '✅ Atelier supprimé !')
    return redirect('core:gestion_ateliers')


def atelier_toggle_visibilite(request, pk):
    atelier = get_object_or_404(Atelier, pk=pk)
    atelier.visible_eleves = not atelier.visible_eleves
    atelier.save()
    return redirect('core:gestion_ateliers')


def atelier_dossier_toggle_visibilite(request, pk):
    dossier = get_object_or_404(DossierAtelier, pk=pk)
    dossier.visible_eleves = not dossier.visible_eleves
    dossier.save()
    return redirect('core:atelier_detail', pk=dossier.atelier.id)


def atelier_fichier_toggle_visibilite(request, pk):
    fichier = get_object_or_404(FichierAtelier, pk=pk)
    fichier.visible_eleves = not fichier.visible_eleves
    fichier.save()
    return redirect('core:atelier_detail', pk=fichier.dossier.atelier.id)


def atelier_dossier_create(request, atelier_id):
    atelier = get_object_or_404(Atelier, id=atelier_id)
    if request.method == 'POST':
        DossierAtelier.objects.create(
            atelier=atelier, nom=request.POST.get('nom'),
            description=request.POST.get('description', ''),
            ordre=request.POST.get('ordre', 0),
            visible_eleves=request.POST.get('visible_eleves') == 'on'
        )
        messages.success(request, '✅ Dossier créé !')
        return redirect('core:atelier_detail', pk=atelier_id)
    return render(request, 'core/atelier_dossier_create.html', {'atelier': atelier})


def atelier_dossier_update(request, pk):
    dossier = get_object_or_404(DossierAtelier, id=pk)
    if request.method == 'POST':
        dossier.nom = request.POST.get('nom')
        dossier.description = request.POST.get('description', '')
        dossier.ordre = request.POST.get('ordre', 0)
        dossier.visible_eleves = request.POST.get('visible_eleves') == 'on'
        dossier.save()
        messages.success(request, '✅ Dossier modifié !')
        return redirect('core:atelier_detail', pk=dossier.atelier.id)
    return render(request, 'core/atelier_dossier_update.html', {'dossier': dossier})


def atelier_dossier_delete(request, pk):
    dossier = get_object_or_404(DossierAtelier, id=pk)
    atelier_id = dossier.atelier.id
    if request.method == 'POST':
        dossier.delete()
        messages.success(request, '✅ Dossier supprimé.')
    return redirect('core:atelier_detail', pk=atelier_id)


def atelier_fichier_create(request, dossier_id):
    dossier = get_object_or_404(DossierAtelier, id=dossier_id)
    if request.method == 'POST':
        fichier = FichierAtelier(
            dossier=dossier, nom=request.POST.get('nom'),
            type_contenu=request.POST.get('type_contenu', 'fichier'),
            ordre=request.POST.get('ordre', 0), createur=request.user
        )
        if fichier.type_contenu == 'fichier':
            fichier.fichier = request.FILES.get('fichier')
        elif fichier.type_contenu == 'lien':
            fichier.lien_externe = request.POST.get('lien_externe')
        elif fichier.type_contenu == 'iframe':
            fichier.code_iframe = request.POST.get('code_iframe')
        fichier.save()
        messages.success(request, '✅ Fichier ajouté !')
        return redirect('core:atelier_detail', pk=dossier.atelier.id)
    return render(request, 'core/atelier_fichier_create.html', {'dossier': dossier})


def atelier_fichier_update(request, pk):
    fichier = get_object_or_404(FichierAtelier, id=pk)
    if request.method == 'POST':
        fichier.nom = request.POST.get('nom')
        fichier.ordre = request.POST.get('ordre', 0)
        if request.POST.get('type_contenu'):
            fichier.type_contenu = request.POST.get('type_contenu')
        if fichier.type_contenu == 'fichier' and request.FILES.get('fichier'):
            fichier.fichier = request.FILES.get('fichier')
        elif fichier.type_contenu == 'lien':
            fichier.lien_externe = request.POST.get('lien_externe')
        elif fichier.type_contenu == 'iframe':
            fichier.code_iframe = request.POST.get('code_iframe')
        fichier.save()
        messages.success(request, '✅ Fichier modifié !')
        return redirect('core:atelier_detail', pk=fichier.dossier.atelier.id)
    return render(request, 'core/atelier_fichier_update.html', {'fichier': fichier})


def atelier_fichier_delete(request, pk):
    fichier = get_object_or_404(FichierAtelier, id=pk)
    atelier_id = fichier.dossier.atelier.id
    if request.method == 'POST':
        fichier.delete()
        messages.success(request, 'Fichier supprimé.')
    return redirect('core:atelier_detail', pk=atelier_id)


# ═══════════════════════════════════════════════════
# PORTFOLIO BAC PRO
# ═══════════════════════════════════════════════════

@login_required
def gestion_portfolio(request):
    """Liste des portfolios BAC Pro — vue professeur."""
    classes_bac = Classe.objects.filter(
        niveau__nom='BAC_PRO', actif=True
    ).order_by('nom')

    classe_id = request.GET.get('classe')

    # Élèves BAC Pro
    eleves_qs = ProfilUtilisateur.objects.filter(
        type_utilisateur='eleve',
        compte_approuve=True,
        est_sorti=False,
        classe__niveau__nom='BAC_PRO',
    ).select_related('user', 'classe').order_by('classe__nom', 'user__last_name')

    if classe_id:
        eleves_qs = eleves_qs.filter(classe_id=classe_id)

    # Créer automatiquement les portfolios manquants
    eleves_sans_portfolio = eleves_qs.filter(portfolio__isnull=True)
    portfolios_a_creer = [
        Portfolio(eleve=e) for e in eleves_sans_portfolio
    ]
    if portfolios_a_creer:
        Portfolio.objects.bulk_create(portfolios_a_creer, ignore_conflicts=True)

    # Récupérer les données enrichies
    from django.db.models import Count, Q as Qf
    portfolios = (
        Portfolio.objects
        .filter(actif=True, eleve__in=eleves_qs)
        .select_related('eleve__user', 'eleve__classe')
        .annotate(
            total_fiches=Count('fiches'),
            fiches_validees=Count('fiches', filter=Qf(fiches__validee_par_prof=True)),
            fiches_en_attente=Count('fiches', filter=Qf(fiches__validee_par_prof=False)),
        )
        .order_by('eleve__classe__nom', 'eleve__user__last_name')
    )

    return render(request, 'core/gestion_portfolio.html', {
        'portfolios': portfolios,
        'classes_bac': classes_bac,
        'classe_selectionnee': classe_id,
    })


def gestion_pfmp(request):
    classes = Classe.objects.all().order_by('nom')
    classe_selectionnee = request.GET.get('classe')
    if classe_selectionnee:
        pfmps = PFMP.objects.filter(classes=classe_selectionnee, actif=True).prefetch_related('classes').order_by('date_debut')
    else:
        pfmps = PFMP.objects.filter(actif=True).prefetch_related('classes').order_by('date_debut', 'titre')
    if request.method == 'POST':
        titre = request.POST.get('titre')
        classes_ids = request.POST.getlist('classes')
        if titre and classes_ids:
            pfmp = PFMP(
                titre=titre,
                description=request.POST.get('description', ''),
                date_debut=request.POST.get('date_debut') or None,
                date_fin=request.POST.get('date_fin') or None,
                type_contenu=request.POST.get('type_contenu', 'fichier'),
                createur=request.user
            )
            type_contenu = request.POST.get('type_contenu', 'fichier')
            if type_contenu == 'fichier' and request.FILES.get('fichier'):
                pfmp.fichier = request.FILES['fichier']
            elif type_contenu == 'lien' and request.POST.get('lien_externe'):
                pfmp.lien_externe = request.POST.get('lien_externe')
            elif type_contenu == 'iframe' and request.POST.get('code_iframe'):
                pfmp.code_iframe = request.POST.get('code_iframe')
            pfmp.save()
            pfmp.classes.set(classes_ids)
            classes_noms = ', '.join(Classe.objects.filter(id__in=classes_ids).values_list('nom', flat=True))
            for eleve in ProfilUtilisateur.objects.filter(classe_id__in=classes_ids, type_utilisateur='eleve', compte_approuve=True, est_sorti=False):
                Notification.objects.create(
                    destinataire=eleve.user, type_notification='pfmp',
                    titre=f'📋 Nouvelle PFMP : {titre}',
                    message=f'Une période de PFMP a été ajoutée ({classes_noms}).',
                    lien=f'/pfmp/{pfmp.id}/'
                )
            messages.success(request, f'✅ PFMP "{titre}" créée !')
            return redirect('core:gestion_pfmp')
        else:
            messages.error(request, '❌ Le titre et au moins une classe sont obligatoires.')
    nb_pfmp = PFMP.objects.filter(actif=True).count()
    return render(request, 'core/gestion_pfmp.html', {
        'pfmps': pfmps, 'classes': classes,
        'classe_selectionnee': classe_selectionnee, 'nb_pfmp': nb_pfmp,
    })


def pfmp_supprimer(request, pk):
    pfmp = get_object_or_404(PFMP, id=pk)
    if request.method == 'POST':
        titre = pfmp.titre
        pfmp.delete()
        messages.success(request, f'✅ PFMP "{titre}" supprimée !')
    return redirect('core:gestion_pfmp')


def pfmp_create(request):
    classes = Classe.objects.all().order_by('nom')
    if request.method == 'POST':
        titre = request.POST.get('titre')
        classes_ids = request.POST.getlist('classes')
        if titre and classes_ids:
            str_date_debut = request.POST.get('date_debut')
            str_date_fin = request.POST.get('date_fin')
            d_debut = datetime.strptime(str_date_debut, '%Y-%m-%d').date() if str_date_debut else None
            d_fin = datetime.strptime(str_date_fin, '%Y-%m-%d').date() if str_date_fin else None
            pfmp = PFMP.objects.create(
                titre=titre,
                description=request.POST.get('description', ''),
                date_debut=d_debut, date_fin=d_fin,
                type_contenu=request.POST.get('type_contenu', 'fichier'),
                createur=request.user
            )
            pfmp.classes.set(classes_ids)
            if pfmp.type_contenu == 'fichier' and request.FILES.get('fichier'):
                pfmp.fichier = request.FILES.get('fichier')
            elif pfmp.type_contenu == 'lien':
                pfmp.lien_externe = request.POST.get('lien_externe')
            elif pfmp.type_contenu == 'iframe':
                pfmp.code_iframe = request.POST.get('code_iframe')
            pfmp.save()
            if request.POST.get('creer_dossier') == 'on':
                dossier_nom = request.POST.get('dossier_nom')
                if dossier_nom:
                    DossierPFMP.objects.create(
                        pfmp=pfmp, nom=dossier_nom,
                        visible_eleves=request.POST.get('dossier_visible') == 'on', ordre=0
                    )
            messages.success(request, f'✅ PFMP "{titre}" créée avec succès !')
            return redirect('core:gestion_pfmp')
        else:
            messages.error(request, '❌ Le titre et au moins une classe sont obligatoires.')
    return render(request, 'core/pfmp_create.html', {'classes': classes})


def pfmp_update(request, pk):
    pfmp = get_object_or_404(PFMP, id=pk)
    classes = Classe.objects.all().order_by('nom')
    if request.method == 'POST':
        pfmp.titre = request.POST.get('titre')
        pfmp.description = request.POST.get('description', '')
        pfmp.date_debut = request.POST.get('date_debut') or None
        pfmp.date_fin = request.POST.get('date_fin') or None
        pfmp.type_contenu = request.POST.get('type_contenu', '')
        classes_ids = request.POST.getlist('classes')
        if classes_ids:
            pfmp.classes.set(classes_ids)
        if pfmp.type_contenu == 'fichier':
            nouveau_fichier = request.FILES.get('fichier')
            if nouveau_fichier:
                pfmp.fichier = nouveau_fichier
            pfmp.lien_externe = None
            pfmp.code_iframe = None
        elif pfmp.type_contenu == 'lien':
            pfmp.lien_externe = request.POST.get('lien_externe', '').strip() or None
            pfmp.code_iframe = None
        elif pfmp.type_contenu == 'iframe':
            pfmp.code_iframe = request.POST.get('code_iframe', '').strip() or None
            pfmp.lien_externe = None
        pfmp.save()
        messages.success(request, '✅ PFMP modifiée !')
        return redirect('core:gestion_pfmp')
    return render(request, 'core/pfmp_update.html', {'pfmp': pfmp, 'classes': classes})


def pfmp_detail(request, pk):
    pfmp = get_object_or_404(PFMP, id=pk)
    is_prof = est_professeur(request.user)
    if hasattr(request.user, 'profil') and request.user.profil.est_eleve():
        if request.user.profil.classe not in pfmp.classes.all():
            messages.error(request, "⛔ Vous n'avez pas accès à cette section.")
            return redirect('core:dashboard_eleve')
        dossiers = DossierPFMP.objects.filter(pfmp=pfmp, actif=True, visible_eleves=True).order_by('ordre', 'nom')
        template = 'core/pfmp_detail_eleve.html'
    else:
        dossiers = DossierPFMP.objects.filter(pfmp=pfmp, actif=True).order_by('ordre', 'nom')
        template = 'core/pfmp_detail.html'
    dossiers_avec_fichiers = []
    for dossier in dossiers:
        fichiers = FichierPFMP.objects.filter(dossier=dossier, actif=True).order_by('ordre', 'nom')
        dossiers_avec_fichiers.append({'dossier': dossier, 'fichiers': fichiers})
    jours_restants = None
    statut_couleur = ''
    statut_texte = ''
    if pfmp.date_debut and pfmp.date_fin:
        today = date.today()
        jours_restants = (pfmp.date_debut - today).days
        if jours_restants < 0:
            if today <= pfmp.date_fin:
                statut_texte = "En cours"
                statut_couleur = "vert"
            else:
                statut_texte = "Terminée"
                statut_couleur = "gris"
        else:
            statut_texte = f"Dans {jours_restants} jours"
            statut_couleur = "bleu"
    return render(request, template, {
        'pfmp': pfmp, 'dossiers_avec_fichiers': dossiers_avec_fichiers,
        'jours_restants': jours_restants, 'statut_texte': statut_texte,
        'statut_couleur': statut_couleur, 'is_prof': is_prof,
    })


def pfmp_dossier_create(request, pfmp_id):
    pfmp = get_object_or_404(PFMP, id=pfmp_id)
    if request.method == 'POST':
        DossierPFMP.objects.create(
            pfmp=pfmp, nom=request.POST.get('nom'),
            description=request.POST.get('description', ''),
            ordre=request.POST.get('ordre', 0),
            visible_eleves=request.POST.get('visible_eleves') == 'on'
        )
        messages.success(request, '✅ Dossier créé !')
        return redirect('core:pfmp_detail', pk=pfmp_id)
    return render(request, 'core/pfmp_dossier_create.html', {'pfmp': pfmp})


def pfmp_dossier_update(request, pk):
    dossier = get_object_or_404(DossierPFMP, id=pk)
    if request.method == 'POST':
        dossier.nom = request.POST.get('nom')
        dossier.description = request.POST.get('description', '')
        dossier.ordre = request.POST.get('ordre', 0)
        dossier.visible_eleves = request.POST.get('visible_eleves') == 'on'
        dossier.save()
        messages.success(request, '✅ Dossier modifié !')
        return redirect('core:pfmp_detail', pk=dossier.pfmp.id)
    return render(request, 'core/pfmp_dossier_update.html', {'dossier': dossier})


def pfmp_dossier_delete(request, pk):
    dossier = get_object_or_404(DossierPFMP, id=pk)
    pfmp_id = dossier.pfmp.id
    if request.method == 'POST':
        dossier.delete()
        messages.success(request, '✅ Dossier supprimé.')
    return redirect('core:pfmp_detail', pk=pfmp_id)


def pfmp_fichier_create(request, dossier_id):
    dossier = get_object_or_404(DossierPFMP, id=dossier_id)
    if request.method == 'POST':
        fichier = FichierPFMP(
            dossier=dossier, nom=request.POST.get('nom'),
            type_contenu=request.POST.get('type_contenu', 'fichier'),
            ordre=request.POST.get('ordre', 0), createur=request.user
        )
        if fichier.type_contenu == 'fichier':
            fichier.fichier = request.FILES.get('fichier')
        elif fichier.type_contenu == 'lien':
            fichier.lien_externe = request.POST.get('lien_externe')
        elif fichier.type_contenu == 'iframe':
            fichier.code_iframe = request.POST.get('code_iframe')
        fichier.save()
        messages.success(request, '✅ Fichier ajouté !')
        return redirect('core:pfmp_detail', pk=dossier.pfmp.id)
    return render(request, 'core/pfmp_fichier_create.html', {'dossier': dossier})


def pfmp_fichier_update(request, pk):
    fichier = get_object_or_404(FichierPFMP, id=pk)
    if request.method == 'POST':
        fichier.nom = request.POST.get('nom')
        fichier.ordre = request.POST.get('ordre', 0)
        if request.POST.get('type_contenu'):
            fichier.type_contenu = request.POST.get('type_contenu')
        if fichier.type_contenu == 'fichier' and request.FILES.get('fichier'):
            fichier.fichier = request.FILES.get('fichier')
        elif fichier.type_contenu == 'lien':
            fichier.lien_externe = request.POST.get('lien_externe')
        elif fichier.type_contenu == 'iframe':
            fichier.code_iframe = request.POST.get('code_iframe')
        fichier.save()
        messages.success(request, '✅ Fichier modifié !')
        return redirect('core:pfmp_detail', pk=fichier.dossier.pfmp.id)
    return render(request, 'core/pfmp_fichier_update.html', {'fichier': fichier})


def pfmp_fichier_delete(request, pk):
    fichier = get_object_or_404(FichierPFMP, id=pk)
    pfmp_id = fichier.dossier.pfmp.id
    if request.method == 'POST':
        fichier.delete()
        messages.success(request, '✅ Fichier supprimé.')
    return redirect('core:pfmp_detail', pk=pfmp_id)


def saisie_suivi_pfmp(request, pfmp_id):
    """Saisie ou mise à jour des jours effectués / manqués par élève pour une PFMP."""
    pfmp = get_object_or_404(PFMP, id=pfmp_id)
    eleves = ProfilUtilisateur.objects.filter(
        classe__in=pfmp.classes.all(), type_utilisateur='eleve',
        compte_approuve=True, est_sorti=False
    ).select_related('user').order_by('user__last_name', 'user__first_name')

    if request.method == 'POST':
        for eleve in eleves:
            effectues  = int(request.POST.get(f'effectues_{eleve.id}', 0) or 0)
            justifies  = int(request.POST.get(f'justifies_{eleve.id}', 0) or 0)
            injustifies = int(request.POST.get(f'injustifies_{eleve.id}', 0) or 0)
            commentaire = request.POST.get(f'commentaire_{eleve.id}', '').strip()
            SuiviPFMP.objects.update_or_create(
                pfmp=pfmp, eleve=eleve,
                defaults={
                    'nb_jours_effectues': effectues,
                    'nb_jours_manques_justifies': justifies,
                    'nb_jours_manques_injustifies': injustifies,
                    'commentaire': commentaire,
                }
            )
        messages.success(request, f'✅ Suivi PFMP "{pfmp.titre}" enregistré !')
        return redirect('core:gestion_pfmp')

    suivis = {s.eleve_id: s for s in SuiviPFMP.objects.filter(pfmp=pfmp)}
    eleves_avec_suivi = []
    for eleve in eleves:
        eleves_avec_suivi.append({'profil': eleve, 'suivi': suivis.get(eleve.id)})

    return render(request, 'core/saisie_suivi_pfmp.html', {
        'pfmp': pfmp,
        'eleves_avec_suivi': eleves_avec_suivi,
    })


def passer_en_classe_superieure(request, eleve_id):
    """Passage d'un élève en classe supérieure ou redoublement."""
    eleve = get_object_or_404(ProfilUtilisateur, id=eleve_id, type_utilisateur='eleve')
    classes = Classe.objects.all().order_by('nom')
    mode = request.GET.get('mode', '') or request.POST.get('mode', '')
    est_redoublement = (mode == 'redoublement')

    if request.method == 'POST':
        nouvelle_classe_id = request.POST.get('nouvelle_classe')
        annee_actuelle     = request.POST.get('annee_actuelle', '').strip()
        date_fin_str       = request.POST.get('date_fin', '')
        redoublement       = request.POST.get('redoublement') == 'on'
        if not nouvelle_classe_id or not annee_actuelle:
            messages.error(request, "❌ La nouvelle classe et l'année scolaire sont obligatoires.")
        else:
            try:
                date_fin_val = datetime.strptime(date_fin_str, '%Y-%m-%d').date() if date_fin_str else date.today()
            except ValueError:
                date_fin_val = date.today()

            # Archiver la classe actuelle
            if eleve.classe:
                HistoriqueClasse.objects.create(
                    eleve=eleve,
                    classe=eleve.classe,
                    annee=annee_actuelle,
                    date_debut=eleve.date_inscription.date() if hasattr(eleve.date_inscription, 'date') else date.today(),
                    date_fin=date_fin_val,
                    redoublement=redoublement,
                )
            # Affecter la nouvelle classe (même classe si redoublement)
            ancienne_classe = eleve.classe.nom if eleve.classe else '—'
            # Si on a choisi l'option spéciale AFB depuis le formulaire, créer/récupérer la classe 1AFB
            if nouvelle_classe_id == '__AFB__':
                niveau, _ = Niveau.objects.get_or_create(nom='BAC_PRO', defaults={'description': 'Baccalauréat Professionnel'})
                classe_afb, created = Classe.objects.get_or_create(nom='1AFB', defaults={'niveau': niveau, 'description': 'Classe 1 AFB (créée automatiquement)'} )
                eleve.classe = classe_afb
                eleve.parcours = 'AFB'
                eleve.save(update_fields=['classe', 'parcours'])
                messages.success(request, f'✅ {eleve.user.get_full_name()} transféré vers {classe_afb.nom} (parcours AFB). Historique enregistré.')
                return redirect('core:classe_detail', pk=classe_afb.id)

            # Assignation normale — on accepte aussi un choix de parcours envoyé depuis le formulaire
            parcours_choice = request.POST.get('parcours')
            eleve.classe_id = nouvelle_classe_id
            if parcours_choice in ('ORGO', 'AFB'):
                eleve.parcours = parcours_choice
                eleve.save(update_fields=['classe', 'parcours'])
            else:
                eleve.save(update_fields=['classe'])

            if redoublement:
                messages.success(request, f'✅ Redoublement enregistré pour {eleve.user.get_full_name()}. Historique mis à jour.')
            else:
                messages.success(request, f'✅ {eleve.user.get_full_name()} transféré de {ancienne_classe} vers {eleve.classe.nom}. Historique enregistré.')
            return redirect('core:classe_detail', pk=int(nouvelle_classe_id))

    return render(request, 'core/passer_en_classe_superieure.html', {
        'eleve': eleve,
        'classes': classes,
        'historique': HistoriqueClasse.objects.filter(eleve=eleve).order_by('-date_debut'),
        'mode': mode,
        'est_redoublement': est_redoublement,
    })


def evaluations_home(request):
    fiches_actives = FicheContrat.objects.filter(
        createur=request.user, actif=True
    ).select_related('classe', 'referentiel').prefetch_related('evaluations').order_by('-date_creation')
    fiches_archivees = FicheContrat.objects.filter(
        createur=request.user, actif=False
    ).order_by('-date_modification')
    nb_fiches_contrat = fiches_actives.count()
    # Compter une évaluation par fiche-contrat (indépendamment du nombre d'élèves)
    nb_evaluations = nb_fiches_contrat
    # Compter les fiches-contrat entièrement validées (toutes les évaluations élèves validées)
    nb_validees = 0
    for fc in fiches_actives:
        total_ev = FicheEvaluation.objects.filter(fiche_contrat=fc).count()
        if total_ev == 0:
            continue
        validees = FicheEvaluation.objects.filter(fiche_contrat=fc, validee=True).count()
        if validees >= total_ev:
            nb_validees += 1
    qcms = QCM.objects.annotate(nb_questions=Count('questions')).select_related('theme', 'classe').order_by('-date_creation')
    return render(request, 'core/evaluations_home.html', {
        'nb_fiches_contrat': nb_fiches_contrat,
        'nb_archives': fiches_archivees.count(),
        'nb_evaluations': nb_evaluations,
        'nb_validees': nb_validees,
        'nb_en_cours': nb_evaluations - nb_validees,
        'fiches_recentes': fiches_actives[:10],
        'fiches_archivees': fiches_archivees,
        'qcms': qcms,
        'nb_qcm': qcms.filter(actif=True).count(),
    })


def evaluation_parametres(request):
    if request.method == 'POST':
        return creer_evaluation(request)
    referentiels = Referentiel.objects.filter(actif=True)
    classes = Classe.objects.filter(actif=True).order_by('nom')
    ateliers = Atelier.objects.filter(actif=True).select_related('classe')
    return render(request, 'core/evaluation_parametres.html', {
        'referentiels': referentiels, 'classes': classes,
        'ateliers': ateliers,
    })


def _extraire_selection_dedupliquee(selection_data):
    """
    Sépare et déduplique les critères et connaissances depuis selection_data.
    Retourne (criteres_selectionnes, connaissances_selectionnees).
    """
    vus_criteres = set()
    criteres_selectionnes = []
    for item in selection_data:
        if item.get('type') == 'critere':
            ind_id = item.get('indicateur_id')
            if ind_id and ind_id not in vus_criteres:
                vus_criteres.add(ind_id)
                criteres_selectionnes.append(item)

    vus_conn = set()
    connaissances_selectionnees = []
    for item in selection_data:
        if item.get('type') == 'connaissance':
            c_id = item.get('id')
            if c_id and c_id not in vus_conn:
                vus_conn.add(c_id)
                connaissances_selectionnees.append(item)

    return criteres_selectionnes, connaissances_selectionnees


def _extraire_noms_connaissances(connaissances_selectionnees):
    """
    Retourne la liste dédupliquée des noms de Connaissance à partir des données sélectionnées.
    """
    noms_vus = set()
    noms_connaissances = []
    for c_data in connaissances_selectionnees:
        try:
            conn = Connaissance.objects.get(id=c_data['id'])
            if conn.nom not in noms_vus:
                noms_vus.add(conn.nom)
                noms_connaissances.append(conn.nom)
        except Connaissance.DoesNotExist:
            pass
    return noms_connaissances


def _creer_lignes_contrat(fiche_contrat, criteres_selectionnes):
    """
    Crée les LigneContrat pour chaque critère sélectionné,
    avec poids réparti équitablement sur 100.
    """
    nb_criteres = len([c for c in criteres_selectionnes if c.get('indicateur_id')])
    poids_initial = round(100 / nb_criteres, 2) if nb_criteres > 0 else 10.0
    for ordre, item in enumerate(criteres_selectionnes):
        ind_id = item.get('indicateur_id')
        if not ind_id:
            continue
        indicateur      = get_object_or_404(IndicateurPerformance, id=ind_id)
        critere         = indicateur.critere
        sous_competence = critere.sous_competence
        competence_pro  = sous_competence.competence_pro
        LigneContrat.objects.create(
            fiche=fiche_contrat, competence_pro=competence_pro,
            sous_competence=sous_competence, critere=critere,
            indicateur=indicateur, poids=poids_initial, ordre=ordre
        )


def _creer_fiches_eleves(fiche_contrat, eleves_ids):
    """
    Crée une FicheEvaluation et les EvaluationLigne associées pour chaque élève sélectionné.
    """
    lignes_contrat = fiche_contrat.lignes.all()
    for eleve_id in eleves_ids:
        eleve = get_object_or_404(ProfilUtilisateur, id=eleve_id)
        fiche_eval = FicheEvaluation.objects.create(fiche_contrat=fiche_contrat, eleve=eleve)
        for lc in lignes_contrat:
            EvaluationLigne.objects.create(fiche_evaluation=fiche_eval, ligne_contrat=lc, note='NE')


def creer_evaluation(request):
    """
    Crée une FicheContrat avec ses lignes et ses fiches élèves à partir du formulaire
    de paramétrage (evaluation_parametres).
    """
    try:
        referentiel_id  = request.POST.get('referentiel')
        classe_id       = request.POST.get('classe')
        titre_tp        = request.POST.get('titre_tp')
        date_tp         = request.POST.get('date_tp') or None
        type_evaluation = request.POST.get('type_evaluation', 'sommative')
        problematique   = request.POST.get('problematique', '')
        contexte        = request.POST.get('contexte', '')
        consigne        = request.POST.get('consigne', '')
        observation_environnement = request.POST.get('observation_environnement', '')
        materiels       = request.POST.get('materiels', '')
        risques_epi     = request.POST.get('risques_epi', '')

        eleves_ids     = json.loads(request.POST.get('eleves_selectionnes', '[]'))
        selection_data = json.loads(request.POST.get('competences_selectionnees', '[]'))

        if not referentiel_id or not classe_id or not titre_tp:
            messages.error(request, "❌ Champs obligatoires manquants")
            return redirect('core:evaluation_parametres')

        criteres_selectionnes, connaissances_selectionnees = _extraire_selection_dedupliquee(selection_data)

        if not eleves_ids:
            messages.error(request, "❌ Sélectionnez au moins un élève")
            return redirect('core:evaluation_parametres')
        if not criteres_selectionnes and not connaissances_selectionnees:
            messages.error(request, "❌ Sélectionnez au moins un critère ou une connaissance")
            return redirect('core:evaluation_parametres')

        referentiel = get_object_or_404(Referentiel, id=referentiel_id)
        classe      = get_object_or_404(Classe, id=classe_id)

        noms_connaissances = _extraire_noms_connaissances(connaissances_selectionnees)

        fiche_contrat = FicheContrat.objects.create(
            referentiel=referentiel, classe=classe, titre_tp=titre_tp,
            date_tp=date_tp, type_evaluation=type_evaluation,
            problematique=problematique, contexte=contexte, consigne=consigne,
            observation_environnement=observation_environnement,
            materiels=materiels, risques_epi=risques_epi,
            savoirs_associes="\n".join(noms_connaissances),
            createur=request.user
        )

        # Si un atelier est fourni, on l'associe (sécurité : vérifie la classe)
        atelier_id = request.POST.get('atelier')
        if atelier_id:
            try:
                atelier_obj = Atelier.objects.get(id=atelier_id, classe=classe)
                fiche_contrat.atelier = atelier_obj
                fiche_contrat.save()
            except Atelier.DoesNotExist:
                # on ignore silencieusement (l'UI enverra un message si nécessaire)
                pass

        _creer_lignes_contrat(fiche_contrat, criteres_selectionnes)
        _creer_fiches_eleves(fiche_contrat, eleves_ids)

        messages.success(request, f"✅ Évaluation créée ! ({len(criteres_selectionnes)} critère(s), {len(connaissances_selectionnees)} connaissance(s))")
        return redirect('core:evaluation_detail', pk=fiche_contrat.id)

    except Exception as e:
        traceback.print_exc()
        messages.error(request, f"❌ Erreur : {str(e)}")
        return redirect('core:evaluation_parametres')


def evaluation_detail(request, pk):
    fiche_contrat = get_object_or_404(FicheContrat, id=pk, createur=request.user)
    evaluations = FicheEvaluation.objects.filter(fiche_contrat=fiche_contrat)\
        .select_related('eleve__user').order_by('eleve__user__last_name')
    for evaluation in evaluations:
        if evaluation.note_sur_20 is None:
            evaluation.calculer_note_sur_20()
    lignes = fiche_contrat.lignes.select_related(
        'competence_pro', 'sous_competence', 'critere', 'indicateur'
    ).order_by('ordre')
    lignes_par_cp = {}
    for ligne in lignes:
        cp_code = ligne.competence_pro.code if ligne.competence_pro else 'Autre'
        cp_nom  = ligne.competence_pro.nom  if ligne.competence_pro else ''
        key = f"{cp_code} - {cp_nom}"
        if key not in lignes_par_cp:
            lignes_par_cp[key] = []
        lignes_par_cp[key].append(ligne)
    # Déduplication des savoirs associés (le champ texte peut contenir des doublons)
    savoirs_bruts = fiche_contrat.savoirs_associes or ""
    savoirs_dedupliques = list(dict.fromkeys(
        l.strip() for l in savoirs_bruts.splitlines() if l.strip()
    ))
    # Élèves de la classe sans fiche d'évaluation (absents)
    eleves_avec_fiche = set(evaluations.values_list('eleve_id', flat=True))
    eleves_sans_fiche = ProfilUtilisateur.objects.filter(
        classe=fiche_contrat.classe, type_utilisateur='eleve',
        compte_approuve=True, est_sorti=False
    ).exclude(id__in=eleves_avec_fiche).select_related('user').order_by('user__last_name')
    # Archivage possible uniquement si contrat + toutes les fiches validées
    nb_eval_total = evaluations.count()
    peut_archiver = (
        fiche_contrat.contrat_valide and
        nb_eval_total > 0 and
        not evaluations.filter(validee=False).exists()
    )
    if not fiche_contrat.contrat_valide:
        raison_blocage_archivage = "Le contrat doit être validé"
    elif nb_eval_total == 0:
        raison_blocage_archivage = "Aucune fiche d'évaluation créée"
    else:
        raison_blocage_archivage = "Toutes les fiches d'évaluation doivent être validées"
    return render(request, 'core/evaluation_detail.html', {
        'fiche_contrat': fiche_contrat,
        'evaluations': evaluations,
        'lignes_par_cp': lignes_par_cp,
        'nb_eleves': evaluations.count(),
        'savoirs_dedupliques': savoirs_dedupliques,
        'eleves_sans_fiche': eleves_sans_fiche,
        'peut_archiver': peut_archiver,
        'raison_blocage_archivage': raison_blocage_archivage,
        'ateliers': Atelier.objects.filter(classe=fiche_contrat.classe, actif=True).order_by('ordre', 'titre'),
        'atelier_selection': getattr(fiche_contrat, 'atelier', None),
    })


@login_required
@user_passes_test(est_professeur)
def evaluation_lier_atelier(request, pk):
    """Lie ou délien une FicheContrat à un Atelier (professeurs seulement)."""
    fiche_contrat = get_object_or_404(FicheContrat, id=pk, createur=request.user)
    if request.method == 'POST':
        atelier_id = request.POST.get('atelier')
        if atelier_id:
            try:
                atelier = Atelier.objects.get(id=atelier_id, classe=fiche_contrat.classe)
                fiche_contrat.atelier = atelier
                fiche_contrat.save()
                messages.success(request, '✅ Atelier lié à la fiche.')
            except Atelier.DoesNotExist:
                messages.error(request, '❌ Atelier introuvable pour cette classe.')
        else:
            fiche_contrat.atelier = None
            fiche_contrat.save()
            messages.success(request, '✅ Atelier détaché de la fiche.')
    return redirect('core:evaluation_detail', pk=fiche_contrat.id)


@login_required
@user_passes_test(est_professeur)
def export_fiche_contrat_archive(request, pk):
    """Génère un ZIP contenant : fichiers de l'atelier (si présent),
    la fiche contrat (PDF) et les fiches évaluations (PDF) pour téléchargement.
    Accessible par le créateur (professeur) seulement.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Export archive requested pk={pk} by user={getattr(request.user, 'username', None)}")
    fiche_contrat = get_object_or_404(FicheContrat, id=pk, createur=request.user)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        # 1) Ajouter fichiers de l'atelier (dossiers + fichiers)
        atelier = getattr(fiche_contrat, 'atelier', None)
        if atelier:
            # fichier direct sur Atelier
            if getattr(atelier, 'fichier', None):
                try:
                    ffield = atelier.fichier
                    name = os.path.basename(ffield.name)
                    with ffield.open('rb') as fh:
                        zf.writestr(f'ateliers/{atelier.titre}/{name}', fh.read())
                except Exception:
                    pass
            # dossiers et fichiers
            for dossier in atelier.dossiers.all():
                for fa in dossier.fichiers.filter(actif=True).order_by('ordre'):
                    if fa.type_contenu == 'fichier' and fa.fichier:
                        try:
                            with fa.fichier.open('rb') as fh:
                                path_in_zip = f'ateliers/{atelier.titre}/{dossier.nom}/{os.path.basename(fa.fichier.name)}'
                                zf.writestr(path_in_zip, fh.read())
                        except Exception:
                            # si stockage distant ou erreur, ignorer
                            continue
                    elif fa.type_contenu == 'lien' and fa.lien_externe:
                        zf.writestr(f'ateliers/{atelier.titre}/{dossier.nom}/{fa.nom}_link.txt', fa.lien_externe)

        # Temporary helper: force HTML output (fallback) to ensure archive downloads
        def render_to_pdf_bytes(template_name, context, filename_base, request):
            # Render template to HTML and return as .html bytes
            html = render_to_string(template_name, context, request=request)
            return html.encode('utf-8'), f'{filename_base}.html'

        # 2) Fiche contrat (page imprimable)
        try:
            lignes_contrat, competences_vises, savoirs_dedupliques = _get_donnees_page1_contrat(fiche_contrat)
            context = {'fiche_contrat': fiche_contrat, 'lignes_contrat': lignes_contrat,
                       'competences_vises': competences_vises, 'savoirs_dedupliques': savoirs_dedupliques}
            data, fname = render_to_pdf_bytes('core/fiche_contrat_print.html', context, f'fiche_contrat_{fiche_contrat.id}', request)
            zf.writestr(fname, data)
        except Exception:
            pass

        # 3) Fiches évaluations (compile toutes les fiches dans un PDF/HTML)
        try:
            # reuse generer_fiches_evaluation context
            fiches_eleves = FicheEvaluation.objects.filter(fiche_contrat=fiche_contrat).select_related('eleve__user')
            donnees_impression = []
            for fe in fiches_eleves:
                groupes = _get_donnees_page2_evaluation(fe, fiche_contrat)[1]
                donnees_impression.append({'eleve': fe.eleve, 'evaluation': fe, 'groupes_competences': groupes})
            context_eval = {'fiche_contrat': fiche_contrat, 'donnees_impression': donnees_impression, 'poids_auto': round(100 / (fiche_contrat.lignes.count() or 1), 2)}
            data_eval, fname_eval = render_to_pdf_bytes('core/fiche_evaluation_print.html', context_eval, f'fiches_evaluation_{fiche_contrat.id}', request)
            zf.writestr(fname_eval, data_eval)
        except Exception:
            pass

        # 4) Modes opératoires liés à l'atelier
        try:
            if atelier:
                for mo in atelier.modes_operatoires.filter(actif=True).order_by('date_creation'):
                    # Build simple context and render
                    lignes = list(mo.lignes.order_by('ordre'))
                    ctx_mo = {'mode_operatoire': mo, 'lignes': lignes}
                    data_mo, fname_mo = render_to_pdf_bytes('core/mode_operatoire_print.html', ctx_mo, f'mode_operatoire_{mo.id}', request)
                    zf.writestr(f'modes_operatoires/{fname_mo}', data_mo)
        except Exception:
            pass

    buf.seek(0)
    filename = f"{fiche_contrat.titre_tp.replace(' ', '_')}_archive.zip"
    response = FileResponse(buf, as_attachment=True, filename=filename)
    return response


def deverrouiller_fiche_evaluation(request, fiche_eval_id):
    """Déverrouille une fiche d'évaluation validée pour correction."""
    fiche_eval = get_object_or_404(FicheEvaluation, id=fiche_eval_id)
    if fiche_eval.fiche_contrat.createur != request.user:
        messages.error(request, "❌ Accès refusé.")
        return redirect('core:evaluations_home')
    if request.method == 'POST':
        fiche_eval.validee = False
        fiche_eval.date_validation = None
        fiche_eval.save()
        messages.success(request, f"🔓 Fiche de {fiche_eval.eleve.user.get_full_name()} déverrouillée. Vous pouvez corriger les notes.")
    return redirect('core:fiche_evaluation_saisie', fiche_eval.fiche_contrat.id, fiche_eval.eleve.id)


def creer_fiche_absent(request, fiche_contrat_id, eleve_id):
    """Crée une fiche d'évaluation vierge pour un élève absent."""
    fiche_contrat = get_object_or_404(FicheContrat, id=fiche_contrat_id, createur=request.user)
    eleve = get_object_or_404(ProfilUtilisateur, id=eleve_id)
    if request.method == 'POST':
        fiche_eval, created = FicheEvaluation.objects.get_or_create(
            fiche_contrat=fiche_contrat, eleve=eleve
        )
        if created:
            lignes_contrat = fiche_contrat.lignes.all()
            for lc in lignes_contrat:
                EvaluationLigne.objects.get_or_create(
                    fiche_evaluation=fiche_eval, ligne_contrat=lc, defaults={'note': 'NE'}
                )
            messages.success(request, f"✅ Fiche créée pour {eleve.user.get_full_name()}. Vous pouvez saisir les notes.")
        else:
            messages.info(request, f"ℹ️ Une fiche existe déjà pour {eleve.user.get_full_name()}.")
        return redirect('core:fiche_evaluation_saisie', fiche_contrat.id, eleve.id)
    return redirect('core:evaluation_detail', fiche_contrat.id)


def fiche_evaluation_saisie(request, fiche_contrat_id, eleve_id):
    fiche_contrat = get_object_or_404(FicheContrat, id=fiche_contrat_id, createur=request.user)
    eleve = get_object_or_404(ProfilUtilisateur, id=eleve_id)
    fiche_eval = get_object_or_404(FicheEvaluation, fiche_contrat=fiche_contrat, eleve=eleve)
    lignes_contrat = fiche_contrat.lignes.select_related(
        'indicateur', 'competence_pro', 'sous_competence', 'critere'
    ).order_by('ordre')
    for lc in lignes_contrat:
        EvaluationLigne.objects.get_or_create(
            fiche_evaluation=fiche_eval, ligne_contrat=lc, defaults={'note': 'NE'})
    lignes_eval = fiche_eval.lignes_evaluation.select_related(
        'ligne_contrat__competence_pro', 'ligne_contrat__sous_competence',
        'ligne_contrat__critere', 'ligne_contrat__indicateur'
    ).order_by(
        'ligne_contrat__competence_pro__ordre',
        'ligne_contrat__competence_pro__code',
        'ligne_contrat__sous_competence__ordre',
        'ligne_contrat__critere__ordre',
        'ligne_contrat__ordre'
    )
    def _get_cp(le): return le.ligne_contrat.competence_pro
    def _get_sc(le): return le.ligne_contrat.sous_competence
    groupes_competences = []
    for cp, lignes_cp in groupby(lignes_eval, key=_get_cp):
        lignes_cp_list = list(lignes_cp)
        sous_competences = []
        for sc, lignes_sc in groupby(lignes_cp_list, key=_get_sc):
            sous_competences.append({'sous_competence': sc, 'lignes': list(lignes_sc)})
        groupes_competences.append({'competence_pro': cp, 'sous_competences': sous_competences})
    if request.method == 'POST':
        if fiche_eval.validee:
            messages.warning(request, "⚠️ Cette évaluation est déjà validée.")
            return redirect('core:fiche_evaluation_saisie', fiche_contrat_id, eleve_id)
        for le in lignes_eval:
            note_key = f'note_{le.id}'
            if note_key in request.POST:
                new_note = request.POST[note_key]
                if new_note in ['NE', '0', '1', '2', '3', '4']:
                    le.note = new_note
                    le.save()
        fiche_eval.compte_rendu = request.POST.get('compte_rendu', '')
        note_finale = fiche_eval.calculer_note_sur_20()
        action = request.POST.get('action', 'sauvegarder')
        if action == 'valider':
            fiche_eval.validee = True
            fiche_eval.date_validation = timezone.now()
            fiche_eval.save()
            messages.success(request, f"✅ Évaluation de {eleve.user.get_full_name()} validée ! Note : {note_finale}/20")
        else:
            fiche_eval.save()
            messages.success(request, f"💾 Sauvegardé. Note provisoire : {note_finale}/20")
        return redirect('core:evaluation_detail', pk=fiche_contrat.id)
    nb_total  = lignes_eval.count()
    nb_evalues = lignes_eval.exclude(note='NE').count()
    progression = int((nb_evalues / nb_total) * 100) if nb_total > 0 else 0
    poids_total = sum(float(lc.poids) for lc in lignes_contrat)
    return render(request, 'core/fiche_evaluation_saisie.html', {
        'fiche_contrat': fiche_contrat, 'eleve': eleve, 'fiche_eval': fiche_eval,
        'groupes_competences': groupes_competences, 'nb_total': nb_total, 'nb_evalues': nb_evalues,
        'progression': progression, 'poids_total': poids_total,
        'detail_calcul': fiche_eval.get_detail_calcul(),
    })


def fiche_evaluation_select_eleves(request, fiche_contrat_id):
    fiche_contrat = get_object_or_404(FicheContrat, id=fiche_contrat_id, createur=request.user)
    eleves = ProfilUtilisateur.objects.filter(
        classe=fiche_contrat.classe, type_utilisateur='eleve', compte_approuve=True, est_sorti=False
    ).select_related('user').order_by('user__last_name', 'user__first_name')
    deja_evalues = set(FicheEvaluation.objects.filter(fiche_contrat=fiche_contrat).values_list('eleve_id', flat=True))
    if request.method == 'POST':
        eleves_ids = request.POST.getlist('eleves')
        if eleves_ids:
            nb_crees = 0
            for eleve_id in eleves_ids:
                eleve = ProfilUtilisateur.objects.get(id=eleve_id)
                fiche_eval, created = FicheEvaluation.objects.get_or_create(
                    fiche_contrat=fiche_contrat, eleve=eleve)
                if created:
                    nb_crees += 1
                    for lc in fiche_contrat.lignes.all():
                        EvaluationLigne.objects.get_or_create(
                            fiche_evaluation=fiche_eval, ligne_contrat=lc, defaults={'note': 'NE'})
            messages.success(request, f"✅ {nb_crees} fiche(s) créée(s) !")
            return redirect('core:evaluation_detail', pk=fiche_contrat.id)
        else:
            messages.error(request, '❌ Sélectionnez au moins un élève.')
    return render(request, 'core/fiche_evaluation_select_eleves.html', {
        'fiche_contrat': fiche_contrat, 'eleves': eleves, 'deja_evalues': deja_evalues,
    })


def fiche_contrat_archiver(request, pk):
    fiche_contrat = get_object_or_404(FicheContrat, id=pk, createur=request.user)
    fiches_eleves = FicheEvaluation.objects.filter(fiche_contrat=fiche_contrat).select_related('eleve__user')
    annee = _annee_scolaire_courante()
    Archive.objects.create(
        titre=f"Évaluation – {fiche_contrat.titre_tp}",
        description=(f"fiche_contrat_id:{fiche_contrat.id} | Référentiel : {fiche_contrat.referentiel.nom} | Classe : {fiche_contrat.classe.nom}"),
        categorie='evaluations', fichier=None, createur=request.user, annee_scolaire=annee
    )
    count = 0
    for fe in fiches_eleves:
        if fe.note_sur_20 is None:
            fe.calculer_note_sur_20()
            fe.refresh_from_db()
        note = fe.note_sur_20
        note_str = f"{round(float(note), 2)}/20" if note else "non disponible"
        Notification.objects.create(
            destinataire=fe.eleve.user,
            titre=f"📋 Évaluation archivée – {fiche_contrat.titre_tp}",
            message=f"Votre évaluation a été archivée. Note : {note_str}.",
            type_notification='evaluation', lien=f'/eleve/fiche-evaluation/{fe.id}/'
        )
        count += 1
    fiche_contrat.actif = False
    fiche_contrat.save()
    messages.success(request, f'📦 "{fiche_contrat.titre_tp}" archivée. {count} élève(s) notifié(s) !')
    return redirect('core:evaluations_home')


def fiche_contrat_supprimer(request, pk):
    fiche_contrat = get_object_or_404(FicheContrat, id=pk, createur=request.user)
    if request.method == 'POST':
        titre = fiche_contrat.titre_tp
        fiche_contrat.delete()
        messages.success(request, f'🗑️ Fiche contrat "{titre}" supprimée définitivement !')
    return redirect('core:evaluations_home')


def generer_fiches_eleves(request, fiche_contrat_id):
    """✅ Fiche contrat imprimable — une par élève"""
    fiche_contrat = get_object_or_404(FicheContrat, id=fiche_contrat_id, createur=request.user)
    eleves = ProfilUtilisateur.objects.filter(
        ficheevaluation__fiche_contrat=fiche_contrat
    ).select_related('user').order_by('user__last_name').distinct()
    if not eleves.exists():
        eleves = ProfilUtilisateur.objects.filter(
            classe=fiche_contrat.classe, type_utilisateur='eleve',
            compte_approuve=True, est_sorti=False
        ).select_related('user').order_by('user__last_name')
    lignes_contrat = fiche_contrat.lignes.select_related(
        'competence_pro', 'sous_competence', 'critere', 'indicateur').order_by('ordre')
    cps_vus = set()
    competences_vises = []
    for ligne in lignes_contrat:
        if ligne.competence_pro and ligne.competence_pro.id not in cps_vus:
            cps_vus.add(ligne.competence_pro.id)
            competences_vises.append(ligne.competence_pro)
    competences_vises.sort(key=lambda x: x.code)
    nb_lignes = lignes_contrat.count()
    poids_auto = round(100 / nb_lignes, 2) if nb_lignes > 0 else 10.0
    savoirs_bruts = fiche_contrat.savoirs_associes or ""
    savoirs_dedupliques = list(dict.fromkeys(
        l.strip() for l in savoirs_bruts.splitlines() if l.strip()
    ))
    return render(request, 'core/fiche_contrat_print.html', {
        'fiche_contrat': fiche_contrat, 'eleves': eleves,
        'competences_vises': competences_vises, 'poids_auto': poids_auto,
        'savoirs_dedupliques': savoirs_dedupliques,
    })


generer_fiches_contrat = generer_fiches_eleves


def generer_fiches_evaluation(request, fiche_contrat_id):
    """✅ Fiche évaluation imprimable — une par élève avec CP/SC/critères"""
    fiche_contrat = get_object_or_404(FicheContrat, id=fiche_contrat_id, createur=request.user)
    fiches_eleves = FicheEvaluation.objects.filter(
        fiche_contrat=fiche_contrat, eleve__est_sorti=False
    ).select_related('eleve__user').order_by('eleve__user__last_name')
    nb_lignes_total = fiche_contrat.lignes.count()
    poids_auto = round(100 / nb_lignes_total, 2) if nb_lignes_total > 0 else 10.0

    def get_cp(l): return l.ligne_contrat.competence_pro
    def get_sc(l): return l.ligne_contrat.sous_competence

    donnees_impression = []
    for fe in fiches_eleves:
        lignes = EvaluationLigne.objects.filter(fiche_evaluation=fe).select_related(
            'ligne_contrat__competence_pro', 'ligne_contrat__sous_competence',
            'ligne_contrat__critere', 'ligne_contrat__indicateur'
        ).order_by('ligne_contrat__competence_pro__code', 'ligne_contrat__sous_competence__ordre', 'ligne_contrat__ordre')
        for ligne in lignes:
            if not ligne.ligne_contrat.poids or ligne.ligne_contrat.poids == 0:
                ligne.ligne_contrat.poids = poids_auto
        groupes_competences = []
        for cp, lignes_cp in groupby(lignes, key=get_cp):
            lignes_cp_list = list(lignes_cp)
            sous_competences = []
            for sc, lignes_sc in groupby(lignes_cp_list, key=get_sc):
                sous_competences.append({'sous_competence': sc, 'lignes': list(lignes_sc)})
            groupes_competences.append({
                'competence_pro': cp, 'lignes': lignes_cp_list, 'sous_competences': sous_competences,
            })
        donnees_impression.append({'eleve': fe.eleve, 'evaluation': fe, 'groupes_competences': groupes_competences})
    return render(request, 'core/fiche_evaluation_print.html', {
        'fiche_contrat': fiche_contrat, 'donnees_impression': donnees_impression, 'poids_auto': poids_auto,
    })


def valider_contrat(request, pk):
    """✅ UNE SEULE définition"""
    fiche_contrat = get_object_or_404(FicheContrat, id=pk, createur=request.user)
    if request.method == 'POST':
        fiche_contrat.contrat_valide = True
        fiche_contrat.save()
        messages.success(request, f"✅ Contrat '{fiche_contrat.titre_tp}' validé !")
    return redirect('core:generer_fiches_eleves', pk)


def valider_fiches_evaluation(request, pk):
    fiche_contrat = get_object_or_404(FicheContrat, id=pk, createur=request.user)
    if request.method == 'POST':
        for fiche_eval in FicheEvaluation.objects.filter(fiche_contrat=fiche_contrat):
            for ligne_eval in EvaluationLigne.objects.filter(fiche_evaluation=fiche_eval):
                note_key  = f'note_{ligne_eval.id}'
                poids_key = f'poids_{ligne_eval.id}'
                if note_key in request.POST:
                    v = request.POST[note_key]
                    ligne_eval.note = 'NE' if v == '-1' else v
                if poids_key in request.POST:
                    try:
                        ligne_eval.ligne_contrat.poids = float(request.POST[poids_key].replace(',', '.'))
                        ligne_eval.ligne_contrat.save()
                    except (ValueError, AttributeError):
                        pass
                ligne_eval.save()
            cr_key = f'compte_rendu_{fiche_eval.id}'
            if cr_key in request.POST:
                fiche_eval.compte_rendu = request.POST[cr_key]
            fiche_eval.calculer_note_sur_20()
            fiche_eval.validee = True
            fiche_eval.date_validation = timezone.now()
            fiche_eval.save()
        fiche_contrat.fiches_eval_valide = True
        fiche_contrat.save()
        messages.success(request, "✅ Toutes les fiches validées !")
    return redirect('core:generer_fiches_evaluation', fiche_contrat_id=pk)


def _get_donnees_page1_contrat(fiche_contrat):
    """
    Prépare les données de la page 1 (fiche contrat) :
    retourne (lignes_contrat, competences_vises dédupliquées triées, savoirs_dedupliques).
    """
    lignes_contrat = fiche_contrat.lignes.select_related(
        'competence_pro', 'sous_competence', 'critere', 'indicateur'
    ).order_by('ordre')

    cps_vus = set()
    competences_vises = []
    for ligne in lignes_contrat:
        if ligne.competence_pro and ligne.competence_pro.id not in cps_vus:
            cps_vus.add(ligne.competence_pro.id)
            competences_vises.append(ligne.competence_pro)
    competences_vises.sort(key=lambda x: x.code)

    savoirs_bruts = fiche_contrat.savoirs_associes or ""
    savoirs_dedupliques = list(dict.fromkeys(
        l.strip() for l in savoirs_bruts.splitlines() if l.strip()
    ))

    return lignes_contrat, competences_vises, savoirs_dedupliques


def _get_donnees_page2_evaluation(fiche_eval, fiche_contrat):
    """
    Prépare les données de la page 2 (fiche évaluation) :
    retourne (poids_auto, groupes_competences) groupés par compétence pro → sous-compétence.
    """
    nb_lignes_total = fiche_contrat.lignes.count()
    poids_auto = round(100 / nb_lignes_total, 2) if nb_lignes_total > 0 else 10.0

    def get_cp(l): return l.ligne_contrat.competence_pro
    def get_sc(l): return l.ligne_contrat.sous_competence

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

    for ligne in lignes_eval:
        if not ligne.ligne_contrat.poids or ligne.ligne_contrat.poids == 0:
            ligne.ligne_contrat.poids = poids_auto

    groupes_competences = []
    for cp, lignes_cp in groupby(lignes_eval, key=get_cp):
        lignes_cp_list = list(lignes_cp)
        sous_competences = []
        for sc, lignes_sc in groupby(lignes_cp_list, key=get_sc):
            sous_competences.append({
                'sous_competence': sc,
                'lignes': list(lignes_sc)
            })
        groupes_competences.append({
            'competence_pro': cp,
            'lignes': lignes_cp_list,
            'sous_competences': sous_competences,
        })

    return poids_auto, groupes_competences


def eleve_fiche_complete(request, pk):
    """
    Vue élève : affiche la fiche contrat + fiche évaluation en lecture seule.
    Clone exact des données de generer_fiches_eleves + generer_fiches_evaluation.
    """
    fiche_eval = get_object_or_404(FicheEvaluation, id=pk)

    # Sécurité : l'élève ne peut voir QUE sa propre fiche
    if request.user != fiche_eval.eleve.user:
        messages.error(request, "❌ Vous n'avez pas accès à cette fiche.")
        return redirect('core:dashboard_eleve')

    fiche_contrat = fiche_eval.fiche_contrat
    eleve         = fiche_eval.eleve

    lignes_contrat, competences_vises, savoirs_dedupliques = _get_donnees_page1_contrat(fiche_contrat)
    poids_auto, groupes_competences = _get_donnees_page2_evaluation(fiche_eval, fiche_contrat)

    if fiche_eval.note_sur_20 is None:
        fiche_eval.calculer_note_sur_20()

    return render(request, 'core/eleve_fiche_complete.html', {
        'fiche_contrat':       fiche_contrat,
        'fiche_eval':          fiche_eval,
        'eleve':               eleve,
        'competences_vises':   competences_vises,
        'savoirs_dedupliques': savoirs_dedupliques,
        'groupes_competences': groupes_competences,
        'poids_auto':          poids_auto,
    })


def eleve_voir_fiche_contrat(request, pk):
    fiche_eval = get_object_or_404(FicheEvaluation, id=pk)
    if request.user != fiche_eval.eleve.user:
        messages.error(request, "❌ Vous n'avez pas accès à cette fiche.")
        return redirect('core:dashboard_eleve')
    lignes_contrat = fiche_eval.fiche_contrat.lignes.select_related(
        'competence_pro', 'sous_competence', 'critere', 'indicateur').order_by('ordre')
    cps_uniques = set()
    for ligne in lignes_contrat:
        if ligne.competence_pro:
            cps_uniques.add(ligne.competence_pro)
    return render(request, 'core/eleve_fiche_contrat_view.html', {
        'fiche_contrat': fiche_eval.fiche_contrat, 'eleve': fiche_eval.eleve,
        'competences_vises': sorted(list(cps_uniques), key=lambda x: x.code),
    })


def eleve_voir_fiche_evaluation(request, pk):
    fiche_eval = get_object_or_404(FicheEvaluation, id=pk)
    if request.user != fiche_eval.eleve.user:
        messages.error(request, "❌ Vous n'avez pas accès à cette fiche.")
        return redirect('core:dashboard_eleve')
    lignes = EvaluationLigne.objects.filter(fiche_evaluation=fiche_eval).select_related(
        'ligne_contrat__competence_pro', 'ligne_contrat__sous_competence',
        'ligne_contrat__critere', 'ligne_contrat__indicateur'
    ).order_by(
        'ligne_contrat__competence_pro__ordre', 'ligne_contrat__competence_pro__code',
        'ligne_contrat__sous_competence__ordre', 'ligne_contrat__critere__ordre', 'ligne_contrat__ordre'
    )

    def get_cp(l): return l.ligne_contrat.competence_pro
    def get_sc(l): return l.ligne_contrat.sous_competence

    groupes_competences = []
    for cp, lignes_cp in groupby(lignes, key=get_cp):
        lignes_cp_list = list(lignes_cp)
        sous_competences = []
        for sc, lignes_sc in groupby(lignes_cp_list, key=get_sc):
            sous_competences.append({'sous_competence': sc, 'lignes': list(lignes_sc)})
        groupes_competences.append({'competence_pro': cp, 'sous_competences': sous_competences})
    return render(request, 'core/eleve_fiche_evaluation_view.html', {
        'fiche_contrat': fiche_eval.fiche_contrat, 'fiche_eval': fiche_eval,
        'eleve': fiche_eval.eleve, 'groupes_competences': groupes_competences,
    })


def api_competences_par_referentiel(request):
    referentiel_id = request.GET.get('referentiel_id')
    if not referentiel_id:
        return JsonResponse({'error': 'Id manquant'}, status=400)
    try:
        ref = Referentiel.objects.get(id=referentiel_id)
        blocs = BlocCompetence.objects.filter(referentiel=ref).order_by('id')
        data = []
        for bloc in blocs:
            comps_data = []
            for comp in Competence.objects.filter(bloc=bloc).order_by('id'):
                cps_data = []
                for cp in CompetenceProfessionnelle.objects.filter(competence=comp).order_by('id'):
                    connaissances_data = [
                        {'id': c.id, 'nom': c.nom}
                        for c in Connaissance.objects.filter(competence_pro=cp).order_by('id')
                    ]
                    scs_data = []
                    for sc in SousCompetence.objects.filter(competence_pro=cp).order_by('id'):
                        criteres_data = []
                        for crit in CritereEvaluation.objects.filter(sous_competence=sc).order_by('id'):
                            ind = IndicateurPerformance.objects.filter(critere=crit).first()
                            criteres_data.append({
                                'id': crit.id, 'nom': crit.nom,
                                'indicateur_id': ind.id if ind else 0
                            })
                        scs_data.append({'id': sc.id, 'nom': sc.nom, 'criteres': criteres_data})
                    cps_data.append({
                        'id': cp.id, 'code': cp.code, 'nom': cp.nom,
                        'connaissances': connaissances_data, 'sous_competences': scs_data
                    })
                comps_data.append({'id': comp.id, 'code': comp.code, 'nom': comp.nom, 'competences_pro': cps_data})
            data.append({'id': bloc.id, 'code': bloc.code, 'nom': bloc.nom, 'competences': comps_data})
        return JsonResponse(data, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def api_eleves_par_classe(request):
    classe_id = request.GET.get('classe_id')
    if not classe_id:
        return JsonResponse({'error': 'classe_id manquant'}, status=400)
    try:
        eleves = ProfilUtilisateur.objects.filter(
            classe_id=classe_id, user__is_active=True,
            type_utilisateur='eleve', compte_approuve=True, est_sorti=False
        ).select_related('user').order_by('user__last_name', 'user__first_name')
        return JsonResponse({'eleves': [{'id': e.id, 'nom': e.user.last_name, 'prenom': e.user.first_name} for e in eleves]})
    except Exception as e:
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


def contact(request):
    return render(request, 'core/contact.html')


def fiche_revision_create(request, dossier_id):
    dossier = get_object_or_404(Dossier, id=dossier_id)
    
    if request.method == 'POST':
        titre = request.POST.get('titre')
        # On ajoute createur=request.user pour satisfaire la base de données !
        fiche = FicheRevision.objects.create(
            titre=titre, 
            dossier=dossier, 
            createur=request.user
        )
        # Si l'utilisateur a envoyé un fichier CSV, l'importer immédiatement
        fichier_csv = request.FILES.get('fichier_csv')
        if fichier_csv:
            contenu_brut = fichier_csv.read()
            contenu = None
            for encodage in ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']:
                try:
                    contenu = contenu_brut.decode(encodage)
                    break
                except UnicodeDecodeError:
                    continue
            if contenu is None:
                messages.error(request, '❌ Impossible de lire le fichier (encodage non reconnu).')
            else:
                try:
                    reader = csv.reader(io.StringIO(contenu))
                    nb = 0
                    ordre_depart = fiche.cartes.count()
                    for i, row in enumerate(reader):
                        if len(row) < 2:
                            continue
                        question  = row[0].strip()
                        reponse   = row[1].strip()
                        image_url = row[2].strip() if len(row) > 2 else ''
                        if not question or not reponse:
                            continue
                        CarteRevision.objects.create(
                            fiche=fiche,
                            question=question,
                            reponse=reponse,
                            image_url=image_url,
                            ordre=ordre_depart + i,
                        )
                        nb += 1
                    if nb:
                        messages.success(request, f'✅ Fiche créée et {nb} carte(s) importée(s).')
                    else:
                        messages.success(request, '✅ Fiche créée (aucune carte importée).')
                except csv.Error as e:
                    messages.error(request, f'❌ Erreur de lecture CSV : {e}')
        else:
            messages.success(request, "Fiche créée !")

        # Rediriger vers la page du thème (comportement souhaité)
        return redirect('core:theme_detail', pk=dossier.theme.id)
        
    return render(request, 'core/fiche_revision_create.html', {'dossier': dossier})


def fiche_revision_detail(request, pk):
    fiche = get_object_or_404(FicheRevision, id=pk)
    if hasattr(request.user, 'profil') and request.user.profil.est_eleve():
        classe_eleve = request.user.profil.classe
        # La fiche est liée à un dossier -> thème -> classes. Vérifier l'appartenance de la classe.
        if not classe_eleve or not fiche.dossier or not fiche.dossier.theme.classes.filter(pk=classe_eleve.id).exists():
            messages.error(request, "❌ Vous n'avez pas accès à cette fiche.")
            return redirect('core:dashboard_eleve')
    cartes = fiche.cartes.all()
    is_prof = est_professeur(request.user)
    cartes_data = list(cartes.values('id', 'question', 'reponse'))
    return render(request, 'core/fiche_revision_detail.html', {
        'fiche': fiche,
        'cartes': cartes,
        'cartes_data': cartes_data,
        'is_prof': is_prof,
    })


def fiche_revision_import_csv(request, fiche_id):
    fiche = get_object_or_404(FicheRevision, id=fiche_id)
    if request.method != 'POST':
        return redirect('core:fiche_revision_detail', pk=fiche_id)

    fichier_csv = request.FILES.get('fichier_csv')
    if not fichier_csv:
        messages.error(request, '❌ Aucun fichier sélectionné.')
        return redirect('core:fiche_revision_detail', pk=fiche_id)

    # 1. Détection automatique de l'encodage
    contenu_brut = fichier_csv.read()
    contenu = None
    for encodage in ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']:
        try:
            contenu = contenu_brut.decode(encodage)
            break
        except UnicodeDecodeError:
            continue

    if contenu is None:
        messages.error(request, '❌ Impossible de lire le fichier (encodage non reconnu).')
        return redirect('core:fiche_revision_detail', pk=fiche_id)

    try:
        # 2. csv.reader — pas d'en-tête, colonnes positionnelles
        reader = csv.reader(io.StringIO(contenu))
        nb = 0
        ordre_depart = fiche.cartes.count()
        for i, row in enumerate(reader):
            if len(row) < 2:
                continue
            question  = row[0].strip()
            reponse   = row[1].strip()
            image_url = row[2].strip() if len(row) > 2 else ''
            if not question or not reponse:
                continue
            CarteRevision.objects.create(
                fiche=fiche,
                question=question,
                reponse=reponse,
                image_url=image_url,
                ordre=ordre_depart + i,
            )
            nb += 1

        if nb:
            messages.success(request, f'✅ {nb} carte(s) importée(s) avec succès.')
        else:
            messages.warning(request, '⚠️ Aucune carte importée (fichier vide ou données manquantes).')

    except csv.Error as e:
        messages.error(request, f'❌ Erreur de lecture CSV : {e}')

    return redirect('core:fiche_revision_detail', pk=fiche_id)


def carte_revision_delete(request, pk):
    carte = get_object_or_404(CarteRevision, id=pk)
    fiche_id = carte.fiche.id
    if request.method == 'POST':
        carte.delete()
        messages.success(request, '🗑️ Carte supprimée.')
    return redirect('core:fiche_revision_detail', pk=fiche_id)


def fiche_revision_delete(request, pk):
    fiche = get_object_or_404(FicheRevision, id=pk)
    dossier = fiche.dossier
    theme_id = dossier.theme.id if dossier and dossier.theme else None
    if request.method == 'POST':
        fiche.delete()
        messages.success(request, '🗑️ Fiche et ses cartes supprimées.')
    return redirect('core:theme_detail', pk=theme_id)


def qcm_gestion(request):
    """Page principale QCM : liste de tous les QCM + formulaire de création."""
    qcms = QCM.objects.filter(createur=request.user).select_related('theme', 'classe').annotate(
        nb_questions=Count('questions')
    ).order_by('-id')
    classes = Classe.objects.all().order_by('nom')
    themes  = Theme.objects.all().order_by('nom')
    fiches_map = {}
    for f in FicheRevision.objects.annotate(nb_cartes=Count('cartes')).order_by('titre'):
        tid = str(f.dossier.theme_id) if f.dossier and f.dossier.theme_id else 'None'
        if tid not in fiches_map:
            fiches_map[tid] = []
        fiches_map[tid].append({'id': f.id, 'titre': f.titre, 'nb': f.nb_cartes})
    return render(request, 'core/qcm_gestion.html', {
        'qcms': qcms,
        'classes': classes,
        'themes': themes,
        'fiches_par_theme_json': json.dumps(fiches_map),
    })


def qcm_create(request, theme_id):
    """Créer un QCM depuis un thème — 3 sources IA : PDF, texte, fiches de révision."""
    theme = get_object_or_404(Theme, id=theme_id)
    classes = Classe.objects.all().order_by('nom')
    fiches_revision = FicheRevision.objects.filter(theme=theme).annotate(
        nb_cartes=Count('cartes')
    ).order_by('titre')

    if request.method == 'POST':
        titre       = request.POST.get('titre', '').strip()
        classe_id   = request.POST.get('classe')
        date_limite = request.POST.get('date_limite')
        nb_q        = int(request.POST.get('nb_questions', 10))
        melange     = request.POST.get('melange_questions') == 'on'
        source_type = request.POST.get('source_type', 'texte')
        texte_src   = request.POST.get('texte_source', '').strip()
        pdf_src     = request.FILES.get('pdf_source')
        fiche_id    = request.POST.get('fiche_id')

        if not titre or not classe_id or not date_limite:
            messages.error(request, '❌ Titre, classe et date limite sont obligatoires.')
            return render(request, 'core/qcm_create.html', {
                'theme': theme, 'classes': classes, 'fiches_revision': fiches_revision
            })

        classe = get_object_or_404(Classe, id=classe_id)
        qcm = QCM.objects.create(
            theme=theme, titre=titre, classe=classe,
            createur=request.user, date_limite=date_limite,
            melange_questions=melange, actif=False,
        )

        ia_erreur = False
        questions  = None

        if source_type == 'fiches' and fiche_id:
            try:
                fiche  = FicheRevision.objects.get(id=fiche_id, theme=theme)
                cartes = list(fiche.cartes.all()[:nb_q])
                if cartes:
                    from .services import generer_distracteurs_depuis_cartes
                    questions = generer_distracteurs_depuis_cartes(cartes)
                    if not questions:
                        ia_erreur = True
                else:
                    messages.warning(request, '⚠️ La fiche sélectionnée ne contient aucune carte.')
                    ia_erreur = True
            except FicheRevision.DoesNotExist:
                messages.warning(request, '⚠️ Fiche introuvable.')
                ia_erreur = True
        else:
            texte_final = None
            if pdf_src:
                from .services import extraire_texte_pdf
                texte_final = extraire_texte_pdf(pdf_src)
                if not texte_final:
                    messages.warning(request, '⚠️ Impossible de lire le PDF. QCM créé sans questions IA.')
            if not texte_final and texte_src:
                texte_final = texte_src
            if texte_final:
                from .services import generer_qcm_depuis_texte
                questions = generer_qcm_depuis_texte(texte_final, nb_q)
                if not questions:
                    ia_erreur = True

        if questions:
            for i, q in enumerate(questions):
                QuestionQCM.objects.create(
                    qcm=qcm, enonce=q['enonce'],
                    choix_a=q['choix_a'], choix_b=q['choix_b'],
                    choix_c=q.get('choix_c', ''), choix_d=q.get('choix_d', ''),
                    bonne_reponse=q['bonne_reponse'], ordre=i,
                )
            messages.success(request, f'✅ QCM "{qcm.titre}" créé avec {len(questions)} questions générées par l\'IA !')
        elif ia_erreur:
            messages.warning(request, '⚠️ QCM créé mais la génération IA a échoué. Ajoutez les questions manuellement.')
        else:
            messages.success(request, f'✅ QCM "{qcm.titre}" créé. Ajoutez maintenant vos questions.')

        return redirect('core:qcm_edit', pk=qcm.id)

    return render(request, 'core/qcm_create.html', {
        'theme': theme, 'classes': classes, 'fiches_revision': fiches_revision
    })


def qcm_edit(request, pk):
    """Éditer un QCM : voir/ajouter des questions, activer/désactiver."""
    qcm = get_object_or_404(QCM, id=pk)
    if qcm.createur != request.user and not request.user.is_staff:
        messages.error(request, "❌ Vous n'êtes pas le créateur de ce QCM.")
        return redirect('core:gestion_themes')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_question':
            enonce     = request.POST.get('enonce', '').strip()
            choix_a    = request.POST.get('choix_a', '').strip()
            choix_b    = request.POST.get('choix_b', '').strip()
            choix_c    = request.POST.get('choix_c', '').strip()
            choix_d    = request.POST.get('choix_d', '').strip()
            bonne_rep  = request.POST.get('bonne_reponse', '').upper()
            if enonce and choix_a and choix_b and bonne_rep in ('A', 'B', 'C', 'D'):
                ordre = qcm.questions.count()
                QuestionQCM.objects.create(
                    qcm=qcm, enonce=enonce,
                    choix_a=choix_a, choix_b=choix_b,
                    choix_c=choix_c, choix_d=choix_d,
                    bonne_reponse=bonne_rep, ordre=ordre,
                )
                messages.success(request, '✅ Question ajoutée.')
            else:
                messages.error(request, '❌ Énoncé, choix A & B et bonne réponse sont obligatoires.')

        elif action == 'update_meta':
            titre = request.POST.get('titre', '').strip()
            classe_id = request.POST.get('classe_id', '').strip()
            date_limite_str = request.POST.get('date_limite', '').strip()
            if titre:
                qcm.titre = titre
            if classe_id:
                qcm.classe_id = int(classe_id)
            if date_limite_str:
                from django.utils.dateparse import parse_datetime
                dt = parse_datetime(date_limite_str)
                if dt:
                    qcm.date_limite = dt
            qcm.save()
            messages.success(request, '✅ Paramètres mis à jour.')

    questions    = qcm.questions.all()
    peut_activer = questions.count() >= 3
    classes      = Classe.objects.all().order_by('nom')
    return render(request, 'core/qcm_edit.html', {
        'qcm': qcm,
        'questions': questions,
        'peut_activer': peut_activer,
        'classes': classes,
    })


def question_edit(request, pk):
    """Modifier une question QCM (enonce, choix, bonne_reponse, image_url)."""
    question = get_object_or_404(QuestionQCM, id=pk)
    qcm      = question.qcm
    if qcm.createur != request.user and not request.user.is_staff:
        messages.error(request, "Vous n'êtes pas le créateur de ce QCM.")
        return redirect('core:qcm_gestion')
    if request.method == 'POST':
        enonce    = request.POST.get('enonce', '').strip()
        choix_a   = request.POST.get('choix_a', '').strip()
        choix_b   = request.POST.get('choix_b', '').strip()
        choix_c   = request.POST.get('choix_c', '').strip()
        choix_d   = request.POST.get('choix_d', '').strip()
        bonne_rep = request.POST.get('bonne_reponse', '').upper()
        image_url = request.POST.get('image_url', '').strip()
        if enonce and choix_a and choix_b and bonne_rep in ('A', 'B', 'C', 'D'):
            question.enonce       = enonce
            question.choix_a      = choix_a
            question.choix_b      = choix_b
            question.choix_c      = choix_c
            question.choix_d      = choix_d
            question.bonne_reponse = bonne_rep
            question.image_url    = image_url
            question.save()
            messages.success(request, 'Question mise à jour.')
        else:
            messages.error(request, 'Énoncé, choix A & B et bonne réponse sont obligatoires.')
    return redirect('core:qcm_edit', pk=qcm.id)


def question_delete(request, pk):
    """Supprimer une question QCM (POST uniquement)."""
    question = get_object_or_404(QuestionQCM, id=pk)
    qcm_id   = question.qcm.id
    if request.method == 'POST':
        question.delete()
        messages.success(request, '🗑️ Question supprimée.')
    return redirect('core:qcm_edit', pk=qcm_id)


def question_regenerer(request, pk):
    """Régénère une question via Gemini en conservant son contexte thématique."""
    question = get_object_or_404(QuestionQCM, id=pk)
    qcm = question.qcm
    if qcm.createur != request.user and not request.user.is_staff:
        messages.error(request, "Vous n'êtes pas le créateur de ce QCM.")
        return redirect('core:qcm_gestion')
    if request.method == 'POST':
        from .services import generer_une_question
        nouvelle = generer_une_question(sujet=question.enonce)
        if nouvelle:
            question.enonce        = nouvelle['enonce']
            question.choix_a       = nouvelle['choix_a']
            question.choix_b       = nouvelle['choix_b']
            question.choix_c       = nouvelle.get('choix_c', '')
            question.choix_d       = nouvelle.get('choix_d', '')
            question.bonne_reponse = nouvelle['bonne_reponse']
            question.image_url     = ''
            question.save()
            messages.success(request, 'Question régénérée par l\'IA.')
        else:
            messages.error(request, 'La régénération IA a échoué. Réessayez ou modifiez manuellement.')
    return redirect('core:qcm_edit', pk=qcm.id)


def qcm_passer(request, pk):
    """Page pour qu'un élève passe un QCM actif."""
    qcm = get_object_or_404(QCM, id=pk, actif=True)
    try:
        profil = request.user.profil
    except ProfilUtilisateur.DoesNotExist:
        return redirect('core:dashboard_eleve')

    # Vérifier que l'élève est dans la bonne classe
    if profil.classe != qcm.classe:
        messages.error(request, 'Ce QCM n\'est pas disponible pour votre classe.')
        return redirect('core:dashboard_eleve')

    # Vérifier si déjà terminé
    session_existante = SessionQCM.objects.filter(qcm=qcm, eleve=profil, termine=True).first()
    if session_existante:
        return redirect('core:qcm_resultats', pk=session_existante.id)

    questions = list(qcm.questions.all())
    if qcm.melange_questions:
        import random
        random.shuffle(questions)

    import random as _rnd
    import hashlib

    def _choix_melanges(pid, q):
        """Retourne [(label_affiche, texte, lettre_orig), ...] avec labels A/B/C/D positionnels."""
        orig = [('A', q.choix_a), ('B', q.choix_b)]
        if q.choix_c: orig.append(('C', q.choix_c))
        if q.choix_d: orig.append(('D', q.choix_d))
        # Seed via MD5 pour une distribution vraiment diverse même avec petits IDs
        seed_str = f"{pid}:{q.id}".encode()
        seed = int(hashlib.md5(seed_str).hexdigest()[:12], 16)
        _rnd.Random(seed).shuffle(orig)
        letters = 'ABCD'
        return [(letters[i], orig[i][1], orig[i][0]) for i in range(len(orig))]
        # (label_positionnel, texte_choix, lettre_originale)

    questions_data = [
        {'q': q, 'choices': _choix_melanges(profil.id, q)}
        for q in questions
    ]

    if request.method == 'POST':
        reponses = {}
        nb_bonnes = 0
        for q in qcm.questions.all():
            label_poste = request.POST.get(f'q_{q.id}', '').upper()
            # Reconstruire le shuffle pour trouver la lettre originale soumise
            choix_melanges = _choix_melanges(profil.id, q)
            # Mapping label_positionnel -> lettre_originale
            pos_to_orig = {c[0]: c[2] for c in choix_melanges}
            lettre_orig = pos_to_orig.get(label_poste, '')
            reponses[str(q.id)] = lettre_orig  # on stocke la lettre ORIGINALE
            if lettre_orig and lettre_orig == q.bonne_reponse.upper():
                nb_bonnes += 1

        total = qcm.questions.count()
        note = round((nb_bonnes / total) * 20, 2) if total > 0 else 0

        session, _ = SessionQCM.objects.get_or_create(qcm=qcm, eleve=profil)
        session.reponses           = reponses
        session.nb_bonnes_reponses = nb_bonnes
        session.note_sur_20        = note
        session.date_soumission    = timezone.now()
        session.termine            = True
        session.save()
        return redirect('core:qcm_resultats', pk=session.id)

    return render(request, 'core/qcm_passer.html', {
        'qcm': qcm,
        'questions_data': questions_data,
        'nb_questions': len(questions_data),
    })


def qcm_resultats(request, pk):
    """Affiche les résultats d'une session QCM pour l'élève."""
    session = get_object_or_404(SessionQCM, id=pk)
    try:
        profil = request.user.profil
    except ProfilUtilisateur.DoesNotExist:
        return redirect('core:dashboard_eleve')

    # Seul l'élève concerné ou un prof peut voir les résultats
    if session.eleve != profil and not profil.est_prof():
        messages.error(request, 'Accès non autorisé.')
        return redirect('core:dashboard_eleve')

    qcm       = session.qcm
    questions = qcm.questions.all()
    reponses  = session.reponses  # dict str(q.id) -> lettre_reponse

    recap = []
    for q in questions:
        rep_eleve = reponses.get(str(q.id), '')
        correct   = rep_eleve.upper() == q.bonne_reponse.upper() if rep_eleve else False
        # libellé du choix selon lettre
        choix_map = {
            'A': q.choix_a, 'B': q.choix_b,
            'C': q.choix_c, 'D': q.choix_d,
        }
        recap.append({
            'question':       q,
            'rep_eleve':      rep_eleve.upper() if rep_eleve else '—',
            'rep_eleve_texte': choix_map.get(rep_eleve.upper(), '—') if rep_eleve else 'Sans réponse',
            'bonne_rep_texte': choix_map.get(q.bonne_reponse, ''),
            'correct':        correct,
        })

    return render(request, 'core/qcm_resultats.html', {
        'session':       session,
        'qcm':           qcm,
        'recap':         recap,
        'total':         questions.count(),
        'nb_mauvaises':  questions.count() - session.nb_bonnes_reponses,
    })


def qcm_resultats_prof(request, pk):
    """Vue professeur : résultats de TOUS les élèves pour un QCM."""
    qcm = get_object_or_404(QCM, pk=pk)
    sessions_qs = (SessionQCM.objects
                   .filter(qcm=qcm, termine=True)
                   .select_related('eleve__user')
                   .order_by('-note_sur_20'))
    total_q = qcm.questions.count()
    nb_passes = sessions_qs.count()
    moyenne = round(sum(s.note_sur_20 for s in sessions_qs) / nb_passes, 2) if nb_passes else None

    def _color(note):
        if note >= 16: return 'excellent'
        if note >= 12: return 'bien'
        if note >= 10: return 'passable'
        return 'echec'

    sessions_data = [
        {
            'session': s,
            'color':   _color(s.note_sur_20),
            'pct':     round((s.note_sur_20 / 20) * 100),
        }
        for s in sessions_qs
    ]

    # Analyse des fautes par question
    questions = list(qcm.questions.all())
    questions_stats = []
    for q in questions:
        nb_ok = 0
        nb_ko = 0
        for s in sessions_qs:
            rep = (s.reponses or {}).get(str(q.id), '')
            if rep and rep.upper() == q.bonne_reponse.upper():
                nb_ok += 1
            elif rep:
                nb_ko += 1
        nb_sans = nb_passes - nb_ok - nb_ko
        pct_ok = round((nb_ok / nb_passes) * 100) if nb_passes else 0
        pct_color = '#2ab090' if pct_ok >= 70 else ('#f59e0b' if pct_ok >= 40 else '#ef4444')
        questions_stats.append({
            'question':  q,
            'nb_ok':     nb_ok,
            'nb_ko':     nb_ko,
            'nb_sans':   nb_sans,
            'pct_ok':    pct_ok,
            'pct_color': pct_color,
        })
    questions_stats.sort(key=lambda x: x['pct_ok'])  # plus difficile en premier

    return render(request, 'core/qcm_resultats_prof.html', {
        'qcm':             qcm,
        'sessions_data':   sessions_data,
        'questions_stats': questions_stats,
        'total_q':         total_q,
        'nb_passes':       nb_passes,
        'moyenne':         moyenne,
    })


def qcm_archiver(request, pk):
    """Archive un QCM : crée une Archive, notifie les élèves, désactive le QCM."""
    qcm = get_object_or_404(QCM, pk=pk, createur=request.user)
    if request.method != 'POST':
        return redirect('core:qcm_resultats_prof', pk=pk)
    sessions_qs = SessionQCM.objects.filter(qcm=qcm, termine=True).select_related('eleve__user')
    nb_passes = sessions_qs.count()
    moyenne_val = round(sum(s.note_sur_20 for s in sessions_qs) / nb_passes, 1) if nb_passes else None
    annee = _annee_scolaire_courante()
    desc_parts = [
        f"qcm_id:{qcm.id}",
        f"Classe : {qcm.classe.nom}",
        f"Questions : {qcm.questions.count()}",
        f"Élèves ayant passé : {nb_passes}",
    ]
    if moyenne_val is not None:
        desc_parts.append(f"Moyenne : {moyenne_val}/20")
    archive = Archive.objects.create(
        titre=f"QCM \u2013 {qcm.titre}",
        description=" | ".join(desc_parts),
        categorie='evaluations',
        fichier=None,
        createur=request.user,
        annee_scolaire=annee,
    )
    for s in sessions_qs:
        note_str = f"{round(float(s.note_sur_20), 1)}/20"
        Notification.objects.create(
            destinataire=s.eleve.user,
            titre=f"\U0001f4cb QCM archiv\u00e9 \u2013 {qcm.titre}",
            message=f"Le QCM \u00ab {qcm.titre} \u00bb a \u00e9t\u00e9 archiv\u00e9. Votre note\u00a0: {note_str}.",
            type_notification='evaluation',
            lien=f'/qcm/session/{s.id}/resultats/',
        )
    qcm.actif = False
    qcm.save()
    messages.success(request, f'\U0001f4e6 QCM \u00ab {qcm.titre} \u00bb archiv\u00e9. {nb_passes} \u00e9l\u00e8ve(s) notifi\u00e9(s)\u00a0!')
    return redirect('core:archive_detail', pk=archive.pk)


def qcm_toggle_actif(request, pk):
    """Activer / désactiver un QCM (POST uniquement)."""
    qcm = get_object_or_404(QCM, id=pk)
    if request.method == 'POST':
        if not qcm.actif and qcm.questions.count() < 3:
            messages.error(request, '❌ Impossible d\'activer : il faut au moins 3 questions.')
        else:
            qcm.actif = not qcm.actif
            qcm.save()
            etat = 'activé' if qcm.actif else 'désactivé'
            messages.success(request, f'✅ QCM {etat}.')
    return redirect('core:qcm_edit', pk=pk)


def qcm_delete(request, pk):
    """Supprimer un QCM et toutes ses questions (POST uniquement)."""
    qcm = get_object_or_404(QCM, id=pk)
    if request.method == 'POST':
        titre = qcm.titre
        qcm.delete()
        messages.success(request, f'QCM "{titre}" supprimé.')
    return redirect('core:qcm_gestion')


def qcm_creer_depuis_dashboard(request):
    """Créer un QCM depuis le dashboard — 3 sources IA : PDF, texte, fiches de révision."""
    if request.method != 'POST':
        return redirect('core:dashboard_professeur')

    titre       = request.POST.get('titre', '').strip()
    theme_id    = request.POST.get('theme_id')
    classe_id   = request.POST.get('classe')
    date_limite = request.POST.get('date_limite')
    nb_q        = int(request.POST.get('nb_questions', 10))
    melange     = request.POST.get('melange_questions') == 'on'
    source_type = request.POST.get('source_type', 'texte')
    texte_src   = request.POST.get('texte_source', '').strip()
    pdf_src     = request.FILES.get('pdf_source')
    fiche_id    = request.POST.get('fiche_id')

    # Debug : log ce qui est reçu
    print(f"[QCM-DEBUG] source_type={source_type!r} | pdf_src={pdf_src} | texte_len={len(texte_src)} | fiche_id={fiche_id!r}")
    print(f"[QCM-DEBUG] FILES keys: {list(request.FILES.keys())}")

    if not titre or not theme_id or not classe_id or not date_limite:
        messages.error(request, '❌ Titre, thème, classe et date limite sont obligatoires.')
        return redirect('core:dashboard_professeur')

    theme  = get_object_or_404(Theme, id=theme_id)
    classe = get_object_or_404(Classe, id=classe_id)

    qcm = QCM.objects.create(
        theme=theme, titre=titre, classe=classe,
        createur=request.user, date_limite=date_limite,
        melange_questions=melange, actif=False,
    )

    ia_erreur = False
    questions  = None

    if source_type == 'fiches' and fiche_id:
        try:
            fiche  = FicheRevision.objects.get(id=fiche_id)
            cartes = list(fiche.cartes.all()[:nb_q])
            if cartes:
                from .services import generer_distracteurs_depuis_cartes
                questions = generer_distracteurs_depuis_cartes(cartes)
                if not questions:
                    ia_erreur = True
            else:
                ia_erreur = True
        except FicheRevision.DoesNotExist:
            ia_erreur = True
    else:
        texte_final = None
        if pdf_src:
            from .services import extraire_texte_pdf
            texte_final = extraire_texte_pdf(pdf_src)
            if not texte_final:
                print("[QCM-DEBUG] PDF recu mais extraction a echoue (PDF scan ou vide)")
                messages.warning(request, 'Le PDF ne contient pas de texte lisible (PDF scanné ou image). Essayez avec un PDF contenant du texte natif, ou utilisez la source Texte libre.')
                ia_erreur = True
        elif source_type == 'pdf':
            # L'utilisateur a choisi PDF mais aucun fichier n'est arrivé
            print("[QCM-DEBUG] source_type=pdf mais aucun fichier dans request.FILES")
            messages.warning(request, 'Aucun fichier PDF reçu. Vérifiez que le fichier est bien sélectionné.')
            ia_erreur = True
        if not texte_final and texte_src:
            ia_erreur = False  # reset si on a du texte
            texte_final = texte_src
        if texte_final:
            from .services import generer_qcm_depuis_texte
            questions = generer_qcm_depuis_texte(texte_final, nb_q)
            if not questions:
                print("[QCM-DEBUG] Gemini n'a retourne aucune question valide")
                ia_erreur = True

    if questions:
        for i, q in enumerate(questions):
            QuestionQCM.objects.create(
                qcm=qcm, enonce=q['enonce'],
                choix_a=q['choix_a'], choix_b=q['choix_b'],
                choix_c=q.get('choix_c', ''), choix_d=q.get('choix_d', ''),
                bonne_reponse=q['bonne_reponse'], ordre=i,
            )
        messages.success(request, f'✅ QCM "{qcm.titre}" créé avec {len(questions)} questions générées par l\'IA !')
    elif ia_erreur:
        messages.warning(request, '⚠️ QCM créé mais la génération IA a échoué. Ajoutez les questions manuellement.')
    else:
        messages.success(request, f'✅ QCM "{qcm.titre}" créé. Ajoutez maintenant vos questions.')

    return redirect('core:qcm_edit', pk=qcm.id)


def mo_create(request, theme_id=None, atelier_id=None):
    """Formulaire de création d'un mode opératoire (vide ou généré par IA)."""
    from django.db.models import Max as DjMax
    theme = get_object_or_404(Theme, id=theme_id) if theme_id else None
    atelier = get_object_or_404(Atelier, id=atelier_id) if atelier_id else None

    if request.method == 'POST':
        titre = request.POST.get('titre', '').strip()
        description = request.POST.get('description', '').strip()
        if not titre:
            messages.error(request, '❌ Le titre est obligatoire.')
            return render(request, 'core/mo_create.html', {'theme': theme, 'atelier': atelier})

        mo = ModeOperatoire.objects.create(
            titre=titre,
            description=description,
            theme=theme,
            atelier=atelier,
            createur=request.user,
        )

        texte_src = request.POST.get('texte_source', '').strip()
        pdf_file = request.FILES.get('pdf_source')
        texte_final = ''

        if pdf_file:
            from .services import extraire_texte_pdf
            texte_final = extraire_texte_pdf(pdf_file) or ''

        if not texte_final and texte_src:
            texte_final = texte_src

        if texte_final:
            from .services import generer_mode_operatoire
            lignes = generer_mode_operatoire(texte_final, titre)
            if lignes:
                lignes = lignes[:10]  # Plafonner à 10 phases max
                for l in lignes:
                    LigneModeOperatoire.objects.create(
                        mode_operatoire=mo,
                        ordre=l.get('ordre', 0),
                        phase=l.get('phase', ''),
                        operations=l.get('operations', ''),
                        materiels=l.get('materiels', ''),
                        controle=l.get('controle', ''),
                        risques_sante=l.get('risques_sante', ''),
                        risques_environnement=l.get('risques_environnement', ''),
                    )
                messages.success(request, f'✅ Mode opératoire "{mo.titre}" créé avec {len(lignes)} phases générées par l\'IA !')
            else:
                messages.warning(request, '⚠️ Mode opératoire créé, mais la génération IA a échoué. Remplissez les phases manuellement.')
        else:
            messages.success(request, f'✅ Mode opératoire "{mo.titre}" créé. Ajoutez les phases manuellement.')

        return redirect('core:mo_edit', pk=mo.id)

    return render(request, 'core/mo_create.html', {'theme': theme, 'atelier': atelier})


def mo_edit(request, pk):
    """Tableau complet éditable du mode opératoire."""
    mo = get_object_or_404(ModeOperatoire, id=pk)
    if mo.createur != request.user and not request.user.is_staff:
        messages.error(request, '❌ Accès refusé.')
        return redirect('core:dashboard_professeur')
    lignes = mo.lignes.all().order_by('ordre')
    return render(request, 'core/mo_edit.html', {'mo': mo, 'lignes': lignes})


def mo_view(request, pk):
    """Vue lecture seule d'un mode opératoire — accessible aux élèves si visible_eleves=True."""
    mo = get_object_or_404(ModeOperatoire, id=pk, actif=True)
    is_eleve = hasattr(request.user, 'profil') and request.user.profil.est_eleve()
    if is_eleve:
        if not mo.visible_eleves:
            messages.error(request, "❌ Ce mode opératoire n'est pas encore accessible.")
            return redirect('core:dashboard_eleve')
        if mo.atelier and mo.atelier.classe != request.user.profil.classe:
            messages.error(request, "❌ Accès refusé.")
            return redirect('core:dashboard_eleve')
    else:
        # Professeur : vérifier que c'est le sien (ou staff)
        if mo.createur != request.user and not request.user.is_staff:
            return redirect('core:mo_edit', pk=pk)
    lignes = mo.lignes.all().order_by('ordre')
    return render(request, 'core/mo_view.html', {'mo': mo, 'lignes': lignes})


def mo_update(request, pk):
    """Sauvegarde le titre et la description du mode opératoire (POST)."""
    if request.method != 'POST':
        return redirect('core:mo_edit', pk=pk)
    mo = get_object_or_404(ModeOperatoire, id=pk)
    if mo.createur != request.user and not request.user.is_staff:
        messages.error(request, '❌ Accès refusé.')
        return redirect('core:dashboard_professeur')
    titre = request.POST.get('titre', '').strip()
    if not titre:
        messages.error(request, '❌ Le titre ne peut pas être vide.')
        return redirect('core:mo_edit', pk=pk)
    mo.titre = titre
    mo.description = request.POST.get('description', '').strip()
    mo.save()
    messages.success(request, '✅ Mode opératoire sauvegardé.')
    return redirect('core:mo_edit', pk=pk)


def mo_toggle_visible_eleves(request, pk):
    """Publie ou masque le mode opératoire pour les élèves (POST)."""
    if request.method != 'POST':
        return redirect('core:mo_edit', pk=pk)
    mo = get_object_or_404(ModeOperatoire, id=pk)
    if mo.createur != request.user and not request.user.is_staff:
        messages.error(request, '❌ Accès refusé.')
        return redirect('core:dashboard_professeur')
    mo.visible_eleves = not mo.visible_eleves
    mo.save()
    etat = 'publié aux élèves' if mo.visible_eleves else 'masqué aux élèves'
    messages.success(request, f'✅ Mode opératoire {etat}.')
    return redirect('core:mo_edit', pk=pk)


def ligne_update(request, pk):
    """Mise à jour d'une ligne (POST uniquement)."""
    if request.method != 'POST':
        return redirect('core:dashboard_professeur')
    ligne = get_object_or_404(LigneModeOperatoire, id=pk)
    if ligne.mode_operatoire.createur != request.user and not request.user.is_staff:
        messages.error(request, '❌ Accès refusé.')
        return redirect('core:dashboard_professeur')

    ligne.phase = request.POST.get('phase', ligne.phase)
    ligne.operations = request.POST.get('operations', ligne.operations)
    ligne.materiels = request.POST.get('materiels', ligne.materiels)
    ligne.controle = request.POST.get('controle', ligne.controle)
    ligne.risques_sante = request.POST.get('risques_sante', ligne.risques_sante)
    ligne.risques_environnement = request.POST.get('risques_environnement', ligne.risques_environnement)
    ligne.ordre = request.POST.get('ordre', ligne.ordre)

    if 'schema_image' in request.FILES:
        ligne.schema_image = request.FILES['schema_image']

    ligne.save()
    messages.success(request, '✅ Phase sauvegardée.')
    return redirect('core:mo_edit', pk=ligne.mode_operatoire.id)


def ligne_regenerer(request, pk, colonne):
    """Régénère le contenu d'une cellule via Gemini (AJAX POST)."""
    if request.method != 'POST':
        return JsonResponse({'succes': False, 'erreur': 'Méthode non autorisée'}, status=405)
    ligne = get_object_or_404(LigneModeOperatoire, id=pk)
    if ligne.mode_operatoire.createur != request.user and not request.user.is_staff:
        return JsonResponse({'succes': False, 'erreur': 'Accès refusé'}, status=403)

    colonnes_autorisees = {'operations', 'materiels', 'controle', 'risques_sante', 'risques_environnement'}
    if colonne not in colonnes_autorisees:
        return JsonResponse({'succes': False, 'erreur': 'Colonne non autorisée'}, status=400)

    from .services import regenerer_ligne
    contenu = regenerer_ligne(ligne.mode_operatoire.titre, ligne.phase, colonne)
    if contenu:
        setattr(ligne, colonne, contenu)
        ligne.save()
        return JsonResponse({'succes': True, 'contenu': contenu})
    return JsonResponse({'succes': False, 'erreur': 'La génération IA a échoué.'})


def ligne_add(request, mo_id):
    """Crée une ligne vide à la fin du MO (POST uniquement)."""
    if request.method != 'POST':
        return redirect('core:dashboard_professeur')
    mo = get_object_or_404(ModeOperatoire, id=mo_id)
    if mo.createur != request.user and not request.user.is_staff:
        messages.error(request, '❌ Accès refusé.')
        return redirect('core:dashboard_professeur')
    from django.db.models import Max as DjMax2
    dernier = mo.lignes.aggregate(m=DjMax2('ordre'))['m'] or 0
    LigneModeOperatoire.objects.create(
        mode_operatoire=mo,
        ordre=dernier + 1,
        phase='Nouvelle phase',
        operations='',
        materiels='',
        controle='',
        risques_sante='',
        risques_environnement='',
    )
    messages.success(request, '✅ Phase ajoutée.')
    return redirect('core:mo_edit', pk=mo.id)


def ligne_delete(request, pk):
    """Supprime une ligne (POST uniquement)."""
    if request.method != 'POST':
        return redirect('core:dashboard_professeur')
    ligne = get_object_or_404(LigneModeOperatoire, id=pk)
    mo_id = ligne.mode_operatoire.id
    if ligne.mode_operatoire.createur != request.user and not request.user.is_staff:
        messages.error(request, '❌ Accès refusé.')
        return redirect('core:dashboard_professeur')
    ligne.delete()
    messages.success(request, '✅ Phase supprimée.')
    return redirect('core:mo_edit', pk=mo_id)


def mo_delete(request, pk):
    """Supprime un MO et toutes ses lignes (POST uniquement)."""
    if request.method != 'POST':
        return redirect('core:dashboard_professeur')
    mo = get_object_or_404(ModeOperatoire, id=pk)
    if mo.createur != request.user and not request.user.is_staff:
        messages.error(request, '❌ Accès refusé.')
        return redirect('core:dashboard_professeur')
    theme_id = mo.theme_id
    atelier_id = mo.atelier_id
    mo.delete()
    messages.success(request, '✅ Mode opératoire supprimé.')
    if theme_id:
        return redirect('core:theme_detail', pk=theme_id)
    if atelier_id:
        return redirect('core:atelier_detail', pk=atelier_id)
    return redirect('core:dashboard_professeur')


def gestion_modes_operatoires(request):
    """Liste globale de tous les modes opératoires actifs du professeur."""
    modes_operatoires = ModeOperatoire.objects.filter(
        actif=True
    ).select_related('theme', 'atelier', 'createur').order_by('-date_creation')
    return render(request, 'core/gestion_modes_operatoires.html', {
        'modes_operatoires': modes_operatoires,
        'nb_total': modes_operatoires.count(),
    })


def assistant_ia(request):
    """Page principale de l'assistant IA Gemini."""
    return render(request, 'core/assistant_ia.html')


def assistant_ia_query(request):
    """Endpoint pour les questions à l'assistant IA."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST requis'}, status=405)

    try:
        # Gestion fichier joint (multipart) ou JSON
        if request.content_type and 'multipart' in request.content_type:
            question = request.POST.get('question', '')
            historique = json.loads(request.POST.get('historique', '[]'))
            fichier = request.FILES.get('fichier')

            fichier_bytes = None
            fichier_mime = None
            fichier_nom = None

            if fichier:
                fichier_bytes = fichier.read()
                fichier_mime = fichier.content_type
                fichier_nom = fichier.name
        else:
            data = json.loads(request.body)
            question = data.get('question', '')
            historique = data.get('historique', [])
            fichier_bytes = None
            fichier_mime = None
            fichier_nom = None

        reponse = assistant_recherche(
            question=question,
            historique=historique,
            fichier_bytes=fichier_bytes,
            fichier_mime=fichier_mime,
            fichier_nom=fichier_nom,
        )
        return JsonResponse({'reponse': reponse})

    except Exception as e:
        print(f"[assistant_ia_query] Erreur : {e}")
        return JsonResponse({'error': str(e)}, status=500)


def assistant_tts(request):
    """Endpoint TTS — synthèse vocale via Edge-TTS."""
    import json
    from django.http import JsonResponse, HttpResponse
    from .services import synthetiser_voix

    if request.method != 'POST':
        return JsonResponse({'error': 'POST requis'}, status=405)

    try:
        data = json.loads(request.body)
        texte = data.get('texte', '').strip()
        voice_id = data.get('voice_id', 'fr-FR-DeniseNeural')

        if not texte:
            return JsonResponse({'error': 'Texte vide'}, status=400)

        audio_bytes = synthetiser_voix(texte, voice_id=voice_id)

        if not audio_bytes:
            return JsonResponse({'error': 'Le serveur n\'a pas pu générer l\'audio. Vérifiez les logs.'}, status=500)

        response = HttpResponse(audio_bytes, content_type='audio/mpeg')
        response['Content-Disposition'] = 'inline; filename="tts.mp3"'
        return response

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


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
        'nb_portfolios':         Portfolio.objects.filter(actif=True, eleve__classe__niveau__nom='BAC_PRO').count() if Classe.objects.filter(niveau__nom='BAC_PRO').exists() else None,
        'nb_ateliers':           Atelier.objects.filter(actif=True).count(),
        'nb_evaluations':        FicheContrat.objects.filter(createur=request.user, actif=True).count(),
        'nb_archives':           Archive.objects.filter(actif=True).count(),
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


def communications_list(request):
    """Liste les messages d'élèves destinés au professeur connecté."""
    communications = MessageEleve.objects.filter(
        professeur=request.user.profil
    ).select_related(
        'eleve__user', 'eleve__classe'
    ).order_by('-date_envoi')
    context = {'communications': communications}
    return render(request, 'core/communications_list.html', context)


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
            'mes_pfmp': PFMP.objects.filter(classes=classe, actif=True).order_by('date_debut'),
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


VILLES_ORIGINE = [
    'Roubaix', 'Tourcoing', 'Hem', 'Croix', 'Halluin', 'Wasquehal',
    "Villeneuve d'Ascq", 'Marcq en Baroeul', 'Lille', 'Mons en Baroeul',
    'Lys lez Lannoy', 'Leers', 'Saint André', 'Marquette-lez-Lille',
    'Linselles', 'Wattrelos', 'Mouvaux', 'Roncq', 'Lambersart', 'Ronchin', 'Cysoing',
]


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
