import boto3
from datetime import datetime, timedelta

logs = boto3.client('logs')

# Get logs from the last 10 minutes
end_time = datetime.now()
start_time = end_time - timedelta(minutes=10)

log_group = "/aws/lambda/RagDemoStack-NotificationsEmailForwarderFnEDBDF37A-PFk8ZU0K50uP"

try:
    response = logs.filter_log_events(
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