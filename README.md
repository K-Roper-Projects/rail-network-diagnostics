# Rail Network Diagnostics

A Python-based network automation and diagnostics platform designed to remotely identify GPS receiver faults and onboard network issues across train fleets.

The project was created to reduce manual fault investigation, improve first-line diagnostics, and minimise unnecessary depot visits by providing automated health checks against onboard systems.

Current Version Highlights

✓ Multi-fleet GPS diagnostics
✓ Automatic GPS device discovery
✓ Fleet-wide GPS scanning
✓ WAN and modem diagnostics
✓ Automated WAN fault classification
✓ Engineering action recommendations
✓ CSV reporting and evidence collection

---

## Project Objectives

### Primary Objectives

* Automate GPS fault diagnosis across multiple train fleets.
* Reduce time spent manually connecting to individual train CCUs.
* Provide consistent fault reporting for support engineers.
* Identify GPS receiver, antenna, and service-related issues remotely.
* Reduce unnecessary site visits and associated operational costs.

### Future Objectives

* WAN fault classification and automated root cause analysis.
* Network switch and access point health monitoring.
* Automated fault trending and reporting.
* Scheduled fleet-wide health scans.
* Cloud-hosted diagnostics platform.
* Web-based dashboard and reporting.

---

## Supported Fleets

| Fleet       | Hardware Platform | GPS Device Method              |
| ----------- | ----------------- | ------------------------------ |
| GWR 165/166 | R3200CCU          | Fixed device (/dev/ttyS1)      |
| GWR 800/802 | 4600CCU           | Automatic GPS device discovery |
| XC 170      | 4600CCU           | Automatic GPS device discovery |
| XC 220/221  | 4600CCU           | Automatic GPS device discovery |

---

## Supported Modems

### Sierra Wireless

* MC7455
* 7710
* 8801

### Huawei

* Huawei Mobile Modems

## Key Features

### GPS Health Checks

The tool remotely validates:

* GPS process status
* MQTT service status
* GPS broadcast process status
* VLAN interface presence
* GPS receiver output
* NMEA sentence availability
* GPS fix status
* Satellite visibility
* UTC timestamp validity

### Fleet Scanning

The tool can automatically:

* Read inventory files
* Connect to multiple trains
* Run diagnostics remotely
* Export results to fleet-specific CSV reports
* Record offline or unreachable units
* Generate fleet health summaries

### WAN & Modem Diagnostics

The tool can remotely validate:

* Modem hardware discovery
* Sierra Wireless modem detection
* Huawei modem detection
* Modem firmware collection
* Serving cell identification
* WAN interface detection
* WAN availability monitoring
* WAN latency (RTT) reporting
* Cellular technology and band information
* Registration status validation
* Attach state monitoring
* Carrier Aggregation (CA) status
* Automated WAN fault classification
* Recommended engineering actions
* WAN diagnostic CSV export

### Automatic GPS Device Discovery

4600CCU platforms dynamically assign USB serial devices during boot.

Rather than relying on hardcoded serial devices, the tool:

1. Locates the running GPS process.
2. Identifies the active serial device from the process file descriptors.
3. Falls back to scanning available USB serial devices.
4. Detects valid NMEA data streams automatically.

This allows diagnostics to continue operating even when GPS devices move between:

```text
/dev/ttyUSB3
/dev/ttyUSB6
/dev/ttyUSB7
/dev/ttyUSB9
```

after system reboots.

---

## Example Output

```text
GPS Diagnostic Report - 802007

SERVICE CHECKS
----------------------------------------
GPS Device Present   : True
GPS Device Used      : /dev/ttyUSB3
GPS Process Running  : True
MQTT Running         : True
Broadcast Running    : True
VLAN105 Present      : True

GPS STATUS
----------------------------------------
GPRMC Status         : A
UTC Time             : 061522.000
Satellites Visible   : 20

ASSESSMENT
----------------------------------------
Diagnosis            : GPS HEALTHY
Likely Cause         : GPS has a valid active fix
```

---

## Project Structure

```text
rail-network-diagnostics
│
├── docs/
├── inventory/
│   └── example_inventory.csv
├── reports/
├── sample_data/
│   ├── healthy_gprmc.txt
│   ├── healthy_nmea.txt
│   ├── faulty_gprmc.txt
│   └── faulty_nmea.txt
│
├── gps_diag.py
├── ssh_test.py
├── requirements.txt
├── README.md
└── .gitignore
```

---

## Technologies Used

* Python
* Paramiko
* SSH
* CSV Reporting
* Linux Diagnostics
* Git
* GitHub

---

## Skills Demonstrated

### Network Engineering

* TCP/IP troubleshooting
* Remote diagnostics
* VLAN validation
* Service monitoring
* Linux administration
* Cellular WAN diagnostics
* Modem firmware validation
* Mobile network troubleshooting

### Software Development

* Python scripting
* Modular design
* File handling
* Exception handling
* Automated reporting

### Automation

* Fleet-wide diagnostics
* Automated health checking
* Inventory-driven scanning
* Dynamic hardware detection
* Dynamic modem discovery
* WAN health reporting

### DevOps & Version Control

* Git workflows
* GitHub repositories
* SSH authentication
* Repository management

---

## Current Capability

### GPS Diagnostics

✓ Fleet GPS scanning  
✓ Automatic GPS device discovery  
✓ GPS process validation  
✓ MQTT validation  
✓ GPS broadcast validation  
✓ CSV reporting  

### WAN Diagnostics

✓ Sierra Wireless modem detection
✓ Huawei modem detection
✓ Firmware collection
✓ Serving cell collection
✓ WAN availability monitoring
✓ WAN latency reporting
✓ Modem state monitoring
✓ Registration status monitoring
✓ Attach state monitoring
✓ Technology and band reporting
✓ Automated fault diagnosis
✓ Recommended engineering actions
✓ CSV reporting

## WAN Fault Classification

The WAN diagnostics engine performs automated analysis of modem runtime state information collected from onboard CCUs.

Current fault classifications include:

* WAN Operational
* Modem Not Detected
* Network Registration Failure
* DHCP Negotiation Failure
* WAN Attach / Interface Bring-Up Failure
* WAN Unavailable - Investigation Required

Each diagnosis includes recommended next steps to assist first-line support teams with fault triage and escalation decisions.

## Lessons Learned

This project highlighted the importance of validating assumptions against real-world systems.

Initially, GPS serial devices were assumed to be fixed across fleets. Investigation of multiple 4600CCU platforms demonstrated that USB serial devices are dynamically assigned during boot, requiring automatic device discovery rather than hardcoded paths.

Investigation of the onboard WAN subsystem revealed that valuable modem health information is exposed through the unified runtime database located under /var/local/unified. By analysing modem state, registration status, attach state, interface creation and carrier aggregation status, the project evolved from simple status reporting into evidence-based fault classification capable of identifying likely modem failures and recommended engineering actions.

The project also reinforced:

* The value of automation for repetitive operational tasks.
* The importance of building hardware-aware software.
* Structured fault diagnosis techniques.
* The benefits of version control and iterative development.

---

## Future Development Roadmap

### GPS Diagnostics

* Automatic GPS fault classification.
* GPS signal quality analysis.
* Historical GPS fault trending.

### WAN Diagnostics

* Fleet WAN scanning.
* Fleet-wide modem health reporting.
* Historical fault trending.
* Additional modem fault signatures.
* Automatic FSE visit recommendations.
* Automated ticket generation.
* SIM and carrier diagnostics.
* DHCP and carrier attach diagnostics.

### Network Monitoring

* Access point diagnostics.
* Switch diagnostics.
* CCTV service monitoring.
* End-to-end network health checks.

### Platform Evolution

* HTML reporting.
* Scheduled health scans.
* Database-backed reporting.
* AWS-hosted diagnostic platform.
* Web dashboard and analytics.

---

## Author

Kevin Roper

IT Field Service Engineer transitioning into Infrastructure, Cloud and Automation Engineering through hands-on development and operational automation projects.
