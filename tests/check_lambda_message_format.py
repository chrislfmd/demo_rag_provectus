import boto3
from datetime import datetime, timedelta

print("🔍 LAMBDA MESSAGE FORMAT ANALYSIS")
print("=" * 60)

logs = boto3.client('logs')

# Get logs from the last 15 minutes to capture our test
end_time = datetime.now()
start_time = end_time - timedelta(minutes=15)

log_group = "/aws/lambda/RagDemoStack-NotificationsEmailForwarderFnEDBDF37A-PFk8ZU0K50uP"

try:
    response = logs.filter_log_events(
        logGroupName=log_group,
        startTime=int(start_time.timestamp() * 1000),
        endTime=int(end_time.timestamp() * 1000),
        filterPattern="Processing"  # Find the message processing logs
    )
    
    events = response.get('events', [])
    print(f"Found {len(events)} processing events:")
    
    for event in events:
        timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
        message = event['message']
        print(f"\n[{timestamp}] {message}")
        
        # Also look for any error messages around the same time
        error_response = logs.filter_log_events(
            logGroupName=log_group,
            startTime=event['timestamp'] - 5000,  # 5 seconds before
            endTime=event['timestamp'] + 5000,    # 5 seconds after
            filterPattern="ERROR"
        )
        
        for error_event in error_response.get('events', []):
            error_timestamp = datetime.fromtimestamp(error_event['timestamp'] / 1000)
            print(f"   ❌ ERROR [{error_timestamp}]: {error_event['message']}")

    # Let's also look for all recent events to see the full picture
    print(f"\n📋 ALL RECENT LAMBDA EVENTS:")
    all_events = logs.filter_log_events(
        logGroupName=log_group,
        startTime=int(start_time.timestamp() * 1000),
        endTime=int(end_time.timestamp() * 1000)
    )
    
    for event in all_events.get('events', [])[-20:]:  # Last 20 events
        timestamp = datetime.fromtimestamp(event['timestamp'] / 1000)
        message = event['message'].strip()
        if any(keyword in message for keyword in ['ERROR', 'Processing', 'Sent email', 'exception', 'failed']):
            print(f"   [{timestamp}] {message}")
            
except Exception as e:
    print(f"Error retrieving logs: {e}")

print(f"\n🤔 POSSIBLE ISSUES:")
print(f"   1. Lambda might be throwing an exception after 'Processing' log")
print(f"   2. Message format might be causing SNS to reject it silently")
print(f"   3. Email might be going to spam/junk folder")
print(f"   4. SNS delivery might be delayed")

print(f"\n✅ VERIFICATION STEPS:")
print(f"   1. Check if you received the direct test email")
print(f"   2. Look for any ERROR logs above")
print(f"   3. Check spam/junk folder thoroughly") 