import pwnagotchi.plugins as plugins
import logging

try:
    from pisugar2 import PiSugar2
except ImportError:
    logging.error("[PiSugar2] Failed to import PiSugar2")
    PiSugar2 = None

try:
    from flask import redirect
except ImportError:
    from flask import redirect

class CycoPiSugar2(plugins.Plugin):
    __author__ = 'cycoslave'
    __version__ = '1.0.0'
    __license__ = 'GPL3'
    __description__ = 'PiSugar2 battery status plugin'

    def __init__(self):
        self.ps = None
        self.available = False
        self.last_capacity = 0
        self.last_voltage = 0
        self.last_current = 0
        self.last_temperature = 0

    def on_loaded(self):
        """Initialize PiSugar2 connection"""
        try:
            if PiSugar2 is None:
                logging.warning("[PiSugar2] PiSugar2 module not installed")
                self.available = False
                return

            self.ps = PiSugar2()
            logging.info("[PiSugar2] Connected to PiSugar2")
            self.available = True
        except Exception as e:
            logging.error(f"[PiSugar2] Failed to initialize PiSugar2: {e}")
            self.available = False
            self.ps = None

    def on_ui_update(self, ui):
        """Update battery information on the display"""
        if not self.available or self.ps is None:
            return

        try:
            # Try to get battery percentage
            try:
                capacity = int(self.ps.get_battery_percentage().value)
            except Exception as e:
                #logging.warning(f"[PiSugar2] Could not get battery percentage: {e}")
                capacity = self.last_capacity

            # Try to get voltage
            try:
                voltage = self.ps.get_battery_voltage().value
            except Exception as e:
                #logging.warning(f"[PiSugar2] Could not get battery voltage: {e}")
                voltage = self.last_voltage

            # Try to get current
            try:
                current = self.ps.get_battery_current().value
            except Exception as e:
                #logging.warning(f"[PiSugar2] Could not get battery current: {e}")
                current = self.last_current

            # Try to get temperature
            try:
                temperature = self.ps.get_battery_temperature().value
            except Exception as e:
                #logging.warning(f"[PiSugar2] Could not get battery temperature: {e}")
                temperature = self.last_temperature

            # Store for next attempt
            self.last_capacity = capacity
            self.last_voltage = voltage
            self.last_current = current
            self.last_temperature = temperature

            # Format the display string
            if isinstance(voltage, (int, float)):
                voltage_str = f"{voltage:.2f}V"
            else:
                voltage_str = str(voltage)

            if isinstance(current, (int, float)):
                current_str = f"{current:.2f}A"
            else:
                current_str = str(current)

            if isinstance(temperature, (int, float)):
                temp_str = f"{temperature:.1f}°C"
            else:
                temp_str = str(temperature)

            # Update the UI
            ui.set('battery', f'{capacity}% {voltage_str} {current_str} {temp_str}')

            logging.debug(f"[PiSugar2] Battery: {capacity}% {voltage_str} {current_str} {temp_str}")

        except Exception as e:
            logging.error(f"[PiSugar2] Error in on_ui_update: {e}")
            self.available = False

    def on_webhook(self, path, request):
        """Redirect to PiSugar web UI"""
        try:
            logging.info(f"[PiSugar2] Webhook called, redirecting to PiSugar web UI")

            # Redirect to PiSugar web UI
            host = request.host.split(':')[0]
            pisugar_url = f'http://{host}:8421'

            logging.info(f"[PiSugar2] Redirecting to: {pisugar_url}")

            return redirect(pisugar_url, code=302)

        except Exception as e:
            logging.error(f"[PiSugar2] Webhook error: {e}", exc_info=True)
            return f"<html><body>Error redirecting: {str(e)}</body></html>"

    def on_unload(self, ui):
        """Cleanup when plugin is unloaded"""
        if self.ps is not None:
            try:
                self.ps.close()
            except:
                pass
        logging.info("[PiSugar2] Plugin unloaded")
