# Ollama and Qwen

Internal endpoint: `http://host.docker.internal:11434`. Model:
`qwen3.6:35b`. It remains unreachable through the host firewall, Compose port
publishing, Tunnel, and browser application.

`app.ai.OllamaNormalizer` uses temperature `0.1`, thinking disabled, non-streaming
output, one bounded validation retry, and Pydantic-generated strict JSON Schema.
It keeps a successfully loaded model resident for 30 minutes, bounds output to
800 tokens, permits a 180-second cold start, and does not repeat a full transport
timeout. Maximum dashboard AI concurrency is one at the calling job.

Accepted output cites known source record IDs and verbatim supporting text,
reports confidence, missing fields and validation state. Unknown citations,
unsupported evidence, malformed JSON, and schema violations are rejected.
Claimed locations, corridors, and explicit times must also occur in the source
text.

Qwen may structure/classify public notices and diagnose parser drift. It cannot
infer route/facility/power/shelter status, generate missing times/coordinates,
overwrite source records, or make operational decisions.
