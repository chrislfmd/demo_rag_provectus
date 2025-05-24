import boto3
import json

sqs = boto3.client('sqs')

# Get DLQ URL
response = sqs.list_queues(QueueNamePrefix='rag-pipeline-notifications-dlq')
dlq_url = response['QueueUrls'][0]

print("Dead Letter Queue Messages:")
print("=" * 50)

# Receive a few messages from DLQ (without deleting them)
response = sqs.receive_message(
    QueueUrl=dlq_url,
    MaxNumberOfMessages=3,
    WaitTimeSeconds=1
)

messages = response.get('Messages', [])
print(f"Found {len(messages)} messages in DLQ")

for i, message in enumerate(messages, 1):
    print(f"\nMessage {i}:")
    print(f"Receipt Handle: {message['ReceiptHandle'][:50]}...")
    
    try:
        body = json.loads(message['Body'])
        print(f"Message Body (formatted):")
        print(json.dumps(body, indent=2))
    except json.JSONDecodeError:
        print(f"Raw Body: {message['Body']}")
    
    # Check for error attributes
    if 'Attributes' in message:
        print(f"Attributes: {message['Attributes']}") 