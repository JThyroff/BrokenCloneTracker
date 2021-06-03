import enum
from datetime import datetime

from colorama import Fore, Style

SEPARATOR = Fore.LIGHTBLACK_EX + Style.DIM + "∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇" + Style.RESET_ALL


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


def get_current_time():
    now = datetime.now()
    dt_string = now.strftime("[%H:%M|%S] ")
    return dt_string


class MyLogger:
    LOG_LEVEL = LogLevel.NONE

    def __init__(self, level: LogLevel):
        self.LOG_LEVEL = level

    def separator(self, level: LogLevel = LogLevel.NONE):
        if level.compare(self.LOG_LEVEL):
            print(get_current_time() + SEPARATOR)

    def yellow(self, text: str, level: LogLevel = LogLevel.NONE):
        if level.compare(self.LOG_LEVEL):
            print(get_current_time() + Fore.YELLOW + Style.DIM + text + Style.RESET_ALL)

    def white(self, text: str, level: LogLevel = LogLevel.NONE):
        if level.compare(self.LOG_LEVEL):
            print(get_current_time() + Style.RESET_ALL + text)

    def blue(self, text: str, level: LogLevel = LogLevel.NONE):
        if level.compare(self.LOG_LEVEL):
            print(get_current_time() + Fore.BLUE + Style.DIM + text + Style.RESET_ALL)

    def red(self, text: str, level: LogLevel = LogLevel.NONE):
        if level.compare(self.LOG_LEVEL):
            print(get_current_time() + Fore.RED + Style.DIM + text + Style.RESET_ALL)
