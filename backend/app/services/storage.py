"""
Object storage service for S3/R2.

Handles file uploads and signed URL generation.
"""

import boto3
from botocore.exceptions import ClientError
from typing import Optional
import uuid

from app.config import get_settings


class StorageService:
    """Service for managing files in object storage (S3/R2)."""
    
    def __init__(self):
        settings = get_settings()
        
        self.bucket = settings.storage_bucket
        self.expiry_minutes = settings.signed_url_expiry_minutes
        
        # Initialize S3 client
        client_kwargs = {
            "region_name": settings.storage_region,
        }
        
        if settings.storage_endpoint_url:
            client_kwargs["endpoint_url"] = settings.storage_endpoint_url
        
        if settings.aws_access_key_id and settings.aws_secret_access_key:
            client_kwargs["aws_access_key_id"] = settings.aws_access_key_id
            client_kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
        
        self.client = boto3.client("s3", **client_kwargs)
    
    def upload_file(
        self,
        file_data: bytes,
        filename: str,
        content_type: str,
        folder: str = "uploads"
    ) -> tuple[str, str]:
        """
        Upload a file to object storage.
        
        Args:
            file_data: File contents as bytes
            filename: Original filename
            content_type: MIME type of the file
            folder: Storage folder/prefix
        
        Returns:
            Tuple of (upload_id, object_key)
        """
        upload_id = str(uuid.uuid4())
        extension = filename.rsplit(".", 1)[-1] if "." in filename else ""
        object_key = f"{folder}/{upload_id}.{extension}" if extension else f"{folder}/{upload_id}"
        
        self.client.put_object(
            Bucket=self.bucket,
            Key=object_key,
            Body=file_data,
            ContentType=content_type,
        )
        
        return upload_id, object_key
    
    def get_signed_url(self, object_key: str, expiry_minutes: Optional[int] = None) -> str:
        """
        Generate a signed URL for accessing an object.
        
        Args:
            object_key: S3 object key
            expiry_minutes: URL expiry time in minutes
        
        Returns:
            Signed URL string
        """
        expiry = expiry_minutes or self.expiry_minutes
        
        url = self.client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self.bucket,
                "Key": object_key,
            },
            ExpiresIn=expiry * 60,
        )
        
        return url
    
    def delete_file(self, object_key: str) -> bool:
        """
        Delete a file from object storage.
        
        Args:
            object_key: S3 object key
        
        Returns:
            True if deleted successfully
        """
        try:
            self.client.delete_object(
                Bucket=self.bucket,
                Key=object_key,
            )
            return True
        except ClientError:
            return False
