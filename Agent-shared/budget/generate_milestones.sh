# Bu, dönüm noktaları oluşturan bir betiktir.

# Kullanıcıya adını sormak
read -p "Adınızı giriniz:" USER_NAME

# Selamlama mesajını göster
echo "Merhaba, ${USER_NAME}!"

# Kilometre taşı sayısını sormak
read -p "Oluşturulacak kilometre taşı sayısını girin:" MILESTONE_COUNT

# Dönüm noktası oluştur
for (( i=1; i<=$MILESTONE_COUNT; i++ ))
do
echo "Kilometre taşı ${i}: Projenin ${i}. fazı tamamlandı."
done

# Tamamlama mesajı
echo "Tüm kilometre taşları oluşturuldu."

# Hata mesajı örnekleri
# Hata: Geçersiz giriş.
# Uyarı: İşlem kesildi.

