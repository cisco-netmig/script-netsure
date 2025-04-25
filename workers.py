import os
import logging
import re
from concurrent.futures import ThreadPoolExecutor
import importlib.resources as packages
from time import sleep
from datetime import datetime
from textfsm import clitable, TextFSM

from PyQt5 import QtCore


class RunEvent(QtCore.QThread):
    """
    Background thread to execute network checks on devices using templates
    and regex patterns, then generate an Excel report.
    """

    def __init__(self, form):
        super().__init__()
        self.form = form

    def run(self):
        """Entry point for the QThread execution."""
        os.makedirs(self.form.output_dir, exist_ok=True)
        self.devices = list(filter(None, self.form.devices_text_edit.toPlainText().splitlines()))
        self._get_checks_params()
        logging.info('RunEvent: Starting device checks...')
        self.data = {}
        self._thread_executor()
        self._dump_results()
        logging.info('RunEvent: Finished device checks and report generation.')

    def _get_checks_params(self):
        """
        Gathers selected checks and prepares command templates for execution.
        Populates self.checks and self.commands.
        """
        self.checks = {}
        self.commands = {}

        if not self.form.templates_data:
            logging.info("Loading NTC templates...")
            self.form.templates_data = load_templates()
            logging.info("Templates loaded successfully.")

        for i in range(self.form.checks_tree.topLevelItemCount()):
            parent = self.form.checks_tree.topLevelItem(i)
            for j in range(parent.childCount()):
                child = parent.child(j)
                if child.checkState(0):  # Checked
                    check = child.text(0)
                    for checklist, checks in self.form.checks_data.items():
                        if check in checks:
                            self.checks.update(checks)
                            template = checks[check]['template']
                            self.checks[check]['template_props'] = self.form.templates_data[template]
                            self.commands[self.form.templates_data[template]['command']] = {}

    def _thread_executor(self):
        """
        Executes collection tasks in parallel threads using a thread pool.
        Handles exceptions and logs errors per device.
        """
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {device: executor.submit(self._collect_task, device) for device in self.devices}
            for device in self.devices:
                sleep(0.5)  # Slight delay between submissions
            executor.shutdown(wait=True)

        for device, future in futures.items():
            exception = future.exception()
            if exception:
                logging.error(f'RunEvent: Exception for {device}: {exception}')

    def _perform_check(self, raw, template_path, search_key, primary_key, regex):
        """
        Performs a single check against command output using a TextFSM template and regex.
        Returns a dictionary with status and matched data.
        """
        data = {
            'Status': 'FAIL',
            'Data': [],
            'Expect': regex,
            'Template': os.path.basename(template_path)
        }

        if regex_match := re.search(r'^r"(.*)"$', regex):
            regex = re.escape(regex_match.group(1))

        if search_key:
            table = TextFSM(open(template_path)).ParseTextToDicts(raw)
            for item in table:
                search_text = item.get('_'.join(search_key.split()).upper(), '')
                primary_text = item.get('_'.join(primary_key.split()).upper(), '') if primary_key else ''
                is_match = bool(re.search(regex, search_text))
                status = '[ PASS ]' if is_match else '[ FAIL ]'
                if is_match and data['Status'] == 'FAIL':
                    data['Status'] = 'PASS'
                entry = f'{status}  {primary_text}  ==>  "{search_text}"' if primary_text else f'{status} {search_key}: "{search_text}"'
                data['Data'].append(entry)
        else:
            for line_idx, line in enumerate(raw.splitlines()):
                if re.search(regex, line):
                    data['Data'].append(f'Line {line_idx + 1}: {line}')
                    data['Status'] = 'PASS'
        return data

    def _collect_task(self, device):
        """
        Collects command output from a single device and performs checks.
        Stores results in self.data.
        """
        from netcore import GenericHandler

        logging.info(f'RunEvent: Connecting to {device}...')
        proxy = {
            'hostname': self.form.session['JUMPHOST_IP'],
            'username': self.form.session['JUMPHOST_USERNAME'],
            'password': self.form.session['JUMPHOST_PASSWORD']
        } if self.form.session.get('JUMPHOST_IP') else None

        try:
            handler = GenericHandler(
                hostname=device,
                username=self.form.session['NETWORK_USERNAME'],
                password=self.form.session['NETWORK_PASSWORD'],
                proxy=proxy,
                handler='NETMIKO'
            )
            logging.info(f'RunEvent: Connection established to {device}')
        except Exception as e:
            logging.error(f'RunEvent: Connection failed to {device} - {e}')
            return

        logging.info(f'RunEvent: Capturing commands from {device}')
        commands_output = {
            command: handler.sendCommand(command).strip()
            for command in self.commands
        }
        handler.close()

        checks_data = {}
        for check, props in self.checks.items():
            command = props['template_props']['command']
            template_path = props['template_props']['path']
            search_key = props['search_key']
            primary_key = props['primary_key']
            regex = props['regex']
            checks_data[check] = self._perform_check(
                commands_output[command], template_path, search_key, primary_key, regex
            )

        self.data[device] = checks_data

    def _dump_results(self):
        """
        Dumps the results into an Excel file with formatted headers.
        """
        from netcore import XLBW

        results = {}
        idx = 0
        for device, checks in self.data.items():
            for check, props in checks.items():
                idx += 1
                results[idx] = {
                    'Device': device,
                    'Check': check,
                    **props
                }

        filename = f"{os.path.basename(os.path.dirname(__file__)).title()}_{datetime.now().strftime('%Y-%m-%d_%H.%M')}.xlsx"
        self.form.output_report = os.path.join(self.form.output_dir, filename)

        logging.info(f'RunEvent: Writing results to {self.form.output_report}')
        workbook = XLBW(self.form.output_report)
        worksheet = workbook.add_worksheet('checks')
        worksheet.freeze_panes(1, 2)
        workbook.dump(results, worksheet)
        workbook.close()


class TemplateLoaderThread(QtCore.QThread):
    """
    Worker thread to load NTC templates in the background using QThread.
    Emits `templates_loaded` signal with the result.
    """
    templates_loaded = QtCore.pyqtSignal(dict)

    def run(self):
        logging.info("Loading NTC templates in background thread...")
        templates_data = load_templates()
        logging.info("Templates loaded successfully.")
        self.templates_loaded.emit(templates_data)


def load_templates():
    """
    Loads and parses NTC templates from the filesystem.

    Returns:
        dict: Parsed template metadata.
    """
    templates = {
        'CISCO GENERIC: show running-config': {
            'command': 'show running-config',
            'path': '',
            'headers': []
        }
    }

    ntc_path = os.path.join(str(packages.files('ntc_templates')), 'templates')
    index_path = os.path.join(ntc_path, 'index')
    index_table = clitable.CliTable(index_file=index_path, template_dir=ntc_path).index.index

    for row in index_table:
        platform = row[2]
        for template_name in row[0].split(':'):
            try:
                template_path = os.path.join(ntc_path, template_name)
                command = template_name.split('.')[0].replace(platform, '').replace('_', ' ').strip()
                headers = TextFSM(open(template_path)).header

                template_key = f"{platform.replace('_', ' ').upper()}: {command}"
                templates[template_key] = {
                    'command': command,
                    'path': template_path,
                    'headers': [header.replace("_", " ").title() for header in headers]
                }
            except Exception as e:
                logging.error(f"Failed to load template {template_name}: {e}")

    return dict(sorted(templates.items()))