# Evrimsel Flat Directory Stratejisi

## Mevcut Yukarıdan Aşağıya 📁 Hiyerarşisinin Sorunları
- [x] Dizin hiyerarşi ağacı benzersiz olarak belirlenemiyor (paralelleştirme modülü adı / derleyici adı gibi üst-alt sırası)
- [x] SIMD uygulaması gibi öğeler derin hiyerarşide dağılarak anlaşılması zorlaşıyor
- /MPI/gcc/SIMD (AVX2)
- /MPI/intel/SIMD (AVX512)
- /openMP/SIMD
- /hybrid_MPI_openMP/SIMD

...Öte yandan 📁 hiç kullanmadan yalnızca yürütülebilir dosyaları artırırsak
İş betiği ve makefile değişiklikleri gerekir ve sürüm yönetimi zahmetli olur


## Flat Directory
Bu paradigma, fiziksel hiyerarşi yapısına bağlı kalmadan, CLI aracısının tamamen otomatik olarak
projenin "bağımlılık ilişkileri" ve "başvuru kapsamını" mantıksal olarak yönetebilme yeteneğini maksimum düzeyde kullanır

📁 Aslında dosya hiyerarşisi ağaç yapısı kısıtlamasına tabi değildir

### Somut Örnek
Örneğin, derin hiyerarşi hiç kullanmadan, aşağıdaki gibi başvuru izni vererek hiyerarşi ilişkisini ifade edebiliriz
```
Kök📂
　　　├📁A 　(talimat.md "Yalnızca A'ya başvuru izni")
　　　├📁B 　(talimat.md "Yalnızca B'ye başvuru izni")
　　　└📁A+B (talimat.md "Yalnızca A ve B'ye başvuru izni")
```
Özellikle aşağıdaki gibi paralel dağıtık (hızlandırma) yaklaşımlarına uygulanır
#### Tipik HPC Kodu
```
📁MPI
📁OpenMP
📁OpenMP_MPI
```
#### LLM Dağıtık Paralel Stratejisi
```
📁PP
📁TP
📁PP_TP
```
gibi etkilidir
Her modülün yazım sırası aşağıdaki kurallarla birleştirilir

### Klasör Adını Benzersiz Belirleme İçin Adlandırma Kuralları
```
◎  OpenACC_CUDA (önce OpenACC'yi for döngüsüne uygula → sonra geri kalanını CUDA ile)
✖  CUDA_OpenACC

◎  MPI_AVX2 (global→lokal ※çok çekirdek→tek çekirdek)
✖  AVX2_MPI

◎  PP_TP_EP (Pipeline dikey paralel→Tensor yatay paralel→FFN katmanı sınırlı Expert paralel)
```
Doğal uygulama (inceleme) sırasına göre farklı paralel (hızlandırma) stratejilerini _ ile ayır
Ek bilgiler MPI-opt1 gibi - ile yazılır. Sürüm varsayılan ise atlanır

### Flat Directory Kullanmamanın Dezavantajları
durum 1
```
Kök📂
　　　├📂A 
　　　│　　└📁/B 
　　　└📁B 　
```
durum 2
```
Kök📂
　　　├📁A 
　　　└📂B 
　　　   　　└📁/A 
```
2 farklı desen mevcut ve görünürlük kötüleşir
A + B + C gibi kombinasyonlar üstel olarak arttığında
- /MPI/OpenMP/SIMD
- /OpenMP/SIMD/MPI
gibi farklı aracıların derin hiyerarşide aynı uygulamayı yapma olasılığı artar



## Evrimsel Aramaya Uygun Aşağıdan Yukarıya 📁 Hiyerarşi Tasarımı

1. İlk olarak basit öğeleri (tekil teknoloji) ayrı ayrı optimize et,
2. Bunlar arasında **umut vadeden olanları "çaprazlayarak"** yeni nesiller üret

Verimli arama yaklaşımı. ※Süper bilgisayarlar arası Auto-Tuning'de de etkili

Kök📂 yalnızca donanımı belirtir
Örnek: /Flow/TypeII/single-node📂
※Doğrudan altındaki hardware_info.md'de bant genişliği ve önbellek dahil ayrıntılı özellikleri topla

Kök📂 altına ara katman yazılımını belirten katman eklenmesi önerilir
※ Ayrıca bunun altına bant genişliği vb. kıyaslama

Örnek:
```
/Flow/TypeII/single-node📂
                        /gcc11.3.0📂
                        /intel2022.3📂
```

### Adlandırma Kuralları
Birden fazla varsa, module load sırasına göre soldan sağa yaz
Örnek:
- /go1.24.4/opencode0.0.55📂
- /singularity4.1.2/konteyner_adı📂

Aşağıda yalnızca /Flow/TypeII/single-node/gcc11.3.0📂 altındaki katmanla sınırlı açıklama
### 【1. Nesil: Tohum Dönemi 🌱】
Her temel teknolojiyi, kullanılan paralel modül tek başına keşfet
```
/AVX2📁🤖
/CUDA📁🤖
/MPI📁🤖
/OpenMP📁🤖
```

### 【2. Nesil: Çaprazlama Dönemi 🌿】
1. neslin umut veren sonuçlarını "füzyon" et veya tekil teknolojiyi daha da "derinleştir"
```
/AVX2📁
/CUDA📁
/CUDA-shardMem📁🤖 (derinleştirme)
/MPI📁🤖
/OpenMP📁
/OpenMP_AVX2📁🤖 (füzyon)
/OpenMP_MPI📁🤖 (füzyon)
```

### 【3. Nesil: Islah Dönemi 🌳】
2. nesilde doğan en iyi başyapıta, daha başka umut veren teknolojileri birleştirerek nihai türü üret
```
/AVX2📁
/CUDA📁
/CUDA-shardMem📁
/MPI📁
/MPI_CUDA-shardMem📁🤖(füzyon)
/OpenMP📁
/OpenMP_CUDA📁🤖(füzyon)
/OpenMP_AVX2📁
/OpenMP_MPI📁
/OpenMP_MPI_AVX2📁🤖(füzyon)
```

※Bu evrimsel Flat📁 altında maksimum 1 worker🤖 çalışabilir,
ve bu 📁'de worker kaç katman olursa olsun özgürce dizin oluşturabilir

