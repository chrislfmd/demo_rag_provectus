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
            
        # Get embeddings and chunks from previous step
        embedded_data = event.get('embedded', {})
        if embedded_data.get('statusCode') != 200:
            raise ValueError(f"Embedding failed: {embedded_data.get('error', 'Unknown error')}")
            
        chunks = embedded_data.get('chunks', [])
        embeddings = embedded_data.get('embeddings', [])
        
        if not chunks or not embeddings:
            raise ValueError("No chunks or embeddings provided in event")
            
        if len(chunks) != len(embeddings):
            raise ValueError(f"Chunk count ({len(chunks)}) doesn't match embedding count ({len(embeddings)})")
            
        # Store each chunk with its embedding
        items_stored = 0
        for i, (chunk_text, embedding_vector) in enumerate(zip(chunks, embeddings)):
            chunk_id = f"chunk_{i}"
            
            try:
                table.put_item(
                    Item={
                        'documentId': document_id,
                        'chunkId': chunk_id,
                        'content': chunk_text,
                        'embedding': embedding_vector,
                        'metadata': {
                            'chunkIndex': i,
                            'chunkLength': len(chunk_text),
                            'embeddingDimension': len(embedding_vector) if embedding_vector else 0,
                            'timestamp': datetime.utcnow().isoformat()
                        }
                    }
                )
                items_stored += 1
            except Exception as chunk_error:
                logger.error(f"Error storing chunk {i}: {str(chunk_error)}")
                # Continue with other chunks but log the error
                
        logger.info(f"Stored {items_stored} chunks for document {document_id}")
        
        # Update document status
        table.update_item(
            Key={
                'documentId': document_id,
                'chunkId': 'metadata'
            },
            UpdateExpression="SET #status = :status, lastUpdated = :timestamp, chunkCount = :count",
            ExpressionAttributeNames={
                '#status': 'status'
            },
            ExpressionAttributeValues={
                ':status': 'loaded',
                ':timestamp': datetime.utcnow().isoformat(),
                ':count': items_stored
            }
        )
        
        return {
            **event,
            'status': 'success',
            'message': f'Successfully loaded {items_stored} chunks',
            'rowCount': items_stored
        }
        
    except Exception as e:
        logger.error(f"Error loading document: {str(e)}")
        raise
