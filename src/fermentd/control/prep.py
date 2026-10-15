"""The 'Prep' stage ("Making it"): brewing or mixing before fermentation starts.

Every profile gets a first stage with id PREP_STAGE (added when profiles load, so the YAML files and
dashboard-saved profiles need no edits). A batch in Prep does not drive the heater, does not count
toward its zone's target range, and raises no temperature alerts. Batches that were already running
keep the profile snapshot they started with, so they are unaffected.
"""

from __future__ import annotations

from typing import Any

PREP_STAGE = "prep"
PREP_LABEL = "Making it"


def with_prep(profile: Any) -> Any:
    from fermentd.profiles.schema import StageSpec

    if any(stage.id == PREP_STAGE for stage in profile.stages):
        return profile
    stages = [StageSpec(id=PREP_STAGE, core="prep"), *profile.stages]
    return profile.model_copy(update={"stages": stages})


def in_prep(batch: Any) -> bool:
    return batch is not None and batch["stage"] == PREP_STAGE
