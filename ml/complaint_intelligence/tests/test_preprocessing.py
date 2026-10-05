"""Unit tests for ComplaintPreprocessor."""

import pytest
from ml.common.exceptions import RoadXDataError
from ml.complaint_intelligence.preprocessing import ComplaintPreprocessor


def test_preprocessor_valid_text():
    preprocessor = ComplaintPreprocessor()
    raw = "  Pothole near  Anna   Salai   road!  "
    cleaned = preprocessor.clean_text(raw)
    assert cleaned == "Pothole near Anna Salai road!"


def test_preprocessor_unicode_normalization():
    preprocessor = ComplaintPreprocessor()
    unicode_text = "Pothole near\u00A0Anna Salai\u200B road"
    cleaned = preprocessor.clean_text(unicode_text)
    assert "Anna Salai" in cleaned


def test_preprocessor_empty_text_raises_error():
    preprocessor = ComplaintPreprocessor()
    with pytest.raises(RoadXDataError):
        preprocessor.clean_text("")

    with pytest.raises(RoadXDataError):
        preprocessor.clean_text("   \n\t  ")

    with pytest.raises(RoadXDataError):
        preprocessor.clean_text(None)


def test_preprocessor_structured_output():
    preprocessor = ComplaintPreprocessor()
    raw = "Huge pothole on MG Road junction"
    result = preprocessor.preprocess(raw)
    assert result["raw_text"] == raw
    assert result["cleaned_text"] == "Huge pothole on MG Road junction"
    assert result["lowercase_text"] == "huge pothole on mg road junction"
    assert result["word_count"] == 6
    assert result["char_count"] > 0
