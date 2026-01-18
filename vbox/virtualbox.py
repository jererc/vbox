import logging
import os
import re
import subprocess
import sys
import time

logger = logging.getLogger(__name__)


class Virtualbox:
    bin_file = {'linux': '/usr/bin/VBoxManage',
                'win32': r'C:\Program Files\Oracle\VirtualBox\VBoxManage.exe'}[sys.platform]

    def __init__(self, headless=True):
        if not os.path.exists(self.bin_file):
            raise FileNotFoundError(f'{self.bin_file} not found')
        self.creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' and headless else 0

    def _list(self, command):
        stdout = subprocess.check_output([self.bin_file, 'list', command], creationflags=self.creationflags)
        return re.findall(r'"([^"]+)"', stdout.decode('utf-8'))

    def list_vms(self):
        return self._list('vms')

    def list_running_vms(self):
        return self._list('runningvms')

    def _wait_for_stopped(self, vm, timeout=20, retry_interval=2):
        end_ts = time.time() + timeout
        while time.time() < end_ts:
            if vm not in self.list_running_vms():
                return
            time.sleep(retry_interval)
        raise Exception(f'timed out waiting for {vm=} to stop')

    def _run_cmd(self, *args):
        cmd = [self.bin_file, *args]
        logger.debug(f'running {cmd=}')
        try:
            subprocess.run(cmd, check=True, stdout=sys.stdout, creationflags=self.creationflags)
        except subprocess.CalledProcessError:
            logger.exception(f'failed to run {cmd=}')
            raise

    def _get_vm_config_file(self, vm):
        cmd = [self.bin_file, 'showvminfo', vm, '--machinereadable']
        logger.debug(f'running {cmd=}')
        result = subprocess.run(cmd, capture_output=True, text=True, creationflags=self.creationflags)
        if result.returncode != 0:
            raise RuntimeError(f"Failed to get VM info: {result.stderr.strip()}")
        for line in result.stdout.splitlines():
            if line.startswith('CfgFile='):
                config_file = line.split('=', 1)[1].strip('"')
                if not os.path.isfile(config_file):
                    raise RuntimeError(f'Config for {vm=} does not exist: {config_file=}')
                return config_file
        raise RuntimeError(f"Config file not found for VM '{vm}'")

    def get_vm_mtime(self, vm):
        try:
            return os.path.getmtime(self._get_vm_config_file(vm))
        except Exception:
            logger.exception(f'failed to get config file for {vm=}')
            return time.time()

    def start_vm(self, vm):
        self._run_cmd('startvm', vm)

    def save_vm(self, vm):
        self._run_cmd('controlvm', vm, 'savestate')

    def stop_vm(self, vm, wait_for_stopped=False):
        self._run_cmd('controlvm', vm, 'acpipowerbutton')
        if wait_for_stopped:
            self._wait_for_stopped(vm)

    def clone_vm(self, vm, name):
        self._run_cmd('clonevm', vm, '--name', name, '--register')

    def export_vm(self, vm, file):
        self._run_cmd('export', vm, '--output', file)

    def get_vm_state(self, vm):
        stdout = subprocess.check_output([self.bin_file, 'showvminfo', '--machinereadable', vm])
        res = re.findall(r'VMState="([^"]+)', stdout.decode('utf-8'))
        return res[0] if res else None

    def _wait_for_all_stopped(self, timeout=60, retry_interval=2):
        end_ts = time.time() + timeout
        while time.time() < end_ts:
            vms = self.list_running_vms()
            if not vms:
                logger.debug('all vms are stopped')
                return
            logger.info(f'waiting for {", ".join(vms)} to stop...')
            time.sleep(retry_interval)
        raise Exception('timed out waiting for all vms to stop')

    def stop_all_vms(self, save=False):
        vms = self.list_running_vms()
        if not vms:
            return
        callable = self.save_vm if save else self.stop_vm
        for vm in vms:
            logger.info(f'calling {callable.__name__} on {vm=}...')
            callable(vm)
        self._wait_for_all_stopped()
