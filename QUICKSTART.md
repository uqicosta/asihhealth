# 🚀 Quick Start - AsihHealth YouTube Automation

Panduan cepat untuk memulai otomasi konten YouTube berbahasa Indonesia.

---

## 1. Persiapan Awal (5-10 menit)

### Install FFmpeg (WAJIB)
```powershell
winget install ffmpeg
# Verifikasi
ffmpeg -version
```

### Install Ollama (Sangat Direkomendasikan - Gratis Total)
1. Download: https://ollama.com/download
2. Install & jalankan
3. Pull model terbaik untuk Bahasa Indonesia:

```powershell
ollama pull qwen2.5:7b
# atau kalau RAM banyak:
ollama pull qwen2.5:14b
```

### (Opsional tapi sangat direkomendasikan) Dapatkan Pexels API Key (Gratis)
1. Daftar di https://www.pexels.com/api/
2. Copy API key
3. Tambahkan ke file `.env` → `PEXELS_API_KEY=xxxxxxxx`

Ini memungkinkan video dengan gambar stock berkualitas tinggi + efek Ken Burns.

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

### Opsi A: Video Cantik dengan Stock Image (Direkomendasikan)

```powershell
python pipeline/run.py --topic "Bahaya minum kopi setiap hari bagi kesehatan" --use-stock
```

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
| TTS | edge-tts (gratis + paling natural untuk ID) |
| Subtitle | faster-whisper `base` (cukup akurat) |
| Video style | Mulai dengan "simple" dulu |
| Panjang script | 8-11 menit paling optimal |

---

## 6. Streamlit Dashboard

```powershell
pip install streamlit
streamlit run dashboard/app.py
```

Dashboard memungkinkan kamu mengelola topik, generate, dan upload dari browser.

## 7. Scheduler Harian (Generate Otomatis Setiap Hari)

```powershell
# Sekali jalan (ambil 1 topik dari antrian)
python scheduler/daily.py --use-stock

# Atau jalankan dalam loop
python scheduler/daily.py --loop
```

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

---

**Selamat membuat konten!** 🎥

Butuh bantuan lebih lanjut? Buka issue di repo atau tanya di grup creator Indonesia.
