"""Unit tests for ComplaintEmbedder."""

import numpy as np
from ml.complaint_intelligence.embedder import ComplaintEmbedder
from ml.complaint_intelligence.features import ComplaintFeatureExtractor


def test_embedder_output_shape_and_dtype():
    embedder = ComplaintEmbedder(embedding_dim=300)
    vec = embedder.embed("There is a pothole near bus stand")

    assert isinstance(vec, np.ndarray)
    assert vec.shape == (300,)
    assert vec.dtype == np.float32


def test_embedder_empty_text():
    embedder = ComplaintEmbedder(embedding_dim=300)
    vec = embedder.embed("")

    assert isinstance(vec, np.ndarray)
    assert vec.shape == (300,)
    assert np.all(vec == 0.0)


def test_embedder_fitted_feature_extractor():
    texts = ["pothole near railway station", "flooding on Anna Salai"]
    vec_extractor = ComplaintFeatureExtractor(max_features=50)
    vec_extractor.fit_transform(texts)

    embedder = ComplaintEmbedder(feature_extractor=vec_extractor, embedding_dim=300)
    vec = embedder.embed("pothole near railway station")

    assert isinstance(vec, np.ndarray)
    assert vec.shape == (300,)
    assert np.linalg.norm(vec) > 0.0
