import boto3

stepfunctions = boto3.client('stepfunctions')

execution_arn = "arn:aws:states:us-east-1:702645448228:execution:StateMachineEtlStateMachine241248B6-nmg8xN9bET1J:6da52bb9-8b6f-4199-b22f-8c3ce6cedab5"

response = stepfunctions.describe_execution(executionArn=execution_arn)

print(f"🔍 Pipeline Execution Status")
print("=" * 50)
print(f"Status: {response['status']}")
print(f"Start Time: {response['startDate']}")

if response['status'] == 'FAILED':
    print(f"❌ Error: {response.get('error', 'Unknown')}")
    print(f"❌ Cause: {response.get('cause', 'Unknown')}")
elif response['status'] == 'SUCCEEDED':
    print(f"✅ End Time: {response['stopDate']}")
    print("✅ Pipeline completed successfully!")
    
    # Calculate duration
    duration = response['stopDate'] - response['startDate']
    print(f"⏱️ Total Duration: {duration}")
elif response['status'] == 'RUNNING':
    print("🔄 Pipeline is still running...")
else:
    print(f"📊 Current Status: {response['status']}")

print(f"\nRun ID: 7a79cc4b-a626-42d5-a099-a34039c01906") 