import json
import boto3
import os
import uuid
from datetime import datetime
from typing import Dict, Any

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
        print(f"Successfully logged to DynamoDB: {log_item}")
        
    except Exception as e:
        print(f"Failed to log to DynamoDB: {type(e).__name__}: {str(e)}")
        print(f"   Table name: {table_name}")
        print(f"   Log item: {log_item}")
        # Don't re-raise the exception to avoid breaking the Lambda

def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Send notification to SQS queues about pipeline execution status.
    
    Expected event structure:
    {
        "runId": "unique-execution-id",
        "status": "SUCCESS|FAILED", 
        "documentInfo": {
            "bucket": "s3-bucket",
            "key": "document.pdf",
            "documentId": "uuid"
        },
        "processingResults": {
            "chunkCount": 5,
            "processingTime": 45.2,
            "textLength": 1234
        },
        "error": "error message if failed"
    }
    """
    
    run_id = event.get('runId', str(uuid.uuid4()))
    document_id = event.get('documentInfo', {}).get('documentId', 'unknown')
    step = "Notify"
    
    try:
        # Log notification start
        log_to_dynamodb(run_id, document_id, step, "STARTED", f"Sending notifications for status: {event.get('status')}")
        
        # Get required parameters
        status = event.get('status', 'UNKNOWN')
        document_info = event.get('documentInfo', {})
        processing_results = event.get('processingResults', {})
        
        # Get SQS queue URLs from environment
        main_queue_url = os.environ.get('NOTIFICATION_QUEUE_URL')
        success_queue_url = os.environ.get('SUCCESS_QUEUE_URL') 
        error_queue_url = os.environ.get('ERROR_QUEUE_URL')
        
        if not main_queue_url:
            raise ValueError("NOTIFICATION_QUEUE_URL environment variable not set")
        
        # Initialize SQS client
        sqs = boto3.client('sqs')
        
        # Create notification message
        notification_message = {
            "timestamp": datetime.utcnow().isoformat(),
            "runId": run_id,
            "status": status,
            "pipeline": "RAG Document Processing",
            "documentInfo": document_info,
            "processingResults": processing_results
        }
        
        # Add error information if failed
        if status == "FAILED" and 'errorDetails' in event:
            notification_message['errorDetails'] = event['errorDetails']
        
        # Create message attributes
        message_attributes = {
            'Status': {
                'StringValue': status,
                'DataType': 'String'
            },
            'Pipeline': {
                'StringValue': 'RAG',
                'DataType': 'String'
            },
            'Timestamp': {
                'StringValue': notification_message['timestamp'],
                'DataType': 'String'
            }
        }
        
        if document_info.get('documentId'):
            message_attributes['DocumentId'] = {
                'StringValue': document_info['documentId'],
                'DataType': 'String'
            }
        
        messages_sent = 0
        
        # Send to main notification queue
        try:
            sqs.send_message(
                QueueUrl=main_queue_url,
                MessageBody=json.dumps(notification_message, indent=2),
                MessageAttributes=message_attributes
            )
            messages_sent += 1
            print(f"Sent notification to main queue: {status}")
        except Exception as e:
            print(f"Failed to send to main queue: {str(e)}")
        
        # Send to status-specific queues
        if status == "SUCCESS" and success_queue_url:
            try:
                # Add success-specific metadata
                success_message = {
                    **notification_message,
                    "successMetrics": {
                        "chunksCreated": processing_results.get('chunkCount', 0),
                        "processingTimeSeconds": processing_results.get('processingTime', 0),
                        "documentSize": processing_results.get('textLength', 0)
                    }
                }
                
                sqs.send_message(
                    QueueUrl=success_queue_url,
                    MessageBody=json.dumps(success_message, indent=2),
                    MessageAttributes=message_attributes
                )
                messages_sent += 1
                print(f"Sent success notification to success queue")
            except Exception as e:
                print(f"Failed to send to success queue: {str(e)}")
        
        elif status == "FAILED" and error_queue_url:
            try:
                # Add error-specific metadata
                error_message = {
                    **notification_message,
                    "errorDetails": {
                        "failedStep": event.get('errorDetails', {}).get('failedStep', 'unknown'),
                        "errorMessage": event.get('errorDetails', {}).get('errorMessage', 'Unknown error'),
                        "retryable": event.get('errorDetails', {}).get('retryable', False)
                    }
                }
                
                sqs.send_message(
                    QueueUrl=error_queue_url,
                    MessageBody=json.dumps(error_message, indent=2),
                    MessageAttributes=message_attributes
                )
                messages_sent += 1
                print(f"Sent error notification to error queue")
            except Exception as e:
                print(f"Failed to send to error queue: {str(e)}")
        
        # Log success
        log_to_dynamodb(run_id, document_id, step, "SUCCESS", 
                       f"Successfully sent {messages_sent} notifications for {status} status")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Notifications sent successfully',
                'runId': run_id,
                'status': status,
                'messagesSent': messages_sent
            })
        }
        
    except Exception as e:
        error_message = str(e)
        print(f"Error sending notifications: {error_message}")
        
        # Log error
        log_to_dynamodb(run_id, document_id, step, "FAILED", f"Notification failed: {error_message}")
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': error_message,
                'runId': run_id
            })
        } 