"""CLI entry point for mempalace-evolve."""

from __future__ import annotations

import argparse
import json
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
    p_srv.add_argument("--api-key", default=None, help="Require this API key in X-API-Key header")
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

    # mempalace setup
    p_setup = sub.add_parser("setup", help="Interactive MCP setup wizard")
    p_setup.add_argument("--wing", default=None, help="Wing/project name")
    p_setup.add_argument("--palace", default=None, help="Palace storage path")


    # mempalace ingest <directory> [--recursive] [--room ...] [--force]
    p_ingest = sub.add_parser("ingest", help="Ingest files into memory palace")
    p_ingest.add_argument("directory", help="Directory to scan for files")
    p_ingest.add_argument("--recursive", action="store_true", default=True, help="Recurse subdirectories")
    p_ingest.add_argument("--room", default="documents", help="Target room for chunks")
    p_ingest.add_argument("--chunk-size", type=int, default=1000, help="Max chars per chunk")
    p_ingest.add_argument("--force", action="store_true", help="Re-index all files")
    p_ingest.add_argument("--palace", default=None, help="Palace path")

    # mempalace sources list [--palace ...]
    p_sources = sub.add_parser("sources", help="Tracked source documents")
    p_sources.add_argument("action", nargs="?", default="list", choices=["list", "stats"], help="Action: list | stats")
    p_sources.add_argument("--palace", default=None, help="Palace path")
    # mempalace export --format json --output memories.json
    p_exp = sub.add_parser("export", help="Export memories to JSON or Markdown")
    p_exp.add_argument("--format", choices=["json", "markdown"], default="json")
    p_exp.add_argument("--output", "-o", default=None, help="Output file path")
    p_exp.add_argument("--palace", default=None, help="Palace path")

    # mempalace review (spaced repetition)
    p_rev = sub.add_parser("review", help="Show memories due for spaced repetition review")
    p_rev.add_argument("--palace", default=None, help="Palace path")
    p_rev.add_argument("--limit", type=int, default=10, help="Max memories to show")
    p_rev.add_argument("--mark", metavar="ID", help="Mark a memory as reviewed by its ID")

    # mempalace top (importance scores)
    p_top = sub.add_parser("top", help="Show top N most important memories")
    p_top.add_argument("n", type=int, nargs="?", default=10, help="Number of memories")
    p_top.add_argument("--palace", default=None, help="Palace path")

    # mempalace similar "content"
    p_sim = sub.add_parser("similar", help="Find similar memories to content")
    p_sim.add_argument("content", help="Content to search for")
    p_sim.add_argument("--room", default=None, help="Room filter")
    p_sim.add_argument("--threshold", type=float, default=0.85, help="Similarity threshold")
    p_sim.add_argument("--palace", default=None, help="Palace path")

    # Lifecycle management commands
    p_purge = sub.add_parser("purge", help="Purge TTL-expired memories")
    p_purge.add_argument("--ttl-days", type=int, default=90, help="TTL for low-importance memories")
    p_purge.add_argument("--ttl-summary", type=int, default=180, help="TTL for summarized memories")
    p_purge.add_argument("--palace", default=None, help="Palace path")

    p_compress = sub.add_parser("compress", help="Compress old, unused memories")
    p_compress.add_argument("--after-days", type=int, default=60, help="Age threshold for compression")
    p_compress.add_argument("--max-chars", type=int, default=800, help="Max summary characters")
    p_compress.add_argument("--palace", default=None, help="Palace path")

    p_conso = sub.add_parser("consolidate", help="Deduplicate and merge similar memories")
    p_conso.add_argument("--dry-run", action="store_true", help="Only preview what would be merged")
    p_conso.add_argument("--palace", default=None, help="Palace path")


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
    if args.command == "setup":
        from mempalace_evolve.setup_wizard import run_setup
        ok = run_setup(wing=args.wing, palace_path=args.palace)
        sys.exit(0 if ok else 1)

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
        serve(host=args.host, port=args.port, palace_path=args.palace,
              api_key=args.api_key)
    elif args.command == "evolve":
        report = palace.evolve()
        print(f"Evolution: {report['promoted']} promoted, {report['dropped']} dropped")
    elif args.command == "ingest":
        from mempalace_evolve.ingest import ingest_directory
        # Create a palace instance
        palace_kwargs = {}
        if args.palace:
            palace_kwargs["palace_path"] = args.palace
        from mempalace_evolve.sdk import MemPalace
        p = MemPalace(**palace_kwargs)
        summary = ingest_directory(
            args.directory,
            p,
            recursive=args.recursive,
            room=args.room,
            chunk_size=args.chunk_size,
            force=args.force,
        )
        print(f"Ingest complete: {summary.indexed} indexed, {summary.skipped} skipped, {summary.errors} errors (of {summary.total_files})")
    elif args.command == "sources":
        from mempalace_evolve.ingest import list_sources
        palace_path = args.palace or "."
        sources = list_sources(palace_path)
        if args.action == "list":
            if not sources:
                print("No tracked sources.")
            else:
                print(f"Tracked sources ({len(sources)}):")
                for src in sources:
                    print(f"  {src.path}  [{src.status}]")
        elif args.action == "stats":
            indexed = sum(1 for s in sources if s.status == "indexed")
            stale = sum(1 for s in sources if s.status == "stale")
            print(f"Indexed: {indexed}, Stale: {stale}, Total: {len(sources)}")
    elif args.command == "export":
        result = palace.export(format=args.format, output=args.output)
        if args.output:
            print(f"Exported to {args.output}")
        elif args.format == "markdown":
            print(result)
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "review":
        due = palace.get_due_for_review()
        if args.mark:
            # Mark a specific memory as reviewed
            ok = palace.mark_reviewed(args.mark)
            if ok:
                print(f"Marked {args.mark} as reviewed")
            else:
                print(f"Failed to mark {args.mark} (not found)")
        else:
            # Show memories due for review
            print(f"Memories due for review: {len(due)}")
            for mem in due[:args.limit]:
                print(f"  [{mem['interval_index']}] {mem['content'][:80]}...")
    elif args.command == "top":
        top = palace.top_memories(args.n)
        print(f"Top {len(top)} important memories:")
        for mem in top:
            print(f"  [{mem['score']:.2f}] {mem['content'][:60]}...")
    elif args.command == "similar":
        similar = palace.find_similar(args.content, room=args.room, threshold=args.threshold)
        print(f"Similar memories: {len(similar)}")
        for mem in similar:
            print(f"  [{mem['similarity']:.2f}] {mem['content'][:60]}...")

    elif args.command == "purge":
        result = palace.purge_expired(ttl_days=args.ttl_days, ttl_summary_days=args.ttl_summary)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == "compress":
        result = palace.compress_old_memories(compress_after_days=args.after_days, max_chars=args.max_chars)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    elif args.command == "consolidate":
        result = palace.consolidate(dry_run=args.dry_run)
        print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
