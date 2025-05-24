import json
import time
import os
import boto3
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

def handler(event, context):
    document_id = event.get("documentId", "unknown")
    run_id = event.get("runId", "unknown")
    blocks = event.get("blocks", [])
    step = "Embed"
    
    log_to_dynamodb(run_id, document_id, step, "STARTED", "Simulating embedding step.")
    
    # Simulate embedding work
    time.sleep(1)
    
    # Create simulated chunks from blocks
    simulated_chunks = []
    simulated_embeddings = []
    
    for i, block in enumerate(blocks):
        if block.get("BlockType") == "LINE" and "Text" in block:
            chunk_text = block["Text"]
            chunk_id = f"chunk_{i}"
            
            # Create chunk
            chunk = {
                "chunkId": chunk_id,
                "text": chunk_text,
                "confidence": block.get("Confidence", 95.0),
                "length": len(chunk_text)
            }
            simulated_chunks.append(chunk)
            
            # Create simulated embedding (384 dimensions for demo)
            embedding = [0.1 + (i * 0.01)] * 384
            simulated_embeddings.append(embedding)
    
    chunk_count = len(simulated_chunks)
    total_text_length = sum(len(chunk["text"]) for chunk in simulated_chunks)
    avg_chunk_size = total_text_length // chunk_count if chunk_count > 0 else 0
    
    log_to_dynamodb(run_id, document_id, step, "SUCCESS", 
                   f"Simulated embeddings for {chunk_count} chunks, total text length: {total_text_length}")
    
    return {
        "statusCode": 200,
        "chunks": simulated_chunks,
        "embeddings": simulated_embeddings,
        "chunk_count": chunk_count,
        "text_length": total_text_length,
        "avg_chunk_size": avg_chunk_size,
        "vector_dimensions": 384,
        "embedding_model": "simulated-embeddings-v1",
        "simulated": True
    }
