#!/usr/bin/env python
"""Run on an already rooted TV: python install.py [install|uninstall]."""
from __future__ import print_function
import os
import sys
import shutil
import subprocess
import signal
import time

STATE = '/var/lib/webos-tvhome-companion'
HOOK = '/var/lib/webosbrew/init.d/55-webos-tvhome-companion'
APP = '/media/developer/apps/usr/palm/applications/com.gathin.tvhome'

def stop():
    try:
        pid = int(open(STATE + '/pid').read())
        cmd = open('/proc/%d/cmdline' % pid, 'rb').read().split(b'\0')
        if (STATE + '/watch.py').encode('utf8') in cmd:
            os.kill(pid, signal.SIGTERM)
            time.sleep(.5)
    except (IOError, OSError, ValueError):
        pass

def main():
    if len(sys.argv) > 2 or (len(sys.argv) == 2 and sys.argv[1] not in ('install', 'uninstall')):
        sys.exit('Usage: python install.py [install|uninstall]')
    if not hasattr(os, 'geteuid') or os.geteuid() != 0:
        sys.exit('Run on the TV using your existing root shell.')
    if len(sys.argv) == 2 and sys.argv[1] == 'uninstall':
        if os.path.exists(STATE + '/enabled'):
            os.unlink(STATE + '/enabled')
        stop()
        if os.path.exists(HOOK):
            os.unlink(HOOK)
        backup = STATE + '/apps.js.before-install'
        if os.path.isfile(backup) and os.path.isdir(APP):
            shutil.copyfile(backup, APP + '/apps.js')
        print('Companion stopped; boot hook removed; original catalog restored.')
        print('State and backup retained in ' + STATE + '; launcher remains installed.')
        print('Reopen Home to reload the restored catalog.')
        return
    if not os.path.isfile(APP + '/appinfo.json'):
        sys.exit('Install the webOS launcher com.gathin.tvhome first.')
    if not os.path.isfile('/usr/bin/luna-send') or not os.path.isdir('/var/lib/webosbrew/init.d'):
        sys.exit('Requires luna-send and existing Homebrew Channel startup hooks.')
    if os.path.exists('/var/lib/webosbrew/init.d/55-custom-home'):
        sys.exit('An earlier custom Home watcher is present. Disable it before installing a second watcher.')
    source = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tv')
    for name in ('watch.py', 'sync-apps.py'):
        with open(os.path.join(source, name), 'rb') as f:
            compile(f.read(), name, 'exec')
    if not os.path.isdir(STATE):
        os.makedirs(STATE, 0o700)
    backup = STATE + '/apps.js.before-install'
    if not os.path.exists(backup):
        shutil.copyfile(APP + '/apps.js', backup)
        os.chmod(backup, 0o600)
    stop()
    for name in ('watch.py', 'sync-apps.py'):
        shutil.copyfile(os.path.join(source, name), STATE + '/' + name)
        os.chmod(STATE + '/' + name, 0o700)
    with open(HOOK, 'w') as f:
        f.write('#!/bin/sh\n[ -f ' + STATE + '/enabled ] || exit 0\n'
                'nohup /usr/bin/python ' + STATE + '/watch.py </dev/null >/dev/null 2>&1 &\n')
    os.chmod(HOOK, 0o700)
    open(STATE + '/enabled', 'w').close()
    null = open(os.devnull, 'r+')
    subprocess.Popen(['/usr/bin/python', STATE + '/watch.py'], stdin=null,
                     stdout=null, stderr=null, close_fds=True, preexec_fn=os.setsid)
    time.sleep(1)
    pid = int(open(STATE + '/pid').read())
    os.kill(pid, 0)
    print('Installed. Home will open when the TV is active; app list refreshes every 15 seconds.')

if __name__ == '__main__':
    main()
