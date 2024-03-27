import sublime

from typing import Callable, Any, Literal, TypeVar, cast
from functools import wraps, reduce
from types import MappingProxyType
import operator
import json
import subprocess
import logging

Prev = TypeVar("Prev")
New = TypeVar("New")


def settings_watcher(prop_selector: str):
    prop_getter = tuple(map(operator.itemgetter, prop_selector.split(".")))
    app_settings: Any = None

    def decorator(fn: Callable[[Prev, New], Any]):
        saved_value: Any = None

        def setup_app_settings():
            nonlocal app_settings
            app_settings = sublime.load_settings(f"{__package__}.sublime-settings")

        @wraps(fn)
        def wrapper():
            nonlocal saved_value
            if app_settings is None:
                setup_app_settings()
            new_value = reduce(lambda setting, f: f(setting), prop_getter, app_settings)
            if saved_value is None or new_value != saved_value:
                previous_value = saved_value
                saved_value = new_value
                return fn(new_value, previous_value)

        return wrapper

    return decorator


colorSchemeMap = MappingProxyType({1: "dark", 2: "light"})


def parse_dbus_call(output: str) -> Literal["dark", "light"]:
    result = json.loads(output)
    system_scheme: Literal[1, 2] = result["data"][0]["data"]
    return cast(Any, colorSchemeMap[system_scheme])


def parse_dbus_monitor(output: str) -> Literal["dark", "light"]:
    result = json.loads(output)
    system_scheme: Literal[1, 2] = result["payload"]["data"][2]["data"]
    return cast(Any, colorSchemeMap[system_scheme])


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
        return parse_dbus_call(output)
    except subprocess.SubprocessError:
        logging.getLogger(__package__).exception("Unable to read theme portal settings")
        return None
