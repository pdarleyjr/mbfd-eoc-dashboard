import json

import httpx
import pytest
import respx

from app.ai import OllamaGroundingError, OllamaNormalizer


@respx.mock
async def test_qwen_output_requires_grounded_source_evidence() -> None:
    source = "Miami Beach notice: Venetian Causeway work begins July 29."
    result = {
        "classification": "traffic_notice",
        "locations": ["Miami Beach"],
        "roads_or_causeways": ["Venetian Causeway"],
        "explicitly_stated_start": "July 29",
        "explicitly_stated_expiration": None,
        "evidence": [
            {
                "source_record_id": "notice-1",
                "supporting_text": "Venetian Causeway work begins July 29.",
            }
        ],
        "confidence": 0.95,
        "missing_fields": ["expiration"],
        "validation_status": "grounded",
    }
    route = respx.post("http://ollama:11434/api/chat").mock(
        return_value=httpx.Response(
            200,
            json={"message": {"content": json.dumps(result)}},
        )
    )
    normalizer = OllamaNormalizer("http://ollama:11434", "qwen3.6:35b")

    extracted = await normalizer.extract(source, {"notice-1"})

    assert extracted.evidence[0].source_record_id == "notice-1"
    assert route.calls[0].request.extensions["timeout"]["read"] == 180
    request_payload = json.loads(route.calls[0].request.content)
    assert request_payload["keep_alive"] == "30m"
    assert request_payload["options"]["num_predict"] == 800
    assert request_payload["format"]["properties"]["classification"]
    assert '"classification"' in request_payload["messages"][0]["content"]
    assert "MUST NOT contain other keys" in request_payload["messages"][0]["content"]
    await normalizer.close()


@respx.mock
async def test_qwen_rejects_invented_citations_and_retries_once() -> None:
    invalid = {
        "classification": "traffic_notice",
        "locations": [],
        "roads_or_causeways": [],
        "explicitly_stated_start": None,
        "explicitly_stated_expiration": None,
        "evidence": [{"source_record_id": "invented", "supporting_text": "invented"}],
        "confidence": 1,
        "missing_fields": [],
        "validation_status": "grounded",
    }
    route = respx.post("http://ollama:11434/api/chat").mock(
        return_value=httpx.Response(
            200,
            json={"message": {"content": json.dumps(invalid)}},
        )
    )
    normalizer = OllamaNormalizer("http://ollama:11434", "qwen3.6:35b")

    with pytest.raises(OllamaGroundingError):
        await normalizer.extract("Official source text", {"notice-1"})

    assert route.call_count == 2
    await normalizer.close()


@respx.mock
async def test_qwen_rejects_entities_not_present_in_source() -> None:
    invalid = {
        "classification": "traffic_notice",
        "locations": ["Invented Location"],
        "roads_or_causeways": [],
        "explicitly_stated_start": None,
        "explicitly_stated_expiration": None,
        "evidence": [
            {
                "source_record_id": "notice-1",
                "supporting_text": "Official source text",
            }
        ],
        "confidence": 0.4,
        "missing_fields": [],
        "validation_status": "grounded",
    }
    route = respx.post("http://ollama:11434/api/chat").mock(
        return_value=httpx.Response(
            200,
            json={"message": {"content": json.dumps(invalid)}},
        )
    )
    normalizer = OllamaNormalizer("http://ollama:11434", "qwen3.6:35b")

    with pytest.raises(OllamaGroundingError):
        await normalizer.extract("Official source text", {"notice-1"})

    assert route.call_count == 2
    await normalizer.close()


@respx.mock
async def test_qwen_does_not_repeat_a_full_transport_timeout() -> None:
    route = respx.post("http://ollama:11434/api/chat").mock(
        side_effect=httpx.ReadTimeout("model did not respond")
    )
    normalizer = OllamaNormalizer("http://ollama:11434", "qwen3.6:35b")

    with pytest.raises(OllamaGroundingError, match="timed out"):
        await normalizer.extract("Official source text", {"notice-1"})

    assert route.call_count == 1
    await normalizer.close()


async def test_qwen_requires_input() -> None:
    normalizer = OllamaNormalizer("http://ollama:11434", "qwen3.6:35b")
    with pytest.raises(OllamaGroundingError):
        await normalizer.extract("", set())
    await normalizer.close()
