# Tipik YBH Kodu Optimizasyon Stratejisi

## 1. Katman: Ortam Kurulum Dizini
- module list, makefile ve shell script'i okuyan LLM otomatik olarak 📂 oluşturur
- "Nasıl ortam kurulur, derlenir ve yürütülür" ana yapısını tanımlar

## 2. Katman: Strateji Dizini
- CUDA-MPI-OMP-{SIMD}-derleyici optimizasyon seviyesi gibi modül seviyesinde iş bölümü
- ※Algoritma seviyesi hızlandırma uygulaması: nonBlock, transpoz, döngü açma... vb. her PG'ye bırakılır

İlk dizin yapısı örneği

Ortam kurulum📁 altına yerleştir

### Gereksinim Tanımı Örneği
Kullanıcıyla soru-cevap sonucu, aşağıdaki belirtimlerin olduğu durumu düşünelim
- Furo TypeII kullanımı
- AutoTuningPlanner hariç aracı sayısı: 12
- single-node paralelleştirmesi yaklaşık %70 tamamlandığında multi-node'a geç
- singularity kullanılmıyor


🤖 Aktif aracının varlığını gösterir

Aşağıdaki gibi Agent kaynaklarını uygun şekilde tahsis ederek verimli optimizasyon yapılır

### Gösterim
- 🤖🥇(PM) Projede 1 adet
- 🤖🥈(SE1) 1 adet~birden fazla: Donanım bazında yerleştir
- 🤖(PG1.1) SE altında veya ortam bazlı dizine yerleştir: Strateji bazında ata
- 🤖(CD) Projede maksimum 1 adet
Kapalı📁 altındaki aracının özgürce klasör oluşturabileceğini gösterir.
Diğerleri açık📂 ile yazılır


### Başlatma Sonrası
```
VibeCodeHPC📂
├── CLAUDE.md📄 (ortak talimatlar)
├── assign_history.txt📄 (aracı atama kaydı)
├── 🤖🥇(PM)
├── GitHub📁🤖(CD)
└── Flow/TypeII📂
    └── single-node📂
        ├── 🤖🥈(SE1)
        ├── intel2024📂
        │   ├── AVX512📁🤖(PG1.1)
        │   ├── MPI📁🤖(PG1.2)
        │   └── OpenMP📁🤖(PG1.3)
        ├── gcc11.3.0📂
        │   ├── AVX2📁🤖(PG1.4)
        │   ├── OpenMP📁🤖(PG1.5)
        │   ├── MPI📁🤖(PG1.6)
        │   └── CUDA📁🤖(PG1.7)
        └── hpc_sdk23.1📂
            └── OpenACC📁🤖(PG1.8)
    └── multi-node📂
```


### Belirli Süre Sonra
```
VibeCodeHPC📂
├── CLAUDE.md📄 (ortak talimatlar)
├── assign_history.txt📄 (aracı atama kaydı)
├── 🤖🥇(PM)
├── GitHub📁🤖(CD)
└── Flow/TypeII📂
    └── single-node📂
        ├── 🤖🥈(SE1)
        ├── intel2024📂
        │   ├── AVX512📁🤖(PG1.1)
        │   ├── MPI📁🤖(PG1.2)
        │   ├── OpenMP📁
        │   └── OpenMP-MPI📁🤖(PG1.3)
        ├── gcc11.3.0📂
        │   ├── AVX2📁
        │   ├── OpenMP📁
        │   ├── OpenMP-MPI📁🤖(PG1.4)
        │   ├── OpenMP-MPI-AVX2📁🤖(PG1.5)
        │   ├── MPI📁
        │   └── CUDA📁🤖(PG1.6)
        └── hpc_sdk23.1📂
            └── OpenACC📁🤖(PG1.7)
    └── multi-node📂

 Atanmamış PG1.2.3 🤖
```


### Daha Fazla Süre Sonra
```
VibeCodeHPC📂
├── CLAUDE.md📄 (ortak talimatlar)
├── assign_history.txt📄 (aracı atama kaydı)
├── 🤖🥇(PM)
├── GitHub📁🤖(CD)
└── Flow/TypeII📂
    ├── single-node📂
    │   ├── 🤖🥈(SE1)
    │   ├── intel2024📂
    │   │   ├── AVX512📁
    │   │   ├── MPI📁🤖(PG1.1)
    │   │   ├── OpenMP📁
    │   │   ├── OpenMP-MPI📁🤖(PG1.2)
    │   │   └── OpenMP-MPI-AVX512📁🤖(PG1.3)
    │   ├── gcc11.3.0📂
    │   │   ├── AVX2📁
    │   │   ├── OpenMP📁
    │   │   ├── OpenMP-MPI📁🤖(PG1.4)
    │   │   ├── OpenMP-MPI-AVX2📁🤖(PG1.5)
    │   │   ├── MPI📁 
    │   │   └── OpenMP-CUDA📁🤖(PG1.2.4)
    │   └── hpc_sdk23.1📂
    │       └── OpenACC📁
    └── multi-node📂
        ├── 🤖🥈(SE2)
        └── gcc11.3.0📂
            ├── MPI📁🤖(PG2.1)     <-- Eski PG1.6 yeniden yerleştirildi
            └── OpenACC📁🤖(PG2.2) <-- Eski PG1.7 yeniden yerleştirildi
```

### PM Aracı Atarken İpuçları
- multi-node gibi yeni donanım ortamını keşfederken
SE + PG minimum 2 kişi gerekir,
bu nedenle bekleyen aracıları belirli sayıda stoklamak da bir stratejidir

- Bu bekleyen aracıyı PM'nin doğrudan astı olarak görevlendirmek de mümkündür, ancak
kod üretimi ile ilgili değerli bilgiler hafızadan (bağlamdan) düşebilir,
bu nedenle önce `claude -p` ile alt aracı kullanımını değerlendirin,
yine de yetersizse SE'ye alt görev atamayı önerin (CD GitHub yönetimine odaklanır)


### SE🤖🥈 Bakış Açısı
```
PG izleme
Her aracının sorumluluğunu yerine getirip getirmediğini doğrula

☑ Başvuru kapsamı ayarı 📁OpenMP_MPI🤖PG için
              aynı katmandaki 📁MPI, 📁OpenMP'ye yalnızca başvuru izni verilmiş mi
              farklı katman örneği: gcc📂 ve intel📂 farklı (başka SE'nin yetki alanı) ama MPI📁 var, izin ver
☑ PG'nin cevabı doğrudan çıkaran hile kod üretip üretmediği
☑ Yararlı test kodunun paylaşımı
☑ PG'nin uygun şekilde module load ve make yapıp yapmadığı
☑ ChangeLog.md'ye kaydın uygun şekilde yapılıp yapılmadığı
```

