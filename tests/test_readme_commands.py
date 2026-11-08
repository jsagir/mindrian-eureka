"""W2 proof: the README shows the doctor and run commands before the quick start."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
HEADING = "## Run Eureka on your own folder"
NEXT_HEADING = "## Quick start"
SHORT_CODE = re.compile(r"\b(R[S]|H[S]I)\b")
FENCE = re.compile(r"```bash\n(.*?)```", re.DOTALL)


def _text() -> str:
    return README.read_text(encoding="utf-8")


def _section() -> str:
    text = _text()
    assert text.count(HEADING) == 1
    after = text.split(HEADING, 1)[1]
    return after.split("\n## ", 1)[0]


def test_section_shows_the_doctor_and_run_commands() -> None:
    commands = [line for block in FENCE.findall(_section()) for line in block.splitlines()]
    assert "uv run eureka doctor" in commands
    assert "uv run eureka run ./my-sources --out ./eureka-run" in commands
    assert "uv sync --extra modern-encoder" in commands


def test_section_holds_the_label_and_the_offline_note() -> None:
    section = _section()
    assert "candidate, not verified" in section
    assert "Every result is a candidate, not verified. It is a lead for human review." in section
    assert "downloads nothing" in section
    assert "no network call" in section


def test_section_link_target_exists() -> None:
    section = _section()
    targets = re.findall(r"\]\(([^)#]+)\)", section)
    assert "docs/offline-install.md" in targets
    for target in targets:
        assert (ROOT / target).exists(), target


def test_section_has_no_short_engine_code_and_no_dash_characters() -> None:
    section = _section()
    assert SHORT_CODE.search(section) is None
    assert chr(0x2014) not in section
    assert chr(0x2013) not in section


def test_section_sits_before_the_quick_start() -> None:
    text = _text()
    assert text.index(HEADING) < text.index(NEXT_HEADING)


HUB_HEADING = "## Open the results as one page"


def _hub_section() -> str:
    return _text().split(HUB_HEADING, 1)[1].split("\n## ", 1)[0]


def test_hub_section_commands_position_and_limits() -> None:
    text = _text()
    assert text.count(HUB_HEADING) == 1
    assert text.index(HEADING) < text.index(HUB_HEADING) < text.index(NEXT_HEADING)
    section = _hub_section()
    assert "uv run eureka hub ./eureka-run --out ./eureka-hub" in section
    assert "uv sync --extra hub-gate" in section
    assert "--password-env HUB_PASS" in section and "--source-dir ./my-sources" in section
    assert "Every result is a candidate, not verified." in section
    assert "It does not protect a computer that already has the passphrase." in section
    assert "The data is readable in the browser after unlock." in section
    assert "sends nothing over the internet" in section
    assert "Original run folders, source files and older open exports remain readable." in section
    assert SHORT_CODE.search(section) is None
    assert not any(char in section for char in (chr(8211), chr(8212)))
    for target in re.findall(r"\]\(([^)#]+)\)", section):
        assert (ROOT / target).is_file(), target


PROFILE_HEADING = "### Choose an encoder profile"


def _profile_section() -> str:
    text = _text()
    assert text.count(PROFILE_HEADING) == 1
    return text.split(PROFILE_HEADING, 1)[1].split("\n## ", 1)[0]


def _help_text(*args: str) -> str:
    import contextlib
    import io

    from mindrian_eureka.cli import main

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), contextlib.suppress(SystemExit):
        main([*args, "--help"])
    return buffer.getvalue()


def test_profile_section_commands_and_flags_exist_in_the_parser_help() -> None:
    section = _profile_section()
    assert "uv run eureka doctor --encoder-profile gpu-nemotron" in section
    assert "--encoder-profile gpu-nemotron --model-path" in section
    for command in ("run", "doctor"):
        assert "--encoder-profile" in _help_text(command)
    assert "--model-path" in _help_text("run")
    assert "uv sync --extra gpu-encoder" in section


def test_profile_section_names_the_profiles_the_code_defines() -> None:
    from mindrian_eureka.encoder_spec import DEFAULT_PROFILE, GPU_PROFILE, PROFILES

    section = _profile_section()
    assert DEFAULT_PROFILE in PROFILES and GPU_PROFILE in PROFILES
    assert f"`{DEFAULT_PROFILE}`" in section and f"`{GPU_PROFILE}`" in section
    assert PROFILES[DEFAULT_PROFILE].model_id in section
    assert PROFILES[GPU_PROFILE].model_id in section


def test_profile_section_does_not_overclaim_the_spike() -> None:
    section = _profile_section()
    assert "unproven" in section and "not run yet" in section
    assert "MiniLM stays the default encoder." in section
    assert "Result: NO MATCH" in section and "eureka.encoder-block.v1" in section
    assert "candidate, not verified" in _text()
    assert not any(char in section for char in (chr(8211), chr(8212)))
    for target in re.findall(r"\]\(([^)#]+)\)", section):
        assert (ROOT / target).is_file(), target


def test_extras_table_lists_every_extra_of_the_project() -> None:
    import tomllib

    extras = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"][
        "optional-dependencies"
    ]
    table = _text().split("Optional extras, from `pyproject.toml`:", 1)[1].split("\n\n", 2)[1]
    for name in extras:
        assert f"| `{name}` |" in table, name


def test_public_example_readme_names_the_gpu_approx_behavior() -> None:
    text = (ROOT / "examples" / "public-example" / "README.md").read_text(encoding="utf-8")
    assert "gpu-approx" in text and "Result: NO MATCH" in text
    assert "not run yet" in text and "unproven" in text
    assert not any(char in text for char in (chr(8211), chr(8212)))
