import json
import boto3
import os
import time
import uuid
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
        print(f"✅ Successfully logged to DynamoDB: {log_item}")
        
    except Exception as e:
        print(f"❌ Failed to log to DynamoDB: {type(e).__name__}: {str(e)}")
        print(f"   Table name: {table_name}")
        print(f"   Log item: {log_item}")
        # Don't re-raise the exception to avoid breaking the Lambda

def send_error_notification(run_id, bucket, key, document_id, error_message, processing_time, step="Validate"):
    """Send error notification directly to SQS"""
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
                "documentId": document_id
            },
            "errorDetails": {
                "failedStep": step,
                "errorMessage": error_message,
                "processingTimeSeconds": round(processing_time, 2),
                "retryable": False
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

def simulate_textract_processing(bucket, key):
    """Simulate Textract document analysis"""
    print(f"Simulating Textract processing for s3://{bucket}/{key}")
    
    # Simulate processing time
    time.sleep(2)
    
    # Check file extension to simulate different outcomes
    file_extension = key.lower().split('.')[-1] if '.' in key else ''
    
    if file_extension in ['txt', 'csv', 'json']:
        # Simulate error for unsupported file types
        raise ValueError(f"Textract job failed: INVALID_IMAGE_TYPE")
    
    # Simulate successful processing for supported file types
    simulated_blocks = [
        {
            "BlockType": "LINE",
            "Text": "This is simulated text extracted from the document.",
            "Confidence": 95.5
        },
        {
            "BlockType": "LINE", 
            "Text": "Second line of simulated extracted text.",
            "Confidence": 92.3
        },
        {
            "BlockType": "LINE",
            "Text": "Third line demonstrating text extraction simulation.",
            "Confidence": 94.1
        }
    ]
    
    return {
        "JobStatus": "SUCCEEDED",
        "Blocks": simulated_blocks
    }

def validate_blocks(blocks):
    """Simple validation to check if blocks have non-empty text"""
    for block in blocks:
        if block.get("BlockType") == "LINE" and "Text" in block and not block["Text"].strip():
            return False
    return True

def handler(event, context):
    run_id = event.get('runId', str(uuid.uuid4()))
    document_id = event.get('documentId', 'unknown')
    start_time = time.time()
    step = "Validate"
    
    # Log the input event
    print(f"Received event: {json.dumps(event)}")
    
    try:
        # Log step start
        log_to_dynamodb(run_id, document_id, step, "STARTED", "Simulating Textract document analysis")
        
        # Get required parameters from event
        bucket = event.get("bucket") 
        key = event.get("key")
        
        if not bucket:
            raise ValueError("Missing bucket in event")
        if not key:
            raise ValueError("Missing key in event")
            
        print(f"Simulating Textract processing for document: s3://{bucket}/{key}")
        
        # Simulate Textract processing
        response = simulate_textract_processing(bucket, key)
        
        # Get blocks from the simulated response
        blocks = response.get("Blocks", [])
        print(f"Simulated {len(blocks)} text blocks")
        
        # Simple validation - check for empty text blocks
        if not validate_blocks(blocks):
            raise ValueError("Validation failed: Found empty text blocks")
        
        processing_time = time.time() - start_time
        print(f"Validation successful in {processing_time:.2f} seconds")
        
        # Log step success
        log_to_dynamodb(run_id, document_id, step, "SUCCESS", 
                       f"Simulated Textract processing successful. Found {len(blocks)} text blocks.")
        
        # Generate a simulated textract job ID for downstream compatibility
        simulated_job_id = f"simulated-job-{uuid.uuid4().hex[:8]}"
        
        # Return the original event plus validation status and simulated job ID
        return {
            "textractJobId": simulated_job_id,
            "bucket": bucket,
            "key": key,
            "runId": run_id,
            "documentId": document_id,
            "validation": {
                "status": "SUCCESS",
                "blocks_count": len(blocks),
                "processing_time": round(processing_time, 2),
                "simulated": True
            },
            "blocks": blocks  # Include blocks for downstream processing
        }
        
    except Exception as e:
        processing_time = time.time() - start_time
        error_message = str(e)
        print(f"Validation error: {error_message}")
        print(f"Event structure: {json.dumps(event)}")
        
        # Log error
        log_to_dynamodb(run_id, document_id, step, "FAILED", f"Validation failed: {error_message}")
        
        # Send error notification
        send_error_notification(run_id, bucket, key, document_id, error_message, processing_time, step)
        
        raise
