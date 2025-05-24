import os
import json
import boto3
import uuid
import time
from datetime import datetime

def log_to_dynamodb(run_id, document_id, step, status, message=None):
    """Log step execution to DynamoDB"""
    table_name = os.environ.get("EXEC_LOG_TABLE")
    if not table_name:
        print("No EXEC_LOG_TABLE env var set, skipping log.")
        return
    
    try:
        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(table_name)
        timestamp = datetime.utcnow().isoformat() + "Z"
        step_timestamp = f"{step}_{timestamp}"  # Unique sort key combining step and timestamp
        
        log_item = {
            "runId": run_id or "unknown",
            "stepTimestamp": step_timestamp,
            "documentId": document_id or "unknown",
            "step": step,
            "status": status,
            "timestamp": timestamp,
            "message": message or ""
        }
        
        print(f"Attempting to log to DynamoDB table '{table_name}': {log_item}")
        
        # Try the put_item operation
        response = table.put_item(Item=log_item)
        
        print(f"DynamoDB put_item response: {response}")
        print(f"Successfully logged to DynamoDB: {log_item}")
        
    except Exception as e:
        print(f"Failed to log to DynamoDB: {type(e).__name__}: {str(e)}")
        print(f"   Table name: {table_name}")
        print(f"   Log item: {log_item}")
        # Don't re-raise the exception to avoid breaking the Lambda

def send_error_notification(run_id, bucket, key, error_message, processing_time, step="InitDB"):
    """Send error notification when database initialization fails"""
    try:
        sqs = boto3.client('sqs')
        
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
                "documentId": "unknown"  # Not created yet due to init failure
            },
            "errorDetails": {
                "failedStep": step,
                "errorMessage": error_message,
                "processingTimeSeconds": round(processing_time, 2),
                "retryable": True  # Init DB failures are usually retryable
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
            print(f"Sent error notification to main queue")
        except Exception as e:
            print(f"Failed to send to main queue: {str(e)}")
        
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
                
                print(f"Sent error notification to error queue")
            except Exception as e:
                print(f"Failed to send to error queue: {str(e)}")
    except Exception as e:
        print(f"Failed to send error notification: {str(e)}")

def handler(event, context):
    run_id = event.get('runId', str(uuid.uuid4()))
    start_time = time.time()
    document_id = str(uuid.uuid4())
    step = "InitDB"
    
    # Extract document info for notifications
    bucket = event.get('bucket', 'unknown')
    key = event.get('key', 'unknown')
    
    try:
        # Log step start
        log_to_dynamodb(run_id, document_id, step, "STARTED", f"Initializing document record for s3://{bucket}/{key}")
        
        # Get table name from environment
        table_name = os.environ['TABLE_NAME']
        
        # Initialize DynamoDB client
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(table_name)
        
        # Create a document record
        table.put_item(
            Item={
                'documentId': document_id,
                'chunkId': 'metadata',
                'filename': key,
                'status': 'initialized',
                'createdAt': datetime.utcnow().isoformat(),
                'metadata': {
                    'bucket': bucket,
                    'key': key
                }
            }
        )
        
        print(f"Initialized document record with ID: {document_id}")
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Log step success
        log_to_dynamodb(run_id, document_id, step, "SUCCESS", 
                       f"Document record created successfully in table {table_name}")
        
        # Return the event with document ID and runId for the next step
        return {
            **event,
            'documentId': document_id,
            'runId': run_id
        }
        
    except Exception as e:
        error_message = str(e)
        print(f"Error initializing document: {error_message}")
        
        # Calculate processing time for error logging
        processing_time = time.time() - start_time
        
        # Log error
        log_to_dynamodb(run_id, document_id, step, "FAILED", f"Failed to initialize document: {error_message}")
        
        # Send error notification
        send_error_notification(run_id, bucket, key, error_message, processing_time, step)
        
        raise 