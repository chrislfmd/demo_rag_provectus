import json
import boto3
import time
import logging
from typing import List, Dict, Any
import tiktoken  # For token counting

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize clients
bedrock = boto3.client('bedrock-runtime')
textract = boto3.client('textract')

# Titan model ID for Bedrock
MODEL_ID = "amazon.titan-embed-text-v2:0"

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
    logger.info(f"Received event: {json.dumps(event)}")
    
    try:
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
        
        return {
            'statusCode': 200,
            'textractJobId': textract_job_id,
            'documentId': document_id,
            'bucket': bucket,
            'key': key,
            'chunks': chunks,
            'embeddings': embeddings,
            'text_length': len(text),
            'chunk_count': len(chunks)
        }
        
    except Exception as e:
        logger.error(f"Handler error: {str(e)}")
        logger.error(f"Event structure: {json.dumps(event)}")
        return {
            'statusCode': 500,
            'error': str(e),
            'chunks': [],
            'embeddings': []
        }
