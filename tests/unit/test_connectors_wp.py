"""⑥単体テスト設計の割当先（S0.1 test-first で実装 — 実装前に赤を確認してから緑にする）。"""

import pytest


@pytest.mark.skip(reason="test-first DU-17: create_draft/publish")
def test_draft_and_publish_separate_keys_separate_rows() -> None:
    """du-contracts DU-17 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-17: create_draft")
def test_create_draft_prepared_sent_confirmed_each_commit() -> None:
    """du-contracts DU-17 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-17: publish")
def test_pair_required_rejected_zero_http() -> None:
    """du-contracts DU-17 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-17: publish")
def test_publish_without_approval_pass_rejected() -> None:
    """du-contracts DU-17 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-17: create_draft/publish")
def test_production_endpoint_denied_before_connect() -> None:
    """du-contracts DU-17 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-17: publish")
def test_sent_reconcile_confirms_without_resend() -> None:
    """du-contracts DU-17 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-17: publish")
def test_sent_unverifiable_unknown_escalates() -> None:
    """du-contracts DU-17 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-17: upload_media")
def test_upload_media_content_hash_idempotent() -> None:
    """du-contracts DU-17 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-17: register_asset")
def test_register_asset_before_published_url_evidence() -> None:
    """du-contracts DU-17 の契約観点を検証する（red→green は実装スライスで）。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-17: create_draft")
def test_draft_remote_idempotency_and_failure_boundaries() -> None:
    """remote meta冪等性、confirmed補完、cap、pre-send、sent unknownを独立fixtureで検証する。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-17: publish")
def test_publish_evidence_order_approval_and_rate_boundaries() -> None:
    """asset後証跡順序、承認なしゼロ送信、rate capのfail-closeを検証する。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-17: upload_media")
def test_upload_media_lifecycle_and_fail_close_boundaries() -> None:
    """media外部操作lifecycleとPair/endpoint/rate/unknown境界を個別fixtureで検証する。"""
    raise NotImplementedError


@pytest.mark.skip(reason="test-first DU-17: register_asset")
def test_register_asset_rejects_unconfirmed_or_invalid_binding() -> None:
    """unconfirmed操作・FK不整合の境界正規化とDB不変を検証する。"""
    raise NotImplementedError
