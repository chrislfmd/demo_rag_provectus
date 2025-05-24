import json
import boto3
import os
from datetime import datetime, timedelta
from decimal import Decimal

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])

def handler(event, context):
    """
    Log execution metadata to DynamoDB
    
    Expected event structure:
    {
        "runId": "unique-execution-id",
        "status": "STARTED|IN_PROGRESS|SUCCESS|FAILED",
        "step": "init_db|validate|embed|load",
        "documentInfo": {...},
        "metadata": {...},
        "error": "error message if failed"
    }
    """
    
    try:
        # Extract required fields
        run_id = event.get('runId')
        status = event.get('status', 'UNKNOWN')
        step = event.get('step', 'unknown')
        
        if not run_id:
            raise ValueError("runId is required")
        
        # Create timestamp
        timestamp = datetime.utcnow().isoformat()
        
        # TTL for 30 days (optional cleanup)
        ttl = int((datetime.utcnow() + timedelta(days=30)).timestamp())
        
        # Prepare log entry
        log_entry = {
            'runId': run_id,
            'timestamp': timestamp,
            'status': status,
            'step': step,
            'ttl': ttl
        }
        
        # Add optional fields
        if 'documentInfo' in event:
            log_entry['documentInfo'] = event['documentInfo']
            
        if 'metadata' in event:
            log_entry['metadata'] = event['metadata']
            
        if 'error' in event:
            log_entry['error'] = event['error']
            
        if 'processingTime' in event:
            log_entry['processingTime'] = Decimal(str(event['processingTime']))
            
        if 'chunkCount' in event:
            log_entry['chunkCount'] = event['chunkCount']
            
        if 'textractJobId' in event:
            log_entry['textractJobId'] = event['textractJobId']
            
        # Write to DynamoDB
        table.put_item(Item=log_entry)
        
        print(f"Logged execution: {run_id} - {step} - {status}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Log entry created successfully',
                'runId': run_id,
                'step': step,
                'status': status
            })
        }
        
    except Exception as e:
        error_msg = str(e)
        print(f"Error logging execution: {error_msg}")
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': error_msg,
                'runId': run_id
            })
        }
