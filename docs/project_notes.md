# Project Notes

## unified_sw_airprime

Discovered state machine strings:

STATE_INIT
STATE_WAIT_DHCP
STATE_NO_PLMN
STATE_SHOW_LTE

Source:
/usr/local/bin/unified_sw_airprime

---

## WAN Runtime Database

Useful locations:

/var/local/unified/01
/var/local/unified/02
/var/local/unified/03

Contains:

- modem-details
- modem-firmware
- attach-state
- registration-status
- state
- rtt
- ifname

---

## Fleet WAN Topology

GWR 165/166
- WAN1 Active
- WAN3 Active

GWR 800/802
- WAN1 Active
- WAN2 Active

XC 170
- WAN1 Active
- WAN2 Active
- WAN3 Active

## Key Discoveries

### GPS

- 4600 CCU GPS devices are dynamically assigned.
- GPS serial devices cannot be assumed to remain fixed across reboots.
- Automatic GPS device discovery was required.

### WAN

- Modem runtime information is stored under /var/local/unified.
- Carrier Aggregation state is exposed through the unified runtime database.
- WAN availability can be determined through a combination of modem state, attach state, interface creation and CA status.

### Fleet Differences

- GWR 165/166 utilise WAN1 and WAN3.
- GWR 800/802 utilise WAN1 and WAN2.
- XC fleets utilise WAN1, WAN2 and WAN3.

## XC220/221 WAN3 Discovery

Observed on unit 220012.

WAN3 reported as "Modem not detected" by diagnostics tool.

Investigation showed:

state = SHOW-LTE
ifname = swa4
dev = swa4
ca = 1
rtt = 44

However the following files were absent:

modem-details
modem-firmware
attach-state
registration-status

Conclusion:

Missing modem-details does not necessarily indicate a failed modem.

Operational indicators such as interface presence and CA state should take precedence over modem-details when determining WAN availability.