#!/usr/bin/env python3
"""
Check CloudWatch logs for Lambda functions to debug logging issues
"""
import boto3
import json
from datetime import datetime, timedelta

def check_lambda_logs(function_name_pattern, run_id=None):
    """Check CloudWatch logs for Lambda functions"""
    logs_client = boto3.client('logs')
    lambda_client = boto3.client('lambda')
    
    # Find Lambda functions matching pattern
    functions = lambda_client.list_functions()
    matching_functions = [f for f in functions['Functions'] if function_name_pattern in f['FunctionName']]
    
    if not matching_functions:
        print(f"❌ No Lambda functions found matching pattern: {function_name_pattern}")
        return
    
    for func in matching_functions:
        function_name = func['FunctionName']
        log_group_name = f"/aws/lambda/{function_name}"
        
        print(f"\n🔍 Checking logs for: {function_name}")
        print("=" * 60)
        
        try:
            # Get recent log streams
            streams_response = logs_client.describe_log_streams(
                logGroupName=log_group_name,
                orderBy='LastEventTime',
                descending=True,
                limit=5  # Check more streams
            )
            
            if not streams_response['logStreams']:
                print("❌ No log streams found")
                continue
            
            # Check multiple recent streams
            for i, stream in enumerate(streams_response['logStreams'][:3]):
                stream_name = stream['logStreamName']
                
                print(f"📄 Stream {i+1}: {stream_name}")
                
                # Get recent log events
                start_time = int((datetime.now() - timedelta(hours=1)).timestamp() * 1000)
                
                events_response = logs_client.get_log_events(
                    logGroupName=log_group_name,
                    logStreamName=stream_name,
                    startTime=start_time
                )
                
                events = events_response['events']
                
                if not events:
                    print("   ❌ No recent log events found")
                    continue
                
                print(f"   📊 Found {len(events)} recent log events")
                
                # Filter events by run_id if provided
                relevant_events = []
                for event in events:
                    message = event['message']
                    if run_id and run_id in message:
                        relevant_events.append(event)
                    elif not run_id and any(keyword in message.lower() for keyword in ['error', 'failed', 'exception', 'logged to dynamodb', 'exec_log_table']):
                        relevant_events.append(event)
                
                if run_id and not relevant_events:
                    print(f"   ❌ No events found for run_id: {run_id}")
                    # Show recent events anyway
                    print("   📝 Recent events (last 3):")
                    for event in events[-3:]:
                        timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                        print(f"      {timestamp}: {event['message'][:80]}...")
                else:
                    for event in relevant_events:
                        timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
                        message = event['message'].strip()
                        
                        # Highlight important messages
                        if "EXEC_LOG_TABLE" in message:
                            print(f"   🚨 {timestamp}: {message}")
                        elif "Logged to DynamoDB" in message:
                            print(f"   ✅ {timestamp}: {message}")
                        elif "Failed to log to DynamoDB" in message:
                            print(f"   ❌ {timestamp}: {message}")
                        elif "error" in message.lower() or "exception" in message.lower():
                            print(f"   🚨 {timestamp}: {message}")
                        elif run_id and run_id in message:
                            print(f"   📝 {timestamp}: {message}")
                        elif not run_id:
                            print(f"   📝 {timestamp}: {message[:100]}...")
                
                if relevant_events:
                    break  # Found relevant events, no need to check more streams
                        
        except Exception as e:
            print(f"❌ Error checking logs: {str(e)}")

if __name__ == "__main__":
    # Check logs for our latest run
    run_id = "b759bfbc-1193-4217-ab92-8e2ebb185ea0"
    
    print(f"🔍 Checking Lambda logs for run: {run_id}")
    
    # Check each Lambda function
    lambda_patterns = ["InitDbFn", "ValidateFn", "EmbedFn", "LoadFn", "NotifyFn"]
    
    for pattern in lambda_patterns:
        check_lambda_logs(pattern, run_id)
    
    print(f"\n🔍 Also checking for general errors in all Lambda functions:")
    for pattern in lambda_patterns:
        check_lambda_logs(pattern, None)  # Check for any errors

    # Get logs from the last 10 minutes
    end_time = datetime.now()
    start_time = end_time - timedelta(minutes=10)

    log_group = "/aws/lambda/RagDemoStack-NotificationsEmailForwarderFnEDBDF37A-PFk8ZU0K50uP"

    try:
        response = boto3.client('logs').filter_log_events(
            logGroupName=log_group,
            startTime=int(start_time.timestamp() * 1000),
            endTime=int(end_time.timestamp() * 1000)
        )
        
        events = response.get('events', [])
        print(f"Found {len(events)} log events in the last 10 minutes:")
        print("=" * 60)
        
        for event in events[-10:]:  # Show last 10 events
            timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
            print(f"[{timestamp}] {event['message']}")
            
    except Exception as e:
        print(f"Error retrieving logs: {e}")
        print("This might be because the Lambda hasn't been invoked recently or logs are still propagating.") 