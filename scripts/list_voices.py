"""
Quick utility: List all available Indonesian voices from edge-tts
"""
import subprocess

def main():
    try:
        result = subprocess.run(
            ["edge-tts", "--list-voices"],
            capture_output=True, text=True, check=True
        )
        print("Available voices (filtered for Indonesian):\n")
        for line in result.stdout.splitlines():
            if "id-ID" in line:
                print(line.strip())
    except FileNotFoundError:
        print("edge-tts not installed or not in PATH.")
        print("Run: pip install edge-tts")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
