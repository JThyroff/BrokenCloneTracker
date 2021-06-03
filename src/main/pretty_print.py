import enum
from datetime import datetime

from colorama import Fore, Style

separator_width = 32

SEPARATOR = Fore.LIGHTBLACK_EX + Style.DIM + separator_width * "∇Δ" + Style.RESET_ALL


class LogLevel(enum.Enum):
    DUMP = 5
    DEBUG = 4
    VERBOSE = 3
    INFO = 2
    RELEVANT = 1
    CRUCIAL = 0
    NONE = -1

    def compare(self, other):
        return self.value <= other.value


def stuff_text(text: str):
    return text.replace("\n", "\n" + get_empty_prefix())


def get_empty_prefix():
    return len(get_prefix()) * " "


def get_prefix():
    return get_current_time()


def get_current_time():
    now = datetime.now()
    dt_string = now.strftime("[%H:%M|%S]  ")
    return dt_string


class MyPrinter:
    LOG_LEVEL = LogLevel.NONE

    def __init__(self, level: LogLevel):
        self.LOG_LEVEL = level

    def separator(self, level: LogLevel = LogLevel.NONE):
        if level.compare(self.LOG_LEVEL):
            print(get_prefix() + SEPARATOR)

    def yellow(self, text: str, level: LogLevel = LogLevel.NONE):
        if level.compare(self.LOG_LEVEL):
            print(get_prefix() + Fore.YELLOW + Style.DIM + stuff_text(text) + Style.RESET_ALL)

    def white(self, text: str, level: LogLevel = LogLevel.NONE):
        if level.compare(self.LOG_LEVEL):
            print(get_prefix() + Style.RESET_ALL + stuff_text(text))

    def blue(self, text: str, level: LogLevel = LogLevel.NONE):
        if level.compare(self.LOG_LEVEL):
            print(get_prefix() + Fore.BLUE + Style.DIM + stuff_text(text) + Style.RESET_ALL)

    def red(self, text: str, level: LogLevel = LogLevel.NONE):
        if level.compare(self.LOG_LEVEL):
            print(get_prefix() + Fore.RED + Style.DIM + stuff_text(text) + Style.RESET_ALL)
