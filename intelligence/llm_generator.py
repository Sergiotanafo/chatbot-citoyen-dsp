"""
Générateur RAG Mistral / LLM pour le DSP Chatbot Citoyen Malien.
Prend en charge :
1. Ollama local (ex: mistral, mistral:7b, llama3)
2. LM Studio / vLLM / Mistral API (endpoint OpenAI-compatible)
3. Fallback extractif & synthétique déterministe (haute disponibilité sans GPU)
"""

import json
import logging
import os
import re
import urllib.request
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Configuration des endpoints LLM
LLM_PROVIDER = os.environ.get("DSP_LLM_PROVIDER", "auto")  # auto, ollama, openai_compatible, fallback
OLLAMA_HOST = os.environ.get("DSP_OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("DSP_OLLAMA_MODEL", "mistral")
OPENAI_COMPATIBLE_HOST = os.environ.get("DSP_OPENAI_HOST", "http://localhost:1234/v1")
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY", "")

SYSTEM_PROMPT_FR = """Tu es l'assistant virtuel officiel de l'administration publique du Mali (Chatbot Citoyen Malien).
Ta mission est de répondre à la question du citoyen de manière vivante, fluide, chaleureuse et pédagogique.

Directives absolues de formulation :
1. REFORMULE TOUJOURS avec tes propres mots. Ne recopie jamais mot pour mot les fiches brutes ou les titres techniques. Parle comme un agent d'accueil bienveillant dans une mairie ou un commissariat malien.
2. Pour les démarches administratives officielles (tarifs, documents requis, lieux de dépôt, délais légaux), appuie-toi fidèlement sur les faits mentionnés dans la documentation sans inventer de règles.
3. Pour les concepts juridiques ou administratifs (ex: greffe, timbre fiscal, jugement supplétif), explique-les simplement avec des exemples concrets de la vie quotidienne.
4. Reste clair et concis (environ 2 à 3 paragraphes ou puces nettes).
"""

SYSTEM_PROMPT_BM = """I ye Mali fasoden dɛmɛbaga ye sariyasɛbɛn kow la.
I ka kuma kɛ Bamanankan na ka ɲininkali jaabi cogo teliya, ɲuman ani nɔgɔman na.
Sariyasɛbɛn sɔngɔ, sɛbɛn minnu bɛ ɲini ni waati kow la, i k'i jigi bila sɛbɛn kɔnɔnakow kan nka i k'a fɔ i yɛrɛ ka da kɔnɔ kuma na.
"""


class MistralRAGGenerator:
    """Moteur de génération et de synthèse de réponses RAG."""

    def __init__(self):
        self.provider = LLM_PROVIDER
        try:
            self.timeout = int(os.environ.get("DSP_LLM_TIMEOUT", "45"))
        except (ValueError, TypeError):
            self.timeout = 45

    def generate(
        self,
        query: str,
        context_chunks: List[str],
        language: str = "fr",
        topic_title: Optional[str] = None,
    ) -> str:
        """Génère la réponse finale en s'appuyant sur les passages documentaires retrouvés."""
        if not context_chunks:
            return self.generate_general(query, language=language)

        # Nettoyage et allègement du contexte pour accélérer le traitement LLM
        cleaned_chunks = []
        for ch in context_chunks:
            lines = [
                l.strip() for l in ch.split("\n")
                if l.strip() and not l.startswith("Questions fréquentes") and not l.startswith("Ñininkaliw")
            ]
            cleaned_chunks.append("\n".join(lines))
        context_text = "\n\n---\n\n".join(cleaned_chunks)
        lang_code = "bm" if language.lower() in ["bm", "bambara", "bamanankan"] else "fr"

        # 1. Tentative via Ollama si disponible
        if self.provider in ["auto", "ollama"]:
            ollama_resp = self._query_ollama(query, context_text, lang_code)
            if ollama_resp:
                return ollama_resp

        # 2. Tentative via endpoint OpenAI / LM Studio / Mistral API
        if self.provider in ["auto", "openai_compatible"]:
            openai_resp = self._query_openai_compatible(query, context_text, lang_code)
            if openai_resp:
                return openai_resp

        # 3. Fallback extractif & synthétique déterministe (sans dépendance externe)
        return self._extractive_synthesis(query, context_chunks, lang_code, topic_title)

    def generate_general(self, query: str, language: str = "fr") -> str:
        """Génère une réponse pour les questions générales hors base documentaire (culture, définitions, Mali)."""
        lang_code = "bm" if language.lower() in ["bm", "bambara", "bamanankan"] else "fr"
        system_p = (
            "I ye Mali fasoden dɛmɛbaga ye. Jaabi kɛ Bamanankan na cogo nɔgɔman na."
            if lang_code == "bm"
            else (
                "Tu es l'assistant virtuel officiel Chatbot Citoyen du Mali. "
                "Réponds à la question de l'usager avec exactitude, clarté, bienveillance et concision. "
                "Si la question concerne le Mali, sa géographie, sa culture ou ses institutions, donne une réponse directe et précise. "
                "Si la question s'éloigne totalement de la citoyenneté ou du Mali, réponds brièvement puis rappelle poliment que tu es spécialisé dans l'accompagnement des démarches administratives maliennes."
            )
        )

        prompt = f"QUESTION : {query}\n\nRÉPONSE DIRECTE ET PRÉCISE :"

        # 1. Tentative Ollama
        if self.provider in ["auto", "ollama"]:
            resp = self._query_ollama_raw(prompt=prompt, system=system_p)
            if resp:
                return resp

        # 2. Tentative OpenAI / LM Studio
        if self.provider in ["auto", "openai_compatible"]:
            resp = self._query_openai_raw(prompt=query, system=system_p)
            if resp:
                return resp

        # 3. Réponse déterministe de repli courtois
        if lang_code == "bm":
            return (
                "Hakɛto, n bɛ baara kɛ Mali sariyasɛbɛn kow de kan (fasodenya sariyasɛbɛn, pasan, wolosɛbɛn, kititigɛso sɛbɛn). "
                "Ni i bɛ sariyasɛbɛn dɔ ɲini, i bɛ se k'o ɲininkali kɛ."
            )
        return (
            "Désolé, je suis spécialisé dans les démarches administratives du Mali (carte d'identité, passeport, état civil, casier judiciaire, etc.). "
            "Je n'ai pas trouvé d'information administrative officielle correspondant à votre demande. Pourriez-vous reformuler ou préciser votre démarche ?"
        )

    def _query_ollama_raw(self, prompt: str, system: str) -> Optional[str]:
        """Interroge directement Ollama avec un prompt et un system prompt personnalisés."""
        url = f"{OLLAMA_HOST}/api/generate"
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "system": system,
            "stream": False,
            "options": {
                "num_predict": 300,
                "temperature": 0.4,
                "top_p": 0.9,
            },
        }
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    text = data.get("response", "").strip()
                    if text:
                        logger.info(f"[LLMGenerator] Réponse générée avec succès par Ollama ({OLLAMA_MODEL}).")
                        return text
        except urllib.error.URLError as e:
            logger.debug(f"[LLMGenerator] Connexion Ollama échouée ({e.reason}). Fallback actif.")
        except Exception as e:
            logger.debug(f"[LLMGenerator] Ollama erreur : {e}. Fallback actif.")
        return None

    def _query_openai_raw(self, prompt: str, system: str) -> Optional[str]:
        """Interroge un serveur compatible OpenAI."""
        url = f"{OPENAI_COMPATIBLE_HOST}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if MISTRAL_API_KEY:
            headers["Authorization"] = f"Bearer {MISTRAL_API_KEY}"

        payload = {
            "model": "mistral-small",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers=headers,
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    text = data["choices"][0]["message"]["content"].strip()
                    if text:
                        return text
        except Exception:
            pass
        return None

    def _query_ollama(self, query: str, context: str, lang: str) -> Optional[str]:
        """Interroge Ollama localement avec contexte documentaire."""
        system_p = SYSTEM_PROMPT_BM if lang == "bm" else SYSTEM_PROMPT_FR
        prompt = (
            f"CONTEXTE ADMINISTRATIF :\n{context}\n\n"
            f"QUESTION DE L'USAGER : {query}\n\n"
            f"RÉPONSE CLAIRE ET STRUCTURÉE :"
        )
        return self._query_ollama_raw(prompt=prompt, system=system_p)

    def _query_openai_compatible(self, query: str, context: str, lang: str) -> Optional[str]:
        """Interroge un serveur compatible OpenAI (LM Studio, vLLM, Mistral API)."""
        system_p = SYSTEM_PROMPT_BM if lang == "bm" else SYSTEM_PROMPT_FR
        prompt = f"CONTEXTE :\n{context}\n\nQUESTION : {query}"
        return self._query_openai_raw(prompt=prompt, system=system_p)

    def _extractive_synthesis(
        self,
        query: str,
        context_chunks: List[str],
        lang: str,
        topic_title: Optional[str] = None,
    ) -> str:
        """Synthétiseur déterministe haute fidélité sans dépendance LLM externe.
        Extrait les éléments clés correspondant précisément à la question.
        """
        primary_chunk = context_chunks[0]

        # Détection du besoin spécifique de la question
        q_low = query.lower()
        is_definition = any(
            w in q_low
            for w in [
                "c'est quoi", "qu'est-ce", "quest-ce", "définition", "definition",
                "signifie", "veut dire", "mun don", "ye mun ye", "c est quoi",
                "c'est", "c est", "qu'est ce"
            ]
        )
        needs_price = any(w in q_low for w in ["combien", "prix", "cout", "coût", "tarif", "payant", "gratuit", "wari", "sɔngɔ"])
        needs_pieces = any(w in q_low for w in ["document", "documents", "piece", "pièce", "pièces", "papier", "papiers", "dossier", "seben", "sɛbɛn", "il faut quel"])
        needs_delai = any(w in q_low for w in ["délai", "delai", "temps", "combien de temps", "quand", "waati", "tile"])
        needs_place = any(w in q_low for w in ["où", "ou", "lieu", "endroit", "déposer", "trouver", "faire", "yɔrɔ", "min"])

        # Analyse du chunk structuré
        lines = [ln.strip() for ln in primary_chunk.split("\n") if ln.strip()]
        title_line = topic_title or (lines[0].replace("#", "").strip() if lines else "Démarche Administrative")

        # 1. Cas question de définition / explication de concept (prioritaire)
        if is_definition:
            for line in lines:
                if line.startswith("#") or line.startswith("Questions fréquentes") or line.startswith("Ñininkaliw"):
                    continue
                if line.startswith("Démarche & Détails :") or line.startswith("Baara cogo :"):
                    def_text = line.split(":", 1)[1].strip()
                    if lang == "bm":
                        return f"💡 *{title_line} kɔnɔna faamuyali :*\n\n{def_text}"
                    return f"💡 *Explication & Définition : {title_line}*\n\n{def_text}"
                # Cas document issu de data/knowledge/ : extraire la première définition concrète
                if any(verb in line.lower() for verb in [" est ", " sont ", " désigne ", " qualifie ", " concerne ", " se rapporte ", "perçue par", "decision de justice", "décision de justice"]):
                    if lang == "bm":
                        return f"💡 *{title_line} kɔnɔna faamuyali :*\n\n{line}"
                    return f"💡 *Définition & Notion : {title_line}*\n\n{line}"

        # Cas document issu du dossier documentaire brut (data/knowledge/)
        if any(h in primary_chunk for h in ["### ", "## "]) or not any("Démarche & Détails :" in l for l in lines):
            clean_lines = [l for l in lines if not l.startswith("#")]
            clean_body = "\n".join(clean_lines)
            if lang == "bm":
                return f"💡 *{title_line}*\n\n{clean_body}"
            return f"💡 *{title_line}*\n\n{clean_body}"

        # 2. Filtrage ciblé selon le besoin
        extracted_sections = []
        for line in lines:
            if needs_price and ("frais" in line.lower() or "wari" in line.lower() or "sɔngɔ" in line.lower()):
                extracted_sections.append(line)
            elif needs_pieces and ("pièces" in line.lower() or "sɛbɛn" in line.lower() or line.startswith("1.") or line.startswith("2.")):
                extracted_sections.append(line)
            elif needs_delai and ("délai" in line.lower() or "waati" in line.lower() or "tile" in line.lower()):
                extracted_sections.append(line)

        if extracted_sections:
            if lang == "bm":
                return f"📌 *{title_line}*\n" + "\n".join(extracted_sections)
            return f"📌 *{title_line}*\n" + "\n".join(extracted_sections)

        # Si pas de focus unitaire, formater la synthèse de façon élégante et lisible
        clean_lines = []
        for ln in lines:
            if ln == title_line or ln.startswith("#") or ln.startswith("Questions fréquentes") or ln.startswith("Ñininkaliw"):
                continue
            if ln.startswith("Démarche & Détails :"):
                clean_lines.append(f"📌 **Procédure officielle** :\n{ln.split(':', 1)[1].strip()}")
            elif ln.startswith("Baara cogo :"):
                clean_lines.append(f"📌 **Baara cogo** :\n{ln.split(':', 1)[1].strip()}")
            elif ln.startswith("Pièces à fournir :"):
                clean_lines.append(f"📋 **Documents requis** :\n{ln.split(':', 1)[1].strip()}")
            elif ln.startswith("Sɛbɛn minnu bɛ ɲini :"):
                clean_lines.append(f"📋 **Sɛbɛn minnu bɛ ɲini** :\n{ln.split(':', 1)[1].strip()}")
            elif ln.startswith("Frais officiels :"):
                clean_lines.append(f"💵 **Tarif officiel** : {ln.split(':', 1)[1].strip()}")
            elif ln.startswith("Wari sɔngɔ :"):
                clean_lines.append(f"💵 **Wari sɔngɔ** : {ln.split(':', 1)[1].strip()}")
            elif ln.startswith("Délais légaux :"):
                clean_lines.append(f"⏱️ **Délai moyen** : {ln.split(':', 1)[1].strip()}")
            elif ln.startswith("Waati joli :"):
                clean_lines.append(f"⏱️ **Waati** : {ln.split(':', 1)[1].strip()}")
            else:
                clean_lines.append(ln)

        body_text = "\n\n".join(clean_lines)
        return f"🇲🇱 *{title_line}*\n\n{body_text}"


# Singleton
_generator_instance = None

def get_llm_generator() -> MistralRAGGenerator:
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = MistralRAGGenerator()
    return _generator_instance
