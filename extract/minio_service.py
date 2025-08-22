import boto3
from django.conf import settings
from django.utils.timezone import now


def get_minio_client():
    """
    Cria um cliente MinIO usando as configurações do Django.
    """
    return boto3.client(
        's3',
        endpoint_url=f"http{'s' if settings.BUCKETEER_SECURE else ''}://{settings.BUCKETEER_ENDPOINT}",
        aws_access_key_id=settings.BUCKETEER_AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.BUCKETEER_AWS_SECRET_ACCESS_KEY,
        use_ssl=settings.BUCKETEER_SECURE,
        config=boto3.session.Config(signature_version='s3v4')
    )

def upload_file_to_minio(file_obj, object_name):
    """
    Faz upload de um arquivo para o MinIO.

    :param file_path: Caminho do arquivo local a ser enviado.
    :param object_name: Nome do objeto no MinIO.
    :return: URL do objeto no MinIO.
    """
    s3_client = get_minio_client()
    s3_client.upload_fileobj(file_obj, settings.BUCKETEER_BUCKET_NAME, object_name)
    
    return f"http{'s' if settings.BUCKETEER_SECURE else ''}://{settings.BUCKETEER_ENDPOINT}/{settings.BUCKETEER_BUCKET_NAME}/{object_name}"
    

# ======================================================
# 🔹 PRESIGNED URL (upload direto do frontend → bucket)
# ======================================================

def generate_presigned_upload_url(filename, expires_in=3600):
    """
    Gera uma URL pré-assinada para upload direto ao Bucketeer.
    :param filename: Nome do arquivo original
    :param expires_in: Tempo de expiração em segundos (default 1h)
    :return: dict { url, fields, key }
    """

    s3_client = get_minio_client()
    # monta nome único no bucket (ex: uploads/20240821_nome.pdf)
    object_name = f"uploads/{now().strftime('%Y%m%d%H%M%S')}_{filename}"

    response = s3_client.generate_presigned_post(
        Bucket=settings.BUCKETEER_BUCKET_NAME,
        Key=object_name,
        ExpiresIn=expires_in
    )

    return {
        "url": response['url'],
        "fields": response['fields'],
        "key": object_name
    }



def download_file_from_minio(object_key):
    """
    Faz download de um arquivo do MinIO.

    :param object_name: Nome do objeto no MinIO.
    :param file_path: Caminho local onde o arquivo será salvo.
    """
    s3_client = get_minio_client()
    response = s3_client.get_object(Bucket=settings.BUCKETEER_BUCKET_NAME, Key=object_key)
    return response['Body'].read()




def generate_presigned_download_url(object_name, expires_in=3600):
    s3_client = get_minio_client()
    return s3_client.generate_presigned_url(
        'get_object',
        Params={"Bucket": settings.BUCKETEER_BUCKET_NAME, "Key": object_name},
        ExpiresIn=expires_in
    )