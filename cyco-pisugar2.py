import pwnagotchi.plugins as plugins
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import LabeledValue
from pwnagotchi.ui.view import BLACK
import logging

try:
    from pisugar2 import PiSugar2
except ImportError:
    logging.error("[cyco-pisugar2] Failed to import PiSugar2")
    PiSugar2 = None

try:
    from flask import redirect
except ImportError:
    from flask import redirect

class CycoPiSugar2(plugins.Plugin):
    __author__ = 'tisboyo, modified by cycoslave'
    __version__ = '1.0.0'
    __license__ = 'GPL3'
    __description__ = 'PiSugar2 battery status plugin'

    def __init__(self):
        self.ps = None
        self.available = False

    def on_loaded(self):
        """Initialize PiSugar2 connection and UI element"""
        # Set defaults for position and label
        self.options.setdefault('x_coord', 150)
        self.options.setdefault('y_coord', 0)
        self.options.setdefault('label', 'PWR')
        self.options.setdefault('shutdown', 5)
        self.options.setdefault('sync_rtc_on_boot', True)

        try:
            if PiSugar2 is None:
                logging.warning("[cyco-pisugar2] PiSugar2 module not installed")
                self.available = False
                return

            self.ps = PiSugar2()
            logging.info("[cyco-pisugar2] Connected to PiSugar2")
            self.available = True
        except Exception as e:
            logging.error(f"[cyco-pisugar2] Failed to initialize PiSugar2: {e}")
            self.available = False
            self.ps = None

    def on_ui_setup(self, ui):
        """Setup the UI element for battery display"""
        try:
            with ui._lock:
                ui.add_element('pwr',
                              LabeledValue(color=BLACK,
                                          label=self.options['label'],
                                          value='?',
                                          position=(int(self.options['x_coord']),
                                                   int(self.options['y_coord'])),
                                          label_font=fonts.Small,
                                          text_font=fonts.Medium))
        except Exception as e:
            logging.error(f"[cyco-pisugar2] Error in on_ui_setup: {e}")

    def on_ui_update(self, ui):
        """Update battery information on the display"""
        if not self.available or self.ps is None:
            return

        try:
            # Try to get battery percentage
            try:
                capacity = int(self.ps.get_battery_percentage().value)
            except Exception as e:
                logging.debug(f"[cyco-pisugar2] Could not get battery percentage: {e}")
                capacity = -1

            # Try to get voltage
            try:
                voltage = self.ps.get_battery_voltage().value
            except Exception as e:
                logging.debug(f"[cyco-pisugar2] Could not get battery voltage: {e}")
                voltage = None

            # Try to get current
            try:
                current = self.ps.get_battery_current().value
            except Exception as e:
                logging.debug(f"[cyco-pisugar2] Could not get battery current: {e}")
                current = None

            # Try to get temperature
            try:
                temperature = self.ps.get_battery_temperature().value
            except Exception as e:
                logging.debug(f"[cyco-pisugar2] Could not get battery temperature: {e}")
                temperature = None

            # Format the display string
            if capacity >= 0:
                display_str = f"{capacity}%"

                if voltage is not None:
                    display_str += f" {voltage:.2f}V"

                if current is not None:
                    display_str += f" {current:.2f}A"

                if temperature is not None:
                    display_str += f" {temperature:.1f}C"
            else:
                display_str = "USB"

            # Update the UI
            ui.set('pwr', display_str)
            logging.debug(f"[cyco-pisugar2] Battery display: {display_str}")

        except Exception as e:
            logging.error(f"[cyco-pisugar2] Error in on_ui_update: {e}")
            self.available = False
            try:
                ui.set('pwr', 'USB')
            except:
                pass

    def on_webhook(self, path, request):
        """Redirect to PiSugar web UI"""
        try:
            logging.info("[cyco-pisugar2] Webhook called, redirecting to PiSugar web UI")

            # Redirect to PiSugar web UI
            host = request.host.split(':')[0]
            pisugar_url = f'http://{host}:8421'

            logging.info(f"[cyco-pisugar2] Redirecting to: {pisugar_url}")

            return redirect(pisugar_url, code=302)

        except Exception as e:
            logging.error(f"[cyco-pisugar2] Webhook error: {e}", exc_info=True)
            return f"<html><body>Error redirecting: {str(e)}</body></html>"

    def on_unload(self, ui):
        """Cleanup when plugin is unloaded"""
        try:
            with ui._lock:
                ui.remove_element('pwr')
        except:
            pass

        if self.ps is not None:
            try:
                self.ps.close()
            except:
                pass

        logging.info("[cyco-pisugar2] Plugin unloaded")
