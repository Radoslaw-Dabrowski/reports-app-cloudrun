"""
S3 client utilities for Cloud Run.
Implements caching and lazy loading for optimal cold start performance.
"""
import logging
from typing import Optional
import pandas as pd
import boto3
from botocore.exceptions import ClientError
from io import StringIO

logger = logging.getLogger(__name__)


class S3Manager:
    """
    S3 Manager with lazy initialization and caching support.
    Optimized for Cloud Run serverless environment.
    """

    def __init__(self, bucket_name: str, aws_access_key: str, aws_secret_key: str, region: str = 'eu-north-1'):
        self.bucket_name = bucket_name
        self.aws_access_key = aws_access_key
        self.aws_secret_key = aws_secret_key
        self.region = region
        self._s3_client = None

    @property
    def s3_client(self):
        """Lazy initialization of S3 client"""
        if self._s3_client is None:
            logger.info("Initializing S3 client")
            self._s3_client = boto3.client(
                's3',
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key,
                region_name=self.region
            )
        return self._s3_client

    def read_csv(self, filename: str) -> pd.DataFrame:
        """
        Read CSV file from S3.

        Args:
            filename: Name of the CSV file in S3

        Returns:
            DataFrame with CSV contents
        """
        try:
            logger.info(f"[S3] Reading {filename} from bucket {self.bucket_name}")
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=filename)
            content = response['Body'].read().decode('utf-8')

            if not content.strip():
                logger.warning(f"{filename} is empty")
                return pd.DataFrame()

            df = pd.read_csv(StringIO(content), quotechar='"')
            logger.info(f"Successfully read {len(df)} rows and {len(df.columns)} columns from {filename}")
            if len(df) > 0:
                logger.debug(f"Columns in {filename}: {df.columns.tolist()[:10]}")  # Log first 10 columns
            return df

        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                logger.error(f"{filename} does not exist in bucket {self.bucket_name}. Available files: {self.list_files()[:10]}")
            elif error_code == 'AllAccessDisabled':
                logger.error(f"Access to bucket {self.bucket_name} is disabled")
            else:
                logger.error(f"Unexpected S3 error: {e}")
            return pd.DataFrame()

        except pd.errors.EmptyDataError:
            logger.error(f"{filename} is empty or has no columns to parse")
            return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error reading {filename} from S3: {e}", exc_info=True)
            return pd.DataFrame()

    def write_csv(self, df: pd.DataFrame, filename: str) -> bool:
        """
        Write DataFrame to S3 as CSV.

        Args:
            df: DataFrame to write
            filename: Target filename in S3

        Returns:
            True if successful, False otherwise
        """
        try:
            csv_buffer = StringIO()
            df.to_csv(csv_buffer, index=False)

            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=filename,
                Body=csv_buffer.getvalue()
            )

            logger.info(f"Successfully uploaded {filename} to S3 bucket {self.bucket_name}")
            return True

        except ClientError as e:
            logger.error(f"Error uploading {filename} to S3: {e}")
            return False

        except Exception as e:
            logger.error(f"Unexpected error uploading {filename}: {e}")
            return False

    def file_exists(self, filename: str) -> bool:
        """Check if a file exists in S3"""
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=filename)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            logger.error(f"Error checking if {filename} exists: {e}")
            return False

    def list_files(self, prefix: str = '') -> list:
        """List files in S3 bucket with optional prefix"""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )

            if 'Contents' not in response:
                return []

            return [obj['Key'] for obj in response['Contents']]

        except ClientError as e:
            logger.error(f"Error listing files in S3: {e}")
            return []
