# Testing plan

No behavioral tests are included for this directory-only scaffold.

- unit/: certainty transitions, contract validation, graph edges, invariant decisions.
- integration/: intent -> certification -> faulted tool -> observation -> wakeup.
- property/: unknown prerequisites block irreversible effects; hard invariants hold;
  safe retries do not duplicate effects; independent work does not block; compensation
  releases active capacity.
- regression/: permanent cases for every discovered correctness bug.

Use pytest and Hypothesis. Bound generated examples for CI. Add deterministic
benchmark smoke coverage with the first runnable scenario. CI runs pytest when
test_*.py files exist; an empty test tree is not evidence of runtime correctness.
