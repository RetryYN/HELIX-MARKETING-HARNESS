# 要件 JSON 正本

> 要件エンティティの機械可読正本（PO 方針 2026-07-30: 要件定義以降は JSON で変換性能を上げる）。
> 人の承認・閲覧は MD、実装・変換・検証の入力は本ディレクトリの JSON を用いる。編集時は両方を同期する。
> 差分局所性のため、媒体系・コレクション系はファイル分割している（1 ファイル 1 関心事）。

| パス | 内容 | 件数 |
|---|---|---|
| br.json | 業務要求（BR 背骨） | 31 |
| br-media/ | 媒体別業務要求（BR-M）— 媒体ごと 21 ファイル＋index.json（§99 判断 decided 4 / pending 4 を含む） | 70 |
| req.json | 要求一覧（REQ） | 45 |
| requirements.json | FR 36 / NFR 10 | 46 |
| ac.json | 受入条件 AC 19（Given/When/Then 展開付き）＋ deferred 17 | 19 |
| fn.json | 機能一覧（FN） | 61 |
| mr/ | 媒体別詳細要件（MR）— 媒体ごと 21 ファイル＋index.json | 54 |
| ltw/ | loops.json 10 / task-types.json 13 / workflows.json 44 / poc.json 13 | — |
| s0/ | S0 契約の機械可読形: ddl.sql・transitions.json・evidence-kinds.json・wf-contracts.json・environment.json・updates.json・migration-rules.json・trace.json | — |

検証: すべて `python3 -m json.tool` が通ること（ddl.sql は sqlite3 適用が通ること）。
件数は元 MD の分母と一致させること（ズレ = 同期漏れ）。
