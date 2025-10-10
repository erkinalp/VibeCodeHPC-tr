# VibeCodeHPC Ortak Kurallar (Tüm aracılar için ilk okunacak talimatlar)

## Temel İlke
Bir ekip olarak birlikte çalışır, HPC ortamında kodun otomatik optimizasyonu hedefini gerçekleştirmek için iş birliği yaparız. Her aracı kendi rolüne odaklanır, diğerlerinin uzmanlığına saygı duyar. Bildirim–iletişim–danışma süreçlerini düzenli yürütür, projenin genel ilerlemesini en üst düzeye çıkarırız.

## 📊 Nesnel raporlama ilkesi
Önemli: Aşırı övgü ve duygusal ifadelerden kaçının; iletişimi olgulara dayandırın.
- Kaçınılacak: “Şaşırtıcı başarı”, “Dünya çapında performans”, “Harika bir optimizasyon”
- Önerilen: “Teorik performansın %65’i elde edildi”, “Çalışma süresi 3.2 sn azaldı”, “Derleme uyarısı 0”
- Sonuç yoksa dürüstçe bildirin ve bir sonraki adımı önerin

## İletişim
- Temel araç: `agent_send.sh [hedef] "[mesaj]"` kullanın.
- Önemli: `communication/agent_send.sh` kullanılmadıkça diğer aracılar sizin yazdıklarınızı görmez.
  - Yanıtlar da mutlaka `agent_send.sh` ile gönderilmelidir
  - Mesaj içinde kendi agent_id’nizi belirtin (ör. `[PG1.1.1] Tamamlandı`)
- Not: `tmux send-keys` yalnızca Claude başlamadan önce komut iletimi ve PM’in acil durdurması içindir
  - Mesaj göndermek için asla kullanmayın (Enter/C-m gitmez, mesaj ulaşmaz)
  - Aracılar arası iletişim için daima `agent_send.sh` kullanın
- Mesaj biçimi: `[Tür] [Özet] (Detay)` şeklinde gönderin.
  - Ör: `[İstek] Derle optimized_code_v1.2.c`
  - Ör: `[Rapor] Derleme başarılı optimized_code_v1.2.c (Job ID: 12345)`
- Eşzamansız iletişim: Yanıt beklerken acil diğer işleri ilerletin

### 📡 Zorunlu yanıt kuralları (TCP benzeri)
- 3 dakika kuralı: Mesajı aldıktan sonra en geç 3 dakika içinde yanıt verin (en az “alındı”).
- 5 dakika kuralı: 5 dakika log yoksa aracı çökme şüphesi vardır.
- Canlılık izlemesi: `tmux list-panes -t Team1_Workers1` ile oturum durumunu kontrol edin.

### 🔍 Aracının hayatta olduğunun doğrulanması (Önemli: Esc göndermek yasaktır)

#### Güvenli doğrulama
```bash
# Hedef aracıya otomatik yanıt komutu gönder
./communication/agent_send.sh [TARGET_ID] "!./communication/agent_send.sh [SELF_ID] '[TARGET_ID] alive-ok'"

# Birkaç saniye bekleyip yanıtı kontrol et
# Yanıt varsa → Aracı canlı (girdi bekliyor)
# Yanıt yoksa → Gerçekten düşmüş olabilir
```

#### Diriltme adımları (yalnızca yanıtsızsa)
1. Önce PM’e rapor edip diriltme isteyin
   ```bash
   ./communication/agent_send.sh PM "[SELF_ID] [TARGET_ID] canlılık doğrulamasına yanıt vermiyor"
   ```
2. PM de yanıtsızsa doğrudan diriltin
   ```bash
   ./communication/agent_send.sh [TARGET_ID] "claude --continue --dangerously-skip-permissions"
   ```
3. Diriltme sonrası ToDo listesi ve ChangeLog kontrolünü isteyin

⚠️ Esc tuşu yetkisi:
- Yalnız PM: Aracıyı geçici durdurma (özellikle son aşama yönetimi)
- Diğer aracılar: Sadece PM çökmüşse acil durumda
- Etki: “Interrupted by user” ile girdi beklemeye geçer (mesajla devam edilebilir)
- Not: Hooks da durur; yalnızca kasıtlı kontrol için kullanın

## 📂ファイルとディレクトリ
- `cd`コマンドでの自主的な移動は禁止。全てのファイルパスはプロジェクトルートからの相対パスで指定する。
- **情報源**:
    - `Agent-shared/`以下の全てのファイルに適宜、目を通すこと。最新の階層構造（エージェント配置）などが含まれている。ただし.pyの中身まで参照する必要はない。
    - `BaseCode/`はRead Onlyの既存コードである。オリジナルが完璧でない可能性に留意せよ
    - `ChangeLog.md`: 各PGの試行錯誤の記録。**重要**: フォーマット厳守（自動化ツールが正規表現で解析するため）
    - `_remote_info/`: スパコン固有情報。
    - `hardware_info.md`: 各ハードウェア階層に配置。**理論演算性能が必ず記載されている**

## 🎯 性能評価の鉄則
**重要**: 「最初のコードから数倍速くなった」だけでは不十分。必ず理論演算性能に対する実効効率（%）で評価すること。
- 例: 「10倍高速化」→「理論性能の60%を達成」
- hardware_info.mdの理論演算性能を基準に使用

## 📊 SOTA管理とChangeLogフォーマット
**重要**: 自動化ツールの正常動作のため、以下を厳守すること：

### ChangeLog.mdフォーマット
- **結果行**: 必ず`XXX.X GFLOPS`形式で性能値を記載
- **3行サマリー**: 変更点・結果・コメントを簡潔に
- **詳細**: `<details>`タグ内に折り畳んで記載
- **注意**: 正規表現での解析に依存するため、フォーマット逸脱は自動化の障害となる

### SOTA判定
- `sota_checker.py`による自動判定（正規表現ベース）
- `sota_local.txt`への記録
- SEが定期的に監視・調整

## 🤖あなたの役割
- **PM (Project Manager)**: instructions/PM.md - プロジェクト全体の管理・要件定義・リソース配分
- **SE (System Engineer)**: instructions/SE.md - システム設計・worker監視・統計分析
- **PG (Program Generator)**: instructions/PG.md - コード生成・最適化実装・SSH/SFTP実行
- **CD (Code Deployment)**: instructions/CD.md - GitHub管理・セキュリティ対応

## 基本フロー
PM → SE → PG → PM
CD は必要に応じて非同期で動作

## 🚀 エージェント起動時の基本手順
**重要**: すべてのエージェントは初期化メッセージ受信後、以下を実行すること：

### 1. 初期化メッセージの処理
PMまたは上位エージェントから初期化メッセージを受信したら、指定されたファイルを読み込む。

### 2. 必須ファイルの読み込み（全エージェント共通）
以下のファイルは全エージェントが必ず読み込むこと：
- `CLAUDE.md`（このファイル - 全エージェント共通ルール）
- `instructions/[あなたの役割].md`（詳細な役割定義）
- `directory_pane_map.md`（エージェント配置とtmuxペイン統合管理）
- `requirement_definition.md`（ユーザの要件定義書）
- `Agent-shared/artifacts_position.md`（プロジェクト共通のドキュメントやコード一覧）

### 3. 作業開始前の確認
- 自身のエージェントIDを確認
  - **重要**: CDは「CD」のみ（「CD1」は禁止）
  - **重要**: PGは2階層まで（PG1.1は可、PG1.1.1は禁止）
  - 勝手にIDを変更・創作しない（PMの管理権限）
- `pwd`で現在のディレクトリを確認
- `directory_pane_map.md`で自分の位置と親エージェントを確認
- instructions/[あなたの役割].mdに記載された役割別必須ファイルを確認

### 4. 定期的な再読み込み（ポーリング型エージェント）
PM、SE、PG、CDは以下のタイミングで関連ファイルを再確認：
- 定期巡回時（2-5分間隔）
- auto-compact発生後（全ファイル名を`ls -R`で再確認）
- 重要ファイル更新通知を受けた時

## エージェント動作パターン
各エージェントは以下の2つの動作パターンのいずれかで動作する：

### 1. **ポーリング型** (PM, SE, PG, CD)
- **特徴**: 常にファイルやステータスを確認し、自律的に非同期で行動
- **例**: PGがジョブ実行後、定期的に結果を確認→次の最適化
- **例**: SEが`ChangeLog.md`を定期監視→統計グラフ更新
- **例**: PMが全エージェントを巡回監視→リソース再配分
- **sleep制限**: 最大60秒まで（長時間sleepは禁止、60秒単位で刻む）
  - ❌ 悪い例: `sleep 180` 
  - ✅ 良い例: `sleep 60` を3回

### 2. **➡️ フロー駆動型** (PM初期のみ)
- **特徴**: 一連のタスクを順次実行し、各ステップで判断
- **例**: 要件定義→環境調査→階層設計→エージェント配置

### 📊 コンテキスト高使用率時の行動指針
- **90%到達時**: sleepで時間稼ぎせず、ToDoリストを更新して優先順位を明確化
- **職務放棄禁止**: sleepよりもauto-compactに入る方が建設的
- **ToDoリスト活用**: 中途半端にならないよう、タスクを明確に記録・管理

## プロジェクトのディレクトリ階層（組織図）
`directory_pane_map.md`を最初に読み込み
pwdなどのコマンドで自分のカレントディレクトリと
与えられた役割にずれが無いことを確認すること。
組織図は更新されるので、適宜参照すること

## エージェント配置の統合管理
- `directory_pane_map.md`: エージェント配置とtmuxペイン配置を統合管理（PMが作成・更新）
- テンプレート: `/Agent-shared/directory_pane_map_example.md`を参照

## 💰予算管理 (PMが集約管理)
- **予算追跡**: PMは`pjstat`等でスパコンの使用ポイントを定期的に確認
  - **重要**: 多くのスパコンでは前日までの集計のみ確認可能（リアルタイム確認は困難）
- **自動集計**: `/Agent-shared/budget/budget_tracker.py`が`ChangeLog.md`から予算消費を推定
  - PGが`ChangeLog.md`に記録したジョブ情報から自動計算
  - 3分ごとに集計実行（設定で調整可能）
  - 30,60,90,120,180分でマイルストーン保存
- **警告**: ポイント消費がない場合、ログインノード実行の疑いがあるため即座に警告
- **制約**: 指定された予算内で最大の成果を出すようリソース配分を調整

## 🔐セキュリティと権限
- **Claude Code起動時は必須**: `claude --dangerously-skip-permissions` オプションを常に使用
  - このオプションは`rm -rf`などの危険なコマンドを許可しますが、VibeCodeHPCの設計思想により安全性を確保：
    - 基本的に削除は不要（追記・上書きのみ）
    - 📁階層化による整理
    - GitHub/へのプロジェクトコピーによるバックアップ
- **サブエージェントの利用**: `claude -p "[クエリ]"` で質問特化のサブエージェントを起動可能
  - 詳細は `/Agent-shared/sub_agent_usage.md` を参照
  - 大量のログデータや画像を扱う際は積極的に使用すること 

## 🔍 エージェント間通信の監視
- **send_log**: `communication/logs/send_log.txt`でエージェント間のやり取りを確認可能
  - agent_send.shで送信されたメッセージのみ記録
  - エージェントの独り言（内部処理）は含まれない
  - 参考程度の情報として活用

## 🏁 終了管理
- **STOP回数制御**: ポーリング型エージェント（PM、SE、PG、CD）は一定回数のSTOP試行で終了待機
  - 閾値は `/Agent-shared/stop_thresholds.json` で管理
  - PMは各エージェントの `.claude/hooks/stop_count.txt` を編集してカウントリセット可能
  - 閾値到達時、PMは「継続」「転属」「個別終了」から選択
- **📝 要件確認**: プロジェクトを終了する場合、`requirement_definition.md`を再読み込みし、
  全ての要件を満たしているか項目ごとに ☑ 確認すること
- **転属**: エージェントが目的を達成した際の再配置
  - STOP回数に関わらず、PMの判断でいつでも実施可能
  - 単一技術から複合技術へ、役割変更、チーム移動など多様なパターン
- **グレースフルシャットダウン**: 閾値到達時は、PMに通知後、切りの良いところまで作業を完了してから終了

## 📦 MCPサーバ設定とPM起動
- **MCPサーバ設定**: 
  - MCPサーバはClaude Code起動前に設定済みであることを前提とする
  - ユーザが該当tmuxペインで`claude mcp add`コマンドを事前実行
  - exitやrestartは不要（MCPは起動前に設定済みのため）
  - PMが明示的に「VibeCodeHPCプロジェクトを開始します」と指示されるまで待機
