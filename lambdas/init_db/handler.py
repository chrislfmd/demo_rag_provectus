import os
import json
import boto3
import logging
import uuid
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    try:
        # Get table name from environment
        table_name = os.environ['TABLE_NAME']
        
        # Initialize DynamoDB client
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(table_name)
        
        # Create a document record
        document_id = str(uuid.uuid4())
        table.put_item(
            Item={
                'documentId': document_id,
                'chunkId': 'metadata',
                'filename': event.get('key', 'unknown'),
                'status': 'initialized',
                'createdAt': datetime.utcnow().isoformat(),
                'metadata': {
                    'bucket': event.get('bucket', 'unknown'),
                    'key': event.get('key', 'unknown')
                }
            }
        )
        
        logger.info(f"Initialized document record with ID: {document_id}")
        
        # Return the event with document ID for the next step
        return {
            **event,
            'documentId': document_id
        }
        
    except Exception as e:
        logger.error(f"Error initializing document: {str(e)}")
        raise 