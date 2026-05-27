"""CLI entry point for mempalace-evolve."""

from __future__ import annotations

import argparse
import sys


def main():
    from mempalace_evolve import __version__

    parser = argparse.ArgumentParser(
        prog="mempalace",
        description="Self-evolving memory palace for AI agents",
    )
    parser.add_argument("--version", action="version", version=f"mempalace {__version__}")
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

    # mempalace demo
    p_demo = sub.add_parser("demo", help="Run a self-contained demo showcase")
    p_demo.add_argument("--keep", action="store_true", help="Keep demo data after run")

    # mempalace doctor
    sub.add_parser("doctor", help="Verify installation and dependencies")

    # mempalace playground
    p_pg = sub.add_parser("playground", help="Interactive memory playground")
    p_pg.add_argument("--palace", default=None, help="Palace path")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    # Commands that don't need a palace instance
    if args.command == "demo":
        from mempalace_evolve.demo import run_demo
        run_demo(keep_data=args.keep)
        return
    if args.command == "doctor":
        from mempalace_evolve.doctor import run_doctor
        ok = run_doctor()
        sys.exit(0 if ok else 1)
    if args.command == "playground":
        from mempalace_evolve.playground import run_playground
        run_playground(palace_path=args.palace)
        return

    # Commands that need a palace instance
    try:
        from mempalace_evolve.sdk import MemPalace
        palace = MemPalace(args.palace)
    except Exception as e:
        from mempalace_evolve.terminal import red, dim
        print(red(f"\n  Error: {e}"))
        print(dim("  Run 'mempalace doctor' to diagnose.\n"))
        sys.exit(1)

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
