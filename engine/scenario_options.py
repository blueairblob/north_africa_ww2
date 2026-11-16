"""Optional, explicitly experimental strategic assumptions for a scenario.

The sea-delivery schedule combines several causes. These options are sensitivity
tests of that schedule, not a reconstruction of a Malta campaign.
"""
from copy import deepcopy

SEA_DELIVERY = (
    ("baseline", "Campaign estimate", 0),
    ("less_interdiction", "Experimental: +15 sea points", 15),
    ("more_interdiction", "Experimental: -15 sea points", -15),
)


def apply(scenario, choice="baseline"):
    selected = next((entry for entry in SEA_DELIVERY if entry[0] == choice), None)
    if selected is None:
        raise ValueError(f"Unknown shipping assumption: {choice}")
    result = deepcopy(scenario)
    if choice != "baseline":
        result["assumption"] = choice
        schedule = result["sides"]["axis"]["sea_pct"]
        result["sides"]["axis"]["sea_pct"] = [
            [day, max(0, min(100, percent + selected[2]))] for day, percent in schedule]
    return result


def label(choice):
    return next(entry[1] for entry in SEA_DELIVERY if entry[0] == choice)
