FLEET_PROFILES = {
    "gwr_165_166": {
        "gps_device_mode": "fixed",
        "gps_device": "/dev/ttyS1",
        "active_wans": ["01", "03"],
        "vlan": "br0.105",
        "gprmc_file": "/var/local/gprmc",
        "broadcast_process": "broadcast_unicast_gps.py",
    },
    "gwr_800_802": {
        "gps_device_mode": "auto",
        "active_wans": ["01", "02"],        
        "vlan": "br0.105",
        "gprmc_file": "/var/local/gprmc",
        "broadcast_process": "broadcast_unicast_gps.py",
    },
    "xc_220_221": {
        "gps_device_mode": "auto",
        "active_wans": ["01", "02", "03"],
        "vlan": "br0.105",
        "gprmc_file": "/var/local/gprmc",
        "broadcast_process": "broadcast_unicast_gps.py",
    },
    "xc_170": {
        "gps_device_mode": "auto",
        "active_wans": ["01", "02", "03"],
        "vlan": "br0.105",
        "gprmc_file": "/var/local/gprmc",
        "broadcast_process": "broadcast_unicast_gps.py",
    },
}