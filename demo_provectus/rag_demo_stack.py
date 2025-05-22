"""
AWS CDK Stack implementing a Retrieval-Augmented Generation (RAG) pipeline with the following components:

Architecture Overview:
--------------------
1. PDF Ingestion: S3 bucket with trigger for new PDF uploads
2. Text Extraction: AWS Textract for PDF processing
3. Validation: Custom validation of extracted text
4. Embedding Generation: Using Amazon Bedrock for text embeddings
5. Vector Storage: pgvector in Aurora PostgreSQL
6. Execution Logging: DynamoDB for pipeline execution tracking
7. Error Handling: SNS notifications for pipeline failures

Security Features:
----------------
- KMS encryption for data at rest
- VPC isolation for database
- IAM roles with least privilege
- S3 bucket policies
- Private subnets for compute resources

Flow:
----
1. User uploads PDF to S3 'incoming/' folder
2. S3 event triggers Lambda
3. Lambda starts Step Functions execution
4. Step Functions orchestrates the pipeline:
   - Textract PDF analysis
   - Validation of extracted text
   - Generate embeddings
   - Store vectors in pgvector
   - Log execution details
"""

from aws_cdk import (
    Stack, Duration, RemovalPolicy,
    Tags,
    aws_s3 as s3,
    aws_kms as kms,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_rds as rds,
    aws_ec2 as ec2,
    aws_secretsmanager as sm,
    aws_sns as sns,
    Environment,
    aws_dynamodb as dynamodb,
    aws_s3_notifications as s3n,
)
from constructs import Construct


class RagDemoStack(Stack):
    """End‑to‑end demo stack: KMS + S3 → Textract → Validate → Embed → Load(pgvector)"""

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # ──────────────────────────
        # 1. Encryption key
        # ──────────────────────────
        # Create KMS key for encrypting all data at rest
        # Used by: S3, DynamoDB, SNS, RDS
        data_key = kms.Key(
            self, "DataKey",
            alias="alias/ragDemoKms",
            enable_key_rotation=True,
            description="CMK for RAG demo data",
        )

        # Grant Textract service permissions to use KMS key
        # Required for: Reading encrypted S3 objects and writing results
        data_key.add_to_resource_policy(
            iam.PolicyStatement(
                actions=[
                    "kms:Decrypt",
                    "kms:GenerateDataKey",
                    "kms:Encrypt",
                    "kms:ReEncrypt*",
                    "kms:DescribeKey"
                ],
                principals=[iam.ServicePrincipal("textract.amazonaws.com")],
                resources=["*"]
            )
        )

        # Additional explicit grant for Textract service
        data_key.grant_encrypt_decrypt(iam.ServicePrincipal("textract.amazonaws.com"))

        # ──────────────────────────
        # 2. S3 Buckets
        # ──────────────────────────
        # Raw PDF bucket - Stores incoming PDF documents
        # - KMS encryption
        # - No public access
        # - Auto-cleanup for development
        raw_bucket = s3.Bucket(
            self, "RawPdfBucket",
            bucket_name="rag-demo-raw-pdf-v2",
            encryption=s3.BucketEncryption.KMS,
            encryption_key=data_key,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # Grant Textract read access to raw PDFs
        raw_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                actions=["s3:GetObject"],
                principals=[iam.ServicePrincipal("textract.amazonaws.com")],
                resources=[raw_bucket.arn_for_objects("*")]
            )
        )

        # Textract output bucket - Stores JSON results from Textract
        textract_bucket = s3.Bucket(
            self, "TextractJsonBucket",
            bucket_name="rag-demo-textract-json-v2",
            encryption=s3.BucketEncryption.KMS,
            encryption_key=data_key,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # Grant Textract write access for results
        textract_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                actions=["s3:PutObject"],
                principals=[iam.ServicePrincipal("textract.amazonaws.com")],
                resources=[textract_bucket.arn_for_objects("*")]
            )
        )

        # Add project tags to buckets
        for b in (raw_bucket, textract_bucket):
            Tags.of(b).add("project", "rag-demo")
            Tags.of(b).add("env", "dev")

        # ──────────────────────────
        # 3. VPC & Aurora pgvector
        # ──────────────────────────
        # Create VPC with public and private subnets
        # - 2 AZs for high availability
        # - NAT Gateway for private subnet internet access
        vpc = ec2.Vpc(
            self, "RagDemoVpc",
            max_azs=2,
            nat_gateway_provider=ec2.NatProvider.instance(
                instance_type=ec2.InstanceType("t3.micro"),
                machine_image=ec2.AmazonLinuxImage(
                    generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2
                )
            ),
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24
                )
            ]
        )

        # Database credentials in Secrets Manager
        db_secret = rds.Credentials.from_generated_secret(
            secret_name="ragDemoDbSecret",
            username="pgadmin",
        )

        # Aurora PostgreSQL cluster with pgvector extension
        # - Serverless v2 for cost optimization
        # - Placed in private subnets
        cluster = rds.DatabaseCluster(
            self,
            "VectorCluster",
            engine=rds.DatabaseClusterEngine.aurora_postgres(
                version=rds.AuroraPostgresEngineVersion.VER_15_3
            ),
            writer=rds.ClusterInstance.serverless_v2(
                "Writer",
                auto_minor_version_upgrade=True,
                instance_identifier="writer"
            ),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            credentials=db_secret,
            default_database_name="ragdemo",
            removal_policy=RemovalPolicy.DESTROY,  # DEV ONLY
        )

        # ──────────────────────────
        # 4. Shared Lambda Role
        # ──────────────────────────
        # IAM role used by all Lambda functions with permissions for:
        # - CloudWatch Logs
        # - VPC access
        # - Step Functions
        # - Textract
        # - KMS
        # - S3
        fn_role = iam.Role(
            self,
            "DemoLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            inline_policies={
                "CloudWatchLogs": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
                            resources=["*"],
                        )
                    ]
                ),
                "VpcAccess": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                "ec2:CreateNetworkInterface",
                                "ec2:DescribeNetworkInterfaces",
                                "ec2:DeleteNetworkInterface",
                                "ec2:AssignPrivateIpAddresses",
                                "ec2:UnassignPrivateIpAddresses"
                            ],
                            resources=["*"],
                        )
                    ]
                ),
                "StepFunctions": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                "states:ListStateMachines",
                                "states:StartExecution"
                            ],
                            resources=["*"],
                        )
                    ]
                ),
                "Textract": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                "textract:StartDocumentAnalysis",
                                "textract:GetDocumentAnalysis"
                            ],
                            resources=["*"],
                        )
                    ]
                )
            },
        )
        data_key.grant_encrypt_decrypt(fn_role)
        raw_bucket.grant_read(fn_role)
        textract_bucket.grant_read_write(fn_role)

        # ──────────────────────────
        # 5. Lambda Functions
        # ──────────────────────────
        # Validate Function:
        # - Validates Textract output
        # - Checks for empty/invalid text blocks
        validate_fn = _lambda.Function(
            self,
            "ValidateFn",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handler.handler",
            code=_lambda.Code.from_asset("lambdas/validate"),
            role=fn_role,
            timeout=Duration.seconds(60),
            memory_size=256,
        )

        # Embed Function:
        # - Generates embeddings using Amazon Bedrock
        # - Processes validated text blocks
        embed_fn = _lambda.Function(
            self,
            "EmbedFn",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handler.handler",
            code=_lambda.Code.from_asset("lambdas/embed"),
            role=fn_role,
            timeout=Duration.seconds(90),
            memory_size=512,
            environment={},
        )
        embed_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=["bedrock:InvokeModel"], resources=["*"]
            )
        )

        # Load Function:
        # - Stores embeddings in pgvector
        # - Uses RDS Data API
        secret = sm.Secret.from_secret_name_v2(
            self, "DbSecret",
            secret_name=db_secret.secret_name
        )

        load_fn = _lambda.Function(
            self,
            "LoadFn",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handler.handler",
            code=_lambda.Code.from_asset("lambdas/load"),
            role=fn_role,
            timeout=Duration.seconds(60),
            memory_size=256,
            environment={
                "DB_SECRET_ARN": secret.secret_arn,
                "DB_CLUSTER_ARN": cluster.cluster_identifier,
                "DB_NAME": "ragdemo",
            },
        )
        secret.grant_read(load_fn)
        load_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "rds-data:ExecuteStatement",
                    "rds-data:BatchExecuteStatement",
                    "rds-data:BeginTransaction",
                    "rds-data:CommitTransaction",
                    "rds-data:RollbackTransaction"
                ],
                resources=[f"arn:aws:rds:{self.region}:{self.account}:cluster:{cluster.cluster_identifier}"]
            )
        )

        # ──────────────────────────
        # 8. Execution Logging
        # ──────────────────────────
        # DynamoDB table for pipeline execution tracking
        exec_log_table = dynamodb.Table(
            self,
            "ExecLogTable",
            table_name="ExecLog",
            partition_key=dynamodb.Attribute(
                name="runId",
                type=dynamodb.AttributeType.STRING
            ),
            encryption=dynamodb.TableEncryption.CUSTOMER_MANAGED,
            encryption_key=data_key,
            removal_policy=RemovalPolicy.DESTROY,  # DEV ONLY
            time_to_live_attribute="ttl",
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
        )

        # Log Function:
        # - Records pipeline execution details
        log_fn = _lambda.Function(
            self,
            "LogFn",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handler.handler",
            code=_lambda.Code.from_asset("lambdas/log"),
            role=fn_role,
            timeout=Duration.seconds(30),
            memory_size=128,
            environment={
                "TABLE_NAME": exec_log_table.table_name,
            },
        )
        exec_log_table.grant_write_data(log_fn)

        # ──────────────────────────
        # 10. Error Handling
        # ──────────────────────────
        # SNS topic for pipeline failure notifications
        failure_topic = sns.Topic(
            self,
            "FailureTopic",
            topic_name="rag-demo-failures",
            display_name="RAG Demo Pipeline Failures",
            master_key=data_key,
        )

        # ──────────────────────────
        # 11. Step Functions Workflow
        # ──────────────────────────
        # Validation task with error handling
        validate_task = tasks.LambdaInvoke(
            self,
            "Validate",
            lambda_function=validate_fn,
            result_path="$.validated",
            payload=sfn.TaskInput.from_object({
                "bucket": textract_bucket.bucket_name,
                "key": sfn.JsonPath.string_at("$.textract.DocumentLocation.S3Uri")
            })
        ).add_catch(
            errors=["States.ALL"],
            handler=tasks.SnsPublish(
                self, "ValidateFailureNotification",
                topic=failure_topic,
                message=sfn.TaskInput.from_object({
                    "state": "Validate",
                    "s3Key": sfn.JsonPath.string_at("$.key"),
                    "cause": sfn.JsonPath.string_at("$.error.Cause"),
                    "error": sfn.JsonPath.string_at("$.error.Error"),
                    "runId": sfn.JsonPath.string_at("$$.Execution.Id"),
                    "timestamp": sfn.JsonPath.string_at("$$.State.EnteredTime")
                }),
                subject="RAG Demo Pipeline - Validation Failed"
            ),
            result_path="$.notified"
        )

        # State machine definition
        state_machine = sfn.StateMachine(
            self, "EtlStateMachine",
            definition=textract_task.add_catch(
                errors=["States.ALL"],
                handler=tasks.SnsPublish(
                    self, "TextractFailureNotification",
                    topic=failure_topic,
                    message=sfn.TaskInput.from_object({
                        "state": "ExtractText",
                        "s3Key": sfn.JsonPath.string_at("$.key"),
                        "cause": sfn.JsonPath.string_at("$.error.Cause"),
                        "error": sfn.JsonPath.string_at("$.error.Error"),
                        "runId": sfn.JsonPath.string_at("$$.Execution.Id"),
                        "timestamp": sfn.JsonPath.string_at("$$.State.EnteredTime")
                    }),
                    subject="RAG Demo Pipeline - Textract Failed"
                ),
                result_path="$.notified"
            ).next(validate_task)
        )

        # Grant KMS permissions to Step Functions
        data_key.grant_encrypt_decrypt(state_machine.role)

        # ──────────────────────────
        # 12. S3 Event Trigger
        # ──────────────────────────
        # Lambda function to start Step Functions on S3 upload
        trigger_fn = _lambda.Function(
            self,
            "TriggerFn",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="index.handler",
            code=_lambda.Code.from_inline("""
import boto3
import json
import logging

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

sfn = boto3.client('stepfunctions')

def handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")
    
    try:
        # Get the S3 bucket and key from the event
        record = event['Records'][0]
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        
        logger.info(f"Processing file: s3://{bucket}/{key}")
        
        # Get state machine ARN
        logger.info("Searching for EtlStateMachine")
        paginator = sfn.get_paginator('list_state_machines')
        state_machine_arn = None
        for page in paginator.paginate():
            for sm in page['stateMachines']:
                logger.info(f"Found state machine: {sm['name']}")
                if 'EtlStateMachine' in sm['name']:
                    state_machine_arn = sm['stateMachineArn']
                    logger.info(f"Found target state machine: {state_machine_arn}")
                    break
            if state_machine_arn:
                break
                
        if not state_machine_arn:
            raise ValueError("Could not find EtlStateMachine")
        
        # Start Step Functions execution
        execution = sfn.start_execution(
            stateMachineArn=state_machine_arn,
            input=json.dumps({
                "bucket": bucket,
                "key": key
            })
        )
        logger.info(f"Started execution: {execution['executionArn']}")
        
        return {
            'statusCode': 200,
            'body': f'Started execution {execution["executionArn"]} for s3://{bucket}/{key}'
        }
    except Exception as e:
        logger.error(f"Error processing event: {str(e)}")
        raise
"""),
            role=fn_role,
            timeout=Duration.seconds(30),
            memory_size=128,
        )

        # Grant Step Functions permissions to trigger function
        trigger_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "states:ListStateMachines",
                    "states:StartExecution"
                ],
                resources=["*"]
            )
        )

        # Configure S3 event notification
        raw_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(trigger_fn),
            s3.NotificationKeyFilter(prefix="incoming/", suffix=".pdf")
        )
