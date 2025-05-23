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

def validate_blocks(blocks):
    """Simple validation to check if blocks have non-empty text"""
    for block in blocks:
        if "Text" in block and not block["Text"].strip():
            return False
    return True

def wait_for_textract_completion(job_id, max_retries=10, wait_seconds=30):
    """Wait for Textract job to complete with exponential backoff"""
    retries = 0
    
    while retries < max_retries:
        try:
            response = textract.get_document_analysis(JobId=job_id)
            job_status = response.get("JobStatus")
            
            logger.info(f"Textract job {job_id} status: {job_status} (attempt {retries + 1})")
            
            if job_status == "SUCCEEDED":
                return response
            elif job_status == "FAILED":
                raise ValueError(f"Textract job failed: {response.get('StatusMessage', 'Unknown error')}")
            elif job_status == "IN_PROGRESS":
                # Wait with exponential backoff
                wait_time = wait_seconds * (2 ** min(retries, 4))  # Cap at 16x base wait
                logger.info(f"Job still in progress, waiting {wait_time} seconds...")
                time.sleep(wait_time)
                retries += 1
            else:
                raise ValueError(f"Unexpected Textract job status: {job_status}")
                
        except Exception as e:
            if "InvalidJobIdException" in str(e):
                raise ValueError(f"Invalid Textract job ID: {job_id}")
            raise
    
    raise ValueError(f"Textract job did not complete after {max_retries} retries")

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
        
        # Log error
        exec_logger.log_error(run_id, "validate", str(e),
                             textractJobId=event.get("textractJobId"),
                             s3Key=event.get("key"))
        
        raise
