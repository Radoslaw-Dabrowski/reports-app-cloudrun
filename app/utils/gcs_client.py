"""
Google Cloud Storage client utilities for Cloud Run.
Used as cache for S3 data to reduce egress costs.
"""
import logging
from typing import Optional
import pandas as pd
from io import StringIO

logger = logging.getLogger(__name__)

# Optional import - if not available, GCS features will be disabled
try:
    from google.cloud import storage
    from google.cloud.exceptions import GoogleCloudError
    GCS_AVAILABLE = True
except ImportError:
    logger.warning("google-cloud-storage not available. GCS features will be disabled.")
    GCS_AVAILABLE = False
    storage = None
    GoogleCloudError = Exception


class GCSManager:
    """
    Google Cloud Storage Manager with lazy initialization.
    Used as cache layer for S3 data.
    """

    def __init__(self, bucket_name: str, project_id: Optional[str] = None):
        self.bucket_name = bucket_name
        self.project_id = project_id
        self._storage_client = None
        self._bucket = None

    @property
    def storage_client(self):
        """Lazy initialization of GCS client"""
        if not GCS_AVAILABLE:
            raise ImportError("google-cloud-storage is not installed. Install it with: pip install google-cloud-storage")
        if self._storage_client is None:
            logger.info("Initializing GCS client")
            if self.project_id:
                self._storage_client = storage.Client(project=self.project_id)
            else:
                self._storage_client = storage.Client()
        return self._storage_client

    @property
    def bucket(self):
        """Get bucket object"""
        if self._bucket is None:
            self._bucket = self.storage_client.bucket(self.bucket_name)
        return self._bucket

    def read_csv(self, filename: str) -> pd.DataFrame:
        """
        Read CSV file from GCS.

        Args:
            filename: Name of the CSV file in GCS

        Returns:
            DataFrame with CSV contents
        """
        try:
            logger.info(f"[GCS] Reading {filename} from bucket {self.bucket_name}")
            blob = self.bucket.blob(filename)
            
            if not blob.exists():
                logger.warning(f"{filename} does not exist in GCS bucket {self.bucket_name}")
                return pd.DataFrame()
            
            content = blob.download_as_text()
            
            if not content.strip():
                logger.warning(f"{filename} is empty")
                return pd.DataFrame()

            df = pd.read_csv(StringIO(content), quotechar='"')
            logger.info(f"Successfully read {len(df)} rows and {len(df.columns)} columns from {filename}")
            if len(df) > 0:
                logger.debug(f"Columns in {filename}: {df.columns.tolist()[:10]}")
            return df

        except GoogleCloudError as e:
            logger.error(f"GCS error reading {filename}: {e}")
            return pd.DataFrame()

        except pd.errors.EmptyDataError:
            logger.error(f"{filename} is empty or has no columns to parse")
            return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error reading {filename} from GCS: {e}", exc_info=True)
            return pd.DataFrame()

    def write_csv(self, df: pd.DataFrame, filename: str) -> bool:
        """
        Write DataFrame to GCS as CSV.

        Args:
            df: DataFrame to write
            filename: Target filename in GCS

        Returns:
            True if successful, False otherwise
        """
        try:
            csv_buffer = StringIO()
            df.to_csv(csv_buffer, index=False)

            blob = self.bucket.blob(filename)
            blob.upload_from_string(
                csv_buffer.getvalue(),
                content_type='text/csv'
            )

            logger.info(f"Successfully uploaded {filename} to GCS bucket {self.bucket_name}")
            return True

        except GoogleCloudError as e:
            logger.error(f"Error uploading {filename} to GCS: {e}")
            return False

        except Exception as e:
            logger.error(f"Unexpected error uploading {filename} to GCS: {e}")
            return False

    def write_from_bytes(self, content: bytes, filename: str, content_type: str = 'text/csv') -> bool:
        """
        Write raw bytes to GCS.

        Args:
            content: Bytes to write
            filename: Target filename in GCS
            content_type: MIME type

        Returns:
            True if successful, False otherwise
        """
        try:
            blob = self.bucket.blob(filename)
            blob.upload_from_string(content, content_type=content_type)
            logger.info(f"Successfully uploaded {filename} to GCS bucket {self.bucket_name}")
            return True
        except Exception as e:
            logger.error(f"Error uploading {filename} to GCS: {e}")
            return False

    def file_exists(self, filename: str) -> bool:
        """Check if a file exists in GCS"""
        try:
            blob = self.bucket.blob(filename)
            return blob.exists()
        except Exception as e:
            logger.error(f"Error checking if {filename} exists: {e}")
            return False

    def list_files(self, prefix: str = '') -> list:
        """List files in GCS bucket with optional prefix"""
        try:
            blobs = self.storage_client.list_blobs(self.bucket_name, prefix=prefix)
            return [blob.name for blob in blobs]
        except Exception as e:
            logger.error(f"Error listing files in GCS: {e}")
            return []

    def get_file_size(self, filename: str) -> int:
        """Get file size in bytes"""
        try:
            blob = self.bucket.blob(filename)
            if blob.exists():
                blob.reload()
                return blob.size
            return 0
        except Exception as e:
            logger.error(f"Error getting file size for {filename}: {e}")
            return 0

