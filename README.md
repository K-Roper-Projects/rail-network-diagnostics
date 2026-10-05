# Rail Network Diagnostics

**Python · Linux · SSH · Network Automation · GPS · Cellular WAN · Automated Fault Classification**

A Python-based network diagnostics platform developed to automate remote fault investigation across operational rail fleets.

The platform securely connects to onboard Linux-based communication systems, collects GPS, network, service and cellular modem health data, and converts raw system state into **fault classifications, engineering recommendations and fleet-wide health reports**.

The project was created from real-world engineering requirements: reducing repetitive manual investigation, improving first-line diagnosis and identifying faults remotely before engineering intervention or depot attendance is required.

### Current Capabilities

* Multi-fleet GPS and WAN diagnostics
* Dynamic GPS hardware discovery
* Automated GPS and WAN fault classification
* Fleet-aware hardware and network topology validation
* Combined GPS and WAN fleet health assessment
* Fleet health classification using HEALTHY, DEGRADED, FAULT and OFFLINE states
* Engineering action recommendations based on detected fault signatures
* Fleet-wide CSV and HTML health reporting
* Modular diagnostic architecture separating configuration, collection, classification and reporting

---

## Architecture & Diagnostic Workflow

The platform uses an inventory-driven workflow to connect to onboard systems, collect diagnostic evidence and convert it into actionable engineering information.

![Rail Network Diagnostics Architecture](docs/images/rail-diagnostics-architecture.png)

---

## Key Capabilities

### GPS Diagnostics

The platform remotely validates the health of the onboard GPS subsystem, including:

* GPS process status
* MQTT service status
* GPS broadcast process status
* Network/VLAN interface presence
* GPS receiver output
* NMEA sentence availability
* GPS fix status
* Satellite visibility
* UTC timestamp validity
* Active GPS device discovery

Collected evidence is assessed by the diagnostic engine to distinguish between healthy operation, service-level warnings, network issues and GPS receiver/fix faults.

### WAN & Modem Diagnostics

WAN diagnostics collect and analyse modem and network state from onboard communication systems.

Current checks include:

* Modem hardware discovery
* Sierra Wireless and Huawei modem detection
* Modem firmware collection
* Serving cell identification
* WAN interface detection
* WAN availability
* WAN latency (RTT)
* Cellular technology and band
* Network registration state
* Attach state
* DHCP/interface state
* Carrier Aggregation status
* Automated WAN fault classification

Rather than reporting raw modem values alone, the platform correlates observed state to produce a likely diagnosis and recommended engineering action.

### Fleet Automation & Reporting

Inventory-driven scanning allows diagnostics to be performed across multiple trains without manually connecting to each system individually.

The platform can:

* Read fleet inventory definitions
* Connect remotely to multiple onboard systems
* Automatically apply fleet-specific hardware profiles
* Run standalone GPS and WAN diagnostics
* Run combined GPS and WAN fleet health scans
* Identify offline or unreachable units
* Classify GPS and WAN faults
* Calculate an overall fleet health state
* Record supporting diagnostic evidence
* Generate fleet-wide CSV reports
* Generate standalone and combined HTML fleet health reports

This provides engineers with both a high-level view of fleet health and the underlying diagnostic evidence required for deeper investigation. Individual subsystem diagnoses remain available even when an overall combined health state is assigned.

---

## Engineering Challenges & Solutions

### Dynamic GPS Device Discovery

One of the early assumptions in the project was that GPS receivers could be accessed using fixed Linux serial-device paths.

Testing across supported fleets showed that USB serial devices are **dynamically assigned during system boot**, meaning a GPS receiver could move between device paths after a reboot.

For example:

```text
/dev/ttyUSB<n>
```

Hardcoding a serial device therefore created unreliable diagnostics.

The platform was redesigned to discover the active GPS receiver dynamically by:

1. Locating the running GPS process.
2. Inspecting its open file descriptors to identify the serial device in use.
3. Falling back to scanning available USB serial devices when required.
4. Validating candidate devices by detecting genuine NMEA data streams.

This allows the same diagnostic logic to continue operating when Linux device enumeration changes between boots.

### Evidence-Based WAN Fault Classification

The WAN functionality initially focused on collecting basic modem and interface status.

Further investigation of the onboard Linux environment identified detailed modem runtime information exposed through the unified communications subsystem.

By analysing combinations of:

* modem detection
* network registration
* attach state
* interface creation
* DHCP state
* cellular technology
* carrier aggregation
* WAN latency
* observed runtime state

the platform evolved from simple status collection into an **evidence-based fault classification engine**.

This allows conditions such as registration failure, DHCP failure, session establishment problems and abnormal WAN latency to be distinguished from one another and paired with appropriate engineering actions.

### Mixed-Fleet Hardware & Topology Support

The supported rail fleets do not share identical hardware or network configurations.

Differences include:

* Hardware generation
* GPS device behaviour
* modem types
* number of active WAN interfaces
* expected WAN topology

A single fixed diagnostic profile would therefore generate false failures.

Fleet-aware profiles were introduced so that the diagnostic engine understands which hardware and interfaces are expected for each fleet.

This allows one diagnostic platform to assess multiple fleets while accounting for legitimate differences in system architecture.

The fleet configuration also separates WAN interfaces that are available for diagnostic collection from those expected to be operational.

For example, a supported fleet may expose multiple WAN runtime slots, allowing all available interfaces to be inspected during diagnostics. Fleet configuration defines which WAN interfaces are expected to be active, while deliberately unused interfaces are excluded from normal health assessment and operator-facing reporting.

This allows the platform to retain diagnostic visibility of the underlying hardware without incorrectly treating deliberately unused WAN interfaces as faults.

### Combined Fleet Health Assessment

GPS and WAN diagnostics were initially developed as independent diagnostic workflows. While useful individually, this required engineers to interpret multiple results when determining the overall health of a train.

Phase 7 introduced a combined fleet health model that evaluates GPS and WAN diagnostics together and assigns one overall operational state:

* **HEALTHY** — GPS and all expected active WAN connections are operational.
* **DEGRADED** — the system remains operational, but a service warning or partial WAN failure has been detected.
* **FAULT** — a GPS fault or loss of all expected active WAN connectivity has been detected.
* **OFFLINE** — the onboard system could not be reached remotely.

WAN interfaces intentionally disabled by fleet design are excluded from the active-WAN health calculation.

The combined scan retains the individual GPS and WAN diagnoses rather than replacing them with a single score. This means the overall state provides a quick fleet-level indication while the underlying evidence remains available for engineering investigation.

Combined results are presented in an HTML fleet health report containing the overall train state, GPS assessment and individual WAN interface results.

---

## Example Diagnostic Output

```text
GPS Diagnostic Report - EXAMPLE

SERVICE CHECKS
----------------------------------------
GPS Device Present   : True
GPS Device Used      : /dev/ttyUSB<n>
GPS Process Running  : True
MQTT Running         : True
Broadcast Running    : False
VLAN105 Present      : True

GPS STATUS
----------------------------------------
GPRMC Status         : A
UTC Time             : <example UTC>
Satellites Visible   : <example count>

ASSESSMENT
----------------------------------------
Diagnosis            : GPS operational with service warning
Likely Cause         : GPS receiver has a valid fix, but the GPS broadcast process is not running.
```

The objective is not simply to expose raw system data, but to provide an engineer with enough context to understand **what has failed, the evidence supporting that diagnosis and the appropriate next action**.

---

## Fault Classification Engine

The diagnostic engine evaluates collected system state against known and observed fault signatures.

### GPS Fault Classifications

Current classifications include:

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

Current classifications include:

* WAN Operational
* WAN Disabled by Fleet Design
* Modem Not Detected
* Network Registration Failure (NO PLMN)
* WAN Attach / Interface Bring-Up Failure
* DHCP Negotiation Failure (`dhcp_cal`)
* DHCP Lease Acquisition Failure (No Lease)
* LTE Session Establishment Failure
* High Latency WAN Failure (60000ms RTT)
* WAN Session Recovery Failure
* Offline / Connection Timeout

Each diagnosis can include recommended engineering actions and escalation guidance based on the observed system state.

The fault library continues to evolve as diagnostic behaviour is compared against verified engineering outcomes.

---

## Supported Fleets

### Fleet & Hardware Profiles

| Fleet | Hardware Profile | GPS Device Method |
| -------- | ---------------- | ----------------- |
| Fleet A | Hardware Profile A | Fixed device mapping |
| Fleet B | Hardware Profile B | Automatic device discovery |
| Fleet C | Hardware Profile C | Automatic device discovery |
| Fleet D | Hardware Profile D | Automatic device discovery |

### WAN Topologies

| Fleet | Expected Active WANs |
| ----- | -------------------- |
| Fleet A | Fleet-defined |
| Fleet B | Fleet-defined |
| Fleet C | Fleet-defined |
| Fleet D | Fleet-defined |

### Modem Support

Current diagnostic logic supports hardware including:

**Sierra Wireless**

* MC7455
* 7710
* 8801

**Huawei**

* Huawei mobile modems

---

## Project Evolution

The platform has developed iteratively in response to real diagnostic requirements and findings from operational systems.

### Phase 1 — GPS Diagnostics

Developed remote GPS health checking, service validation and initial fault assessment.

### Phase 2 — Multi-Fleet & Dynamic Hardware Support

Extended diagnostics across differing hardware platforms and introduced automatic GPS device discovery after identifying dynamic Linux USB enumeration.

### Phase 3 — Fleet Automation

Introduced inventory-driven scanning, automated remote diagnostics, offline-unit detection and fleet-wide CSV reporting.

### Phase 4 — WAN & Modem Diagnostics

Expanded the platform beyond GPS to collect modem, cellular network, interface and WAN health information.

### Phase 5 — Fault Classification

Developed evidence-based GPS and WAN fault signatures with automated diagnoses and recommended engineering actions.

### Phase 6 — Fleet Health Reporting

Introduced mixed-fleet WAN topology awareness, hardware-specific profiles and HTML fleet health reporting.

### Phase 7 — Modular Architecture & Combined Fleet Health

Refactored the original diagnostic application into a modular architecture while preserving the existing GPS and WAN diagnostic workflows.

Fleet configuration, SSH communication, GPS analysis, WAN analysis and reporting responsibilities were separated into dedicated modules:

* `config/fleet_profiles.py` — fleet-specific hardware and WAN topology definitions
* `ssh_client.py` — reusable SSH communication
* `diagnostics/gps.py` — GPS parsing and fault classification
* `diagnostics/wan.py` — WAN parsing and fault classification
* `diagnostics/health.py` — combined fleet health classification
* `reporting/reports.py` — CSV and HTML report generation
* `gps_diag.py` — application workflow and diagnostic orchestration

A combined GPS and WAN fleet scan was then introduced to assess both subsystems during a single remote diagnostic run.

The combined health engine classifies each train as:

* **HEALTHY**
* **DEGRADED**
* **FAULT**
* **OFFLINE**

The severity model deliberately retains the underlying GPS and individual WAN diagnoses rather than reducing diagnostic evidence to an arbitrary numeric health score.

Phase 7 also introduced a combined HTML fleet health report, providing a fleet-level summary alongside individual GPS and WAN diagnostic results.

### Current Direction — Diagnostic Platform Evolution

Current development is focused on extending the platform toward historical analytics, scheduled diagnostics, wider network health assessment and increasingly automated fault response.

---

## Project Structure

```text
rail-network-diagnostics/
│
├── config/
│   ├── __init__.py
│   └── fleet_profiles.py
│
├── diagnostics/
│   ├── __init__.py
│   ├── gps.py
│   ├── wan.py
│   └── health.py
│
├── reporting/
│   ├── __init__.py
│   └── reports.py
│
├── docs/
│   ├── diagrams/
│   │   └── rail-diagnostics-architecture.drawio
│   ├── images/
│   │   └── rail-diagnostics-architecture.png
│   ├── FAULT_LIBRARY.md
│   └── project_notes.md
│
├── inventory/
│   └── example_inventory.csv
│
├── reports/
│
├── sample_data/
│   ├── healthy_gprmc.txt
│   ├── healthy_nmea.txt
│   ├── faulty_gprmc.txt
│   └── faulty_nmea.txt
│
├── gps_diag.py
├── ssh_client.py
├── ssh_test.py
├── requirements.txt
├── README.md
└── .gitignore
```

---

## Technologies

* **Python** — modular diagnostic logic, fault classification, automation and reporting
* **Paramiko / SSH** — secure remote system interrogation
* **Linux** — process, device, interface and service diagnostics
* **TCP/IP & VLANs** — onboard network health assessment
* **Cellular WAN** — modem, registration, attach and session diagnostics
* **NMEA** — GPS receiver and fix-state analysis
* **CSV / HTML** — fleet health reporting and evidence collection
* **Git / GitHub** — source control and project management

---

## Repository Security & Data Handling

This public repository is designed to demonstrate the diagnostic platform without exposing operational fleet data or credentials.

* Operational inventory files are excluded from version control.
* A sanitised `example_inventory.csv` demonstrates the expected inventory structure.
* SSH keys and environment files are excluded through `.gitignore`.
* Generated diagnostic reports are excluded from source control.
* Example and sample diagnostic data is used where appropriate for public documentation.

Operational credentials, private addressing information and fleet-specific inventory data are not required to understand or review the project.

---

## Future Development

### Diagnostics

* Access point health diagnostics
* Network switch diagnostics
* CCTV service monitoring
* Additional end-to-end network health checks

### Automation & Analytics

* Historical GPS and WAN fault trending
* Scheduled fleet health scans
* Automated remediation workflows
* Reporting notifications
* Ticketing integration

### Platform

* Database-backed diagnostic history
* Interactive web dashboard
* Cloud-hosted deployment
* Fleet health analytics

The longer-term objective is to evolve the project from a remote diagnostic tool into a broader **network health, fault analysis and automated recovery platform**.

---

## Author

**Kevin Roper**

Infrastructure Engineer | AWS Certified | Cloud & Automation

[GitHub Profile](https://github.com/K-Roper-Projects)
