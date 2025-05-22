import boto3
import json
import time

def configure_resources():
    # Configure S3 notifications
    s3 = boto3.client('s3')
    lambda_client = boto3.client('lambda')
    
    # Get function ARN
    trigger_function = lambda_client.get_function(
        FunctionName='RagDemoStack-TriggerFnDEDD2D87-YG3bmTMlrAqZ'
    )
    function_arn = trigger_function['Configuration']['FunctionArn']
    
    # Add S3 notification
    s3.put_bucket_notification_configuration(
        Bucket='rag-demo-raw-pdf-v2',
        NotificationConfiguration={
            'LambdaFunctionConfigurations': [
                {
                    'LambdaFunctionArn': function_arn,
                    'Events': ['s3:ObjectCreated:*'],
                    'Filter': {
                        'Key': {
                            'FilterRules': [
                                {
                                    'Name': 'prefix',
                                    'Value': 'incoming/'
                                }
                            ]
                        }
                    }
                }
            ]
        }
    )
    
    print("Successfully configured S3 notifications")
    
    # Enable Data API for Aurora cluster
    rds = boto3.client('rds')
    
    # Get cluster identifier
    clusters = rds.describe_db_clusters()
    cluster_id = None
    for cluster in clusters['DBClusters']:
        if 'ragdemostack-storagevectorcluster' in cluster['DBClusterIdentifier'].lower():
            cluster_id = cluster['DBClusterIdentifier']
            break
    
    if cluster_id:
        print(f"Enabling Data API for cluster {cluster_id}")
        rds.modify_db_cluster(
            DBClusterIdentifier=cluster_id,
            EnableHttpEndpoint=True,
            ApplyImmediately=True
        )
        
        # Wait for the modification to complete with timeout
        print("Waiting for Data API to be enabled...")
        max_retries = 12  # 2 minutes total
        retry_count = 0
        while retry_count < max_retries:
            response = rds.describe_db_clusters(DBClusterIdentifier=cluster_id)
            if response['DBClusters'][0]['HttpEndpointEnabled']:
                print("Data API enabled successfully")
                break
            retry_count += 1
            if retry_count == max_retries:
                print("Warning: Timed out waiting for Data API to be enabled. Please check the AWS Console.")
                break
            time.sleep(10)
    
    print("Post-deployment configuration completed successfully")

if __name__ == '__main__':
    configure_resources() 