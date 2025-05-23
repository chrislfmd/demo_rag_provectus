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

# Initialize SQS client
sqs = boto3.client('sqs')

def send_success_notification(run_id, bucket, key, document_id, chunks_stored, processing_time, total_text_length=0):
    """Send success notification when pipeline completes successfully"""
    try:
        # Get SQS queue URLs from environment or use default names
        notification_queue_url = os.environ.get('NOTIFICATION_QUEUE_URL')
        success_queue_url = os.environ.get('SUCCESS_QUEUE_URL')
        
        if not notification_queue_url:
            # Fallback: construct queue URL from account info
            account_id = boto3.client('sts').get_caller_identity()['Account']
            region = boto3.Session().region_name or 'us-east-1'
            notification_queue_url = f"https://sqs.{region}.amazonaws.com/{account_id}/rag-pipeline-notifications"
            success_queue_url = f"https://sqs.{region}.amazonaws.com/{account_id}/rag-pipeline-success"
        
        success_notification = {
            "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
            "runId": run_id,
            "status": "SUCCESS",
            "pipeline": "RAG Document Processing",
            "documentInfo": {
                "bucket": bucket,
                "key": key,
                "documentId": document_id
            },
            "processingResults": {
                "chunkCount": chunks_stored,
                "textLength": total_text_length,
                "processingTimeSeconds": round(processing_time, 2),
                "avgChunkSize": round(total_text_length / chunks_stored, 2) if chunks_stored > 0 else 0
            },
            "completionInfo": {
                "pipelineStage": "COMPLETED",
                "lastStep": "Load",
                "dataStored": True,
                "searchReady": True
            }
        }
        
        # Send to main notification queue
        try:
            sqs.send_message(
                QueueUrl=notification_queue_url,
                MessageBody=json.dumps(success_notification, indent=2),
                MessageAttributes={
                    'Status': {'StringValue': 'SUCCESS', 'DataType': 'String'},
                    'Pipeline': {'StringValue': 'RAG', 'DataType': 'String'},
                    'DocumentId': {'StringValue': document_id, 'DataType': 'String'},
                    'ChunkCount': {'StringValue': str(chunks_stored), 'DataType': 'Number'}
                }
            )
            print(f"✅ Sent success notification to main queue")
        except Exception as e:
            print(f"⚠️ Failed to send to main queue: {str(e)}")
        
        # Send to success-specific queue
        if success_queue_url:
            try:
                sqs.send_message(
                    QueueUrl=success_queue_url,
                    MessageBody=json.dumps(success_notification, indent=2),
                    MessageAttributes={
                        'Status': {'StringValue': 'SUCCESS', 'DataType': 'String'},
                        'DocumentId': {'StringValue': document_id, 'DataType': 'String'},
                        'ChunkCount': {'StringValue': str(chunks_stored), 'DataType': 'Number'}
                    }
                )
                print(f"✅ Sent success notification to success queue")
            except Exception as e:
                print(f"⚠️ Failed to send to success queue: {str(e)}")
        
    except Exception as e:
        print(f"❌ Failed to send success notification: {str(e)}")

def send_error_notification(run_id, bucket, key, document_id, error_message, processing_time, step="Load"):
    """Send error notification when load operation fails"""
    try:
        # Get SQS queue URLs from environment or use default names
        notification_queue_url = os.environ.get('NOTIFICATION_QUEUE_URL')
        error_queue_url = os.environ.get('ERROR_QUEUE_URL')
        
        if not notification_queue_url:
            # Fallback: construct queue URL from account info
            account_id = boto3.client('sts').get_caller_identity()['Account']
            region = boto3.Session().region_name or 'us-east-1'
            notification_queue_url = f"https://sqs.{region}.amazonaws.com/{account_id}/rag-pipeline-notifications"
            error_queue_url = f"https://sqs.{region}.amazonaws.com/{account_id}/rag-pipeline-errors"
        
        error_notification = {
            "timestamp": time.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
            "runId": run_id,
            "status": "FAILED",
            "pipeline": "RAG Document Processing",
            "documentInfo": {
                "bucket": bucket,
                "key": key,
                "documentId": document_id
            },
            "errorDetails": {
                "failedStep": step,
                "errorMessage": error_message,
                "processingTimeSeconds": round(processing_time, 2),
                "retryable": True
            }
        }
        
        # Send to main notification queue
        try:
            sqs.send_message(
                QueueUrl=notification_queue_url,
                MessageBody=json.dumps(error_notification, indent=2),
                MessageAttributes={
                    'Status': {'StringValue': 'FAILED', 'DataType': 'String'},
                    'Pipeline': {'StringValue': 'RAG', 'DataType': 'String'},
                    'FailedStep': {'StringValue': step, 'DataType': 'String'}
                }
            )
            print(f"✅ Sent error notification to main queue")
        except Exception as e:
            print(f"⚠️ Failed to send to main queue: {str(e)}")
        
        # Send to error-specific queue
        if error_queue_url:
            try:
                sqs.send_message(
                    QueueUrl=error_queue_url,
                    MessageBody=json.dumps(error_notification, indent=2),
                    MessageAttributes={
                        'Status': {'StringValue': 'FAILED', 'DataType': 'String'},
                        'FailedStep': {'StringValue': step, 'DataType': 'String'}
                    }
                )
                print(f"✅ Sent error notification to error queue")
            except Exception as e:
                print(f"⚠️ Failed to send to error queue: {str(e)}")
        
    except Exception as e:
        print(f"❌ Failed to send error notification: {str(e)}")

def handler(event, context):
    run_id = event.get('runId', str(uuid.uuid4()))
    start_time = time.time()
    
    # Extract document info for notifications
    bucket = event.get('bucket', 'unknown')
    key = event.get('key', 'unknown')
    document_id = event.get('documentId')
    
    try:
        # Log step start
        exec_logger.log_start(run_id, "load",
                             documentId=document_id)
        
        # Get table name from environment
        table_name = os.environ['TABLE_NAME']
        
        # Initialize DynamoDB client
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(table_name)
        
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
            
        # Calculate total text length for metrics
        total_text_length = sum(len(chunk) for chunk in chunks)
            
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
        
        # Send success notification - PIPELINE COMPLETED! 🎉
        send_success_notification(run_id, bucket, key, document_id, items_stored, processing_time, total_text_length)
        
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
        
        # Send error notification
        send_error_notification(run_id, bucket, key, document_id, str(e), processing_time, "Load")
        
        # Log error
        exec_logger.log_error(run_id, "load", str(e),
                             documentId=document_id,
                             processingTime=processing_time)
        
        raise
