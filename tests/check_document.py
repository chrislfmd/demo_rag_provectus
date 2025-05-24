#!/usr/bin/env python3
"""
Check a specific document's chunks in DynamoDB
"""
import boto3
import json
from boto3.dynamodb.conditions import Key

def check_document(document_id):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('Documents')
    
    try:
        # Query all items for this document
        response = table.query(
            KeyConditionExpression=Key('documentId').eq(document_id)
        )
        
        items = response.get('Items', [])
        
        print(f"📊 Found {len(items)} items for document {document_id}:")
        print("=" * 80)
        
        for item in items:
            chunk_id = item.get('chunkId', 'Unknown')
            content = item.get('content', '')
            
            print(f"🔹 Chunk: {chunk_id}")
            
            if content:
                print(f"   Content: {content}")
            
            # Check if it has embedding
            if 'embedding' in item:
                embedding = item['embedding']
                print(f"   Embedding: {len(embedding)} dimensions")
                print(f"   Sample values: {embedding[:5]}...")
            
            # Check metadata
            if 'metadata' in item:
                metadata = item['metadata']
                print(f"   Metadata: {json.dumps(metadata, indent=6)}")
            
            print("-" * 60)
        
        if not items:
            print("❌ No items found for this document")
        else:
            print(f"✅ Successfully found {len(items)} items!")
            
    except Exception as e:
        print(f"❌ Error checking document: {str(e)}")

if __name__ == "__main__":
    # Check our successful test document
    document_id = "1efb6ece-5988-47fa-8599-f9fef361bfee"
    print(f"🔍 Checking Document: {document_id}")
    check_document(document_id) 