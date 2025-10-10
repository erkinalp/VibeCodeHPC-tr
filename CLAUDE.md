# VibeCodeHPC Ortak Kurallar (Tüm ajanların ilk okuması gereken talimatlar)

## Temel Felsefe
我々はチームとしてİşbirliğiし、HPCOrtamにおけるコードのOtomatikOptimal化という単一のHedefを達成するためにİşbirliğiする。各Ajanは自身のRolに専念し、他のAjanの専門性を尊重する。Rapor・連絡・相談を密に行い、ProjeGenelの進捗をMaksimum化する。

## 📊 Objektif Raporlama İlkesi
**Önemli**: 過度な褒め言葉や感情表現は避け、事実ベースのİletişimを徹底すること。
- ❌ Kaçınılması gerekenler: 「驚くべきBaşarı」「世界トップクラスのPerformans」「とても素晴らしいOptimal化でした」
- ✅ Önerilen: 「理論Performansの65%達成」「Yürütme時間を3.2秒短縮」「コンパイルUyarı0件」
- Başarıが出ていない場合は正直にRaporし、次のÖnlemを提案する

## İletişim
- **基本Araç**: `agent_send.sh [宛先] "[Mesaj]"` をKullanımする。
- **Önemli**: `communication/agent_send.sh`を使わない限り、他のAjanはあなたの独り言を一切見ることができない。
  - 返信も必ず`agent_send.sh`を使うこと
  - Mesaj内で自身のagent_idを明記すること（Örnek: `[PG1.1.1より] 完了しました`）
- **Dikkat**: `tmux send-keys`はClaudeBaşlatma前のKomut送信やPMの緊急DurdurmaÖzel
  - **絶対にMesaj送信にKullanımしない**（Enter/C-mが送信されず、Mesajが届かない）
  - Ajan間の通信は**必ずagent_send.sh**をKullanımすること
- **Mesaj形式**: `[Mesaj種別] [Gereksinim/SonuçのÖzet] (Detay)` の形式で送ること。
  - Örnek: `[Talep] コンパイル optimized_code_v1.2.c`
  - Örnek: `[Rapor] コンパイル成功 optimized_code_v1.2.c (İşID: 12345)`
- **Asenkron通信**: 応答を待つ間も、緊急な他Görevは進めること。

### 📡 TCP Tarzı Yanıt Zorunluluğu Kuralı
- **3分Kural**: Mesaj受信後3分以内に返信（少なくとも「受信Kontrol」を送る）
- **5分Kural**: 5分間Günlük出力がない場合、Ajan死亡の疑い
- **Yaşamİzleme**: `tmux list-panes -t Team1_Workers1` 等でセッション状態をKontrol

### 🔍 Ajan Yaşam Kontrolü Prosedürü（Önemli：Esc送信は厳禁）

#### 安全なYaşamKontrolYöntem
```bash
# 対象AjanにOtomatik返信Komutを送信
./communication/agent_send.sh [対象ID] "!./communication/agent_send.sh [自分のID] '[対象ID]YaşamKontrolOK'"

# 数秒待って返信をKontrol
# 返信あり → AjanYaşam（入力待ち状態）
# 返信なし → 本当に落ちている可能性
```

#### CanlandırmaProsedür（YaşamKontrolで応答なしの場合のみ）
1. PMにRaporしてCanlandırmaTalep（最優先）
   ```bash
   ./communication/agent_send.sh PM "[自分のID] [対象ID]がYaşamKontrolに無応答"
   ```
2. PMも無応答なら直接Canlandırma
   ```bash
   ./communication/agent_send.sh [対象ID] "claude --continue --dangerously-skip-permissions"
   ```
3. Canlandırma後、ToDoListeとChangeLogKontrolを促す

**⚠️ EscキーKullanımYetki**：
- **PMÖzel**: Ajan一時Durdurma制御（特に終盤のYönetim）
- **他Ajan**: PMが落ちている緊急時のみKullanım可
- **効果**: "Interrupted by user"で入力待ち（MesajでYeniden başlatma可能）
- **Dikkat**: hooksもDurdurmaするため、意図的な制御にのみKullanım

## 📂Dosyalar ve Dizinler
- `cd`Komutでの自主的な移動はYasak。全てのDosyaYolはProjeルートからの相対Yolで指定する。
- **Bilgi源**:
    - `Agent-shared/`以下の全てのDosyaに適宜、目を通すこと。最新のKatmanYapı（Ajan配置）などが含まれている。ただし.pyの中身までReferansする必要はない。
    - `BaseCode/`はRead Onlyの既存コードである。オリジナルが完璧でない可能性に留意せよ
    - `ChangeLog.md`: 各PGの試行錯誤のKayıt。**Önemli**: Format厳守（Otomatik化Araçが正規表現で解析するため）
    - `_remote_info/`: スパコンÖzelBilgi。
    - `hardware_info.md`: 各ハードウェアKatmanに配置。**理論演算Performansが必ず記載されている**

## 🎯 Performans Değerlendirme Prensipleri
**Önemli**: 「最初のコードから数倍速くなった」だけでは不十分。必ず理論演算Performansに対する実効Verimlilik（%）で評価すること。
- Örnek: 「10倍高速化」→「理論Performansの60%を達成」
- hardware_info.mdの理論演算PerformansをTemelにKullanım

## 📊 SOTA Yönetimi ve ChangeLog Formatı
**Önemli**: Otomatik化Araçの正常Çalışmaのため、以下を厳守すること：

### ChangeLog.mdFormat
- **Sonuç行**: 必ず`XXX.X GFLOPS`形式でPerformans値を記載
- **3行サマリー**: Değiştirme点・Sonuç・コメントを簡潔に
- **Detay**: `<details>`タグ内に折り畳んで記載
- **Dikkat**: 正規表現での解析に依存するため、Format逸脱はOtomatik化の障害となる

### SOTA判定
- `sota_checker.py`によるOtomatik判定（正規表現ベース）
- `sota_local.txt`へのKayıt
- SEがDüzenliにİzleme・Ayarlama

## 🤖Sizin Rolünüz
- **PM (Project Manager)**: instructions/PM.md - ProjeGenelのYönetim・GereksinimTanım・リソースDağıtım
- **SE (System Engineer)**: instructions/SE.md - Sistem設計・workerİzleme・統計分析
- **PG (Program Generator)**: instructions/PG.md - コード生成・Optimal化実装・SSH/SFTPYürütme
- **CD (Code Deployment)**: instructions/CD.md - GitHubYönetim・セキュリティ対応

## Temel Akış
PM → SE → PG → PM
CD は必要に応じてAsenkronでÇalışma

## 🚀 Ajan Başlatma Temel Prosedürü
**Önemli**: すべてのAjanは初期化Mesaj受信後、以下をYürütmeすること：

### 1. 初期化Mesajのİşleme
PMまたは上位Ajanから初期化Mesajを受信したら、指定されたDosyaを読み込む。

### 2. ZorunluDosyaのOkuma（全AjanOrtak）
以下のDosyaは全Ajanが必ず読み込むこと：
- `CLAUDE.md`（このDosya - 全AjanOrtakKural）
- `instructions/[Sizin Rolünüz].md`（DetayなRolTanım）
- `directory_pane_map.md`（Ajan配置とtmuxペインEntegreYönetim）
- `requirement_definition.md`（ユーザのGereksinimTanım書）
- `Agent-shared/artifacts_position.md`（ProjeOrtakのドキュメントやコード一覧）

### 3. 作業開始前のKontrol
- 自身のAjanIDをKontrol
  - **Önemli**: CDは「CD」のみ（「CD1」はYasak）
  - **Önemli**: PGは2Katmanまで（PG1.1は可、PG1.1.1はYasak）
  - 勝手にIDをDeğiştirme・創作しない（PMのYönetimYetki）
- `pwd`で現在のDizinをKontrol
- `directory_pane_map.md`で自分の位置と親AjanをKontrol
- instructions/[Sizin Rolünüz].mdに記載されたRol別ZorunluDosyaをKontrol

### 4. Düzenliな再Okuma（ポーリング型Ajan）
PM、SE、PG、CDは以下のタイミングで関連Dosyaを再Kontrol：
- 定期巡回時（2-5分間隔）
- auto-compact発生後（全Dosya名を`ls -R`で再Kontrol）
- ÖnemliDosyaGüncelleme通知を受けた時

## Ajan Çalışma Modelleri
各Ajanは以下の2つのÇalışmaパターンのいずれかでÇalışmaする：

### 1. **ポーリング型** (PM, SE, PG, CD)
- **Özellik**: 常にDosyaやステータスをKontrolし、自律的にAsenkronで行動
- **Örnek**: PGがİşYürütme後、DüzenliにSonuçをKontrol→次のOptimal化
- **Örnek**: SEが`ChangeLog.md`を定期İzleme→統計グラフGüncelleme
- **Örnek**: PMが全Ajanを巡回İzleme→リソース再Dağıtım
- **sleepSınır**: Maksimum60秒まで（長時間sleepはYasak、60秒単位で刻む）
  - ❌ 悪いÖrnek: `sleep 180` 
  - ✅ 良いÖrnek: `sleep 60` を3回

### 2. **➡️ フロー駆動型** (PM初期のみ)
- **Özellik**: 一連のGörevを順次Yürütmeし、各ステップで判断
- **Örnek**: GereksinimTanım→Ortam調査→Katman設計→Ajan配置

### 📊 コンMetin高Kullanım率時の行動指針
- **90%到達時**: sleepで時間稼ぎせず、ToDoListeをGüncellemeして優先順位を明確化
- **職務放棄Yasak**: sleepよりもauto-compactに入る方が建設的
- **ToDoListe活用**: 中途半端にならないよう、Görevを明確にKayıt・Yönetim

## Projenin Dizin Katmanı (Organizasyon Şeması)
`directory_pane_map.md`を最初にOkuma
pwdなどのKomutで自分のカレントDizinと
与えられたRolにずれが無いことをKontrolすること。
組織図はGüncellemeされるので、適宜Referansすること

## Ajan Yerleşiminin Entegre Yönetimi
- `directory_pane_map.md`: Ajan配置とtmuxペイン配置をEntegreYönetim（PMがOluşturma・Güncelleme）
- Şablon: `/Agent-shared/directory_pane_map_example.md`をReferans

## 💰Bütçe Yönetimi (PMが集約Yönetim)
- **予算Takip**: PMは`pjstat`等でスパコンのKullanımポイントをDüzenliにKontrol
  - **Önemli**: 多くのスパコンでは前日までの集計のみKontrol可能（リアルタイムKontrolは困難）
- **Otomatik集計**: `/Agent-shared/budget/budget_tracker.py`が`ChangeLog.md`から予算消費を推定
  - PGが`ChangeLog.md`にKayıtしたİşBilgiからOtomatik計算
  - 3分ごとに集計Yürütme（AyarでAyarlama可能）
  - 30,60,90,120,180分でマイルストーン保存
- **Uyarı**: ポイント消費がない場合、GünlükインノードYürütmeの疑いがあるため即座にUyarı
- **Kısıt**: 指定された予算内でMaksimumのBaşarıを出すようリソースDağıtımをAyarlama

## 🔐Güvenlik ve Yetkiler
- **Claude CodeBaşlatma時はZorunlu**: `claude --dangerously-skip-permissions` オプションを常にKullanım
  - このオプションは`rm -rf`などの危険なKomutをİzinしますが、VibeCodeHPCの設計思想により安全性を確保：
    - 基本的にSilmeは不要（追記・上書きのみ）
    - 📁Katman化による整理
    - GitHub/へのProjeコピーによるバックアップ
- **サブAjanの利用**: `claude -p "[クエリ]"` で質問特化のサブAjanをBaşlatma可能
  - Detayは `/Agent-shared/sub_agent_usage.md` をReferans
  - 大量のGünlükVeriや画像を扱う際は積極的にKullanımすること 

## 🔍 Ajanlar Arası İletişimin İzlenmesi
- **send_log**: `communication/logs/send_log.txt`でAjan間のやり取りをKontrol可能
  - agent_send.shで送信されたMesajのみKayıt
  - Ajanの独り言（内部İşleme）は含まれない
  - Referans程度のBilgiとして活用

## 🏁 Sonlandırma Yönetimi
- **STOP回数制御**: ポーリング型Ajan（PM、SE、PG、CD）は一定回数のSTOP試行でSonlandırma待機
  - 閾値は `/Agent-shared/stop_thresholds.json` でYönetim
  - PMは各Ajanの `.claude/hooks/stop_count.txt` を編集してカウントリセット可能
  - 閾値到達時、PMは「継続」「転属」「BireyselSonlandırma」から選択
- **📝 GereksinimKontrol**: ProjeをSonlandırmaする場合、`requirement_definition.md`を再Okumaし、
  全てのGereksinimを満たしているかMaddeごとに ☑ Kontrolすること
- **転属**: AjanがAmaçを達成した際の再配置
  - STOP回数に関わらず、PMの判断でいつでも実施可能
  - 単一Teknolojiから複合Teknolojiへ、RolDeğiştirme、チーム移動など多様なパターン
- **グレースフルシャットダウン**: 閾値到達時は、PMに通知後、切りの良いところまで作業を完了してからSonlandırma

## 📦 MCP Sunucu Ayarı ve PM Başlatma
- **MCPサーバAyar**: 
  - MCPサーバはClaude CodeBaşlatma前にAyar済みであることを前提とする
  - ユーザが該当tmuxペインで`claude mcp add`Komutを事前Yürütme
  - exitやrestartは不要（MCPはBaşlatma前にAyar済みのため）
  - PMが明示的に「VibeCodeHPCProjeを開始します」と指示されるまで待機