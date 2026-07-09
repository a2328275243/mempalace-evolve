"""mempalace playground — interactive REPL for exploring memories."""

import cmd
import os

from mempalace_evolve.terminal import (
    bold,
    cyan,
    green,
    yellow,
    dim,
    magenta,
)


class PalaceShell(cmd.Cmd):
    """Interactive memory palace shell."""

    intro = bold(cyan("\n  MemPalace Playground")) + dim(
        "\n  输入文字即存储 | /search 搜索 | /help 帮助 | /quit 退出\n"
    )
    prompt = green("  mempalace> ")

    def __init__(self, palace):
        super().__init__()
        self.palace = palace

    def default(self, line: str):
        """Any non-command input is stored as a memory."""
        text = line.strip()
        if not text:
            return
        did = self.palace.remember(text, room="playground")
        print(f"    {green('✓')} 已存储 {dim(did[:20])}")

    def do_search(self, arg):
        """Semantic search: /search <query>"""
        if not arg.strip():
            print(yellow("    用法: /search <查询内容>"))
            return
        results = self.palace.recall(arg.strip(), limit=5)
        if not results:
            print(dim("    无匹配结果"))
            return
        for i, r in enumerate(results, 1):
            dist = r["distance"]
            content = r["content"][:80]
            print(f"    {cyan(str(i))}. {content}  {dim(f'[{dist:.3f}]')}")

    def do_fact(self, arg):
        """Add knowledge triple: /fact subject predicate object"""
        parts = arg.strip().split(None, 2)
        if len(parts) < 3:
            print(yellow("    用法: /fact 主语 谓语 宾语"))
            return
        self.palace.add_fact(*parts)
        print(f"    {green('✓')} {magenta(parts[0])} ─{parts[1]}→ {cyan(parts[2])}")

    def do_entity(self, arg):
        """Query entity: /entity <name>"""
        if not arg.strip():
            print(yellow("    用法: /entity <实体名>"))
            return
        rels = self.palace.query_entity(arg.strip())
        if not rels:
            print(dim("    无关系记录"))
            return
        for r in rels:
            print(f"    {magenta(r['subject'])} ─{r['predicate']}→ {cyan(r['object'])}")

    def do_evolve(self, arg):
        """Run evolution pipeline on recent input."""
        report = self.palace.evolve()
        promoted = report.get("promoted", 0)
        dropped = report.get("dropped", 0)
        print(f"    晋升: {green(str(promoted))}  丢弃: {dim(str(dropped))}")

    def do_quit(self, arg):
        """Exit playground."""
        print(dim("    再见！"))
        return True

    do_exit = do_quit
    do_EOF = do_quit

    def do_help(self, arg):
        """Show available commands."""
        print(dim("    命令:"))
        print(f"      {bold('/search')} <query>     语义搜索记忆")
        print(f"      {bold('/fact')} S P O         添加知识三元组")
        print(f"      {bold('/entity')} <name>      查询实体关系")
        print(f"      {bold('/evolve')}             运行进化管道")
        print(f"      {bold('/quit')}               退出")
        print(f"      {dim('<任意文字>')}           直接存储为记忆")

    def precmd(self, line: str) -> str:
        """Strip leading / from commands."""
        stripped = line.strip()
        if stripped.startswith("/"):
            return stripped[1:]
        return line


def run_playground(palace_path: str | None = None) -> None:
    """Start an interactive MemPalace session."""
    from mempalace_evolve.sdk import MemPalace

    path = palace_path or os.path.join(os.path.expanduser("~"), ".mempalace", "playground")
    palace = MemPalace(path, wing="playground")
    shell = PalaceShell(palace)
    try:
        shell.cmdloop()
    except KeyboardInterrupt:
        print(dim("\n    再见！"))
