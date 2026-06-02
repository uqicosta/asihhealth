"""
Quick utility: List all available Indonesian voices from edge-tts

Jalankan:
    python scripts/list_voices.py

Lalu copy salah satu voice ke file .env kamu:
    TTS_VOICE=id-ID-AndikaNeural
"""
import subprocess

def main():
    print("Mencari voice Bahasa Indonesia yang tersedia via edge-tts...\n")
    try:
        result = subprocess.run(
            ["edge-tts", "--list-voices"],
            capture_output=True, text=True, check=True
        )
        id_voices = []
        for line in result.stdout.splitlines():
            if "id-ID" in line:
                id_voices.append(line.strip())

        if id_voices:
            print("Voice Indonesia yang tersedia:\n")
            for v in id_voices:
                print("  " + v)
            print("\nRekomendasi untuk konten kesehatan:")
            print("  - id-ID-AndikaNeural  (male, paling direkomendasikan untuk narasi)")
            print("  - id-ID-GadisNeural   (female)")
            print("\nCara pakai:")
            print("  Edit file .env → TTS_VOICE=id-ID-AndikaNeural")
            print("  Atau jalankan pipeline dengan: --voice id-ID-GadisNeural")
        else:
            print("Tidak menemukan voice id-ID. Mungkin edge-tts belum update atau masalah jaringan.")
    except FileNotFoundError:
        print("edge-tts tidak ditemukan.")
        print("Install dengan: pip install edge-tts")
    except Exception as e:
        print(f"Error: {e}")
        print("\nPastikan kamu punya koneksi internet, karena edge-tts mengambil daftar voice dari Microsoft.")


if __name__ == "__main__":
    main()
