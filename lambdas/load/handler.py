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
        
        # Get document ID from previous step
        document_id = event.get('documentId')
        if not document_id:
            raise ValueError("No documentId provided in event")
            
        # Get embeddings from previous step
        embeddings = event.get('embedded', {}).get('embeddings', [])
        if not embeddings:
            raise ValueError("No embeddings provided in event")
            
        # Store each chunk with its embedding
        for i, embedding in enumerate(embeddings):
            chunk_id = f"chunk_{i}"
            table.put_item(
                Item={
                    'documentId': document_id,
                    'chunkId': chunk_id,
                    'content': embedding.get('text', ''),
                    'embedding': embedding.get('vector', []),
                    'metadata': {
                        'chunkIndex': i,
                        'timestamp': datetime.utcnow().isoformat()
                    }
                }
            )
            
        logger.info(f"Stored {len(embeddings)} chunks for document {document_id}")
        
        # Update document status
        table.update_item(
            Key={
                'documentId': document_id,
                'chunkId': 'metadata'
            },
            UpdateExpression="SET #status = :status, lastUpdated = :timestamp",
            ExpressionAttributeNames={
                '#status': 'status'
            },
            ExpressionAttributeValues={
                ':status': 'loaded',
                ':timestamp': datetime.utcnow().isoformat()
            }
        )
        
        return {
            **event,
            'status': 'success',
            'message': f'Successfully loaded {len(embeddings)} chunks'
        }
        
    except Exception as e:
        logger.error(f"Error loading document: {str(e)}")
        raise
