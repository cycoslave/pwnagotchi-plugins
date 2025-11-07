# pwnagotchi-plugins
Plugins for pwnagotchi that I either modified or created.

## cyco-pisugar2.py
I just did changes to an existing plugin to be able to change the location on the screen without the need to change the actual plugin python script.

### Install Pisugar
```
# Install PiSugar Power Manager 
curl http://cdn.pisugar.com/release/Pisugar-power-manager.sh | sudo bash

# Download the plugin and support library
# the content need to be copied in your pythons packages (/usr/local/lib/python3.11/dist-packages/)
git clone https://github.com/PiSugar/pisugar2py.git
```

### Config.toml
```
main.plugins.cyco-pisugar2.enabled = true
main.plugins.cyco-pisugar2.x_coord = 150
main.plugins.cyco-pisugar2.y_coord = 0
main.plugins.cyco-pisugar2.label = ""
main.plugins.cyco-pisugar2.shutdown = 5
main.plugins.cyco-pisugar2.sync_rtc_on_boot = true
```

## cyco-backup.py
A plugin that does regular backup of your pwnagotchi, you can download them from the webui.

### Config.toml
```
main.plugins.cyco-backup.enabled = true
main.plugins.cyco-backup.backup_path = "/root/backups/"
main.plugins.cyco-backup.interval_hours = 1
main.plugins.cyco-backup.max_backups = 5
main.plugins.cyco-backup.backup_config = true
main.plugins.cyco-backup.backup_system_files = true
main.plugins.cyco-backup.backup_custom_plugins = true
main.plugins.cyco-backup.backup_handshakes = true
main.plugins.cyco-backup.backup_btsniffer_data = true
main.plugins.cyco-backup.backup_logs = true
main.plugins.cyco-backup.backup_last_session = false
```

## cyco-btsniffer.py
A plugin that keeps a record of seen bluetooth devices.

### Config.toml
```
main.plugins.cyco-btsniffer.enabled = true
main.plugins.cyco-btsniffer.timer = 45
main.plugins.cyco-btsniffer.devices_file = "/root/bluetooth_devices.json"
main.plugins.cyco-btsniffer.count_interval = 300
main.plugins.cyco-btsniffer.bt_x_coord = 70
main.plugins.cyco-btsniffer.bt_y_coord = 32
```
