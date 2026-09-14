# Project Notes

This document records engineering discoveries, platform behaviours and implementation decisions identified while developing the Rail Network Diagnostics platform.

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

Current fleet profiles:

| Fleet       | CCU / Platform | GPS Method          | Expected WANs    |
| ----------- | -------------- | ------------------- | ---------------- |
| GWR 165/166 | R3200CCU       | Fixed `/dev/ttyS1`  | WAN1, WAN3       |
| GWR 800/802 | 4600CCU        | Automatic discovery | WAN1, WAN2       |
| XC 170      | 4600CCU        | Automatic discovery | WAN1, WAN2, WAN3 |
| XC 220/221  | 4600CCU        | Automatic discovery | WAN1, WAN2, WAN3 |

Fleet-specific profiles are necessary because onboard hardware and WAN topology differ between fleets.

A single universal hardware assumption would create false diagnostic failures.

---

# 3. GPS Discoveries

## Fixed GPS Device Assumption

Initial development assumed GPS receivers could be accessed using known fixed Linux serial-device paths.

This is valid on some older R3200CCU systems where GPS is available through:

```text
/dev/ttyS1
```

Testing on 4600CCU platforms showed this assumption does not apply universally.

---

## Dynamic USB Enumeration on 4600CCU

USB serial devices on 4600CCU systems are dynamically assigned during Linux boot.

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

## XC 220/221 GPS Discovery

Investigation of XC 220/221 systems identified the running GPS process and the serial device it had opened.

Example process discovery:

```text
/usr/local/bin/gps --section "default"
python3 /gpsApp
```

Inspection of the GPS process file descriptors identified:

```text
/dev/ttyS6
```

The wider lesson remains that the diagnostic platform should discover the active device from system state rather than rely solely on assumed hardware mappings.

---

# 4. WAN Runtime Environment

Detailed modem and WAN runtime information is exposed through the unified communications subsystem.

Important runtime locations include:

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

# 5. unified_sw_airprime Observations

Investigation of the onboard `unified_sw_airprime` component revealed useful WAN state-machine terminology.

Observed strings include:

```text
STATE_INIT
STATE_WAIT_DHCP
STATE_NO_PLMN
STATE_SHOW_LTE
```

Runtime binary:

```text
/usr/local/bin/unified_sw_airprime
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

During investigation of an XC 220/221 WAN, diagnostics initially reported:

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
* Fleet topology

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

Repeated occurrence following WAN reset or CCU reboot should therefore be treated differently from a transient network-registration issue.

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

Expected WAN configuration differs by fleet.

## GWR 165/166

```text
WAN1 active
WAN2 disabled by design
WAN3 active
```

## GWR 800/802

```text
WAN1 active
WAN2 active
WAN3 disabled by design
```

## XC 170

```text
WAN1 active
WAN2 active
WAN3 active
```

## XC 220/221

```text
WAN1 active
WAN2 active
WAN3 active
```

A WAN that is intentionally unused must not be counted as a diagnostic failure.

This led to implementation of fleet-aware WAN profiles.

---

# 13. Diagnostic Design Principles

## Evidence Before Assumption

The platform should derive health from the observed operational state of the train rather than rely on assumed hardware mappings or the presence of a single file.

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

The train remains operational, but a warning or partial WAN failure has been detected.

Examples include:

* GPS operational with a service warning
* GPS operational with a network warning
* One or more expected WANs unavailable while another expected WAN remains operational

### FAULT

A GPS fault has been detected or no expected active WAN connectivity remains available.

### OFFLINE

The onboard CCU cannot be reached sufficiently to complete the combined diagnostic assessment.

An unreachable CCU is classified as `OFFLINE` rather than attempting to infer GPS or WAN failure from missing evidence.

---

## WAN Health Calculation

WAN health is calculated using only interfaces expected to be active for the selected fleet profile.

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

# 16. Application Architecture

Phase 7 refactored the original diagnostic application before introducing combined GPS and WAN health assessment.

The project had developed primarily within `gps_diag.py`, which was responsible for fleet configuration, SSH communication, GPS diagnostics, WAN diagnostics, reporting and application workflow.

As functionality increased, continuing to add features to the same script would make the diagnostic platform increasingly difficult to maintain and extend.

The application was therefore separated into dedicated modules while preserving existing diagnostic behaviour.

Current responsibilities are:

```text
config/fleet_profiles.py
    Fleet-specific hardware and WAN topology configuration

ssh_client.py
    Reusable SSH communication

diagnostics/gps.py
    GPS parsing and diagnostic classification

diagnostics/wan.py
    WAN parsing and diagnostic classification

diagnostics/health.py
    Combined GPS/WAN health classification

reporting/reports.py
    CSV and HTML report generation

gps_diag.py
    Diagnostic collection, workflow and application orchestration
```

## Collection vs Interpretation

An important architectural decision was to separate collection of diagnostic evidence from interpretation of that evidence.

Remote operations that interact directly with the onboard Linux system remain part of the collection/orchestration layer.

Examples include:

* SSH command execution
* GPS device discovery
* Process inspection
* Reading runtime files
* WAN evidence collection

Functions that interpret already-collected evidence belong in the diagnostic modules.

Examples include:

* GPRMC parsing
* Satellite parsing
* GPS fault classification
* WAN state parsing
* WAN fault classification
* Combined health classification

This separation should allow future diagnostics to be developed and tested without continually increasing the responsibilities of the main application script.

---

## Refactor Validation

The refactor was intentionally behaviour-preserving.

Existing healthy and faulty offline GPS samples were used repeatedly during development to confirm that moving functionality between modules did not alter established diagnostic results.

Validation during Phase 7 included:

* Python `py_compile` checks
* VS Code/Pylance static analysis
* Existing GPS regression samples
* Direct GPS/WAN health-classification tests
* Combined health-classification tests
* Simulated combined HTML reporting across HEALTHY, DEGRADED, FAULT and OFFLINE states

Pylance identified unresolved WAN diagnostic dependencies within `reporting/reports.py` that were not identified by `py_compile`.

This reinforced the use of both static analysis and runtime/compilation checks when validating future refactoring work.

Final live validation against operational systems is required before the Phase 7 implementation is considered fully validated.

---

# 17. Future Engineering Notes

Planned areas for future investigation include:

* Combined GPS and WAN health scanning
* Severity-based train-health states
* Access point diagnostics
* Managed switch diagnostics
* Additional onboard service monitoring
* Historical fault recurrence
* Automated remediation
* Scheduled scanning
* Ticketing integration
* Database-backed diagnostic history
* Interactive dashboarding
* Cloud-hosted execution

Significant discoveries made while implementing these features should be recorded here before they are distilled into permanent documentation or fault-classification logic.
