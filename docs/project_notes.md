# Project Notes

This document records engineering discoveries, fleet behaviours and implementation decisions identified while developing the Rail Network Diagnostics platform.

It is intended as a technical development reference rather than formal user documentation.

Confirmed fault signatures and engineering actions belong in `FAULT_LIBRARY.md`. This document records the discoveries and system behaviour that explain why the platform operates as it does.

---

# 1. Onboard System Environment

The diagnostic platform connects remotely to Linux-based onboard communication systems over SSH.

Diagnostics currently collect information relating to:

* GPS receiver operation
* GPS supporting services
* GPS network/VLAN state
* Cellular modem hardware
* WAN runtime state
* Network registration
* Cellular attach state
* WAN interfaces
* Carrier Availability
* WAN latency
* Fleet-specific network topology

---

# 2. Fleet Profiles

The platform supports multiple fleet configurations with differing onboard hardware, GPS interfaces and WAN topologies.

For the purposes of this public repository, operational fleet identities and infrastructure mappings have been anonymised.

| Profile | GPS Method          | WAN Configuration        |
| ------- | ------------------- | ------------------------ |
| Fleet A | Fixed serial device | Fleet-specific           |
| Fleet B | Automatic discovery | Fleet-specific           |
| Fleet C | Automatic discovery | Fleet-specific           |
| Fleet D | Automatic discovery | Fleet-specific           |

Fleet-specific profiles are necessary because onboard hardware and WAN topology differ between operational environments.

A single universal hardware assumption would create false diagnostic failures.

The public profiles demonstrate the configuration model used by the fleets without exposing operational fleet-to-hardware or fleet-to-network mappings.

---

# 3. GPS Discoveries

## Fixed GPS Device Assumption

Initial development assumed GPS receivers could be accessed using known fixed Linux serial-device paths.

This is valid on some older supported systems where GPS is available through:

```text
/dev/ttyS1
```

Testing on newer supported platforms showed this assumption does not apply universally.

---

## Dynamic USB Enumeration

USB serial devices on some supported onboard systems are dynamically assigned during Linux boot.

Observed GPS device paths have included:

```text
/dev/ttyUSB3
/dev/ttyUSB6
/dev/ttyUSB7
/dev/ttyUSB9
```

The device number cannot therefore be reliably hardcoded.

A reboot may cause the same GPS hardware to appear under a different `/dev/ttyUSBx` path.

---

## GPS Device Discovery Method

The diagnostic platform was changed to locate the active GPS receiver dynamically.

Current approach:

1. Locate the running GPS process.
2. Determine its process ID.
3. Inspect `/proc/<PID>/fd`.
4. Identify the serial device currently opened by the GPS process.
5. Validate the candidate device by checking for NMEA output.
6. If required, fall back to scanning available `/dev/ttyUSB*` devices.
7. Accept the device only when recognised NMEA data is detected.

This is significantly more reliable than relying on device numbering.

---

## Serial GPS Discovery

Investigation of another supported platform identified the running GPS process and the serial device it had opened.

Example process discovery:

```text
/usr/local/bin/gps --section "default"
python3 /gpsApp
```

Inspection of the GPS process file descriptors identified:

```text
/dev/ttyS6
```

Although `/dev/ttyS6` was identified during live testing, the diagnostic platform continues to discover the active GPS device from system state rather than treating the observed device path as a permanent fleet mapping.

This maintains a consistent discovery approach across supported platforms and avoids introducing fixed device assumptions where runtime discovery is available.

---

# 4. WAN Runtime Environment

Detailed modem and WAN runtime information is exposed through the onboard communications subsystem.

During development, runtime data sources were identified that expose diagnostic information for individual WAN instances.

Representative runtime locations include:

```text
/var/local/unified/01
/var/local/unified/02
/var/local/unified/03
```

These correspond to WAN instances.

Potentially useful files include:

```text
modem-details
modem-firmware
cell-id
attach-state
registration-status
state
current-operator
tech
tech-details
ifname
dev
ca
```

Load-balance information is available under:

```text
/var/local/loadbalance/wans/wan1
/var/local/loadbalance/wans/wan2
/var/local/loadbalance/wans/wan3
```

Useful load-balance fields include:

```text
interface
ca
rtt
bw
rank
```

---

# 5. WAN State-Machine Observations

Investigation of the onboard WAN management components revealed useful state-machine terminology.

Observed strings include:

```text
STATE_INIT
STATE_WAIT_DHCP
STATE_NO_PLMN
STATE_SHOW_LTE
```

These states helped identify relationships between modem initialisation, mobile-network registration, DHCP negotiation and LTE session establishment.

This investigation contributed directly to development of the WAN fault-classification logic.

---

# 6. WAN Availability Discovery

Initial WAN diagnostics relied heavily on modem metadata such as:

```text
modem-details
modem-firmware
attach-state
registration-status
```

Further live testing showed this was not reliable enough on its own.

---

## Missing Modem Metadata Does Not Always Mean Modem Failure

During investigation of a WAN on one supported platform, diagnostics initially reported:

```text
Modem not detected
```

because several unified metadata files were absent.

Further investigation showed operational evidence including:

```text
state = SHOW-LTE
interface present
device present
ca = 1
normal RTT
```

Despite the missing metadata, the WAN was operating correctly.

### Conclusion

Missing `modem-details` must not automatically be treated as modem failure.

Operational indicators should take priority.

Important healthy indicators include:

```text
Active WAN interface
Carrier Availability = 1
Usable RTT
```

The WAN classification logic was updated accordingly.

---

# 7. Carrier Availability

Carrier Availability (`ca`) is a useful indicator of whether a WAN is available for load balancing.

Typical interpretation:

```text
ca = 1
WAN available
```

```text
ca = 0
WAN unavailable or not currently usable
```

CA should not be assessed in isolation, but it provides strong operational evidence when combined with interface and RTT information.

---

# 8. WAN Latency Behaviour

WAN RTT is exposed through the load-balance runtime information.

Normal RTT represents a usable WAN path.

A value around:

```text
60000 ms
```

has been observed as a failure condition rather than genuine network latency.

### Classification Decision

RTT values greater than or equal to `60000 ms` are treated as a failed latency check even if an interface temporarily appears present.

This prevents unusable WAN sessions from being classified as healthy.

---

# 9. WAN State Findings

Observed WAN fault states have included:

```text
INIT
NO PLMN
NO CARD
Power On
No Lease
dhcp_cal
WAIT#DHCP
SHOW-LTE
SHOWTIME
```

These states represent different stages or failures within modem initialisation, mobile-network registration, attach, DHCP and data-session establishment.

The diagnostic engine therefore classifies faults using combinations of evidence rather than relying on a single state value.

Relevant evidence includes:

* Modem detection
* Modem state
* Registration status
* Attach state
* Interface presence
* WAN device
* Carrier Availability
* RTT
* Cellular technology
* Fleet-specific WAN expectations

---

# 10. DHCP / Session Behaviour

Testing identified WAN conditions where a modem progresses through network registration but fails during DHCP or session establishment.

Observed examples include:

```text
No Lease
WAIT#DHCP
dhcp_cal
```

These conditions may indicate a modem session or DHCP state-machine problem rather than a simple mobile-network registration failure.

Repeated occurrence following WAN reset or onboard system reboot should therefore be treated differently from a transient network-registration issue.

---

# 11. NO PLMN Behaviour

`NO PLMN` indicates failure to register successfully with a Public Land Mobile Network.

It may appear within:

```text
state
attach-state
registration-status
```

This condition is distinct from situations where the modem is already registered but subsequently fails during attach or DHCP.

Maintaining that distinction is important because the likely cause and engineering action differ.

---

# 12. Fleet WAN Topology

Expected WAN configuration differs between supported fleets.

The diagnostic platform therefore separates WAN interfaces that are available for diagnostic collection from those expected to be operational.

## Example Multi-WAN Platform

A representative multi-WAN configuration may expose four runtime WAN slots while only a subset are expected to participate in normal operation.

For example:

```text
WAN1 active
WAN2 disabled by design
WAN3 active
WAN4 disabled by design
```

The platform represents this distinction using two configuration values:

- `wan_slots` – WAN interfaces available for diagnostic collection.
- `active_wans` – WAN interfaces expected to be operational and included in health assessment.

This allows diagnostic data to be collected from interfaces that exist within the underlying platform without incorrectly treating deliberately unused interfaces as faults.

## Dynamic WAN Collection

The WAN diagnostic collector gathers data dynamically using the configured `wan_slots` rather than assuming that every supported platform exposes the same number of WAN interfaces.

For the representative four-slot configuration:

- WAN1-WAN4 are available for diagnostic collection.
- Only the configured `active_wans` are included in normal operator-facing WAN output.
- Interfaces disabled by design do not affect fleet health classification.
- Combined Fleet Health reporting displays only the WAN interfaces expected to be operational.

Other supported profiles may expose different numbers of WAN slots and different `active_wans` configurations.

This allows the same diagnostic engine to support differing onboard network architectures without embedding those assumptions throughout the application.

## Live Validation

The separation between `wan_slots` and `active_wans` was validated against an operational fleet.

Live testing confirmed that the diagnostic collector could inspect all configured WAN slots while operator-facing output remained limited to the interfaces expected to be active.

The Combined Fleet Health Scan was also completed across the operational inventory, with deliberately unused WAN interfaces correctly excluded from health classification and reporting.

This validated the separation between physical/runtime WAN availability (`wan_slots`) and expected operational WAN configuration (`active_wans`).

A WAN that is intentionally unused must not be counted as a diagnostic failure.

This led to implementation of fleet-aware WAN profiles.

---

# 13. Diagnostic Design Principles

## Evidence Before Assumption

The platform should derive health from the observed operational state of the onboard system rather than rely on assumed hardware mappings or the presence of a single file.

Examples:

* GPS device paths are discovered rather than assumed.
* Missing modem metadata does not automatically mean a failed modem.
* WAN availability is determined using interface, CA and RTT evidence.
* Expected WAN topology comes from the fleet profile.

---

## Combine Multiple Signals

Where possible, diagnoses should use multiple pieces of supporting evidence.

For WAN diagnostics this includes:

```text
modem state
registration state
attach state
interface state
carrier availability
RTT
```

For GPS diagnostics this includes:

```text
device discovery
process state
NMEA output
GPRMC status
satellite visibility
UTC
supporting services
network interface state
```

This reduces false classifications.

---

## Preserve Unknown States

If collected evidence does not confidently match a known fault signature, the platform should return:

```text
cause not yet classified
```

rather than force the condition into an incorrect diagnosis.

The unknown state can then be investigated and, if confirmed, incorporated into the fault library.

---

# 14. Reporting

The platform currently supports:

* Individual GPS diagnostic output
* Fleet GPS scans
* Individual WAN diagnostics
* Fleet WAN scans
* Combined GPS and WAN fleet-health scans
* CSV diagnostic reports
* HTML WAN fleet-health reports
* Combined GPS and WAN HTML fleet-health reports
* Fleet-level healthy/degraded/fault/offline summaries
* Actionable fault summaries

Combined reporting retains the underlying GPS and individual WAN diagnoses alongside the overall train-health state.

This allows the overall state to provide a quick fleet-level indication without removing the diagnostic evidence required for engineering investigation.

Generated CSV and HTML reports are excluded from source control.

---

# 15. Combined Fleet Health

Phase 7 introduced a combined health model that evaluates GPS and WAN health together during a single fleet scan.

The combined health model uses four explicit states:

```text
HEALTHY
DEGRADED
FAULT
OFFLINE
```

## Health State Interpretation

### HEALTHY

GPS is healthy and all expected active WAN interfaces are available.

### DEGRADED

The onboard system remains operational, but a warning or partial WAN failure has been detected.

Examples include:

* GPS operational with a service warning
* GPS operational with a network warning
* One or more expected WANs unavailable while another expected WAN remains operational

### FAULT

A GPS fault has been detected or no expected active WAN connectivity remains available.

### OFFLINE

The onboard system cannot be reached sufficiently to complete the combined diagnostic assessment.

An unreachable onboard system is classified as `OFFLINE` rather than attempting to infer GPS or WAN failure from missing evidence.

---

## WAN Health Calculation

WAN health is calculated using only interfaces expected to be active for the selected platform profile.

Current logic:

```text
All expected active WANs available
    -> HEALTHY

At least one expected active WAN available, but not all
    -> DEGRADED

No expected active WANs available
    -> FAULT
```

WAN interfaces disabled by fleet design are excluded from the calculation.

This is important because loss of a single WAN does not necessarily mean the onboard communications system has completely failed when another cellular path remains operational.

---

## Combined Health Decision

The most severe meaningful subsystem condition determines the combined result.

A numeric health percentage was deliberately avoided.

A percentage could imply a level of precision that does not exist and could hide the operational importance of an individual failure.

For example, one failed WAN on a three-WAN platform does not mean that the train is simply "66% healthy".

The explicit severity states provide a clearer operational interpretation while the individual GPS and WAN results retain the evidence behind the classification.

---

## Offline Handling

The combined scan retries an SSH connection following a connection timeout.

If communication remains unavailable after retry, the train is classified as:

```text
OFFLINE
```

rather than assigning a GPS or WAN fault without supporting evidence.

One condition remains for live operational validation:

If GPS collection succeeds but SSH connectivity is subsequently lost during WAN collection, the current implementation classifies the train as `OFFLINE`.

Live testing will determine whether this remains the most useful classification or whether an interrupted/incomplete diagnostic state should be distinguished in future.

---

## 16. Phase 7 – Combined Fleet Health Validation

Phase 7 introduced the Combined Fleet Health Scan, bringing GPS and WAN diagnostics together into a single fleet-level health assessment.

The objective was to move the project beyond individual GPS and WAN diagnostic functions and provide a single operational view of each train, suitable for identifying healthy units, degraded services, confirmed faults and units that cannot currently be reached.

### 16.1 Combined Health Workflow

The Combined Fleet Health Scan performs the following workflow for each train in the selected inventory profile:

1. Loads the train identifier and target address from the selected inventory.
2. Connects to the onboard system using SSH.
3. Collects GPS diagnostic data using the fleet-specific GPS configuration.
4. Collects WAN diagnostic data using the fleet-specific WAN configuration.
5. Classifies the GPS state.
6. Classifies each relevant WAN state.
7. Passes the GPS and WAN results to the combined health engine.
8. Assigns an overall train health state.
9. Adds the result to the combined fleet report.

The combined health engine uses four overall states:

- `HEALTHY` – GPS and expected WAN services are operating normally.
- `DEGRADED` – The train remains operational, but one or more monitored services are not in their expected state.
- `FAULT` – A confirmed diagnostic fault has been identified.
- `OFFLINE` – The onboard system could not be reached or the required diagnostic data could not be collected due to a connection timeout.

This provides a higher-level operational view while retaining the detailed GPS and WAN diagnoses underneath the overall state.

### 16.2 Fleet-Specific Configuration

Fleet behaviour is defined through `config/fleet_profiles.py`.

This allows the diagnostic logic to account for differences between onboard hardware, GPS interfaces and WAN configurations without embedding fleet-specific behaviour throughout the main application.

For the purposes of the public repository, operational fleet identities and their associated hardware mappings are anonymised.

The configuration model supports four representative profiles:

- Fleet A
- Fleet B
- Fleet C
- Fleet D

Fleet-specific configuration can define:

- Whether GPS uses a fixed serial device or automatic device discovery.
- Which WAN slots are available for diagnostic collection.
- Which WAN interfaces are expected to be operational.
- Which interfaces should contribute to health classification and operator-facing reporting.

Observed GPS device paths are retained as engineering findings where useful, but are not treated as permanent fleet mappings.

This separation allows the diagnostic engine to support differing onboard architectures while keeping operational configuration separate from the core diagnostic logic.

### 16.3 Fleet-Aware WAN Configuration

Live validation identified an important distinction between WAN interfaces that are available for diagnostic collection and WAN interfaces that are operationally expected for a particular fleet.

The configuration model therefore separates:

- `wan_slots` – WAN interfaces available to the diagnostic collector.
- `active_wans` – WAN interfaces expected to participate in normal operation.

This allows diagnostic data to be collected from all configured WAN slots while limiting operator-facing reporting and combined health assessment to the interfaces expected to be active.

Interfaces that are deliberately unused do not incorrectly degrade the overall health state.

This preserves diagnostic visibility of the underlying WAN configuration while allowing the same diagnostic engine to support platforms with different network topologies.

### 16.4 Timeout Handling

Connection failures are handled explicitly by the combined health workflow.

Examples include:

- `GPS CONNECTION TIMEOUT`
- `WAN CONNECTION TIMEOUT`

Where the onboard system cannot be reached and diagnostic collection cannot be completed, the overall train state is classified as:

`OFFLINE`

This separates connectivity failures from confirmed GPS or WAN faults and prevents an unreachable train from being incorrectly reported as a diagnostic hardware or service failure.

### 16.5 Combined HTML Reporting

Phase 7 introduced combined HTML reporting through:

`generate_combined_html_report()`

The report provides a fleet-level summary containing:

- Train ID
- IP address
- Overall health state
- GPS state and diagnosis
- WAN state and diagnosis
- Per-WAN diagnostic information

The HTML output is intended to provide a quick operational overview while still exposing enough diagnostic information to support further investigation.

An initial combined health report was shared with operational support users for feedback.

Feedback was positive, confirming that the report and diagnostic capability would be useful for day-to-day fault investigation.

### 16.6 Live Fleet Validation

Phase 7 was live validated against an operational fleet.

The full Combined Fleet Health Scan completed successfully across the selected inventory.

Validation confirmed that:

- Fleet inventory processing operates correctly.
- Live SSH diagnostic collection operates correctly.
- GPS results are collected and classified correctly.
- WAN results are collected and classified correctly.
- Fleet-specific WAN expectations are respected.
- Interfaces disabled by design do not incorrectly affect health classification.
- Combined health states are generated correctly.
- Combined HTML reporting completes successfully.
- The resulting report provides a usable fleet-level operational view.

The successful fleet scan completed the live validation requirement for Phase 7.

### 16.7 Operational Deployment Considerations

Following feedback from operational support users, a future development requirement is to make the diagnostic platform accessible without requiring users to run the Python application manually from the command line.

Any future interface must preserve secure individual authentication and avoid introducing shared infrastructure credentials.

Potential future development includes:

- A simple local web interface for launching fleet scans.
- Fleet selection from the user interface.
- Secure user authentication and access control.
- Display of scan progress and completion status.
- Direct access to generated HTML reports.
- Local deployment to avoid unnecessary cloud hosting costs.
- Packaging the application so that installation and operation require minimal technical setup.

This would retain the existing diagnostic engine while placing a simpler operational interface in front of it.

### 16.8 Phase 7 Outcome

Phase 7 successfully moved the project from separate diagnostic functions toward a structured fleet health platform.

The project now contains:

- Modular GPS diagnostic logic.
- Modular WAN diagnostic logic.
- Centralised fleet configuration.
- Reusable SSH connectivity.
- Reusable reporting functions.
- Combined GPS and WAN health assessment.
- Fleet-specific service expectations.
- Explicit timeout and offline handling.
- Combined HTML fleet reporting.
- Successful live fleet validation.

The Combined Fleet Health Scan has also received positive initial feedback from its intended operational users.

Phase 7 is therefore considered development complete and live validated.

Further work will focus on operational accessibility, automation, historical analysis and continued expansion of fleet support.

---

# 17. Future Engineering Notes

With Phase 7 complete, future development can build on the combined fleet health platform rather than adding further isolated diagnostic functions.

Planned areas for future investigation include:

* Access point diagnostics
* Managed switch diagnostics
* Additional onboard service monitoring
* Historical fault recurrence and trend analysis
* Database-backed diagnostic history
* Scheduled and automated fleet scanning
* Automated remediation where appropriate and safe
* Ticketing and Service Desk integration
* Interactive dashboarding
* Operational web interface for Service Desk users
* Continued expansion and validation across supported fleets
* Telemetry discovery, including investigation of existing MQTT/Mosquitto services and data flows
* Fleet simulator development for safe offline testing of diagnostic and telemetry behaviour
* Investigation of real-time fleet status ingestion as a foundation for a future FleetManager-style operational view
* Evaluation of local and cloud-hosted deployment options as operational requirements develop

The immediate development priority is to understand the telemetry already produced by the onboard systems and determine how that information can complement the existing SSH-based diagnostic workflow.

SSH diagnostics should remain the authoritative method for targeted live investigation, while telemetry could provide continuous fleet visibility, historical data and automated identification of units requiring deeper diagnostic checks.

Longer term, these capabilities could allow the platform to evolve from an engineer-triggered diagnostic tool into a broader fleet monitoring and diagnostics platform, while retaining the evidence-based diagnostic approach developed throughout the project.
