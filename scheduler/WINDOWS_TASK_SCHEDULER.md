# Cara Menjalankan Scheduler Harian di Windows (Task Scheduler)

Karena kamu pakai Windows, cara paling reliable untuk "1 video per hari" adalah menggunakan **Windows Task Scheduler**.

## Langkah-langkah Setup

### 1. Buat Virtual Environment Aktif (penting)

Buat file batch sederhana di root project:

**`run_daily.bat`** (buat file baru):

```batch
@echo off
cd /d "D:\github-uqicosta\asihhealth"
call .venv\Scripts\activate.bat
python scheduler\daily.py --use-stock
pause
```

### 2. Buka Task Scheduler

1. Tekan `Win + S`, ketik **Task Scheduler**, buka.
2. Klik **Create Basic Task** di kanan.
3. **Name**: `AsihHealth Daily Video`
4. **Description**: Generate 1 video kesehatan otomatis setiap hari
5. **Trigger**: Daily → Next
6. **Daily**: Atur jam (misal 09:00 pagi) → Next
7. **Action**: Start a program
   - Program/script: `D:\github-uqicosta\asihhealth\run_daily.bat`
8. Centang **Open the Properties dialog for this task when I click Finish**
9. Finish

### 3. Pengaturan Lanjutan (Penting)

Di tab yang terbuka:

- **General** tab:
  - Centang **Run whether user is logged on or not**
  - Centang **Do not store password** (kalau tidak mau input password)
  
- **Settings** tab:
  - Centang **Allow task to be run on demand**
  - Centang **If the running task does not end when requested, force it to stop**

- **Actions** tab → Edit:
  - Pastikan "Start in" diisi: `D:\github-uqicosta\asihhealth`

### 4. Test

Klik kanan task → **Run**

Cek apakah video muncul di `output/videos/`

### Tips

- Untuk melihat log, jalankan manual dulu dengan `python scheduler\daily.py`
- **Sangat penting untuk reliability**: Jangan pakai edge-tts untuk daily automation. Set `TTS_PROVIDER=xtts` atau `piper` + reference di `.env` (lihat QUICKSTART.md)
- Topik diambil dari `scheduler/topics.json` (prioritas tinggi duluan)
- Topik yang sudah diproses disimpan di `output/scheduler_processed.json`
- Kalau ingin reset: hapus file `scheduler_processed.json`

## Alternatif: Biarkan Script Running (Mode Loop)

Jika tidak mau pakai Task Scheduler:

```powershell
python scheduler\daily.py --loop
```

Script akan generate setiap 24 jam (bisa diubah).

Jalankan di background pakai `nohup` atau biarkan PowerShell terbuka.
