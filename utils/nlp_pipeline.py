"""
utils/nlp_pipeline.py
──────────────────────
NLP Pipeline for resume screening.

Features:
  - Text preprocessing (tokenization, stopword removal, lemmatization)
  - Skill extraction using spaCy NER + keyword matching
  - TF-IDF vectorization
  - KNN-based candidate ranking
  - Cosine similarity scoring
"""

import re
import numpy as np
import spacy
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors
from sklearn.metrics.pairwise import cosine_similarity
from loguru import logger

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

# ── Known tech skills dictionary ──────────────────────────────────
TECH_SKILLS = {
    # Languages
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust",
    "ruby", "php", "swift", "kotlin", "scala", "r", "matlab",
    # Web
    "react", "angular", "vue", "node.js", "fastapi", "django", "flask",
    "express", "spring", "html", "css", "rest", "graphql",
    # Data
    "sql", "postgresql", "mysql", "mongodb", "redis", "elasticsearch",
    "apache spark", "kafka", "airflow", "pandas", "numpy", "tensorflow",
    "pytorch", "scikit-learn", "keras",
    # Cloud & DevOps
    "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "jenkins",
    "github actions", "ci/cd", "linux", "git",
    # Other
    "machine learning", "deep learning", "nlp", "computer vision",
    "microservices", "agile", "scrum",
}


class NLPPipeline:
    """
    Core NLP pipeline for resume and JD processing.
    Used by the Screener Agent for fast, explainable ranking.
    """

    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            max_features=5000,
            ngram_range=(1, 2),       # unigrams + bigrams
            stop_words="english",
            sublinear_tf=True,        # apply log normalization
        )
        self.knn = NearestNeighbors(
            n_neighbors=10,
            metric="cosine",
            algorithm="brute",
        )
        self.fitted = False
        self.jd_vectors = None
        self.jd_texts = []
        self.jd_metadata = []
        logger.info("NLP Pipeline initialized")

    # ── Text Preprocessing ────────────────────────────────────────

    def preprocess(self, text: str) -> str:
        """
        Clean and normalize text.
        - Lowercase
        - Remove special chars
        - Lemmatize
        - Remove stopwords
        """
        text = text.lower()
        text = re.sub(r"[^\w\s\+\#\.]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()

        doc = nlp(text)
        tokens = [
            token.lemma_
            for token in doc
            if not token.is_stop and not token.is_punct and len(token.text) > 1
        ]
        return " ".join(tokens)

    # ── Skill Extraction ──────────────────────────────────────────

    def extract_skills(self, text: str) -> list[str]:
        """
        Extract technical skills from text using:
        1. spaCy NER (catches proper nouns like AWS, Docker)
        2. Keyword matching against TECH_SKILLS dictionary
        """
        text_lower = text.lower()
        found_skills = set()

        # Method 1: keyword matching
        for skill in TECH_SKILLS:
            if skill in text_lower:
                found_skills.add(skill)

        # Method 2: spaCy NER — catch proper nouns and orgs
        doc = nlp(text[:5000])
        for ent in doc.ents:
            if ent.label_ in ("ORG", "PRODUCT") and len(ent.text) > 1:
                skill_candidate = ent.text.lower().strip()
                if skill_candidate in TECH_SKILLS:
                    found_skills.add(skill_candidate)

        return sorted(list(found_skills))

    # ── TF-IDF Vectorization ──────────────────────────────────────

    def fit_vectorizer(self, texts: list[str]):
        """Fit TF-IDF on a corpus of texts."""
        processed = [self.preprocess(t) for t in texts]
        self.vectorizer.fit(processed)
        logger.debug(f"TF-IDF fitted | vocab_size={len(self.vectorizer.vocabulary_)}")

    def vectorize(self, text: str) -> np.ndarray:
        """Convert a single text to TF-IDF vector."""
        processed = self.preprocess(text)
        return self.vectorizer.transform([processed]).toarray()[0]

    def vectorize_batch(self, texts: list[str]) -> np.ndarray:
        """Convert multiple texts to TF-IDF matrix."""
        processed = [self.preprocess(t) for t in texts]
        return self.vectorizer.transform(processed).toarray()

    # ── KNN Ranking ───────────────────────────────────────────────

    def fit_knn(self, jd_texts: list[str], jd_metadata: list[dict]):
        """
        Fit KNN on job description vectors.
        Call this after adding JDs to the system.
        """
        self.jd_texts = jd_texts
        self.jd_metadata = jd_metadata
        self.fit_vectorizer(jd_texts)
        self.jd_vectors = self.vectorize_batch(jd_texts)
        self.knn.fit(self.jd_vectors)
        self.fitted = True
        logger.info(f"KNN fitted | jds={len(jd_texts)}")

    def find_similar_jds(self, resume_text: str, top_k: int = 5) -> list[dict]:
        """
        Find most similar JDs for a resume using KNN.
        Returns list of {metadata, similarity_score, rank}
        """
        if not self.fitted:
            logger.warning("KNN not fitted — no JDs in system")
            return []

        resume_vec = self.vectorize(resume_text).reshape(1, -1)
        k = min(top_k, len(self.jd_texts))
        distances, indices = self.knn.kneighbors(resume_vec, n_neighbors=k)

        results = []
        for rank, (dist, idx) in enumerate(zip(distances[0], indices[0])):
            similarity = float(1 - dist)   # cosine distance → similarity
            results.append({
                "rank": rank + 1,
                "similarity_score": round(similarity * 100, 1),
                "metadata": self.jd_metadata[idx],
                "jd_text": self.jd_texts[idx],
            })

        return results

    # ── Candidate Scoring ─────────────────────────────────────────

    def score_candidate(self, resume_text: str, jd_text: str) -> dict:
        """
        Score a single candidate against a JD.
        Returns detailed NLP scores.
        """
        # Preprocess both
        resume_processed = self.preprocess(resume_text)
        jd_processed = self.preprocess(jd_text)

        # Fit vectorizer on both texts combined
        local_vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            stop_words="english",
            sublinear_tf=True,
        )
        local_vectorizer.fit([resume_processed, jd_processed])
        vectors = local_vectorizer.transform([resume_processed, jd_processed]).toarray()

        # Cosine similarity
        cos_sim = float(cosine_similarity([vectors[0]], [vectors[1]])[0][0])

        # Skill matching
        resume_skills = set(self.extract_skills(resume_text))
        jd_skills = set(self.extract_skills(jd_text))

        matched = resume_skills & jd_skills
        missing = jd_skills - resume_skills
        bonus = resume_skills - jd_skills

        skill_score = (len(matched) / len(jd_skills) * 100) if jd_skills else 0

        # Combined NLP score (cosine * 0.5 + skill_match * 0.5)
        nlp_score = (cos_sim * 50) + (skill_score * 0.5)

        return {
            "cosine_similarity": round(cos_sim * 100, 1),
            "skill_match_score": round(skill_score, 1),
            "nlp_score": round(nlp_score, 1),
            "matched_skills": sorted(list(matched)),
            "missing_skills": sorted(list(missing)),
            "bonus_skills": sorted(list(bonus)),
        }

    def rank_candidates(
        self,
        jd_text: str,
        resume_texts: list[str],
        candidate_names: list[str],
    ) -> list[dict]:
        """
        Rank multiple candidates against a JD using NLP.
        Returns sorted list with NLP scores.
        """
        results = []
        for i, (resume, name) in enumerate(zip(resume_texts, candidate_names)):
            scores = self.score_candidate(resume, jd_text)
            results.append({
                "rank": 0,
                "name": name,
                "resume_index": i,
                **scores,
            })

        # Sort by nlp_score descending
        results.sort(key=lambda x: x["nlp_score"], reverse=True)

        # Assign final ranks
        for i, r in enumerate(results):
            r["rank"] = i + 1

        logger.info(f"Ranked {len(results)} candidates | top_score={results[0]['nlp_score'] if results else 0}")
        return results


# ── Singleton instance ────────────────────────────────────────────
nlp_pipeline = NLPPipeline()