import json
from app.modules.moderation.service import ModerationService


def test_parse_valid_json():
    raw = json.dumps({
        "verdict": "violation",
        "category": "insult",
        "severity": "high",
        "explanation": "توهین مستقیم",
        "confidence": 0.9,
        "suggested_action": "warn",
    })
    s = ModerationService.__new__(ModerationService)
    parsed = s._parse_response(raw)
    assert parsed is not None
    assert parsed.verdict.value == "violation"
    assert parsed.category.value == "insult"


def test_parse_invalid_json_returns_none():
    s = ModerationService.__new__(ModerationService)
    assert s._parse_response("not json at all") is None