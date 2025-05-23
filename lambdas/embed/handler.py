import json
import boto3
import time
import logging
import sys
import uuid
from typing import List, Dict, Any
import tiktoken  # For token counting
import os

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

# Initialize clients
bedrock = boto3.client('bedrock-runtime')
textract = boto3.client('textract')
sqs = boto3.client('sqs')

# Titan model ID for Bedrock
MODEL_ID = "amazon.titan-embed-text-v2:0"

def send_error_notification(run_id, bucket, key, document_id, error_message, processing_time, step="Embed"):
    """Send error notification when embedding generation fails"""
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

def count_tokens(text: str) -> int:
    """Count tokens using tiktoken's cl100k_base encoder."""
    encoder = tiktoken.get_encoding("cl100k_base")
    return len(encoder.encode(text))

def extract_text_from_blocks(blocks: List[Dict]) -> str:
    """Extract text from Textract blocks."""
    text_blocks = []
    
    for block in blocks:
        if block.get('BlockType') == 'LINE' and 'Text' in block:
            text_blocks.append(block['Text'])
    
    # Join with spaces and clean up
    text = ' '.join(text_blocks)
    text = ' '.join(text.split())  # Normalize whitespace
    
    logger.info(f"Extracted {len(text)} characters from {len(text_blocks)} text blocks")
    return text

def chunk_text(text: str, max_tokens: int = 500) -> List[str]:
    """Split text into chunks of approximately max_tokens."""
    chunks = []
    current_chunk = []
    current_length = 0
    
    # Split by sentences for better semantic boundaries
    sentences = text.replace('\n', ' ').split('. ')
    
    for sentence in sentences:
        sentence = sentence.strip() + '. '
        sentence_tokens = count_tokens(sentence)
        
        if current_length + sentence_tokens > max_tokens and current_chunk:
            chunks.append(''.join(current_chunk))
            current_chunk = [sentence]
            current_length = sentence_tokens
        else:
            current_chunk.append(sentence)
            current_length += sentence_tokens
    
    if current_chunk:
        chunks.append(''.join(current_chunk))
    
    return chunks

def get_embeddings(texts: List[str]) -> List[List[float]]:
    """Get embeddings from Titan model via Bedrock. Titan only supports one inputText per call."""
    embeddings = []
    try:
        for text in texts:
            response = bedrock.invoke_model(
                modelId=MODEL_ID,
                body=json.dumps({
                    "inputText": text
                })
            )
            result = json.loads(response['body'].read())
            embeddings.append(result['embedding'])
            time.sleep(0.2)  # Rate limit safety
    except Exception as e:
        logger.error(f"Error getting embedding: {str(e)}")
        raise
    return embeddings

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for text embedding."""
    run_id = event.get('runId', str(uuid.uuid4()))
    start_time = time.time()
    
    logger.info(f"Received event: {json.dumps(event)}")
    
    try:
        # Log step start
        exec_logger.log_start(run_id, "embed",
                             textractJobId=event.get("textractJobId"),
                             documentId=event.get("documentId"))
        
        # Get required parameters from event
        textract_job_id = event.get("textractJobId")
        bucket = event.get("bucket")
        key = event.get("key")
        document_id = event.get("documentId")
        
        if not textract_job_id:
            raise ValueError("Missing textractJobId in event")
        if not document_id:
            raise ValueError("Missing documentId in event")
            
        logger.info(f"Processing Textract job: {textract_job_id}")
        logger.info(f"Document ID: {document_id}")
        
        # Get Textract results using JobId
        response = textract.get_document_analysis(JobId=textract_job_id)
        
        job_status = response.get("JobStatus")
        if job_status != "SUCCEEDED":
            raise ValueError(f"Textract job not successful. Status: {job_status}")
            
        blocks = response.get("Blocks", [])
        logger.info(f"Retrieved {len(blocks)} blocks from Textract")
        
        # Extract text from blocks
        text = extract_text_from_blocks(blocks)
        
        if not text.strip():
            raise ValueError("No text extracted from document")
        
        logger.info(f"Extracted text length: {len(text)} characters")
        
        # Chunk the text
        chunks = chunk_text(text)
        logger.info(f"Created {len(chunks)} chunks")
        
        # Get embeddings for each chunk
        embeddings = get_embeddings(chunks)
        logger.info(f"Generated {len(embeddings)} embeddings")
        
        # Calculate processing time
        processing_time = time.time() - start_time
        
        # Log step success
        exec_logger.log_success(run_id, "embed",
                               textractJobId=textract_job_id,
                               documentId=document_id,
                               chunkCount=len(chunks),
                               textLength=len(text),
                               processingTime=processing_time,
                               embeddingCount=len(embeddings))
        
        return {
            'statusCode': 200,
            'textractJobId': textract_job_id,
            'documentId': document_id,
            'bucket': bucket,
            'key': key,
            'runId': run_id,
            'chunks': chunks,
            'embeddings': embeddings,
            'text_length': len(text),
            'chunk_count': len(chunks)
        }
        
    except Exception as e:
        logger.error(f"Handler error: {str(e)}")
        logger.error(f"Event structure: {json.dumps(event)}")
        
        # Calculate processing time for error logging
        processing_time = time.time() - start_time
        
        # Log error
        exec_logger.log_error(run_id, "embed", str(e),
                             textractJobId=event.get("textractJobId"),
                             documentId=event.get("documentId"),
                             processingTime=processing_time)
        
        # Send error notification
        send_error_notification(run_id, bucket, key, document_id, str(e), processing_time)
        
        return {
            'statusCode': 500,
            'error': str(e),
            'runId': run_id,
            'chunks': [],
            'embeddings': []
        }
