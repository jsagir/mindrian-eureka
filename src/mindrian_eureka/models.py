"""Find the local sentence model folder for `eureka doctor` and `eureka run`.

One function, `discover_model`, decides which folder holds the model. The order is
fixed: the `--model-path` flag, then two environment variables, then the Hugging Face
cache. The first source that is set decides. A source that is set but invalid stops
the search with a problem line. The search never falls through to another model
silently. It makes no network call, downloads nothing and imports only the standard
library.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

MODEL_REPO = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_FOLDER_NAME = "all-MiniLM-L6-v2"
ENV_RS_MODEL_PATH = "MINDRIAN_EUREKA_RS_MODEL_PATH"
ENV_HSI_MODEL_PATH = "MINDRIAN_EUREKA_HSI_MODEL_PATH"
HF_MODEL_DIR_NAME = "models--sentence-transformers--all-MiniLM-L6-v2"

ORIGIN_FLAG = "--model-path"
ORIGIN_CACHE = "Hugging Face cache"

_REQUIRED_FILES = ("config.json", "modules.json")
_WEIGHT_FILES = ("model.safetensors", "pytorch_model.bin")
_TOKENIZER_FILES = ("tokenizer.json", "vocab.txt")
_WEIGHT_LABEL = "model.safetensors or pytorch_model.bin"
_TOKENIZER_LABEL = "tokenizer.json or vocab.txt"


@dataclass(frozen=True)
class ModelResolution:
    """The result of the model search.

    Attributes:
        path: The model folder, or None when nothing usable was found.
        origin: The source that supplied the folder, or None.
        searched: One line for every place that was looked at.
        problems: Problem lines. A source that is set but invalid adds one.
    """

    path: Path | None
    origin: str | None
    searched: tuple[str, ...]
    problems: tuple[str, ...]

    @property
    def ok(self) -> bool:
        """True when a usable folder was found and no problem was raised."""
        return self.path is not None and not self.problems


@dataclass(frozen=True)
class _Partial:
    """The outcome of one source.

    Attributes:
        decided: True when the search must stop here (found, or set but invalid).
        path: The folder when the source was valid.
        origin: The source name when the source was valid.
        problems: Problem lines when the source was set but invalid.
        lines: The searched lines of this source.
    """

    decided: bool
    path: Path | None
    origin: str | None
    problems: tuple[str, ...]
    lines: tuple[str, ...]


def os_variants(posix: str, windows: str) -> str:
    """Join a Linux or macOS text and a Windows text, naming each system.

    Args:
        posix: The text for Linux and macOS.
        windows: The text for Windows (PowerShell).

    Returns:
        The two lines joined by a newline, or the text alone when both are equal.
    """
    if posix == windows:
        return posix
    return f"On Linux or macOS: {posix}\nOn Windows (PowerShell): {windows}"


def missing_files(path: Path) -> list[str]:
    """List the names that make a model folder invalid.

    A valid folder holds config.json, modules.json, one weight file and one
    tokenizer file.

    Args:
        path: The candidate model folder.

    Returns:
        The missing names. The list is empty for a valid folder.
    """
    missing = [name for name in _REQUIRED_FILES if not (path / name).is_file()]
    if not any((path / name).is_file() for name in _WEIGHT_FILES):
        missing.append(_WEIGHT_LABEL)
    if not any((path / name).is_file() for name in _TOKENIZER_FILES):
        missing.append(_TOKENIZER_LABEL)
    return missing


def _line(origin: str, where: str | None, reason: str) -> str:
    return f"{origin}: {where if where is not None else 'not set'} ({reason})"


def _check_set_path(origin: str, raw: str) -> _Partial:
    """Check a folder that a flag or a variable names."""
    path = Path(raw).expanduser()
    if not path.is_dir():
        reason = "folder not found"
        problem = f"{origin} is set to {path} but that folder does not exist."
        return _Partial(True, None, origin, (problem,), (_line(origin, str(path), reason),))
    missing = missing_files(path)
    if missing:
        listed = ", ".join(missing)
        problem = f"{origin} is set to {path} but the folder lacks: {listed}."
        return _Partial(
            True, None, origin, (problem,), (_line(origin, str(path), f"missing: {listed}"),)
        )
    return _Partial(True, path, origin, (), (_line(origin, str(path), "valid"),))


def _explicit_source(explicit: Path | None) -> _Partial:
    if explicit is None:
        return _Partial(False, None, None, (), (_line(ORIGIN_FLAG, None, "not given"),))
    return _check_set_path(ORIGIN_FLAG, str(explicit))


def _env_source(name: str, env: Mapping[str, str]) -> _Partial:
    raw = env.get(name, "").strip()
    if not raw:
        return _Partial(False, None, None, (), (_line(name, None, "variable not set"),))
    return _check_set_path(name, raw)


def _cache_roots(env: Mapping[str, str], home: Path) -> list[Path]:
    """Return the Hugging Face cache roots in search order, without duplicates."""
    roots: list[Path] = []
    hub = env.get("HF_HUB_CACHE", "").strip()
    if hub:
        roots.append(Path(hub).expanduser())
    hf_home = env.get("HF_HOME", "").strip()
    if hf_home:
        roots.append(Path(hf_home).expanduser() / "hub")
    roots.append(home / ".cache" / "huggingface" / "hub")
    unique: list[Path] = []
    for root in roots:
        if root not in unique:
            unique.append(root)
    return unique


def _read_main_ref(model_dir: Path) -> str | None:
    try:
        text = (model_dir / "refs" / "main").read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return text or None


def _cache_source(env: Mapping[str, str], home: Path) -> _Partial:
    lines: list[str] = []
    for root in _cache_roots(env, home):
        model_dir = root / HF_MODEL_DIR_NAME
        if not model_dir.is_dir():
            lines.append(_line(ORIGIN_CACHE, str(root), "model not in this cache"))
            continue
        snapshots_dir = model_dir / "snapshots"
        names: list[str] = []
        if snapshots_dir.is_dir():
            names = sorted(entry.name for entry in snapshots_dir.iterdir() if entry.is_dir())
        ref = _read_main_ref(model_dir)
        if ref is not None and ref in names and not missing_files(snapshots_dir / ref):
            path = snapshots_dir / ref
            lines.append(_line(ORIGIN_CACHE, str(path), "valid snapshot named by refs/main"))
            return _Partial(True, path, ORIGIN_CACHE, (), tuple(lines))
        valid = [name for name in names if not missing_files(snapshots_dir / name)]
        if len(valid) == 1:
            path = snapshots_dir / valid[0]
            lines.append(_line(ORIGIN_CACHE, str(path), "the only valid snapshot"))
            return _Partial(True, path, ORIGIN_CACHE, (), tuple(lines))
        if len(valid) > 1:
            listed = ", ".join(valid)
            lines.append(_line(ORIGIN_CACHE, str(snapshots_dir), f"several snapshots: {listed}"))
            problem = (
                f"The Hugging Face cache {snapshots_dir} holds {len(valid)} valid snapshots "
                f"({listed}) and refs/main does not name one of them. "
                f"Pass --model-path to choose one."
            )
            return _Partial(True, None, ORIGIN_CACHE, (problem,), tuple(lines))
        lines.append(_line(ORIGIN_CACHE, str(model_dir), "no valid snapshot"))
    return _Partial(False, None, None, (), tuple(lines))


def discover_model(
    explicit: Path | None = None,
    *,
    env: Mapping[str, str] | None = None,
    home: Path | None = None,
) -> ModelResolution:
    """Find the local model folder.

    The order is: `explicit`, the first model variable, the second model variable, then the
    Hugging Face cache. The first source that is set decides. A source that is set but
    invalid gives a not-ok result and later sources are not tried. Nothing is
    downloaded and no network call is made.

    Args:
        explicit: The folder given with `--model-path`, or None.
        env: The environment. The default is `os.environ`.
        home: The home folder for the default cache root. The default is `Path.home()`.

    Returns:
        The resolution, with every searched place listed.
    """
    environment: Mapping[str, str] = os.environ if env is None else env
    home_dir = Path.home() if home is None else home
    searched: list[str] = []
    sources: tuple[Callable[[], _Partial], ...] = (
        lambda: _explicit_source(explicit),
        lambda: _env_source(ENV_RS_MODEL_PATH, environment),
        lambda: _env_source(ENV_HSI_MODEL_PATH, environment),
        lambda: _cache_source(environment, home_dir),
    )
    for source in sources:
        partial = source()
        searched.extend(partial.lines)
        if partial.decided:
            return ModelResolution(
                partial.path, partial.origin, tuple(searched), partial.problems
            )
    return ModelResolution(None, None, tuple(searched), ())


def model_fix_text() -> str:
    """Return the fix block for a missing or unusable model.

    Returns:
        Numbered steps with a Linux or macOS line and a Windows line.
    """
    variable = os_variants(
        f"export {ENV_RS_MODEL_PATH}=/absolute/path/to/{MODEL_FOLDER_NAME}",
        f'$env:{ENV_RS_MODEL_PATH} = "C:\\path\\to\\{MODEL_FOLDER_NAME}"',
    )
    indented = "\n".join(f"     {line}" for line in variable.splitlines())
    return (
        "1. On a machine with internet, fetch the folder once: "
        f"uv run hf download {MODEL_REPO} --local-dir {MODEL_FOLDER_NAME}\n"
        "2. Copy the folder to this machine.\n"
        "3. Set the variable, or pass --model-path:\n"
        f"{indented}"
    )


def missing_model_message(
    resolution: ModelResolution,
    *,
    explicit_given: bool = False,
    fix_text: str | None = None,
) -> str:
    """Explain why no model was found and how to fix it.

    Args:
        resolution: The result of `discover_model`.
        explicit_given: True when the user passed `--model-path`.
        fix_text: The fix block to print, or None for the block of the default model.

    Returns:
        A message that starts with "No local model found." when nothing was found, or
        "The local model is not usable." when a set source was invalid. It lists every
        searched place, then the fix.
    """
    header = "The local model is not usable." if resolution.problems else "No local model found."
    parts = [header, "Searched:"]
    parts.extend(f"  - {line}" for line in resolution.searched)
    if resolution.problems:
        parts.append("Problems:")
        parts.extend(f"  - {problem}" for problem in resolution.problems)
    if explicit_given:
        parts.append("The folder given with --model-path was checked first and decides.")
    parts.append("Fix:")
    block = model_fix_text() if fix_text is None else fix_text
    parts.extend(f"  {line}" for line in block.splitlines())
    return "\n".join(parts)
