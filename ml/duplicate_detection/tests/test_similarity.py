"""Unit tests for SimilarityCalculator and Phase 5 embedding integration."""

import numpy as np
from ml.duplicate_detection.similarity import SimilarityCalculator
from ml.complaint_intelligence.embedder import ComplaintEmbedder


def test_exact_duplicate_similarity():
    calc = SimilarityCalculator()
    text = "There is a large pothole near the railway station."
    sim = calc.calculate_similarity(text, text)
    assert round(sim, 4) == 1.0000


def test_semantically_similar_text():
    calc = SimilarityCalculator()
    t1 = "There is a large pothole near the bus stop."
    t2 = "A big pothole is causing problems near the bus stand."
    sim = calc.calculate_similarity(t1, t2)
    assert sim > 0.40  # Semantically similar text via Phase 5 TF-IDF embeddings


def test_empty_text_similarity():
    calc = SimilarityCalculator()
    assert calc.calculate_similarity("", "Pothole road") == 0.0
    assert calc.calculate_similarity("Pothole road", "   ") == 0.0


def test_phase5_embedding_dimension_integration():
    embedder = ComplaintEmbedder()
    vec = embedder.embed("Pothole on Anna Salai road")
    assert isinstance(vec, np.ndarray)
    assert vec.shape == (300,)  # Phase 5 actual embedding dimension
    assert vec.dtype == np.float32
