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
2. Enable viewing of commands and logs from the console. Open console with `` Ctrl + ` `` and type the following commands:
    ```py
    sublime.log_commands(True)
    sublime.log_input(True)
    ```
3. Start developing :hammer: (See more [docs](https://www.sublimetext.com/docs/))
4. Commit changes
5. Release a new version using the `release.sh` script
