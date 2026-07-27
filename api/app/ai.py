import json
from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


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


class OllamaGroundingError(RuntimeError):
    pass


class OllamaNormalizer:
    def __init__(
        self,
        base_url: str,
        model: str,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.client = client or httpx.AsyncClient()
        self._owns_client = client is None

    async def close(self) -> None:
        if self._owns_client:
            await self.client.aclose()

    async def extract(
        self,
        source_text: str,
        source_record_ids: set[str],
    ) -> GroundedExtraction:
        if not source_text.strip() or not source_record_ids:
            raise OllamaGroundingError("source text and record IDs are required")
        schema = GroundedExtraction.model_json_schema()
        prompt = (
            "Return JSON only, with no markdown or commentary. "
            "The JSON MUST validate against this exact schema and MUST NOT contain "
            f"other keys:\n{json.dumps(schema, separators=(',', ':'))}\n"
            "Extract only facts explicitly present in the public-source text. "
            "Never infer route status, facility status, restoration, occupancy, coordinates, "
            "or missing times. Cite only the provided source record IDs. "
            "Use a verbatim substring of PUBLIC SOURCE TEXT for every supporting_text value. "
            f"Allowed source record IDs: {sorted(source_record_ids)}\n"
            f"PUBLIC SOURCE TEXT:\n{source_text[:24000]}"
        )
        payload = {
            "model": self.model,
            "stream": False,
            "think": False,
            "format": schema,
            "options": {"temperature": 0.1, "num_ctx": 32768},
            "messages": [{"role": "user", "content": prompt}],
        }
        last_error: Exception | None = None
        for _attempt in range(2):
            try:
                response = await self.client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    timeout=240,
                )
                response.raise_for_status()
                content = response.json().get("message", {}).get("content")
                if not isinstance(content, str):
                    raise OllamaGroundingError("Ollama response content is missing")
                result = GroundedExtraction.model_validate(json.loads(content))
                cited = {item.source_record_id for item in result.evidence}
                if not cited <= source_record_ids:
                    raise OllamaGroundingError("AI cited an unknown source record ID")
                if any(item.supporting_text not in source_text for item in result.evidence):
                    raise OllamaGroundingError("AI evidence is not verbatim source support")
                return result
            except (
                httpx.HTTPError,
                json.JSONDecodeError,
                ValidationError,
                OllamaGroundingError,
                TypeError,
            ) as exc:
                last_error = exc
        raise OllamaGroundingError(
            "Ollama output failed grounded schema validation"
        ) from last_error
