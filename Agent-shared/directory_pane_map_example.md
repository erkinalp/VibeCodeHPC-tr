# VibeCodeHPC Aracı Yerleşim Haritası

## Proje hiyerarşi yapısı
```
VibeCodeHPC-GEMM📂
├── 🤖PM (Proje Yönetimi)
├── directory_pane_map.md (bu dosya - ID aracı yerine geçer)
├── GitHub📁 🤖CD ⬛
└── Akış/TypeII📂
    ├── single-node📂 🤖SE1 🟨
    │   ├── gcc11.3.0📂
    │   │   ├── OpenMP📁 🤖PG1.1 🟦
    │   │   ├── MPI📁 🤖PG1.2 🟦
    │   │   ├── AVX2📁 🤖PG1.3 🟦
    │   │   └── OpenMP_MPI📁 (2. nesil)
    │   ├── intel2024📂
    │   │   ├── OpenMP📁 🤖PG1.4 🟪
    │   │   ├── MPI📁 🤖PG1.5 🟪
    │   │   └── AVX512📁
    │   └── nvidia_hpc📂
    │       ├── CUDA📁 🤖PG1.6 🟫
    │       └── OpenACC📁
    └── multi-node📂 🤖SE2 🟡
        ├── gcc11.3.0📂
        │   ├── MPI📁 🤖PG2.1 🔵
        │   └── OpenMP📁 🤖PG2.2 🔵
        └── intel2024📂
            └── MPI📁 🤖PG2.3 🟣
```

## tmux yerleşim diyagramı (Worker sayısı: 12 iken)
Markdown’ı düz metin gösteren editörlerde de okunabilir kılmak için
aşağıdaki formata uyun ve boşluklarla hizalamayı koruyun

### tmux bölünmesi tek bir Window’a sığarsa (12/12 pane - 4x3 düzen)
| Team1 | Workers1 | | |
|:---|:---|:---|:---|
| 🟨SE1     | 🟦PG1.1   | 🟦PG1.2   | 🟦PG1.3   |
| 🟪PG1.4   | 🟪PG1.5   | 🟫PG1.6   | 🟡SE2     |
| 🔵PG2.1   | 🔵PG2.2   | 🟣PG2.3   | ⬛CD      |

### Tek bir Window yetmeyecek kadar darsa
`no space for new pane` hatası oluşursa otomatik olarak birden fazla tmux oturumu oluşturulur
Not: tmux session : tmux Window = 1 : 1

#### Team1_Workers1 (7/9 pane - 3x3 düzen)
| Team1 | Workers1 | |
|:---|:---|:---|
| 🟨SE1     | 🟦PG1.1   | 🟦PG1.2   |
| 🟦PG1.3   | 🟪PG1.4   | 🟪PG1.5   |
| 🟫PG1.6   | ⬜        | ⬜        |

#### Team1_Workers2 (5/9 pane - 3x3 düzen)
| Team1 | Workers2 | |
|:---|:---|:---|
| 🟡SE2     | 🔵PG2.1   | 🔵PG2.2   |
| 🟣PG2.3   | ⬛CD      | ⬜        |
| ⬜        | ⬜        | ⬜        |

## Renk efsanesi (öncelik sırasıyla)
### Kare emojiler (temel)
- 🟨 Sarı: SE1 (single-node izleme)
- 🟦 Mavi: gcc-tabanlı PG (SE1 altında)
- 🟪 Mor: intel-tabanlı PG (SE1 altında)
- 🟫 Kahverengi: nvidia-tabanlı PG (SE1 altında)
- ⬛ Siyah: CD (GitHub yönetimi)
- ⬜ Beyaz: Boş pane

### Daire emojiler (renk yetersizse)
- 🟡 Altın: SE2 (multi-node izleme)
- 🔵 Mavi daire: multi-node gcc-tabanlı PG (SE2 altında)
- 🟣 Mor daire: multi-node intel-tabanlı PG (SE2 altında)
- 🟤 Kahverengi daire: Ek takım için (gerektiğinde)
