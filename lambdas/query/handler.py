import json
import boto3
import os
import logging
import math
from typing import List, Dict, Any
from decimal import Decimal

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize clients
dynamodb = boto3.resource('dynamodb')
bedrock = boto3.client('bedrock-runtime')

# Get table name from environment
TABLE_NAME = os.environ.get('TABLE_NAME', 'Documents')
table = dynamodb.Table(TABLE_NAME)

# Titan model ID for Bedrock
MODEL_ID = "amazon.titan-embed-text-v2:0"

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors using pure Python."""
    if len(vec1) != len(vec2):
        return 0.0
    
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    norm_vec1 = math.sqrt(sum(a * a for a in vec1))
    norm_vec2 = math.sqrt(sum(a * a for a in vec2))
    
    if norm_vec1 == 0 or norm_vec2 == 0:
        return 0.0
    
    return dot_product / (norm_vec1 * norm_vec2)

def embed_query(query_text: str) -> List[float]:
    """Generate embedding for query text using Bedrock Titan."""
    try:
        request_body = {
            "inputText": query_text,
            "dimensions": 1024,
            "normalize": True
        }
        
        response = bedrock.invoke_model(
            modelId=MODEL_ID,
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response['body'].read())
        return response_body['embedding']
        
    except Exception as e:
        logger.error(f"Error generating embedding: {str(e)}")
        raise

def decimal_to_float(obj):
    """Convert DynamoDB Decimal objects to float for JSON serialization."""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decimal_to_float(v) for v in obj]
    return obj

def search_similar_chunks(query_embedding: List[float], limit: int = 5) -> List[Dict]:
    """Search for similar document chunks in DynamoDB."""
    try:
        # Scan all documents to find chunks with embeddings
        response = table.scan(
            FilterExpression='attribute_exists(embedding) AND chunkId <> :metadata',
            ExpressionAttributeValues={':metadata': 'metadata'}
        )
        
        chunks_with_similarity = []
        
        for item in response['Items']:
            if 'embedding' in item and item['embedding']:
                # Convert DynamoDB number format to float list
                stored_embedding = [float(x) for x in item['embedding']]
                
                # Calculate similarity
                similarity = cosine_similarity(query_embedding, stored_embedding)
                
                # Add similarity score to the item
                result_item = decimal_to_float(item)
                result_item['similarity'] = similarity
                chunks_with_similarity.append(result_item)
        
        # Sort by similarity (highest first) and return top results
        chunks_with_similarity.sort(key=lambda x: x['similarity'], reverse=True)
        return chunks_with_similarity[:limit]
        
    except Exception as e:
        logger.error(f"Error searching similar chunks: {str(e)}")
        raise

def handler(event, context):
    """Main handler for query processing."""
    logger.info(f"Received event: {json.dumps(event)}")
    
    try:
        # Parse the request
        if 'body' in event:
            # API Gateway format
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
            query_text = body.get('query')
            limit = body.get('limit', 5)
        else:
            # Direct invocation format
            query_text = event.get('query')
            limit = event.get('limit', 5)
        
        if not query_text:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': 'Query text is required'
                })
            }
        
        logger.info(f"Processing query: {query_text}")
        
        # Generate embedding for the query
        query_embedding = embed_query(query_text)
        logger.info(f"Generated query embedding with {len(query_embedding)} dimensions")
        
        # Search for similar chunks
        similar_chunks = search_similar_chunks(query_embedding, limit)
        logger.info(f"Found {len(similar_chunks)} similar chunks")
        
        # Prepare response
        response = {
            'query': query_text,
            'results': similar_chunks,
            'count': len(similar_chunks)
        }
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(response, default=str)
        }
        
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'error': f'Internal server error: {str(e)}'
            })
        } 