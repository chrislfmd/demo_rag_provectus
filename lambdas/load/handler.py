import os
import json
import boto3
import logging
import uuid
import sys
import time
from datetime import datetime

# Add path for common modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import execution logger
try:
    from common.exec_logger import logger as exec_logger
except ImportError:
    # Fallback if common module not available
    class DummyLogger:
        def log_start(self, *args, **kwargs): pass
        def log_success(self, *args, **kwargs): pass
        def log_error(self, *args, **kwargs): pass
        def log_document_complete(self, *args, **kwargs): pass
    exec_logger = DummyLogger()

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    run_id = event.get('runId', str(uuid.uuid4()))
    start_time = time.time()
    
    try:
        # Log step start
        exec_logger.log_start(run_id, "load",
                             documentId=event.get('documentId'))
        
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
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Log document completion
        exec_logger.log_document_complete(run_id, items_stored, processing_time,
                                         documentId=document_id,
                                         tableName=table_name)
        
        # Log step success
        exec_logger.log_success(run_id, "load",
                               documentId=document_id,
                               itemsStored=items_stored,
                               processingTime=processing_time,
                               tableName=table_name)
        
        return {
            **event,
            'status': 'success',
            'message': f'Successfully loaded {items_stored} chunks',
            'rowCount': items_stored
        }
        
    except Exception as e:
        logger.error(f"Error loading document: {str(e)}")
        
        # Calculate processing time for error logging
        processing_time = time.time() - start_time
        
        # Log error
        exec_logger.log_error(run_id, "load", str(e),
                             documentId=event.get('documentId'),
                             processingTime=processing_time)
        
        raise
