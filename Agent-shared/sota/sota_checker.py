# Bu bir yorumdur.

class SotaChecker:
    """Bu, SotaChecker sınıfının doküman dizisidir."""

    def __init__(self):
        # **Başlatma işlemi**

(Alternatif olarak: **İlklendirme işlemi**)
        self.message = "Merhaba, dünya!"
        self.error_message = "Hata oluştu."

    def check_sota(self, data):
        # SOTA kontrolü gerçekleştirilecek.
        if not data:
            print(self.error_message) # **Veri yok.**
            return False
        print(self.message) # İşlem başarıyla tamamlandı.
        return True

# **Ana işlem**
if __name__ == "__main__":
    checker = SotaChecker()
    checker.check_sota("some data")
    checker.check_sota(None)

