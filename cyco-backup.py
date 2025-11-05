import pwnagotchi.plugins as plugins
from pwnagotchi.utils import StatusFile
import logging
import os
import subprocess
from datetime import datetime

class CycoBackup(plugins.Plugin):
    __author__ = 'tonyroy@wcksoft.com'
    __version__ = '1.0.0'
    __license__ = 'GPL3'
    __description__ = 'Automatic backup plugin for Pwnagotchi configuration and data'

    def __init__(self):
        self.ready = False
        self.status = StatusFile('/root/.cyco-backup-status')

    def on_loaded(self):
        # Default configuration
        if 'backup_path' not in self.options:
            self.options['backup_path'] = '/root/backups/'

        if 'interval_days' not in self.options:
            self.options['interval_days'] = 7

        if 'max_backups' not in self.options:
            self.options['max_backups'] = 5

        # Create backup directory if it doesn't exist
        os.makedirs(self.options['backup_path'], exist_ok=True)

        self.ready = True
        logging.info("[cyco-backup] Plugin loaded successfully")

    def on_internet_available(self, agent):
        if not self.ready:
            return

        # Check if it's time to backup
        if self.status.newer_then_days(self.options['interval_days']):
            logging.info("[cyco-backup] Backup already done recently")
            return

        self._create_backup(agent)

    def _create_backup(self, agent):
        try:
            display = agent.view()
            display.set('status', 'Creating backup...')
            display.update()
            self.pwnagotchi_name = agent.name if agent.name else 'pwnagotchi'

            # Generate backup filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
            backup_filename = f"{self.pwnagotchi_name}-{timestamp}.tgz"
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
                self._cleanup_old_backups()
            else:
                raise Exception(f"Tar command failed: {stderr.decode()}")

        except Exception as e:
            logging.error(f"[cyco-backup] Backup failed: {e}")
            display.set('status', 'Backup failed!')
            display.update()

    def _cleanup_old_backups(self):
        """Remove old backups keeping only max_backups newest ones"""
        try:
            name_prefix = self.pwnagotchi_name if self.pwnagotchi_name else 'pwnagotchi'
            backup_files = []
            for filename in os.listdir(self.options['backup_path']):
                if filename.startswith(name_prefix) and filename.endswith('.tgz'):
                    filepath = os.path.join(self.options['backup_path'], filename)
                    backup_files.append((filepath, os.path.getmtime(filepath)))

            # Sort by modification time (newest first)
            backup_files.sort(key=lambda x: x[1], reverse=True)

            # Remove old backups
            for filepath, _ in backup_files[self.options['max_backups']:]:
                os.remove(filepath)
                logging.info(f"[cyco-backup] Removed old backup: {filepath}")

        except Exception as e:
            logging.error(f"[cyco-backup] Cleanup failed: {e}")

    def on_ui_setup(self, ui):
        # Add UI element to show last backup time
        pass

    def on_unload(self, ui):
        logging.info("[cyco-backup] Plugin unloaded")
