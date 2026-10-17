# Domain configurations

These YAML files reserve domain configuration locations; they are not runnable
benchmark scenarios. Implement and validate txnagentbench/schema.py before
expanding them. Every scenario must declare the PRD section 17 fields:
scenario_id, domain, initial_state, agents, workflows, tool_contracts,
semantic_invariants, fault_schedule, success_conditions, forbidden_states,
and expected_serial_outcome.
