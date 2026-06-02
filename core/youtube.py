"""
AsihHealth - YouTube Upload Automation
Uses official YouTube Data API v3.

Setup required:
1. Create project di Google Cloud Console
2. Enable YouTube Data API v3
3. Create OAuth 2.0 Client ID → download client_secrets.json
4. First run will open browser for authentication
"""

import logging
from pathlib import Path
from typing import Optional, List
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle

import json
from config.settings import YOUTUBE_CLIENT_SECRETS, YOUTUBE_CREDENTIALS

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",  # needed for thumbnails + playlists
]


def get_authenticated_service():
    """Get authenticated YouTube API service."""
    creds = None
    token_path = Path(YOUTUBE_CREDENTIALS)
    secrets_path = Path(YOUTUBE_CLIENT_SECRETS)

    if token_path.exists():
        with open(token_path, "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not secrets_path.exists():
                raise FileNotFoundError(
                    f"client_secrets.json not found at {secrets_path}. "
                    "Download from Google Cloud Console."
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(secrets_path), SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_path, "wb") as token:
            pickle.dump(creds, token)

    return build("youtube", "v3", credentials=creds)


def upload_video(
    video_path: Path,
    title: str,
    description: str,
    tags: List[str],
    category_id: str = "27",  # Education
    privacy_status: str = "private",  # private | unlisted | public
) -> Optional[str]:
    """
    Upload video to YouTube.
    Returns video ID if successful.
    """
    try:
        youtube = get_authenticated_service()

        body = {
            "snippet": {
                "title": title[:100],  # YouTube limit
                "description": description[:5000],
                "tags": tags[:30],
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": False,
            },
        }

        media = MediaFileUpload(
            str(video_path),
            mimetype="video/mp4",
            chunksize=-1,
            resumable=True
        )

        logger.info(f"Uploading video: {title}")
        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                logger.info(f"Upload progress: {int(status.progress() * 100)}%")

        video_id = response["id"]
        logger.info(f"Upload successful! Video ID: {video_id}")
        logger.info(f"URL: https://youtu.be/{video_id}")
        return video_id

    except Exception as e:
        logger.exception("YouTube upload failed")
        return None


def upload_from_script_json(
    script_json_path: Path,
    video_path: Path,
    privacy: str = "private"
) -> Optional[str]:
    """Convenience wrapper: load metadata from our script JSON + upload."""
    data = json.loads(script_json_path.read_text(encoding="utf-8"))

    return upload_video(
        video_path=video_path,
        title=data["title"],
        description=data["description"],
        tags=data.get("tags", []),
        privacy_status=privacy,
    )


def upload_thumbnail(video_id: str, thumbnail_path: Path) -> bool:
    """Upload custom thumbnail for an existing video."""
    if not thumbnail_path.exists():
        logger.error(f"Thumbnail not found: {thumbnail_path}")
        return False

    try:
        youtube = get_authenticated_service()
        media = MediaFileUpload(str(thumbnail_path), mimetype="image/png")

        youtube.thumbnails().set(
            videoId=video_id,
            media_body=media
        ).execute()

        logger.info(f"Thumbnail uploaded for video {video_id}")
        return True
    except Exception as e:
        logger.exception(f"Failed to upload thumbnail: {e}")
        return False


def upload_video_with_thumbnail(
    video_path: Path,
    title: str,
    description: str,
    tags: List[str],
    thumbnail_path: Optional[Path] = None,
    category_id: str = "27",  # Education
    privacy_status: str = "private",
    default_language: str = "id",
) -> Optional[str]:
    """
    Full upload: video + metadata (in Indonesian) + optional thumbnail.
    """
    video_id = upload_video(
        video_path=video_path,
        title=title,
        description=description,
        tags=tags,
        category_id=category_id,
        privacy_status=privacy_status,
    )

    if video_id and thumbnail_path:
        upload_thumbnail(video_id, thumbnail_path)

    return video_id


def add_to_playlist(video_id: str, playlist_id: str) -> bool:
    """Add a video to an existing playlist."""
    try:
        youtube = get_authenticated_service()
        youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": video_id,
                    },
                }
            },
        ).execute()
        logger.info(f"Video {video_id} added to playlist {playlist_id}")
        return True
    except Exception as e:
        logger.exception(f"Failed to add to playlist: {e}")
        return False


# Mapping kategori ke nama playlist yang rapi
CATEGORY_PLAYLIST_MAP = {
    "Kesehatan Jantung": "AsihHealth | Kesehatan Jantung & Kardiovaskular",
    "Nutrisi & Vitamin": "AsihHealth | Nutrisi, Vitamin & Suplemen",
    "Penyakit Kronik": "AsihHealth | Penyakit Kronik (Diabetes, Kolesterol, dll)",
    "Kesehatan Mental & Tidur": "AsihHealth | Kesehatan Mental, Stres & Tidur",
    "Pencegahan & Gaya Hidup": "AsihHealth | Pencegahan & Gaya Hidup Sehat",
    "Kesehatan Pencernaan": "AsihHealth | Kesehatan Pencernaan",
    "Kesehatan Otak": "AsihHealth | Kesehatan Otak & Saraf",
    "Imunitas & Penyakit Menular": "AsihHealth | Imunitas & Penyakit Menular",
    "Kesehatan Umum": "AsihHealth | Kesehatan Umum & Tips Harian",
}


def get_or_create_playlist(category: str, description: str = "") -> Optional[str]:
    """
    Cari playlist berdasarkan kategori. Kalau belum ada, buat baru.
    Return playlist ID.
    """
    playlist_title = CATEGORY_PLAYLIST_MAP.get(category, f"AsihHealth | {category}")

    try:
        youtube = get_authenticated_service()

        # Cari playlist yang sudah ada milik channel
        playlists = youtube.playlists().list(
            part="snippet",
            mine=True,
            maxResults=50
        ).execute()

        for item in playlists.get("items", []):
            if item["snippet"]["title"] == playlist_title:
                logger.info(f"Playlist ditemukan: {playlist_title}")
                return item["id"]

        # Buat playlist baru
        body = {
            "snippet": {
                "title": playlist_title,
                "description": description or f"Playlist otomatis untuk konten {category} - AsihHealth",
            },
            "status": {
                "privacyStatus": "public"  # atau "unlisted"
            }
        }

        response = youtube.playlists().insert(
            part="snippet,status",
            body=body
        ).execute()

        playlist_id = response["id"]
        logger.info(f"Playlist baru dibuat: {playlist_title} (ID: {playlist_id})")
        return playlist_id

    except Exception as e:
        logger.exception(f"Gagal membuat/mencari playlist untuk kategori {category}: {e}")
        return None


def upload_with_auto_playlist(
    video_path: Path,
    script_json_path: Path,
    thumbnail_path: Optional[Path] = None,
    privacy: str = "private",
) -> Optional[str]:
    """
    Upload + otomatis masukkan ke playlist berdasarkan kategori di script.
    """
    data = json.loads(script_json_path.read_text(encoding="utf-8"))
    category = data.get("category", "Kesehatan Umum")

    video_id = upload_video_with_thumbnail(
        video_path=video_path,
        title=data["title"],
        description=data["description"],
        tags=data.get("tags", []),
        thumbnail_path=thumbnail_path,
        privacy_status=privacy,
    )

    if video_id:
        playlist_id = get_or_create_playlist(category)
        if playlist_id:
            add_to_playlist(video_id, playlist_id)

    return video_id


def upload_complete_from_pipeline(
    video_path: Path,
    script_json_path: Path,
    thumbnail_path: Optional[Path] = None,
    privacy: str = "private",
    playlist_id: Optional[str] = None,
    auto_playlist: bool = True,
) -> Optional[str]:
    """
    Best integration point from the main pipeline.
    Uploads video + thumbnail + otomatis masukkan ke playlist berdasarkan kategori.
    """
    data = json.loads(script_json_path.read_text(encoding="utf-8"))

    if auto_playlist:
        return upload_with_auto_playlist(
            video_path=video_path,
            script_json_path=script_json_path,
            thumbnail_path=thumbnail_path,
            privacy=privacy,
        )

    video_id = upload_video_with_thumbnail(
        video_path=video_path,
        title=data["title"],
        description=data["description"],
        tags=data.get("tags", []),
        thumbnail_path=thumbnail_path,
        privacy_status=privacy,
    )

    if video_id and playlist_id:
        add_to_playlist(video_id, playlist_id)

    return video_id

