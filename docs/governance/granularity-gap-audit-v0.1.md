# 粒度ギャップ監査 v0.1（HELIX-HARNESS 基準）

> status: **active**（2026-08-01 PO 指示「全層再降下・粒度是正」ステップ 1）
> 機械可読正本: [json/granularity-gap-audit.json](json/granularity-gap-audit.json)
> 基準正本: マーケティング思想 = TAKUMI_CMO-Claude_Cowark ／ 二重ループ思想 =
> [charter v0.4](../L0-charter/marketing-harness-charter_v0.4.md) ／ 成果物粒度・契約強度・機械ゲート =
> HELIX-HARNESS 最新 main（`~/HELIX-HARNESS`）。本体をコピーせず、粒度・契約・トレース・fail-close
> 構造をマーケティングへ**翻訳**する。

---

## 0. 総括 — 実測

| 観点 | HELIX-HARNESS | 本リポジトリ（監査時点） |
|---|---|---|
| 設計文書 | 86 文書・12,512 行（L1〜L14、要求→要件 2 段階＋L6 機能別設計 20 本） | 要件 13 文書 2,634 行＋設計 6 文書（1 段階降下） |
| FR:AC 密度 | FR 26 : AC 85（全 FR に正常/異常/境界 ≥3＋人間判断点列必須） | FR 36 : AC 19（＋deferred 17）— 大半の FR に AC ゼロ |
| 詳細設計 | L5 7 sub-doc 1,271 行（export 1:1 の公開 IF・DbC・エラー分類） | ⑤ 1 文書 259 行／DU 23（責務 1 行） |
| ゲート | lint 40 本超（意味検証を含む） | 81 本（件数・参照・ペア中心。粒度の意味ゲートは実質 G-SUBSTANCE のみ） |

**根本原因**: ①が「責務 1 行」粒度で confirmed になったため、③はその粒度でしか TC を書けず、
②⑤は被覆表化した。**記述粒度そのものを fail-close するゲートが不在**だったため、薄い本文のまま
全ペアゲートを通過して confirmed に到達できた。

## 1. 層別ギャップ台帳

詳細（欠落契約項目の全列挙）は JSON 正本。ここでは各エンティティの「現状 → 下流影響 → 是正先」を示す。

| ID | エンティティ | 現状粒度 | 下流への影響 | 是正先 |
|---|---|---|---|---|
| GAP-BR | BR 31＋BR-M 70 | 1 行要求文＋trace のみ | 価値・禁止・証跡が下流へ継承されず AC が空洞化。12 独立要求群が BR 面で未分離 | 再降下2＋G-REQ-CONTRACT |
| GAP-REQ | REQ 45 | 1 行躯体 | 要求→要件の 2 段階詳細化が 1 段階に潰れる | 再降下2＋G-REQ-CONTRACT |
| GAP-FR | FR 36 | 責務 1 段落（入出力・異常系未分離） | AC が書けない（AC 19/36）。TC が状態・副作用・証跡を検証できない | 再降下3＋G-REQ-CONTRACT/G-INVARIANT-TRACE |
| GAP-SR | SR 16 | 宣言文（実行契約は契約文書へ散在） | AC-SR 6 件のみ。境界・競合が未検証 | 再降下3＋G-AC-COVERAGE |
| GAP-NFR | NFR 10 | 目標値宣言のみ | 測定方法のない閾値 = 検証不能 | 再降下3＋G-NFR-MEASURABLE |
| GAP-AC | AC 19＋17／AC-SR 6 | GWT のみ（fixture・DB 差分・証跡・禁止副作用・エラー型なし） | TC が「行が存在する」検証に退化 | 再降下4＋G-AC-COVERAGE/G-AC-POLARITY/G-HUMAN-JUDGE |
| GAP-TC | TC 59／ITC 16／STC 28 | 双方向被覆は成立、本文が観測点を規定しない | UT green が品質を意味しない | 再降下5 |
| GAP-CMP | CMP 13＋SCM 10 | 責務・被覆・依存宣言まで | IF 契約・エラー分類・degradation が⑤へ降りない。独立設計書ゼロ | 再降下6＋G-CMP-INTERFACE |
| GAP-DU | DU 23 | モジュール名簿（API 署名は DU-02 のみ） | UT が関数名を参照できない。S0.1 が無契約で始まる。機能別設計 0 本（HELIX L6 は 20 本） | 再降下7＋G-DU-API/G-DU-DBC/G-DU-ERROR/G-DU-DATA |
| GAP-UT | UTC 69／STC-I 10 | ファイル存在＋割当まで | module-level skip で green が出る | 再降下8＋G-API-UT |
| GAP-GATE | ゲート 81 | 構造整合のみ | 薄い本文のまま confirmed に到達できる（本事象） | 再降下9（14 ゲート追加） |
| GAP-SSOT | 正本管理 | MD/JSON 手動二重更新 | 二重更新コストが粒度向上を阻害 | 再降下9（JSON 内容正本化・MD 生成ビュー段階移行） |

## 2. 是正の順序（依存関係）

再降下2（要求）→ 3（要件・NFR）→ 4（AC）→ 5（検証設計）→ 6（基本設計＋独立設計書）→
7（詳細設計＋機能別設計）→ 8（単体テスト設計）→ 9（ゲート 14 本＋JSON 正本化）→
Sol ブラインドレビュー（HELIX-HARNESS 基準）Go → S0.1 実装再開。

各ステップの完了条件は PO 指示の完了条件 1〜8 に従う。分母削減は禁止（ラチェット）、
追加・分解・詳細化のみ許可。現行成果物は履歴として保持する。
