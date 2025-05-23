#!/usr/bin/env python3
"""
Monitor SQS notifications from the RAG pipeline
"""

import boto3
import json
import time
from datetime import datetime
import argparse

def format_timestamp(timestamp_str):
    """Format ISO timestamp for display"""
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
    except:
        return timestamp_str

def monitor_queue(queue_url, queue_name, max_messages=10, wait_time=20):
    """Monitor a specific SQS queue for messages"""
    
    sqs = boto3.client('sqs')
    
    print(f"\n📡 Monitoring {queue_name} Queue")
    print(f"🔗 URL: {queue_url}")
    print(f"⏰ Polling every {wait_time} seconds...")
    print("=" * 60)
    
    messages_received = 0
    
    try:
        while messages_received < max_messages:
            # Poll for messages
            response = sqs.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=wait_time,
                MessageAttributeNames=['All']
            )
            
            messages = response.get('Messages', [])
            
            if not messages:
                print(f"⏳ No messages received (checked at {datetime.now().strftime('%H:%M:%S')})")
                continue
            
            for message in messages:
                messages_received += 1
                
                # Parse message
                try:
                    body = json.loads(message['Body'])
                    
                    # Extract key information
                    status = body.get('status', 'UNKNOWN')
                    run_id = body.get('runId', 'unknown')
                    timestamp = body.get('timestamp', datetime.now().isoformat())
                    document_info = body.get('documentInfo', {})
                    
                    # Status icon
                    status_icon = {
                        'SUCCESS': '✅',
                        'FAILED': '❌',
                        'UNKNOWN': '❓'
                    }.get(status, '❓')
                    
                    print(f"\n{status_icon} NOTIFICATION #{messages_received}")
                    print(f"   🕐 Time: {format_timestamp(timestamp)}")
                    print(f"   🆔 Run ID: {run_id[:12]}...")
                    print(f"   📊 Status: {status}")
                    
                    if document_info:
                        print(f"   📄 Document: {document_info.get('key', 'unknown')}")
                        if document_info.get('documentId'):
                            print(f"   🔑 Doc ID: {document_info['documentId'][:12]}...")
                    
                    # Show success metrics
                    if status == 'SUCCESS' and 'processingResults' in body:
                        results = body['processingResults']
                        if 'successMetrics' in body:
                            metrics = body['successMetrics']
                            print(f"   📈 Success Metrics:")
                            print(f"      📝 Chunks: {metrics.get('chunksCreated', 0)}")
                            print(f"      ⏱️  Time: {metrics.get('processingTimeSeconds', 0):.2f}s")
                            print(f"      📏 Size: {metrics.get('documentSize', 0)} chars")
                        else:
                            print(f"   📈 Processing Results:")
                            print(f"      📝 Chunks: {results.get('chunkCount', 0)}")
                            print(f"      📏 Text Length: {results.get('textLength', 0)}")
                    
                    # Show error details
                    if status == 'FAILED':
                        if 'error' in body:
                            print(f"   ❌ Error: {body['error']}")
                        if 'errorDetails' in body:
                            details = body['errorDetails']
                            print(f"   🔍 Error Details:")
                            print(f"      🎯 Failed Step: {details.get('failedStep', 'unknown')}")
                            print(f"      💬 Message: {details.get('errorMessage', 'Unknown')}")
                            print(f"      🔄 Retryable: {details.get('retryable', False)}")
                    
                    # Show message attributes
                    attributes = message.get('MessageAttributes', {})
                    if attributes:
                        print(f"   🏷️  Message Attributes:")
                        for key, value in attributes.items():
                            print(f"      {key}: {value.get('StringValue', 'N/A')}")
                    
                except json.JSONDecodeError:
                    print(f"\n❌ Invalid JSON message received:")
                    print(f"   {message['Body'][:100]}...")
                except Exception as e:
                    print(f"\n❌ Error processing message: {str(e)}")
                
                # Delete message after processing
                try:
                    sqs.delete_message(
                        QueueUrl=queue_url,
                        ReceiptHandle=message['ReceiptHandle']
                    )
                except Exception as e:
                    print(f"⚠️ Failed to delete message: {str(e)}")
            
            if messages_received >= max_messages:
                print(f"\n🏁 Reached maximum message limit ({max_messages})")
                break
                
    except KeyboardInterrupt:
        print(f"\n\n⏹️  Monitoring stopped by user")
    except Exception as e:
        print(f"\n❌ Error monitoring queue: {str(e)}")
    
    print(f"\n📊 Total messages processed: {messages_received}")

def list_queues():
    """List all RAG pipeline SQS queues"""
    
    sqs = boto3.client('sqs')
    
    try:
        response = sqs.list_queues(QueueNamePrefix='rag-pipeline')
        queues = response.get('QueueUrls', [])
        
        print(f"\n📋 RAG Pipeline SQS Queues:")
        print("=" * 50)
        
        if not queues:
            print("❌ No RAG pipeline queues found")
            return {}
        
        queue_map = {}
        for i, queue_url in enumerate(queues, 1):
            queue_name = queue_url.split('/')[-1]
            queue_map[str(i)] = {'url': queue_url, 'name': queue_name}
            print(f"  {i}. {queue_name}")
            print(f"     🔗 {queue_url}")
        
        return queue_map
        
    except Exception as e:
        print(f"❌ Error listing queues: {str(e)}")
        return {}

def main():
    parser = argparse.ArgumentParser(description='Monitor RAG pipeline SQS notifications')
    parser.add_argument('--queue', help='Specific queue name to monitor')
    parser.add_argument('--max-messages', type=int, default=10, help='Maximum messages to process (default: 10)')
    parser.add_argument('--wait-time', type=int, default=20, help='Polling wait time in seconds (default: 20)')
    parser.add_argument('--list', action='store_true', help='List available queues')
    
    args = parser.parse_args()
    
    if args.list:
        list_queues()
        return
    
    # Get available queues
    queue_map = list_queues()
    
    if not queue_map:
        return
    
    if args.queue:
        # Find specific queue
        target_queue = None
        for queue_info in queue_map.values():
            if args.queue.lower() in queue_info['name'].lower():
                target_queue = queue_info
                break
        
        if not target_queue:
            print(f"❌ Queue '{args.queue}' not found")
            return
    else:
        # Interactive selection
        print(f"\n🎯 Select a queue to monitor:")
        choice = input("Enter queue number (or 'all' for main queue): ").strip()
        
        if choice.lower() == 'all':
            # Default to main notification queue
            target_queue = None
            for queue_info in queue_map.values():
                if 'notifications' in queue_info['name'] and 'dlq' not in queue_info['name']:
                    target_queue = queue_info
                    break
        elif choice in queue_map:
            target_queue = queue_map[choice]
        else:
            print("❌ Invalid selection")
            return
    
    if not target_queue:
        print("❌ No suitable queue found")
        return
    
    # Monitor the selected queue
    monitor_queue(
        target_queue['url'], 
        target_queue['name'], 
        args.max_messages, 
        args.wait_time
    )

if __name__ == "__main__":
    main() 