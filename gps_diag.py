from pathlib import Path
from getpass import getpass
import re
import csv
import socket
from datetime import datetime
import paramiko

SSH_PORT = 2510

FLEET_PROFILES = {
    "gwr_165_166": {
        "gps_device": "/dev/ttyS1",
        "vlan": "br0.105",
        "gprmc_file": "/var/local/gprmc",
        "broadcast_process": "broadcast_unicast_gps.py",
    },
    "gwr_800_802": {
        "gps_device": "/dev/ttyUSB7",
        "vlan": "br0.105",
        "gprmc_file": "/var/local/gprmc",
        "broadcast_process": "broadcast_unicast_gps.py",
    },
    "xc_220_221": {
        "gps_device": "/dev/ttyUSB9",
        "vlan": "br0.105",
        "gprmc_file": "/var/local/gprmc",
        "broadcast_process": "broadcast_unicast_gps.py",
    },
    "xc_170": {
        "gps_device": "/dev/ttyUSB9",
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
            timeout=10,
            look_for_keys=False,
            allow_agent=False,
        )

        stdin, stdout, stderr = client.exec_command(command, timeout=15)

        output = stdout.read().decode(errors="ignore").strip()
        error = stderr.read().decode(errors="ignore").strip()

        return output if output else error

    except (socket.timeout, TimeoutError):
        return "CONNECTION_TIMEOUT"

    except Exception as e:
        return f"SSH_ERROR: {e}"

    finally:
        client.close()


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

    mqtt_running = (
        "mosquitto" in results["mqtt"].lower()
        or "mqtt" in results["mqtt"].lower()
    )

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

    print(f"TTYS1 Present        : {tty_ok}")
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
    
def save_csv_report(train_id, host, results, satellites, diagnosis, likely_cause):
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)

    csv_file = Path(results.get("report_file", reports_dir / "gps_diagnostics.csv"))

    gprmc = parse_gprmc(results["gprmc"])

    tty_ok = "/dev/" in results["tty"]
    gps_running = len(results["gps"].strip()) > 0
    mqtt_running = "mosquitto" in results["mqtt"].lower() or "mqtt" in results["mqtt"].lower()
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
                "gprmc_status",
                "utc_time",
                "satellites_visible",
                "ttyS1_present",
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
                "gprmc_status",
                "utc_time",
                "satellites_visible",
                "ttyS1_present",
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
    port = int(input("SSH port [2510]: ") or "2510")
    username = input("Username [root]: ") or "root"
    key_file = input("OpenSSH private key path: ")
    passphrase = getpass("SSH key passphrase: ")

    print("\nCollecting diagnostics...\n")

    results = {}

    checks = {
        "tty": "ls -l /dev/ttyS1",
        "gps": "ps aux | grep -i gps | grep -v grep",
        "mqtt": "ps aux | grep -i mqtt | grep -v grep",
        "broadcast": "ps aux | grep broadcast | grep -v grep",
        "vlan105": "ip addr show br0.105",
        "gprmc": "cat /var/local/gprmc",
        "nmea": "timeout 5 cat /dev/ttyS1",
    }

    for name, command in checks.items():
        results[name] = run_ssh_command(
            host,
            port,
            username,
            key_file,
            passphrase,
            command,
        )
    
    if "CONNECTION_TIMEOUT" in results.values():
        print("\nNetwork connection timed out")
        save_timeout_csv_report(
            train_id,
            host,
        )
        return    
    
    results["host"] = host
        
    satellites = parse_satellites(results["nmea"])

    print_extended_report(
        train_id,
        results,
        satellites,
    )


def main():
    print("GPS Diagnostic Tool")
    print()
    print("1. Test healthy GPRMC sample")
    print("2. Test faulty GPRMC sample")
    print("3. Enter custom file path")
    print("4. Live SSH GPS check")
    print("5. Fleet Scan")

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
 
def diagnose_fleet():

    username = input("Username [root]: ") or "root"
    key_file = input("OpenSSH private key path: ")
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

    print(f"\nLoaded {len(trains)} trains.\n")

    for train in trains:

        train_id = train["train_id"]
        host = train["ip_address"]

        print(f"\nChecking {train_id} ({host})")

        try:

            results = {}

            checks = {
                "tty": f"ls -l {profile['gps_device']}",
                "gps": "ps aux | grep -i gps | grep -v grep",
                "mqtt": "ps aux | grep -i mqtt | grep -v grep",
                "broadcast": f"ps aux | grep {profile['broadcast_process']} | grep -v grep",
                "vlan105": f"ip addr show {profile['vlan']}",
                "gprmc": f"cat {profile['gprmc_file']}",
                "nmea": f"timeout 5 cat {profile['gps_device']}",
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

            if "CONNECTION_TIMEOUT" in results.values():

                print("OFFLINE")
                
                offline_count += 1

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

            print_extended_report(
                train_id,
                results,
                satellites,
            )

        except Exception as e:
            
            error_count += 1
            print(f"ERROR: {e}")
    
    print("\n" + "=" * 60)
    print("Fleet Scan Complete")
    print("=" * 60)
    print(f"Total Trains Checked : {len(trains)}")
    print(f"Healthy              : {healthy_count}")
    print(f"Failed               : {failed_count}")
    print(f"Offline              : {offline_count}")
    print(f"Errors               : {error_count}")
    print("=" * 60)

if __name__ == "__main__":
    main()