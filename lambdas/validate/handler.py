import json
import boto3
import os
import logging
import time
import sys
import uuid

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
    exec_logger = DummyLogger()

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize Textract client
textract = boto3.client('textract')

# Initialize SQS client
sqs = boto3.client('sqs')

def validate_blocks(blocks):
    """Simple validation to check if blocks have non-empty text"""
    for block in blocks:
        if "Text" in block and not block["Text"].strip():
            return False
    return True

def send_error_notification(run_id, bucket, key, error_message, step="Validate"):
    """Send error notification directly to SQS"""
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
                "key": key
            },
            "errorDetails": {
                "failedStep": step,
                "errorMessage": error_message,
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

def wait_for_textract_completion(textract_job_id, max_wait_time=300):
    """Poll Textract job until completion with timeout"""
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        try:
            response = textract.get_document_analysis(JobId=textract_job_id)
            status = response.get('JobStatus')
            
            if status == 'SUCCEEDED':
                return response
            elif status == 'FAILED':
                error_msg = response.get('StatusMessage', 'Unknown error')
                raise ValueError(f"Textract job failed: {error_msg}")
            elif status in ['IN_PROGRESS']:
                print(f"Textract job {textract_job_id} still in progress, waiting...")
                time.sleep(30)
            else:
                raise ValueError(f"Unexpected Textract status: {status}")
                
        except Exception as e:
            if "InvalidJobIdException" in str(e):
                raise ValueError(f"Textract job ID not found: {textract_job_id}")
            elif "Textract job failed" in str(e):
                raise  # Re-raise the specific error
            else:
                print(f"Error checking Textract status: {str(e)}")
                time.sleep(10)
    
    raise TimeoutError(f"Textract job {textract_job_id} did not complete within {max_wait_time} seconds")

def handler(event, _ctx):
    run_id = event.get('runId', str(uuid.uuid4()))
    
    # Log the input event
    logger.info(f"Received event: {json.dumps(event)}")
    
    try:
        # Log step start
        exec_logger.log_start(run_id, "validate",
                             textractJobId=event.get("textractJobId"),
                             s3Key=event.get("key"))
        
        # Get required parameters from event
        textract_job_id = event.get("textractJobId")
        bucket = event.get("bucket") 
        key = event.get("key")
        
        if not textract_job_id:
            raise ValueError("Missing textractJobId in event")
        if not bucket:
            raise ValueError("Missing bucket in event")
        if not key:
            raise ValueError("Missing key in event")
            
        logger.info(f"Processing Textract job: {textract_job_id}")
        logger.info(f"Original document: s3://{bucket}/{key}")
        
        # Wait for Textract job to complete and get results
        response = wait_for_textract_completion(textract_job_id)
        
        # Get blocks from the Textract response
        if "Blocks" not in response:
            raise ValueError(f"No Blocks found in Textract response. Available fields: {list(response.keys())}")
            
        blocks = response["Blocks"]
        logger.info(f"Found {len(blocks)} blocks to validate")
        
        # Simple validation - check for empty text blocks
        if not validate_blocks(blocks):
            logger.error("Validation failed: Found empty text blocks")
            raise ValueError("Validation failed: Found empty text blocks")
        
        logger.info("Validation successful")
        
        # Log step success
        exec_logger.log_success(run_id, "validate",
                               textractJobId=textract_job_id,
                               blocksCount=len(blocks),
                               validationStatus="SUCCESS")
        
        # Return the original event plus validation status
        return {
            "textractJobId": textract_job_id,
            "bucket": bucket,
            "key": key,
            "runId": run_id,
            "validation": {
                "status": "SUCCESS",
                "blocks_count": len(blocks)
            }
        }
        
    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        logger.error(f"Event structure: {json.dumps(event)}")
        
        # Send error notification directly
        send_error_notification(run_id, bucket, key, str(e), "Validate")
        
        # Log error
        exec_logger.log_error(run_id, "validate", str(e),
                             textractJobId=event.get("textractJobId"),
                             s3Key=event.get("key"))
        
        raise
