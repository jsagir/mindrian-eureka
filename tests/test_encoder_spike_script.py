"""Tests of the GPU spike script `scripts/encoder-spike.py`.

The script is meant to run on the owner's GPU computer in a scratch environment. Here it runs
only against a fake backend (no GPU, no model, no network) and in `-I` subprocesses that prove
it needs the standard library alone for `--help`, `--dry-run` and `--render-doc`.

Every number below is a sentinel that the fake backend returns. None is a measurement.
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any

import numpy as np
import pytest
from mindrian_eureka.encoder_spec import PROFILES

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "encoder-spike.py"
RECORDS = ROOT / "examples" / "public-example" / "reference-run" / "corpus" / "records.jsonl"
HEAVY = ("numpy", "torch", "transformers", "sentence_transformers", "huggingface_hub")

REVISION = "0123456789abcdef0123456789abcdef01234567"
LOAD_SECONDS = {"bf16": 3.5, "fp32": 7.25, "minilm": 1.5}
PEAK_BYTES = {"bf16": 2147483648, "fp32": 4294967296, "minilm": 536870912}
TEXTS_PER_SECOND = {"bf16": 41.5, "fp32": 29.75, "minilm": 100.0}
GPU_NAME = "Test GPU 3060"
DRIVER = "999.99"
WIDTH = 8


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("encoder_spike", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["encoder_spike"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def spike() -> ModuleType:
    return load_script()


def record_ids() -> list[str]:
    ids = []
    for line in RECORDS.read_text(encoding="utf-8").splitlines():
        item = json.loads(line)
        if item.get("record_type") == "record":
            ids.append(item["id"])
    return ids


def fake_vectors(kind: str, count: int) -> np.ndarray:
    """Return deterministic float32 vectors. The three kinds differ from each other."""
    seeds = {"bf16": 11, "cpu": 13, "minilm": 17}
    base = np.random.RandomState(seeds.get(kind, 11)).standard_normal((count, WIDTH))
    if kind == "fp32":
        noise = np.random.RandomState(29).standard_normal((count, WIDTH))
        base = np.random.RandomState(11).standard_normal((count, WIDTH)) + 0.5 * noise
    return base.astype(np.float32)


def pair_key(left: str, right: str) -> str:
    joined = "\0".join(sorted([left, right]))
    return "pair-" + hashlib.sha256(joined.encode("utf-8")).hexdigest()[:20]


def top200(vectors: np.ndarray, ids: list[str]) -> set[str]:
    """The test's own dense top-200: plain loops, no shared code with the script."""
    matrix = np.asarray(vectors, dtype=np.float64)
    matrix = matrix / np.linalg.norm(matrix, axis=1, keepdims=True)
    rows = []
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            rows.append((-float(matrix[i] @ matrix[j]), i, j))
    rows.sort()
    return {pair_key(ids[i], ids[j]) for _, i, j in rows[:200]}


def own_overlap(left: np.ndarray, right: np.ndarray, ids: list[str]) -> float:
    return len(top200(left, ids) & top200(right, ids)) / 200


class FakeBackend:
    """A backend that returns sentinel values and records its calls."""

    def __init__(
        self,
        *,
        cuda: bool = True,
        load_errors: dict[int, Exception] | None = None,
        prompts: dict[str, str] | None = None,
    ) -> None:
        self.cuda = cuda
        self.load_errors = load_errors or {}
        self.prompt_value = (
            {"query": "query: ", "document": "passage: "} if prompts is None else prompts
        )
        self.loads: list[tuple[str, str, str | None]] = []
        self.snapshots: list[bool] = []
        self.unloaded: list[Any] = []
        self.embedded: list[tuple[str, list[str]]] = []

    def environment(self) -> dict[str, Any]:
        return {
            "python": "3.12.0",
            "platform": "Test-OS",
            "torch": "0.0.1",
            "transformers": "0.0.2",
            "sentence_transformers": "0.0.3",
            "numpy": "0.0.4",
            "cuda_available": self.cuda,
            "cuda_runtime": "99.9",
            "driver": DRIVER,
            "gpu_name": GPU_NAME,
            "gpu_memory_bytes": 12884901888,
        }

    def snapshot(self, model_id: str, allow_download: bool) -> dict[str, Any]:
        self.snapshots.append(allow_download)
        return {
            "path": "/fake/snapshots/" + REVISION,
            "revision": REVISION,
            "files": [(f"file-{index}.bin", 1000 + index) for index in range(12)],
            "sharded_weights": False,
        }

    def load(self, model_id: str, path: str, dtype: str, attention: str | None) -> SimpleNamespace:
        self.loads.append((model_id, dtype, attention))
        error = self.load_errors.get(len(self.loads))
        if error is not None:
            raise error
        if model_id != "nvidia/Nemotron-3-Embed-1B-BF16":
            kind = "minilm"
        else:
            kind = {"bfloat16": "bf16", "float32": "fp32"}[dtype]
        return SimpleNamespace(
            kind=kind, load_seconds=LOAD_SECONDS[kind], native_max_seq_length=32768
        )

    def prompts(self, handle: Any) -> dict[str, str]:
        return self.prompt_value

    def embed(self, handle: Any, texts: list[str], batch_size: int, repeats: int) -> dict[str, Any]:
        self.embedded.append((handle.kind, list(texts)))
        each = len(texts) / TEXTS_PER_SECOND[handle.kind]
        return {
            "vectors": fake_vectors(handle.kind, len(texts)),
            "seconds": [each * 0.9, each, each * 1.1],
            "peak_allocated_bytes": PEAK_BYTES[handle.kind],
        }

    def max_tokens(self, handle: Any, texts: list[str]) -> int:
        return 4321

    def unload(self, handle: Any) -> None:
        self.unloaded.append(handle)


def run_with(
    spike: ModuleType, out: Path, backend: FakeBackend, *extra: str
) -> tuple[int, dict[str, Any]]:
    args = spike.build_parser().parse_args(["--out-dir", str(out), *extra])
    code = spike.run_spike(args, backend)
    log_path = out / "gpu-spike-log.json"
    log = json.loads(log_path.read_text(encoding="utf-8")) if log_path.exists() else {}
    return code, log


def run_script(*argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-I", str(SCRIPT), *argv],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


# --- isolation ----------------------------------------------------------------------------


def test_script_is_self_contained() -> None:
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    top_level: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            top_level.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            top_level.add(node.module.split(".")[0])
    assert top_level <= set(sys.stdlib_module_names), top_level - set(sys.stdlib_module_names)
    everywhere: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            everywhere.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            everywhere.add(node.module.split(".")[0])
    assert "mindrian_eureka" not in everywhere
    assert not (top_level & set(HEAVY))


def test_help_needs_only_the_standard_library() -> None:
    result = run_script("--help")
    assert result.returncode == 0, result.stderr
    for option in (
        "--dry-run",
        "--allow-download",
        "--out-dir",
        "--records",
        "--minilm-dir",
        "--cpu-vectors",
        "--render-doc",
        "--log",
    ):
        assert option in result.stdout, option


def test_dry_run_writes_a_skeleton_without_numbers(tmp_path: Path, spike: ModuleType) -> None:
    out = tmp_path / "out"
    code = (
        "import json, runpy, sys\n"
        f"sys.argv = [{str(SCRIPT)!r}, '--dry-run', '--out-dir', {str(out)!r}]\n"
        "status = None\n"
        "try:\n"
        f"    runpy.run_path({str(SCRIPT)!r}, run_name='__main__')\n"
        "except SystemExit as stop:\n"
        "    status = stop.code\n"
        f"loaded = [name for name in {HEAVY!r} if name in sys.modules]\n"
        "print(json.dumps({'status': status, 'loaded': loaded}))\n"
    )
    result = subprocess.run(
        [sys.executable, "-I", "-c", code], capture_output=True, text=True, timeout=60, check=False
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout.strip().splitlines()[-1])
    assert report["status"] in (0, None)
    assert report["loaded"] == []
    log = json.loads((out / "gpu-spike-log.json").read_text(encoding="utf-8"))
    assert log["schema_version"] == "eureka.encoder-spike-log.v1"
    assert log["status"] == "not_run"
    for dotted, _label, _kind in spike.LOG_FIELDS:
        assert spike.lookup(log, dotted) is None, dotted


def test_out_dir_inside_the_repository_is_refused(tmp_path: Path) -> None:
    target = ROOT / "spike-out-should-not-exist"
    assert not target.exists()
    result = run_script("--dry-run", "--out-dir", str(target))
    assert result.returncode == 2
    text = result.stdout + result.stderr
    assert "outside the repository" in text
    assert not target.exists()


def test_remote_code_is_never_enabled() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "trust_remote_code=False" in source
    assert "trust_remote_code=True" not in source


def test_defaults_equal_the_gpu_profile(spike: ModuleType) -> None:
    profile = PROFILES["gpu-nemotron"]
    assert spike.MODEL_ID == profile.model_id
    assert spike.QUERY_PREFIX == profile.query_prefix
    assert spike.DOCUMENT_PREFIX == profile.document_prefix
    assert spike.MAX_SEQ_LENGTH == profile.max_seq_length
    assert spike.BATCH_SIZE == profile.batch_size


def test_log_fields_are_unique_triples(spike: ModuleType) -> None:
    paths = [dotted for dotted, _label, _kind in spike.LOG_FIELDS]
    assert len(paths) == len(set(paths))
    kinds = {"str", "int", "float2", "gib", "bool", "overlap4"}
    for dotted, label, kind in spike.LOG_FIELDS:
        assert kind in kinds, dotted
        assert label and "|" not in label


# --- runs against the fake backend --------------------------------------------------------


def test_success_run_records_what_the_backend_returned(tmp_path: Path, spike: ModuleType) -> None:
    out = tmp_path / "out"
    fake = FakeBackend()
    code, log = run_with(spike, out, fake)
    assert code == 0
    assert log["status"] == "recorded"
    ids = record_ids()
    assert len(ids) == 36
    look = spike.lookup
    assert look(log, "environment.gpu_name") == GPU_NAME
    assert look(log, "environment.driver") == DRIVER
    assert look(log, "load.bf16.seconds") == 3.5
    assert look(log, "load.fp32.seconds") == 7.25
    assert look(log, "memory.bf16.peak_allocated_bytes") == PEAK_BYTES["bf16"]
    assert look(log, "memory.fp32.peak_allocated_bytes") == PEAK_BYTES["fp32"]
    assert look(log, "speed.bf16.texts_per_second") == pytest.approx(41.5)
    assert look(log, "speed.fp32.texts_per_second") == pytest.approx(29.75)
    assert look(log, "model.revision") == REVISION
    assert look(log, "model.file_count") == 12
    assert look(log, "embedding.dimension") == WIDTH
    assert look(log, "embedding.max_seq_length") == 32768
    assert look(log, "texts.count") == 36
    assert look(log, "texts.max_tokens") == 4321
    assert look(log, "load.bf16.ok") is True
    assert look(log, "load.fp32.ok") is True
    assert look(log, "load.needs_remote_code") is False
    expected = own_overlap(fake_vectors("bf16", 36), fake_vectors("fp32", 36), ids)
    assert look(log, "drift.bf16_vs_fp32.top200_overlap") == pytest.approx(expected)
    assert look(log, "drift.minilm_gpu_vs_cpu.top200_overlap") is None
    for name in ("nemotron-bf16-vectors.npz", "nemotron-fp32-vectors.npz"):
        with np.load(out / name, allow_pickle=False) as data:
            assert [str(item) for item in data["ids"]] == ids
            assert data["vectors"].shape == (36, WIDTH)
            assert data["vectors"].dtype == np.float32
    assert len(fake.unloaded) == 2
    # The log keeps no folder path and no user name.
    text = (out / "gpu-spike-log.json").read_text(encoding="utf-8")
    assert "/fake/snapshots" not in text
    assert str(tmp_path) not in text
    assert text.endswith("\n")


def test_documents_are_embedded_with_the_document_prefix(
    tmp_path: Path, spike: ModuleType
) -> None:
    fake = FakeBackend()
    run_with(spike, tmp_path / "out", fake)
    assert fake.embedded
    for _kind, texts in fake.embedded:
        assert len(texts) == 36
        assert all(text.startswith("passage: ") for text in texts)


@pytest.mark.parametrize(
    ("prompts", "expected"),
    [
        ({"query": "query: ", "document": "passage: "}, (True, True)),
        ({"query": "query:", "document": "passage:"}, (False, False)),
        ({}, (None, None)),
    ],
)
def test_prefix_confirmation(
    tmp_path: Path,
    spike: ModuleType,
    prompts: dict[str, str],
    expected: tuple[bool | None, bool | None],
) -> None:
    _code, log = run_with(spike, tmp_path / "out", FakeBackend(prompts=prompts))
    assert spike.lookup(log, "embedding.query_prefix_confirmed") is expected[0]
    assert spike.lookup(log, "embedding.document_prefix_confirmed") is expected[1]
    if prompts:
        assert repr(prompts) == spike.lookup(log, "embedding.prompts")


def test_remote_code_stops_the_run(
    tmp_path: Path, spike: ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    error = ValueError("This model needs trust_remote_code=True to run")
    fake = FakeBackend(load_errors={1: error})
    code, log = run_with(spike, tmp_path / "out", fake)
    assert code == 3
    assert len(fake.loads) == 1
    assert log["status"] == "partial"
    assert spike.lookup(log, "load.needs_remote_code") is True
    assert spike.lookup(log, "load.bf16.ok") is False
    assert spike.lookup(log, "load.fp32.ok") is None
    assert spike.lookup(log, "load.fp32.seconds") is None


def test_out_of_memory_in_the_second_run_keeps_the_first(
    tmp_path: Path, spike: ModuleType
) -> None:
    fake = FakeBackend(load_errors={2: RuntimeError("CUDA out of memory")})
    code, log = run_with(spike, tmp_path / "out", fake)
    assert code == 0
    assert log["status"] == "partial"
    assert spike.lookup(log, "load.fp32.ok") is False
    assert "out of memory" in spike.lookup(log, "load.fp32.error")
    assert spike.lookup(log, "load.bf16.ok") is True
    assert spike.lookup(log, "load.bf16.seconds") == 3.5
    assert spike.lookup(log, "speed.bf16.texts_per_second") == pytest.approx(41.5)
    assert spike.lookup(log, "memory.bf16.peak_allocated_bytes") == PEAK_BYTES["bf16"]
    assert spike.lookup(log, "drift.bf16_vs_fp32.top200_overlap") is None


def test_attention_fallback_is_recorded(tmp_path: Path, spike: ModuleType) -> None:
    fake = FakeBackend(load_errors={1: RuntimeError("sdpa is not supported here")})
    code, log = run_with(spike, tmp_path / "out", fake)
    assert code == 0
    assert spike.lookup(log, "load.bf16.ok") is True
    assert spike.lookup(log, "load.bf16.attention_used") == "default"
    attempts = log["load"]["attempts"]
    assert [item["attention"] for item in attempts[:2]] == ["sdpa", "default"]
    assert "sdpa is not supported" in attempts[0]["error"]
    assert attempts[1]["error"] is None
    assert fake.loads[0][2] == "sdpa"
    assert fake.loads[1][2] is None


def test_sdpa_is_the_first_try(tmp_path: Path, spike: ModuleType) -> None:
    fake = FakeBackend()
    _code, log = run_with(spike, tmp_path / "out", fake)
    assert fake.loads[0] == ("nvidia/Nemotron-3-Embed-1B-BF16", "bfloat16", "sdpa")
    assert spike.lookup(log, "load.bf16.attention_used") == "sdpa"
    assert fake.loads[1][1] == "float32"


def test_no_cuda_stops_before_any_load(
    tmp_path: Path, spike: ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    fake = FakeBackend(cuda=False)
    code, log = run_with(spike, tmp_path / "out", fake)
    assert code == 3
    assert fake.loads == []
    assert fake.snapshots == []
    assert log["status"] == "not_run"
    shown = capsys.readouterr()
    assert "No CUDA device was found. This script measures the GPU." in shown.out + shown.err


@pytest.mark.parametrize(("flag", "expected"), [([], False), (["--allow-download"], True)])
def test_download_needs_the_flag(
    tmp_path: Path, spike: ModuleType, flag: list[str], expected: bool
) -> None:
    fake = FakeBackend()
    run_with(spike, tmp_path / "out", fake, *flag)
    assert fake.snapshots == [expected]


def test_optional_minilm_drift(tmp_path: Path, spike: ModuleType) -> None:
    ids = record_ids()
    cpu = fake_vectors("cpu", 36)
    cpu_file = tmp_path / "cpu.npz"
    np.savez(cpu_file, ids=np.array(ids), vectors=cpu, fingerprint=np.array("sha256:test"))
    minilm_dir = tmp_path / "minilm"
    minilm_dir.mkdir()
    fake = FakeBackend()
    code, log = run_with(
        spike,
        tmp_path / "out",
        fake,
        "--minilm-dir",
        str(minilm_dir),
        "--cpu-vectors",
        str(cpu_file),
    )
    assert code == 0
    assert len(fake.loads) == 3
    assert fake.loads[2][1] == "float32"
    assert fake.loads[2][0] != "nvidia/Nemotron-3-Embed-1B-BF16"
    expected = own_overlap(fake_vectors("minilm", 36), cpu, ids)
    assert spike.lookup(log, "drift.minilm_gpu_vs_cpu.top200_overlap") == pytest.approx(expected)
    minilm_texts = [texts for kind, texts in fake.embedded if kind == "minilm"][0]
    assert not any(text.startswith("passage: ") for text in minilm_texts)


def test_minilm_options_come_as_a_pair(tmp_path: Path, spike: ModuleType) -> None:
    fake = FakeBackend()
    code, _log = run_with(spike, tmp_path / "out", fake, "--minilm-dir", str(tmp_path))
    assert code == 2
    assert fake.loads == []


# --- the page renderer -----------------------------------------------------------------


PAGE = (
    "---\nstatus: not_run\n---\n\n# Title\n\nBefore the block.\n\n"
    "<!-- spike-table:start -->\nold text\n<!-- spike-table:end -->\n\nAfter the block.\n"
)


def table_rows(text: str) -> list[str]:
    start = text.index("<!-- spike-table:start -->")
    end = text.index("<!-- spike-table:end -->")
    return [line for line in text[start:end].splitlines() if line.startswith("|")]


def test_render_doc_fills_the_block(tmp_path: Path, spike: ModuleType) -> None:
    page = tmp_path / "page.md"
    # A dry-run log: every value cell is NOT RUN.
    skeleton = tmp_path / "skeleton.json"
    skeleton.write_text(json.dumps(spike.skeleton_log()), encoding="utf-8")
    page.write_text(PAGE, encoding="utf-8")
    result = run_script("--render-doc", str(page), "--log", str(skeleton))
    assert result.returncode == 0, result.stderr
    text = page.read_text(encoding="utf-8")
    rows = table_rows(text)
    assert rows[0] == "| Measure | Value | Log field |"
    body = rows[2:]
    assert len(body) == len(spike.LOG_FIELDS)
    for row, (dotted, label, _kind) in zip(body, spike.LOG_FIELDS, strict=True):
        assert row == f"| {label} | NOT RUN | `{dotted}` |"
    assert "Before the block.\n" in text and "After the block.\n" in text
    assert "status: not_run" in text

    # A success log from the fake backend: cells equal the formatted log values.
    out = tmp_path / "out"
    _code, log = run_with(spike, out, FakeBackend())
    page.write_text(PAGE, encoding="utf-8")
    result = run_script("--render-doc", str(page), "--log", str(out / "gpu-spike-log.json"))
    assert result.returncode == 0, result.stderr
    rendered = page.read_text(encoding="utf-8")
    rows = {line.split(" | ")[2].strip("` |"): line for line in table_rows(rendered)[2:]}
    label_of = {dotted: label for dotted, label, _kind in spike.LOG_FIELDS}
    overlap = spike.lookup(log, "drift.bf16_vs_fp32.top200_overlap")
    expected_cells = {
        "load.bf16.seconds": "3.50",
        "load.fp32.seconds": "7.25",
        "memory.bf16.peak_allocated_bytes": "2.00",
        "memory.fp32.peak_allocated_bytes": "4.00",
        "speed.bf16.texts_per_second": "41.50",
        "speed.fp32.texts_per_second": "29.75",
        "environment.gpu_name": GPU_NAME,
        "model.file_count": "12",
        "load.bf16.ok": "yes",
        "load.needs_remote_code": "no",
        "drift.bf16_vs_fp32.top200_overlap": f"{overlap:.4f}",
        "drift.minilm_gpu_vs_cpu.top200_overlap": "NOT RUN",
        "load.bf16.error": "none",
    }
    for dotted, cell in expected_cells.items():
        assert rows[dotted] == f"| {label_of[dotted]} | {cell} | `{dotted}` |", dotted
    assert "status: recorded" in rendered
    assert "Before the block.\n" in rendered and "After the block.\n" in rendered

    # Rendering twice gives equal text.
    result = run_script("--render-doc", str(page), "--log", str(out / "gpu-spike-log.json"))
    assert result.returncode == 0
    assert page.read_text(encoding="utf-8") == rendered


def test_render_doc_refuses_a_page_without_markers(tmp_path: Path, spike: ModuleType) -> None:
    page = tmp_path / "page.md"
    page.write_text("# No markers here\n", encoding="utf-8")
    log = tmp_path / "log.json"
    log.write_text(json.dumps(spike.skeleton_log()), encoding="utf-8")
    result = run_script("--render-doc", str(page), "--log", str(log))
    assert result.returncode == 2
    assert page.read_text(encoding="utf-8") == "# No markers here\n"
