# 🚀 Quick Start - AsihHealth YouTube Automation

Panduan cepat untuk memulai otomasi konten YouTube berbahasa Indonesia.

---

## 1. Persiapan Awal (5-10 menit)

**PENTING: Python Version**

Proyek ini support **Python 3.9 atau 3.10** untuk fitur TTS lokal terbaik (XTTS).

- Python 3.11+ (termasuk 3.14 yang kamu pakai) **tidak didukung** oleh package `TTS` (Coqui XTTS).
- Kamu akan dapat error: `No matching distribution found for TTS`

**Solusi cepat di Windows:**
- Install Python 3.10 dari https://www.python.org/downloads/release/python-31011/ (atau versi 3.10 terbaru)
- Gunakan `py` launcher:
  ```powershell
  py -3.10 -m venv .venv
  .venv\Scripts\Activate.ps1
  py -3.10 -m pip install -r requirements.txt
  py -3.10 pipeline/run.py --topic "..."
  ```

Atau pakai Conda (paling mudah untuk multiple Python):
```powershell
conda create -n asih python=3.10
conda activate asih
pip install -r requirements.txt
```

### Install FFmpeg (WAJIB)
```powershell
winget install ffmpeg
# Verifikasi
ffmpeg -version
```

### Install Ollama (Opsional - Gratis Total)
Jika ingin 100% offline & gratis:

1. Download: https://ollama.com/download
2. Pull model:

```powershell
ollama pull qwen2.5:7b
```

### Menggunakan Groq (API - Cepat & Murah)

Jika tidak pakai Ollama, gunakan Groq:

1. Buat API key di https://console.groq.com/keys
2. Edit file `.env`:

```env
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_xxxxxxxxxxxx
GROQ_MODEL=llama-3.3-70b-versatile
```

Model Groq yang bagus:
- `llama-3.3-70b-versatile` (kualitas tinggi - recommended)
- `llama-3.1-8b-instant` (paling cepat & murah)

**Penting**: Jangan gunakan model Ollama (`qwen2.5:7b`) saat pakai Groq. Nama model harus sesuai Groq.

### (Opsional) Stock Images untuk Video (Pexels atau OpenAI)
- Default: Pexels (gratis) → butuh `PEXELS_API_KEY`
- Alternatif: OpenAI DALL·E untuk gambar kustom → set `ASSET_IMAGE_PROVIDER=openai` (pakai OPENAI_API_KEY yang sama)
1. Untuk Pexels: Daftar di https://www.pexels.com/api/ → copy key ke `.env`
2. Atau untuk AI images: `ASSET_IMAGE_PROVIDER=openai`

Keduanya mendukung efek Ken Burns di video.

### Rekomendasi TTS yang Lebih Reliable (edge-tts sering bermasalah)
edge-tts bagus tapi **kurang reliable** karena tergantung layanan online Microsoft.

Untuk penggunaan scheduler / daily / production, **sangat disarankan** pakai salah satu opsi berikut:

**Opsi #1 Paling Mudah: OpenAI TTS (Cloud API) — Direkomendasikan jika tidak mau ribet install**

- Tidak butuh Python khusus, tidak butuh model 2GB, tidak butuh espeak-ng.
- Kualitas narasi sangat natural.
- Biaya sangat murah (tts-1 ≈ Rp15 per 1000 karakter / ~Rp250 per video 5-7 menit).
- Setup paling cepat:

1. Daftar & buat API key di https://platform.openai.com/api-keys (gratis credit pertama kali)
2. Copy key (format `sk-...`)
3. Tambahkan ke file `.env` (copy dari `.env.example`):

```env
TTS_PROVIDER=openai
OPENAI_API_KEY=sk-proj-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
# Pilihan bagus:
OPENAI_TTS_VOICE=onyx          # male deep, cocok narasi kesehatan
# OPENAI_TTS_VOICE=nova        # female
OPENAI_TTS_MODEL=tts-1         # atau tts-1-hd untuk kualitas lebih tinggi
```

Selesai. Jalankan pipeline seperti biasa — otomatis pakai OpenAI TTS.

Script yang panjang (lebih dari ~4000 karakter) akan otomatis dipecah menjadi beberapa panggilan API dan hasil audionya digabungkan.

**Opsi #2 (Gratis Total): XTTS (paling direkomendasikan untuk kualitas & reliability di Windows jika mau full offline)**

**Syarat wajib:** Python 3.9 atau 3.10 (lihat bagian paling atas tentang Python version requirement).

1. Rekam sample suara Anda 15-30 detik (jelas, dalam Bahasa Indonesia, tanpa noise).
2. Simpan di `assets/voices/reference/narator.wav`
3. Install (pastikan pakai Python 3.10):

```powershell
py -3.10 -m pip install TTS
# Jika torch error di Windows (CPU):
py -3.10 -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
```

4. Di `.env`:

```env
TTS_PROVIDER=xtts
TTS_REFERENCE_AUDIO=assets/voices/reference/narator.wav
```

Model ~2GB akan download otomatis pertama kali.

Jika masih error, pesan error sekarang sudah sangat detail.

**Opsi #3 Super Ringan & Cepat (Gratis Total, sangat direkomendasikan untuk scheduler):**

```powershell
python scripts/download_piper_voice.py
```

Script ini akan otomatis mengunduh voice Indonesia bagus (`id_ID-news_tts-medium`) ke folder yang benar.

Setelah itu di `.env` (script akan print instruksi):

```env
TTS_PROVIDER=piper
PIPER_MODEL=assets/voices/piper/id_ID-news_tts-medium.onnx
```

Lalu jalankan pipeline seperti biasa — sekarang akan pakai local TTS secara otomatis (lebih reliable daripada edge-tts).

### Setup Python Environment
```powershell
cd asihhealth
python -m venv .venv
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
# Jika ada error 'requests' atau 'rich', pastikan sudah terinstall di atas
```

---

## 2. Generate Video Pertama (One Command)

**Penting:** Pastikan virtual environment aktif:

```powershell
.venv\Scripts\Activate.ps1
```

Lalu jalankan dari root folder project.

### Opsi A: Video Cantik dengan Stock Image (Direkomendasikan)

```powershell
python pipeline/run.py --topic "Bahaya minum kopi setiap hari bagi kesehatan" --use-stock
```

> Catatan: Script sudah include path fix sehingga `python pipeline/run.py` berjalan langsung dari root folder. Alternatif: `python -m pipeline.run --topic "..."`

### Opsi B: Cepat (hanya background gelap + teks)

```powershell
python pipeline/run.py --topic "Bahaya minum kopi setiap hari bagi kesehatan"
```

### Opsi C: Full Otomatis + Thumbnail + Upload + Playlist Otomatis

```powershell
python pipeline/run.py --topic "..." --use-stock --upload --privacy unlisted
```

### Opsi D: Dengan Voice Cloning

```powershell
python pipeline/run.py --topic "..." --use-stock --voice-clone assets/voices/reference/narator.wav
```

**Output yang akan dihasilkan:**
- `output/scripts/...json` → Script + judul + deskripsi
- `output/audio/voice_....mp3` → Narasi suara Indonesia (AndikaNeural)
- `output/videos/..._kenburns.mp4` atau `..._simple.mp4` → Video
- `output/thumbnails/...` → Thumbnail otomatis
- `output/subtitles/...srt` → Subtitle otomatis
- `output/videos/..._with_subs.mp4` → Video final dengan subtitle

---

## 3. Mode Lain yang Berguna

### Hanya Script + Voice (untuk diedit manual di CapCut/Premiere)
```powershell
python pipeline/run.py --topic "..." --only-script-voice
```

### Pakai Stock Visuals (Ken Burns)
```powershell
python pipeline/run.py --topic "..." --use-stock
```

### Paksa Simple Background (tanpa download)
```powershell
python pipeline/run.py --topic "..." --no-stock
```

### Ganti Voice (Female)
```powershell
python pipeline/run.py --topic "..." --voice id-ID-GadisNeural
```

### Pakai Model LLM yang lebih kuat
```powershell
python pipeline/run.py --topic "..." --model qwen2.5:14b
```

### Tanpa Subtitle (lebih cepat)
```powershell
python pipeline/run.py --topic "..." --no-subtitles
```

---

## 4. Daftar Voice Indonesia

```powershell
python scripts/list_voices.py
```

Rekomendasi:
- `id-ID-AndikaNeural` → Male (paling cocok untuk narasi kesehatan)
- `id-ID-GadisNeural` → Female

---

## 5. Tips Cost Efficient & Kualitas

| Hal | Rekomendasi |
|-----|-------------|
| LLM | Ollama `qwen2.5:7b` (gratis + bagus untuk ID) |
| TTS | edge-tts (default) / openai (API mudah & reliable) / piper (ringan gratis) |
| Subtitle | faster-whisper guided by generated script (lebih akurat + sesuai naskah) |
| Thumbnail | Pillow (gratis) atau OpenAI DALL·E (custom AI image via THUMBNAIL_PROVIDER) |
| Video style | Mulai dengan "simple" dulu |
| Panjang script | 8-11 menit paling optimal |

---

## 6. Streamlit Dashboard

```powershell
pip install streamlit
streamlit run dashboard/app.py
```

Dashboard memungkinkan kamu mengelola topik, generate, dan upload dari browser.

Jalankan dari root folder dengan venv aktif. Path fix sudah disertakan.

## 7. Scheduler Harian (Generate Otomatis Setiap Hari)

```powershell
# Sekali jalan (ambil 1 topik dari antrian)
python scheduler/daily.py --use-stock

# Atau jalankan dalam loop
python scheduler/daily.py --loop
```

Pastikan venv aktif dan jalankan dari root folder.

Lihat panduan Windows Task Scheduler di `scheduler/WINDOWS_TASK_SCHEDULER.md`

## 7. Langkah Setelah Video Jadi

1. **Review script** di file JSON (pastikan fakta akurat)
2. Thumbnail sudah dibuat otomatis di `output/thumbnails/`
3. **Upload** ke YouTube (bisa pakai `--upload`)
4. Tambahkan card, end screen, playlist

---

## Troubleshooting Umum

**"edge-tts not found"** → `pip install edge-tts`

**"Ollama connection refused"** → Pastikan Ollama sedang running (`ollama serve`)

**FFmpeg error** → Pastikan FFmpeg ada di PATH

**Subtitle jelek** → Coba ganti `WHISPER_MODEL=small` di `.env`

**Python version error saat install TTS / XTTS**
```
ERROR: Could not find a version that satisfies the requirement TTS
Requires-Python >=3.7.0,<3.11
```

**Penyebab:** Kamu pakai Python 3.11+ (termasuk 3.14). Package `TTS` (Coqui XTTS) belum support Python baru.

**Solusi:** Ikuti instruksi di bagian atas "PENTING: Python Version". Gunakan Python 3.10 + `py -3.10`.

**"No audio was received" / edge_tts.exceptions.NoAudioReceived**  
Ini error umum dari Microsoft Edge TTS service. Penyebab & solusi:

Karena edge-tts kurang reliable, **solusi terbaik & termudah** adalah pindah ke OpenAI TTS (cloud API):

Di `.env`:
```env
TTS_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_TTS_VOICE=onyx
```

Atau (gratis total) pindah ke local TTS:

```powershell
python scripts/download_piper_voice.py
```

Lalu set di .env:
```env
TTS_PROVIDER=piper
PIPER_MODEL=assets/voices/piper/id_ID-news_tts-medium.onnx
```

Atau gunakan XTTS dengan reference audio (harus pakai Python <= 3.10).

Jika tetap pakai edge-tts:
1. Voice tidak valid.
   - Jalankan: `python scripts/list_voices.py`
   - Di `.env`, ganti `TTS_VOICE=id-ID-GadisNeural`

2. Koneksi internet bermasalah.

3. Teks terlalu panjang.

4. Service Microsoft bermasalah → coba lagi nanti.

**Piper menghasilkan file audio 0 KB**

Penyebab paling umum di Windows: **espeak-ng belum terinstall**.

Piper membutuhkan espeak-ng untuk mengubah teks Indonesia menjadi fonem.

**Solusi cepat:**
1. Download installer espeak-ng dari: https://github.com/espeak-ng/espeak-ng/releases/latest
2. Install (pilih "Add to PATH" jika ada opsi).
3. Restart PowerShell / terminal Anda.
4. Coba generate lagi.

Jika masih bermasalah, lebih mudah pindah ke OpenAI (paling simpel) atau XTTS:
```env
TTS_PROVIDER=openai
OPENAI_API_KEY=sk-...
# atau
# TTS_PROVIDER=xtts
# TTS_REFERENCE_AUDIO=assets/voices/reference/narator.wav
```

Kode pipeline sekarang akan mendeteksi file 0KB dan memberikan pesan error yang jelas.

---

**Selamat membuat konten!** 🎥

Butuh bantuan lebih lanjut? Buka issue di repo atau tanya di grup creator Indonesia.
