---
artifact_id: L2-PROTOTYPES-INDEX
lifecycle_status: draft
slice: S1
---

# L2 プロトタイプ設計

> status: **draft**。HELIX-HARNESS の L2 方法論を、screen／workflow／operating-scenario の責務へ整理する。
> 現在は要求基準を再定義中であり、配下の内容は旧要求で書式を評価した参考資料である。
> 新要求の製品設計・実装入力には使わず、要求承認後に内容を再作成する。

## フォルダ責務

| フォルダ | 正本の責務 | 現状 |
|---|---|---|
| `screens/` | screen-list、screen-flow、ui-element、wireframe、screen-detail の 5 点セット | S1 draft |
| `workflows/` | actor lane、判断点、画面 edge、外部境界を横断する業務 flow | S1 draft |
| `operating-scenarios/` | 実運用の normal／cancel／failure／timeout シナリオと観測計画 | 未着手 |

## 読み順

1. [画面一覧](screens/ui-screen-list_v0.1.md) で screen ID／route／read-write 境界を確認する。
2. [画面フロー](screens/screen-flow_v0.1.md) で trigger、状態保持、back、失敗出口を確認する。
3. [UI 要素](screens/ui-element_v0.1.md) と [wireframe](screens/wireframe_v0.1.md) で表示・操作・layout を確認する。
4. [画面詳細](screens/screen-detail_v0.1.md) の 13-field matrix と相互突合する。
5. [business flow](workflows/business-flow_v0.1.md) で PO／operator／system／外部 channel の判断点を確認する。

画面実装を開始する前に、L3 契約、認証・CSRF・principal 束縛、AC／TC、承認 digest が揃っていることを確認する。
