# Rail Network Diagnostics

A Python-based network automation and diagnostics platform designed to remotely identify GPS receiver faults and onboard network issues across train fleets.

The project was created to reduce manual fault investigation, improve first-line diagnostics, and minimise unnecessary depot visits by providing automated health checks against onboard systems.

The platform currently supports automated GPS and WAN diagnostics across multiple fleets, generating fleet-wide CSV and HTML reports with engineering recommendations based on detected fault signatures.

Current Version Highlights

✓ Multi-fleet GPS diagnostics
✓ Automatic GPS device discovery
✓ Fleet-wide GPS scanning
✓ Automate GPS fault diagnosis across multiple train fleets
✓ Fleet-wide WAN scanning
✓ WAN and modem diagnostics
✓ Automated WAN fault classification
✓ Engineering action recommendations
✓ Mixed-fleet hardware profile support
✓ CSV reporting and evidence collection
✓ HTML fleet reporting
✓ Real-world modem fault signature analysis

---

## Project Objectives

### Primary Objectives

* Combined GPS and WAN fleet health reporting
* Historical fault trending and analytics
* Reduce time spent manually connecting to individual train CCUs.
* Provide consistent fault reporting for support engineers.
* Identify GPS receiver, antenna, and service-related issues remotely.
* Reduce unnecessary site visits and associated operational costs.

### Future Objectives

* Combined GPS and WAN fleet health reporting.
* Historical fault trending and analytics.
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

### Fleet WAN Scanning

The platform can perform fleet-wide WAN health assessments across multiple train fleets.

Features include:

* Inventory-driven WAN scanning
* Automatic fleet profile detection
* Support for differing WAN topologies
* Offline train identification
* WAN fault classification
* Engineering action recommendations
* Fleet-wide CSV reporting
* Fleet-wide HTML reporting

Supported WAN configurations:

| Fleet | Active WANs |
|---------|---------|
| GWR 165/166 | WAN1, WAN3 |
| GWR 800/802 | WAN1, WAN2 |
| XC 170 | WAN1, WAN2, WAN3 |
| XC 220/221 | WAN1, WAN2, WAN3 |

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
Broadcast Running    : False
VLAN105 Present      : True

GPS STATUS
----------------------------------------
GPRMC Status         : A
UTC Time             : 061522.000
Satellites Visible   : 20

ASSESSMENT
----------------------------------------
Diagnosis            : GPS operational with service warning
Likely Cause         : GPS receiver has a valid fix, but the GPS broadcast process is not running.
```

---

## Project Structure

```text
rail-network-diagnostics
│
├── docs/
│   ├── FAULT_LIBRARY.md
│   └── project_notes.md
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
✓ Advanced GPS fault classification
✓ Engineering action recommendations
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
✓ HTML reporting
✓ Fleet WAN scanning
✓ Mixed-fleet inventory support
✓ Automatic WAN topology awareness
✓ Offline train detection
✓ WAN fault signature analysis
✓ Engineering action recommendations

## Fault Classification Engine

The WAN diagnostics engine performs automated analysis of modem runtime state information collected from onboard CCUs.

### GPS Fault Classifications

Current fault classifications include:

* GPS Operational
* GPS Operational with Service Warning
* GPS Operational with Network Warning
* GPS Device Not Detected
* GPS Process Not Running
* GPS Receiver Not Outputting NMEA
* GPS Invalid Fix - No Satellites Visible
* GPS Invalid Fix Despite Satellite Visibility
* GPS Invalid Fix
* GPS Broadcast Process Not Running
* MQTT Process Not Running
* GPS VLAN105 Interface Missing

### WAN Fault Classifications

Current fault classifications include:

* WAN Operational
* WAN Disabled by Fleet Design
* Modem Not Detected
* Network Registration Failure (NO PLMN)
* WAN Attach / Interface Bring-Up Failure
* DHCP Negotiation Failure (dhcp_cal)
* DHCP Lease Acquisition Failure (No Lease)
* LTE Session Establishment Failure
* High Latency WAN Failure (60000ms RTT)
* WAN Session Recovery Failure
* Offline / Connection Timeout

Each diagnosis includes recommended engineering actions and escalation guidance based on observed modem state information.

The classification engine is continuously refined using live fleet data and verified engineering outcomes.

## Lessons Learned

This project highlighted the importance of validating assumptions against real-world systems.

Initially, GPS serial devices were assumed to be fixed across fleets. Investigation of multiple 4600CCU platforms demonstrated that USB serial devices are dynamically assigned during boot, requiring automatic device discovery rather than hardcoded paths.

Investigation of the onboard WAN subsystem revealed that valuable modem health information is exposed through the unified runtime database located under /var/local/unified. By analysing modem state, registration status, attach state, interface creation and carrier aggregation status, the project evolved from simple status reporting into evidence-based fault classification capable of identifying likely modem failures and recommended engineering actions.

Fleet-wide WAN scanning introduced additional complexity due to differing hardware and modem configurations across train fleets. This required the development of fleet-specific WAN profiles capable of understanding which WAN interfaces are expected to be operational on each platform. The resulting architecture allows a single diagnostics platform to accurately assess multiple fleets while accounting for hardware differences and differing network topologies.

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

* Combined GPS and WAN fleet health reports.
* Interactive web dashboard.
* Scheduled WAN health scans.
* Historical WAN fault trending.
* Automated remediation workflows.
* Email-based reporting and notifications.
* Automated ticket generation.

### Network Monitoring

* Access point diagnostics.
* Switch diagnostics.
* CCTV service monitoring.
* End-to-end network health checks.

### Platform Evolution

* Combined GPS and WAN HTML reporting.
* Scheduled health scans.
* Database-backed reporting.
* AWS-hosted diagnostic platform.
* Web dashboard and analytics.

---

## Recent Project Milestones

* Implemented advanced GPS fault classification and engineering recommendations.
* Added GPS service and network warning detection.
* Added GPS invalid-fix fault signatures based on live fleet observations.
* Consolidated GPS and WAN knowledge into a unified fault library.
* Added fleet-wide WAN diagnostics across multiple train fleets.
* Implemented automated modem fault classification.
* Added engineering action recommendations based on detected fault signatures.
* Introduced mixed-fleet support with hardware-aware WAN profiles.
* Created a growing WAN fault knowledge base from live operational data.
* Reduced the need for manual modem investigation and WAN troubleshooting.
* Added fleet-wide HTML WAN reporting.
* Implemented fleet-aware WAN topology validation.
* Added WAN disabled-by-design detection.
* Added DHCP lease acquisition fault detection (No Lease).

## Author

Kevin Roper

IT Field Service Engineer transitioning into Infrastructure, Cloud and Automation Engineering through hands-on development and operational automation projects.
