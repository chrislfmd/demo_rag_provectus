#!/usr/bin/env python3
"""
View and analyze RAG pipeline execution logs from DynamoDB
"""

import boto3
import json
from datetime import datetime
from boto3.dynamodb.conditions import Key
import argparse

def format_timestamp(timestamp_str):
    """Format ISO timestamp for display"""
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
    except:
        return timestamp_str

def view_execution_logs(run_id=None, limit=20, show_details=False):
    """View execution logs from DynamoDB"""
    
    # Initialize DynamoDB
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('ExecLog')
    
    try:
        if run_id:
            # Get logs for specific run
            response = table.query(
                KeyConditionExpression=Key('runId').eq(run_id),
                ScanIndexForward=True  # Sort by timestamp ascending
            )
            items = response['Items']
            print(f"\n📄 Execution Logs for Run: {run_id}")
        else:
            # Scan all logs (limited)
            response = table.scan(Limit=limit)
            items = response['Items']
            
            # Sort by timestamp
            items.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            print(f"\n📊 Recent Execution Logs (Latest {len(items)} entries)")
        
        print("=" * 80)
        
        if not items:
            print("❌ No execution logs found")
            return
        
        # Group by runId for better organization
        runs = {}
        for item in items:
            run_id_key = item['runId']
            if run_id_key not in runs:
                runs[run_id_key] = []
            runs[run_id_key].append(item)
        
        # Display logs
        for run_id_key, run_logs in runs.items():
            print(f"\n🔄 Run ID: {run_id_key}")
            print("-" * 60)
            
            # Sort steps by timestamp
            run_logs.sort(key=lambda x: x.get('timestamp', ''))
            
            for log_entry in run_logs:
                timestamp = format_timestamp(log_entry.get('timestamp', 'Unknown'))
                step = log_entry.get('step', 'unknown')
                status = log_entry.get('status', 'UNKNOWN')
                
                # Status icon
                status_icon = {
                    'STARTED': '🚀',
                    'SUCCESS': '✅',
                    'FAILED': '❌',
                    'IN_PROGRESS': '⏳'
                }.get(status, '❓')
                
                print(f"  {status_icon} {timestamp} | {step:12} | {status}")
                
                # Show additional details if requested
                if show_details:
                    details = []
                    
                    if 'documentId' in log_entry:
                        details.append(f"Doc: {log_entry['documentId'][:8]}...")
                    
                    if 'textractJobId' in log_entry:
                        details.append(f"Job: {log_entry['textractJobId'][:8]}...")
                    
                    if 'chunkCount' in log_entry:
                        details.append(f"Chunks: {log_entry['chunkCount']}")
                    
                    if 'processingTime' in log_entry:
                        time_val = float(log_entry['processingTime'])
                        details.append(f"Time: {time_val:.2f}s")
                    
                    if 'error' in log_entry:
                        details.append(f"Error: {log_entry['error'][:50]}...")
                    
                    if details:
                        print(f"     └─ {' | '.join(details)}")
        
        # Summary statistics
        print(f"\n📊 SUMMARY:")
        print(f"   📄 Total Runs: {len(runs)}")
        print(f"   📝 Total Log Entries: {len(items)}")
        
        # Count statuses
        status_counts = {}
        for item in items:
            status = item.get('status', 'UNKNOWN')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print(f"   📈 Status Distribution:")
        for status, count in status_counts.items():
            icon = {
                'STARTED': '🚀',
                'SUCCESS': '✅',
                'FAILED': '❌',
                'IN_PROGRESS': '⏳'
            }.get(status, '❓')
            print(f"      {icon} {status}: {count}")
        
    except Exception as e:
        print(f"❌ Error viewing logs: {str(e)}")

def view_run_summary():
    """View summary of all runs"""
    
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('ExecLog')
    
    try:
        # Scan all logs
        response = table.scan()
        items = response['Items']
        
        print(f"\n🎯 RAG PIPELINE EXECUTION SUMMARY")
        print("=" * 60)
        
        if not items:
            print("❌ No execution logs found")
            return
        
        # Group by runId
        runs = {}
        for item in items:
            run_id = item['runId']
            if run_id not in runs:
                runs[run_id] = {
                    'steps': [],
                    'start_time': None,
                    'end_time': None,
                    'status': 'UNKNOWN',
                    'errors': []
                }
            
            runs[run_id]['steps'].append(item)
            
            # Track timing
            timestamp = item.get('timestamp')
            if timestamp:
                if not runs[run_id]['start_time'] or timestamp < runs[run_id]['start_time']:
                    runs[run_id]['start_time'] = timestamp
                if not runs[run_id]['end_time'] or timestamp > runs[run_id]['end_time']:
                    runs[run_id]['end_time'] = timestamp
            
            # Track status
            if item.get('status') == 'FAILED':
                runs[run_id]['status'] = 'FAILED'
                if 'error' in item:
                    runs[run_id]['errors'].append(item['error'])
            elif runs[run_id]['status'] != 'FAILED' and item.get('status') == 'SUCCESS':
                runs[run_id]['status'] = 'SUCCESS'
        
        # Display summary
        successful_runs = 0
        failed_runs = 0
        
        for run_id, run_data in runs.items():
            status = run_data['status']
            step_count = len(run_data['steps'])
            
            status_icon = '✅' if status == 'SUCCESS' else '❌' if status == 'FAILED' else '❓'
            
            print(f"\n{status_icon} Run: {run_id[:12]}...")
            print(f"   📅 Start: {format_timestamp(run_data['start_time']) if run_data['start_time'] else 'Unknown'}")
            print(f"   📊 Steps: {step_count}")
            print(f"   🎯 Status: {status}")
            
            if run_data['errors']:
                print(f"   ❌ Errors: {len(run_data['errors'])}")
                for error in run_data['errors'][:2]:  # Show first 2 errors
                    print(f"      └─ {error[:60]}...")
            
            if status == 'SUCCESS':
                successful_runs += 1
            elif status == 'FAILED':
                failed_runs += 1
        
        # Overall statistics
        total_runs = len(runs)
        success_rate = (successful_runs / total_runs * 100) if total_runs > 0 else 0
        
        print(f"\n🏆 OVERALL STATISTICS:")
        print(f"   📊 Total Runs: {total_runs}")
        print(f"   ✅ Successful: {successful_runs}")
        print(f"   ❌ Failed: {failed_runs}")
        print(f"   📈 Success Rate: {success_rate:.1f}%")
        
    except Exception as e:
        print(f"❌ Error viewing run summary: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='View RAG pipeline execution logs')
    parser.add_argument('--run-id', help='View logs for specific run ID')
    parser.add_argument('--limit', type=int, default=20, help='Limit number of log entries (default: 20)')
    parser.add_argument('--details', action='store_true', help='Show detailed information')
    parser.add_argument('--summary', action='store_true', help='Show run summary instead of logs')
    
    args = parser.parse_args()
    
    if args.summary:
        view_run_summary()
    else:
        view_execution_logs(args.run_id, args.limit, args.details)

if __name__ == "__main__":
    main() 