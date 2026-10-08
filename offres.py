OFFRES = {
    "dev_fullstack_ia": {
        "titre": "Développeur Fullstack IA",
        "description": (
            "Concevoir et développer des applications web de bout en bout intégrant "
            "des fonctionnalités d'intelligence artificielle (LLM, RAG, agents)."
        ),
        "competences": [
            "Python (Flask / FastAPI / Django)",
            "JavaScript / TypeScript, React ou Vue",
            "API REST, bases de données SQL et NoSQL",
            "Intégration d'API de LLM (OpenAI, etc.), prompt engineering, RAG",
            "Git, Docker, CI/CD, déploiement cloud",
        ],
        "profil": "Bac+3 à Bac+5 en informatique, 1 à 3 ans d'expérience, curieux et autonome.",
    },
    "marketing_digital": {
        "titre": "Chargé(e) de Marketing Digital",
        "description": (
            "Piloter la stratégie d'acquisition et de visibilité en ligne : "
            "SEO/SEA, réseaux sociaux, emailing et analyse de performance."
        ),
        "competences": [
            "SEO / SEA (Google Ads, Meta Ads)",
            "Gestion des réseaux sociaux et création de contenu",
            "Emailing et marketing automation",
            "Google Analytics, suivi de KPI et reporting",
            "Outils IA pour la création de contenu",
        ],
        "profil": "Bac+3 à Bac+5 en marketing / communication, créatif et orienté résultats.",
    },
    "data_analyst": {
        "titre": "Data Analyst",
        "description": (
            "Collecter, nettoyer et analyser les données de l'entreprise afin de "
            "produire des indicateurs et tableaux de bord utiles à la décision."
        ),
        "competences": [
            "SQL avancé",
            "Python (pandas, numpy) ou R",
            "Power BI / Tableau / Looker",
            "Statistiques et visualisation de données",
            "Excel avancé, communication des résultats",
        ],
        "profil": "Bac+3 à Bac+5 en statistiques, data ou informatique, rigoureux et pédagogue.",
    },
}


def get_offre(offre_id):
    return OFFRES.get(offre_id)


def offre_en_texte(offre_id):
    offre = OFFRES[offre_id]
    competences = "\n".join(f"- {c}" for c in offre["competences"])
    return (
        f"Poste : {offre['titre']}\n"
        f"Description : {offre['description']}\n"
        f"Compétences attendues :\n{competences}\n"
        f"Profil recherché : {offre['profil']}"
    )
