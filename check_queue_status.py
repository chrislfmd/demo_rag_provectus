import boto3

sqs = boto3.client('sqs')

# Get all RAG pipeline queues
response = sqs.list_queues(QueueNamePrefix='rag-pipeline')
queue_urls = response.get('QueueUrls', [])

print("RAG Pipeline Queue Status:")
print("=" * 50)

for queue_url in queue_urls:
    queue_name = queue_url.split('/')[-1]
    
    # Get queue attributes
    attrs = sqs.get_queue_attributes(
        QueueUrl=queue_url,
        AttributeNames=['ApproximateNumberOfMessages', 'ApproximateNumberOfMessagesNotVisible']
    )
    
    visible_messages = attrs['Attributes'].get('ApproximateNumberOfMessages', '0')
    invisible_messages = attrs['Attributes'].get('ApproximateNumberOfMessagesNotVisible', '0')
    
    print(f"{queue_name}:")
    print(f"  Visible messages: {visible_messages}")
    print(f"  Processing messages: {invisible_messages}")
    print() 