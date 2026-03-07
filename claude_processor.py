import anthropic
from config import ANTHROPIC_API_KEY

MODEL = "claude-sonnet-4-6"

KATEGORILER = {"iliski", "aile", "is", "arkadaslik", "genel"}


class ClaudeProcessor:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    def _mesaj_gonder(self, sistem: str, kullanici: str) -> str:
        yanit = self.client.messages.create(
            model=MODEL,
            max_tokens=512,
            system=sistem,
            messages=[{"role": "user", "content": kullanici}],
        )
        return yanit.content[0].text.strip()

    def duzenle(self, itiraf: str) -> str:
        """Yazim hatalarini duzelt, cok uzunsa 2-3 cumleye indir."""
        sistem = (
            "Sen bir metin editörsün. Kullanicinin gönderdiği itiraf metnini aynen koru, "
            "sadece yazım ve dilbilgisi hatalarını düzelt. "
            "Metin çok uzunsa 2-3 cümleye indir ama anlam bütünlüğünü koru. "
            "Emoji ekleme, üslup değiştirme, yorum yapma. "
            "Sadece düzenlenmiş metni döndür, başka hiçbir şey yazma."
        )
        return self._mesaj_gonder(sistem, itiraf)

    def kategori_belirle(self, itiraf: str) -> str:
        """Metni oku ve su 5 kategoriden birini tek kelimeyle don: iliski / aile / is / arkadaslik / genel"""
        sistem = (
            "Sana bir itiraf metni göndereceğim. "
            "Metni okuyarak şu 5 kategoriden yalnızca birine ata: "
            "iliski / aile / is / arkadaslik / genel\n"
            "Sadece tek kelimelik kategori adını döndür, başka hiçbir şey yazma."
        )
        sonuc = self._mesaj_gonder(sistem, itiraf).lower().strip()
        # Guvence: taninan bir kategori degilse 'genel' don
        if sonuc not in KATEGORILER:
            return "genel"
        return sonuc

    def caption_uret(self, itiraf: str, kategori: str) -> str:
        """2 cumle caption, son cumlede itiraf gondermege davet, 3-5 hashtag."""
        sistem = (
            "Sen bir Instagram içerik yazarısın. "
            "Sana bir itiraf metni ve kategorisi verilecek. "
            "Şu kurallara göre bir caption yaz:\n"
            "1. Tam olarak 2 cümle.\n"
            "2. İlk cümle merak uyandırsın, okuyucuyu düşündürsün.\n"
            "3. İkinci cümle takipçileri kendi itiraflarını DM'den göndermeye davet etsin.\n"
            "4. Sonuna 3-5 hashtag ekle.\n"
            "5. Çok az emoji kullan (0-2 adet).\n"
            "Sadece caption metnini döndür, başka hiçbir şey yazma."
        )
        girdi = f"Kategori: {kategori}\nİtiraf: {itiraf}"
        return self._mesaj_gonder(sistem, girdi)
