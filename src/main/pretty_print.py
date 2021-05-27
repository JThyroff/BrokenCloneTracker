import enum

from colorama import Fore, Style

SEPARATOR = Fore.LIGHTBLACK_EX + Style.DIM + "∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇" + Style.RESET_ALL


class LogLevels(enum.Enum):
    VERBOSE = 3
    INFO = 2
    RELEVANT = 1

    def compare(self, other):
        return self.value <= other.value


class MyLogger:
    LOG_LEVEL = LogLevels.INFO
    logger = None

    @classmethod
    def get_logger(cls):
        if cls.logger is None:
            cls.logger = MyLogger()
        return cls.logger

    def print_separator(self, level: LogLevels = LogLevels.VERBOSE):
        if level.compare(self.LOG_LEVEL):
            print(SEPARATOR)

    def print_highlighted(self, text: str, level: LogLevels = LogLevels.VERBOSE):
        if level.compare(self.LOG_LEVEL):
            print(Fore.YELLOW + Style.DIM + text + Style.RESET_ALL)

    def print(self, text: str, level: LogLevels = LogLevels.VERBOSE):
        if level.compare(self.LOG_LEVEL):
            print(Style.RESET_ALL + text)
