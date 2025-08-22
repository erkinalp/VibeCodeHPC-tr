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
│   └── load_custom_module.md  # モジュール読み込み手順
│
└── fugaku/                 # 富岳の場合
    └── （同様の構成）
```

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
