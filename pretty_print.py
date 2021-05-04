from colorama import Fore, Style

SEPARATOR = Fore.LIGHTBLACK_EX + Style.DIM + "∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇Δ∇" + Style.RESET_ALL


def print_separator():
    print(SEPARATOR)


def print_highlighted(text: str):
    print(Fore.YELLOW + Style.DIM + text + Style.RESET_ALL)
