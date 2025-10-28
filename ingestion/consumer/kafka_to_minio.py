import boto3
from kafka import KafkaConsumer
import json
import pandas as pd
from datetime import datetime
import os
from dotenv import load_dotenv
import sys

from src.exception import CustomException
from src.logger import logging

# -----------------------------
# Load secrets from .env
# -----------------------------
load_dotenv()

# Kafka consumer settings
try:
    consumer = KafkaConsumer(
        'banking_server.public.customers',
        'banking_server.public.accounts',
        'banking_server.public.transactions',
        bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP"),
        auto_offset_reset='earliest',
        enable_auto_commit=True,
        group_id=os.getenv("KAFKA_GROUP"),
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )
    logging.info("Kafka Consumer connected successfully.")
except Exception as e:
    raise CustomException(e, sys)

# MinIO client
try:
    s3 = boto3.client(
        's3',
        endpoint_url=os.getenv("MINIO_ENDPOINT"),
        aws_access_key_id=os.getenv("MINIO_ACCESS_KEY"),
        aws_secret_access_key=os.getenv("MINIO_SECRET_KEY")
    )
    bucket = os.getenv("MINIO_BUCKET")

    # Create bucket if not exists
    if bucket not in [b['Name'] for b in s3.list_buckets()['Buckets']]:
        s3.create_bucket(Bucket=bucket)
        logging.info(f"Bucket '{bucket}' created successfully.")
    else:
        logging.info(f"Bucket '{bucket}' already exists.")
        
except Exception as e:
    raise CustomException(e, sys)

# -----------------------------
# Write data to MinIO
# -----------------------------
def write_to_minio(table_name, records):
    if not records:
        return
    try:
        df = pd.DataFrame(records)
        date_str = datetime.now().strftime('%Y-%m-%d')
        file_path = f'{table_name}_{date_str}.parquet'
        df.to_parquet(file_path, engine='fastparquet', index=False)
        
        s3_key = f'{table_name}/date={date_str}/{table_name}_{datetime.now().strftime("%H%M%S%f")}.parquet'
        
        s3.upload_file(file_path, bucket, s3_key)
        os.remove(file_path)
        
        logging.info(f'Uploaded {len(records)} records to s3://{bucket}/{s3_key}')
        
    except Exception as e:
        raise CustomException(e, sys)

# -----------------------------
# Consume Kafka and batch write
# -----------------------------
batch_size = 50
buffer = {
    'banking_server.public.customers': [],
    'banking_server.public.accounts': [],
    'banking_server.public.transactions': []
}

logging.info("Connected to Kafka. Listening for messages...")

try:
    for message in consumer:
        try:
            topic = message.topic
            event = message.value
            payload = event.get("payload", {})
            record = payload.get("after")

            if record:
                buffer[topic].append(record)
                logging.debug(f"Received record from topic '{topic}': {record}")  # Debugging

            # Write to MinIO when batch is full
            if len(buffer[topic]) >= batch_size:
                table_name = topic.split('.')[-1]
                write_to_minio(table_name, buffer[topic])
                buffer[topic] = []
            
        except Exception as e:
            raise CustomException(e, sys)
        
except Exception as e:
    raise CustomException(e, sys)

finally:
    consumer.close()
    logging.info("Kafka consumer connection closed.")