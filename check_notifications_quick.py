#!/usr/bin/env python3

import boto3
import json
import time

def check_notifications():
    sqs = boto3.client('sqs')
    account_id = boto3.client('sts').get_caller_identity()['Account']
    region = 'us-east-1'
    queue_url = f'https://sqs.{region}.amazonaws.com/{account_id}/rag-pipeline-notifications'

    print('🔍 Checking for recent notifications...')
    try:
        response = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=5,
            WaitTimeSeconds=10,
            MessageAttributeNames=['All']
        )
        
        messages = response.get('Messages', [])
        if messages:
            print(f'📬 Found {len(messages)} notification(s):')
            for i, msg in enumerate(messages, 1):
                print(f'\n--- Message {i} ---')
                body = json.loads(msg['Body'])
                print(f'Status: {body.get("status", "unknown")}')
                print(f'Pipeline: {body.get("pipeline", "unknown")}')
                print(f'RunId: {body.get("runId", "unknown")}')
                print(f'Timestamp: {body.get("timestamp", "unknown")}')
                
                if body.get('status') == 'FAILED':
                    error_details = body.get("errorDetails", {})
                    print(f'Failed Step: {error_details.get("failedStep", "unknown")}')
                    print(f'Error: {error_details.get("errorMessage", "unknown")}')
                    print(f'Retryable: {error_details.get("retryable", "unknown")}')
                elif body.get('status') == 'SUCCESS':
                    results = body.get("processingResults", {})
                    print(f'Chunks: {results.get("chunkCount", "unknown")}')
                    print(f'Text Length: {results.get("textLength", "unknown")}')
                    print(f'Processing Time: {results.get("processingTimeSeconds", "unknown")}s')
                    completion_info = body.get("completionInfo", {})
                    print(f'Pipeline Stage: {completion_info.get("pipelineStage", "unknown")}')
                    print(f'Search Ready: {completion_info.get("searchReady", "unknown")}')
                
                # Show document info
                doc_info = body.get("documentInfo", {})
                print(f'Document: s3://{doc_info.get("bucket", "unknown")}/{doc_info.get("key", "unknown")}')
                
                # Delete the message after reading (optional)
                # sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=msg['ReceiptHandle'])
        else:
            print('📭 No notifications found yet. Pipeline may still be running...')
    except Exception as e:
        print(f'❌ Error checking notifications: {e}')

if __name__ == '__main__':
    check_notifications() 