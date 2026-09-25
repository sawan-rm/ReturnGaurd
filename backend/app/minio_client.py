from minio import Minio
from minio.error import S3Error
from app.config import settings

def get_minio_client() -> Minio:
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=False
    )

def ensure_bucket_exists():
    client = get_minio_client()
    try:
        if not client.bucket_exists(settings.minio_bucket):
            client.make_bucket(settings.minio_bucket)
            # Make bucket public for easy reading by frontend
            policy = f"""{{
                "Version": "2012-10-17",
                "Statement": [
                    {{
                        "Effect": "Allow",
                        "Principal": {{"AWS": "*"}},
                        "Action": ["s3:GetObject"],
                        "Resource": ["arn:aws:s3:::{settings.minio_bucket}/*"]
                    }}
                ]
            }}"""
            client.set_bucket_policy(settings.minio_bucket, policy)
    except S3Error as err:
        print(f"MinIO bucket error: {err}")
