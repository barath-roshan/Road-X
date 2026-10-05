"""Unit tests for LocationExtractor."""

from ml.complaint_intelligence.location_extractor import LocationExtractor
from ml.complaint_intelligence.schemas import LocationEntityType


def test_location_extractor_bus_stop():
    extractor = LocationExtractor()
    text = "There is a huge pothole near Gandhipuram bus stand causing traffic delays."
    mentions = extractor.extract_locations(text)
    assert len(mentions) > 0
    match = mentions[0]
    assert match.type == LocationEntityType.BUS_STOP
    assert "Gandhipuram bus stand" in match.text


def test_location_extractor_road_landmark():
    extractor = LocationExtractor()
    text = "Large crater near Coimbatore railway station on Anna Salai road."
    mentions = extractor.extract_locations(text)
    assert len(mentions) >= 1
    texts = [m.text for m in mentions]
    assert any("railway station" in t.lower() for t in texts) or any("salai" in t.lower() or "road" in t.lower() for t in texts)


def test_location_extractor_empty_text():
    extractor = LocationExtractor()
    assert extractor.extract_locations("") == []
    assert extractor.extract_locations("    ") == []


def test_location_extractor_no_locations():
    extractor = LocationExtractor()
    mentions = extractor.extract_locations("The road condition is bad and dangerous.")
    assert isinstance(mentions, list)
