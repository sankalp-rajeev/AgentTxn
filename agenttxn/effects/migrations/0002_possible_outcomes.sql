-- Keep epistemic certainty separate from the provider-world possibility set.
ALTER TABLE effect_intents ADD COLUMN IF NOT EXISTS possible_outcomes JSONB;
