import re
from config import ANTHROPIC_API_KEY

MODEL = "claude-sonnet-4-6"
KATEGORILER = {"iliski", "aile", "is", "arkadaslik", "genel"}

CAPTION_SABLONLAR = {
    "iliski":     "Kalpler bazen en derin sirlari saklar... Senin de paylasmak istedigin bir itiraf var mi? DM'den yaz, anonim yayinlayalim. #itiraf #iliski #gizliduygular #anonimitiraf",
    "aile":       "Aile icinde yasanan bazi duygular hic dile getirilmez... Senin de icinde biriken bir sey var mi? DM'den itirafini gonder. #itiraf #aile #gizliduygular #anonimitiraf",
    "is":         "Is hayatinda kimseye soyleyemediklerin olur bazen... Senin de paylasmak istedigin bir itiraf var mi? DM'den yaz. #itiraf #isyasami #gizliduygular #anonimitiraf",
    "arkadaslik": "Arkadasliklar bazen soylenemeyecek sirlari barindiriyor... Senin de bir itirafin var mi? DM'den anonim olarak paylas. #itiraf #arkadaslik #gizliduygular #anonimitiraf",
    "genel":      "Bazı duygular yıllarca içimizde kalır, hiç söylenemez... Senin de bir itirafın var mı? DM'den yaz, anonim yayınlayalım. #itiraf #anonimitiraf #gizliduygular #sır",
}


class ClaudeProcessor:
    def __init__(self):
        self._aktif = bool(ANTHROPIC_API_KEY)
        if self._aktif:
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            except ImportError:
                print("Uyari: anthropic kutuphanesi bulunamadi, Claude devre disi.")
                self._aktif = False

    def _mesaj_gonder(self, sistem: str, kullanici: str) -> str:
        yanit = self.client.messages.create(
            model=MODEL,
            max_tokens=512,
            system=sistem,
            messages=[{"role": "user", "content": kullanici}],
        )
        return yanit.content[0].text.strip()

    def duzenle(self, itiraf: str) -> str:
        """Claude varsa yazim duzelt, yoksa metni oldugu gibi dondur."""
        if not self._aktif:
            return itiraf.strip()
        sistem = (
            "Sen bir metin editörsün. Kullanicinin gönderdiği itiraf metnini aynen koru, "
            "sadece yazım ve dilbilgisi hatalarını düzelt. "
            "Metin çok uzunsa 2-3 cümleye indir ama anlam bütünlüğünü koru. "
            "Emoji ekleme, üslup değiştirme, yorum yapma. "
            "Sadece düzenlenmiş metni döndür, başka hiçbir şey yazma."
        )
        return self._mesaj_gonder(sistem, itiraf)

    def kategori_belirle(self, itiraf: str) -> str:
        """Claude varsa kategori belirle, yoksa anahtar kelimeyle tahmin et."""
        if not self._aktif:
            return self._tahmin_kategori(itiraf)
        sistem = (
            "Sana bir itiraf metni göndereceğim. "
            "Metni okuyarak şu 5 kategoriden yalnızca birine ata: "
            "iliski / aile / is / arkadaslik / genel\n"
            "Sadece tek kelimelik kategori adını döndür, başka hiçbir şey yazma."
        )
        sonuc = self._mesaj_gonder(sistem, itiraf).lower().strip()
        return sonuc if sonuc in KATEGORILER else "genel"

    def caption_uret(self, itiraf: str, kategori: str) -> str:
        """Claude varsa caption uret, yoksa sablon kullan."""
        if not self._aktif:
            return CAPTION_SABLONLAR.get(kategori, CAPTION_SABLONLAR["genel"])
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

    @staticmethod
    def _tahmin_kategori(metin: str) -> str:
        """Basit anahtar kelime eslesme ile kategori tahmini."""
        m = metin.lower()
        if re.search(r"sevgili|seviyorum|ask|ask|iliski|erkek arkadas|kiz arkadas|evlilik|bosanma|aldatma|flort", m):
            return "iliski"
        if re.search(r"annem|babam|kardesim|aile|anne|baba|dede|babaanne|nine|evlat|cocuk", m):
            return "aile"
        if re.search(r"patron|is|sirket|ofis|calismak|maas|isten|mudir|toplanti|kariyer", m):
            return "is"
        if re.search(r"arkadas|dost|yaninda|birlikte|grubu|takim|sinif", m):
            return "arkadaslik"
        return "genel"
