import os
import json
import boto3
import logging
import uuid
import sys
from datetime import datetime

# Add path for common modules
sys.path.append('/opt/python')
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
        def log_document_start(self, *args, **kwargs): pass
    exec_logger = DummyLogger()

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    run_id = event.get('runId', str(uuid.uuid4()))
    
    try:
        # Log step start
        exec_logger.log_start(run_id, "init_db", 
                             s3Key=event.get('key', 'unknown'),
                             bucket=event.get('bucket', 'unknown'))
        
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
        
        # Log document start
        exec_logger.log_document_start(run_id, 
                                      filename=event.get('key', 'unknown'),
                                      s3_key=event.get('key', 'unknown'),
                                      documentId=document_id)
        
        # Log step success
        exec_logger.log_success(run_id, "init_db", 
                               documentId=document_id,
                               tableName=table_name)
        
        # Return the event with document ID and runId for the next step
        return {
            **event,
            'documentId': document_id,
            'runId': run_id
        }
        
    except Exception as e:
        logger.error(f"Error initializing document: {str(e)}")
        
        # Log error
        exec_logger.log_error(run_id, "init_db", str(e),
                             s3Key=event.get('key', 'unknown'))
        
        raise 