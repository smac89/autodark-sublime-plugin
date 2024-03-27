import logging
import sublime
import sublime_plugin

import os
import threading
import time
import subprocess
import fcntl
import functools
import pathlib
import signal
import itertools
import shutil
import contextlib
import uuid

from .helpers import settings_listener, read_system_theme, parse_dbus_monitor
from .lifecycle import lifecycle, CycleStage
from .logger import logger

from typing import Optional, Any

plugin_settings_file = f"{__package__}.sublime-settings"
plugin_settings: Any

daemon = None
stop_daemon = True


class AutoDarkLinuxInputHandler(sublime_plugin.ListInputHandler):
    def name(self):
        # this is used to determine the name of the argument passed to the
        # auto_dark_linux command when a list item is picked
        return "new_mode"

    def validate(self, text):
        return True

    def placeholder(self):
        return "Color scheme mode"

    def list_items(self):
        return [("Dark", "dark"), ("Light", "light"), ("System", "system")]


class AutoDarkLinuxCommand(sublime_plugin.ApplicationCommand):
    def run(self, new_mode="system"):
        logger.info(f"setting mode to '{new_mode}'")
        current_mode = plugin_settings.get("auto_dark_mode", "system")
        if new_mode is None or new_mode == "system":
            plugin_settings["auto_dark_mode"] = "system"
        else:
            plugin_settings["auto_dark_mode"] = new_mode
        sublime.save_settings(plugin_settings_file)

        if new_mode == "system":
            if (new_mode := read_system_theme()) is None:
                return

        if current_mode == "system":
            current_mode = read_system_theme()
        sublime.set_timeout(functools.partial(change_color_scheme, new_mode, current_mode))

    def input(self, _):
        return AutoDarkLinuxInputHandler()

    def is_visible(self) -> bool:
        return sublime.platform() == "linux"

    def is_checked(self, new_mode: str):
        return new_mode == plugin_settings.get("auto_dark_mode", "system")

    def is_enabled(self) -> bool:
        return shutil.which("busctl") is not None


class AutoDarkLinuxEventListener(sublime_plugin.EventListener):
    def on_exit(self):
        logger.info("Exiting. Cleaning up")
        unmonitor()
        logger.info("Exited")


@lifecycle(CycleStage.LOADED)
def plugin_loaded():
    if sublime.platform() != "linux":
        return sublime.message_dialog("AutoDarkLinux plugin only works on Linux")
    if not shutil.which("busctl"):
        return sublime.message_dialog(
            "AutoDarkLinux plugin requires the 'busctl' command from systemd"
        )
    global plugin_settings
    plugin_settings = sublime.load_settings(plugin_settings_file)
    return plugin_settings.get("auto_dark_mode", "system")


@lifecycle(CycleStage.UNLOADED)
def plugin_unloaded():
    # save settings before the plugin is unloaded
    sublime.save_settings("Preferences.sublime-settings")
    unmonitor()


def monitor():
    pid_file = pathlib.Path(sublime.cache_path()) / f"{__package__}/daemon.pid"
    with contextlib.suppress(FileNotFoundError, ValueError, ProcessLookupError):
        with open(pid_file, "r") as pid:
            daemon_pid = int(next(pid))
            os.kill(daemon_pid, signal.SIGTERM)

    current_mode = read_system_theme()
    with subprocess.Popen(
        [
            "/usr/bin/busctl",
            "--user",
            "--json=short",
            "--match",
            ",".join(
                [
                    "type='signal'",
                    "interface='org.freedesktop.portal.Settings'",
                    "path='/org/freedesktop/portal/desktop'",
                    "member='SettingChanged'",
                    "arg0='org.freedesktop.appearance'",
                    "arg1='color-scheme'",
                ]
            ),
            "monitor",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as proc:
        assert proc.stdout is not None
        fcntl.fcntl(proc.stdout, fcntl.F_SETFL, os.O_NONBLOCK)
        pid_file.write_text(f"{proc.pid}")
        logger.info("Daemon started with pid: %d", proc.pid)
        global stop_daemon
        while proc.poll() is None:
            if stop_daemon:
                proc.kill()
                break
            data = None
            for data in itertools.takewhile(bool, map(proc.stdout.readline, itertools.repeat(-1))):
                # ignore duplicate events, only take the last one
                pass
            if not data:
                time.sleep(0.5)
                continue
            mode = parse_dbus_monitor(data.decode("utf-8").strip())
            sublime.set_timeout(functools.partial(change_color_scheme, mode, current_mode))
            current_mode = mode
        else:
            proc.kill()
            unmonitor()


def unmonitor():
    global daemon
    if daemon is not None:
        global stop_daemon
        stop_daemon = True
        if threading.current_thread() == threading.main_thread():
            daemon.join()
        daemon = None
        logger.info("Daemon stopped")


def change_color_scheme(new_scheme: str, old_scheme: Optional[str] = None):
    settings = sublime.load_settings("Preferences.sublime-settings")
    ui_info = sublime.ui_info()
    if (theme := settings.get(f"{new_scheme}_theme")) != ui_info.get("theme").get("resolved_value"):
        settings["theme"] = theme
    if (color_scheme := settings.get(f"{new_scheme}_color_scheme")) != ui_info.get(
        "color_scheme"
    ).get("resolved_value"):
        settings["color_scheme"] = color_scheme

    if new_scheme != old_scheme:
        logger.info(f"Color scheme change detected: previous={old_scheme}, new={new_scheme}")
        sublime.save_settings("Preferences.sublime-settings")


@settings_listener("auto_dark_mode")
def listen_auto_mode(new_mode: str, old_mode: Optional[str] = None):
    global daemon, stop_daemon
    unmonitor()
    if new_mode == "system":
        stop_daemon = False
        daemon = threading.Thread(target=monitor, name="AutoDarkLinuxMonitor")
        daemon.start()
    else:
        sublime.run_command("auto_dark_linux", args={"new_mode": new_mode})


@plugin_loaded.notify(include_result=True)
@plugin_unloaded.notify()
def watch_settings(life_cycle=CycleStage.NONE, result="", tag=[uuid.uuid4()]):
    # the use of mutable key 'tag' is to persist the value across
    # multiple function calls
    if life_cycle == CycleStage.LOADED:
        if plugin_settings.get("debug", False):
            logger.setLevel(logging.INFO)
        logger.info(f"Plugin load detected. Initial mode={result}")
        sublime.run_command("auto_dark_linux", args={"new_mode": result})
        plugin_settings.add_on_change(str(tag[0]), listen_auto_mode)
    elif life_cycle == CycleStage.UNLOADED:
        logger.info(f"Plugin unload detected. Removing listener with tag='{str(tag[0])}'")
        plugin_settings.clear_on_change(str(tag[0]))