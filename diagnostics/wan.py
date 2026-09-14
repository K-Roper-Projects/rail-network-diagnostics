
def parse_wan_loadbalance(loadbalance_text):

    data = {}

    for line in loadbalance_text.splitlines():

        if "=" not in line:
            continue

        key, value = line.split("=", 1)

        data[key.strip()] = value.strip()

    return {
        "interface": data.get("interface", ""),
        "ca": data.get("ca", "0"),
        "rtt": data.get("rtt", ""),
        "bandwidth": data.get("bw", ""),
        "rank": data.get("rank", ""),
    }
    
def classify_wan_status(wan_data):

    if wan_data["ca"] == "1":
        return "AVAILABLE"

    return "UNAVAILABLE"
    
def get_wan_recommendation(wan_number, status, results):
    prefix = f"wan{wan_number}"

    state = results.get(f"{prefix}_state", "").strip()
    attach_state = results.get(f"{prefix}_attach_state", "").strip()
    registration = results.get(f"{prefix}_registration_status", "").strip()
    modem_details = results.get(f"{prefix}_modem_details", "").strip()
    interface = results.get(f"{prefix}_ifname", "").strip()
    device = results.get(f"{prefix}_dev", "").strip()
    ca_state = results.get(f"{prefix}_ca", "").strip()

    wan_data = parse_wan_loadbalance(
        results.get(f"{prefix}_loadbalance", "")
    )

    loadbalance_interface = wan_data.get("interface", "")
    loadbalance_ca = wan_data.get("ca", "0")
    loadbalance_rtt = wan_data.get("rtt", "")

    try:
        latency_ms = int(float(loadbalance_rtt or 0))
    except ValueError:
        latency_ms = 0

    # 60000ms is a failure value, even if interface/CA data briefly looks valid.
    if latency_ms >= 60000:
        return (
            "WAN attached but failing latency check",
            "Reset WAN process and monitor. If high latency returns, raise FSE ticket for modem investigation or replacement."
        )

    # Trust operational loadbalance evidence before missing modem metadata.
    if (
        (interface or loadbalance_interface)
        and (str(ca_state) == "1" or str(loadbalance_ca) == "1")
    ):
        return (
            "WAN operational",
            "No action required."
        )

    if status == "AVAILABLE":
        return (
            "WAN operational",
            "No action required."
        )

    if (
        "PDP" in state.upper()
        or "PDP" in attach_state.upper()
        or "PDP" in registration.upper()
    ):
        return (
            "PDP context/session error",
            "Reset WAN process and monitor. If PDP error reoccurs, investigate SIM/APN/session setup and escalate if persistent."
        )

    if (
        "NO PLMN" in state.upper()
        or "NO PLMN" in attach_state.upper()
        or "NO PLMN" in registration.upper()
    ):
        return (
            "Network registration failure - NO PLMN",
            "Reset WAN process and monitor. If NO PLMN reoccurs after WAN process restart or train reboot, raise FSE ticket for modem or SIM investigation."
        )

    if (
        "POWER ON" in state.upper()
        or "POWER ON" in attach_state.upper()
    ):
        return (
            "Modem stuck during power-on initialisation",
            "Reset WAN process or reboot CCU. If the state returns, raise FSE ticket for modem investigation or replacement."
        )

    if (
        state == "INIT"
        and "ATTEMPTING NETWORK ATTACH" in attach_state.upper()
        and "REGISTERED" in registration.upper()
    ):
        return (
            "WAN INIT - attach/interface bring-up failure",
            "Reset WAN process and monitor. If the fault reoccurs after WAN process restart or train reboot, raise FSE ticket for modem replacement."
        )
    if (
        "NO LEASE" in state.upper()
        or "NO LEASE" in attach_state.upper()
        or "NO LEASE" in registration.upper()
    ):
        return (
            "WAN DHCP lease acquisition failure",
            "Reset WAN process and monitor. If fault develops into dhcp_cal or reoccurs, investigate Sierra Wireless modem session handling and consider modem replacement."
        )
    
    if state in ["WAIT#DHCP", "STATE_WAIT_DHCP"]:
        return (
            "WAN DHCP negotiation failure",
            "Reset WAN process and monitor. If DHCP failure reoccurs, investigate modem DHCP/session handling and consider modem replacement."
        )

    if state in ["SHOW-LTE", "SHOWTIME"] and attach_state == "-------":
        return (
            "LTE session establishment incomplete",
            "Reset WAN process and monitor. If fault persists, investigate modem registration and data session establishment."
        )

    if (
        not modem_details
        and not interface
        and not device
        and not loadbalance_interface
        and str(ca_state) != "1"
        and str(loadbalance_ca) != "1"
    ):
        return (
            "Modem not detected",
            "Reboot CCU and recheck modem detection. If still not detected, raise FSE ticket for modem replacement."
        )

    if interface == "" and device == "" and loadbalance_interface == "":
        return (
            "WAN unavailable - no active interface",
            "Reset WAN process and monitor. If interface remains unavailable, raise to 2nd Line or FSE for modem investigation."
        )

    return (
        "WAN unavailable - cause not yet classified",
        "Review modem state, registration status, attach state, and interface data. Escalate if fault persists."
    )
    
def get_wan_result(wan_number, results, train_profile):
    wan_id = f"{wan_number:02d}"
    prefix = f"wan{wan_number}"

    if wan_id not in train_profile.get("active_wans", []):
        return {
            "status": "DISABLED",
            "diagnosis": "WAN disabled by fleet design",
            "next_steps": "No action required.",
        }

    wan_data = parse_wan_loadbalance(
        results.get(f"{prefix}_loadbalance", "")
    )

    status = classify_wan_status(wan_data)

    diagnosis, next_steps = get_wan_recommendation(
        wan_number,
        status,
        results,
    )

    if diagnosis == "WAN operational":
        status = "AVAILABLE"

    return {
        "status": status,
        "diagnosis": diagnosis,
        "next_steps": next_steps,
    }