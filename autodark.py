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
stopDaemon = False

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
logger.setLevel(logging.WARNING)
logger.propagate = False


class AutoDarkLinuxInputHandler(sublime_plugin.ListInputHandler):
    def name(self):
        return "mode"

    def validate(self, text):
        return True

    def placeholder(self):
        return "Color scheme mode"

    def list_items(self):
        return [("Dark", "dark"), ("Light", "light"), ("System", "system")]


class AutoDarkLinuxCommand(sublime_plugin.ApplicationCommand):
    def run(self, mode="system"):
        plugin_settings = sublime_lib.NamedSettingsDict("AutoDarkLinux")
        current_mode = plugin_settings.get("auto_dark_mode", "system")
        if mode is None or mode == "system":
            plugin_settings["auto_dark_mode"] = "system"
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
                systemScheme = result["data"][0]["data"]
                mode = colorSchemeMap[systemScheme]
            except subprocess.CalledProcessError:
                logger.exception("Unable to read system xdg-portal settings")
                plugin_settings.save()
                return
        else:
            plugin_settings["auto_dark_mode"] = mode
            if mode != current_mode:
                logger.info(f"Color scheme change detected: previous={current_mode}, current={mode}")

        plugin_settings.save()
        sublime.set_timeout(functools.partial(change_color_scheme, mode, current_mode))

    def input(self, _):
        return AutoDarkLinuxInputHandler()

    def is_visible(self) -> bool:
        return sublime.platform() == "linux"

    def is_enabled(self) -> bool:
        # This option is used to conditionally enable
        # menu items that depend on this command
        return shutil.which("busctl") is not None


class AutoDarkLinuxEventListener(sublime_plugin.EventListener):
    def on_exit(self):
        logger.info("Exiting, cleaning up")
        # save settings before closing the last window
        sublime.save_settings("Preferences.sublime-settings")
        unmonitor()
        logger.info("Bye, bye!")

def unmonitor():
    global daemon
    if daemon is not None and daemon.is_alive():
        global stopDaemon
        stopDaemon = True
        daemon.join()
        daemon = None
        logger.info("Daemon stopped")


def monitor():
    pidPath = pathlib.Path(sublime.cache_path()) / f'{__package__}/daemon.pid'
    with contextlib.suppress(FileNotFoundError, ValueError, ProcessLookupError):
        with open(pidPath, "r") as pid:
            daemon_pid=int(next(pid))
            os.kill(daemon_pid, signal.SIGTERM)

    with subprocess.Popen(
        [
            "/usr/bin/busctl",
            "--user",
            "--json=short",
            "--match",
            "type='signal',interface='org.freedesktop.portal.Settings',path='/org/freedesktop/portal/desktop',member='SettingChanged',arg0='org.freedesktop.appearance',arg1='color-scheme'",
            "monitor",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as proc:
        assert proc.stdout is not None
        fcntl.fcntl(proc.stdout, fcntl.F_SETFL, os.O_NONBLOCK)
        pidPath.write_text(f'{proc.pid}')
        logger.info("Daemon started with pid: %d", proc.pid)
        global stopDaemon
        while proc.poll() is None:
            if stopDaemon:
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
            systemScheme = data["payload"]["data"][2]["data"]
            mode = colorSchemeMap[systemScheme]
            sublime.set_timeout(functools.partial(change_color_scheme, mode))
        else:
            stopDaemon = True
            proc.kill()


def listen_auto_mode(new_mode: str, _: Optional[str] = None):
    global daemon
    if new_mode == "system":
        if daemon is None:
            daemon = threading.Thread(target=monitor, name="AutoDarkLinuxMonitor")
            daemon.start()
    elif daemon is not None:
        unmonitor()


def change_color_scheme(new_mode: str, old_mode: str):
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


def plugin_loaded():
    if sublime.platform() != "linux":
        return sublime.message_dialog("AutoDarkLinux plugin only works on Linux")
    if not shutil.which("busctl"):
        return sublime.message_dialog(
            "AutoDarkLinux plugin requires the 'busctl' command from systemd"
        )
    plugin_settings = sublime_lib.NamedSettingsDict("AutoDarkLinux")
    plugin_settings.subscribe("auto_dark_mode", listen_auto_mode)
    current_mode = cast(str, plugin_settings.get("auto_dark_mode", default="system"))
    listen_auto_mode(current_mode)
    sublime.run_command("auto_dark", args={"mode": current_mode})


def plugin_unloaded():
    # save settings before the plugin is unloaded
    sublime.save_settings("Preferences.sublime-settings")
    unmonitor()
