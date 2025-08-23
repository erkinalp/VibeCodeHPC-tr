# 予算集計システム使用ガイド

## 概要
ChangeLog.mdに記録された時刻情報から、プロジェクトの予算消費を自動集計するシステムです。

## PG向け：ジョブ実行時の記録方法

### 1. ジョブスクリプトに時刻記録を追加
```bash
# スクリプト先頭
source $PROJECT_ROOT/Agent-shared/budget/job_time_template.sh
# または必要部分をコピー

# リソースグループを明記（重要）
RESOURCE_GROUP="cx-small"  # 使用するリソースグループ
```

### 2. ChangeLog.mdへの記録（必須）
```markdown
### v1.2.0
**生成時刻**: `2025-01-30T10:00:00Z`
**変更点**: "OpenMP並列化実装"
**結果**: 理論性能の65%達成 `312.4 GFLOPS`

<details>

- [x] **job**
    - id: `12345`
    - resource_group: `cx-small`  # 必須：料金計算に使用
    - start_time: `2025-01-30T10:00:00Z`  # 必須
    - end_time: `2025-01-30T10:45:32Z`  # 必須（完了時）
    - runtime_sec: `2732`  # 必須（完了時）
    - status: `completed`

</details>
```

### 3. キャンセル時の記録
```markdown
- [ ] **job**
    - id: `12345`
    - resource_group: `cx-small`
    - start_time: `2025-01-30T10:00:00Z`
    - cancelled_time: `2025-01-30T10:15:00Z`  # end_timeの代わり
    - runtime_sec: `900`  # キャンセルまでの実行時間
    - status: `cancelled`
```

## SE向け：集計と監視

### 1. 即座に現在の消費量を確認
```bash
# プロジェクトのどこからでも実行可能
python Agent-shared/budget/budget_tracker.py --summary

# 出力例：
# === 予算集計サマリー ===
# 総消費: 1234.5 ポイント
# ジョブ数: 完了=10, 実行中=2
# 最低: 123.5%
# 目安: 49.4%
# 上限: 24.7%
```

### 2. 詳細レポート生成
```bash
python Agent-shared/budget/budget_tracker.py --report

# snapshots/に以下が生成される：
# - budget_YYYY-MM-DDTHH-MM-SSZ.json（タイムスタンプ付き）
# - latest.json（最新版）
```

### 3. periodic_monitor.shへの統合
```bash
# 5分ごとに自動集計（periodic_monitor.shに追加済み）
if [ $((ELAPSED_MINUTES % 5)) -eq 0 ]; then
    python "$PROJECT_ROOT/Agent-shared/budget/budget_tracker.py" --report
fi
```

### 4. JSON形式での取得（可視化用）
```bash
python Agent-shared/budget/budget_tracker.py --json > budget.json
```

## リソースグループごとのレート

### 不老TypeII（デフォルト設定）
| リソースグループ | GPU数 | レート（ポイント/秒） |
|---------------|------|-------------------|
| cx-share      | 1    | 0.007            |
| cx-small      | 4    | 0.028            |
| cx-middle     | 4    | 0.028            |
| cx-middle2    | 4    | 0.056（2倍）      |

### 他のスパコンへの対応
`budget_tracker.py`の`load_rates()`メソッドを編集するか、
`_remote_info/[スパコン名]/node_resource_groups.md`から自動読み込み（将来実装）

## トラブルシューティング

### Q: ジョブのポイントが計算されない
A: ChangeLog.mdに以下が記載されているか確認：
- resource_group（必須）
- start_time（必須）
- end_timeまたはcancelled_time（実行後必須）

### Q: 集計結果が0ポイント
A: プロジェクト開始時刻が記録されているか確認：
```bash
cat Agent-shared/project_start_time.txt
```

### Q: 実行中のジョブが反映されない
A: statusが`running`になっているか確認。end_timeが無い場合は現在時刻まで計算されます。

## 注意事項

- **ステートレス実行**: 毎回全ChangeLog.mdを読み直すため、ファイル数が多い場合は時間がかかる可能性があります
- **リアルタイム性**: ChangeLog.mdへの記録タイミングに依存します（PGが記録するまで反映されません）
- **精度**: 秒単位での計算のため、実際の課金との誤差は最大で数ポイント程度です