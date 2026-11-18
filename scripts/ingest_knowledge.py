"""
Script d'Ingestion et de Scraping de Documents Administratifs du Mali.
Permet d'enrichir durablement la base de connaissances du DSP :
1. Téléchargement / Scraping de pages officielles (portails .gov.ml, Journal Officiel).
2. Nettoyage HTML et extraction du texte utile.
3. Découpage en sections normalisées Markdown (### Titre du document).
4. Sauvegarde dans data/knowledge/ et ré-indexation vectorielle automatique.
"""

import argparse
import logging
import os
import re
import sys
import urllib.request
from typing import List, Optional

# Configuration des chemins
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

KNOWLEDGE_DIR = os.path.join(BASE_DIR, "data", "knowledge")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("KnowledgeIngestion")

# Portails officiels documentaires de référence au Mali
OFFICIAL_SOURCES_MALI = [
    {
        "name": "Portail National des Démarches Administratives",
        "url": "https://demarchesadministratives.gouv.ml",
        "description": "Portail interministériel officiel recensant les procédures citoyennes (CNI, état civil, permis, passeport).",
    },
    {
        "name": "Portail des Services Publics du Mali",
        "url": "https://servicespublics.gov.ml",
        "description": "Fiches officielles des démarches administratives et ministérielles.",
    },
    {
        "name": "Secrétariat Général du Gouvernement (SGG)",
        "url": "https://sgg-mali.ml",
        "description": "Journal Officiel de la République du Mali, lois, ordonnances et décrets.",
    },
    {
        "name": "Direction Générale de la Police Nationale (DGPN)",
        "url": "https://dgpn.gouv.ml",
        "description": "Conditions de délivrance des cartes d'identité biométriques et passeports.",
    },
    {
        "name": "Direction Générale des Impôts (DGI)",
        "url": "https://dgid.gouv.ml",
        "description": "Fiscalité malienne, NIF, timbres fiscaux, droits d'enregistrement.",
    },
]


def clean_html_to_markdown(html_content: str, title: str) -> str:
    """Transforme un flux HTML brut en un document Markdown propre."""
    # Suppression des balises script et style
    text = re.sub(r"<script[^>]*>.*?</script>", "", html_content, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    # Remplacement des balises de saut de ligne et paragraphes
    text = re.sub(r"<(?:br|p|div|li)[^>]*>", "\n", text, flags=re.IGNORECASE)
    # Suppression de toutes les balises HTML restantes
    text = re.sub(r"<[^>]+>", " ", text)
    # Décodage des entités HTML courantes
    text = text.replace("&nbsp;", " ").replace("&eacute;", "é").replace("&agrave;", "à").replace("&egrave;", "è")
    text = text.replace("&ocirc;", "ô").replace("&icirc;", "î").replace("&amp;", "&").replace("&quot;", '"')
    # Normalisation des espaces multiples
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in text.split("\n")]
    clean_body = "\n".join([ln for ln in lines if len(ln) > 20])

    markdown_doc = f"### {title}\n{clean_body}\n"
    return markdown_doc


def fetch_url(url: str, timeout: int = 10) -> Optional[str]:
    """Télécharge le contenu HTML d'une page Web officielle."""
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ChatbotCitoyenMali-DSP/1.0"
            },
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                charset = response.headers.get_content_charset() or "utf-8"
                return response.read().decode(charset, errors="replace")
    except Exception as e:
        logger.warning(f"Impossible de joindre {url} : {e}")
    return None


def add_document_chunk(filename: str, title: str, content: str):
    """Ajoute une section documentaire normalisée dans data/knowledge/."""
    os.makedirs(KNOWLEDGE_DIR, exist_ok=True)
    target_file = os.path.join(KNOWLEDGE_DIR, filename)

    chunk = f"\n### {title}\n{content.strip()}\n"
    mode = "a" if os.path.exists(target_file) else "w"
    with open(target_file, mode, encoding="utf-8") as f:
        f.write(chunk)
    logger.info(f"Section '{title}' enregistrée avec succès dans {target_file}")


def reindex_vector_store():
    """Déclenche la ré-indexation complète du Vector Store."""
    from intelligence.vector_store import get_vector_store
    store = get_vector_store()
    store.index_knowledge_base()
    logger.info(f"VectorStore actualisé : {len(store.chunks)} documents indexés.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Outil d'ingestion de documents administratifs maliens.")
    parser.add_argument("--url", type=str, help="URL de la page administrative à scraper")
    parser.add_argument("--title", type=str, help="Titre de la démarche ou loi")
    parser.add_argument("--file", type=str, default="demarches_web.md", help="Nom du fichier cible dans data/knowledge/")
    parser.add_argument("--reindex", action="store_true", help="Ré-indexer le vector store après l'ajout")
    parser.add_argument("--list-sources", action="store_true", help="Lister les plateformes administratives du Mali")

    args = parser.parse_args()

    if args.list_sources:
        print("\n🏛️  PLATEFORMES ADMINISTRATIVES OFFICIELLES DU MALI (SCRAPING & VEILLE) :")
        for src in OFFICIAL_SOURCES_MALI:
            print(f"• {src['name']} : {src['url']}")
            print(f"  └─ {src['description']}")
        sys.exit(0)

    if args.url and args.title:
        logger.info(f"Téléchargement de {args.url}...")
        html = fetch_url(args.url)
        if html:
            md = clean_html_to_markdown(html, args.title)
            add_document_chunk(args.file, args.title, md)
        else:
            logger.error("Échec de la récupération du contenu.")

    if args.reindex:
        reindex_vector_store()
