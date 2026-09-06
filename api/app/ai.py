import json
import re
import uuid
from pathlib import Path
from typing import Literal

import httpx
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    ValidationError,
    model_validator,
)


class EvidenceReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_record_id: str = Field(min_length=1, max_length=500)
    supporting_text: str = Field(min_length=1, max_length=2000)


class GroundedExtraction(BaseModel):
    """Strict envelope for non-authoritative AI-assisted text extraction."""

    model_config = ConfigDict(extra="forbid")

    classification: Literal[
        "emergency_notice",
        "traffic_notice",
        "utility_notice",
        "facility_notice",
        "transit_notice",
        "not_relevant",
    ]
    locations: list[str] = Field(max_length=20)
    roads_or_causeways: list[str] = Field(max_length=20)
    explicitly_stated_start: str | None = None
    explicitly_stated_expiration: str | None = None
    evidence: list[EvidenceReference] = Field(min_length=1, max_length=20)
    confidence: float = Field(ge=0, le=1)
    missing_fields: list[str] = Field(max_length=30)
    validation_status: Literal["grounded", "insufficient_evidence"]

    @model_validator(mode="after")
    def insufficient_evidence_cannot_be_high_confidence(self) -> "GroundedExtraction":
        if self.validation_status == "insufficient_evidence" and self.confidence > 0.5:
            raise ValueError("insufficient evidence cannot have confidence above 0.5")
        return self


class GatewayGroundingError(RuntimeError):
    pass


def _require_request_id_echo(response: httpx.Response, request_id: str) -> None:
    if response.headers.get("X-Request-ID") != request_id:
        raise GatewayGroundingError("gateway request ID echo is missing or mismatched")


def load_gateway_credential(path: Path) -> SecretStr:
    try:
        token = path.read_text(encoding="utf-8").strip()
    except OSError:
        return SecretStr("")
    if not re.fullmatch(r"[A-Za-z0-9_-]{32,256}", token):
        return SecretStr("")
    return SecretStr(token)


class GatewayNormalizer:
    request_timeout_seconds = 90
    source_text_limit = 12000

    def __init__(
        self,
        base_url: str,
        capability: str,
        credential: SecretStr,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if capability != "mbfd-eoc-grounding":
            raise ValueError("unsupported EOC grounding capability")
        self.base_url = base_url.rstrip("/")
        self.capability = capability
        self.credential = credential
        self.client = client or httpx.AsyncClient()
        self._owns_client = client is None

    async def close(self) -> None:
        if self._owns_client:
            await self.client.aclose()

    def _request_headers(self, request_id: str) -> dict[str, str]:
        token = self.credential.get_secret_value()
        if not re.fullmatch(r"[A-Za-z0-9_-]{32,256}", token):
            raise GatewayGroundingError("gateway credential is unavailable")
        return {
            "Authorization": f"Bearer {token}",
            "X-MBFD-Capability": self.capability,
            "X-Request-ID": request_id,
        }

    async def readiness(self) -> dict[str, str]:
        request_id = f"eoc-grounding-health-{uuid.uuid4()}"
        try:
            response = await self.client.get(
                f"{self.base_url}/health/backends",
                headers=self._request_headers(request_id),
                timeout=httpx.Timeout(5, connect=3),
            )
            response.raise_for_status()
            _require_request_id_echo(response, request_id)
            capability = response.json().get("capabilities", {}).get(self.capability)
            if not isinstance(capability, dict):
                raise GatewayGroundingError("grounding capability is not registered")
            state = capability.get("state")
            if not isinstance(state, str) or not state:
                raise GatewayGroundingError("grounding readiness state is unavailable")
            return {"status": state, "capability": self.capability}
        except (
            httpx.HTTPError,
            AttributeError,
            GatewayGroundingError,
            TypeError,
            ValueError,
        ) as exc:
            raise GatewayGroundingError("gateway readiness is unavailable") from exc

    async def extract(
        self,
        source_text: str,
        source_record_ids: set[str],
    ) -> GroundedExtraction:
        if not source_text.strip() or not source_record_ids:
            raise GatewayGroundingError("source text and record IDs are required")
        request_id = f"eoc-grounding-{uuid.uuid4()}"
        headers = self._request_headers(request_id)
        schema = GroundedExtraction.model_json_schema()
        prompt = (
            "Return JSON only, with no markdown or commentary. "
            "The JSON MUST validate against this exact schema and MUST NOT contain "
            f"other keys:\n{json.dumps(schema, separators=(',', ':'))}\n"
            "Extract only facts explicitly present in the public-source text. "
            "Never infer route status, facility status, restoration, occupancy, coordinates, "
            "or missing times. Cite only the provided source record IDs. "
            "Use a verbatim substring of PUBLIC SOURCE TEXT for every supporting_text value. "
            "Every locations, roads_or_causeways, explicitly_stated_start, and "
            "explicitly_stated_expiration value must itself be an exact contiguous substring "
            "of PUBLIC SOURCE TEXT; use an empty list or null instead of paraphrasing. "
            f"Allowed source record IDs: {sorted(source_record_ids)}\n"
            f"PUBLIC SOURCE TEXT:\n{source_text[: self.source_text_limit]}"
        )
        payload = {
            "model": self.capability,
            "stream": False,
            "think": False,
            "format": schema,
            "options": {
                "temperature": 0.1,
                "num_predict": 600,
            },
            "messages": [{"role": "user", "content": prompt}],
        }
        last_error: Exception | None = None
        for _attempt in range(2):
            try:
                response = await self.client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    headers=headers,
                    timeout=httpx.Timeout(self.request_timeout_seconds, connect=5),
                )
                response.raise_for_status()
                _require_request_id_echo(response, request_id)
                content = response.json().get("message", {}).get("content")
                if not isinstance(content, str):
                    raise GatewayGroundingError("gateway response content is missing")
                result = GroundedExtraction.model_validate(json.loads(content))
                cited = {item.source_record_id for item in result.evidence}
                if not cited <= source_record_ids:
                    raise GatewayGroundingError("AI cited an unknown source record ID")
                if any(item.supporting_text not in source_text for item in result.evidence):
                    raise GatewayGroundingError("AI evidence is not verbatim source support")
                source_lower = source_text.lower()
                claimed_values = [
                    *result.locations,
                    *result.roads_or_causeways,
                    *([result.explicitly_stated_start] if result.explicitly_stated_start else []),
                    *(
                        [result.explicitly_stated_expiration]
                        if result.explicitly_stated_expiration
                        else []
                    ),
                ]
                if any(value.lower() not in source_lower for value in claimed_values):
                    raise GatewayGroundingError(
                        "AI returned a location, corridor, or time absent from source text"
                    )
                return result
            except httpx.TimeoutException as exc:
                # A second full model timeout can extend a scrape-audit job by
                # several minutes without improving correctness.
                raise GatewayGroundingError("gateway request timed out") from exc
            except (
                httpx.HTTPError,
                AttributeError,
                json.JSONDecodeError,
                ValidationError,
                GatewayGroundingError,
                TypeError,
            ) as exc:
                last_error = exc
        raise GatewayGroundingError(
            "gateway output failed grounded schema validation"
        ) from last_error
