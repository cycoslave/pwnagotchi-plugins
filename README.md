# pwnagotchi-plugins
Plugins for pwnagotchi that I either modified or created.

## pisugar2-cyco.py
I just did changes to an existing plugin to be able to change the location on the screen without the need to change the actual plugin python script.

### Install Pisugar
```
# Install PiSugar Power Manager 
curl http://cdn.pisugar.com/release/Pisugar-power-manager.sh | sudo bash

# Download the plugin and support library
git clone https://github.com/PiSugar/pisugar2py.git
```

### Config.toml
```
main.plugins.pisugar2-cyco.enabled = true
main.plugins.pisugar2-cyco.x_coord = 150
main.plugins.pisugar2-cyco.y_coord = 0
main.plugins.pisugar2-cyco.label = "BAT"
main.plugins.pisugar2-cyco.shutdown = 5
main.plugins.pisugar2-cyco.sync_rtc_on_boot = true
```

## pwnbackup.py
This is a work in progress currently.
