# _remote_info 階層構造

スパコン固有の接続情報とプロジェクト設定を格納するディレクトリです。

⚠️ **重要**: このディレクトリはGit管理対象外です。
機密情報を含むため、絶対にコミットしないでください。

## フォルダ構成例

```
_remote_info/
├── flow/                   # スパコン不老の場合
│   ├── user_info.md        # SSH接続情報とリモート作業ディレクトリ
│   ├── command_list.md     # システム固有のコマンド一覧
│   ├── sample_bash.sh      # ジョブスクリプトのサンプル
│   ├── load_custom_module.md  # モジュール読み込み手順
│   └── node_resource_groups.md  # 🆕 リソースグループ制限一覧（必須）
│
└── fugaku/                 # 富岳の場合
    └── （同様の構成）
```

## 必須追加ファイル

### `node_resource_groups.md` - リソースグループ制限一覧
**重要**: 各スパコンディレクトリに必ず追加してください。

#### 記載内容
- 各リソースグループ（ジョブクラス）の詳細仕様をMarkdownテーブル形式で記載
- 以下の情報を含める：
  - リソースグループ名（cx-small, fx-large等）
  - 最小/最大ノード数
  - CPU/GPUコア数
  - メモリ容量
  - 最大実行時間（デフォルト値と最大値）
  - 料金レート（ポイント/秒）
  - 備考（ノード共有、優先実行等）

#### 取得方法
1. スパコンの公式ドキュメントページから表をコピー
2. Markdown形式のテーブルに変換
3. 料金計算式を明記（例: TypeII = 0.007ポイント/秒×GPU数）

#### 用途
- **PM**: 初期化時に読み込み、リソース配分戦略を決定
- **PG**: ジョブ投入時に適切なリソースグループを選択
- **予算管理**: ジョブ実行コストの推定計算に使用

## ファイル内容の例

### `/flow/user_info.md`
```markdown
- **SSH情報**: username@supercomputer.example.jp
- **SSH先で使用するディレクトリ**: /data/username/VibeCodeHPC/project_name/
```

### `/flow/command_list.md`
システムで利用可能なコマンドの一覧。例：
- ジョブ管理: `pjsub`, `pjstat`, `pjdel`
- 予算確認: `charge`（パス設定: `export PATH=/home/center/local/bin:${PATH}`）
- 環境設定: `module avail`, `module load`

### `/flow/sample_bash.sh`
```bash
#!/bin/bash
#PJM -L rscgrp=cx-small      # リソースグループ指定
#PJM -L node=2               # ノード数
#PJM --mpi proc=8            # MPIプロセス数
#PJM -L elapse=1:00:00       # 実行時間
#PJM -j                      # 標準エラー出力をマージ

module load oneapi
export OMP_NUM_THREADS=10
mpiexec -machinefile $PJM_O_NODEINF -n $PJM_MPI_PROC ./a.out
```

## セキュリティ注意事項
- ファイル権限: `chmod 600` で設定
- パスワード・秘密鍵🔑は外部のssh-agentで管理
