"""⑥単体テスト設計の割当先（S0.1 test-first で実装 — 実装前に赤を確認してから緑にする）。"""

import pytest

pytest.skip("S0.1 test-first: 対応 DU の実装と同時に赤→緑（utest.json の割当が正本）",
            allow_module_level=True)
