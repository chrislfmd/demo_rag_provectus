import boto3
import json

print("🔍 EMAIL DELIVERY DEBUGGING")
print("=" * 60)

# Check SNS topic and subscription status
sns = boto3.client('sns')

# List all SNS topics
topics_response = sns.list_topics()
rag_topics = [t for t in topics_response['Topics'] if 'rag-pipeline' in t['TopicArn']]

print("📡 SNS TOPICS:")
for topic in rag_topics:
    topic_arn = topic['TopicArn']
    topic_name = topic_arn.split(':')[-1]
    print(f"   Topic: {topic_name}")
    print(f"   ARN: {topic_arn}")
    
    # Get subscriptions for this topic
    subs_response = sns.list_subscriptions_by_topic(TopicArn=topic_arn)
    subscriptions = subs_response['Subscriptions']
    
    print(f"   Subscriptions ({len(subscriptions)}):")
    for sub in subscriptions:
        print(f"     - Protocol: {sub['Protocol']}")
        print(f"       Endpoint: {sub['Endpoint']}")
        print(f"       Status: {sub['SubscriptionArn']}")
        if sub['SubscriptionArn'] == 'PendingConfirmation':
            print("       ⚠️  EMAIL SUBSCRIPTION NOT CONFIRMED!")
        elif 'arn:aws:sns' in str(sub['SubscriptionArn']):
            print("       ✅ Email subscription confirmed")
    print()

# Test direct SNS delivery
print("🧪 TESTING DIRECT SNS EMAIL DELIVERY:")
notification_topic_arn = None
for topic in rag_topics:
    if 'notifications' in topic['TopicArn'] and 'error' not in topic['TopicArn']:
        notification_topic_arn = topic['TopicArn']
        break

if notification_topic_arn:
    try:
        test_response = sns.publish(
            TopicArn=notification_topic_arn,
            Subject="🧪 Test Email from RAG Pipeline Debug",
            Message="""This is a direct test email to verify SNS email delivery is working.

If you receive this email, then SNS delivery is working correctly.
The issue might be with the message format from the Lambda function.

Time: Right now
Source: Manual debug test"""
        )
        print(f"   ✅ Direct test email sent successfully!")
        print(f"   📧 SNS Message ID: {test_response['MessageId']}")
        print(f"   ⏰ You should receive this test email within 1-5 minutes")
    except Exception as e:
        print(f"   ❌ Failed to send test email: {str(e)}")
else:
    print("   ❌ Could not find notification topic")

print(f"\n🔍 NEXT STEPS:")
print(f"   1. Check your email for the direct test message")
print(f"   2. If you get the test email, the issue is with Lambda message format")
print(f"   3. If no test email arrives, there's an SNS configuration issue")
print(f"   4. Check spam/junk folder too!") 