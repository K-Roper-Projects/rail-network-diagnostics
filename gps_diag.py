from pathlib import Path
from getpass import getpass
import re
import csv
import socket
from datetime import datetime
import paramiko

SSH_PORT = 2510
SSH_USERNAME = "root"
SSH_KEY_PATH = r"C:\SSH\kevin-roper"

FLEET_PROFILES = {
    "gwr_165_166": {
        "gps_device_mode": "fixed",
        "gps_device": "/dev/ttyS1",
        "active_wans": ["01", "03"],
        "vlan": "br0.105",
        "gprmc_file": "/var/local/gprmc",
        "broadcast_process": "broadcast_unicast_gps.py",
    },
    "gwr_800_802": {
        "gps_device_mode": "auto",
        "active_wans": ["01", "02"],        
        "vlan": "br0.105",
        "gprmc_file": "/var/local/gprmc",
        "broadcast_process": "broadcast_unicast_gps.py",
    },
    "xc_220_221": {
        "gps_device_mode": "auto",
        "active_wans": ["01", "02", "03"],
        "vlan": "br0.105",
        "gprmc_file": "/var/local/gprmc",
        "broadcast_process": "broadcast_unicast_gps.py",
    },
    "xc_170": {
        "gps_device_mode": "auto",
        "active_wans": ["01", "02", "03"],
        "vlan": "br0.105",
        "gprmc_file": "/var/local/gprmc",
        "broadcast_process": "broadcast_unicast_gps.py",
    },
}

def parse_gprmc(line):
    line = line.strip()

    if not line.startswith("$GPRMC"):
        return {
            "valid_sentence": False,
            "utc_time": None,
            "status": "UNKNOWN",
            "healthy": False,
            "reason": "Not a valid GPRMC sentence",
        }

    parts = line.split(",")

    if len(parts) < 3:
        return {
            "valid_sentence": False,
            "utc_time": None,
            "status": "UNKNOWN",
            "healthy": False,
            "reason": "Incomplete GPRMC sentence",
        }

    utc_time = parts[1]
    status = parts[2]

    if status == "A":
        reason = "Valid active GPS fix"
        healthy = True
    elif status == "V":
        reason = "Invalid GPS fix"
        healthy = False
    else:
        reason = "Unknown GPS fix status"
        healthy = False

    return {
        "valid_sentence": True,
        "utc_time": utc_time if utc_time else "Missing",
        "status": status,
        "healthy": healthy,
        "reason": reason,
    }


def parse_satellites(nmea_text):
    match = re.search(r"\$GPGSV,\d+,\d+,(\d+)", nmea_text)

    if not match:
        return None

    return int(match.group(1))

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

    if status == "AVAILABLE":
        return (
            "WAN operational",
            "No action required."
        )
    rtt = results.get(f"{prefix}_loadbalance", "")

    wan_data = parse_wan_loadbalance(
    results.get(f"{prefix}_loadbalance", "")
    )

    try:
        latency_ms = int(float(wan_data.get("rtt", "0")))
    except ValueError:
        latency_ms = 0

    if state in ["SHOW-LTE", "SHOWTIME"] and latency_ms >= 60000:
        return (
            "WAN attached but failing latency check",
            "Reset WAN process and monitor. If high latency returns, raise FSE ticket for modem investigation or replacement."
        )
    
    if (
        state == "INIT"
        and "Attempting network attach" in attach_state
        and "Registered" in registration
        and ca_state == "0"
    ):
        return (
            "WAN INIT - attach/interface bring-up failure",
            "Reset WAN process and monitor. If the fault reoccurs after WAN process restart or train reboot, raise FSE ticket for modem replacement."
        )

    if "NO PLMN" in state or "NO PLMN" in registration:
        return (
            "Network registration failure",
            "Reset WAN process and monitor. If the fault reoccurs after WAN process restart or train reboot, raise FSE ticket for modem replacement."
        )

    if not modem_details or "0000:0000" in modem_details:
        return (
            "Modem not detected",
            "Reboot CCU and recheck modem detection. If still not detected, raise FSE ticket for modem replacement."
        )

    if state in ["WAIT#DHCP", "STATE_WAIT_DHCP"]:
        return (
            "WAN DHCP negotiation failure",
            "Reset WAN process and monitor. If DHCP failure reoccurs, investigate modem DHCP/session handling and consider modem replacement."
        )

    if state in ["Power On", "POWER ON"]:
        return (
            "Modem stuck during power-on initialisation",
            "Reset WAN process or reboot CCU. If the state returns, raise FSE ticket for modem investigation or replacement."
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

    if interface == "" and device == "" and ca_state == "0":
        return (
            "WAN unavailable - no active interface",
            "Reset WAN process and monitor. If interface remains unavailable, raise to 2nd Line or FSE for modem investigation."
        )
    
    if state in ["SHOW-LTE", "SHOWTIME"] and attach_state == "Power On":
        return (
            "WAN session not fully established after reset",
            "Monitor for recovery. If the WAN remains in Power On state or reoccurs after WAN process reset, escalate for modem investigation."
        )

    if state == "SHOW-LTE" and attach_state == "-------":
        return (
            "LTE registration incomplete",
            "Reset WAN process and monitor. If fault persists, investigate modem registration and data session establishment."
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

    return {
        "status": status,
        "diagnosis": diagnosis,
        "next_steps": next_steps,
    }

def run_ssh_command(host, port, username, key_file, passphrase, command):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(
            hostname=host,
            port=port,
            username=username,
            key_filename=key_file,
            passphrase=passphrase,
            timeout=25,
            look_for_keys=False,
            allow_agent=False,
        )

        stdin, stdout, stderr = client.exec_command(command, timeout=30)

        output = stdout.read().decode(errors="ignore").strip()
        error = stderr.read().decode(errors="ignore").strip()

        return output if output else error

    except (socket.timeout, TimeoutError, paramiko.ssh_exception.NoValidConnectionsError):
        return "CONNECTION_TIMEOUT"

    except Exception as e:
        return f"SSH_ERROR: {e}"

    finally:
        client.close()
        
def contains_nmea(text):
    return any(
        sentence in text
        for sentence in [
            "$GPRMC",
            "$GPGGA",
            "$GPGSV",
            "$GNGSA",
            "$GLGSV",
        ]
    )


def detect_gps_device(host, username, key_file, passphrase, profile):

    if profile.get("gps_device_mode") == "fixed":
        fixed_device = profile["gps_device"]

        nmea_output = run_ssh_command(
            host,
            SSH_PORT,
            username,
            key_file,
            passphrase,
            f"timeout 5 cat {fixed_device}",
        )

        return fixed_device, nmea_output

    gps_pid_command = (
        "ps aux | grep '/usr/local/bin/gps' | grep -v grep | awk '{print $2}'"
    )

    gps_pid = run_ssh_command(
        host,
        SSH_PORT,
        username,
        key_file,
        passphrase,
        gps_pid_command,
    ).strip()

    if gps_pid and not gps_pid.startswith("SSH_ERROR"):

        fd_output = run_ssh_command(
            host,
            SSH_PORT,
            username,
            key_file,
            passphrase,
            f"ls -l /proc/{gps_pid}/fd 2>/dev/null",
        )

        match = re.search(r"->\s+(/dev/ttyUSB\d+)", fd_output)

        if match:

            detected_device = match.group(1)

            nmea_output = run_ssh_command(
                host,
                SSH_PORT,
                username,
                key_file,
                passphrase,
                f"timeout 5 cat {detected_device}",
            )

            if contains_nmea(nmea_output):
                return detected_device, nmea_output

    usb_devices_output = run_ssh_command(
        host,
        SSH_PORT,
        username,
        key_file,
        passphrase,
        "ls -1 /dev/ttyUSB* 2>/dev/null",
    )

    for device in usb_devices_output.splitlines():

        device = device.strip()

        if not device.startswith("/dev/ttyUSB"):
            continue

        nmea_output = run_ssh_command(
            host,
            SSH_PORT,
            username,
            key_file,
            passphrase,
            f"timeout 3 cat {device}",
        )

        if contains_nmea(nmea_output):
            return device, nmea_output

    return "NOT_DETECTED", ""

def collect_wan_diagnostics(
    host,
    username,
    key_file,
    passphrase,
):
    results = {}

    command = r"""
    echo
    echo "### ls_unified ###"
    /usr/local/bin/ls_unified 2>/dev/null
    echo
    echo "### wan1_modem_details ###"
    cat /var/local/unified/01/modem-details 2>/dev/null
    echo
    echo "### wan1_firmware ###"
    cat /var/local/unified/01/modem-firmware 2>/dev/null
    echo
    echo "### wan1_cell_id ###"
    cat /var/local/unified/01/cell-id 2>/dev/null
    echo
    echo "### wan1_loadbalance ###"
    cat /var/local/loadbalance/wans/wan1 2>/dev/null
    echo
    echo "### wan1_state ###"
    cat /var/local/unified/01/state 2>/dev/null
    echo
    echo "### wan1_attach_state ###"
    cat /var/local/unified/01/attach-state 2>/dev/null
    echo
    echo "### wan1_registration_status ###"
    cat /var/local/unified/01/registration-status 2>/dev/null
    echo
    echo "### wan1_operator ###"
    cat /var/local/unified/01/current-operator 2>/dev/null
    echo
    echo "### wan1_tech ###"
    cat /var/local/unified/01/tech 2>/dev/null
    echo
    echo "### wan1_tech_details ###"
    cat /var/local/unified/01/tech-details 2>/dev/null
    echo
    echo "### wan1_ifname ###"
    cat /var/local/unified/01/ifname 2>/dev/null
    echo
    echo "### wan1_dev ###"
    cat /var/local/unified/01/dev 2>/dev/null
    echo
    echo "### wan1_ca ###"
    cat /var/local/unified/01/ca 2>/dev/null
    echo
    
    echo "### wan2_modem_details ###"
    cat /var/local/unified/02/modem-details 2>/dev/null
    echo
    echo "### wan2_firmware ###"
    cat /var/local/unified/02/modem-firmware 2>/dev/null
    echo
    echo "### wan2_cell_id ###"
    cat /var/local/unified/02/cell-id 2>/dev/null
    echo
    echo "### wan2_loadbalance ###"
    cat /var/local/loadbalance/wans/wan2 2>/dev/null
    echo
    echo "### wan2_state ###"
    cat /var/local/unified/02/state 2>/dev/null
    echo
    echo "### wan2_attach_state ###"
    cat /var/local/unified/02/attach-state 2>/dev/null
    echo
    echo "### wan2_registration_status ###"
    cat /var/local/unified/02/registration-status 2>/dev/null
    echo
    echo "### wan2_operator ###"
    cat /var/local/unified/02/current-operator 2>/dev/null
    echo
    echo "### wan2_tech ###"
    cat /var/local/unified/02/tech 2>/dev/null
    echo
    echo "### wan2_tech_details ###"
    cat /var/local/unified/02/tech-details 2>/dev/null
    echo
    echo "### wan2_ifname ###"
    cat /var/local/unified/02/ifname 2>/dev/null
    echo
    echo "### wan2_dev ###"
    cat /var/local/unified/02/dev 2>/dev/null
    echo
    echo "### wan2_ca ###"
    cat /var/local/unified/02/ca 2>/dev/null
    echo

    echo "### wan3_modem_details ###"
    cat /var/local/unified/03/modem-details 2>/dev/null
    echo
    echo "### wan3_firmware ###"
    cat /var/local/unified/03/modem-firmware 2>/dev/null
    echo
    echo "### wan3_cell_id ###"
    cat /var/local/unified/03/cell-id 2>/dev/null
    echo
    echo "### wan3_loadbalance ###"
    cat /var/local/loadbalance/wans/wan3 2>/dev/null
    echo
    echo "### wan3_state ###"
    cat /var/local/unified/03/state 2>/dev/null
    echo
    echo "### wan3_attach_state ###"
    cat /var/local/unified/03/attach-state 2>/dev/null
    echo
    echo "### wan3_registration_status ###"
    cat /var/local/unified/03/registration-status 2>/dev/null
    echo
    echo "### wan3_operator ###"
    cat /var/local/unified/03/current-operator 2>/dev/null
    echo
    echo "### wan3_tech ###"
    cat /var/local/unified/03/tech 2>/dev/null
    echo
    echo "### wan3_tech_details ###"
    cat /var/local/unified/03/tech-details 2>/dev/null
    echo
    echo "### wan3_ifname ###"
    cat /var/local/unified/03/ifname 2>/dev/null
    echo
    echo "### wan3_dev ###"
    cat /var/local/unified/03/dev 2>/dev/null
    echo
    echo "### wan3_ca ###"
    cat /var/local/unified/03/ca 2>/dev/null
    echo
    """

    output = run_ssh_command(
        host,
        SSH_PORT,
        username,
        key_file,
        passphrase,
        command,
    )

    if output == "CONNECTION_TIMEOUT" or str(output).startswith("SSH_ERROR"):
        results["ls_unified"] = output
        return results

    current_key = None
    buffer = []

    for line in output.splitlines():
        if line.startswith("### ") and line.endswith(" ###"):
            if current_key is not None:
                results[current_key] = "\n".join(buffer).strip()

            current_key = line.replace("###", "").strip()
            buffer = []
        else:
            buffer.append(line)

    if current_key is not None:
        results[current_key] = "\n".join(buffer).strip()

    expected_keys = ["ls_unified"]

    for wan in [1, 2, 3]:
        expected_keys.extend([
            f"wan{wan}_modem_details",
            f"wan{wan}_firmware",
            f"wan{wan}_cell_id",
            f"wan{wan}_loadbalance",
            f"wan{wan}_state",
            f"wan{wan}_attach_state",
            f"wan{wan}_registration_status",
            f"wan{wan}_operator",
            f"wan{wan}_tech",
            f"wan{wan}_tech_details",
            f"wan{wan}_ifname",
            f"wan{wan}_dev",
            f"wan{wan}_ca",
        ])

    for key in expected_keys:
        results.setdefault(key, "")

    return results

def print_report(train_id, gprmc_line, satellites=None):
    gprmc = parse_gprmc(gprmc_line)

    if gprmc["healthy"]:
        diagnosis = "GPS HEALTHY"
        likely_cause = "GPS has a valid active fix"

    elif gprmc["status"] == "V" and satellites == 0:
        diagnosis = "GPS FAILED"
        likely_cause = "Likely GPS reception / antenna path issue"

    elif gprmc["status"] == "V":
        diagnosis = "GPS FAILED"
        likely_cause = "Invalid GPS fix"

    else:
        diagnosis = "GPS UNKNOWN"
        likely_cause = "Unable to classify GPS status"

    print("=" * 70)
    print(f"GPS Diagnostic Report - {train_id}")
    print("=" * 70)
    print(f"Raw GPRMC: {gprmc_line}")
    print()
    print(f"Valid Sentence: {gprmc['valid_sentence']}")
    print(f"Fix Status: {gprmc['status']}")
    print(f"UTC Time: {gprmc['utc_time']}")
    print(f"Satellites Visible: {satellites}")
    print()
    print(f"Diagnosis: {diagnosis}")
    print(f"Likely Cause: {likely_cause}")
    print("=" * 70)
    
def print_extended_report(train_id, results, satellites):

    gprmc = parse_gprmc(results["gprmc"])

    tty_ok = "/dev/" in results["tty"]

    gps_running = len(results["gps"].strip()) > 0

    mqtt_running = "mosquitto" in results["mqtt"].lower()

    broadcast_running = (
        "broadcast_unicast_gps.py"
        in results["broadcast"]
    )

    vlan_present = "br0.105" in results["vlan105"]

    if gprmc["healthy"]:
        diagnosis = "GPS HEALTHY"
        likely_cause = "GPS has a valid active fix"

    elif gprmc["status"] == "V" and satellites == 0:
        diagnosis = "GPS FAILED"
        likely_cause = "Likely GPS reception / antenna path issue"

    elif gprmc["status"] == "V":
        diagnosis = "GPS FAILED"
        likely_cause = "Invalid GPS fix"

    else:
        diagnosis = "GPS UNKNOWN"
        likely_cause = "Unable to classify GPS status"

    print("\n" + "=" * 80)
    print(f"GPS Diagnostic Report - {train_id}")
    print("=" * 80)

    print("\nSERVICE CHECKS")
    print("-" * 40)

    print(f"GPS Device Present   : {tty_ok}")
    print(f"GPS Device Used      : {results.get('gps_device', 'Unknown')}")
    print(f"GPS Process Running  : {gps_running}")
    print(f"MQTT Running         : {mqtt_running}")
    print(f"Broadcast Running    : {broadcast_running}")
    print(f"VLAN105 Present      : {vlan_present}")

    print("\nGPS STATUS")
    print("-" * 40)

    print(f"GPRMC Status         : {gprmc['status']}")
    print(f"UTC Time             : {gprmc['utc_time']}")
    print(f"Satellites Visible   : {satellites}")

    print("\nASSESSMENT")
    print("-" * 40)

    print(f"Diagnosis            : {diagnosis}")
    print(f"Likely Cause         : {likely_cause}")

    print("\nRAW DATA")
    print("-" * 40)
    
    print(results["gprmc"])

    print("\n" + "=" * 80)
    
    save_csv_report(
        train_id,
        results.get("host", "unknown"),
        results,
        satellites,
        diagnosis,
        likely_cause,
    )
    print("\nSUMMARY")
    print("-" * 40)
    print(f"Train ID             : {train_id}")
    print(f"GPS Device           : {results.get('gps_device', 'Unknown')}")
    print(f"Diagnosis            : {diagnosis}")

def print_wan_report(train_id, results):

    print("\n" + "=" * 80)
    print(f"WAN Diagnostic Report - {train_id}")
    print("=" * 80)

    print("\nMODEM HARDWARE DISCOVERY")
    print("-" * 40)
    print(results.get("ls_unified", "No ls_unified output"))

    wan1 = parse_wan_loadbalance(
    results["wan1_loadbalance"]
)

    wan1_status = classify_wan_status(wan1)
    wan1_diagnosis, wan1_action = get_wan_recommendation(
    1,
    wan1_status,
    results,
    )
    
    print("\nWAN 1")
    print("-" * 40)

    print(f"Modem State   : {results.get('wan1_state', '')}")
    print(f"Attach State  : {results.get('wan1_attach_state', '')}")
    print(f"Registration  : {results.get('wan1_registration_status', '')}")
    print(f"Operator      : {results.get('wan1_operator', '')}")
    print(f"Technology    : {results.get('wan1_tech', '')}")
    print(f"Tech Details  : {results.get('wan1_tech_details', '')}")
    print(f"Unified IF    : {results.get('wan1_ifname', '')}")
    print(f"Device        : {results.get('wan1_dev', '')}")
    print(f"CA State      : {results.get('wan1_ca', '')}")
    print(f"Status        : {wan1_status}")
    print(f"Interface     : {wan1['interface']}")
    print(f"Latency (RTT) : {wan1['rtt']} ms")
    print(f"Serving Cell  : {results['wan1_cell_id']}")
    print(f"Modem         : {results['wan1_modem_details']}")
    print(f"Firmware      : {results['wan1_firmware']}")
    print("\nDiagnosis")
    print("-" * 40)
    print(f"Diagnosis     : {wan1_diagnosis}")
    print(f"Next Steps    : {wan1_action}")

    wan2 = parse_wan_loadbalance(
    results["wan2_loadbalance"]
    )

    wan2_status = classify_wan_status(wan2)
    wan2_diagnosis, wan2_action = get_wan_recommendation(
    2,
    wan2_status,
    results,
    )

    print("\nWAN 2")
    print("-" * 40)

    print(f"Modem State   : {results.get('wan2_state', '')}")
    print(f"Attach State  : {results.get('wan2_attach_state', '')}")
    print(f"Registration  : {results.get('wan2_registration_status', '')}")
    print(f"Operator      : {results.get('wan2_operator', '')}")
    print(f"Technology    : {results.get('wan2_tech', '')}")
    print(f"Tech Details  : {results.get('wan2_tech_details', '')}")
    print(f"Unified IF    : {results.get('wan2_ifname', '')}")
    print(f"Device        : {results.get('wan2_dev', '')}")
    print(f"CA State      : {results.get('wan2_ca', '')}")
    print(f"Status        : {wan2_status}")
    print(f"Interface     : {wan2['interface']}")
    print(f"Latency (RTT) : {wan2['rtt']} ms")
    print(f"Serving Cell  : {results['wan2_cell_id']}")
    print(f"Modem         : {results['wan2_modem_details']}")
    print(f"Firmware      : {results['wan2_firmware']}")
    print("\nDiagnosis")
    print("-" * 40)
    print(f"Diagnosis     : {wan2_diagnosis}")
    print(f"Next Steps    : {wan2_action}")

    wan3 = parse_wan_loadbalance(
    results["wan3_loadbalance"]
    )

    wan3_status = classify_wan_status(wan3)
    wan3_diagnosis, wan3_action = get_wan_recommendation(
    3,
    wan3_status,
    results,
    )

    print("\nWAN 3")
    print("-" * 40)

    print(f"Modem State   : {results.get('wan3_state', '')}")
    print(f"Attach State  : {results.get('wan3_attach_state', '')}")
    print(f"Registration  : {results.get('wan3_registration_status', '')}")
    print(f"Unified IF    : {results.get('wan3_ifname', '')}")
    print(f"Device        : {results.get('wan3_dev', '')}")
    print(f"CA State      : {results.get('wan3_ca', '')}") 
    print(f"Status        : {wan3_status}")
    print(f"Interface     : {wan3['interface']}")
    print("\nDiagnosis")
    print("-" * 40)
    print(f"Diagnosis     : {wan3_diagnosis}")
    print(f"Next Steps    : {wan3_action}")

    print("\n" + "=" * 80)   

def save_wan_csv_report(train_id, host, results):
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)

    csv_file = reports_dir / "wan_diagnostics.csv"

    wan1 = parse_wan_loadbalance(results["wan1_loadbalance"])
    wan2 = parse_wan_loadbalance(results["wan2_loadbalance"])
    wan3 = parse_wan_loadbalance(results["wan3_loadbalance"])

    file_exists = csv_file.exists()

    with open(csv_file, mode="a", newline="") as file:
        writer = csv.writer(file)

        if not file_exists:
            writer.writerow([
                "timestamp",
                "train_id",
                "ip_address",

                "wan1_status",
                "wan1_modem_state",
                "wan1_attach_state",
                "wan1_registration_status",
                "wan1_operator",
                "wan1_technology",
                "wan1_tech_details",
                "wan1_unified_if",
                "wan1_device",
                "wan1_ca_state",
                "wan1_interface",
                "wan1_latency_ms",
                "wan1_serving_cell",
                "wan1_modem",
                "wan1_firmware",
                "wan1_diagnosis",
                "wan1_next_steps",

                "wan2_status",
                "wan2_modem_state",
                "wan2_attach_state",
                "wan2_registration_status",
                "wan2_operator",
                "wan2_technology",
                "wan2_tech_details",
                "wan2_unified_if",
                "wan2_device",
                "wan2_ca_state",
                "wan2_interface",
                "wan2_latency_ms",
                "wan2_serving_cell",
                "wan2_modem",
                "wan2_firmware",
                "wan2_diagnosis",
                "wan2_next_steps",

                "wan3_status",
                "wan3_modem_state",
                "wan3_attach_state",
                "wan3_registration_status",
                "wan3_unified_if",
                "wan3_device",
                "wan3_ca_state",
                "wan3_interface",
                "wan3_latency_ms",
                "wan3_diagnosis",
                "wan3_next_steps",
            ])

        wan1_diagnosis, wan1_action = get_wan_recommendation(
            1,
            classify_wan_status(wan1),
            results
        )
            
        wan2_diagnosis, wan2_action = get_wan_recommendation(
            2,
            classify_wan_status(wan2),
            results
        )

        wan3_diagnosis, wan3_action = get_wan_recommendation(
            3,
            classify_wan_status(wan3),
            results
        )

        writer.writerow([
            datetime.now().isoformat(timespec="seconds"),
            train_id,
            host,

            classify_wan_status(wan1),
            results.get("wan1_state", ""),
            results.get("wan1_attach_state", ""),
            results.get("wan1_registration_status", ""),
            results.get("wan1_operator", ""),
            results.get("wan1_tech", ""),
            results.get("wan1_tech_details", ""),
            results.get("wan1_ifname", ""),
            results.get("wan1_dev", ""),
            results.get("wan1_ca", ""),
            wan1["interface"],
            wan1["rtt"],
            results.get("wan1_cell_id", ""),
            results.get("wan1_modem_details", ""),
            results.get("wan1_firmware", ""),
            wan1_diagnosis,
            wan1_action,

            classify_wan_status(wan2),
            results.get("wan2_state", ""),
            results.get("wan2_attach_state", ""),
            results.get("wan2_registration_status", ""),
            results.get("wan2_operator", ""),
            results.get("wan2_tech", ""),
            results.get("wan2_tech_details", ""),
            results.get("wan2_ifname", ""),
            results.get("wan2_dev", ""),
            results.get("wan2_ca", ""),
            wan2["interface"],
            wan2["rtt"],
            results.get("wan2_cell_id", ""),
            results.get("wan2_modem_details", ""),
            results.get("wan2_firmware", ""),
            wan2_diagnosis,
            wan2_action,

            classify_wan_status(wan3),
            results.get("wan3_state", ""),
            results.get("wan3_attach_state", ""),
            results.get("wan3_registration_status", ""),
            results.get("wan3_ifname", ""),
            results.get("wan3_dev", ""),
            results.get("wan3_ca", ""),
            wan3["interface"],
            wan3["rtt"],
            wan3_diagnosis,
            wan3_action,
        ])

    print(f"\nWAN CSV report updated: {csv_file}")

def save_wan_fleet_csv_report(train_id, host, results, train_profile, report_file):
    file_exists = Path(report_file).exists()

    with open(report_file, mode="a", newline="") as file:
        writer = csv.writer(file)

        if not file_exists:
            writer.writerow([
                "timestamp",
                "train_id",
                "ip_address",
                "wan",
                "fleet_expected",
                "status",
                "diagnosis",
                "next_steps",
                "modem_state",
                "attach_state",
                "registration_status",
                "operator",
                "technology",
                "tech_details",
                "unified_if",
                "device",
                "ca_state",
                "interface",
                "latency_ms",
                "serving_cell",
                "modem",
                "firmware",
            ])

        for wan_number in [1, 2, 3]:
            wan_id = f"{wan_number:02d}"
            prefix = f"wan{wan_number}"
            fleet_expected = wan_id in train_profile.get("active_wans", [])

            wan_data = parse_wan_loadbalance(
                results.get(f"{prefix}_loadbalance", "")
            )

            wan_result = get_wan_result(
                wan_number,
                results,
                train_profile,
            )

            writer.writerow([
                datetime.now().isoformat(timespec="seconds"),
                train_id,
                host,
                f"WAN{wan_number}",
                fleet_expected,
                wan_result["status"],
                wan_result["diagnosis"],
                wan_result["next_steps"],
                results.get(f"{prefix}_state", ""),
                results.get(f"{prefix}_attach_state", ""),
                results.get(f"{prefix}_registration_status", ""),
                results.get(f"{prefix}_operator", ""),
                results.get(f"{prefix}_tech", ""),
                results.get(f"{prefix}_tech_details", ""),
                results.get(f"{prefix}_ifname", ""),
                results.get(f"{prefix}_dev", ""),
                results.get(f"{prefix}_ca", ""),
                wan_data["interface"],
                wan_data["rtt"],
                results.get(f"{prefix}_cell_id", ""),
                results.get(f"{prefix}_modem_details", ""),
                results.get(f"{prefix}_firmware", ""),
            ])

def save_csv_report(train_id, host, results, satellites, diagnosis, likely_cause):
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)

    csv_file = Path(results.get("report_file", reports_dir / "gps_diagnostics.csv"))

    gprmc = parse_gprmc(results["gprmc"])

    tty_ok = "/dev/" in results["tty"]
    gps_running = len(results["gps"].strip()) > 0
    mqtt_running = "mosquitto" in results["mqtt"].lower()
    broadcast_running = "broadcast_unicast_gps.py" in results["broadcast"]
    vlan_present = "br0.105" in results["vlan105"]

    file_exists = csv_file.exists()

    with open(csv_file, mode="a", newline="") as file:
        writer = csv.writer(file)

        if not file_exists:
            writer.writerow([
                "timestamp",
                "train_id",
                "ip_address",
                "gps_device",
                "gprmc_status",
                "utc_time",
                "satellites_visible",
                "gps_device_present",
                "gps_running",
                "mqtt_running",
                "broadcast_running",
                "vlan105_present",
                "diagnosis",
                "likely_cause",
                "raw_gprmc",
            ])

        writer.writerow([
            datetime.now().isoformat(timespec="seconds"),
            train_id,
            host,
            results.get("gps_device", "Unknown"),
            gprmc["status"],
            gprmc["utc_time"],
            satellites,
            tty_ok,
            gps_running,
            mqtt_running,
            broadcast_running,
            vlan_present,
            diagnosis,
            likely_cause,
            results["gprmc"],
        ])

    print(f"\nCSV report updated: {csv_file}")

def save_timeout_csv_report(train_id, host, report_file=None):
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)

    csv_file = Path(report_file) if report_file else reports_dir / "gps_diagnostics.csv"
    file_exists = csv_file.exists()

    with open(csv_file, mode="a", newline="") as file:
        writer = csv.writer(file)

        if not file_exists:
            writer.writerow([
                "timestamp",
                "train_id",
                "ip_address",
                "gps_device",
                "gprmc_status",
                "utc_time",
                "satellites_visible",
                "gps_device_present",
                "gps_running",
                "mqtt_running",
                "broadcast_running",
                "vlan105_present",
                "diagnosis",
                "likely_cause",
                "raw_gprmc",
            ])

        writer.writerow([
            datetime.now().isoformat(timespec="seconds"),
            train_id,
            host,
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "Network connection timed out",
            "Train unreachable or CCU offline",
            "",
        ])

    print(f"\nCSV report updated: {csv_file}")

def diagnose_from_files(gprmc_file, nmea_file=None):
    gprmc_path = Path(gprmc_file)

    if not gprmc_path.exists():
        print(f"File not found: {gprmc_path}")
        return

    gprmc_line = gprmc_path.read_text().strip()
    satellites = None

    if nmea_file:
        nmea_path = Path(nmea_file)
        if nmea_path.exists():
            nmea_text = nmea_path.read_text(errors="ignore")
            satellites = parse_satellites(nmea_text)

    print_report("Offline Sample", gprmc_line, satellites)


def diagnose_live_train():
    train_id = input("Train ID: ")
    host = input("CCU IP address: ")
    username = SSH_USERNAME
    key_file = SSH_KEY_PATH
    passphrase = getpass("SSH key passphrase: ")

    profile_name, profile = select_profile()

    print(f"\nUsing profile: {profile_name}")
    print("Collecting diagnostics...\n")

    results = {}

    gps_device, nmea_output = detect_gps_device(
        host,
        username,
        key_file,
        passphrase,
        profile,
    )

    checks = {
        "tty": f"ls -l {gps_device}" if gps_device != "NOT_DETECTED" else "echo GPS_DEVICE_NOT_DETECTED",
        "gps": "ps aux | grep -i gps | grep -v grep",
        "mqtt": "ps aux | grep -i mosquitto | grep -v grep",
        "broadcast": f"ps aux | grep {profile['broadcast_process']} | grep -v grep",
        "vlan105": f"ip addr show {profile['vlan']}",
        "gprmc": f"cat {profile['gprmc_file']}",
    }

    for name, command in checks.items():
        results[name] = run_ssh_command(
            host,
            SSH_PORT,
            username,
            key_file,
            passphrase,
            command,
        )

    results["nmea"] = nmea_output
    results["gps_device"] = gps_device

    if "CONNECTION_TIMEOUT" in results.values():
        print("\nNetwork connection timed out")
        save_timeout_csv_report(train_id, host)
        return

    results["host"] = host

    satellites = parse_satellites(results["nmea"])

    print_extended_report(
        train_id,
        results,
        satellites,
    )

def diagnose_wan_live():

    train_id = input("Train ID: ")
    host = input("CCU IP address: ")
    username = SSH_USERNAME
    key_file = SSH_KEY_PATH
    passphrase = getpass("SSH key passphrase: ")

    print("\nCollecting WAN diagnostics...\n")

    results = collect_wan_diagnostics(
        host,
        username,
        key_file,
        passphrase,
    )

    print_wan_report(
        train_id,
        results,
    )

    save_wan_csv_report(
    train_id,
    host,
    results,
    )

def main():
    print("GPS Diagnostic Tool")
    print()
    print("1. Test healthy GPRMC sample")
    print("2. Test faulty GPRMC sample")
    print("3. Enter custom file path")
    print("4. Live SSH GPS check")
    print("5. Fleet Scan")
    print("6. WAN / Modem Diagnostics")
    print("7. Fleet WAN Scan")

    choice = input("\nSelect option: ")

    if choice == "1":
        diagnose_from_files("sample_data/healthy_gprmc.txt")

    elif choice == "2":
        diagnose_from_files("sample_data/faulty_gprmc.txt")

    elif choice == "3":
        gprmc_file = input("Enter GPRMC file path: ")
        nmea_file = input("Enter NMEA file path optional, press Enter to skip: ")
        diagnose_from_files(gprmc_file, nmea_file if nmea_file else None)

    elif choice == "4":
        diagnose_live_train()
        
    elif choice == "5":
        diagnose_fleet()

    elif choice == "6":
        diagnose_wan_live()

    elif choice == "7":
        diagnose_wan_fleet()

    else:
        print("Invalid option")
    
def select_inventory_file():
    inventory_dir = Path("inventory")
    inventory_files = sorted(inventory_dir.glob("*.csv"))

    if not inventory_files:
        raise FileNotFoundError("No inventory CSV files found in inventory directory")

    print("\nAvailable inventory files:")
    for index, file in enumerate(inventory_files, start=1):
        print(f"{index}. {file.name}")

    choice = int(input("\nSelect inventory file: "))
    return inventory_files[choice - 1]

def select_profile():
    print("\nAvailable hardware profiles:")
    for index, profile_name in enumerate(FLEET_PROFILES.keys(), start=1):
        print(f"{index}. {profile_name}")

    choice = int(input("\nSelect hardware profile: "))
    profile_name = list(FLEET_PROFILES.keys())[choice - 1]

    return profile_name, FLEET_PROFILES[profile_name]

def load_train_inventory(inventory_file):
    trains = []

    with open(inventory_file, newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            trains.append({
                "train_id": row["train_id"],
                "ip_address": row["ip_address"],
                "fleet": row.get("fleet", "")
            })

    return trains
 
def create_report_file(inventory_file):
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    inventory_name = Path(inventory_file).stem

    return reports_dir / f"{timestamp}_{inventory_name}_gps_diag.csv"

def create_wan_report_file(inventory_file):
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    inventory_name = Path(inventory_file).stem

    return reports_dir / f"{timestamp}_{inventory_name}_wan_diag.csv"

def diagnose_wan_fleet():

    username = SSH_USERNAME
    key_file = SSH_KEY_PATH
    passphrase = getpass("SSH key passphrase: ")

    inventory_file = select_inventory_file()
    profile_name = inventory_file.stem
    profile = FLEET_PROFILES.get(profile_name)

    if not profile:
        raise ValueError(f"No fleet profile found for inventory: {profile_name}")

    report_file = create_wan_report_file(inventory_file)
    trains = load_train_inventory(inventory_file)

    total_checked = 0
    healthy_count = 0
    faulty_count = 0
    offline_count = 0
    actionable_faults = []
    offline_units = []
    error_units = []
    fault_counter = {}

    print(f"\nLoaded {len(trains)} trains.")
    print(f"Using WAN profile: {profile_name}")
    print(f"Active WANs for this fleet: {', '.join(profile.get('active_wans', []))}\n")

    for train in trains:
        train_id = train["train_id"]
        host = train["ip_address"]
        fleet_name = train.get("fleet") or profile_name
        train_profile = FLEET_PROFILES.get(fleet_name)

        if not train_id or not host:
            continue

        if not train_profile:
            print(f"ERROR: No fleet profile found for {fleet_name} on train {train_id}")
            error_units.append(train_id)
            continue

        print(f"\nChecking WAN diagnostics for {train_id} ({host}) - {fleet_name}")

        try:
            results = collect_wan_diagnostics(
                host,
                username,
                key_file,
                passphrase,
            )

            if results.get("ls_unified") == "CONNECTION_TIMEOUT":
                print("TIMEOUT - retrying once...")

                results = collect_wan_diagnostics(
                    host,
                    username,
                    key_file,
                    passphrase,
                )

                if results.get("ls_unified") == "CONNECTION_TIMEOUT":
                    print("OFFLINE")
                    offline_count += 1
                    offline_units.append(train_id)
                    continue

            elif str(results.get("ls_unified", "")).startswith("SSH_ERROR"):
                print("SSH ERROR")
                offline_count += 1
                offline_units.append(train_id)
                continue

            save_wan_fleet_csv_report(
                train_id,
                host,
                results,
                train_profile,
                report_file,
            )

            total_checked += 1
            train_fault = False

            for wan_number in [1, 2, 3]:
                wan_result = get_wan_result(
                    wan_number,
                    results,
                    train_profile,
                )

                print(
                    f"WAN{wan_number}: "
                    f"{wan_result['status']} - "
                    f"{wan_result['diagnosis']}"
                )

                if (
                    wan_result["status"] != "AVAILABLE"
                    and wan_result["diagnosis"] != "WAN disabled by fleet design"
                ):
                    train_fault = True

                    actionable_faults.append(
                        f"{train_id} WAN{wan_number}: {wan_result['diagnosis']}"
                    )

                    fault_counter[wan_result["diagnosis"]] = (
                        fault_counter.get(wan_result["diagnosis"], 0) + 1
                    )

            if train_fault:
                faulty_count += 1
            else:
                healthy_count += 1

        except Exception as e:
            print(f"ERROR: {e}")
            error_units.append(train_id)

    print("\n" + "=" * 70)
    print("Fleet WAN Scan Complete")
    print("=" * 70)
    print(f"Inventory            : {inventory_file.name}")
    print(f"Total Trains Loaded  : {len(trains)}")
    print(f"Successfully Checked : {total_checked}")
    print(f"Healthy Trains       : {healthy_count}")
    print(f"Faulty Trains        : {faulty_count}")
    print(f"Offline              : {offline_count}")
    print(f"Errors               : {len(error_units)}")
    print(f"Actionable Faults    : {len(actionable_faults)}")
    print(f"Offline Units        : {', '.join(offline_units) if offline_units else 'None'}")
    print(f"Error Units          : {', '.join(error_units) if error_units else 'None'}")

    print("\nFault Breakdown")
    print("-" * 70)

    if fault_counter:
        for fault, count in fault_counter.items():
            print(f"{fault}: {count}")
    else:
        print("None")

    print("\nActionable Fault Summary")
    print("-" * 70)

    if actionable_faults:
        for fault in actionable_faults:
            print(f"- {fault}")
    else:
        print("None")

    print("=" * 70)
    print(f"WAN fleet report saved to: {report_file}")
 
def diagnose_fleet():

    username = SSH_USERNAME
    key_file = SSH_KEY_PATH
    passphrase = getpass("SSH key passphrase: ")

    inventory_file = select_inventory_file()
    profile_name = inventory_file.stem
    profile = FLEET_PROFILES.get(profile_name)

    if not profile:
        raise ValueError(f"No fleet profile found for inventory: {profile_name}")

    report_file = create_report_file(inventory_file)

    trains = load_train_inventory(inventory_file)

    healthy_count = 0
    failed_count = 0
    offline_count = 0
    error_count = 0
    failed_units = []
    offline_units = []
    error_units = []

    print(f"\nLoaded {len(trains)} trains.\n")

    for train in trains:

        train_id = train["train_id"]
        host = train["ip_address"]

        if not train_id or not host:
            continue

        print(f"\nChecking {train_id} ({host})")

        try:

            results = {}

            gps_device, nmea_output = detect_gps_device(
                host,
                username,
                key_file,
                passphrase,
                profile,
            )

            checks = {
                "tty": f"ls -l {gps_device}" if gps_device != "NOT_DETECTED" else "echo GPS_DEVICE_NOT_DETECTED",
                "gps": "ps aux | grep -i gps | grep -v grep",
                "mqtt": "ps aux | grep -i mosquitto | grep -v grep",
                "broadcast": f"ps aux | grep {profile['broadcast_process']} | grep -v grep",
                "vlan105": f"ip addr show {profile['vlan']}",
                "gprmc": f"cat {profile['gprmc_file']}",
            }
            
            for name, command in checks.items():
                results[name] = run_ssh_command(
                    host,
                    SSH_PORT,
                    username,
                    key_file,
                    passphrase,
                    command,
                )
            
            results["nmea"] = nmea_output
            results["gps_device"] = gps_device
            
            if "CONNECTION_TIMEOUT" in results.values():

                print("OFFLINE")
                
                offline_count += 1
                offline_units.append(train_id)

                save_timeout_csv_report(
                    train_id,
                    host,
                    report_file,
                )

                continue

            results["host"] = host
            results["report_file"] = report_file

            satellites = parse_satellites(
                results["nmea"]
            )

            gprmc = parse_gprmc(results["gprmc"])

            if gprmc["healthy"]:
                healthy_count += 1
            else:
                failed_count += 1
                failed_units.append(train_id)

            print_extended_report(
                train_id,
                results,
                satellites,
            )

        except Exception as e:
            
            error_count += 1
            error_units.append(train_id)
            print(f"ERROR: {e}")
    
    print("\n" + "=" * 60)
    print("Fleet Scan Complete")
    print("=" * 60)
    print(f"Total Trains Checked : {len(trains)}")
    print(f"Healthy              : {healthy_count}")
    print(f"Failed               : {failed_count}")
    print(f"Offline              : {offline_count}")
    print(f"Errors               : {error_count}")
    print(f"Failed Units         : {', '.join(failed_units) if failed_units else 'None'}")
    print(f"Offline Units        : {', '.join(offline_units) if offline_units else 'None'}")
    print(f"Error Units          : {', '.join(error_units) if error_units else 'None'}")
    print("=" * 60)

if __name__ == "__main__":
    main()