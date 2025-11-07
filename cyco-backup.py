import pwnagotchi.plugins as plugins
from pwnagotchi.utils import StatusFile
import logging
import os
import subprocess
from datetime import datetime
import time
import configparser
import glob
import threading

try:
    from flask import send_file, render_template_string
except ImportError:
    logging.error("[cyco-backup] Failed to import Flask components")
    send_file = None
    render_template_string = None

class CycoBackup(plugins.Plugin):
    __author__ = 'cycoslave'
    __version__ = '1.1.1'
    __license__ = 'GPL3'
    __description__ = 'Automatic backup plugin for Pwnagotchi configuration and data with configurable options'

    def __init__(self):
        self.ready = False
        self.status = StatusFile('/root/.cyco-backup-status')
        self.last_backup_time = 0
        self.backup_interval = 3600
        self.backup_in_progress = False
        self.upload_faces = []
        self.face_index = 0
        self.agent = None

    def on_loaded(self):
        try:
            self.options.setdefault('backup_path', '/root/backups/')
            self.options.setdefault('interval_hours', 1)
            self.options.setdefault('max_backups', 5)
            self.options.setdefault('backup_config', True)
            self.options.setdefault('backup_system_files', True)
            self.options.setdefault('backup_custom_plugins', True)
            self.options.setdefault('backup_handshakes', True)
            self.options.setdefault('backup_btsniffer_data', True)
            self.options.setdefault('backup_logs', True)
            self.options.setdefault('backup_last_session', False)

            self.backup_interval = int(self.options['interval_hours']) * 3600
            os.makedirs(self.options['backup_path'], exist_ok=True)
            self._load_upload_faces()

            self.ready = True
            logging.info("[cyco-backup] Plugin loaded successfully")
            self.last_backup_time = time.time()

        except Exception as e:
            logging.error("[cyco-backup] Error in on_loaded: " + str(e), exc_info=True)
            self.ready = False

    def _load_upload_faces(self):
        try:
            config = configparser.ConfigParser()
            config.read('/etc/pwnagotchi/config.toml')
            self.upload_faces = []

            if config.has_section('ui.faces'):
                if config.has_option('ui.faces', 'upload'):
                    upload = config.get('ui.faces', 'upload')
                    if upload:
                        self.upload_faces.append(upload)
                if config.has_option('ui.faces', 'upload1'):
                    upload1 = config.get('ui.faces', 'upload1')
                    if upload1:
                        self.upload_faces.append(upload1)
                if config.has_option('ui.faces', 'upload2'):
                    upload2 = config.get('ui.faces', 'upload2')
                    if upload2:
                        self.upload_faces.append(upload2)

            if not self.upload_faces:
                self.upload_faces = ['(1__0)', '(1__1)', '(0__1)']

        except Exception as e:
            logging.error("[cyco-backup] Error loading upload faces: " + str(e))
            self.upload_faces = ['(1__0)', '(1__1)', '(0__1)']

    def on_tick(self, agent):
        if not self.ready:
            return
        try:
            self.agent = agent
            current_time = time.time()
            if (current_time - self.last_backup_time) >= self.backup_interval:
                self._create_backup(agent)
                self.last_backup_time = current_time
        except Exception as e:
            logging.error("[cyco-backup] Error in on_tick: " + str(e))

    def on_webhook(self, path, request):
        try:
            if not self.ready or render_template_string is None:
                return "<html><body>Plugin not ready</body></html>"

            if path is None:
                path = ''

            if 'backup' in path and 'download' not in path and 'delete' not in path:
                return self._trigger_manual_backup()

            if 'delete' in path:
                parts = path.split('/')
                filename = parts[-1] if parts[-1] else parts[-2]
                return self._delete_backup(filename)

            if 'download' in path:
                parts = path.split('/')
                filename = parts[-1] if parts[-1] else parts[-2]
                return self._download_backup(filename)

            return self._list_backups_html()

        except Exception as e:
            logging.error("[cyco-backup] Webhook error: " + str(e), exc_info=True)
            return "<html><body>Error: " + str(e) + "</body></html>"

    def _get_last_backup_time(self):
        try:
            status_file = '/root/.cyco-backup-status'
            if os.path.exists(status_file):
                mod_time = os.path.getmtime(status_file)
                last_backup = datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')
                return last_backup
        except Exception as e:
            logging.error("[cyco-backup] Error reading status file: " + str(e))
        return "Never"

    def _list_backups_html(self):
        try:
            last_backup_time = self._get_last_backup_time()

            if not os.path.exists(self.options['backup_path']):
                error_row = "<tr><td colspan='5' style='text-align: center; padding: 20px; color: red;'>Backup directory not found</td></tr>"
                return self._render_page(error_row, last_backup_time)

            backup_files = glob.glob(os.path.join(self.options['backup_path'], '*.tar.gz'))
            backup_files += glob.glob(os.path.join(self.options['backup_path'], '*.tgz'))
            backup_files.sort(reverse=True)

            rows = ""
            for backup_path in backup_files:
                filename = os.path.basename(backup_path)
                size_mb = os.path.getsize(backup_path) / (1024 * 1024)
                timestamp = datetime.fromtimestamp(os.path.getmtime(backup_path)).strftime('%Y-%m-%d %H:%M:%S')
                rows += "<tr><td>" + filename + "</td><td>" + str(round(size_mb, 2)) + " MB</td><td>" + timestamp + "</td><td><a href=\"/plugins/cyco-backup/download/" + filename + "\" style=\"padding: 5px 10px; background-color: #2196F3; color: white; text-decoration: none; border-radius: 3px; display: inline-block;\">Download</a></td><td><a href=\"/plugins/cyco-backup/delete/" + filename + "\" style=\"padding: 5px 10px; background-color: #F44336; color: white; text-decoration: none; border-radius: 3px; display: inline-block;\" onclick=\"return confirm('Delete this backup?');\">Delete</a></td></tr>"

            if not rows:
                rows = "<tr><td colspan='5' style='text-align: center; padding: 20px;'>No backups available</td></tr>"

            return self._render_page(rows, last_backup_time)

        except Exception as e:
            logging.error("[cyco-backup] Error listing backups: " + str(e), exc_info=True)
            return "<html><body>Error: " + str(e) + "</body></html>"

    def _render_page(self, rows, last_backup_time):
        status_msg = '<div style="padding: 10px; background-color: #fff3cd; border: 1px solid #ffc107; border-radius: 3px; margin-bottom: 20px;">Backup in progress...</div>' if self.backup_in_progress else ""
        interval = str(self.options['interval_hours'])

        html = """{% extends "base.html" %}
{% set active_page = "plugins" %}
{% block title %}Backups{% endblock %}
{% block content %}
<div id="container">
<h1>Backups</h1>
""" + status_msg + """
<div style="margin-bottom: 20px; padding: 15px; background-color: #f0f0f0; border-radius: 5px;">
<p><strong>Last Backup:</strong> """ + last_backup_time + """</p>
<p><strong>Backup Interval:</strong> Every """ + interval + """ hour(s)</p>
</div>
<div style="margin-bottom: 20px;">
<button onclick="window.location.href='/plugins/cyco-backup/backup'" style="padding: 10px 20px; background-color: #4CAF50; color: white; border: none; border-radius: 3px; cursor: pointer;">Run Backup Now</button>
</div>
<table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
<thead><tr style="background-color: #f2f2f2;">
<th style="padding: 12px; text-align: left; border-bottom: 1px solid #ddd;">Filename</th>
<th style="padding: 12px; text-align: left; border-bottom: 1px solid #ddd;">Size</th>
<th style="padding: 12px; text-align: left; border-bottom: 1px solid #ddd;">Created</th>
<th style="padding: 12px; text-align: left; border-bottom: 1px solid #ddd;">Download</th>
<th style="padding: 12px; text-align: left; border-bottom: 1px solid #ddd;">Delete</th>
</tr></thead>
<tbody>
""" + rows + """
</tbody>
</table>
</div>
{% endblock %}
"""
        return render_template_string(html)

    def _trigger_manual_backup(self):
        try:
            if self.backup_in_progress:
                return self._render_backup_status("Backup already in progress...")

            logging.info("[cyco-backup] Manual backup triggered")
            self.backup_in_progress = True

            backup_thread = threading.Thread(target=self._create_backup_standalone)
            backup_thread.daemon = True
            backup_thread.start()

            html = """{% extends "base.html" %}
{% set active_page = "plugins" %}
{% block title %}Backup Status{% endblock %}
{% block content %}
<div id="container">
<h1>Backup Status</h1>
<div style="padding: 20px; background-color: #e8f5e9; border: 2px solid #4CAF50; border-radius: 5px; text-align: center;">
<h2 style="color: #4CAF50;">Backup Started</h2>
<p>Your backup is being created in the background.</p>
<a href="/plugins/cyco-backup/" style="padding: 10px 20px; background-color: #2196F3; color: white; text-decoration: none; border-radius: 3px; display: inline-block;">Back to Backups</a>
</div>
</div>
{% endblock %}
"""
            return render_template_string(html)

        except Exception as e:
            logging.error("[cyco-backup] Error triggering backup: " + str(e), exc_info=True)
            self.backup_in_progress = False
            return "<html><body>Error: " + str(e) + "</body></html>"

    def _render_backup_status(self, message):
        html = """{% extends "base.html" %}
{% set active_page = "plugins" %}
{% block title %}Status{% endblock %}
{% block content %}
<div id="container">
<h1>Status</h1>
<div style="padding: 20px; background-color: #fff3cd; border: 2px solid #ffc107; border-radius: 5px; text-align: center;">
<p>""" + message + """</p>
<a href="/plugins/cyco-backup/" style="padding: 10px 20px; background-color: #2196F3; color: white; text-decoration: none; border-radius: 3px; display: inline-block;">Back</a>
</div>
</div>
{% endblock %}
"""
        return render_template_string(html)

    def _download_backup(self, filename):
        try:
            filename = filename.strip('/ ')
            if '..' in filename or '/' in filename or filename == '':
                return "<html><body>Invalid filename</body></html>"

            backup_path = os.path.join(self.options['backup_path'], filename)
            if not os.path.exists(backup_path) or not os.path.isfile(backup_path):
                return "<html><body>File not found</body></html>"

            if not os.path.abspath(backup_path).startswith(os.path.abspath(self.options['backup_path'])):
                return "<html><body>Invalid path</body></html>"

            return send_file(backup_path, as_attachment=True, download_name=filename, mimetype='application/gzip')

        except Exception as e:
            logging.error("[cyco-backup] Download failed: " + str(e))
            return "<html><body>Error: " + str(e) + "</body></html>"

    def _delete_backup(self, filename):
        try:
            filename = filename.strip('/ ')
            if '..' in filename or '/' in filename or filename == '':
                return "<html><body>Invalid filename</body></html>"

            backup_path = os.path.join(self.options['backup_path'], filename)
            if not os.path.exists(backup_path) or not os.path.isfile(backup_path):
                return self._render_backup_status("File not found")

            if not os.path.abspath(backup_path).startswith(os.path.abspath(self.options['backup_path'])):
                return self._render_backup_status("Invalid path")

            os.remove(backup_path)

            html = """{% extends "base.html" %}
{% set active_page = "plugins" %}
{% block title %}Deleted{% endblock %}
{% block content %}
<div id="container">
<h1>Backup Deleted</h1>
<div style="padding: 20px; background-color: #e8f5e9; border: 2px solid #4CAF50; border-radius: 5px; text-align: center;">
<h2 style="color: #4CAF50;">Success</h2>
<p>Backup deleted successfully.</p>
<a href="/plugins/cyco-backup/" style="padding: 10px 20px; background-color: #2196F3; color: white; text-decoration: none; border-radius: 3px; display: inline-block;">Back</a>
</div>
</div>
{% endblock %}
"""
            return render_template_string(html)

        except Exception as e:
            logging.error("[cyco-backup] Delete failed: " + str(e))
            return "<html><body>Error: " + str(e) + "</body></html>"

    def _build_backup_items(self):
        backup_items = [
            '/etc/pwnagotchi/',
            '/etc/hostname',
            '/etc/hosts',
            '/etc/network/interfaces',
            '/etc/network/interfaces.d/',
        ]

        if self.options.get('backup_system_files', True):
            backup_items.extend([
                '/etc/wpa_supplicant/wpa_supplicant.conf',
                '/etc/dhcpcd.conf',
                '/etc/resolv.conf',
                '/etc/dnsmasq.conf',
                '/etc/ssh/',
                '/boot/firmware/config.txt',
                '/boot/cmdline.txt',
            ])

        if self.options.get('backup_custom_plugins', True):
            backup_items.append('/usr/local/share/pwnagotchi/custom-plugins/')

        if self.options.get('backup_handshakes', True):
            backup_items.append('/root/handshakes/')

        if self.options.get('backup_btsniffer_data', True):
            backup_items.append('/root/handshakes/bluetooth_devices.json')

        if self.options.get('backup_logs', True):
            backup_items.extend(['/var/log/pwnagotchi.log', '/root/.bashrc', '/root/.profile'])

        backup_items.extend(['/root/peers/', '/root/.ssh/', '/home/pi/.ssh/', '/home/pi/.bashrc', '/home/pi/.profile'])

        return backup_items

    def _get_name(self):
        """Get Pwnagotchi name from hostname file"""
        try:
            with open('/etc/hostname', 'r') as f:
                name = f.read().strip()
                if name:
                    logging.info("[cyco-backup] Got name from hostname: " + str(name))
                    return name
        except Exception as e:
            logging.debug("[cyco-backup] Could not read hostname: " + str(e))

        return 'pwnagotchi'

    def _create_backup_standalone(self):
        try:
            pwnagotchi_name = self._get_name()
            timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
            backup_filename = pwnagotchi_name + "-backup-" + timestamp + ".tar.gz"
            backup_path = os.path.join(self.options['backup_path'], backup_filename)

            logging.info("[cyco-backup] Creating backup: " + str(backup_path))

            backup_items = self._build_backup_items()
            existing_items = [item for item in backup_items if os.path.exists(item.rstrip('*'))]

            tar_cmd = ['tar', '-czf', backup_path] + existing_items
            process = subprocess.Popen(tar_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()

            if process.returncode == 0:
                logging.info("[cyco-backup] Backup created: " + str(backup_path))
                self.status.update()
                self._cleanup_old_backups(pwnagotchi_name)
            else:
                logging.error("[cyco-backup] Backup failed: " + stderr.decode())

        except Exception as e:
            logging.error("[cyco-backup] Standalone backup failed: " + str(e), exc_info=True)
        finally:
            self.backup_in_progress = False

    def _create_backup(self, agent):
        try:
            display = agent.view()
            pwnagotchi_name = self._get_name()
            timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
            backup_filename = pwnagotchi_name + "-backup-" + timestamp + ".tar.gz"
            backup_path = os.path.join(self.options['backup_path'], backup_filename)

            logging.info("[cyco-backup] Creating backup: " + str(backup_path))

            backup_items = self._build_backup_items()
            existing_items = [item for item in backup_items if os.path.exists(item.rstrip('*'))]

            tar_cmd = ['tar', '-czf', backup_path] + existing_items
            process = subprocess.Popen(tar_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            face_index = 0
            while process.poll() is None:
                if len(self.upload_faces) > 0:
                    current_face = self.upload_faces[face_index % len(self.upload_faces)]
                    display.set('face', current_face)
                display.set('status', 'Backing up...')
                display.update()
                face_index += 1
                time.sleep(0.5)

            stdout, stderr = process.communicate()

            if process.returncode == 0:
                logging.info("[cyco-backup] Backup created: " + str(backup_path))
                display.set('status', 'Backup complete!')
                display.update()
                self.status.update()
                self._cleanup_old_backups(pwnagotchi_name)
            else:
                logging.error("[cyco-backup] Backup failed: " + stderr.decode())

        except Exception as e:
            logging.error("[cyco-backup] Backup failed: " + str(e), exc_info=True)

    def _cleanup_old_backups(self, pwnagotchi_name):
        try:
            backup_files = []
            for filename in os.listdir(self.options['backup_path']):
                if filename.startswith(pwnagotchi_name) and (filename.endswith('.tar.gz') or filename.endswith('.tgz')):
                    filepath = os.path.join(self.options['backup_path'], filename)
                    backup_files.append((filepath, os.path.getmtime(filepath)))

            backup_files.sort(key=lambda x: x[1], reverse=True)

            for filepath, _ in backup_files[int(self.options['max_backups']):]:
                os.remove(filepath)
                logging.info("[cyco-backup] Removed old backup")

        except Exception as e:
            logging.error("[cyco-backup] Cleanup failed: " + str(e))

    def on_unload(self, ui):
        logging.info("[cyco-backup] Plugin unloaded")
