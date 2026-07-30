# 設計 JSON 正本

②基本設計・④総合テスト設計の機械可読正本。MD が承認単位、JSON が実装入力（両方同期、ゲートで検証）。

| ファイル | 内容 | 分母 | 主な検証ゲート |
|---|---|---|---|
| components.json | ②の CMP 台帳（13 コンポーネント、S0 25 FN を完全被覆） | CMP 13 | G-CMP-CNT/UNIQ/FN |
| itest.json | ④の ITC 台帳（fixtures・assertions 構造化、ペア台帳含む） | ITC 16 | G-ITC-*、G-PAIR2-HDR |

編集時は MD・JSON・`docs/governance/baseline.json`（`--update-baseline`）を同一コミットで更新すること。
