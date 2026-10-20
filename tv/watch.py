from __future__ import print_function
import os, sys, time, json, subprocess, select, struct, glob

STATE = '/var/lib/webos-tvhome-companion'
TARGET = 'com.gathin.tvhome'
def is_wake(previous, current, gap=0):
    return current == 'Active' and (previous != 'Active' or gap > 8)

def is_stock_input(app):
    return app.startswith('com.webos.app.hdmi') or app in (
        'com.webos.app.livetv', 'com.webos.app.home', 'com.webos.app.fullhome')

def main():
    import fcntl
    os.closerange(3, 1024)
    lock = open(STATE + '/lock', 'w')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError:
        sys.exit(0)
    with open(STATE + '/pid', 'w') as f:
        f.write(str(os.getpid()))
    last = 0
    fds = {}
    next_scan = 0
    pending = 0
    pending_reason = None
    next_sync = 0
    next_power = 0
    previous_power = None
    last_tick = None
    startup_until = 0
    startup_check = 0
    while os.path.exists(STATE + '/enabled'):
        now = time.time()
        tick = float(open('/proc/uptime').read().split()[0])
        if last_tick is not None and tick - last_tick > 8:
            previous_power = None
            next_power = 0
        last_tick = tick
        if now >= next_scan:
            for path in glob.glob('/dev/input/event*'):
                if path not in fds.values():
                    try: fds[os.open(path, os.O_RDONLY | os.O_NONBLOCK)] = path
                    except OSError: pass
            next_scan = now + 5
        if now >= next_sync:
            next_sync = now + 15
            try:
                subprocess.check_call(['/usr/bin/python', STATE + '/sync-apps.py'], close_fds=True)
            except Exception: pass
        if now >= next_power:
            next_power = now + 3
            try:
                raw = subprocess.check_output(['/usr/bin/luna-send', '-n', '1', '-w', '2000',
                    'luna://com.webos.service.tvpower/power/getPowerState', '{}'], close_fds=True)
                power = json.loads(raw)
                current = power.get('state') if power.get('returnValue') else None
                if is_wake(previous_power, current):
                    pending = time.time() + 2
                    pending_reason = 'power-on'
                    startup_until = time.time() + 30
                    startup_check = time.time() + 5
                if current is not None:
                    previous_power = current
            except Exception: pass
        if startup_until and now >= startup_check:
            startup_check = now + 3
            if now > startup_until:
                startup_until = 0
            elif previous_power == 'Active':
                try:
                    raw = subprocess.check_output(['/usr/bin/luna-send','-n','1','-w','2000',
                        'luna://com.webos.applicationManager/getForegroundAppInfo','{}'],close_fds=True)
                    front = json.loads(raw).get('appId','')
                    if is_stock_input(front):
                        pending = now + .1
                        pending_reason = 'startup-input-restore'
                except Exception: pass
        ready = select.select(list(fds), [], [], .1)[0]
        for fd in ready:
            try: data = os.read(fd, 4096)
            except OSError: data = ''
            if not data:
                os.close(fd); del fds[fd]; continue
            for offset in range(0, len(data) - 15, 16):
                _, _, typ, code, value = struct.unpack('IIHHi', data[offset:offset+16])
                if typ == 1 and value == 1 and code not in (116, 773):
                    startup_until = 0
                    if pending_reason in ('power-on', 'startup-input-restore'):
                        pending = 0
                if typ == 1 and code == 116 and value == 1:
                    previous_power = None
                    next_power = time.time() + 3
                if typ == 1 and code == 773 and value in (0, 1):
                    pending = time.time() + .25
                    pending_reason = 'remote-home-773'
        if pending and time.time() >= pending:
            pending = 0
            if time.time() - last < .5: continue
            if not os.path.isfile('/media/developer/apps/usr/palm/applications/' + TARGET + '/appinfo.json'): continue
            try:
                result = subprocess.check_output(['/usr/bin/luna-send', '-n', '1', '-w', '2000',
                    'luna://com.webos.applicationManager/launch', json.dumps({'id': TARGET})], close_fds=True)
                last = time.time()
                with open(STATE + '/status.json', 'w') as f:
                    json.dump({'lastRedirect':last,'source':pending_reason,
                        'success':bool(json.loads(result).get('returnValue'))},f)
            except Exception: pass

if __name__ == '__main__':
    main()
