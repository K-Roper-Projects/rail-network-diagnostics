# Fault Library

## GPS Faults

### GPS invalid fix - no satellites visible

Signature:
- GPRMC Status = V
- UTC Missing
- Satellites = 0

Likely Cause:
- GPS antenna fault
- GPS reception issue
- GPS receiver fault

Recommended Action:
- Check antenna path
- Check receiver
- Reboot and retest

---

### GPS invalid fix despite satellite visibility

Signature:
- GPRMC Status = V
- UTC Present
- Satellites > 0

Likely Cause:
- Receiver unable to calculate navigation solution
- Antenna degradation
- Receiver fault

Recommended Action:
- Monitor
- Reboot and retest
- Investigate receiver performance

---

## WAN Faults

### NO PLMN

Signature:
- State = NO PLMN

Likely Cause:
- Network registration failure

Recommended Action:
- Restart WAN process
- Investigate SIM/modem if persistent

---

### No Lease

Signature:
- State = INIT
- Other = No Lease

Likely Cause:
- DHCP lease acquisition failure

Recommended Action:
- Restart WAN process
- Monitor for dhcp_cal progression

# WAN Fault Library

This document records known WAN and modem fault signatures identified through live fleet diagnostics.

The purpose of this library is to support consistent first-line diagnosis, reduce unnecessary depot visits, and provide evidence-based escalation guidance for Field Service attendance.

---

## Healthy WAN State

### Signature

```text
State: SHOW-LTE / SHOWTIME
Attach State: Stage 2 connection achieved - PDP context active
CA State: 1
Interface: Present
RTT: Normal

Diagnosis: WAN operational.
Recommended Action: No action required.



### INIT / NO PLMN
State: INIT
Attach State: NO PLMN
Registration: Not registered / searching / unavailable
CA State: 0
Interface: Blank

Diagnosis: Network registration failure.
The modem is detected but has not successfully registered with the mobile network.
Recommended Action: Reset WAN process and monitor.
If the fault reoccurs after WAN process restart or CCU reboot, raise an FSE ticket for modem or SIM investigation.


### INIT / Attempting Network Attach
State: INIT
Attach State: Attempting network attach
Registration: Registered on Home Network
CA State: 0
Interface: Blank

Diagnosis: WAN attach/interface bring-up failure.
The modem has registered to the mobile network but has not completed PDP attach or interface creation.
Recommended Action: Reset WAN process and monitor.
If the fault reoccurs after WAN process restart or CCU reboot, raise an FSE ticket for modem replacement investigation.


### NO CARD / Modem Not Detected
State: no#card / NO CARD
Modem Details: Blank or 0000:0000
CA State: 0
Interface: Blank

Diagnosis: Modem not detected.
The CCU is not detecting the modem correctly.
Recommended Action: Reboot CCU and recheck modem detection.
If the modem is still not detected, raise an FSE ticket to inspect modem seating, cabling, or replace the modem.


### WAIT#DHCP
State: WAIT#DHCP
CA State: 0
Interface: Present or partially created
IP/Gateway: Missing or incomplete

Diagnosis: WAN DHCP negotiation failure.
The modem appears to have progressed through registration but has not completed DHCP/session setup.
Recommended Action: Reset WAN process and monitor.
If DHCP failure reoccurs, investigate modem DHCP/session handling and consider modem replacement.


### SHOW-LTE / 60000ms RTT
State: SHOW-LTE
Attach State: Stage 2 connection achieved or similar
RTT: 60000 ms
CA State: 0 or unavailable
Interface: Present

Diagnosis: WAN attached but failing latency check.
The modem is detected and appears attached, but the WAN is effectively unusable.
Recommended Action: Reset WAN process and monitor.
If high latency returns, raise an FSE ticket for modem investigation or replacement.


### SHOW-LTE / ------
State: SHOW-LTE
Attach State: -------
CA State: 0
Interface: May be blank or incomplete
Traffic: Limited or unavailable

Diagnosis: LTE session establishment incomplete.
The modem has reached LTE state but has not completed a clean usable data session.
Recommended Action: Reset WAN process and monitor.
If the fault reoccurs, investigate modem registration and data session establishment.


### SHOW-LTE / Power On
State: SHOW-LTE
Attach State: Power On
CA State: 0
Traffic: None or limited

Diagnosis: WAN session not fully established after reset.
The modem has not returned to a healthy attached state after recovery action.
Recommended Action: Monitor briefly after reset.
If the WAN remains in Power On state after WAN reset or CCU reboot, escalate for modem investigation.


### Offline / Connection Timeout
SSH Result: CONNECTION_TIMEOUT
No WAN data collected

Diagnosis:Train or CCU unreachable at time of scan.
This does not automatically mean the train is offline in service. It may be temporarily slow to respond, changing network state, or unreachable via VPN at the time of scan.
Recommended Action: Retry scan.
If the unit repeatedly fails to respond, investigate train connectivity or CCU reachability.

| Train ID | Fleet       | WAN  | Fault Signature                  | Action Taken             | Outcome                                        |
| -------- | ----------- | ---- | -------------------------------- | ------------------------ | ---------------------------------------------- |
| 165122   | GWR 165/166 | WAN1 | INIT / Attempting network attach | WAN reset attempted      | Fault persisted, modem replacement recommended |
| 800014   | GWR 800/802 | WAN1 | SHOW-LTE / Power On              | WAN reset x2, CCU reboot | Fault persisted, FSE investigation required    |

Fault family: Sierra Wireless DHCP/session lock
Observed modem: Sierra Wireless MC7455
State progression: INIT / No Lease → INIT - dhcp_cal
Likely cause: Modem session/DHCP process stuck
Recommended action: Reset WAN process and monitor
Escalation: If recurring, raise for modem investigation/replacement