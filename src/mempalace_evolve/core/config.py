"""
MemPalace 统一配置模块
=====================
所有模块的配置入口，解析全局/项目级 YAML，提供 project→wing 映射。
"""

import json
import logging
import os
import sys
from pathlib import Path

logger = logging.getLogger("mempalace.config")


def atomic_write(path: Path, content: str, encoding: str = "utf-8"):
    """原子写入文本文件：先写临时文件再重命名，防止写入中断导致文件损坏。

    Args:
        path: 目标文件路径
        content: 要写入的文本内容
        encoding: 文件编码，默认 utf-8
    """
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp.write_text(content, encoding=encoding)
        tmp.replace(path)
    except Exception:
        logger.debug("atomic rename failed for %s, falling back to direct write", path, exc_info=True)
        try:
            tmp.unlink(missing_ok=True)
        except Exception:
            pass
        path.write_text(content, encoding=encoding)


def atomic_write_json(path: Path, data, ensure_ascii: bool = False, indent: int = 2):
    """原子写入 JSON 文件。

    Args:
        path: 目标文件路径
        data: 要序列化的数据
        ensure_ascii: 是否转义非 ASCII 字符
        indent: 缩进空格数
    """
    atomic_write(path, json.dumps(data, ensure_ascii=ensure_ascii, indent=indent))

# ---------------------------------------------------------------------------
# 路径常量
# ---------------------------------------------------------------------------
# 支持环境变量覆盖，默认用 ~/.mempalace
_MEMPALACE_ROOT = os.environ.get("MEMPALACE_ROOT", str(Path.home() / ".mempalace"))
GLOBAL_PALACE = Path(_MEMPALACE_ROOT)
GLOBAL_CHROMA = GLOBAL_PALACE / "palace"
COLLECTION_NAME = "mempalace_drawers"
IDENTITY_FILE = "identity.txt"
MEMORY_FILE = "MEMORY.md"
YAML_FILE = "mempalace.yaml"
YAML_ALT = "mempal.yaml"


def _yaml_safe_load(text: str) -> dict:
    """简易 YAML 解析器（不依赖 pyyaml）。
    支持 key: value、- list 项、嵌套 dict（最多 4 层）、内联注释。
    """
    lines = text.split("\n")

    # 预处理：去内联注释，计算缩进
    parsed_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # 去内联注释（保留引号内的 #）
        in_quote = False
        clean = []
        for ch in stripped:
            if ch in ('"', "'"):
                in_quote = not in_quote
            if ch == '#' and not in_quote:
                break
            clean.append(ch)
        clean_text = "".join(clean).rstrip()
        if clean_text:
            indent = len(line) - len(line.lstrip())
            parsed_lines.append((indent, clean_text))

    # 递归解析
    result, _ = _parse_block(parsed_lines, 0, 0, len(parsed_lines))
    return result if isinstance(result, dict) else {}


def _parse_block(lines, start, min_indent, end):
    """解析一个 YAML 块（dict 或 list），返回 (result, next_index)"""
    if start >= end:
        return {}, end

    # 判断是 list 还是 dict
    first_text = lines[start][1]
    if first_text.startswith("- "):
        return _parse_list(lines, start, min_indent, end)

    return _parse_dict(lines, start, min_indent, end)


def _parse_dict(lines, start, min_indent, end):
    """解析 dict 块"""
    result = {}
    i = start
    while i < end:
        indent, text = lines[i]
        if indent < min_indent and i > start:
            break

        if ":" not in text:
            i += 1
            continue

        key, _, val = text.partition(":")
        key = key.strip()
        val = val.strip()

        if val:
            # key: value（简单值）
            result[key] = _parse_yaml_value(val)
            i += 1
        else:
            # key:（后面可能是子 dict 或 list）
            key_indent = indent
            i += 1
            if i >= end or lines[i][0] <= key_indent:
                result[key] = None
                continue
            child_indent = lines[i][0]
            child_result, i = _parse_block(lines, i, child_indent, end)
            result[key] = child_result

    return result, i


def _parse_list(lines, start, min_indent, end):
    """解析 list 块（- 开头的项）"""
    result = []
    i = start
    while i < end:
        indent, text = lines[i]
        if indent < min_indent and i > start:
            break
        if not text.startswith("- "):
            break

        item_text = text[2:].strip()
        item_indent = indent + 2  # "- " 后的内容缩进

        if ":" in item_text and not item_text.startswith('"'):
            # - key: value 或 - 开头的 dict
            # 收集同一项的所有行
            item_lines = [(indent + 2, item_text)]
            j = i + 1
            while j < end and lines[j][0] > indent:
                item_lines.append(lines[j])
                j += 1
            parsed_item, _ = _parse_dict(item_lines, 0, item_indent, len(item_lines))
            result.append(parsed_item)
            i = j
        else:
            result.append(_parse_yaml_value(item_text))
            i += 1

    return result, i


def _parse_yaml_value(val: str):
    """解析 YAML 标量值"""
    if val.lower() in ("true", "yes"):
        return True
    if val.lower() in ("false", "no"):
        return False
    if val.lower() in ("null", "~", ""):
        return None
    try:
        return int(val)
    except ValueError:
        pass
    try:
        return float(val)
    except ValueError:
        pass
    # 去掉引号
    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        return val[1:-1]
    return val


class UserConfig:
    """统一配置管理器"""

    def __init__(self, config_dir: str = None):
        self._config_dir = Path(config_dir) if config_dir else GLOBAL_PALACE
        self._projects_cache = None
        self._yaml_cache = {}

    # ------------------------------------------------------------------
    # 项目管理
    # ------------------------------------------------------------------

    def get_projects(self) -> list[dict]:
        """读取全局 mempalace.yaml，返回已注册项目列表。
        每项: {name, path, palace_path, type}
        """
        if self._projects_cache is not None:
            return self._projects_cache

        projects = []
        # 从全局 MEMORY.md 扫描项目路径
        memory_md = self._config_dir / MEMORY_FILE
        yaml_data = self._load_yaml(self._config_dir / YAML_FILE)

        if yaml_data and "projects" in yaml_data:
            for p in yaml_data["projects"]:
                if isinstance(p, dict):
                    projects.append(p)

        # 补充：扫描 MEMORY.md 中可能遗漏的项目
        if memory_md.exists():
            text = memory_md.read_text(encoding="utf-8")
            for line in text.split("\n"):
                line = line.strip()
                if "- **路径**：`" in line or "- **路径**: `" in line:
                    start = line.index("`") + 1
                    end = line.index("`", start)
                    proj_path = line[start:end]
                    # 检查是否已在列表中
                    if not any(p.get("path") == proj_path for p in projects):
                        palace = str(Path(proj_path) / ".mempalace")
                        if Path(palace).exists():
                            projects.append({
                                "name": Path(proj_path).name,
                                "path": proj_path,
                                "palace_path": palace,
                                "type": "other",
                            })

        self._projects_cache = projects
        return projects

    def resolve_wing(self, project_path: str) -> str:
        """将项目路径映射为 wing 名称"""
        projects = self.get_projects()
        proj_path = str(Path(project_path).resolve())

        for p in projects:
            if str(Path(p["path"]).resolve()) == proj_path:
                return p["name"]

        # 没注册的项目，用目录名
        return Path(project_path).name

    def resolve_palace_path(self, wing: str = None) -> str:
        """给定 wing 名称，返回 ChromaDB 目录路径。
        无 wing 时返回全局 palace。
        """
        if wing is None:
            return str(GLOBAL_CHROMA)

        for p in self.get_projects():
            if p["name"] == wing:
                palace = p.get("palace_path", "")
                if palace and Path(palace).exists():
                    return str(palace)

        return str(GLOBAL_CHROMA)

    def get_rooms_for_wing(self, wing: str) -> list[dict]:
        """获取指定 wing 的房间定义。
        从项目的 mempalace.yaml 中读取 wings.rooms 配置。
        """
        for p in self.get_projects():
            if p["name"] == wing:
                palace_path = Path(p.get("palace_path", ""))
                yaml_data = self._load_yaml(palace_path / YAML_FILE)
                if not yaml_data:
                    yaml_data = self._load_yaml(palace_path / YAML_ALT)

                if yaml_data and "wings" in yaml_data:
                    rooms = []
                    wings = yaml_data["wings"]
                    if isinstance(wings, dict):
                        for wing_name, wing_data in wings.items():
                            if isinstance(wing_data, dict) and "rooms" in wing_data:
                                for r in wing_data["rooms"]:
                                    rooms.append({"name": r, "wing": wing_name})
                    return rooms
                return []
        return []

    def resolve_identity_path(self, wing: str = None) -> str:
        """获取 identity.txt 路径。优先项目级，其次全局。"""
        if wing:
            for p in self.get_projects():
                if p["name"] == wing:
                    identity = Path(p.get("palace_path", "")) / IDENTITY_FILE
                    if identity.exists():
                        return str(identity)

        return str(self._config_dir / IDENTITY_FILE)

    # ------------------------------------------------------------------
    # ChromaDB 配置
    # ------------------------------------------------------------------

    @property
    def collection_name(self) -> str:
        return COLLECTION_NAME

    @property
    def palace_path(self) -> str:
        """默认全局 ChromaDB 路径"""
        return str(GLOBAL_CHROMA)

    # ------------------------------------------------------------------
    # 辅助方法
    # ------------------------------------------------------------------

    def _load_yaml(self, path: Path) -> dict | None:
        """加载 YAML 文件（用缓存）"""
        path = Path(path)
        if not path.exists():
            return None

        path_str = str(path)
        if path_str in self._yaml_cache:
            return self._yaml_cache[path_str]

        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            return None

        # 尝试 pyyaml
        try:
            import yaml
            data = yaml.safe_load(text)
            if isinstance(data, dict):
                self._yaml_cache[path_str] = data
                return data
        except ImportError:
            pass  # 静默回退，不打日志以免每次都刷屏
        except Exception:
            logger.warning(f"pyyaml 解析失败 ({path})，回退到简易解析器")

        # 回退到简易解析器（功能有限，仅支持简单 key:value）
        data = _yaml_safe_load(text)
        if isinstance(data, dict):
            self._yaml_cache[path_str] = data
            return data

        return None

    @property
    def lifecycle_config(self) -> dict:
        """生命周期管理配置（带默认值）"""
        defaults = {
            "decay_lambda": 0.02,
            "compress_after_days": 60,
            "compress_max_summary_chars": 800,
            "max_total_drawers": 500,
            "max_drawers_per_wing": 200,
            "conflict_threshold": 0.95,
        }
        yaml_data = self._load_yaml(self._config_dir / YAML_FILE)
        if yaml_data and "lifecycle" in yaml_data:
            lc = yaml_data["lifecycle"]
            if isinstance(lc, dict):
                defaults.update({k: v for k, v in lc.items() if v is not None})
        return defaults

    def scan_all_mempalaces(self) -> list[dict]:
        """扫描全局和所有项目级 .mempalace/ 目录，收集 .md 文件"""
        files = []

        # 全局 palace
        for md in self._config_dir.glob("*.md"):
            if md.name not in ("README.md",):
                files.append({
                    "path": str(md),
                    "wing": "global",
                    "name": md.name,
                })

        # 项目级
        for p in self.get_projects():
            palace = p.get("palace_path", "")
            if not palace or not Path(palace).exists():
                continue
            wing = p["name"]
            for md in palace.glob("*.md"):
                files.append({
                    "path": str(md),
                    "wing": wing,
                    "name": md.name,
                })

        return files


# ---------------------------------------------------------------------------
# 全局单例
# ---------------------------------------------------------------------------
_config = None

def get_config() -> UserConfig:
    global _config
    if _config is None:
        _config = UserConfig()
    return _config


# Alias for SDK compatibility
PalaceConfig = UserConfig
