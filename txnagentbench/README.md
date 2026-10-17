# TxnAgentBench

Required benchmark artifact; implementation pending.

schema.py owns the scenario contract from PRD section 17. runner.py executes the
same seeded scenarios for each baseline. evaluator.py checks provider truth,
forbidden states, success conditions, and the expected serial outcome.

commerce/ and identity/ are required domains; cloudops/ is optional.
Keep initial scenarios small and deterministic. Generated outputs belong in
artifacts/, with reproducibility metadata recorded in experiments/protocol.md.
