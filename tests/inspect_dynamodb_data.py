#!/usr/bin/env python3
"""
Script to inspect DynamoDB data in the RAG pipeline system.
Shows actual data being logged to both Documents and ExecLogV2 tables.
"""

import boto3
from boto3.dynamodb.conditions import Key, Attr
from datetime import datetime, timedelta
import json

def format_timestamp(timestamp_str):
    """Format timestamp for display"""
    try:
        if timestamp_str.endswith('Z'):
            dt = datetime.fromisoformat(timestamp_str[:-1])
        else:
            dt = datetime.fromisoformat(timestamp_str)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return timestamp_str

def inspect_documents_table():
    """Inspect the Documents table content"""
    print("\n" + "="*60)
    print("DOCUMENTS TABLE INSPECTION")
    print("="*60)
    
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('Documents')
        
        # Scan for recent items (limit to avoid costs)
        response = table.scan(Limit=20)
        items = response['Items']
        
        if not items:
            print("No items found in Documents table")
            return
            
        print(f"Found {len(items)} items (showing max 20)")
        
        # Group by documentId
        documents = {}
        for item in items:
            doc_id = item['documentId']
            if doc_id not in documents:
                documents[doc_id] = {'metadata': None, 'chunks': []}
            
            if item['chunkId'] == 'metadata':
                documents[doc_id]['metadata'] = item
            else:
                documents[doc_id]['chunks'].append(item)
        
        # Display each document
        for doc_id, doc_data in documents.items():
            print(f"\nDOCUMENT: {doc_id}")
            print("-" * 40)
            
            # Show metadata
            if doc_data['metadata']:
                meta = doc_data['metadata']
                print(f"  Filename: {meta.get('filename', 'Unknown')}")
                print(f"  Status: {meta.get('status', 'Unknown')}")
                print(f"  Created: {format_timestamp(meta.get('createdAt', ''))}")
                print(f"  Chunks: {meta.get('chunkCount', len(doc_data['chunks']))}")
                
                if 'metadata' in meta and isinstance(meta['metadata'], dict):
                    print(f"  S3 Location: s3://{meta['metadata'].get('bucket', '')}/{meta['metadata'].get('key', '')}")
            
            # Show chunk summary
            chunks = doc_data['chunks']
            if chunks:
                print(f"  \nCHUNK SUMMARY ({len(chunks)} chunks):")
                for i, chunk in enumerate(chunks):
                    content = chunk.get('content', '')
                    content_preview = content[:60] + "..." if len(content) > 60 else content
                    embedding_size = len(chunk.get('embedding', []))
                    print(f"    {chunk.get('chunkId', f'chunk_{i}')}: {content_preview}")
                    print(f"      Embedding: {embedding_size} dimensions")
                    
                    # Show metadata if available
                    chunk_meta = chunk.get('metadata', {})
                    if isinstance(chunk_meta, dict):
                        print(f"      Length: {chunk_meta.get('chunkLength', 'Unknown')} chars")
                        print(f"      Confidence: {chunk_meta.get('confidence', 'Unknown')}")
            
    except Exception as e:
        print(f"Error inspecting Documents table: {str(e)}")

def inspect_execlog_table():
    """Inspect the ExecLogV2 table content"""
    print("\n" + "="*60)  
    print("EXECLOGV2 TABLE INSPECTION")
    print("="*60)
    
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('ExecLogV2')
        
        # Get recent logs (last 24 hours)
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        cutoff_str = cutoff_time.isoformat()
        
        # Scan for recent items
        response = table.scan(
            FilterExpression=Attr('timestamp').gte(cutoff_str),
            Limit=50
        )
        items = response['Items']
        
        if not items:
            print("No recent execution logs found (last 24 hours)")
            return
            
        print(f"Found {len(items)} recent log entries")
        
        # Group by runId
        runs = {}
        for item in items:
            run_id = item['runId']
            if run_id not in runs:
                runs[run_id] = []
            runs[run_id].append(item)
        
        # Sort and display each run
        for run_id, logs in runs.items():
            # Sort logs by timestamp
            logs.sort(key=lambda x: x.get('timestamp', ''))
            
            print(f"\nPIPELINE RUN: {run_id}")
            print("-" * 50)
            
            # Determine overall status
            has_failed = any(log.get('status') == 'FAILED' for log in logs)
            last_step = logs[-1] if logs else None
            
            if has_failed:
                status = "FAILED"
            elif last_step and last_step.get('status') == 'SUCCESS':
                status = "COMPLETED"
            else:
                status = "IN_PROGRESS"
                
            print(f"  Overall Status: {status}")
            print(f"  Steps Logged: {len(logs)}")
            
            # Show document info if available
            doc_ids = set(log.get('documentId') for log in logs if log.get('documentId') != 'unknown')
            if doc_ids:
                print(f"  Document IDs: {', '.join(doc_ids)}")
            
            # Show step timeline
            print(f"  \nSTEP TIMELINE:")
            for log in logs:
                step = log.get('step', 'Unknown')
                status = log.get('status', 'Unknown')
                timestamp = format_timestamp(log.get('timestamp', ''))
                message = log.get('message', '')
                
                status_icon = {
                    'STARTED': '▶',
                    'SUCCESS': '✓',
                    'FAILED': '✗'
                }.get(status, '?')
                
                print(f"    {status_icon} {timestamp} - {step}: {status}")
                if message and len(message) < 100:
                    print(f"      {message}")
                elif message:
                    print(f"      {message[:97]}...")
            
            # Show any error details
            failed_logs = [log for log in logs if log.get('status') == 'FAILED']
            if failed_logs:
                print(f"  \nERROR DETAILS:")
                for log in failed_logs:
                    print(f"    Step: {log.get('step')}")
                    print(f"    Message: {log.get('message', 'No error message')}")
    
    except Exception as e:
        print(f"Error inspecting ExecLogV2 table: {str(e)}")

def show_table_info():
    """Show basic table information"""
    print("RAG PIPELINE DYNAMODB INSPECTION")
    print("="*60)
    print("This script shows actual data stored in your DynamoDB tables:")
    print("  • Documents table: Document content, chunks, and embeddings")
    print("  • ExecLogV2 table: Pipeline execution logs and debugging info")
    print("\nTables inspected:")
    
    try:
        dynamodb = boto3.resource('dynamodb')
        
        # Check Documents table
        try:
            docs_table = dynamodb.Table('Documents')
            docs_response = docs_table.describe_table()
            item_count = docs_response['Table'].get('ItemCount', 'Unknown')
            print(f"  • Documents: {item_count} items")
        except Exception as e:
            print(f"  • Documents: Error accessing table - {str(e)}")
        
        # Check ExecLogV2 table  
        try:
            exec_table = dynamodb.Table('ExecLogV2')
            exec_response = exec_table.describe_table()
            item_count = exec_response['Table'].get('ItemCount', 'Unknown')
            print(f"  • ExecLogV2: {item_count} items")
        except Exception as e:
            print(f"  • ExecLogV2: Error accessing table - {str(e)}")
            
    except Exception as e:
        print(f"Error accessing DynamoDB: {str(e)}")

def main():
    """Main inspection function"""
    show_table_info()
    
    # Inspect both tables
    inspect_documents_table()
    inspect_execlog_table()
    
    print(f"\n" + "="*60)
    print("INSPECTION COMPLETE")
    print("="*60)
    print("Key points:")
    print("• Documents table stores your actual document content and embeddings")
    print("• ExecLogV2 table tracks pipeline execution for debugging")
    print("• Logs automatically expire after 30 days")
    print("• Document content persists until manually deleted")

if __name__ == "__main__":
    main() 