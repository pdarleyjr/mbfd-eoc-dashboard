# Ollama and Qwen

Production uses a dedicated host service at `http://172.20.0.1:11437` and model
`qwen3.5:9b`. The unit is tracked in `deploy/ollama-eoc.service`; it binds only
to the external `mbfd-ai` Docker bridge and the host firewall permits only
`172.20.0.0/24` to that port. It remains unreachable through Compose port
publishing, Cloudflare Tunnel, and the browser application.

Do not point EOC back at the shared port `11434`. That service also handles a
65K-context coding workload. Live testing showed it evicting the EOC runner and
spending about 121 seconds reloading the 35B model. The isolated 9B service
avoids that queue and runner churn while staying within the same local trust
boundary.

`app.ai.OllamaNormalizer` uses temperature `0.1`, thinking disabled, non-streaming
output, one bounded validation retry, and Pydantic-generated strict JSON Schema.
It keeps a successfully loaded model resident for 30 minutes, uses an 8K context,
bounds output to 600 tokens, permits a 90-second cold start, and does not repeat
a full transport timeout. Maximum dashboard AI concurrency is one at the
calling job.

Accepted output cites known source record IDs and verbatim supporting text,
reports confidence, missing fields and validation state. Unknown citations,
unsupported evidence, malformed JSON, and schema violations are rejected.
Claimed locations, corridors, and explicit times must also occur in the source
text.

Qwen may structure/classify public notices and diagnose parser drift. It cannot
infer route/facility/power/shelter status, generate missing times/coordinates,
overwrite source records, or make operational decisions.
