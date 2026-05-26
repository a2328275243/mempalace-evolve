"""CLI entry point for mempalace-evolve."""

from __future__ import annotations

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(
        prog="mempalace",
        description="Self-evolving memory palace for AI agents",
    )
    sub = parser.add_subparsers(dest="command")

    # mempalace remember "content" --room decisions
    p_rem = sub.add_parser("remember", help="Store a memory")
    p_rem.add_argument("content", help="Content to remember")
    p_rem.add_argument("--room", default="general", help="Room/category")
    p_rem.add_argument("--palace", default=None, help="Palace path")

    # mempalace recall "query"
    p_rec = sub.add_parser("recall", help="Search memories")
    p_rec.add_argument("query", help="Search query")
    p_rec.add_argument("--limit", type=int, default=5)
    p_rec.add_argument("--palace", default=None, help="Palace path")

    # mempalace serve --port 8765
    p_srv = sub.add_parser("serve", help="Start REST API server")
    p_srv.add_argument("--port", type=int, default=8765)
    p_srv.add_argument("--host", default="0.0.0.0")
    p_srv.add_argument("--palace", default=None, help="Palace path")

    # mempalace evolve
    p_evo = sub.add_parser("evolve", help="Run evolution cycle")
    p_evo.add_argument("--palace", default=None, help="Palace path")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    from mempalace_evolve.sdk import MemPalace
    palace = MemPalace(args.palace)

    if args.command == "remember":
        did = palace.remember(args.content, room=args.room)
        print(f"Stored: {did}")
    elif args.command == "recall":
        results = palace.recall(args.query, limit=args.limit)
        for r in results:
            print(f"  [{r.get('distance', '?'):.3f}] {r.get('content', '')[:100]}")
    elif args.command == "serve":
        from mempalace_evolve.adapters.rest_api import serve
        serve(host=args.host, port=args.port, palace_path=args.palace)
    elif args.command == "evolve":
        report = palace.evolve()
        print(f"Evolution: {report['promoted']} promoted, {report['dropped']} dropped")


if __name__ == "__main__":
    main()
