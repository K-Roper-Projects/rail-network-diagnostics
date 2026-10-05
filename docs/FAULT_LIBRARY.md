# Diagnostic Fault Library

This document records known GPS, WAN and modem fault signatures identified through development and live diagnostic testing of the Rail Network Diagnostics platform.

Its purpose is to provide a consistent evidence-based reference for automated fault classification, first-line diagnosis and engineering escalation.

The fault library should evolve alongside the diagnostic engine as new behaviours are observed and validated.

---

# 1. GPS Fault Signatures

## GPS Operational

### Signature

```text
GPS device detected
GPS process running
NMEA output present
GPRMC Status = A
Valid UTC time present
Satellites visible > 0
MQTT process running
GPS broadcast process running
VLAN105 present
```

### Diagnosis

GPS operational.

### Recommended Action

No action required.

---

## GPS Operational with Service Warning

### Signature

```text
GPRMC Status = A
Valid GPS fix present
Satellites visible > 0

AND one of:

MQTT process not running
GPS broadcast process not running
```

### Diagnosis

The GPS receiver is operational and has a valid navigation fix, but a supporting GPS service is not running correctly.

### Likely Cause

* MQTT service failure
* GPS broadcast process failure
* Service failed to start after boot
* Temporary software/process issue

### Recommended Action

* Restart the affected service where appropriate.
* Reboot the onboard system if required.
* Confirm downstream systems are receiving GPS information.
* Escalate for software investigation if the process repeatedly fails.

---

## GPS Operational with Network Warning

### Signature

```text
GPRMC Status = A
Valid GPS fix present
Satellites visible > 0
VLAN105 interface missing
```

### Diagnosis

The GPS receiver is operational, but the expected GPS network/VLAN interface is unavailable.

### Likely Cause

* VLAN configuration issue
* Network interface configuration fault
* Service/network startup problem

### Recommended Action

* Check onboard system network configuration.
* Confirm VLAN105 is configured and active.
* Confirm GPS information is reaching downstream systems.
* Escalate for network configuration investigation if persistent.

---

## GPS Device Not Detected

### Signature

```text
GPS device discovery fails
gps_device = NOT_DETECTED
```

or:

```text
GPS_DEVICE_NOT_DETECTED
```

### Diagnosis

GPS device not detected.

### Likely Cause

* GPS receiver unavailable
* Serial device mapping issue
* Receiver hardware fault
* Cabling or connection fault
* Device discovery failure

### Recommended Action

* Check GPS receiver connection.
* Check serial device mapping.
* Reboot and retest.
* If the device remains unavailable, raise an engineering ticket for receiver or cabling investigation.

---

## GPS Process Not Running

### Signature

```text
GPS device may be present
GPS process output is empty
```

### Diagnosis

GPS process not running.

### Likely Cause

* GPS service failed to start
* GPS process crashed
* Software fault

### Recommended Action

* Restart the GPS service if supported.
* Reboot the onboard system.
* If the process repeatedly fails, escalate for software/service investigation.

---

## GPS Receiver Not Outputting NMEA

### Signature

```text
GPS device detected
GPS process may be running
No recognised NMEA sentences detected
```

Expected NMEA examples include:

```text
$GPRMC
$GPGGA
$GPGSV
$GNGSA
$GLGSV
```

### Diagnosis

GPS receiver not outputting NMEA data.

### Likely Cause

* Receiver fault
* Incorrect serial device
* Serial communication fault
* GPS service holding an unexpected device
* Receiver startup problem

### Recommended Action

* Verify the active GPS device.
* Check receiver output directly.
* Reboot and retest.
* Raise an engineering ticket for receiver or antenna-path investigation if no NMEA data is present after recovery attempts.

---

## GPS Invalid Fix - No Satellites Visible

### Signature

```text
GPRMC Status = V
Satellites Visible = 0
```

UTC may also be missing.

### Diagnosis

GPS receiver does not have a valid navigation fix and cannot see satellites.

### Likely Cause

* GPS antenna fault
* Antenna cabling fault
* Poor or blocked reception
* GPS receiver fault

### Recommended Action

* Check antenna path.
* Check antenna connections and cabling.
* Check receiver health.
* Reboot and retest.
* Raise an engineering ticket if persistent.

---

## GPS Invalid Fix Despite Satellite Visibility

### Signature

```text
GPRMC Status = V
Satellites Visible > 0
```

A UTC value may still be present.

### Diagnosis

The receiver can see satellites but has not obtained a valid navigation solution.

### Likely Cause

* Receiver unable to calculate a valid fix
* Degraded antenna performance
* Receiver instability
* Temporary navigation solution loss

### Recommended Action

* Monitor for recovery.
* Reboot and retest if persistent.
* Investigate antenna and receiver performance if the fault continues.

---

## GPS Invalid Fix

### Signature

```text
GPRMC Status = V
```

and the fault does not match a more specific known signature.

### Diagnosis

GPS receiver is producing data but currently has no valid navigation fix.

### Recommended Action

* Monitor for recovery.
* Review satellite visibility and UTC information.
* Investigate receiver and antenna performance if persistent.

---

## GPS Fault - Cause Not Yet Classified

### Signature

GPS health checks indicate abnormal behaviour but the collected evidence does not match a known fault signature.

### Diagnosis

GPS fault - cause not yet classified.

### Recommended Action

Review:

* GPS process state
* GPS device discovery
* Serial device mapping
* NMEA output
* GPRMC status
* Satellite count
* MQTT state
* GPS broadcast process
* VLAN105 state

Record confirmed findings so the fault library and classification logic can be extended.

---

# 2. WAN and Modem Fault Signatures

## WAN Operational

### Signature

Operational evidence includes:

```text
Active WAN interface present
Carrier Availability / CA = 1
Normal RTT
```

Typical healthy runtime states may include:

```text
SHOW-LTE
SHOWTIME
```

### Diagnosis

WAN operational.

### Recommended Action

No action required.

### Important Classification Rule

Operational network evidence takes precedence over incomplete modem metadata.

A WAN must **not** automatically be classified as failed solely because files such as the following are missing:

```text
modem-details
modem-firmware
attach-state
registration-status
```

If an active interface exists and Carrier Availability indicates the WAN is operational, the WAN should be treated as available.

---

## WAN Disabled by Fleet Design

### Signature

The WAN number is not included in the fleet's configured `active_wans` profile.

### Diagnosis

WAN disabled by fleet design.

### Recommended Action

No action required.

This condition must not be counted as a fault.

---

## Modem Not Detected

### Signature

Typical evidence:

```text
No modem-details
No active interface
No WAN device
No load-balance interface
CA = 0
```

Runtime state may also report:

```text
NO CARD
no#card
```

### Diagnosis

Modem not detected.

### Likely Cause

* Modem hardware unavailable
* Modem seating issue
* USB/PCI device detection problem
* Hardware or cabling fault
* Modem failed to initialise

### Recommended Action

* Reboot the onboard system.
* Recheck modem detection.
* Check hardware seating and connections.
* If still unavailable, raise an engineering ticket for modem investigation or replacement.

---

## Network Registration Failure - NO PLMN

### Signature

One or more runtime values contain:

```text
NO PLMN
```

This may appear in:

```text
state
attach-state
registration-status
```

### Diagnosis

The modem is detected but has failed to register successfully with the mobile network.

### Likely Cause

* Network registration failure
* SIM issue
* Modem issue
* Poor or unavailable mobile network coverage

### Recommended Action

* Reset the WAN process.
* Monitor for successful registration.
* If NO PLMN returns after WAN restart or onboard system reboot, raise an engineering ticket for modem/SIM investigation.

---

## WAN INIT - Attach / Interface Bring-Up Failure

### Signature

Typical evidence:

```text
State = INIT
Attach State = Attempting Network Attach
Registration = Registered
No usable WAN interface
```

### Diagnosis

The modem has registered with the mobile network but has not completed data-session establishment or interface creation.

### Likely Cause

* PDP/session establishment issue
* Modem software state problem
* Interface bring-up failure
* Modem instability

### Recommended Action

* Reset the WAN process.
* Monitor for recovery.
* Reboot the onboard system if required.
* If the fault reoccurs, raise an engineering ticket for modem investigation or replacement.

---

## WAN DHCP Lease Acquisition Failure

### Signature

Runtime values include:

```text
No Lease
```

### Diagnosis

The modem has failed to obtain the required WAN DHCP lease.

### Likely Cause

* Modem session problem
* DHCP handling issue
* Sierra Wireless modem session lock
* Incomplete network/session establishment

### Recommended Action

* Reset the WAN process.
* Monitor subsequent state progression.
* Pay particular attention to progression into `dhcp_cal`.
* If recurring, investigate modem session handling and consider modem replacement.

---

## WAN DHCP Negotiation Failure

### Signature

```text
State = WAIT#DHCP
```

or:

```text
STATE_WAIT_DHCP
```

A related state may also be observed as:

```text
dhcp_cal
```

### Diagnosis

The modem has progressed through network registration but DHCP/session negotiation has not completed successfully.

### Likely Cause

* DHCP negotiation failure
* Modem session lock
* Interface/session setup problem

### Recommended Action

* Reset the WAN process.
* Monitor for recovery.
* If the fault repeatedly returns, investigate modem DHCP/session handling.
* Consider modem replacement if confirmed persistent.

---

## PDP Context / Session Error

### Signature

Runtime state, attach state or registration information contains:

```text
PDP
```

in an error or incomplete-session condition.

### Diagnosis

PDP context or cellular data-session establishment failure.

### Likely Cause

* SIM or APN configuration issue
* Mobile network session failure
* Modem session state problem
* Software/session establishment fault

### Recommended Action

* Reset the WAN process.
* Monitor session establishment.
* Check SIM/APN configuration if relevant.
* Escalate if persistent.

---

## LTE Session Establishment Incomplete

### Signature

Example:

```text
State = SHOW-LTE
Attach State = -------
CA = 0
```

The interface may be absent or incomplete.

### Diagnosis

The modem has reached an LTE state but has not completed establishment of a usable data session.

### Likely Cause

* Incomplete PDP/session establishment
* Registration/session transition failure
* Modem software state issue

### Recommended Action

* Reset the WAN process.
* Monitor for complete session establishment.
* If the fault persists, investigate registration and modem data-session behaviour.

---

## Modem Stuck During Power-On Initialisation

### Signature

State or attach state contains:

```text
Power On
```

without progressing to a healthy operational condition.

### Diagnosis

The modem has failed to progress cleanly through initialisation.

### Likely Cause

* Modem startup failure
* Driver or software initialisation problem
* Hardware instability

### Recommended Action

* Reset the WAN process.
* Reboot the onboard system if required.
* If the state repeatedly returns, raise an engineering ticket for modem investigation or replacement.

---

## WAN Attached but Failing Latency Check

### Signature

Typical evidence:

```text
State = SHOW-LTE
Interface present
RTT >= 60000 ms
```

### Diagnosis

The modem appears attached and an interface exists, but the WAN is effectively unusable.

A value of approximately `60000 ms` is treated as a failure condition rather than valid latency.

### Likely Cause

* Failed or stalled cellular data session
* Modem session lock
* Network path failure
* Modem instability

### Recommended Action

* Reset the WAN process.
* Monitor for normal RTT recovery.
* If high latency returns, raise an engineering ticket for modem investigation or replacement.

---

## WAN Unavailable - No Active Interface

### Signature

```text
No active unified interface
No WAN device
No load-balance interface
```

but available evidence is insufficient to classify the modem itself as missing.

### Diagnosis

WAN unavailable - no active interface.

### Recommended Action

* Reset the WAN process.
* Monitor interface creation.
* If the interface remains unavailable, escalate for modem/session investigation.

---

## WAN Unavailable - Cause Not Yet Classified

### Signature

The WAN is unavailable but collected evidence does not match a known fault signature.

### Diagnosis

WAN unavailable - cause not yet classified.

### Recommended Action

Review:

* Modem state
* Attach state
* Registration status
* Operator
* Cellular technology
* WAN interface
* Device mapping
* Carrier Availability
* Load-balance data
* RTT
* Modem hardware details
* Firmware

Record confirmed findings so the fault library and diagnostic engine can be extended.

---

# 3. Offline / Connectivity Conditions

## Onboard System Unreachable

### Signature

```text
CONNECTION_TIMEOUT
```

or an SSH connection failure prevents diagnostic collection.

### Diagnosis

Train or onboard system unreachable at the time of the scan.

### Important Note

This condition does **not automatically mean that the train itself is offline in service**.

Possible causes include:

* Temporary VPN reachability issue
* Onboard system changing network state
* Slow response
* Train communications unavailable
* Onboard system offline
* Routing/connectivity issue

### Recommended Action

* Retry the scan.
* If the unit repeatedly fails to respond, investigate train and onboard system connectivity.

---

# 4. Known Behaviour and Classification Principles

## Dynamic GPS Device Enumeration

On supported platforms, Linux USB serial device numbering can change after reboot.

GPS devices must therefore not be assumed to remain on a fixed `/dev/ttyUSBx` path.

The diagnostic platform identifies the active device using:

1. GPS process discovery.
2. Open file-descriptor inspection.
3. Serial-device fallback scanning.
4. NMEA validation.

---

## Operational Evidence Takes Priority

Some runtime metadata files may be absent even when a WAN is operating correctly.

The classifier should therefore favour direct operational indicators such as:

```text
Active interface
CA = 1
Usable RTT
```

over the simple absence of `modem-details` or similar metadata.

This prevents healthy WANs from being incorrectly classified as failed.

---

## Fleet-Specific WAN Expectations

The platform must evaluate WAN health against the appropriate fleet profile.

Different supported fleets may have different expected active WAN interfaces.

The diagnostic engine therefore uses the configured `active_wans` profile when determining WAN health.

Inactive WAN positions defined by fleet design must not be treated as faults.

---

# 5. Maintaining the Fault Library

A new fault signature should only be added when sufficient diagnostic evidence exists to distinguish it from existing classifications.

Where possible, record:

* Observed runtime state
* Supporting diagnostic evidence
* Confirmed root cause
* Recovery action attempted
* Outcome
* Whether the issue reoccurred

The objective is for the fault library to remain an evidence-based engineering reference rather than a list of assumptions.
