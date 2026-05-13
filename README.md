# Agri-Flow: Yapay Zeka Destekli Envanter Yönetimi

**Agri-Flow**, düzensiz WhatsApp mesajlarını yapılandırılmış envanter verilerine dönüştüren uçtan uca bir tedarik zinciri çözümüdür. **FastAPI**, **Google Gemini** ve **Streamlit** kullanarak, depo yöneticilerinin doğal dil (Türkçe/İngilizce) ile stok güncellemesine ve bu değişiklikleri anlık olarak izlemesine olanak tanır.

---

## Öne Çıkan Özellikler

*   **Doğal Dil İşleme (NLP):** *"50 kilo mısır geldi"* veya *"20 çuval buğday sattık"* gibi karmaşık depo komutları için çift dilli (TR/EN) destek.
*   **Akıllı Birim Çıkarımı:** Birim belirtilmese bile ürüne göre en mantıklı birimi otomatik atar (örn: buğday → kg, süt → litre).
*   **Gerçek Zamanlı Dashboard:** Stok seviyelerini, değişim grafiklerini ve işlem geçmişini gösteren Streamlit tabanlı izleme paneli.
*   **WhatsApp Entegrasyonu:** Twilio aracılığıyla mobil cihazlardan anında veri girişi.
*   **Otomatik Defter Tutma:** Her işlem; zaman damgası, miktar değişimi ve ürün bazlı olarak PostgreSQL veritabanına kaydedilir.

---

## Tech Stack

| Bileşen | Teknoloji |
| :--- | :--- |
| **Dil** | Python 3.10+ |
| **Zeka (Yapay Zeka)** | Google Gemini 1.5 Flash |
| **API Framework** | FastAPI |
| **Veritabanı** | PostgreSQL + SQLAlchemy |
| **Frontend / Dashboard** | Streamlit + Jinja2 |
| **Tünelleme** | Ngrok |
| **Mesajlaşma** | Twilio WhatsApp API |

---

## Kurulum ve Başlangıç

### 1. Ön Gereksinimler
*   Python yüklü olmalıdır.
*   **Twilio** hesabı ve WhatsApp Sandbox kurulumu.
*   **Google AI Studio** API Anahtarı.
*   **Ngrok** (Sadece yerel çalıştırma için).

### 2. Yükleme
```bash
# Depoyu klonlayın
git clone [https://github.com/burak-arabacioglu/warehouse-agent.git](https://github.com/burak-arabacioglu/warehouse-agent.git)
cd warehouse-agent

# Gerekli kütüphaneleri yükleyin
pip install -r requirements.txt