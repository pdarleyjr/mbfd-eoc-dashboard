import json

import httpx
import pytest
import respx
from pydantic import SecretStr

from app.ai import GatewayGroundingError, GatewayNormalizer, load_gateway_credential


def _gateway_json(request: httpx.Request, payload: object) -> httpx.Response:
    return httpx.Response(
        200,
        headers={"X-Request-ID": request.headers["X-Request-ID"]},
        json=payload,
    )


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
    route = respx.post("http://gateway:11440/api/chat").mock(
        side_effect=lambda request: _gateway_json(
            request,
            {"message": {"content": json.dumps(result)}},
        )
    )
    normalizer = GatewayNormalizer(
        "http://gateway:11440",
        "mbfd-eoc-grounding",
        SecretStr("test-gateway-token-abcdefghijklmnopqrstuvwxyz"),
    )

    extracted = await normalizer.extract(source, {"notice-1"})

    assert extracted.evidence[0].source_record_id == "notice-1"
    assert route.calls[0].request.extensions["timeout"]["read"] == 90
    request_payload = json.loads(route.calls[0].request.content)
    assert request_payload["model"] == "mbfd-eoc-grounding"
    assert "keep_alive" not in request_payload
    assert "num_ctx" not in request_payload["options"]
    assert request_payload["options"]["num_predict"] == 600
    assert request_payload["format"]["properties"]["classification"]
    assert '"classification"' in request_payload["messages"][0]["content"]
    assert "MUST NOT contain other keys" in request_payload["messages"][0]["content"]
    assert "exact contiguous substring" in request_payload["messages"][0]["content"]
    assert route.calls[0].request.headers["Authorization"].startswith("Bearer ")
    assert route.calls[0].request.headers["X-MBFD-Capability"] == "mbfd-eoc-grounding"
    assert route.calls[0].request.headers["X-Request-ID"].startswith("eoc-grounding-")
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
    route = respx.post("http://gateway:11440/api/chat").mock(
        side_effect=lambda request: _gateway_json(
            request,
            {"message": {"content": json.dumps(invalid)}},
        )
    )
    normalizer = GatewayNormalizer(
        "http://gateway:11440",
        "mbfd-eoc-grounding",
        SecretStr("test-gateway-token-abcdefghijklmnopqrstuvwxyz"),
    )

    with pytest.raises(GatewayGroundingError):
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
    route = respx.post("http://gateway:11440/api/chat").mock(
        side_effect=lambda request: _gateway_json(
            request,
            {"message": {"content": json.dumps(invalid)}},
        )
    )
    normalizer = GatewayNormalizer(
        "http://gateway:11440",
        "mbfd-eoc-grounding",
        SecretStr("test-gateway-token-abcdefghijklmnopqrstuvwxyz"),
    )

    with pytest.raises(GatewayGroundingError):
        await normalizer.extract("Official source text", {"notice-1"})

    assert route.call_count == 2
    await normalizer.close()


@respx.mock
async def test_qwen_does_not_repeat_a_full_transport_timeout() -> None:
    route = respx.post("http://gateway:11440/api/chat").mock(
        side_effect=httpx.ReadTimeout("model did not respond")
    )
    normalizer = GatewayNormalizer(
        "http://gateway:11440",
        "mbfd-eoc-grounding",
        SecretStr("test-gateway-token-abcdefghijklmnopqrstuvwxyz"),
    )

    with pytest.raises(GatewayGroundingError, match="timed out"):
        await normalizer.extract("Official source text", {"notice-1"})

    assert route.call_count == 1
    await normalizer.close()


async def test_qwen_requires_input() -> None:
    normalizer = GatewayNormalizer(
        "http://gateway:11440",
        "mbfd-eoc-grounding",
        SecretStr("test-gateway-token-abcdefghijklmnopqrstuvwxyz"),
    )
    with pytest.raises(GatewayGroundingError):
        await normalizer.extract("", set())
    await normalizer.close()


@respx.mock
async def test_gateway_credential_is_required_before_network_access() -> None:
    route = respx.post("http://gateway:11440/api/chat").mock(return_value=httpx.Response(500))
    normalizer = GatewayNormalizer(
        "http://gateway:11440",
        "mbfd-eoc-grounding",
        SecretStr(""),
    )

    with pytest.raises(GatewayGroundingError, match="credential is unavailable"):
        await normalizer.extract("Official source text", {"notice-1"})

    assert route.call_count == 0
    await normalizer.close()


@respx.mock
async def test_gateway_readiness_reports_only_logical_capability_state() -> None:
    route = respx.get("http://gateway:11440/health/backends").mock(
        side_effect=lambda request: _gateway_json(
            request,
            {
                "capabilities": {
                    "mbfd-eoc-grounding": {
                        "backend": "private-provider",
                        "model": "physical-model-must-not-leak",
                        "state": "model_cold",
                    }
                }
            },
        )
    )
    normalizer = GatewayNormalizer(
        "http://gateway:11440",
        "mbfd-eoc-grounding",
        SecretStr("test-gateway-token-abcdefghijklmnopqrstuvwxyz"),
    )

    result = await normalizer.readiness()

    assert result == {
        "status": "model_cold",
        "capability": "mbfd-eoc-grounding",
    }
    assert route.calls[0].request.headers["X-MBFD-Capability"] == "mbfd-eoc-grounding"
    assert route.calls[0].request.headers["X-Request-ID"].startswith("eoc-grounding-health-")
    assert "physical-model-must-not-leak" not in str(result)
    await normalizer.close()


def test_gateway_credential_loader_fails_closed(tmp_path) -> None:
    missing = load_gateway_credential(tmp_path / "missing")
    invalid_path = tmp_path / "invalid"
    invalid_path.write_text("not a credential with spaces", encoding="utf-8")
    invalid = load_gateway_credential(invalid_path)

    assert missing.get_secret_value() == ""
    assert invalid.get_secret_value() == ""


@respx.mock
async def test_gateway_response_must_echo_exact_request_id() -> None:
    result = {
        "classification": "not_relevant",
        "locations": [],
        "roads_or_causeways": [],
        "explicitly_stated_start": None,
        "explicitly_stated_expiration": None,
        "evidence": [
            {
                "source_record_id": "notice-1",
                "supporting_text": "Official source text",
            }
        ],
        "confidence": 1.0,
        "missing_fields": [],
        "validation_status": "grounded",
    }
    route = respx.post("http://gateway:11440/api/chat").mock(
        return_value=httpx.Response(
            200,
            headers={"X-Request-ID": "wrong-request-id"},
            json={"message": {"content": json.dumps(result)}},
        )
    )
    normalizer = GatewayNormalizer(
        "http://gateway:11440",
        "mbfd-eoc-grounding",
        SecretStr("test-gateway-token-abcdefghijklmnopqrstuvwxyz"),
    )

    with pytest.raises(GatewayGroundingError, match="schema validation"):
        await normalizer.extract("Official source text", {"notice-1"})

    assert route.call_count == 2
    await normalizer.close()


@respx.mock
async def test_malformed_gateway_readiness_is_controlled() -> None:
    def malformed_response(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"X-Request-ID": request.headers["X-Request-ID"]},
            json=[],
        )

    respx.get("http://gateway:11440/health/backends").mock(side_effect=malformed_response)
    normalizer = GatewayNormalizer(
        "http://gateway:11440",
        "mbfd-eoc-grounding",
        SecretStr("test-gateway-token-abcdefghijklmnopqrstuvwxyz"),
    )

    with pytest.raises(GatewayGroundingError, match="readiness is unavailable"):
        await normalizer.readiness()

    await normalizer.close()
