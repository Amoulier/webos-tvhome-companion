from __future__ import print_function
import os, json, re, subprocess, shutil
BASE = '/media/developer/apps/usr/palm/applications/com.gathin.tvhome'
def luna(method, payload=None):
    return json.loads(subprocess.check_output(['/usr/bin/luna-send', '-n', '1', '-w', '2000',
        'luna://com.webos.applicationManager/' + method, json.dumps(payload or {})], close_fds=True))
def read_bytes(path):
    with open(path, 'rb') as f:
        return f.read()

def sync(dry_run=False):
    result = luna('listLaunchPoints')
    if not result.get('returnValue') or not result.get('launchPoints'):
        return
    with open(BASE + '/apps.js') as f:
        old = f.read()
    match = re.search(r'(?:"inputs"|inputs)\s*:\s*(\[.*\])\s*};?\s*$', old, re.S)
    inputs = match.group(1) if match else '[]'
    apps = []
    for p in result['launchPoints']:
        if p.get('hidden') or not p.get('id'):
            continue
        ident = p['id']
        filename = re.sub(r'[^a-zA-Z0-9._-]', '_', ident) + '.png'
        destination = BASE + '/icons/' + filename
        source = next((p.get(k) for k in ('largeIcon', 'icon') if p.get(k) and os.path.isfile(p[k])), None)
        if not dry_run and source and os.path.realpath(source) != os.path.realpath(destination):
            if not os.path.exists(destination) or read_bytes(source) != read_bytes(destination):
                shutil.copyfile(source, destination)
                os.chmod(destination, 0o644)
        apps.append({'id':ident, 'title':p.get('title') or ident,
            'icon':'icons/' + filename if os.path.isfile(destination) else 'icon.png',
            'iconColor':p.get('iconColor') or p.get('bgColor') or ''})
    text = 'window.TV_APPS={"apps":' + json.dumps(apps, sort_keys=True) + ',"inputs":' + inputs + '};\n'
    if dry_run:
        print(json.dumps({'appCount':len(apps),'changed':text != old}))
        return
    if text == old:
        return
    with open(BASE + '/apps.js.new', 'w') as f:
        f.write(text)
    os.chmod(BASE + '/apps.js.new', 0o644)
    replace = getattr(os, 'replace', os.rename)
    replace(BASE + '/apps.js.new', BASE + '/apps.js')
    front = luna('getForegroundAppInfo').get('appId')
    subprocess.check_output(['/usr/bin/luna-send','-n','1','-w','2000',
        'luna://com.palm.webappmanager/killApp',json.dumps({'appId':'com.gathin.tvhome'})],close_fds=True)
    if front == 'com.gathin.tvhome':
        luna('launch', {'id':'com.gathin.tvhome'})
    print('SYNCED', len(apps))
if __name__ == '__main__':
    import sys
    sync('--dry-run' in sys.argv)
