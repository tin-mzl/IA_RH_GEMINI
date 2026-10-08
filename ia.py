import json
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types
from pypdf import PdfReader

from offres import OFFRES, offre_en_texte
from live import SYSTEM_INSTRUCTIONS

load_dotenv()

# Initialisation du client Google GenAI
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MODELE_TEXTE = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
MODELE_LIVE = os.getenv("GEMINI_LIVE_MODEL", "gemini-2.0-flash-exp")
VOIX_LIVE = os.getenv("GEMINI_LIVE_VOICE", "Puck")


def extraire_texte_pdf(chemin):
    reader = PdfReader(chemin)
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages).strip()


def _demander_json(instructions, contenu):
    reponse = client.models.generate_content(
        model=MODELE_TEXTE,
        contents=contenu,
        config=types.GenerateContentConfig(
            system_instruction=instructions,
            response_mime_type="application/json",
            temperature=0.2,
        ),
    )
    return json.loads(reponse.text)


def analyser_cv(texte_cv, offre_id):
    instructions = (
        "Tu es un recruteur RH expert. Analyse le CV fourni par rapport à l'offre d'emploi. "
        "Réponds uniquement en JSON avec les clés suivantes :\n"
        '- "score" : entier de 0 à 100, adéquation du CV avec l\'offre\n'
        '- "resume" : résumé du profil en 2-3 phrases\n'
        '- "points_forts" : liste de chaînes\n'
        '- "points_faibles" : liste de chaînes\n'
        '- "competences_manquantes" : liste de chaînes\n'
        '- "recommandations" : liste de conseils pour améliorer le CV\n'
        '- "questions_probables" : liste de 5 questions que le recruteur posera probablement\n'
        "Rédige en français."
    )
    contenu = f"OFFRE :\n{offre_en_texte(offre_id)}\n\nCV :\n{texte_cv}"
    return _demander_json(instructions, contenu)


def instructions_entretien(texte_cv, offre_id, analyse=None):
    texte = (
        f"{SYSTEM_INSTRUCTIONS}\n\n"
        "============================================================\n"
        "CONTEXTE DE CET ENTRETIEN\n"
        "============================================================\n\n"
        f"OFFRE :\n{offre_en_texte(offre_id)}\n\n"
        f"CV DU CANDIDAT :\n{texte_cv}"
    )
    if analyse:
        texte += (
            "\n\nPOINTS À CREUSER (issus de l'analyse du CV) :\n"
            f"Points faibles : {', '.join(analyse.get('points_faibles', []))}\n"
            f"Compétences manquantes : {', '.join(analyse.get('competences_manquantes', []))}"
        )
    return texte


def message_accueil(offre_id):
    titre = OFFRES[offre_id]["titre"]
    return (
        f"L'entretien pour le poste de {titre} commence maintenant. Parle en premier, en français : "
        "salue le candidat, présente-toi brièvement comme le recruteur qui conduit l'entretien, "
        "puis pose ta première question en faisant référence à son parcours. "
        "Ensuite, arrête-toi et écoute sa réponse."
    )


def config_session_live(instructions):
    """Génère la configuration de session Live pour Gemini."""
    return types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=VOIX_LIVE)
            )
        ),
        system_instruction=types.Content(
            parts=[types.Part.from_text(text=instructions)]
        ),
    )


def evaluer_entretien(transcription, offre_id):
    instructions = (
        "Tu es un recruteur RH expert. Évalue la performance du candidat lors de l'entretien "
        "à partir de la transcription. Réponds uniquement en JSON avec les clés :\n"
        '- "note_globale" : entier de 0 à 100\n'
        '- "communication" : entier de 0 à 10\n'
        '- "competences_techniques" : entier de 0 à 10\n'
        '- "motivation" : entier de 0 à 10\n'
        '- "points_forts" : liste de chaînes\n'
        '- "axes_amelioration" : liste de chaînes\n'
        '- "meilleures_reponses" : liste d\'objets {"question", "conseil"} pour les réponses à retravailler\n'
        '- "verdict" : phrase de synthèse\n'
        "Rédige en français."
    )
    dialogue = "\n".join(f"{m['role']} : {m['texte']}" for m in transcription)
    contenu = f"OFFRE :\n{offre_en_texte(offre_id)}\n\nTRANSCRIPTION :\n{dialogue}"
    return _demander_json(instructions, contenu)