import pwnagotchi.plugins as plugins
from pwnagotchi.utils import StatusFile
import logging
import os
import subprocess
from datetime import datetime
import time
import configparser
import glob

try:
    from flask import send_file, render_template_string
except ImportError:
    from flask.helpers import send_file
    from flask import render_template_string

class CycoBackup(plugins.Plugin):
    __author__ = 'your@email.com'
    __version__ = '1.0.0'
    __license__ = 'GPL3'
    __description__ = 'Automatic backup plugin for Pwnagotchi configuration and data'

    def __init__(self):
        self.ready = False
        self.status = StatusFile('/root/.cyco-backup-status')
        self.last_backup_time = 0
        self.backup_interval = 3600  # 1 hour in seconds

    def on_loaded(self):
        # Default configuration
        if 'backup_path' not in self.options:
            self.options['backup_path'] = '/root/backups/'

        if 'interval_hours' not in self.options:
            self.options['interval_hours'] = 1

        if 'max_backups' not in self.options:
            self.options['max_backups'] = 5

        # Convert hours to seconds
        self.backup_interval = self.options['interval_hours'] * 3600

        # Create backup directory if it doesn't exist
        os.makedirs(self.options['backup_path'], exist_ok=True)

        self.ready = True
        logging.info(f"[cyco-backup] Plugin loaded successfully. Backup interval: {self.options['interval_hours']} hour(s)")
        logging.info(f"[cyco-backup] Backup path: {self.options['backup_path']}")

        # Run backup immediately on load
        self.last_backup_time = time.time()
        logging.info("[cyco-backup] First backup will run after interval")

    def on_tick(self, agent):
        """Called periodically, better for scheduled tasks"""
        if not self.ready:
            return

        current_time = time.time()

        # Check if it's time for a backup
        if (current_time - self.last_backup_time) >= self.backup_interval:
            self._create_backup(agent)
            self.last_backup_time = current_time

    def on_webhook(self, path, request):
        """Handle web interface requests for listing and downloading backups"""
        try:
            if not self.ready:
                return "<html><body>Plugin not ready</body></html>"

            # Handle None path
            if path is None:
                path = ''

            logging.info(f"[cyco-backup] Webhook called with path: {path}")

            # Download file - check multiple path formats
            if path and ('download' in path):
                # Extract filename from various path formats
                if '/download/' in path:
                    filename = path.split('/download/')[-1]
                else:
                    filename = path.replace('download', '').strip('/')

                logging.info(f"[cyco-backup] Download request for: {filename}")
                return self._download_backup(filename)

            # List backups
            else:
                logging.info(f"[cyco-backup] Listing backups")
                return self._list_backups_html()

        except Exception as e:
            logging.error(f"[cyco-backup] Webhook error: {e}", exc_info=True)
            return f"<html><body>Error: {str(e)}</body></html>"

    def _get_last_backup_time(self):
        """Get the last backup timestamp from status file"""
        try:
            status_file = '/root/.cyco-backup-status'
            if os.path.exists(status_file):
                mod_time = os.path.getmtime(status_file)
                last_backup = datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')
                return last_backup
        except Exception as e:
            logging.error(f"[cyco-backup] Error reading status file: {e}")

        return "Never"

    def _list_backups_html(self):
        """Generate HTML list of available backups"""
        try:
            logging.info(f"[cyco-backup] Looking for backups in: {self.options['backup_path']}")

            # Get last backup time
            last_backup_time = self._get_last_backup_time()

            # Check if directory exists
            if not os.path.exists(self.options['backup_path']):
                logging.warning(f"[cyco-backup] Backup directory does not exist: {self.options['backup_path']}")
                return self._render_page("<tr><td colspan='4' style='text-align: center; padding: 20px; color: red;'>Backup directory not found: " + self.options['backup_path'] + "</td></tr>", last_backup_time)

            # List all files in directory for debugging
            all_files = os.listdir(self.options['backup_path'])
            logging.info(f"[cyco-backup] Files in backup directory: {all_files}")

            # Find both .tar.gz and .tgz files
            backup_files = glob.glob(os.path.join(self.options['backup_path'], '*.tar.gz'))
            backup_files += glob.glob(os.path.join(self.options['backup_path'], '*.tgz'))

            logging.info(f"[cyco-backup] Found {len(backup_files)} backup files: {backup_files}")

            backup_files.sort(reverse=True)

            # Generate table rows
            rows = ""
            for backup_path in backup_files:
                filename = os.path.basename(backup_path)
                size_mb = os.path.getsize(backup_path) / (1024 * 1024)
                timestamp = datetime.fromtimestamp(os.path.getmtime(backup_path)).strftime('%Y-%m-%d %H:%M:%S')

                logging.info(f"[cyco-backup] Adding backup to list: {filename} ({size_mb:.2f} MB)")

                rows += f"""
                <tr>
                    <td>{filename}</td>
                    <td>{size_mb:.2f} MB</td>
                    <td>{timestamp}</td>
                    <td>
                        <a href="/plugins/cyco-backup/download/{filename}"
                           style="padding: 5px 10px; background-color: #2196F3; color: white; text-decoration: none; border-radius: 3px; display: inline-block;">
                            ⬇️ Download
                        </a>
                    </td>
                </tr>
                """

            if not rows:
                logging.warning("[cyco-backup] No backups found")
                rows = "<tr><td colspan='4' style='text-align: center; padding: 20px;'>No backups available. Run a manual backup first.</td></tr>"

            return self._render_page(rows, last_backup_time)

        except Exception as e:
            logging.error(f"[cyco-backup] Error listing backups: {e}", exc_info=True)
            return f"<html><body>Error listing backups: {e}</body></html>"

    def _render_page(self, rows, last_backup_time):
        """Render the backups page with Pwnagotchi frame"""
        html = f"""
        {{% extends "base.html" %}}
        {{% set active_page = "plugins" %}}

        {{% block title %}}Backups{{% endblock %}}

        {{% block content %}}
        <div id="container">
            <h1>Backups</h1>
            <div style="margin-bottom: 20px; padding: 15px; background-color: #f0f0f0; border-radius: 5px;">
                <p><strong>Last Backup:</strong> {last_backup_time}</p>
                <p><strong>Backup Interval:</strong> Every {self.options['interval_hours']} hour(s)</p>
            </div>
            <p>Download your backup files below:</p>
            <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
                <thead>
                    <tr style="background-color: #f2f2f2;">
                        <th style="padding: 12px; text-align: left; border-bottom: 1px solid #ddd;">Filename</th>
                        <th style="padding: 12px; text-align: left; border-bottom: 1px solid #ddd;">Size</th>
                        <th style="padding: 12px; text-align: left; border-bottom: 1px solid #ddd;">Created</th>
                        <th style="padding: 12px; text-align: left; border-bottom: 1px solid #ddd;">Action</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </div>
        {{% endblock %}}
        """

        return render_template_string(html)

    def _download_backup(self, filename):
        """Send backup file to user"""
        try:
            logging.info(f"[cyco-backup] Download function called for: {filename}")

            # Clean up filename - remove any extra slashes or whitespace
            filename = filename.strip('/ ')
            logging.info(f"[cyco-backup] Cleaned filename: {filename}")

            # Validate filename to prevent path traversal attacks
            if '..' in filename or '/' in filename or filename == '':
                logging.warning(f"[cyco-backup] Invalid filename attempt: {filename}")
                return "<html><body>Invalid filename</body></html>"

            backup_path = os.path.join(self.options['backup_path'], filename)
            logging.info(f"[cyco-backup] Full backup path: {backup_path}")
            logging.info(f"[cyco-backup] File exists: {os.path.exists(backup_path)}")
            logging.info(f"[cyco-backup] Is file: {os.path.isfile(backup_path)}")

            # Verify file exists and is in the backup directory
            if not os.path.exists(backup_path):
                logging.warning(f"[cyco-backup] Backup file not found: {backup_path}")
                return "<html><body>Backup file not found: " + filename + "</body></html>"

            if not os.path.isfile(backup_path):
                logging.warning(f"[cyco-backup] Path is not a file: {backup_path}")
                return "<html><body>Invalid file path</body></html>"

            if not os.path.abspath(backup_path).startswith(os.path.abspath(self.options['backup_path'])):
                logging.warning(f"[cyco-backup] Invalid file path: {backup_path}")
                return "<html><body>Invalid file path</body></html>"

            logging.info(f"[cyco-backup] Sending file for download: {backup_path}")

            # Send file for download
            return send_file(
                backup_path,
                as_attachment=True,
                download_name=filename,
                mimetype='application/gzip'
            )

        except Exception as e:
            logging.error(f"[cyco-backup] Download failed: {e}", exc_info=True)
            return f"<html><body>Download failed: {str(e)}</body></html>"

    def _create_backup(self, agent):
        try:
            display = agent.view()
            display.set('status', 'Creating backup...')
            display.update()

            # Get Pwnagotchi name - read directly from config file
            pwnagotchi_name = self._get_name()

            logging.info(f"[cyco-backup] Using name: {pwnagotchi_name}")

            # Generate backup filename with name and timestamp
            timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
            backup_filename = f"{pwnagotchi_name}-backup-{timestamp}.tar.gz"
            backup_path = os.path.join(self.options['backup_path'], backup_filename)

            logging.info(f"[cyco-backup] Creating backup: {backup_path}")

            # Define files and directories to backup
            backup_items = [
                '/root/brain.json',
                '/root/.api-report.json',
                '/root/.auto-update',
                '/root/.bt-tether*',
                '/root/.net_pos_saved',
                '/root/.ohc_uploads',
                '/root/.wigle_uploads',
                '/root/.wpa_sec_uploads',
                '/root/handshakes/',
                '/root/peers/',
                '/root/.ssh/',
                '/root/.bashrc',
                '/root/.profile',
                '/etc/pwnagotchi/',
                '/etc/hostname',
                '/etc/hosts',
                '/etc/network/interfaces',
                '/etc/network/interfaces.d/',
                '/etc/wpa_supplicant/wpa_supplicant.conf',
                '/etc/dhcpcd.conf',
                '/etc/resolv.conf',
                '/etc/dnsmasq.conf',
                '/etc/ssh/',
                '/boot/firmware/config.txt',
                '/boot/cmdline.txt',
                '/usr/local/share/pwnagotchi/custom-plugins/',
                '/home/pi/.ssh/',
                '/home/pi/.bashrc',
                '/home/pi/.profile',
                '/var/log/pwnagotchi.log'
            ]

            # Filter to only existing files/directories
            existing_items = [item for item in backup_items if os.path.exists(item.rstrip('*'))]

            # Create tar command
            tar_cmd = ['tar', '-czvf', backup_path] + existing_items

            # Execute backup
            process = subprocess.Popen(
                tar_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate()

            if process.returncode == 0:
                logging.info(f"[cyco-backup] Backup created successfully: {backup_path}")
                display.set('status', 'Backup complete!')
                display.update()
                self.status.update()

                # Clean up old backups
                self._cleanup_old_backups(pwnagotchi_name)
            else:
                raise Exception(f"Tar command failed: {stderr.decode()}")

        except Exception as e:
            logging.error(f"[cyco-backup] Backup failed: {e}", exc_info=True)
            display.set('status', 'Backup failed!')
            display.update()

    def _get_name(self):
        """Get Pwnagotchi name from config.toml"""
        try:
            config = configparser.ConfigParser()
            config.read('/etc/pwnagotchi/config.toml')
            return config.get('main', 'name', fallback='pwnagotchi')
        except:
            return 'pwnagotchi'

    def _cleanup_old_backups(self, pwnagotchi_name):
        """Remove old backups keeping only max_backups newest ones"""
        try:
            backup_files = []
            for filename in os.listdir(self.options['backup_path']):
                if filename.startswith(pwnagotchi_name) and (filename.endswith('.tar.gz') or filename.endswith('.tgz')):
                    filepath = os.path.join(self.options['backup_path'], filename)
                    backup_files.append((filepath, os.path.getmtime(filepath)))

            # Sort by modification time (newest first)
            backup_files.sort(key=lambda x: x[1], reverse=True)

            # Remove old backups
            for filepath, _ in backup_files[self.options['max_backups']:]:
                os.remove(filepath)
                logging.info(f"[cyco-backup] Removed old backup: {filepath}")

        except Exception as e:
            logging.error(f"[cyco-backup] Cleanup failed: {e}", exc_info=True)

    def on_unload(self, ui):
        logging.info("[cyco-backup] Plugin unloaded")
