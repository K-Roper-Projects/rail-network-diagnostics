import csv
from datetime import datetime
from pathlib import Path

from diagnostics.wan import (
    parse_wan_loadbalance,
    get_wan_recommendation,
    classify_wan_status,
    get_wan_result,
)

def generate_wan_html_report(scan_results, output_file):
    generated_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Fleet WAN Diagnostic Report</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f4f6f8;
        }}
        h1 {{
            color: #2c3e50;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            background-color: white;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }}
        th {{
            background-color: #2c3e50;
            color: white;
        }}
        .healthy {{
            color: green;
            font-weight: bold;
        }}
        .fault {{
            color: red;
            font-weight: bold;
        }}
        .offline {{
            color: gray;
            font-weight: bold;
        }}
    </style>
</head>
<body>

<h1>Fleet WAN Diagnostic Report</h1>
<p><strong>Generated:</strong> {generated_time}</p>

<table>
<tr>
    <th>Train ID</th>
    <th>IP Address</th>
    <th>WAN1 Status</th>
    <th>WAN1 Diagnosis</th>
    <th>WAN2 Status</th>
    <th>WAN2 Diagnosis</th>
    <th>WAN3 Status</th>
    <th>WAN3 Diagnosis</th>
    <th>Overall Status</th>
</tr>
"""

    for row in scan_results:
        overall_status = row.get("overall_status", "UNKNOWN")
        status_class = get_status_class(overall_status)

        html += f"""
<tr>
    <td>{row.get("train_id", "")}</td>
    <td>{row.get("ip_address", "")}</td>
    <td>{row.get("wan1_status", "N/A")}</td>
    <td>{row.get("wan1_diagnosis", "N/A")}</td>
    <td>{row.get("wan2_status", "N/A")}</td>
    <td>{row.get("wan2_diagnosis", "N/A")}</td>
    <td>{row.get("wan3_status", "N/A")}</td>
    <td>{row.get("wan3_diagnosis", "N/A")}</td>
    <td class="{status_class}">{overall_status}</td>
</tr>
"""

    html += """
</table>
</body>
</html>
"""

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as file:
        file.write(html)
        
def get_status_class(status):
    status = str(status).upper()

    if status in ["HEALTHY", "ONLINE", "AVAILABLE"]:
        return "healthy"
    elif status in ["FAULT", "FAULTY", "FAILED", "ERROR"]:
        return "fault"
    elif status in ["WARNING", "DEGRADED", "ATTENTION"]:
        return "warning"
    elif status in ["OFFLINE", "TIMEOUT", "UNREACHABLE"]:
        return "offline"
    else:
        return ""
        
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
            "Train unreachable or onboard system offline",
            "",
        ])

    print(f"\nCSV report updated: {csv_file}")

def generate_combined_html_report(results, report_file):

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    status_counts = {
        "HEALTHY": 0,
        "DEGRADED": 0,
        "FAULT": 0,
        "OFFLINE": 0,
    }

    for result in results:
        state = result.get("overall_state", "FAULT")
        if state in status_counts:
            status_counts[state] += 1

    report_wans = sorted({
        wan_number
        for result in results
        for wan_number in result.get("report_wans", [])
    })

    rows = []

    for result in results:

        train_id = result.get("train_id", "Unknown")
        ip_address = result.get("ip_address", "")
        overall_state = result.get("overall_state", "FAULT")

        gps_state = result.get("gps_state", "UNKNOWN")
        gps_diagnosis = result.get(
            "gps_diagnosis",
            "No GPS diagnosis available",
        )

        wan_state = result.get("wan_state", "UNKNOWN")
        wan_results = result.get("wan_results", [])

        wan_lookup = {
            wan.get("wan_number"): wan
            for wan in wan_results
        }

        wan_cells = []

        for wan_number in report_wans:

            wan = wan_lookup.get(wan_number)

            if wan:
                status = wan.get("status", "UNKNOWN")
                diagnosis = wan.get(
                    "diagnosis",
                    "No diagnosis available",
                )

                wan_cells.append(
                    f"""
                    <td>
                        <strong>{status}</strong><br>
                        <span>{diagnosis}</span>
                    </td>
                    """
                )

            else:
                wan_cells.append(
                    """
                    <td>
                        <strong>UNKNOWN</strong><br>
                        <span>No data available</span>
                    </td>
                    """
                )

        rows.append(
            f"""
            <tr>
                <td>{train_id}</td>
                <td>{ip_address}</td>
                <td class="{overall_state.lower()}">
                    {overall_state}
                </td>
                <td>
                    <strong>{gps_state}</strong><br>
                    <span>{gps_diagnosis}</span>
                </td>
                <td>{wan_state}</td>
                {''.join(wan_cells)}
            </tr>
            """
        )

    wan_headers = "".join(
        f"<th>WAN{wan_number}</th>"
        for wan_number in report_wans
    )

    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Combined Fleet Health Report</title>

        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 30px;
                background-color: #f5f5f5;
            }}

            h1 {{
                margin-bottom: 5px;
            }}

            .summary {{
                margin: 20px 0;
                padding: 15px;
                background: white;
                border-radius: 6px;
            }}

            table {{
                width: 100%;
                border-collapse: collapse;
                background: white;
            }}

            th,
            td {{
                border: 1px solid #cccccc;
                padding: 10px;
                text-align: left;
                vertical-align: top;
            }}

            th {{
                background-color: #eeeeee;
            }}

            .healthy {{
                background-color: #d4edda;
            }}

            .degraded {{
                background-color: #fff3cd;
            }}

            .fault {{
                background-color: #f8d7da;
            }}

            .offline {{
                background-color: #d6d8db;
            }}

            span {{
                font-size: 0.9em;
            }}
        </style>
    </head>

    <body>

        <h1>Combined Fleet Health Report</h1>
        <p>Generated: {generated_at}</p>

        <div class="summary">
            <strong>Total Trains:</strong> {len(results)}<br>
            <strong>Healthy:</strong> {status_counts["HEALTHY"]}<br>
            <strong>Degraded:</strong> {status_counts["DEGRADED"]}<br>
            <strong>Fault:</strong> {status_counts["FAULT"]}<br>
            <strong>Offline:</strong> {status_counts["OFFLINE"]}
        </div>

        <table>
            <thead>
                <tr>
                    <th>Train</th>
                    <th>IP Address</th>
                    <th>Overall</th>
                    <th>GPS</th>
                    <th>WAN Health</th>
                    {wan_headers}
                </tr>
            </thead>

            <tbody>
                {''.join(rows)}
            </tbody>
        </table>

    </body>
    </html>
    """

    report_file.write_text(
        html,
        encoding="utf-8",
    )
