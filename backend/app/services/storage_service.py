from io import BytesIO

from minio import Minio

from app.config.settings import settings


class StorageService:
    def __init__(self) -> None:
        self._client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )

    def upload_file(self, bucket: str, object_name: str, file_bytes: bytes) -> None:
        if not self._client.bucket_exists(bucket):
            self._client.make_bucket(bucket)

        data = BytesIO(file_bytes)
        self._client.put_object(
            bucket_name=bucket,
            object_name=object_name,
            data=data,
            length=len(file_bytes),
        )

    def download_file(self, bucket: str, object_name: str) -> bytes:
        response = self._client.get_object(bucket_name=bucket, object_name=object_name)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()


storage_service = StorageService()
