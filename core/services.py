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
        class _FakeResp:
            text = "Clé API Gemini non configurée. Contactez l'administrateur."
        return _FakeResp()

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
        from google import genai
        from django.conf import settings

        api_key = settings.GEMINI_API_KEY
        if not api_key:
            print("[Gemini] GEMINI_API_KEY non configurée dans settings.py")
            return None

        client = genai.Client(api_key=api_key)

        texte_tronque = texte[:8000] if len(texte) > 8000 else texte
        texte_tronque = texte_tronque.replace('\\', ' ').replace('"', "'")

        prompt = (
            f"Tu es un professeur expert en construction et bâtiment. "
            f"Génère exactement {nb_questions} questions QCM en français à partir de ce texte. "
            f"Réponds UNIQUEMENT avec du JSON valide, sans markdown, sans bloc code, sans explication. "
            f"Format strict :\n"
            f'{{"questions": [{{'
            f'"enonce": "...", '
            f'"choix_a": "...", '
            f'"choix_b": "...", '
            f'"choix_c": "...", '
            f'"choix_d": "...", '
            f'"bonne_reponse": "A ou B ou C ou D"'
            f'}}]}}\n'
            f"Texte : {texte_tronque}"
        )

        response = _appeler_gemini('gemini-2.5-flash-lite', prompt)
        raw = response.text.strip()
        print(f"[Gemini] Réponse brute ({len(raw)} chars) : {raw[:200]}...")

        raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)
        raw = re.sub(r'```\s*$', '', raw, flags=re.MULTILINE)
        raw = raw.strip()
        raw = re.sub(r'\\([^"\\/bfnrtu])', r'\1', raw)

        data = json.loads(raw)
        questions_brutes = data.get('questions', [])

        questions_valides = []
        champs_requis = {'enonce', 'choix_a', 'choix_b', 'bonne_reponse'}
        for i, q in enumerate(questions_brutes):
            manquants = champs_requis - set(q.keys())
            if manquants:
                print(f"[Gemini] Question #{i+1} ignorée — champs manquants : {manquants}")
                continue
            if not q.get('bonne_reponse', '').upper() in ('A', 'B', 'C', 'D'):
                print(f"[Gemini] Question #{i+1} ignorée — bonne_reponse invalide : {q.get('bonne_reponse')}")
                continue
            q['bonne_reponse'] = q['bonne_reponse'].upper()
            q.setdefault('choix_c', '')
            q.setdefault('choix_d', '')
            questions_valides.append(q)

        print(f"[Gemini] {len(questions_valides)}/{len(questions_brutes)} questions valides.")
        return questions_valides if questions_valides else None

    except json.JSONDecodeError as e:
        print(f"[Gemini] Erreur parsing JSON : {e}")
        print(f"[Gemini] Texte reçu : {raw[:500] if 'raw' in dir() else 'N/A'}")
        return None
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
        from google import genai
        from django.conf import settings

        api_key = settings.GEMINI_API_KEY
        if not api_key:
            print("[Gemini-Cartes] GEMINI_API_KEY manquante")
            return None

        client = genai.Client(api_key=api_key)

        cartes_str = '\n'.join(
            f'{i+1}. Question: "{_nettoyer_texte(c.question)}" | Réponse correcte: "{_nettoyer_texte(c.reponse)}"'
            for i, c in enumerate(cartes)
        )
        n = len(cartes)

        prompt = (
            f"Tu es un professeur expert en construction et bâtiment. "
            f"Pour chacune de ces {n} cartes de révision, génère 3 réponses fausses mais plausibles en français. "
            f"Règles strictes : enonce = la question exacte, choix_a = la réponse correcte exacte, "
            f"choix_b/c/d = 3 fausses réponses plausibles, bonne_reponse = toujours 'A'. "
            f"Réponds UNIQUEMENT avec du JSON valide sans markdown ni bloc code.\n"
            f'{{"questions": [{{"enonce":"...", "choix_a":"bonne", "choix_b":"faux1", "choix_c":"faux2", "choix_d":"faux3", "bonne_reponse":"A"}}]}}\n\n'
            f"Cartes:\n{cartes_str}"
        )

        response = _appeler_gemini('gemini-2.5-flash-lite', prompt)
        raw = response.text.strip()
        print(f"[Gemini-Cartes] Réponse brute ({len(raw)} chars) : {raw[:150]}...")

        raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)
        raw = re.sub(r'```\s*$', '', raw, flags=re.MULTILINE)
        raw = raw.strip()
        raw = re.sub(r'\\([^"\\/bfnrtu])', r'\1', raw)

        data = json.loads(raw)
        questions_brutes = data.get('questions', [])

        valides = []
        for q in questions_brutes:
            if not q.get('enonce') or not q.get('choix_a') or not q.get('choix_b'):
                continue
            q.setdefault('choix_c', '')
            q.setdefault('choix_d', '')
            q['bonne_reponse'] = 'A'
            valides.append(q)

        print(f"[Gemini-Cartes] {len(valides)}/{len(questions_brutes)} questions valides.")
        return valides if valides else None

    except json.JSONDecodeError as e:
        print(f"[Gemini-Cartes] Erreur JSON : {e}")
        return None
    except Exception as e:
        print(f"[Gemini-Cartes] Erreur : {e}")
        return None


# =====================================================
# GÉNÉRATION D'UNE SEULE QUESTION DE REMPLACEMENT
# =====================================================

def generer_une_question(sujet, contexte=''):
    try:
        from google import genai
        from django.conf import settings

        api_key = settings.GEMINI_API_KEY
        if not api_key:
            return None

        client = genai.Client(api_key=api_key)

        sujet_nettoye = _nettoyer_texte(sujet[:500] if len(sujet) > 500 else sujet)

        prompt = (
            f"Tu es un professeur expert en construction et bâtiment. "
            f"Génère exactement 1 nouvelle question QCM sur le même thème que : '{sujet_nettoye}'. "
            f"La question doit être différente mais couvrir le même domaine. "
            f"Réponds UNIQUEMENT avec du JSON valide, sans markdown, sans explication. "
            f"Format strict : "
            f'{{"enonce": "...", "choix_a": "...", "choix_b": "...", "choix_c": "...", "choix_d": "...", "bonne_reponse": "A ou B ou C ou D"}}'
        )

        response = _appeler_gemini('gemini-2.5-flash-lite', prompt)
        raw = response.text.strip()
        raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)
        raw = re.sub(r'```\s*$', '', raw, flags=re.MULTILINE).strip()
        raw = re.sub(r'\\([^"\\/bfnrtu])', r'\1', raw)

        q = json.loads(raw)
        if isinstance(q, list) and q:
            q = q[0]
        if not isinstance(q, dict):
            return None
        if not q.get('enonce') or not q.get('choix_a') or not q.get('choix_b'):
            return None
        q.setdefault('choix_c', '')
        q.setdefault('choix_d', '')
        br = q.get('bonne_reponse', 'A')
        if isinstance(br, str) and len(br) >= 1:
            br = br.strip()[0].upper()
        q['bonne_reponse'] = br if br in ('A', 'B', 'C', 'D') else 'A'
        print(f"[Gemini-1Q] Question générée : {q['enonce'][:60]}")
        return q

    except json.JSONDecodeError as e:
        print(f"[Gemini-1Q] Erreur JSON : {e}")
        return None
    except Exception as e:
        print(f"[Gemini-1Q] Erreur : {e}")
        return None


# =====================================================
# GÉNÉRATION MODE OPÉRATOIRE COMPLET
# =====================================================

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
            f"- Chaque champ doit être COURT et SYNTHÉTIQUE (2-3 lignes max, style liste à puces).\n"
            f"- 'operations' : actions concrètes, verbes d'action, 1-3 phrases max.\n"
            f"- 'materiels' : liste courte séparée par des virgules, pas de phrases.\n"
            f"- 'controle' : 1-2 points de contrôle essentiels.\n"
            f"- 'risques_sante' : 1-2 risques + mesure de prévention, très synthétique.\n"
            f"- 'risques_environnement' : 1-2 risques + mesure, très synthétique.\n"
            f"- Génère entre 5 et 8 phases maximum, bien ordonnées.\n\n"
            f"Réponds UNIQUEMENT avec du JSON valide, "
            f"sans markdown, sans bloc code.\n"
            f"Format strict :\n"
            f'{{"lignes": [{{'
            f'"ordre": 1, '
            f'"phase": "Nom court de la phase", '
            f'"operations": "Actions concises...", '
            f'"materiels": "outil1, outil2, matériau1", '
            f'"controle": "Point clé à vérifier", '
            f'"risques_sante": "Risque — EPI requis", '
            f'"risques_environnement": "Risque — mesure"'
            f'}}]}}\n\n'
            f"Texte source : {texte_tronque}"
        )

        response = _appeler_gemini('gemini-2.5-flash-lite', prompt)
        raw = response.text.strip()
        print(f"[Gemini-MO] Réponse brute ({len(raw)} chars) : {raw[:200]}...")

        raw = re.sub(r'^```(?:json)?\s*', '', raw, flags=re.MULTILINE)
        raw = re.sub(r'```\s*$', '', raw, flags=re.MULTILINE)
        raw = raw.strip()
        raw = re.sub(r'\\([^"\\/bfnrtu])', r'\1', raw)

        data = json.loads(raw)
        lignes_brutes = data.get('lignes', [])

        champs_requis = {'ordre', 'phase', 'operations', 'materiels', 'controle', 'risques_sante', 'risques_environnement'}
        lignes_valides = []
        for i, l in enumerate(lignes_brutes):
            manquants = champs_requis - set(l.keys())
            if manquants:
                print(f"[Gemini-MO] Ligne #{i+1} ignorée — champs manquants : {manquants}")
                continue
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
            'operations':            "actions concrètes à réaliser (verbes d'action, 2-3 phrases max)",
            'materiels':             'liste courte de matériels et outils séparés par des virgules (pas de phrases)',
            'controle':              '1-2 points de contrôle essentiels, très concis',
            'risques_sante':         '1-2 risques santé + mesure EPI, format : "Risque — prévention"',
            'risques_environnement': '1-2 risques environnement + mesure, format : "Risque — prévention"',
        }
        description = descriptions_colonnes.get(colonne, 'contenu synthétique, 2-3 lignes max')

        prompt = (
            f"Pour le mode opératoire '{titre_mo}', phase '{phase}', "
            f"génère UNIQUEMENT le contenu de la colonne '{colonne}' : {description}. "
            f"Sois BREF et SYNTHÉTIQUE. "
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
# SYNTHÈSE VOCALE — ELEVENLABS TTS
# =====================================================

# Voix ElevenLabs disponibles
# IMPORTANT : ces IDs sont des voix de la bibliothèque publique ElevenLabs.
# Si vous obtenez une erreur 404, connectez-vous sur elevenlabs.io → Voices
# → cherchez chaque voix → cliquez "Add to my voices" pour les activer sur votre compte.
_EL_VOICE_ID = 'XB0fDUnXU5powFXDhCwa'  # Charlotte (défaut)
_EL_MODEL    = 'eleven_multilingual_v2'

EL_VOIX_DISPONIBLES = {
    'XB0fDUnXU5powFXDhCwa': 'Charlotte – Femme, naturelle',
    'EXAVITQu4vr4xnSDxMaL': 'Sarah – Femme, douce',
    'piTKgcLEGmPE4e6mEKli': 'Nicole – Femme, posée',
    'onwK4e9ZLuTAKqWW03F9': 'Daniel – Homme, professionnel',
    'nPczCjzI2devNBz1zQrb': 'Brian – Homme, clair',
    'JBFqnCBsd6RMkjVDRZzb': 'George – Homme, grave',
}

def synthetiser_voix(texte, voice_id=None):
    """
    Convertit du texte en audio MP3 via l'API ElevenLabs.
    Rotation automatique des clés si quota épuisé (429) ou invalide (403/401).

    PRÉREQUIS : Les voix dans EL_VOIX_DISPONIBLES doivent être ajoutées à votre
    compte ElevenLabs via elevenlabs.io → Voices → "Add to my voices".

    Args:
        texte     (str) : texte à synthétiser
        voice_id  (str) : ID de la voix ElevenLabs (défaut : Charlotte)
    Returns:
        bytes : données audio MP3
    Raises:
        Exception si toutes les clés sont épuisées ou non configurées
    """
    import requests as _req
    from django.conf import settings

    cles = getattr(settings, 'ELEVENLABS_API_KEYS', [])
    if not cles:
        raise Exception("Aucune clé ElevenLabs configurée (ELEVENLABS_API_KEY dans .env).")

    print(f"[ElevenLabs] {len(cles)} clé(s) disponible(s).")

    # Limiter à 4000 caractères max
    texte = texte[:4000]

    derniere_erreur = None
    for cle in cles:
        try:
            print(f"[ElevenLabs] Tentative avec clé ...{cle[-8:]} (longueur={len(cle)})")
            vid = voice_id if voice_id in EL_VOIX_DISPONIBLES else _EL_VOICE_ID
            print(f"[ElevenLabs] Voix utilisée : {vid}")

            resp = _req.post(
                f'https://api.elevenlabs.io/v1/text-to-speech/{vid}',
                headers={
                    'xi-api-key': cle,
                    'Content-Type': 'application/json',
                    'Accept': 'audio/mpeg',
                },
                json={
                    'text': texte,
                    'model_id': _EL_MODEL,
                    'voice_settings': {
                        'stability': 0.5,
                        'similarity_boost': 0.75,
                        'style': 0.0,
                        'use_speaker_boost': True,
                    },
                },
                timeout=30,
            )

            # LOG DÉTAILLÉ de l'erreur pour diagnostic
            if resp.status_code != 200:
                corps_erreur = resp.text[:500] if resp.text else '(vide)'
                print(f"[ElevenLabs] Erreur HTTP {resp.status_code} : {corps_erreur}")

            if resp.status_code in (401, 403):
                derniere_erreur = Exception(f"ElevenLabs clé invalide (HTTP {resp.status_code}) : {resp.text[:200]}")
                continue
            if resp.status_code == 429:
                print(f"[ElevenLabs] Quota épuisé pour clé ...{cle[-8:]}, bascule.")
                derniere_erreur = Exception(f"ElevenLabs quota épuisé (HTTP 429)")
                continue
            if resp.status_code == 404:
                # La voix n'est pas dans le compte — on lève une erreur claire
                raise Exception(
                    f"Voix '{vid}' introuvable (HTTP 404). "
                    f"Allez sur elevenlabs.io → Voices → cherchez la voix → cliquez 'Add to my voices'."
                )

            resp.raise_for_status()
            print(f"[ElevenLabs] Audio généré ({len(resp.content)} octets) avec clé ...{cle[-8:]}")
            return resp.content

        except _req.exceptions.RequestException as e:
            print(f"[ElevenLabs] Erreur réseau : {e}")
            derniere_erreur = e
            continue

    raise derniere_erreur or Exception("Toutes les clés ElevenLabs sont épuisées.")