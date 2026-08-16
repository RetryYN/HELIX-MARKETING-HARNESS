from pathlib import Path

from scripts import dev


def test_doctor_reaches_authoritative_gates_after_requirement_no_go(
    monkeypatch, tmp_path: Path
) -> None:
    required = [
        "pyproject.toml",
        "uv.lock",
        "Makefile",
        "src/helix",
        "docs/00-authority/artifact-manifest.json",
        "docs/00-authority/baselines/baseline.json",
        "docs/00-authority/template/helix-harness-alignment.json",
        "docs/00-authority/development/requirement-discovery-events.json",
        "docs/00-authority/development/requirement-discovery-event.schema.json",
    ]
    for relative in required:
        path = tmp_path / relative
        if "." not in path.name:
            path.mkdir(parents=True)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()

    calls: list[str] = []
    monkeypatch.setattr(dev, "ROOT", tmp_path)
    monkeypatch.setattr(dev, "check_python", lambda: None)
    monkeypatch.setattr(dev, "require_uv", lambda: "/usr/bin/uv")
    monkeypatch.setattr(dev, "requirements", lambda: calls.append("requirements") or 1)
    monkeypatch.setattr(dev, "docs", lambda check=False: calls.append("docs") or 0)
    monkeypatch.setattr(dev, "gates", lambda: calls.append("gates") or 1)

    assert dev.doctor() == 1
    assert calls == ["requirements", "docs", "gates"]
