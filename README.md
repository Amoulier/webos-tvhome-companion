# webOS TV Home companion

TV-local Home-button handling, startup/wake handling and installed-app synchronization for the
[webOS launcher](https://github.com/OmkarK97/webos-vibehack), inspired by
[CleanYourTV](https://github.com/Gathin23/cleanyourtv). This is a companion to that launcher,
not another launcher or an Android debloat script.

Developed on **LG UN7000PUC, webOS 5.6.2, firmware 04.64.00, 32-bit ARM** with an existing
rooted Homebrew Channel setup. Other TV generations and firmware have not been verified.

## What it does

- Recognizes the physical remote's Home key (evdev code 773) and opens `com.gathin.tvhome`.
- Opens Home after startup and wake, including the case where LG restores the last HDMI input
  after Home has already opened. Recovery runs for at most 30 seconds after detected wake;
  another remote key cancels the recovery window.
- Handles a suspend/resume gap even if the power-state API reports `Active` before and after sleep.
- Refreshes the launcher catalog from LG's launch points every 15 seconds, including app names
  and local icons. Newly installed launchable apps appear; removed apps disappear.
- Keeps entries even if their icons cannot be copied, preserves the existing Inputs menu,
  and only rewrites the catalog when its content changes. If needed, it restarts Home to
  reload the updated catalog, without bringing it over another app.
- Runs entirely on the TV, with no always-on computer or Raspberry Pi.

The implementation listens to input devices without grabbing or suppressing their events.
LG's original home ribbon or the last input can appear briefly before Home opens. This does
not replace the firmware's native default launcher.

## Requirements

An **already rooted TV**, Homebrew Channel's `/var/lib/webosbrew/init.d` startup hooks,
`/usr/bin/python` (Python 2.7 or Python 3), `/usr/bin/luna-send`, and the installed webOS port
with app ID `com.gathin.tvhome`. Developer Mode alone does not provide these privileges.
Rooting and launcher installation are outside this repository; no exploit is included.

## Install on the TV

Copy this repository to a temporary folder on the TV using your existing administration
connection. In your **TV root shell**, from that folder:

```sh
python install.py install
```

This installs two helpers in `/var/lib/webos-tvhome-companion`, creates an opt-in `enabled`
file, saves the previous `apps.js` there, and adds the Homebrew startup hook
`/var/lib/webosbrew/init.d/55-webos-tvhome-companion`. It does not change the launcher's
`config.js`, user dock order, app installations, privacy settings, or media libraries.
Normal launcher hidden-app settings continue to apply.

To preview the catalog comparison without writing files or restarting Home:

```sh
python /var/lib/webos-tvhome-companion/sync-apps.py --dry-run
```

To stop and undo the integration, run the original installer from your copied checkout:

```sh
python install.py uninstall
```

This removes the boot hook, stops this watcher's verified process and restores the original
catalog. It retains its small state folder and backup for inspection. The launcher itself
stays installed. Reopen Home after uninstalling to reload that original catalog.

If an earlier `/var/lib/webosbrew/init.d/55-custom-home` exists, installation stops rather
than running two competing watchers. Keep a copy of that hook, stop its watcher and disable
the old hook before migrating. Do not run multiple Home watchers simultaneously.

## Verification and limits

See [the device report](docs/lg-un7000puc.md). Home-button operation and opening Home after
power-on were confirmed on the physical TV. Kodi and Homebrew Channel were absent from the
launcher's stale catalog and appeared after synchronization; Kodi was also placed in the dock
through a separate local configuration change. That personal dock change is not installed here.

The published packaging separates the working device helpers from private administration
tooling, removes device-specific paths and Kodi-specific assertions, and adds an installer,
uninstaller and tests. It has not been subjected to a multi-day or multi-model reliability test.
An actual future app installation/removal still needs an end-to-end automatic-refresh test.

The wake detector polls power state every three seconds. An eight-second gap in execution is
treated as possible resume; unusually long stalls can therefore also open Home. Startup recovery
can override an HDMI change made by HDMI-CEC within its 30-second window. Remote key input
cancels that window, but CEC-only navigation has not been verified. Network-injected `HOME`
is not a substitute for testing the physical remote on this firmware.

Home may briefly reload after the catalog changes, resetting its focus. A TV with a different
Home key code, app installation path, input-event structure, or power API needs adaptation.
The input parser targets the tested 32-bit ARM `input_event` layout, not 64-bit webOS.

## Privacy and scope

The helpers communicate only with local Luna services and read local input events and app
icons. They do not open a network listener, send telemetry, store remote-key history, or embed
accounts, addresses, device identifiers, streaming subscriptions or media databases.

This companion does **not** claim to remove all LG telemetry or streaming-app ads. Android's
`pm disable-user` commands do not apply to webOS. The separately tested privacy-service
overrides and Kodi modifications are outside this launcher contribution.

## Development

No third-party Python dependencies are needed. On a development machine:

```sh
python -m unittest discover -s tests -v
python -m compileall -q install.py tv
```

The daemon is installed opt-in; importing `tv/watch.py` does not start it. Tests cover wake
classification, recovery targets, catalog preservation and dry-run behavior without TV access.

MIT licensed. The launcher, its artwork and its own license remain in the upstream project.
