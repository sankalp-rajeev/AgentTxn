# Related-work register

Targeted check: 16 October 2026. This is a scoped search, not a systematic review.
Searches covered semantic concurrency for LLM agents, cross-service invariants,
in-doubt external actions, and the named prior systems in the PRD.

## Primary sources reviewed

- [Atomix, v2, 29 May 2026](https://arxiv.org/html/2602.14849): groups tool effects
  and gates settlement with resource frontiers. Semantic validation is explicitly
  outside its contribution, but it provides a pre-commit hook; Appendix D.1
  demonstrates rejecting invalid attempts with that hook. Comparing only against
  an unaugmented resource baseline cannot establish novelty over Atomix.
- [CoAgent, v1, 13 June 2026](https://arxiv.org/html/2606.15376): fixed launch-order
  serialization, advisory invalidation, agent repair, and registered tool inverses.
  Relevant to concurrency and recovery; its reviewed model does not establish
  AgentTxn's proposed combination of cross-provider budget reservations and
  unresolved external-effect tracking.
- [Cordon, v1, 16 June 2026](https://arxiv.org/html/2606.17573): task-scoped semantic
  transactions, result lineage, shadow state, and an external-effect outbox.
  Cross-step validation and irreversible-effect gating are already prior art;
  the reviewed account does not establish concurrent cross-transaction budgets.
- [State Consistency / SVBE, posted 16 September 2026](https://ssrn.com/abstract=7472480):
  effect-time deterministic validation compared against locking, OCC, CAS, and
  PostgreSQL SERIALIZABLE across application workloads. This directly overlaps
  the generic claim that semantic checks preserve valid reasoning under state
  changes. Review was limited to the accessible primary abstract; full-text
  cross-provider and ambiguous-effect coverage remains unverified.
- [Where Does Exactly-Once Live?, v1, 24 September 2026](https://arxiv.org/html/2609.29095):
  Limbo models heterogeneous services, late commits, duplicate delivery, partial
  batches, and capability-dependent recovery. Unknown outcomes, fault injection,
  and provider-contract limits are not new individually. Its reviewed focus is
  duplicate-effect recovery, rather than online cross-agent invariant admission.
- [Authority at Commit Time, v1, 25 September 2026](https://arxiv.org/html/2609.31490):
  combines OCC, semantic verification, idempotent outbox admission, and receipt
  reconciliation behind a logical authority. This overlaps deterministic commit
  decisions and declared dependencies; its evaluated claims are explicitly bounded.
- [Agentic Transaction, August 2026](https://arxiv.org/html/2608.13900) and
  [AgentMercury, August 2026](https://arxiv.org/html/2608.20634) were screened as
  adjacent semantic-transaction and cross-service environment work. They warrant
  deeper review before any publication-level novelty claim.

Statements about what a source does not establish are scoped reading inferences,
not proofs of absence. No paper implementation is reproduced by these baselines.
The search found component overlap, but no verified single source demonstrating
the full PRD nine-part combination.

## Consequences for the spike

Add a resource-OCC control with a shared incident-budget key. If it prevents the
same conflict, report the metadata distinction honestly. Do not claim semantic
certification is inherently more expressive than resource coordination with a
correctly declared semantic footprint. Compare evidence-based admission under
ambiguity, task completion, and useful concurrency separately from novel claims.
