# core/services.py — Services IA : extraction PDF + génération QCM via Gemini

import json
import re


# =====================================================
# HELPER GEMINI — ROTATION AUTOMATIQUE DES CLÉS API
# =====================================================

def _appeler_gemini(model, contents):
    """
    Appelle l'API Gemini avec rotation automatique des clés si quota épuisé (429).
    Utilise GEMINI_API_KEY puis GEMINI_API_KEY_2 si la première est bloquée.
    """
    from google import genai
    from django.conf import settings

    cles = getattr(settings, 'GEMINI_API_KEYS', [])
    if not cles:
        cle = getattr(settings, 'GEMINI_API_KEY', '')
        cles = [cle] if cle else []

    if not cles:
        raise RuntimeError("Aucune clé GEMINI_API_KEY n'est configurée.")

    derniere_erreur = None
    for cle in cles:
        try:
            client = genai.Client(api_key=cle)
            return client.models.generate_content(model=model, contents=contents)
        except Exception as e:
            if '429' in str(e) or 'RESOURCE_EXHAUSTED' in str(e):
                print(f"[Gemini] Quota épuisé pour la clé ...{cle[-6:]}, bascule vers la clé suivante.")
                derniere_erreur = e
                continue
            raise  # autre erreur : on la remonte immédiatement
    raise derniere_erreur  # toutes les clés épuisées



def extraire_texte_pdf(fichier):
    """
    Extrait et concatène le texte de toutes les pages d'un fichier PDF.
    Utilise pymupdf (fitz) en priorité, puis PyPDF2 en fallback.
    """
    try:
        if hasattr(fichier, 'read'):
            if hasattr(fichier, 'seek'):
                fichier.seek(0)
            pdf_bytes = fichier.read()
        else:
            with open(fichier, 'rb') as f:
                pdf_bytes = f.read()
    except Exception as e:
        print(f"[PDF] Impossible de lire le fichier : {e}")
        return None

    try:
        import fitz  # pymupdf
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        texte_pages = []
        for page in doc:
            texte = page.get_text()
            if texte and texte.strip():
                texte_pages.append(texte.strip())
        doc.close()
        resultat = '\n\n'.join(texte_pages)
        print(f"[PDF] pymupdf : {len(texte_pages)} pages avec texte, {len(resultat)} caractères.")
        if resultat.strip():
            return resultat
    except Exception as e:
        print(f"[PDF] pymupdf erreur (fallback PyPDF2) : {e}")

    try:
        import io
        import PyPDF2
        reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        texte_pages = []
        for page in reader.pages:
            texte = page.extract_text()
            if texte:
                texte_pages.append(texte.strip())
        resultat = '\n\n'.join(texte_pages)
        print(f"[PDF] PyPDF2 fallback : {len(reader.pages)} pages, {len(resultat)} caractères.")
        return resultat if resultat.strip() else None
    except Exception as e:
        print(f"[PDF] PyPDF2 erreur : {e}")
        return None


# =====================================================
# GÉNÉRATION QCM DEPUIS TEXTE — API GEMINI
# =====================================================

def generer_qcm_depuis_texte(texte, nb_questions=10):
    try:
        if not texte or not texte.strip():
            return None
        if nb_questions not in (5, 10, 15, 20, 30, 40, 50):
            raise ValueError("Le nombre de questions demandé n'est pas autorisé.")

        texte_tronque = texte[:8000] if len(texte) > 8000 else texte
        texte_tronque = texte_tronque.replace('\\', ' ').replace('"', "'")
        questions_valides = []
        champs_requis = {'enonce', 'choix_a', 'choix_b', 'bonne_reponse'}
        for debut in range(0, nb_questions, 10):
            if len(questions_valides) >= nb_questions:
                break
            taille_lot = min(10, nb_questions - debut)
            prompt = (
                "Tu es un professeur expert en construction et bâtiment. "
                f"Génère exactement {taille_lot} questions QCM différentes en français à partir de ce texte. "
                "Réponds UNIQUEMENT avec du JSON valide, sans markdown ni explication. "
                'Format : {"questions":[{"enonce":"...","choix_a":"...",'
                '"choix_b":"...","choix_c":"...","choix_d":"...",'
                '"bonne_reponse":"A"}]} ; bonne_reponse doit être la lettre A, B, C ou D.\n'
                f"Texte : {texte_tronque}"
            )
            try:
                response = _appeler_gemini('gemini-2.5-flash-lite', prompt)
                raw = _reparer_json(response.text or '')
                questions_brutes = json.loads(raw).get('questions', [])
            except Exception as e:
                print(f"[Gemini] Échec du lot {debut // 10 + 1}: {e}")
                continue

            for q in questions_brutes:
                if not isinstance(q, dict) or champs_requis - set(q):
                    continue
                bonne_reponse = str(q.get('bonne_reponse', '')).upper()
                if bonne_reponse not in ('A', 'B', 'C', 'D'):
                    continue
                q['bonne_reponse'] = bonne_reponse
                q.setdefault('choix_c', '')
                q.setdefault('choix_d', '')
                questions_valides.append(q)
                if len(questions_valides) == nb_questions:
                    break

        print(f"[Gemini] {len(questions_valides)}/{nb_questions} questions demandées générées.")
        return questions_valides[:nb_questions] or None
    except Exception as e:
        print(f"[Gemini] Erreur inattendue : {e}")
        return None


# =====================================================
# GÉNÉRATION QCM DEPUIS FICHES DE RÉVISION
# =====================================================

def _nettoyer_texte(texte):
    if not texte:
        return texte
    texte = re.sub(r'\$[^\$]*\$', lambda m: re.sub(r'[\\{}^_$]', '', m.group()), texte)
    texte = texte.replace('\\', ' ')
    return texte.strip()


def generer_distracteurs_depuis_cartes(cartes):
    if not cartes:
        return None
    try:
        valides = []
        for debut in range(0, len(cartes), 10):
            lot = cartes[debut:debut + 10]
            cartes_str = '\n'.join(
                f'{i+1}. Question: "{_nettoyer_texte(c.question)}" | Réponse correcte: "{_nettoyer_texte(c.reponse)}"'
                for i, c in enumerate(lot)
            )
            prompt = (
                "Tu es un professeur expert en construction et bâtiment. "
                f"Pour chacune de ces {len(lot)} cartes, génère 3 réponses fausses mais plausibles en français. "
                "Conserve exactement chaque énoncé et chaque réponse correcte en choix_a. "
                "bonne_reponse doit toujours être A. Réponds uniquement en JSON valide sans markdown.\n"
                '{"questions":[{"enonce":"...","choix_a":"bonne",'
                '"choix_b":"faux1","choix_c":"faux2","choix_d":"faux3",'
                '"bonne_reponse":"A"}]}\n'
                f"Cartes:\n{cartes_str}"
            )
            try:
                response = _appeler_gemini('gemini-2.5-flash-lite', prompt)
                raw = _reparer_json(response.text or '')
                questions_brutes = json.loads(raw).get('questions', [])
            except Exception as e:
                print(f"[Gemini-Cartes] Échec du lot {debut // 10 + 1}: {e}")
                continue

            for q in questions_brutes[:len(lot)]:
                if not isinstance(q, dict) or not q.get('enonce') or not q.get('choix_a') or not q.get('choix_b'):
                    continue
                q.setdefault('choix_c', '')
                q.setdefault('choix_d', '')
                q['bonne_reponse'] = 'A'
                valides.append(q)

        print(f"[Gemini-Cartes] {len(valides)}/{len(cartes)} questions valides.")
        return valides or None
    except Exception as e:
        print(f"[Gemini-Cartes] Erreur : {e}")
        return None


# =====================================================
# GÉNÉRATION D'UNE SEULE QUESTION DE REMPLACEMENT
# =====================================================

def generer_une_question(sujet, contexte=''):
    try:
        sujet_nettoye = _nettoyer_texte(sujet[:500] if len(sujet) > 500 else sujet)
        prompt = (
            "Tu es un professeur expert en construction et bâtiment. "
            f"Génère exactement 1 nouvelle question QCM sur le même thème que : '{sujet_nettoye}'. "
            "La question doit être différente mais couvrir le même domaine. "
            "Réponds UNIQUEMENT avec du JSON valide, sans markdown, sans explication. "
            'Format : {"enonce":"...","choix_a":"...","choix_b":"...",'
            '"choix_c":"...","choix_d":"...","bonne_reponse":"A ou B ou C ou D"}'
        )
        if contexte:
            prompt += f"\nContexte complémentaire : {_nettoyer_texte(contexte)}"

        response = _appeler_gemini('gemini-2.5-flash-lite', prompt)
        raw = _reparer_json(response.text or '')
        question = json.loads(raw)
        if isinstance(question, list) and question:
            question = question[0]
        if not isinstance(question, dict):
            return None
        if not question.get('enonce') or not question.get('choix_a') or not question.get('choix_b'):
            return None
        question.setdefault('choix_c', '')
        question.setdefault('choix_d', '')
        bonne_reponse = str(question.get('bonne_reponse', 'A')).strip()[:1].upper()
        question['bonne_reponse'] = bonne_reponse if bonne_reponse in ('A', 'B', 'C', 'D') else 'A'
        return question
    except Exception as e:
        print(f"[Gemini-1Q] Erreur : {e}")
        return None


# =====================================================
# GÉNÉRATION MODE OPÉRATOIRE COMPLET
# =====================================================

def _reparer_json(raw):
    """
    Répare les problèmes courants dans la réponse JSON de Gemini :
    - Supprime les blocs markdown (```json ... ```)
    - Remplace les retours à la ligne RÉELS à l'intérieur des strings JSON
      par des séquences d'échappement \\n valides
    - Corrige les séquences d'échappement invalides
    """
    # Supprimer les blocs markdown
    raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)
    raw = re.sub(r'```\s*$', '', raw, flags=re.MULTILINE)
    raw = raw.strip()

    # Remplacer les vrais sauts de ligne à l'intérieur des valeurs JSON
    # en parcourant le texte caractère par caractère
    result = []
    in_string = False
    i = 0
    while i < len(raw):
        c = raw[i]
        if c == '\\' and in_string:
            # Séquence échappée — copier les deux caractères tels quels
            result.append(c)
            i += 1
            if i < len(raw):
                result.append(raw[i])
                i += 1
            continue
        if c == '"':
            in_string = not in_string
        if in_string and c == '\n':
            result.append('\\n')
        elif in_string and c == '\r':
            pass  # ignorer CR
        elif in_string and c == '\t':
            result.append('\\t')
        else:
            result.append(c)
        i += 1
    raw = ''.join(result)

    # Corriger les séquences d'échappement invalides restantes
    raw = re.sub(r'\\([^"\\/bfnrtu0-9])', r'\1', raw)
    return raw


def generer_mode_operatoire(texte, titre):
    try:
        from google import genai
        from django.conf import settings

        api_key = settings.GEMINI_API_KEY
        if not api_key:
            print("[Gemini-MO] GEMINI_API_KEY non configurée dans settings.py")
            return None

        client = genai.Client(api_key=api_key)

        texte_tronque = texte[:8000] if len(texte) > 8000 else texte

        prompt = (
            f"Tu es un expert en construction et bâtiment.\n"
            f"Génère un mode opératoire pour : {titre}\n\n"
            f"RÈGLES IMPÉRATIVES :\n"
            f"- Génère entre 5 et 10 phases, bien ordonnées.\n"
            f"- Chaque champ : texte court, plusieurs éléments séparés par des virgules.\n"
            f"- 'operations' : actions concrètes, verbes d'action, plusieurs étapes.\n"
            f"- 'materiels' : matériels, outils et EPI nécessaires séparés par des virgules.\n"
            f"- 'controle' : points de contrôle qualité essentiels.\n"
            f"- 'risques_sante' : OBLIGATOIRE — 2-3 risques santé/sécurité + EPI. JAMAIS vide.\n"
            f"- 'risques_environnement' : OBLIGATOIRE — 2-3 risques environnementaux + mesures. JAMAIS vide.\n\n"
            f"Réponds UNIQUEMENT en JSON valide sans markdown ni bloc de code.\n"
            f"Format :\n"
            f'{{"lignes": [{{"ordre": 1, "phase": "Nom", "operations": "op1, op2, op3", "materiels": "outil1, outil2", "controle": "point1, point2", "risques_sante": "Chute de plain-pied — chaussures de sécurité, Poussières — masque FFP2", "risques_environnement": "Déchets BTP — benne dédiée, Eau de gâchage — bac récupération"}}]}}\n\n'
            f"Texte source : {texte_tronque}"
        )

        response = _appeler_gemini('gemini-2.5-flash-lite', prompt)
        raw = response.text.strip()
        print(f"[Gemini-MO] Réponse brute ({len(raw)} chars) : {raw[:200]}...")

        raw = _reparer_json(raw)

        data = json.loads(raw)
        lignes_brutes = data.get('lignes', [])

        champs_requis = {'ordre', 'phase', 'operations', 'materiels', 'controle', 'risques_sante', 'risques_environnement'}
        lignes_valides = []
        for i, l in enumerate(lignes_brutes):
            manquants = champs_requis - set(l.keys())
            if manquants:
                print(f"[Gemini-MO] Ligne #{i+1} ignorée — champs manquants : {manquants}")
                continue
            # Fallback si les risques sont vides malgré les instructions
            if not l.get('risques_sante', '').strip():
                l['risques_sante'] = 'Risques propres à cette phase — consulter le responsable sécurité'
            if not l.get('risques_environnement', '').strip():
                l['risques_environnement'] = 'Impacts environnementaux à identifier pour cette phase'
            lignes_valides.append(l)

        print(f"[Gemini-MO] {len(lignes_valides)}/{len(lignes_brutes)} lignes valides.")
        return lignes_valides if lignes_valides else None

    except json.JSONDecodeError as e:
        print(f"[Gemini-MO] Erreur parsing JSON : {e}")
        return None
    except Exception as e:
        print(f"[Gemini-MO] Erreur inattendue : {e}")
        return None


def regenerer_ligne(titre_mo, phase, colonne):
    try:
        from google import genai
        from django.conf import settings

        api_key = settings.GEMINI_API_KEY
        if not api_key:
            print("[Gemini-MO-Ligne] GEMINI_API_KEY non configurée dans settings.py")
            return None

        client = genai.Client(api_key=api_key)

        descriptions_colonnes = {
            'operations':            "actions concrètes à réaliser (verbes d'action, plusieurs étapes séparées par des virgules)",
            'materiels':             'liste des matériels, outils et EPI nécessaires séparés par des virgules',
            'controle':              'points de contrôle qualité et conformité séparés par des virgules',
            'risques_sante':         'OBLIGATOIRE — 2-3 risques santé/sécurité + EPI, format : "Risque — prévention, Risque 2 — EPI"',
            'risques_environnement': 'OBLIGATOIRE — 2-3 risques environnementaux + mesures, format : "Risque — mesure, Risque 2 — mesure"',
        }
        description = descriptions_colonnes.get(colonne, 'contenu synthétique séparé par des virgules')

        prompt = (
            f"Pour le mode opératoire '{titre_mo}', phase '{phase}', "
            f"génère UNIQUEMENT le contenu de la colonne '{colonne}' : {description}. "
            f"Réponds avec du texte brut uniquement, pas de JSON, pas de markdown."
        )

        response = _appeler_gemini('gemini-2.5-flash-lite', prompt)
        texte = response.text.strip()
        print(f"[Gemini-MO-Ligne] '{colonne}' régénérée ({len(texte)} chars).")
        return texte if texte else None

    except Exception as e:
        print(f"[Gemini-MO-Ligne] Erreur : {e}")
        return None


# =====================================================
# ASSISTANT IA — RÉPONSE LIBRE
# =====================================================

def assistant_recherche(question, historique=None, fichier_bytes=None, fichier_mime=None, fichier_nom=None):
    try:
        from google import genai
        from google.genai import types
        from django.conf import settings

        api_key = settings.GEMINI_API_KEY
        if not api_key:
            return "Clé API Gemini non configurée. Contactez l'administrateur."

        client = genai.Client(api_key=api_key)

        contexte_hist = ""
        if historique:
            for msg in historique[-6:]:
                role = "Prof" if msg['role'] == 'user' else "Assistant"
                contexte_hist += f"{role}: {msg['texte']}\n"

        system = (
            "Tu es un assistant pédagogique expert pour un lycée professionnel spécialisé "
            "dans le bâtiment, la construction, la maçonnerie et le gros œuvre. "
            "Réponds en français, de façon naturelle et conversationnelle, comme si tu parlais à un élève. "
            "Évite le markdown : pas de titres avec #, pas d'astérisques, pas de tirets en liste. "
            "Utilise des phrases complètes et fluides, séparées par des sauts de ligne si nécessaire. "
            "Tu peux numéroter les étapes (1., 2., 3.) si c'est une procédure. "
            "Sois précis et concis (300 mots max sauf si on te demande plus).\n\n"
        )
        if contexte_hist:
            system += f"Historique de la conversation :\n{contexte_hist}\n\n"

        if fichier_bytes and fichier_mime:
            nom_affiche = fichier_nom or "document joint"
            prompt_texte = system + (
                f"L'utilisateur a joint le fichier '{nom_affiche}'.\n"
                f"Question : {question or 'Fais un résumé structuré de ce document.'}"
            )
            part_texte   = types.Part.from_text(text=prompt_texte)
            part_fichier = types.Part.from_bytes(data=fichier_bytes, mime_type=fichier_mime)
            contents = [part_texte, part_fichier]
        else:
            contents = system + f"Question : {question}"

        response = _appeler_gemini('gemini-2.5-flash-lite', contents)
        return response.text.strip()

    except Exception as e:
        print(f"[Gemini-Assistant] Erreur : {e}")
        return f"Une erreur s'est produite : {str(e)}"


# =====================================================
# SYNTHÈSE VOCALE — GOOGLE TTS (gTTS) - Anti-blocage 403
# =====================================================
import io
from gtts import gTTS

EL_VOIX_DISPONIBLES = {
    'fr-FR': 'Français (France)',
    'fr-CA': 'Français (Canada)',
    'en-US': 'Anglais (États-Unis)',
}

def synthetiser_voix(texte, voice_id=None):
    """
    Génère l'audio via Google TTS.
    Aucun blocage d'IP (contrairement à Edge-TTS sur Render).
    """
    texte = texte[:5000].strip()
    if not texte:
        return None

    # Par défaut, français de France
    lang = 'fr'
    tld = 'fr'
    
    if voice_id == 'fr-CA':
        tld = 'ca'
    elif voice_id == 'en-US':
        lang = 'en'
        tld = 'com'

    try:
        # Création de l'audio Google
        tts = gTTS(text=texte, lang=lang, tld=tld, slow=False)
        
        # Sauvegarde en mémoire RAM (pas besoin de fichier temporaire)
        buffer = io.BytesIO()
        tts.write_to_fp(buffer)
        audio_bytes = buffer.getvalue()
        
        print(f"✅ [gTTS] Audio généré ({len(audio_bytes)} octets) en {lang}-{tld}", flush=True)
        return audio_bytes
        
    except Exception as e:
        print(f"❌ [gTTS] ERREUR : {str(e)}", flush=True)
        return None