import sublime
import sublime_plugin
from AutoDarkLinux.sublime_lib.st3 import sublime_lib
import logging

import os
import threading
import time
import subprocess
import json
import fcntl
import functools
import pathlib
import signal
import itertools
import shutil
import contextlib


from typing import Optional, cast

colorSchemeMap = {1: "dark", 2: "light"}
daemon = None
stop_daemon = True

logger = logging.getLogger(__package__)
handler = logging.StreamHandler()
formatter = logging.Formatter(
    fmt="[{asctime} {name}] {levelname}: {message}",
    datefmt=logging.Formatter.default_time_format,
    style="{",
    validate=True,
)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.WARN)
logger.propagate = False


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
    def run(self, new_mode='system'):
        logger.info(f"setting scheme to '{new_mode}'")
        plugin_settings = sublime_lib.NamedSettingsDict("AutoDarkLinux")
        current_mode = plugin_settings.get("auto_dark_mode", "system")
        if new_mode is None or new_mode == "system":
            plugin_settings["auto_dark_mode"] = "system"
        else:
            plugin_settings["auto_dark_mode"] = new_mode
        plugin_settings.save()

        if new_mode == "system":
            if (new_mode := read_system_theme()) is None:
                return
        sublime.set_timeout(
            functools.partial(change_color_scheme, new_mode, current_mode)
        )

    def input(self, _):
        return AutoDarkLinuxInputHandler()

    def is_visible(self) -> bool:
        return sublime.platform() == "linux"

    def is_checked(self, new_mode:str):
        plugin_settings = sublime_lib.NamedSettingsDict("AutoDarkLinux")
        return new_mode == plugin_settings.get("auto_dark_mode", "system")

    def is_enabled(self) -> bool:
        return shutil.which("busctl") is not None

class AutoDarkLinuxEventListener(sublime_plugin.EventListener):
    def on_exit(self):
        logger.info("Exiting. Cleaning up")
        sublime.save_settings("Preferences.sublime-settings")
        unmonitor()
        logger.info("Exited")

def read_system_theme():
    try:
        output = subprocess.check_output(
            [
                "/usr/bin/busctl",
                "--user",
                "--json=short",
                "call",
                "org.freedesktop.portal.Desktop",
                "/org/freedesktop/portal/desktop",
                "org.freedesktop.portal.Settings",
                "ReadOne",
                "ss",
                "org.freedesktop.appearance",
                "color-scheme",
            ],
            universal_newlines=True,
            stderr=subprocess.STDOUT,
        )
        result = json.loads(output)
        system_scheme = result["data"][0]["data"]
        return colorSchemeMap[system_scheme]
    except subprocess.SubprocessError:
        logger.exception("Unable to read system xdg-portal settings")
        return None

def unmonitor():
    global daemon
    if daemon is not None:
        global stop_daemon
        stop_daemon = True
        if threading.current_thread() == threading.main_thread():
            daemon.join()
        daemon = None
        logger.info("Daemon stopped")

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
            for data in itertools.takewhile(
                bool, map(proc.stdout.readline, itertools.repeat(-1))
            ):
                # ignore duplicate events, only take the last one
                pass
            if not data:
                time.sleep(0.5)
                continue
            data = data.decode("utf-8").strip()
            data = json.loads(data)
            system_scheme = data["payload"]["data"][2]["data"]
            mode = colorSchemeMap[system_scheme]
            sublime.set_timeout(functools.partial(change_color_scheme, mode, current_mode))
            current_mode = mode
        else:
            proc.kill()
            unmonitor()

def listen_auto_mode(new_mode: str, _: Optional[str] = None):
    global daemon, stop_daemon
    unmonitor()
    if new_mode == "system":
        stop_daemon = False
        daemon = threading.Thread(target=monitor, name="AutoDarkLinuxMonitor")
        daemon.start()

def change_color_scheme(new_mode: str, old_mode: Optional[str] = None):
    settings = sublime_lib.NamedSettingsDict("Preferences")
    ui_info = sublime.ui_info()
    if (theme := settings.get(f"{new_mode}_theme")) != ui_info.get("theme").get(
        "resolved_value"
    ):
        settings["theme"] = theme
    if (color_scheme := settings.get(f"{new_mode}_color_scheme")) != ui_info.get(
        "color_scheme"
    ).get("resolved_value"):
        settings["color_scheme"] = color_scheme

    if new_mode != old_mode:
        logger.info(f"Color scheme change detected: previous={old_mode}, new={new_mode}")

def plugin_loaded():
    if sublime.platform() != "linux":
        return sublime.message_dialog(
            "AutoDarkLinux plugin only works on Linux"
        )
    if not shutil.which("busctl"):
        return sublime.message_dialog(
            "AutoDarkLinux plugin requires the 'busctl' command from systemd"
        )
    plugin_settings = sublime_lib.NamedSettingsDict("AutoDarkLinux")
    plugin_settings.subscribe("auto_dark_mode", listen_auto_mode)
    current_mode = cast(str, plugin_settings.get("auto_dark_mode", default="system"))
    sublime.run_command("auto_dark_linux", args={"new_mode": current_mode})
    listen_auto_mode(current_mode)
    plugin_settings.subscribe("auto_dark_mode", listen_auto_mode)

def plugin_unloaded():
    # save settings before the plugin is unloaded
    sublime.save_settings("Preferences.sublime-settings")
    unmonitor()
