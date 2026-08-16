"""run_all の baseline 更新における非承認 content-binding receipt の境界。"""

from __future__ import annotations

from tools.gates import run_all


def test_receipt_index_accepts_verified_content_binding_migration() -> None:
    index = run_all._receipt_index()

    assert "e36352ef7e92" in index[
        ("ADR-013-vps-product-ui-primary-human-interface", "-")
    ]


def test_mutation_invalid_content_binding_migration_is_rejected(monkeypatch) -> None:
    monkeypatch.setattr(
        run_all.authority,
        "content_binding_migration_faults",
        lambda _ctx: ["synthetic invalid migration"],
    )

    index = run_all._receipt_index()

    assert "e36352ef7e92" not in index.get(
        ("ADR-013-vps-product-ui-primary-human-interface", "-"), set()
    )
