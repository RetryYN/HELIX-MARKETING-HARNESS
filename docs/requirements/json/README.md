# 要件 JSON 正本

> 要件エンティティの機械可読正本（PO 方針 2026-07-30: 要件定義以降は JSON で変換性能を上げる）。
> 人の承認・閲覧は MD、実装・変換・検証の入力は本ディレクトリの JSON を用いる。編集時は両方を同期する。

| ファイル | 内容 | 件数 |
|---|---|---|
| br.json | 業務要求（BR 背骨） | 31 |
| br-media.json | 媒体別業務要求（BR-M）＋ §99 判断（decided 4 / pending 4） | 70 |
| req.json | 要求一覧（REQ） | 45 |
| requirements.json | FR 36 / NFR 10 / AC 19（Given/When/Then 展開付き）＋ deferred 17 | 65 |
| fn.json | 機能一覧（FN） | 61 |
| mr.json | 媒体別詳細要件（MR） | 54 |
| ltw.json | loops 10 / task_types 13 / workflows 44 / poc 13 | — |

検証: すべて `python3 -m json.tool` が通ること。件数は元 MD の分母と一致させること（ズレ = 同期漏れ）。
