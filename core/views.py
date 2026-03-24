
"""Facade module: expose the merged AST-generated views.

This file imports all symbols from `views_merged_ast.py` (the cleaned merge)
and provides small compatibility aliases expected by `core/urls.py`.
"""

from .views_merged_ast import *  # noqa: F401,F403

# Compat alias: older URLs expect `export_annuel_complet`.
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
    
	# Alias attendu par core.urls

# Compat alias historique : `core/urls.py` importe `export_annuel_complet`.
try:
	export_annuel_complet = archives_export
except NameError:
	export_annuel_complet = None

