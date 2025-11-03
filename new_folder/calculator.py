import argparse
import sys


def add(a: float, b: float) -> float:
    return a + b


def sub(a: float, b: float) -> float:
    return a - b


def mul(a: float, b: float) -> float:
    return a * b


def div(a: float, b: float) -> float:
    if b == 0:
        raise ZeroDivisionError("Cannot divide by zero")
    return a / b


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Simple calculator. Use a subcommand (add, sub, mul, div) or run with no args for examples.")
    sub = parser.add_subparsers(dest="cmd")

    for name in ("add", "sub", "mul", "div"):
        p = sub.add_parser(name, help=f"{name} two numbers")
        p.add_argument("a", type=float)
        p.add_argument("b", type=float)
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.cmd:
        print("Examples:")
        print("  python new_folder/calculator.py add 2 3")
        print("  python new_folder/calculator.py sub 10 4")
        print("  python new_folder/calculator.py mul 6 7")
        print("  python new_folder/calculator.py div 8 2")
        return 0

    try:
        a = float(args.a)
        b = float(args.b)
        match args.cmd:
            case "add":
                result = add(a, b)
            case "sub":
                result = sub(a, b)
            case "mul":
                result = mul(a, b)
            case "div":
                result = div(a, b)
            case _:
                parser.error(f"Unknown command: {args.cmd}")
                return 2
        print(result)
        return 0
    except ZeroDivisionError as e:
        print(f"Error: {e}")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
