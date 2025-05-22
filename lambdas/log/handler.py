import os
import json
import boto3
import time
from typing import Dict, Any
from datetime import datetime, timezone

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['TABLE_NAME'])

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for logging execution details to DynamoDB.
    Expected event structure for success:
    {
        "runId": "uuid-string",
        "s3Key": "path/to/file.pdf",
        "status": "SUCCEEDED|FAILED",
        "startTs": "2024-03-14T12:00:00Z",  # ISO format
        "endTs": "2024-03-14T12:01:00Z",    # ISO format
        "rowCount": 42                       # Number of embeddings stored
    }
    
    For failures, the event will include:
    {
        "error": {
            "Cause": "error message",
            "Error": "error type"
        }
    }
    """
    try:
        # Add TTL (30 days from now)
        ttl = int(time.time()) + (30 * 24 * 60 * 60)
        
        # Check if this is an error case
        if "error" in event:
            item = {
                "runId": event["runId"],
                "s3Key": event["s3Key"],
                "status": "FAILED",
                "startTs": event["startTs"],
                "endTs": datetime.now(timezone.utc).isoformat(),
                "error": event["error"].get("Cause", "Unknown error"),
                "failedState": event.get("state", "Unknown"),
                "ttl": ttl
            }
        else:
            item = {
                "runId": event["runId"],
                "s3Key": event["s3Key"],
                "status": event["status"],
                "startTs": event["startTs"],
                "endTs": event["endTs"],
                "rowCount": event.get("rowCount", 0),
                "ttl": ttl
            }
        
        # Store execution log
        table.put_item(Item=item)
        
        return {
            "statusCode": 200,
            "runId": event["runId"],
            "message": "Execution log stored successfully",
            "status": item["status"]
        }
        
    except Exception as e:
        print(f"Error storing execution log: {str(e)}")
        return {
            "statusCode": 500,
            "error": str(e)
        }
