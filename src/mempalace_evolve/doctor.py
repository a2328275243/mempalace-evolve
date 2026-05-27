"""mempalace doctor — verify installation and diagnose issues."""
import sys
import tempfile
import shutil

from mempalace_evolve.terminal import bullet, fail, bold, dim, green, red, divider


def run_doctor() -> bool:
    """Run diagnostic checks. Returns True if all required checks pass."""
    print(bold("\n  MemPalace Doctor\n"))
    print(divider())
    passed = 0
    failed = 0

    # 1. Python version
    v = sys.version_info
    if v >= (3, 10):
        print(bullet(f"Python {v.major}.{v.minor}.{v.micro}"))
        passed += 1
    else:
        print(fail(f"Python {v.major}.{v.minor} — 需要 >= 3.10"))
        failed += 1

    # 2. chromadb import
    try:
        import chromadb
        print(bullet(f"chromadb {chromadb.__version__}"))
        passed += 1
    except ImportError:
        print(fail("chromadb 未安装 — pip install mempalace-evolve"))
        failed += 1

    # 3. Read/write test
    tmp = tempfile.mkdtemp(prefix="mempalace_doctor_")
    try:
        from mempalace_evolve.sdk import MemPalace
        p = MemPalace(tmp, wing="doctor")
        did = p.remember("doctor test", room="test")
        results = p.recall("doctor test", limit=1)
        if results and results[0]["content"] == "doctor test":
            print(bullet("记忆读写正常"))
            passed += 1
        else:
            print(fail("记忆读写异常"))
            failed += 1
    except Exception as e:
        print(fail(f"记忆读写失败: {e}"))
        failed += 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # 4. Knowledge graph test
    tmp2 = tempfile.mkdtemp(prefix="mempalace_doctor_kg_")
    try:
        p2 = MemPalace(tmp2, wing="doctor")
        p2.add_fact("A", "relates_to", "B")
        rels = p2.query_entity("A")
        if rels:
            print(bullet("知识图谱正常"))
            passed += 1
        else:
            print(fail("知识图谱查询无结果"))
            failed += 1
    except Exception as e:
        print(fail(f"知识图谱失败: {e}"))
        failed += 1
    finally:
        shutil.rmtree(tmp2, ignore_errors=True)

    # 5. Optional dependencies
    print(dim("\n  可选依赖:"))
    for name, pkg in [("fastapi", "fastapi"), ("fastmcp", "fastmcp"), ("langchain-core", "langchain_core")]:
        try:
            mod = __import__(pkg)
            ver = getattr(mod, "__version__", "?")
            print(bullet(f"{name} {ver}"))
        except ImportError:
            print(dim(f"      - {name} (未安装，可选)"))

    # Summary
    print(divider())
    if failed == 0:
        print(bold(green(f"\n  ✓ 全部通过 ({passed}/{passed})")))
    else:
        print(bold(red(f"\n  ✗ {failed} 项失败，{passed} 项通过")))
    print()
    return failed == 0
