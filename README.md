# IA DRH

Application web de recrutement assistée par intelligence artificielle, développée en Python avec Flask. Elle permet à un recruteur de :

- créer un compte et se connecter,
- télécharger un CV au format PDF,
- analyser la compatibilité entre le CV et une offre d'emploi,
- lancer un entretien de recrutement simulé en temps réel avec un assistant IA,
- enregistrer la transcription et obtenir une évaluation finale de l'entretien.

---

## Fonctionnalités

### 1. Gestion des comptes
- Inscription et connexion utilisateur
- Session sécurisée avec Flask
- Stockage des comptes dans SQLite

### 2. Analyse de CV
- Import d'un CV au format PDF
- Extraction du texte via `pypdf`
- Analyse de l'adéquation CV / offre d'emploi grâce à Google Gemini
- Retour structuré sous forme JSON : score, points forts, points faibles, compétences manquantes, recommandations, questions probables

### 3. Offres d'emploi
- Catalogue d'offres prédéfini dans `offres.py`
- Support de plusieurs postes :
  - Développeur Fullstack IA
  - Chargé(e) de Marketing Digital
  - Data Analyst

### 4. Entretien simulé avec IA
- Session d'entretien en live via WebSocket
- Conversation audio/texte avec Gemini Live
- Génération d'un message d'accueil personnalisé selon l'offre
- Suivi de l'état de l'entretien (en cours / terminé)
- Évaluation finale du candidat après la transcription

### 5. Historique et suivi
- Conservation des CV uploadés
- Historique des analyses effectuées
- Historique des entretiens et évaluations

---

## Stack technique

- Python 3
- Flask
- Flask-Sock (WebSocket)
- SQLite
- Google GenAI / Gemini
- PyPDF
- Werkzeug

---

## Structure du projet

```text
IA_DRH/
├── script.py              # Application Flask principale
├── ia.py                  # Logique d'IA et appels Gemini
├── models.py              # Initialisation SQLite et schéma de données
├── offres.py              # Catalogue des offres et contenu des postes
├── live.py                # Instructions système pour l'entretien oral
├── requirements.txt       # Dépendances Python
├── database.db            # Base SQLite générée automatiquement
├── uploads/               # CV importés par les utilisateurs
├── static/                # Fichiers front-end statiques
├── templates/             # Templates HTML Flask
├── .env                   # Variables d'environnement locales
└── README.md              # Documentation du projet
```

---

## Prérequis

- Python 3.10+
- Un accès à l'API Google Gemini
- Un fichier `.env` configuré localement

---

## Installation

1. Cloner le projet

```bash
git clone <url-du-projet>
cd IA_DRH
```

2. Créer un environnement virtuel

```bash
python -m venv .venv
```

3. Activer l'environnement virtuel

Sous Windows PowerShell :

```powershell
.\.venv\Scripts\Activate.ps1
```

Sous Linux/macOS :

```bash
source .venv/bin/activate
```

4. Installer les dépendances

```bash
pip install -r requirements.txt
```

5. Créer un fichier `.env`

```env
SECRET_KEY=votre_cle_secrete
GEMINI_API_KEY=votre_cle_api_google
PORT=5001
GEMINI_MODEL=gemini-2.5-flash
GEMINI_LIVE_MODEL=gemini-2.0-flash-exp
GEMINI_LIVE_VOICE=Puck
```

> Le fichier `.env` n'est pas versionné et doit contenir vos clés locales.

---

## Lancer l'application

```bash
python script.py
```

L'application démarre alors par défaut sur :

```text
http://localhost:5001
```

---

## Utilisation

1. Ouvrir l'URL de l'application dans le navigateur.
2. Créer un compte ou se connecter.
3. Uploader un CV au format PDF.
4. Sélectionner une offre d'emploi.
5. Lancer l'analyse du CV.
6. Démarrer un entretien simulé AI.
7. Terminer l'entretien pour obtenir une évaluation détaillée.

---

## Base de données

Le projet utilise SQLite avec le fichier `database.db`.

La base est créée automatiquement au démarrage via `models.py` et contient notamment :

- `users`
- `pdfs`
- `analyses`
- `entretiens`

---

## Sécurité et bonnes pratiques

- Garder les clés API dans le fichier `.env`
- Ne pas exposer le secret dans le dépôt Git
- Sécuriser la clé `SECRET_KEY` en production
- Vérifier les droits d'accès utilisateur sur les CV et entretiens

---

## Remarques

Ce projet est une démonstration d'un outil RH intelligent, orienté vers l'automatisation du tri de CV et de l'entretien de recrutement. Il est conçu pour être facilement extensible :

- ajout de nouvelles offres,
- intégration d'autres modèles d'IA,
- amélioration du moteur d'évaluation,
- ajout d'une interface plus avancée côté front.

---

## Licence

Ce projet est fourni sans licence spécifique dans ce dépôt. À adapter selon votre contexte d'utilisation.
