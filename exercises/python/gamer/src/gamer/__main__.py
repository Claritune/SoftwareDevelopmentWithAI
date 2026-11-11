import argparse

import uvicorn

from gamer.app import create_app


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="gamer", description="Turn-based game server")
    parser.add_argument("--host", default="127.0.0.1", help="use 0.0.0.0 for LAN play")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    uvicorn.run(create_app(), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
