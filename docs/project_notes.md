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
* CSV diagnostic reports
* HTML WAN fleet-health reports
* Fleet-level healthy/fault/offline summaries
* Actionable fault summaries

Current development direction is toward a combined GPS and WAN fleet-health model.

---

# 15. Future Engineering Notes

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
