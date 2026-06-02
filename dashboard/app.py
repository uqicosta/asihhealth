"""
AsihHealth - Simple Streamlit Dashboard
Untuk mengelola otomasi konten YouTube secara visual.

Jalankan dengan:
    streamlit run dashboard/app.py

Fitur:
- Lihat & kelola topik di scheduler
- Generate video dari topik tertentu
- Lihat daftar video yang sudah dibuat
- Upload manual ke YouTube
- Statistik sederhana
"""

import streamlit as st
import json
from pathlib import Path
from datetime import datetime
import subprocess
import sys

# Paths
ROOT = Path(__file__).parent.parent
TOPICS_FILE = ROOT / "scheduler" / "topics.json"
PROCESSED_FILE = ROOT / "output" / "scheduler_processed.json"
OUTPUT_VIDEOS = ROOT / "output" / "videos"
OUTPUT_SCRIPTS = ROOT / "output" / "scripts"
OUTPUT_THUMBNAILS = ROOT / "output" / "thumbnails"

st.set_page_config(page_title="AsihHealth Dashboard", page_icon="🎬", layout="wide")
st.title("🎬 AsihHealth - Dashboard Otomasi YouTube")
st.caption("Cost Efficient Content Pipeline | Bahasa Indonesia")

# Sidebar controls
st.sidebar.header("Quick Actions")

if st.sidebar.button("🔄 Refresh Data"):
    st.rerun()

# ========== TOPICS & SCHEDULER ==========
st.header("📋 Antrian Topik (Scheduler)")

col1, col2 = st.columns([2, 1])

with col1:
    if TOPICS_FILE.exists():
        topics = json.loads(TOPICS_FILE.read_text(encoding="utf-8"))
        processed = []
        if PROCESSED_FILE.exists():
            try:
                processed = json.loads(PROCESSED_FILE.read_text(encoding="utf-8"))
            except:
                pass

        for i, topic in enumerate(topics):
            topic_text = topic["topic"]
            is_done = topic_text in processed
            status = "✅ Selesai" if is_done else "⏳ Pending"
            priority = topic.get("priority", 5)

            with st.expander(f"{status} | P{priority} | {topic_text[:70]}..."):
                st.write(f"**Topik lengkap:** {topic_text}")
                if not is_done:
                    if st.button(f"🚀 Generate Sekarang", key=f"gen_{i}"):
                        with st.spinner("Menjalankan pipeline... (bisa memakan waktu 10-30 menit)"):
                            try:
                                # Call the pipeline
                                result = subprocess.run(
                                    [sys.executable, "pipeline/run.py", "--topic", topic_text, "--use-stock"],
                                    cwd=ROOT,
                                    capture_output=True,
                                    text=True,
                                    timeout=1800  # 30 minutes max
                                )
                                st.success("Pipeline selesai!")
                                st.text(result.stdout[-2000:] if result.stdout else "No output")
                                if result.returncode == 0:
                                    st.balloons()
                            except Exception as e:
                                st.error(f"Error: {e}")
                else:
                    st.info("Sudah diproses sebelumnya.")
    else:
        st.warning("topics.json tidak ditemukan.")

with col2:
    st.subheader("Tambah Topik Baru")
    new_topic = st.text_area("Topik kesehatan baru:")
    new_priority = st.slider("Priority", 1, 10, 7)

    if st.button("➕ Tambah ke Antrian"):
        if new_topic.strip():
            topics = json.loads(TOPICS_FILE.read_text(encoding="utf-8")) if TOPICS_FILE.exists() else []
            topics.append({
                "topic": new_topic.strip(),
                "priority": new_priority,
                "added": datetime.now().isoformat()
            })
            TOPICS_FILE.write_text(json.dumps(topics, ensure_ascii=False, indent=2), encoding="utf-8")
            st.success("Topik ditambahkan!")
            st.rerun()

# ========== GENERATED CONTENT ==========
st.header("🎥 Video yang Sudah Dibuat")

if OUTPUT_VIDEOS.exists():
    videos = sorted(OUTPUT_VIDEOS.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    if videos:
        cols = st.columns(3)
        for idx, video in enumerate(videos[:9]):  # show latest 9
            with cols[idx % 3]:
                st.video(str(video))
                st.caption(f"📁 {video.name}")
                # Find matching thumbnail
                thumb = list(OUTPUT_THUMBNAILS.glob(f"*{video.stem.split('_')[0]}*.png"))[:1]
                if thumb:
                    st.image(str(thumb[0]), width=200)
    else:
        st.info("Belum ada video yang di-generate.")
else:
    st.info("Folder output/videos belum ada.")

# ========== MANUAL UPLOAD ==========
st.header("📤 Manual Upload ke YouTube")

col_a, col_b = st.columns(2)

with col_a:
    video_files = list(OUTPUT_VIDEOS.glob("*.mp4")) if OUTPUT_VIDEOS.exists() else []
    if video_files:
        selected_video = st.selectbox("Pilih Video", [v.name for v in video_files])
        script_files = list(OUTPUT_SCRIPTS.glob("*.json")) if OUTPUT_SCRIPTS.exists() else []
        selected_script = st.selectbox("Pilih Script JSON", [s.name for s in script_files]) if script_files else None

        privacy = st.selectbox("Privacy", ["private", "unlisted", "public"], index=0)

        if st.button("🚀 Upload ke YouTube"):
            if selected_video and selected_script:
                script_path = OUTPUT_SCRIPTS / selected_script
                video_path = OUTPUT_VIDEOS / selected_video

                with st.spinner("Uploading..."):
                    try:
                        from core.youtube import upload_complete_from_pipeline
                        vid_id = upload_complete_from_pipeline(
                            video_path=video_path,
                            script_json_path=script_path,
                            privacy=privacy,
                            auto_playlist=True
                        )
                        if vid_id:
                            st.success(f"Upload berhasil! https://youtu.be/{vid_id}")
                        else:
                            st.error("Upload gagal.")
                    except Exception as e:
                        st.error(str(e))
    else:
        st.warning("Tidak ada video di output.")

# ========== STATS ==========
st.header("📊 Statistik Singkat")

if OUTPUT_VIDEOS.exists():
    total_videos = len(list(OUTPUT_VIDEOS.glob("*.mp4")))
    st.metric("Total Video Dibuat", total_videos)

if PROCESSED_FILE.exists():
    processed = json.loads(PROCESSED_FILE.read_text(encoding="utf-8"))
    st.metric("Topik yang Sudah Diproses", len(processed))

st.markdown("---")
st.caption("AsihHealth YouTube Automation • Cost Efficient • Bahasa Indonesia • Powered by Ollama + edge-tts + FFmpeg")
