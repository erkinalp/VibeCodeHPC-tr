# 🔌 wcgw運用ガイド

## 概要

wcgwは、SSH接続時の以下の課題を解決するための外部ツールです：
- 2段階認証の処理
- 大容量ファイル転送の効率化
- 大量の標準出力によるコンテキスト浪費の防止

## 運用方針

### wcgw使用対象
- **CI（Continuous Integration）エージェント**: 主要なwcgw使用者
  - ジョブ実行ログの取得
  - 大容量ファイルの転送（SFTP）
  - 長時間のコンパイル・実行処理

### wcgw不使用対象
- **PM/SE**: 環境調査時は直接SSH（wcgwを介さない）
- **PG**: コード生成に集中するため使用しない
- **CD**: 緊急時を除きSSH接続しない

### サブエージェントでの対応
大量データ通信が必要な場合は、`claude -p` によるサブエージェントで対応：
```bash
# 例：大容量ログの解析
cat huge_job_output.log | claude -p "エラーメッセージを抽出して要約"
```

## ディレクトリ構造の維持

### 重要な原則
- **リモート環境でもローカルと同じディレクトリ階層を維持**
- これによりmakefileや.bashrcの混同を防ぐ
- directory_map.txtの階層を再現することを推奨

### 階層再現の範囲
- エージェント配置ディレクトリまでは厳密に再現
- PGが作成する下位階層は、実行に影響なければ自由

## wcgw初期設定手順（CI用）

### 1. thread_id作成の担当
- **2段階認証がある場合**: PMが主導（ユーザとの対話が必要）
  - サブエージェント（`claude -p`）を活用して効率化
- **2段階認証がない場合**: 各CIが自分用のthread_idを作成
  - 必要に応じて追加作成（全員が5個作るのは避ける）

### 2. thread_id作成手順
```bash
# 各CIエージェントが自分用に1-2個作成
# wcgwでinitialize実行
# thread_id_CI1.1_main, thread_id_CI1.1_backup など命名
```

### 3. thread_idの管理
- 各CIエージェントが自分のthread_idを管理
- 必要に応じて追加作成
- 各CIのローカルディレクトリにwcgw_thread_id_list.txtを作成・更新

## MCP設定の運用

### 現在の方針
- プロジェクトレベル（-s project）の.mcp.jsonは使用しない
  - 許可が毎回求められる問題
  - .mcp.jsonが読み込まれないバグ
- ローカルスコープ（デフォルト）で各エージェントごとに設定

### エージェント割り当て時の手順
```bash
# 方法1: MCP不要な場合（PG等）
agent-send.sh CI1.1 "!cd Flow/TypeII/single-node/gcc11.3.0/OpenMP && claude --dangerously-skip-permissions"

# 方法2: MCP必要な場合（CI）
# 1. MCPサーバ追加
claude mcp add
# 2. 2分待機（timeout）
sleep 120
# 3. 終了
exit
# 4. 再起動
claude --dangerously-skip-permissions
```

## 効率化のヒント

### CIエージェントの事前準備
1. プロジェクト開始時にCIエージェントのMCP設定を一括実行
2. thread_idプールを作成しておく
3. 必要に応じて使い回し

### 緊急時の対応
- PM/SEが一時的にwcgwを使用する場合は、予備thread_idを使用
- 使用後は必ずクリーンアップ

## まとめ

wcgwは主にCIエージェントが使用し、その他のエージェントは必要最小限の使用に留めます。この運用により、効率的なSSH接続管理とコンテキスト消費の最適化を実現します。