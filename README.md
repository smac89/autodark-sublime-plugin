# autodark-sublime-plugin
Fix auto dark mode for sublime v4 on Linux. Sublime text 4 supposedly has such a feature, but it seems to not be working for me. If you also experience the same, this plugin bridges that gap and provides an adequate solution until the problem is fixed.

## Dependencies:
- Sublime text (build 4050+)
- Systemd (for `busctl` command)
- A desktop environment or a DBus service which implements `org.freedesktop.portal.Settings`. The major DE's provide this already

## Installation:
- Install [Package Control](https://packagecontrol.io/installation)
- Search for `Auto Dark` and install

## Configuration/Usage:
- Either from the context menu (under View), or from the command pallet (search for AutoDark)
    - `System`: Sublime follows the system settings
    - `Light`: Sublime sticks to only light mode
    - `Dark`: Sublime sticks to only dark mode
- Any option selected is set as the default and will be remembered
