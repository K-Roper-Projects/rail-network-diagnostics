import re

def parse_gprmc(line):
    line = line.strip()

    if not line.startswith("$GPRMC"):
        return {
            "valid_sentence": False,
            "utc_time": None,
            "status": "UNKNOWN",
            "healthy": False,
            "reason": "Not a valid GPRMC sentence",
        }

    parts = line.split(",")

    if len(parts) < 3:
        return {
            "valid_sentence": False,
            "utc_time": None,
            "status": "UNKNOWN",
            "healthy": False,
            "reason": "Incomplete GPRMC sentence",
        }

    utc_time = parts[1]
    status = parts[2]

    if status == "A":
        reason = "Valid active GPS fix"
        healthy = True
    elif status == "V":
        reason = "Invalid GPS fix"
        healthy = False
    else:
        reason = "Unknown GPS fix status"
        healthy = False

    return {
        "valid_sentence": True,
        "utc_time": utc_time if utc_time else "Missing",
        "status": status,
        "healthy": healthy,
        "reason": reason,
    }
    
def parse_satellites(nmea_text):
    match = re.search(r"\$GPGSV,\d+,\d+,(\d+)", nmea_text)

    if not match:
        return None

    return int(match.group(1))

def contains_nmea(text):
    return any(
        sentence in text
        for sentence in [
            "$GPRMC",
            "$GPGGA",
            "$GPGSV",
            "$GNGSA",
            "$GLGSV",
        ]
    )

def get_gps_recommendation(results, satellites):
    gprmc = parse_gprmc(results.get("gprmc", ""))
    gps_device = results.get("gps_device", "")
    nmea = results.get("nmea", "")
    tty = results.get("tty", "")
    gps_process = results.get("gps", "")
    mqtt_process = results.get("mqtt", "")
    broadcast_process = results.get("broadcast", "")
    vlan105 = results.get("vlan105", "")

    if gps_device == "NOT_DETECTED" or "GPS_DEVICE_NOT_DETECTED" in tty:
        return (
            "GPS device not detected",
            "Check GPS receiver connection, serial device mapping, and onboard system hardware. If the device remains missing after reboot, escalate for GPS receiver or cabling investigation."
        )

    if not gps_process.strip():
        return (
            "GPS process not running",
            "Restart GPS service or reboot onboard system. If the GPS process repeatedly fails to start, escalate for software/service investigation."
        )

    if not contains_nmea(nmea):
        return (
            "GPS receiver not outputting NMEA",
            "Check GPS receiver output and serial port assignment. If no NMEA is present after reboot, escalate for GPS receiver or antenna path investigation."
        )

    if satellites == 0:
        return (
            "GPS has no satellites visible",
            "Check GPS antenna, antenna cabling, receiver placement, and possible obstruction. Escalate if persistent."
        )

    if (
        gprmc["status"] == "V"
        and gprmc["utc_time"] == "Missing"
        and satellites == 0
    ):
        return (
            "GPS invalid fix - no satellites visible",
            "Likely GPS antenna, receiver, or reception issue. Check antenna path and receiver health."
        )

    if (
        gprmc["status"] == "V"
        and satellites is not None
        and satellites > 0
    ):
        return (
            "GPS invalid fix despite satellite visibility",
            "GPS receiver can see satellites but has not obtained a valid navigation solution. Monitor for recovery and investigate receiver or antenna performance if persistent."
        )

    if gprmc["status"] == "V":
        return (
            "GPS invalid fix",
            "GPS receiver is outputting data but does not currently have a valid fix. Monitor and investigate if persistent."
        )

    if gprmc["healthy"]:

        if not mqtt_process.strip():
            return (
                "GPS operational with service warning",
                "GPS receiver has a valid fix, but MQTT is not running. Restart MQTT process or reboot onboard system if GPS data is not being consumed correctly."
            )

        if "broadcast_unicast_gps.py" not in broadcast_process:
            return (
                "GPS operational with service warning",
                "GPS receiver has a valid fix, but the GPS broadcast process is not running. Restart GPS broadcast process or reboot onboard system if downstream systems are not receiving GPS data."
            )

        if "br0.105" not in vlan105:
            return (
                "GPS operational with network warning",
                "GPS receiver has a valid fix, but VLAN105 is missing. Check onboard system network/VLAN configuration if GPS data is not reaching downstream systems."
            )

        return (
            "GPS operational",
            "No action required."
        )

    return (
        "GPS fault - cause not yet classified",
        "Review GPS process, serial device, NMEA output, GPRMC status, satellite count, MQTT, broadcast process, and VLAN105 status."
    )
    