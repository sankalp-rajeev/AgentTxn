-- A repeated opaque observation is a new evidence epoch even if the set is unchanged.
ALTER TABLE effect_intents ADD COLUMN IF NOT EXISTS outcome_revision INTEGER NOT NULL DEFAULT -1;
UPDATE effect_intents AS intents
SET outcome_revision = (
    SELECT COUNT(*)::INTEGER - 1 FROM effect_events AS events
    WHERE events.run_id = intents.run_id AND events.effect_id = intents.effect_id
      AND events.event->>'event_type' = 'outcome_observation'
)
WHERE intents.possible_outcomes IS NOT NULL;
