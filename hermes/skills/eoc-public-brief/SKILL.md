---
name: eoc-public-brief
description: Produce a grounded internal context brief from normalized MBFD EOC public data.
---

# EOC Public Brief

GET `http://127.0.0.1:8220/api/v1/dashboard/summary` and source health. Generate a
concise internal context summary using only normalized fields. Cite every item
with its internal record ID and label authoritative, advisory, supplemental,
stale and unavailable categories explicitly.

Use Qwen with thinking disabled, temperature 0.1, non-streaming strict JSON, one
bounded retry, and one concurrent job. Reject unknown citations or evidence not
present in source records.

Never write back, infer route/facility/power/shelter state, create missing times,
publish public emergency instructions, or make an operational decision.
