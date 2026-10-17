# Mock external services

Payments, Shipping, Refunds, and Customer Credit expose FastAPI applications at
`services.<package>.app:app`. They implement POST /effects, GET
/operations/{logical_operation_id}, and GET /health.

Providers retain their own in-memory receipts and committed-effect journals.
Stable keys deduplicate identical requests and reject changed arguments.
The benchmark injects faults through provider construction, not public request
headers. Timeout-before-effect and timeout-after-effect return the same 504 body.

Compose exposes standalone APIs on localhost ports 18001-18004. Benchmark
conditions use fresh in-process HTTP instances to reset truth and inject the
same deterministic schedules. TCP smoke tests independently exercise Compose.

The mocks have no delayed in-flight writes and receipt reads are strongly
consistent. A missing receipt is definitive only under those assumptions.
Provider state is lost on restart. Other service directories are placeholders.
