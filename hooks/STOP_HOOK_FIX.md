# STOP Hook 修正内容

## 問題
ポーリング型エージェント（PM, SE, CI, CD）が待機状態に入ってしまう

## 原因
Claude Codeのフックリファレンスによると、終了コード0でJSON出力してもStopイベントでは効果がない

## 修正
```python
# 修正前（動作しない）
output = {"decision": "block", "reason": reason}
print(json.dumps(output))
sys.exit(0)

# 修正後（正しく動作）
print(reason, file=sys.stderr)
sys.exit(2)
```

## 重要な仕様
- **終了コード2**: Claudeに自動的にstderrの内容をフィードバック
- **終了コード0**: JSON出力は特定のフックイベントでのみ有効
- **Stop hookの場合**: 終了コード2が推奨される方法