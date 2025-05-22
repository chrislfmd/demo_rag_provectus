import json
import boto3
import time
from typing import List, Dict, Any
import tiktoken  # For token counting

# Initialize Bedrock client
bedrock = boto3.client('bedrock-runtime')

# Titan model ID for Bedrock
MODEL_ID = "amazon.titan-embed-text-v2:0"

def count_tokens(text: str) -> int:
    """Count tokens using tiktoken's cl100k_base encoder."""
    encoder = tiktoken.get_encoding("cl100k_base")
    return len(encoder.encode(text))

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
        print(f"Error getting embedding: {str(e)}")
        raise
    return embeddings

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for text embedding."""
    try:
        # Get text from previous step
        text = event['validated']['Payload']['text']
        # Chunk the text
        chunks = chunk_text(text)
        # Get embeddings for each chunk
        embeddings = get_embeddings(chunks)
        return {
            'statusCode': 200,
            'chunks': chunks,
            'embeddings': embeddings
        }
    except Exception as e:
        print(f"Handler error: {str(e)}")
        return {
            'statusCode': 500,
            'error': str(e),
            'chunks': [],
            'embeddings': []
        }
