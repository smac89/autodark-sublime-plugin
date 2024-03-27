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
- Edit your preferences and configure the following keys:
    - `dark_color_scheme`
    - `light_color_scheme`
    - `dark_theme`
    - `light_theme`
- Either from the context menu (under View), or from the command pallet (search for AutoDark)
    - `System`: Sublime follows the system settings
    - `Light`: Sublime sticks to only light mode
    - `Dark`: Sublime sticks to only dark mode
- Any option selected is set as the default and will be remembered

## FAQ

- **Q:** Switching to system mode does not automatically infer my preferred colorscheme

    **A**: This might be caused when you have two competing xdg-desktop-portal implementations installed on your system. _e.g. `kde` and `gtk`, but `gtk` wins because its name comes first alphabetically._:shrug:

    You can check the `/usr/share/xdg-desktop-portal/portals/` folder to see which portals are installed. e.g. `kde.portal`, `gkt.portal`, etc. Once you determine which implementation you want to use (this would most likely be determined by your current desktop), create a file called `~/.config/xdg-desktop-portal/portals.conf` (see [portals.conf manpage](https://man.archlinux.org/man/portals.conf.5)), and add the following to it:

    ```ini
    [preferred]
    default=enter-your-choice-here-without.portal-suffix
    ```
    Restart xdg-desktop-portal service using `systemctl restart --user xdg-desktop-service`, or logout and log back in to see the new changes.

    This should hopefully fix the issue with automatically switching modes.

---

## Development
These are just reminders for myself, but feel free to follow along if you need to start developing packages

1. Clone this project into the folder `~/.config/sublime-text-3/Packages/AutoDarkLinux`. If you already cloned the project elsewhere, just symlink it inside the above folder using the command:

    ```sh
    ln --symbolic --target-directory ~/.config/sublime-text-3/Packages/  /path/to/autodark-sublime-plugin/
    mv ~/.config/sublime-text-3/Packages/{autodark-sublime-plugin,AutoDarkLinux}
    ```

    See [link](https://www.sublimetext.com/docs/packages.html) for more info.

    _Note: The reason for using the name **AutoDarkLinux** is because that's the name this plugin was published under. It's also the name you have to use if you want to import other modules from within this package during development and at runtime._
2. (Optional) Install the virtualenv using `pipenv install --dev`. This is useful for auto completion during development
2. Restart sublime to make sure the plugin is loaded. Enable viewing of commands and logs from the console. Open console with `` Ctrl + ` `` and type the following commands:

    ```py
    sublime.log_commands(True)
    sublime.log_input(True)
    ```
3. Start developing :hammer: (see [docs](https://www.sublimetext.com/docs/), especially [api_ref](https://www.sublimetext.com/docs/api_reference.html), and this [one](https://forum.sublimetext.com/t/solved-where-and-how-do-i-store-internal-package-settings/48843))
3. Enable [`INFO`](https://docs.python.org/3.8/library/logging.html#levels) logging to see more logs in the console
4. Commit changes
5. Release a new version using the `scripts/release.sh` script
6. Remove the symlinked dev package from the sublime folder
