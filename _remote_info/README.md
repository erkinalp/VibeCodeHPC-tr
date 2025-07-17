# _remote_info Directory Structure

スパコン固有の接続情報とプロジェクト設定を格納するディレクトリです。

⚠️ **重要**: このディレクトリはGit管理対象外です。
機密情報を含むため、絶対にコミットしないでください。

## 推奨フォルダ構成

```
_remote_info/
├── flow/              # スパコン不老の場合
│   ├── ssh.conf
│   ├── budget.txt # 予算制限
│   ├── modules.list
│   └── job_templates/
│
└── other_systems/     # 他のSSH先
```

## 必須ファイル例

### `/ssh.conf`
```bash
HOST=your.super.computer.jp
USER=your_user_id
PROJECT_ID=your_project_id
BASE_DIR=/work/your_project
```

### `/budget.txt`
```
開始時のユーザ予算：絶対値
ユーザが使用を許可した予算：相対値

上記２つから計算された、絶対に超えてはならない予算のライン：絶対値
```

## セキュリティ注意事項
- ファイル権限: `chmod 600` で設定
- パスワード・秘密鍵🔑は外部のssh-agentで管理
