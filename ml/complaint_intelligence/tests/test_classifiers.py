"""Unit tests for IssueClassifier, UrgencyClassifier, and SafetyRiskClassifier."""

import pytest
from ml.common.exceptions import ModelNotFittedError
from ml.complaint_intelligence.features import ComplaintFeatureExtractor
from ml.complaint_intelligence.classifiers import IssueClassifier, UrgencyClassifier, SafetyRiskClassifier


@pytest.fixture
def trained_pipeline():
    texts = [
        "Huge pothole near railway station dangerous for bikes",
        "Road crack expanding across Anna Salai road",
        "Streetlight not working dark night area",
        "Major accident happened at intersection collision",
        "Waterlogging flooded road submerged traffic",
    ]
    categories = ["POTHOLE", "ROAD_CRACK", "STREETLIGHT", "ACCIDENT", "WATERLOGGING"]
    urgencies = ["HIGH", "MEDIUM", "LOW", "CRITICAL", "HIGH"]
    safeties = ["HIGH", "MEDIUM", "LOW", "HIGH", "HIGH"]

    vec = ComplaintFeatureExtractor(max_features=100)
    X = vec.fit_transform(texts)

    issue_clf = IssueClassifier()
    issue_clf.train(X, categories)

    urgency_clf = UrgencyClassifier()
    urgency_clf.train(X, urgencies)

    safety_clf = SafetyRiskClassifier()
    safety_clf.train(X, safeties)

    return vec, issue_clf, urgency_clf, safety_clf


def test_classifiers_unfitted_raise_error():
    issue_clf = IssueClassifier()
    with pytest.raises(ModelNotFittedError):
        issue_clf.predict(["test"])


def test_classifiers_predict_and_confidence(trained_pipeline):
    vec, issue_clf, urgency_clf, safety_clf = trained_pipeline

    sample_X = vec.transform(["Huge pothole near railway station dangerous for bikes"])

    issue_preds = issue_clf.predict_with_confidence(sample_X)
    assert len(issue_preds) == 1
    label, conf = issue_preds[0]
    assert isinstance(label, str)
    assert 0.0 <= conf <= 1.0

    urgency_preds = urgency_clf.predict_with_confidence(sample_X)
    assert len(urgency_preds) == 1
    u_label, u_conf = urgency_preds[0]
    assert 0.0 <= u_conf <= 1.0

    safety_preds = safety_clf.predict_with_confidence(sample_X)
    assert len(safety_preds) == 1
    s_label, s_conf = safety_preds[0]
    assert 0.0 <= s_conf <= 1.0


def test_classifier_save_load_roundtrip(trained_pipeline, tmp_path):
    vec, issue_clf, _, _ = trained_pipeline
    save_path = tmp_path / "issue_model.joblib"

    issue_clf.save(save_path)
    loaded_clf = IssueClassifier.load(save_path)

    assert loaded_clf.is_fitted
    assert loaded_clf.model_name == "IssueClassifier"

    sample_X = vec.transform(["Pothole road"])
    orig_pred = issue_clf.predict(sample_X)
    loaded_pred = loaded_clf.predict(sample_X)
    assert orig_pred == loaded_pred
