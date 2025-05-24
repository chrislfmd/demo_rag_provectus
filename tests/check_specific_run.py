#!/usr/bin/env python3
"""
Check ExecLog table for a specific run ID
"""
import boto3
import json
from boto3.dynamodb.conditions import Key

def check_run_logs(run_id):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('ExecLogV2')
    
    try:
        # Query for specific run ID
        response = table.query(
            KeyConditionExpression=Key('runId').eq(run_id)
        )
        
        items = response.get('Items', [])
        
        print(f"📊 Found {len(items)} log entries for run: {run_id}")
        print("=" * 80)
        
        if not items:
            print("❌ No log entries found for this run")
            return
        
        # Sort by timestamp
        items.sort(key=lambda x: x.get('timestamp', ''))
        
        for item in items:
            timestamp = item.get('timestamp', 'Unknown')
            step = item.get('step', 'Unknown')
            status = item.get('status', 'Unknown')
            message = item.get('message', '')
            document_id = item.get('documentId', 'Unknown')
            step_timestamp = item.get('stepTimestamp', 'Unknown')
            
            status_icon = "✅" if status == "SUCCESS" else "❌" if status == "FAILED" else "🔄"
            
            print(f"{status_icon} {timestamp} | {step:12} | {status}")
            print(f"   Document ID: {document_id}")
            print(f"   Step Timestamp: {step_timestamp}")
            if message:
                print(f"   Message: {message}")
            print("-" * 60)
            
    except Exception as e:
        print(f"❌ Error checking run logs: {str(e)}")

def scan_all_recent_logs():
    """Scan all recent logs to debug the issue"""
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('ExecLogV2')
    
    try:
        print("\n🔍 Scanning all recent logs in ExecLogV2 table:")
        print("=" * 80)
        
        # Scan the table (limited to recent entries)
        response = table.scan(Limit=50)
        items = response.get('Items', [])
        
        # Sort by timestamp
        items.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        print(f"📊 Found {len(items)} total log entries (latest 50)")
        
        # Group by runId
        runs = {}
        for item in items:
            run_id = item.get('runId', 'unknown')
            if run_id not in runs:
                runs[run_id] = []
            runs[run_id].append(item)
        
        # Show recent runs
        for run_id, run_items in list(runs.items())[:5]:  # Show latest 5 runs
            print(f"\n🔄 Run ID: {run_id}")
            print("-" * 40)
            
            run_items.sort(key=lambda x: x.get('timestamp', ''))
            
            for item in run_items:
                timestamp = item.get('timestamp', 'Unknown')
                step = item.get('step', 'Unknown')
                status = item.get('status', 'Unknown')
                
                status_icon = "✅" if status == "SUCCESS" else "❌" if status == "FAILED" else "🔄"
                print(f"  {status_icon} {timestamp} | {step:12} | {status}")
        
    except Exception as e:
        print(f"❌ Error scanning logs: {str(e)}")

def check_document_created(document_id):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('Documents')
    
    try:
        # Query for document
        response = table.query(
            KeyConditionExpression=Key('documentId').eq(document_id)
        )
        
        items = response.get('Items', [])
        print(f"\n📄 Found {len(items)} document items for: {document_id}")
        
        if items:
            for item in items:
                chunk_id = item.get('chunkId', 'Unknown')
                if chunk_id == 'metadata':
                    print(f"   📋 Metadata: {item.get('status')} | {item.get('filename')}")
                else:
                    content = item.get('content', '')
                    print(f"   📝 Chunk {chunk_id}: {content[:50]}...")
        
    except Exception as e:
        print(f"❌ Error checking document: {str(e)}")

if __name__ == "__main__":
    # Check our latest test run from pipeline
    run_id = "4b7a070e-d4bb-45db-bca6-09f2b8f4ea08"  # Updated to latest test run
    print(f"🔍 Checking logs for pipeline run: {run_id}")
    check_run_logs(run_id)
    
    # Scan all recent logs to debug
    scan_all_recent_logs()
    
    # Check if document was created - we need to extract it from the pipeline output
    # Based on our pipeline output, the document ID was: 07831d44-33b3-4116-915e-8b210c21cb7c
    document_id = "07831d44-33b3-4116-915e-8b210c21cb7c"  # Updated to latest document ID
    check_document_created(document_id)
    
    print(f"\n🔍 Also checking logs for the test run ID: {run_id}")
    check_run_logs(run_id) 