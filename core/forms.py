from django import forms
from .models import ProfilUtilisateur, Theme, PFMP  # <-- J'ai ajouté PFMP ici

class FormulaireSortie(forms.ModelForm):
    """
    Formulaire pour marquer un élève comme sorti
    avec gestion dynamique du diplôme
    """
    class Meta:
        model = ProfilUtilisateur
        fields = [
            'date_sortie',
            'annee_scolaire_sortie',
            'raison_sortie',
            'type_diplome_obtenu',
            'mention_obtenue',
            'poursuite_etudes',
            'type_poursuite'
        ]
        widgets = {
            'date_sortie': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control',
                'required': True
            }),
            'annee_scolaire_sortie': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: 2024-2025',
                'required': True
            }),
            'raison_sortie': forms.Select(attrs={
                'class': 'form-control',
                'id': 'raison_sortie',
                'required': True
            }),
            'type_diplome_obtenu': forms.Select(attrs={
                'class': 'form-control',
            }),
            'mention_obtenue': forms.Select(attrs={
                'class': 'form-control',
            }),
            'poursuite_etudes': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'id': 'poursuite_etudes'
            }),
            'type_poursuite': forms.Select(attrs={
                'class': 'form-control',
                'id': 'type_poursuite'
            }),
        }
        labels = {
            'date_sortie': 'Date de sortie *',
            'annee_scolaire_sortie': 'Année scolaire *',
            'raison_sortie': 'Raison de la sortie *',
            'type_diplome_obtenu': 'Type de diplôme',
            'mention_obtenue': 'Mention obtenue',
            'poursuite_etudes': 'Poursuite d\'études',
            'type_poursuite': 'Type de poursuite',
        }

class ThemeForm(forms.ModelForm):
    class Meta:
        model = Theme
        fields = ['nom', 'description', 'classes', 'visible_eleves', 'ressources_html', 'ordre']
        widgets = {
            'nom': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: DTU 20.1 - Maçonnerie'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Description courte du thème...'
            }),
            'classes': forms.SelectMultiple(attrs={'class': 'form-control'}),
            'visible_eleves': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'ressources_html': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 10,
                'placeholder': 'Collez ici votre code HTML (iframes Canva, YouTube, liens, images...)',
                'style': 'font-family: monospace; font-size: 0.9rem;'
            }),
            'ordre': forms.NumberInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'nom': 'Nom du thème',
            'description': 'Description',
            'classes': 'Classes',
            'visible_eleves': 'Visible pour les élèves',
            'ressources_html': '📎 Ressources intégrées (HTML/iframes)',
            'ordre': 'Ordre d\'affichage',
        }

# --- AJOUT DU FORMULAIRE MANQUANT ---
class PFMPForm(forms.ModelForm):
    class Meta:
        model = PFMP
        fields = ['classes', 'titre', 'description', 'date_debut', 'date_fin', 'type_contenu', 'fichier', 'lien_externe', 'code_iframe']
        widgets = {
            'classes': forms.SelectMultiple(attrs={'class': 'form-control', 'size': '5'}),
            'titre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Stage Janvier'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'date_debut': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'date_fin': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'type_contenu': forms.Select(attrs={'class': 'form-control'}),
            'fichier': forms.FileInput(attrs={'class': 'form-control'}),
            'lien_externe': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
            'code_iframe': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': '<iframe...>'}),
        }

    def __init__(self, *args, **kwargs):
        super(PFMPForm, self).__init__(*args, **kwargs)
        # C'est ici qu'on désactive l'obligation des dates
        self.fields['date_debut'].required = False
        self.fields['date_fin'].required = False