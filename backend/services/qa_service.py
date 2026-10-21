import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass
class Passage:
    passage_id: int
    text: str
    page_number: Optional[int]


@dataclass
class ScoredPassage:
    passage: Passage
    score: float
    matched_terms: List[str]


QUESTION_STOP_WORDS = {
    "what", "is", "are", "was", "were", "the", "a", "an", "in", "on", "at",
    "by", "for", "with", "about", "against", "between", "into", "through",
    "during", "before", "after", "above", "below", "to", "from", "up", "down",
    "of", "off", "over", "under", "again", "further", "then", "once", "here",
    "there", "when", "where", "why", "how", "all", "any", "both", "each",
    "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only",
    "own", "same", "so", "than", "too", "very", "can", "will", "just", "don",
    "should", "now", "tell", "me", "show", "give", "find", "does", "did", "do"
}


def segment_document_into_passages(text: str) -> List[Passage]:
    """
    Segment document text into passages while preserving reliable page metadata.
    Detects page markers such as:
      - '--- Page X ---'
      - '[Page X]'
      - 'Page X:'
    """
    if not text or not text.strip():
        return []

    lines = text.split("\n")
    passages: List[Passage] = []

    current_page = 1
    current_lines: List[str] = []
    passage_counter = 0

    page_marker_regex = re.compile(
        r"^(?:---+\s*Page\s*(\d+)\s*---+|\[\s*Page\s*(\d+)\s*\]|Page\s*(\d+)\s*:)",
        re.IGNORECASE
    )

    def flush_passage():
        nonlocal passage_counter, current_lines
        if not current_lines:
            return
        passage_text = " ".join(" ".join(current_lines).split()).strip()
        current_lines = []

        if len(passage_text) >= 10:
            # If passage is very long, split into multi-sentence chunks
            if len(passage_text) > 400:
                sentences = re.split(r"(?<=[.!?])\s+", passage_text)
                chunk: List[str] = []
                chunk_len = 0
                for s in sentences:
                    s_clean = s.strip()
                    if not s_clean:
                        continue
                    chunk.append(s_clean)
                    chunk_len += len(s_clean)
                    if chunk_len >= 250:
                        passage_counter += 1
                        passages.append(
                            Passage(
                                passage_id=passage_counter,
                                text=" ".join(chunk),
                                page_number=current_page
                            )
                        )
                        chunk = []
                        chunk_len = 0
                if chunk:
                    passage_counter += 1
                    passages.append(
                        Passage(
                            passage_id=passage_counter,
                            text=" ".join(chunk),
                            page_number=current_page
                        )
                    )
            else:
                passage_counter += 1
                passages.append(
                    Passage(
                        passage_id=passage_counter,
                        text=passage_text,
                        page_number=current_page
                    )
                )

    for line in lines:
        stripped = line.strip()
        if not stripped:
            flush_passage()
            continue

        match = page_marker_regex.match(stripped)
        if match:
            flush_passage()
            page_str = match.group(1) or match.group(2) or match.group(3)
            try:
                current_page = int(page_str)
            except (ValueError, TypeError):
                pass
            continue

        current_lines.append(stripped)

    flush_passage()
    return passages


def extract_keywords(query: str) -> List[str]:
    """
    Extract meaningful search keywords from the query.
    """
    words = re.findall(r"\b[A-Za-z0-9_-]{2,}\b", query.lower())
    keywords = [w for w in words if w not in QUESTION_STOP_WORDS]
    return keywords if keywords else words


class DocumentQAService:
    """
    Enterprise Document Question Answering Engine.
    Uses existing Scikit-Learn TF-IDF, token matching, and contextual evidence extraction.
    Strictly isolated to the selected document.
    """

    def answer_question(
        self,
        document_text: str,
        question: str
    ) -> Tuple[str, List[dict], bool]:
        """
        Answers a question using only the provided document text.

        Returns:
            (answer_text, citations_list, has_sufficient_evidence)
        """
        # Validate document text
        if not document_text or not document_text.strip():
            return (
                "The selected document is empty and does not contain readable text to answer questions.",
                [],
                False
            )

        passages = segment_document_into_passages(document_text)
        if not passages:
            return (
                "The selected document does not contain readable text passages.",
                [],
                False
            )

        keywords = extract_keywords(question)
        if not keywords:
            return (
                "Please provide a more specific question with keywords related to the document.",
                [],
                False
            )

        # Build corpus of passages
        corpus = [p.text for p in passages]

        # TF-IDF Retrieval
        try:
            vectorizer = TfidfVectorizer(
                ngram_range=(1, 2),
                stop_words="english",
                token_pattern=r"(?u)\b\w+\b"
            )
            tfidf_matrix = vectorizer.fit_transform(corpus)
            query_vector = vectorizer.transform([question])
            similarities = cosine_similarity(query_vector, tfidf_matrix).flatten()
        except Exception:
            similarities = np.zeros(len(passages))

        scored_passages: List[ScoredPassage] = []

        for idx, passage in enumerate(passages):
            p_text_lower = passage.text.lower()

            # Exact keyword overlap score
            matched = [k for k in keywords if k in p_text_lower]
            overlap_score = len(matched) / len(keywords) if keywords else 0.0

            # Substring boost for consecutive multi-word matches
            boost = 0.0
            if len(keywords) >= 2:
                joined_keywords = " ".join(keywords[:2])
                if joined_keywords in p_text_lower:
                    boost = 0.25

            # Combined score
            tfidf_val = float(similarities[idx]) if idx < len(similarities) else 0.0
            final_score = (0.55 * tfidf_val) + (0.45 * overlap_score) + boost
            final_score = min(max(final_score, 0.0), 1.0)

            if final_score > 0.05 or overlap_score > 0.0:
                scored_passages.append(
                    ScoredPassage(
                        passage=passage,
                        score=final_score,
                        matched_terms=matched
                    )
                )

        scored_passages.sort(key=lambda sp: sp.score, reverse=True)

        # Check evidence sufficiency
        # Threshold: must have a minimum score or at least one matched keyword
        if not scored_passages or scored_passages[0].score < 0.15 or not scored_passages[0].matched_terms:
            return (
                "The document does not contain enough evidence to answer this question.",
                [],
                False
            )

        top_passage = scored_passages[0]

        # Extract answer and supporting quotation
        answer, quote = self._extract_best_answer_and_quote(
            top_passage.passage.text,
            keywords,
            question
        )

        citations = [
            {
                "quote": quote or top_passage.passage.text[:250],
                "page_number": top_passage.passage.page_number,
                "confidence": round(float(min(max(top_passage.score, 0.50), 0.99)), 2)
            }
        ]

        # If a second passage also has high relevance, include as secondary citation
        if len(scored_passages) > 1 and scored_passages[1].score >= 0.40:
            second_passage = scored_passages[1]
            if second_passage.passage.passage_id != top_passage.passage.passage_id:
                citations.append({
                    "quote": second_passage.passage.text[:200],
                    "page_number": second_passage.passage.page_number,
                    "confidence": round(float(min(max(second_passage.score, 0.40), 0.95)), 2)
                })

        return answer, citations, True

    def _extract_best_answer_and_quote(
        self,
        passage_text: str,
        keywords: List[str],
        question: str
    ) -> Tuple[str, str]:
        """
        Finds the most specific sentence or line answering the query and formats a concise response.
        """
        # Split by both sentence terminators and line breaks for structured/key-value lines
        candidates = re.split(r"(?<=[.!?])\s+|\n+", passage_text)
        best_candidate = passage_text
        best_score = -1

        for cand in candidates:
            c_clean = cand.strip()
            if not c_clean:
                continue
            c_lower = c_clean.lower()
            matches = sum(1 for k in keywords if k in c_lower)
            if matches > best_score:
                best_score = matches
                best_candidate = c_clean

        quote = best_candidate.strip()

        # Format natural language answer
        q_lower = question.lower()
        if "who" in q_lower or "name" in q_lower:
            answer = f"Based on the document, {quote}"
        elif "salary" in q_lower or "amount" in q_lower or "total" in q_lower or "cost" in q_lower:
            answer = f"According to the document: {quote}"
        elif "department" in q_lower or "role" in q_lower or "title" in q_lower:
            answer = f"The document indicates: {quote}"
        else:
            answer = f"Based on the document: {quote}"

        return answer, quote
