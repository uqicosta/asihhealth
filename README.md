# 🎬 AsihHealth - Otomasi Konten YouTube (Cost Efficient)

Sistem otomasi pembuatan konten YouTube **berbahasa Indonesia** yang hemat biaya, menggunakan **Python + FFmpeg + LLM lokal + TTS gratis**.

Dibuat khusus untuk channel kesehatan (AsihHealth) tapi bisa digunakan untuk topik apapun.

---

## 🎯 Fitur Utama

| Fitur | Teknologi | Biaya |
|-------|-----------|-------|
| Penulisan Script | Ollama (Qwen2.5 / Llama3.1) | **Gratis** |
| Voice Narasi (ID) | edge-tts (Microsoft) | **Gratis** |
| **Stock Visuals** | Pexels API (gratis) + Ken Burns | **Gratis** |
| Video Editing | FFmpeg (zoompan + xfade) | **Gratis** |
| Auto Subtitle | faster-whisper | **Gratis** |
| Upload YouTube | YouTube Data API | Gratis (quota) |

**Total biaya per video**: **Rp0** (setelah setup awal)

---

## 🏗️ Arsitektur Pipeline (Cost Efficient)

```
Topik / Keyword
      ↓
[LLM Lokal - Ollama] → Script + Judul + Deskripsi + Tags
      ↓
[edge-tts] → Voiceover (Bahasa Indonesia natural)
      ↓
[FFmpeg] → Video Assembly (stock footage / background + audio)
      ↓
[faster-whisper] → Generate .srt
      ↓
[FFmpeg] → Burn Subtitle + Final Render (H.264 + AAC)
      ↓
[YouTube API] → Upload otomatis (opsional)
```

---

## ✅ Rekomendasi Stack (Paling Hemat 2026)

| Komponen | Rekomendasi | Alasan |
|----------|-------------|--------|
| **LLM** | Ollama + `qwen2.5:7b` atau `llama3.1:8b` | Sangat bagus untuk bahasa Indonesia, gratis total |
| **TTS** | `edge-tts` (default) atau `xtts` / `piper` (local, direkomendasikan) | edge-tts bagus tapi online (bisa unreliable). Gunakan local XTTS/Piper untuk scheduler & daily generation |
| **Video Engine** | FFmpeg (via subprocess) | Paling cepat & efisien resource |
| **Subtitle** | `faster-whisper` (model `base` atau `small`) | Akurat untuk bahasa Indonesia |
| **Visual** | Pexels (gratis) + Ken Burns (FFmpeg zoompan) | Tanpa biaya AI image/video |

Alternatif lebih murah (kalau tidak mau install Ollama):
- LLM: Groq (Llama3-70B) atau Gemini Flash (sangat murah)
- TTS: Tetap pakai edge-tts

---

## 📦 Instalasi

### 1. Prerequisites

- **Python 3.11+** (disarankan 3.12)
- **FFmpeg** (harus ada di PATH)
- **Ollama** (opsional tapi sangat direkomendasikan)

### 2. Install FFmpeg (Windows)

```powershell
# Pakai winget (paling mudah)
winget install ffmpeg

# Atau download manual dari https://ffmpeg.org/download.html
```

Verifikasi:
```powershell
ffmpeg -version
```

### 3. Install Ollama (Recommended - Gratis Total)

Download: https://ollama.com/download

```powershell
ollama pull qwen2.5:7b          # Paling recommended untuk Bahasa Indonesia
# atau
ollama pull llama3.1:8b
```

### 4. Clone & Setup Project

```powershell
git clone https://github.com/uqicosta/asihhealth.git
cd asihhealth

python -m venv .venv
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

### 5. Install Requirements

**PENTING: Python Version Requirement**

- **Supported:** Python 3.9 atau 3.10 (paling stabil untuk TTS lokal seperti XTTS)
- **Tidak didukung:** Python 3.11, 3.12, 3.13, 3.14 (termasuk yang kamu pakai sekarang)

Package `TTS` (untuk XTTS) di PyPI memiliki batasan `Requires-Python >=3.7.0,<3.11`.

**Cara fix di Windows:**
```powershell
# Install Python 3.10 dari python.org jika belum ada
py -3.10 -m venv .venv
.venv\Scripts\Activate.ps1
py -3.10 -m pip install -r requirements.txt
```

Atau pakai Conda:
```powershell
conda create -n asih python=3.10 -y
conda activate asih
pip install -r requirements.txt
```

Lihat [requirements.txt](requirements.txt) (setelah setup Python yang benar)

### TTS yang Lebih Reliable (Penting!)

Karena edge-tts kadang kurang reliable (tergantung layanan online), untuk penggunaan otomatis (scheduler) kami sarankan pindah ke local:

**Opsi Terbaik: XTTS (local)**
**Syarat wajib:** Python 3.9 atau 3.10 (baca bagian "Python Version Requirement" di atas).

- Rekam 15-30 detik suara sample.
- Simpan `assets/voices/reference/narator.wav`
- Install (dengan Python 3.10):
  ```powershell
  py -3.10 -m pip install TTS
  py -3.10 -m pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu
  ```
- Di `.env`:
  ```env
  TTS_PROVIDER=xtts
  TTS_REFERENCE_AUDIO=assets/voices/reference/narator.wav
  ```

**Opsi Super Cepat & Ringan: Piper (local) — sangat direkomendasikan**
- Jalankan helper script (paling mudah):
  ```powershell
  python scripts/download_piper_voice.py
  ```
- Script akan download voice Indonesia dan print perintah .env yang benar.

Atau manual dari https://huggingface.co/rhasspy/piper-voices/tree/main/id

Lihat QUICKSTART.md untuk detail.

### 6. Menggunakan Groq (bukan Ollama)

Jika Anda ingin pakai Groq (bukan Ollama lokal):

1. Dapatkan API key gratis di https://console.groq.com/keys
2. Tambahkan ke file `.env`:

```env
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
GROQ_MODEL=llama-3.3-70b-versatile
```

Model bagus di Groq:
- `llama-3.3-70b-versatile` → Kualitas terbaik (rekomendasi)
- `llama-3.1-8b-instant` → Sangat cepat & murah

Kemudian jalankan:

```powershell
python pipeline/run.py --topic "Bahaya minum kopi setiap hari" --use-stock
```

**Penting**: Jangan pakai model Ollama (`qwen2.5:7b`) ketika `LLM_PROVIDER=groq`. Model name harus sesuai dengan Groq.

### 6. (Sangat Direkomendasikan) Setup Pexels API Key

1. Buka https://www.pexels.com/api/ → Sign up (gratis)
2. Copy API key
3. Buat file `.env` dari `.env.example` lalu isi:

```env
PEXELS_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
USE_STOCK_VISUALS=true
```

Tanpa ini, pipeline akan fallback ke video background polos (masih bagus, tapi kurang visual).

---

## 🚀 Cara Pakai (Quick Start)

### Mode 1: Full Otomatis dengan Visual Cantik (Direkomendasikan)

Pastikan venv aktif dan Anda berada di root folder project.

```powershell
.venv\Scripts\Activate.ps1
python pipeline/run.py --topic "Bahaya minum kopi setiap hari bagi kesehatan hati" --use-stock
```

### Mode 2: Cepat (Simple Background)

```powershell
python pipeline/run.py --topic "Bahaya minum kopi setiap hari bagi kesehatan hati"
```

### Mode 3: Step by Step

```powershell
# 1. Generate script
python core/generate_script.py --topic "Manfaat puasa intermittent"

# 2. Generate voiceover
python core/generate_voice.py --script output/script.json

# 3. Buat video
python core/assemble_video.py --audio output/voice.wav --script output/script.json
```

### Mode 4: Generate + Thumbnail + Upload Sekaligus

```powershell
python pipeline/run.py --topic "..." --use-stock --upload --privacy unlisted
```

### Mode 5: Hanya Generate Script + Voice (untuk manual editing)

```powershell
python pipeline/run.py --topic "..." --only-script-voice
```

---

## 📁 Struktur Project

```
asihhealth/
├── README.md
├── requirements.txt
├── .env.example
├── config/
│   └── settings.py
├── core/
│   ├── llm.py              # Ollama / Groq / Gemini client
│   ├── tts.py              # edge-tts wrapper (Bahasa Indonesia)
│   ├── subtitles.py        # Whisper + FFmpeg burn
│   ├── video.py            # FFmpeg video assembly engine
│   └── youtube.py          # Upload automation
├── pipeline/
│   └── run.py              # Main orchestrator
├── templates/
│   └── prompts/
│       ├── health_script.txt
│       └── general_script.txt
├── assets/
│   ├── stock/              # Stock footage & images
│   └── voices/             # Cached audio
└── output/                 # Semua hasil generate
    ├── scripts/
    ├── audio/
    ├── videos/
    └── subtitles/
```

---

## 🎙️ Voice Indonesia yang Direkomendasikan

Dari `edge-tts --list-voices`:

| Voice | Gender | Kualitas | Rekomendasi |
|-------|--------|----------|-------------|
| `id-ID-AndikaNeural` | Male | Sangat Natural | **Default untuk narasi kesehatan** |
| `id-ID-GadisNeural` | Female | Sangat Natural | Alternatif bagus |
| `id-ID-ArdiNeural` | Male | Natural | - |

---

## 💰 Estimasi Biaya (Real World)

| Item | Biaya per Video (10-12 menit) |
|------|-------------------------------|
| LLM (Ollama lokal) | Rp0 |
| TTS (edge-tts) | Rp0 |
| Whisper lokal | Rp0 |
| FFmpeg | Rp0 |
| Stock footage | Rp0 |
| **Total** | **Rp0** |

Kalau pakai API (Groq/Gemini):
- ~Rp200-800 per video (tergantung panjang script)

---

## 📌 Roadmap

- [x] Script generator + prompt kesehatan ID
- [x] TTS integration (edge-tts)
- [x] FFmpeg video assembly (Ken Burns + Pexels stock)
- [x] Auto subtitle + burn-in
- [x] Thumbnail generator otomatis (Pillow)
- [x] Scheduler harian (1 video/hari)
- [x] YouTube upload automation (dengan thumbnail)
- [ ] Dashboard sederhana (Streamlit/Gradio)
- [ ] Voice cloning (opsional)

---

## 📅 Scheduler Harian (1 Video/Hari)

Jalankan otomatis setiap hari:

```powershell
# Generate 1 video dari antrian topics.json
python scheduler/daily.py --use-stock

# Mode loop (biarkan running)
python scheduler/daily.py --loop
```

Lihat panduan lengkap untuk **Windows Task Scheduler** di:
[scheduler/WINDOWS_TASK_SCHEDULER.md](scheduler/WINDOWS_TASK_SCHEDULER.md)

Topik dikelola di `scheduler/topics.json`.

## 🗣️ Voice Cloning (Opsional - Advanced)

Untuk suara yang benar-benar mirip narator manusia (bukan AI standar):

1. Rekam 10-30 detik suara yang jelas dalam Bahasa Indonesia (tanpa noise).
2. Simpan sebagai `.wav` di `assets/voices/reference/narator.wav`
3. Jalankan dengan flag:

```powershell
python pipeline/run.py --topic "..." --voice-clone assets/voices/reference/narator.wav
```

**Catatan:** Voice cloning menggunakan **Coqui XTTS-v2** (open source). Instalasi lebih berat:
```powershell
pip install TTS torch torchaudio
```

Kalau tidak diinstall, otomatis fallback ke edge-tts.

## 📤 Upload Otomatis ke YouTube

Pertama kali harus setup OAuth:
1. Google Cloud Console → Buat project
2. Enable **YouTube Data API v3**
3. Buat **OAuth 2.0 Client ID** → download `client_secrets.json`
4. Letakkan di root project

Lalu:

```powershell
python pipeline/run.py --topic "..." --upload --privacy private
```

Fitur upload sekarang sudah support:
- Upload video
- Set thumbnail otomatis
- Bahasa Indonesia
- Privacy (private/unlisted/public)
- **Auto playlist berdasarkan kategori** (Kesehatan Jantung, Nutrisi, dll) — playlist dibuat otomatis kalau belum ada

## 📊 Streamlit Dashboard

Jalankan dashboard visual:

```powershell
pip install streamlit
streamlit run dashboard/app.py
```

Fitur dashboard:
- Lihat & tambah topik scheduler
- Generate video langsung dari UI
- Preview video + thumbnail
- Manual upload ke YouTube
- Statistik sederhana

Sangat berguna untuk monitoring.

## ⚠️ Catatan Penting

1. **Konten Kesehatan** harus akurat. Selalu review script sebelum upload.
2. YouTube sangat ketat terhadap konten medis. Gunakan disclaimer.
3. Untuk scale besar, siapkan beberapa akun YouTube (kuota API terbatas).

---

## 📄 Lisensi

MIT License - Silakan digunakan untuk channel pribadi maupun komersial.

---

**Dibuat dengan ❤️ untuk creator Indonesia yang ingin scale konten tanpa biaya mahal.**
