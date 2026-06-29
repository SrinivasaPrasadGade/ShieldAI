"""
Firebase Storage service for ShieldAI.
Handles uploading temporary and permanent files to cloud storage.
"""

import uuid
from firebase_admin import storage
from models.database import get_firestore_client  # ensures firebase is initialized
from config import settings
from logging_config import get_logger

logger = get_logger("shield_ai.storage")

class StorageService:
    def __init__(self):
        # We call get_firestore_client just to ensure firebase_admin.initialize_app() has run
        get_firestore_client()
        
    def upload_file(self, file_bytes: bytes, content_type: str, folder: str = "temp") -> str:
        """
        Uploads a file to Firebase Storage and returns its storage path/URL.
        
        Args:
            file_bytes: Raw bytes of the file
            content_type: MIME type of the file
            folder: The prefix/folder to store the file in
            
        Returns:
            The GCS path/URI (e.g. gs://bucket/path/to/file)
        """
        filename = f"{folder}/{uuid.uuid4()}"
        try:
            bucket = storage.bucket(settings.FIREBASE_STORAGE_BUCKET)
            blob = bucket.blob(filename)
            blob.upload_from_string(file_bytes, content_type=content_type)
            logger.info("file_uploaded", path=filename, size=len(file_bytes))
            # Return a generic URI that the worker can parse or download
            return f"gs://{settings.FIREBASE_STORAGE_BUCKET}/{filename}"
        except Exception as e:
            logger.error("file_upload_failed", error=str(e), filename=filename)
            raise

    def download_file(self, uri: str) -> bytes:
        """
        Downloads a file from Firebase Storage given its gs:// URI.
        """
        try:
            if not uri.startswith("gs://"):
                raise ValueError("Invalid URI format, expected gs://...")
            
            # Parse bucket and path
            path_parts = uri.replace("gs://", "").split("/", 1)
            if len(path_parts) < 2 or not path_parts[1]:
                raise ValueError(f"Invalid GCS URI format: {uri}. Expected gs://bucket/path")
            bucket_name = path_parts[0]
            blob_path = path_parts[1]
            
            bucket = storage.bucket(bucket_name)
            blob = bucket.blob(blob_path)
            file_bytes = blob.download_as_string()
            logger.info("file_downloaded", path=uri, size=len(file_bytes))
            return file_bytes
        except Exception as e:
            logger.error("file_download_failed", error=str(e), uri=uri)
            raise

_storage_service: StorageService | None = None

def get_storage_service() -> StorageService:
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
