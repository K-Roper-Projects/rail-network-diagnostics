def classify_gps_health(diagnosis):
    if diagnosis == "GPS operational":
        return "HEALTHY"

    if diagnosis in [
        "GPS operational with service warning",
        "GPS operational with network warning",
    ]:
        return "DEGRADED"

    return "FAULT"


def classify_wan_health(wan_results):
    active_wans = [
        result
        for result in wan_results
        if result.get("status") != "DISABLED"
    ]

    if not active_wans:
        return "FAULT"

    available_count = sum(
        1
        for result in active_wans
        if result.get("status") == "AVAILABLE"
    )

    if available_count == len(active_wans):
        return "HEALTHY"

    if available_count > 0:
        return "DEGRADED"

    return "FAULT"


def combine_health_states(gps_state, wan_state, online=True):
    if not online:
        return "OFFLINE"

    if gps_state == "FAULT" or wan_state == "FAULT":
        return "FAULT"

    if gps_state == "DEGRADED" or wan_state == "DEGRADED":
        return "DEGRADED"

    return "HEALTHY"
