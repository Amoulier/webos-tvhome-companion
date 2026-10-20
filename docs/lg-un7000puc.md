# Device report: LG UN7000PUC

- webOS: 5.6.2
- Firmware: 04.64.00
- Architecture: ARMv7, 32-bit userspace
- Existing setup: rooted Homebrew Channel; `com.gathin.tvhome` installed
- Validation date: 2026-10-20

## Confirmed on the physical TV

1. The original launcher's catalog predated later app installations and still contained removed
   apps. LG's current launch-point list included Kodi and Homebrew Channel.
2. Synchronization updated titles and local icons, retained Inputs, removed stale entries and
   showed the current applications. Merely closing a web app could retain its old page;
   `com.palm.webappmanager/killApp` was used before reopening it to refresh the catalog.
3. The foreground-app subscription alone did not reliably identify the original Home ribbon on
   this firmware. Physical evdev Home code 773 opened the custom launcher successfully.
4. The first power detector could leave the TV on HDMI 2 after waking. Resume-gap detection and
   a bounded startup recovery window were added. After powering off for about 15 seconds and
   back on, the owner confirmed that Home opened without pressing other buttons.

The device-local paths and private account data used during administration are not published.
The original helpers were tested on the TV; the generalized installation and uninstall workflow
is separate packaging. Its automated tests do not replace a fresh device installation test.
The published Python files also compiled under the TV's Python 2.7, and its catalog synchronizer
completed a read-only dry run against the live TV: 12 launch points, catalog unchanged.

## Not established

- Continuous operation for several days, a power-cable cold boot, all webOS generations, or 64-bit TVs.
- Automatic catalog refresh after a newly installed future app (the stale-catalog repair was observed).
- HDMI-CEC-only interaction during the recovery window.
- Removal of all telemetry or advertisements, playback compatibility, or IPTV-provider reliability.

No movie/show library or media-addon settings are included or modified by these helpers.
