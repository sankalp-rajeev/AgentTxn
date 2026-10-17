# Mock external services

Provider simulations own external truth independently of runtime observations.
Start with Payments and Shipping for the feasibility spike. Refunds and customer
credit support the required disjoint-resource compensation-budget example.

Service app.py modules are placeholders, not running FastAPI applications.
Add explicit contracts, reconciliation probes, fault hooks, and health checks
when implementing each provider. Compose currently starts only PostgreSQL.

Identity, Documents, Email, Ticketing, Approvals, and Audit cover the second
domain. CloudOps is optional. Keep fault schedules seeded and replayable.
