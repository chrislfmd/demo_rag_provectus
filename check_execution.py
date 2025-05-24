import boto3

stepfunctions = boto3.client('stepfunctions')

execution_arn = "arn:aws:states:us-east-1:702645448228:execution:StateMachineEtlStateMachine241248B6-nmg8xN9bET1J:86d279dc-0eff-4b9d-b606-1b4befde78af"

response = stepfunctions.describe_execution(executionArn=execution_arn)

print(f"Execution Status: {response['status']}")
if response['status'] == 'FAILED':
    print(f"Error: {response.get('error', 'Unknown')}")
    print(f"Cause: {response.get('cause', 'Unknown')}")
elif response['status'] == 'SUCCEEDED':
    print("✅ Pipeline completed successfully!")
    print("Now checking if email notification was sent...") 