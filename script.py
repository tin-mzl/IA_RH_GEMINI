import asyncio
import base64
import json
import os
import uuid
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, send_file, session
from flask_sock import Sock
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from google.genai import types

import ia
from models import get_connection, init_db
from offres import OFFRES, get_offre

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-a-changer")
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 Mo max par PDF

# Initialisation du support WebSocket
sock = Sock(app)

UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
init_db()


# ============================================================
# OUTILS
# ============================================================

def erreur(message, code=400):
    return jsonify({"error": message}), code


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return erreur("Authentification requise", 401)
        return f(*args, **kwargs)

    return wrapper


def get_pdf_utilisateur(conn, pdf_id):
    return conn.execute(
        "SELECT * FROM pdfs WHERE id = ? AND user_id = ?", (pdf_id, session["user_id"])
    ).fetchone()


def get_entretien_utilisateur(conn, entretien_id):
    return conn.execute(
        "SELECT * FROM entretiens WHERE id = ? AND user_id = ?", (entretien_id, session["user_id"])
    ).fetchone()


def pdf_en_dict(pdf):
    return {"id": pdf["id"], "filename": pdf["filename"], "uploaded_at": pdf["uploaded_at"]}


def entretien_en_dict(e):
    return {
        "id": e["id"],
        "pdf_id": e["pdf_id"],
        "offre": e["offre"],
        "statut": e["statut"],
        "transcription": json.loads(e["transcription"]) if e["transcription"] else [],
        "evaluation": json.loads(e["evaluation"]) if e["evaluation"] else None,
        "created_at": e["created_at"],
    }


# ============================================================
# PAGE
# ============================================================

@app.route("/")
def index():
    return render_template("index.html")


# ============================================================
# AUTHENTIFICATION & CV & ANALYSES (inchangé)
# ============================================================

@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    champs = ["nom", "prenom", "email", "password"]
    if not all(data.get(c) for c in champs):
        return erreur("Champs requis : nom, prenom, email, password")
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO users (nom, prenom, email, password) VALUES (?, ?, ?, ?)",
            (data["nom"], data["prenom"], data["email"].lower().strip(), generate_password_hash(data["password"])),
        )
        conn.commit()
    except Exception:
        return erreur("Cet email est déjà utilisé", 409)
    finally:
        conn.close()
    session["user_id"] = cursor.lastrowid
    return jsonify({"id": cursor.lastrowid, "message": "Compte créé"}), 201


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    conn = get_connection()
    user = conn.execute("SELECT * FROM users WHERE email = ?", ((data.get("email") or "").lower().strip(),)).fetchone()
    conn.close()
    if user is None or not check_password_hash(user["password"], data.get("password") or ""):
        return erreur("Email ou mot de passe incorrect", 401)
    session["user_id"] = user["id"]
    return jsonify({"id": user["id"], "message": "Connecté"})


@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Déconnecté"})


@app.route("/api/me")
@login_required
def me():
    conn = get_connection()
    user = conn.execute("SELECT id, nom, prenom, email, created_at FROM users WHERE id = ?",
                        (session["user_id"],)).fetchone()
    conn.close()
    return jsonify(dict(user))


@app.route("/api/offres")
def liste_offres():
    return jsonify([{"id": k, **v} for k, v in OFFRES.items()])


@app.route("/api/offres/<offre_id>")
def detail_offre(offre_id):
    offre = get_offre(offre_id)
    if offre is None:
        return erreur("Offre introuvable", 404)
    return jsonify({"id": offre_id, **offre})


@app.route("/api/cv", methods=["POST"])
@login_required
def upload_cv():
    fichier = request.files.get("file")
    if fichier is None or fichier.filename == "":
        return erreur("Aucun fichier envoyé")
    if not fichier.filename.lower().endswith(".pdf"):
        return erreur("Seuls les PDF sont acceptés")
    filename = secure_filename(fichier.filename)
    dossier = os.path.join(UPLOAD_FOLDER, str(session["user_id"]))
    os.makedirs(dossier, exist_ok=True)
    filepath = os.path.join(dossier, f"{uuid.uuid4().hex}.pdf")
    fichier.save(filepath)
    try:
        contenu = ia.extraire_texte_pdf(filepath)
    except Exception:
        os.remove(filepath)
        return erreur("PDF illisible")
    if not contenu:
        os.remove(filepath)
        return erreur("Aucun texte trouvé (PDF scanné ?)")
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO pdfs (user_id, filename, filepath, contenu) VALUES (?, ?, ?, ?)",
            (session["user_id"], filename, filepath, contenu),
        )
        conn.commit()
    except Exception:
        os.remove(filepath)
        return erreur("Un CV avec ce nom existe déjà", 409)
    finally:
        conn.close()
    return jsonify({"id": cursor.lastrowid, "filename": filename}), 201


@app.route("/api/cv")
@login_required
def liste_cv():
    conn = get_connection()
    pdfs = conn.execute("SELECT * FROM pdfs WHERE user_id = ? ORDER BY uploaded_at DESC",
                        (session["user_id"],)).fetchall()
    conn.close()
    return jsonify([pdf_en_dict(p) for p in pdfs])


@app.route("/api/cv/<int:pdf_id>")
@login_required
def detail_cv(pdf_id):
    conn = get_connection()
    pdf = get_pdf_utilisateur(conn, pdf_id)
    conn.close()
    if pdf is None:
        return erreur("CV introuvable", 404)
    return jsonify({**pdf_en_dict(pdf), "contenu": pdf["contenu"]})


@app.route("/api/cv/<int:pdf_id>/fichier")
@login_required
def telecharger_cv(pdf_id):
    conn = get_connection()
    pdf = get_pdf_utilisateur(conn, pdf_id)
    conn.close()
    if pdf is None:
        return erreur("CV introuvable", 404)
    return send_file(pdf["filepath"], mimetype="application/pdf", download_name=pdf["filename"])


@app.route("/api/cv/<int:pdf_id>", methods=["DELETE"])
@login_required
def supprimer_cv(pdf_id):
    conn = get_connection()
    pdf = get_pdf_utilisateur(conn, pdf_id)
    if pdf is None:
        conn.close()
        return erreur("CV introuvable", 404)
    conn.execute("DELETE FROM pdfs WHERE id = ?", (pdf_id,))
    conn.commit()
    conn.close()
    if os.path.exists(pdf["filepath"]):
        os.remove(pdf["filepath"])
    return jsonify({"message": "CV supprimé"})


@app.route("/api/cv/<int:pdf_id>/analyse", methods=["POST"])
@login_required
def analyser_cv(pdf_id):
    offre_id = (request.get_json() or {}).get("offre")
    if get_offre(offre_id) is None:
        return erreur(f"Offre invalide. Choix : {', '.join(OFFRES)}")
    conn = get_connection()
    pdf = get_pdf_utilisateur(conn, pdf_id)
    if pdf is None:
        conn.close()
        return erreur("CV introuvable", 404)
    try:
        resultat = ia.analyser_cv(pdf["contenu"], offre_id)
    except Exception as e:
        conn.close()
        return erreur(f"Erreur lors de l'analyse : {e}", 502)
    conn.execute(
        """INSERT INTO analyses (pdf_id, offre, score, resultat)
           VALUES (?, ?, ?, ?) ON CONFLICT(pdf_id, offre) DO
        UPDATE SET
            score = excluded.score, resultat = excluded.resultat, created_at = CURRENT_TIMESTAMP""",
        (pdf_id, offre_id, resultat.get("score"), json.dumps(resultat, ensure_ascii=False)),
    )
    conn.commit()
    conn.close()
    return jsonify({"pdf_id": pdf_id, "offre": offre_id, **resultat})


@app.route("/api/cv/<int:pdf_id>/analyses")
@login_required
def liste_analyses(pdf_id):
    conn = get_connection()
    if get_pdf_utilisateur(conn, pdf_id) is None:
        conn.close()
        return erreur("CV introuvable", 404)
    analyses = conn.execute("SELECT * FROM analyses WHERE pdf_id = ? ORDER BY score DESC", (pdf_id,)).fetchall()
    conn.close()
    return jsonify(
        [{"offre": a["offre"], "created_at": a["created_at"], **json.loads(a["resultat"])} for a in analyses])


# ============================================================
# ENTRETIEN (GEMINI LIVE WEBSOCKET)
# ============================================================

@app.route("/api/entretiens", methods=["POST"])
@login_required
def demarrer_entretien():
    """Crée une session d'entretien en BDD et retourne l'URL WebSocket à rejoindre."""
    data = request.get_json() or {}
    pdf_id, offre_id = data.get("pdf_id"), data.get("offre")
    if get_offre(offre_id) is None:
        return erreur(f"Offre invalide. Choix : {', '.join(OFFRES)}")

    conn = get_connection()
    pdf = get_pdf_utilisateur(conn, pdf_id)
    if pdf is None:
        conn.close()
        return erreur("CV introuvable", 404)

    session_ws_id = uuid.uuid4().hex

    cursor = conn.execute(
        "INSERT INTO entretiens (user_id, pdf_id, offre, live_session_id, statut) VALUES (?, ?, ?, ?, 'en_cours')",
        (session["user_id"], pdf_id, offre_id, session_ws_id),
    )
    entretien_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return jsonify({
        "entretien_id": entretien_id,
        "websocket_url": f"/ws/live/{entretien_id}",
        "message_accueil": ia.message_accueil(offre_id),
    }), 201


@sock.route("/ws/live/<int:entretien_id>")
def live_websocket(ws, entretien_id):
    conn = get_connection()
    entretien = conn.execute("SELECT * FROM entretiens WHERE id = ?", (entretien_id,)).fetchone()
    if not entretien:
        conn.close()
        ws.send(json.dumps({"error": "Entretien introuvable"}))
        return

    pdf = conn.execute("SELECT contenu FROM pdfs WHERE id = ?", (entretien["pdf_id"],)).fetchone()
    analyse = conn.execute(
        "SELECT resultat FROM analyses WHERE pdf_id = ? AND offre = ?",
        (entretien["pdf_id"], entretien["offre"])
    ).fetchone()
    conn.close()

    analyse_data = json.loads(analyse["resultat"]) if analyse else None
    instructions = ia.instructions_entretien(pdf["contenu"], entretien["offre"], analyse_data)
    config = ia.config_session_live(instructions)

    async def pont_gemini():
        async with ia.client.aio.live.connect(model=ia.MODELE_LIVE, config=config) as g_session:

            # Message initial pour que l'IA prenne la parole
            msg_initial = ia.message_accueil(entretien["offre"])
            await g_session.send(input=msg_initial, end_of_turn=True)

            async def client_vers_gemini():
                loop = asyncio.get_running_loop()
                chunk_count = 0
                while True:
                    msg = await loop.run_in_executor(None, ws.receive)
                    if msg is None:
                        break
                    
                    try:
                        data = json.loads(msg)
                        if "audio" in data:
                            pcm_bytes = base64.b64decode(data["audio"])
                            # Récupération de la fréquence réelle transmise par le JS (ex: 48000 ou 44100)
                            sample_rate = data.get("sampleRate", 16000)
                            
                            chunk_count += 1
                            if chunk_count % 20 == 0:
                                print(f"[OK] {chunk_count} paquets audio transmis ({sample_rate}Hz)...")

                            await g_session.send(
                                input=types.LiveClientRealtimeInput(
                                    media_chunks=[
                                        types.Blob(
                                            data=pcm_bytes,
                                            mime_type=f"audio/pcm;rate={sample_rate}"
                                        )
                                    ]
                                )
                            )
                        elif "text" in data:
                            await g_session.send(input=data["text"], end_of_turn=True)
                    except Exception as e:
                        print(f"Erreur audio Gemini : {e}")

            async def gemini_vers_client():
                async for response in g_session.receive():
                    server_content = response.server_content
                    if server_content and server_content.model_turn:
                        for part in server_content.model_turn.parts:
                            if part.inline_data:
                                audio_b64 = base64.b64encode(part.inline_data.data).decode("utf-8")
                                ws.send(json.dumps({"type": "audio", "data": audio_b64}))
                            if part.text:
                                ws.send(json.dumps({"type": "text", "data": part.text}))

            t1 = asyncio.create_task(client_vers_gemini())
            t2 = asyncio.create_task(gemini_vers_client())
            await asyncio.gather(t1, t2)

    try:
        asyncio.run(pont_gemini())
    except Exception as e:
        print(f"Session WebSocket terminée : {e}")

@app.route("/api/entretiens/<int:entretien_id>/transcription", methods=["POST"])
@login_required
def enregistrer_transcription(entretien_id):
    messages = (request.get_json() or {}).get("messages") or []
    conn = get_connection()
    entretien = get_entretien_utilisateur(conn, entretien_id)
    if entretien is None:
        conn.close()
        return erreur("Entretien introuvable", 404)

    transcription = json.loads(entretien["transcription"]) if entretien["transcription"] else []
    transcription += [
        {"role": m["role"], "texte": m["texte"]} for m in messages if m.get("role") and m.get("texte")
    ]
    conn.execute(
        "UPDATE entretiens SET transcription = ? WHERE id = ?",
        (json.dumps(transcription, ensure_ascii=False), entretien_id),
    )
    conn.commit()
    conn.close()
    return jsonify({"nb_messages": len(transcription)})


@app.route("/api/entretiens/<int:entretien_id>/terminer", methods=["POST"])
@login_required
def terminer_entretien(entretien_id):
    conn = get_connection()
    entretien = get_entretien_utilisateur(conn, entretien_id)
    if entretien is None:
        conn.close()
        return erreur("Entretien introuvable", 404)

    transcription = json.loads(entretien["transcription"]) if entretien["transcription"] else []
    if not transcription:
        conn.close()
        return erreur("Transcription vide, impossible d'évaluer l'entretien")

    try:
        evaluation = ia.evaluer_entretien(transcription, entretien["offre"])
    except Exception as e:
        conn.close()
        return erreur(f"Erreur lors de l'évaluation : {e}", 502)

    conn.execute(
        "UPDATE entretiens SET evaluation = ?, statut = 'termine' WHERE id = ?",
        (json.dumps(evaluation, ensure_ascii=False), entretien_id),
    )
    conn.commit()
    conn.close()
    return jsonify(evaluation)


@app.route("/api/entretiens")
@login_required
def liste_entretiens():
    conn = get_connection()
    entretiens = conn.execute("SELECT * FROM entretiens WHERE user_id = ? ORDER BY created_at DESC",
                              (session["user_id"],)).fetchall()
    conn.close()
    return jsonify([entretien_en_dict(e) for e in entretiens])


@app.route("/api/entretiens/<int:entretien_id>")
@login_required
def detail_entretien(entretien_id):
    conn = get_connection()
    entretien = get_entretien_utilisateur(conn, entretien_id)
    conn.close()
    if entretien is None:
        return erreur("Entretien introuvable", 404)
    return jsonify(entretien_en_dict(entretien))


if __name__ == "__main__":
    app.run(debug=True, port=int(os.getenv("PORT", 5001)))