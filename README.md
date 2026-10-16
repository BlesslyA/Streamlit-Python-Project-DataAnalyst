# E-Commerce Data Analysis & Streamlit Dashboard :bar_chart:

Proyek akhir analisis data pada program Fundamental Analisis Data oleh Dicoding. Proyek ini melakukan eksplorasi data komprehensif pada **E-Commerce Public Dataset** (Brazilian E-Commerce by Olist), mencakup proses Data Wrangling, Exploratory Data Analysis (EDA), Visualisasi Data, Analisis Lanjutan (RFM Analysis & Geospatial Demographics), serta penyajian dashboard interaktif berbasis Streamlit.

---

## 📌 Pertanyaan Bisnis
1. **Pertanyaan 1:** Kategori produk apa saja yang menghasilkan total revenue tertinggi dan terendah selama periode 2017 – 2018?
2. **Pertanyaan 2:** Bagaimana pengaruh status keterlambatan pengiriman terhadap rata-rata skor ulasan (*review score*) pelanggan pada tahun 2017 – 2018?

---

## 📁 Struktur Direktori
```text
submission/
├── dashboard/
│   ├── main_data.csv              # Dataset gabungan yang telah dibersihkan
│   └── dashboard.py               # Aplikasi dashboard interaktif Streamlit
├── data/
│   ├── customers_dataset.csv
│   ├── order_items_dataset.csv
│   ├── order_reviews_dataset.csv
│   ├── orders_dataset.csv
│   ├── product_category_name_translation.csv
│   └── products_dataset.csv
├── Proyek_Analisis_Data.ipynb     # Notebook Jupyter lengkap berisi analisis data dan visualisasi
├── README.md                      # Panduan menjalankan proyek
├── requirements.txt               # Daftar dependensi library
└── url.txt                        # Tautan dashboard pada Streamlit Cloud
```

---

## 🌐 Live Dashboard
Aplikasi dashboard ini telah di-deploy ke Streamlit Cloud dan dapat diakses publik melalui:
🔗 **[Streamlit Cloud Dashboard](https://ecommerce-dashboard-dicoding-gabriel.streamlit.app/)**

---

## ⚙️ Panduan Menjalankan Proyek

### 1. Prasyarat
Pastikan sistem Anda telah terinstal **Python 3.8+**.

### 2. Membuat dan Mengaktifkan Virtual Environment
Sangat disarankan menggunakan virtual environment agar dependensi terisolasi dengan rapi.

- **Windows (PowerShell):**
  ```powershell
  python -m venv venv
  .\venv\Scripts\Activate.ps1
  ```

- **Linux / macOS (Bash):**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

### 3. Menginstal Dependensi
Instal semua package yang tercantum pada berkas `requirements.txt`:
```bash
pip install -r requirements.txt
```
atau pada Windows:
```powershell
python -m pip install -r requirements.txt
```

### 4. Menjalankan Dashboard Streamlit
Jalankan salah satu perintah berikut pada terminal:
```powershell
# Rekomendasi (berjalan lancar di semua sistem operasi & Windows PowerShell):
python -m streamlit run dashboard/dashboard.py

# Atau menggunakan CLI Streamlit langsung:
streamlit run dashboard/dashboard.py
```
atau jika berada di dalam folder `dashboard`:
```powershell
cd dashboard
python -m streamlit run dashboard.py
```
Aplikasi dashboard akan otomatis terbuka pada peramban web di alamat `http://localhost:8501`.

---

## 📊 Ringkasan Temuan & Rekomendasi Bisnis
1. **Performa Kategori Produk:**
   - Kategori berpenghasilan tertinggi dipimpin oleh **health_beauty**, **watches_gifts**, dan **bed_bath_table** dengan kontribusi jutaan Brazilian Real (BRL).
   - Kategori terendah seperti **security_and_services** dan **fashion_childrens_clothes** memiliki volume dan revenue sangat kecil, perlu dievaluasi penataan katalognya.
2. **Keterlambatan Logistik & Kepuasan Pelanggan:**
   - Keterlambatan pengiriman berakibat fatal pada kepuasan pelanggan: skor ulasan anjlok dari **4.29 / 5.0 (On Time)** menjadi **2.25 / 5.0 (Late)**.
   - Lebih dari **56%** pelanggan yang mengalami pesanan terlambat langsung memberikan rating terburuk (bintang 1).
   - Diperlukan kalibrasi SLA estimasi kedatangan yang lebih realistis dan sistem kompensasi/notifikasi proaktif untuk mencegah churn.
3. **Analisis Lanjutan (RFM & Geospasial):**
   - Mayoritas pembeli (~97%) bertransaksi satu kali (*one-time buyers*), menandakan potensi besar untuk strategi program loyalitas / repeat order.
   - Sebaran pelanggan terkonsentrasi kuat di wilayah Tenggara Brazil, khususnya negara bagian **São Paulo (SP)** (>40% transaksi), **Rio de Janeiro (RJ)**, dan **Minas Gerais (MG)**.

---
**Author:** Gabriel Jel Blessly Aipassa
Dicoding Academy - Fundamental Analisis Data Project