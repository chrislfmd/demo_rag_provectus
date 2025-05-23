"""
AWS CDK Stack implementing a Retrieval-Augmented Generation (RAG) pipeline.
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
    aws_dynamodb as dynamodb,
    aws_s3_notifications as s3n,
    aws_sqs as sqs,
)
from constructs import Construct
import uuid

class StorageConstruct(Construct):
    """Storage resources: S3 buckets and DynamoDB."""
    
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id)
        
        # Create KMS key for DynamoDB
        self.data_key = kms.Key(
            self, "DataKey",
            alias="alias/ragDemoKms",
            enable_key_rotation=True,
            description="CMK for RAG demo data (DynamoDB)",
        )

        # Raw PDF bucket
        self.raw_bucket = s3.Bucket(
            self, "RawPdfBucket",
            bucket_name="rag-demo-raw-pdf-v2",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # Textract output bucket
        self.textract_bucket = s3.Bucket(
            self, "TextractJsonBucket",
            bucket_name="rag-demo-textract-json-v2",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # Add bucket policy to allow Textract service to write results
        self.textract_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                principals=[iam.ServicePrincipal("textract.amazonaws.com")],
                actions=[
                    "s3:PutObject",
                    "s3:PutObjectAcl"
                ],
                resources=[f"{self.textract_bucket.bucket_arn}/*"]
            )
        )
        
        self.textract_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                principals=[iam.ServicePrincipal("textract.amazonaws.com")],
                actions=[
                    "s3:GetBucketLocation",
                    "s3:ListBucket"
                ],
                resources=[self.textract_bucket.bucket_arn]
            )
        )

        # DynamoDB table for documents and vectors
        self.documents_table = dynamodb.Table(
            self,
            "DocumentsTable",
            table_name="Documents",
            partition_key=dynamodb.Attribute(
                name="documentId",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="chunkId",
                type=dynamodb.AttributeType.STRING
            ),
            encryption=dynamodb.TableEncryption.CUSTOMER_MANAGED,
            encryption_key=self.data_key,
            removal_policy=RemovalPolicy.DESTROY,
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
        )

        # DynamoDB table for execution logging
        self.exec_log_table = dynamodb.Table(
            self,
            "ExecLogTable",
            table_name="ExecLog",
            partition_key=dynamodb.Attribute(
                name="runId",
                type=dynamodb.AttributeType.STRING
            ),
            encryption=dynamodb.TableEncryption.CUSTOMER_MANAGED,
            encryption_key=self.data_key,
            removal_policy=RemovalPolicy.DESTROY,
            time_to_live_attribute="ttl",
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
        )

class NotificationConstruct(Construct):
    """SQS queues for pipeline notifications."""
    
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id)
        
        # Dead letter queue for failed messages
        self.dlq = sqs.Queue(
            self, "NotificationDLQ",
            queue_name="rag-pipeline-notifications-dlq",
            retention_period=Duration.days(14),
            removal_policy=RemovalPolicy.DESTROY,
        )
        
        # Main notification queue
        self.notification_queue = sqs.Queue(
            self, "NotificationQueue", 
            queue_name="rag-pipeline-notifications",
            visibility_timeout=Duration.minutes(5),
            retention_period=Duration.days(7),
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=3,
                queue=self.dlq
            ),
            removal_policy=RemovalPolicy.DESTROY,
        )
        
        # Success-specific queue (optional, for filtered processing)
        self.success_queue = sqs.Queue(
            self, "SuccessQueue",
            queue_name="rag-pipeline-success",
            visibility_timeout=Duration.minutes(2),
            retention_period=Duration.days(3),
            removal_policy=RemovalPolicy.DESTROY,
        )
        
        # Error-specific queue (optional, for urgent error handling)
        self.error_queue = sqs.Queue(
            self, "ErrorQueue",
            queue_name="rag-pipeline-errors",
            visibility_timeout=Duration.minutes(2), 
            retention_period=Duration.days(7),
            removal_policy=RemovalPolicy.DESTROY,
        )

class LambdaConstruct(Construct):
    """Lambda functions and their roles."""
    
    def __init__(self, scope: Construct, id: str, storage: StorageConstruct, notifications: NotificationConstruct, **kwargs) -> None:
        super().__init__(scope, id)

        # Create base Lambda role policies
        lambda_base_policies = {
            "CloudWatchLogs": iam.PolicyDocument(
                statements=[
                    iam.PolicyStatement(
                        actions=["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
                        resources=["*"],
                    )
                ]
            )
        }

        # Initialize DB Function role and function
        init_db_role = iam.Role(
            self, "InitDbRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            inline_policies=lambda_base_policies
        )
        storage.documents_table.grant_read_write_data(init_db_role)
        storage.exec_log_table.grant_write_data(init_db_role)

        self.init_db_fn = _lambda.Function(
            self, "InitDbFn",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handler.handler",
            code=_lambda.Code.from_asset("lambdas/init_db"),
            role=init_db_role,
            timeout=Duration.seconds(60),
            memory_size=256,
            environment={
                "TABLE_NAME": storage.documents_table.table_name,
                "EXEC_LOG_TABLE": storage.exec_log_table.table_name,
            }
        )

        # Validate Function role and function
        validate_role = iam.Role(
            self, "ValidateRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            inline_policies={
                **lambda_base_policies,
                "Textract": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["textract:GetDocumentAnalysis"],
                            resources=["*"]
                        )
                    ]
                ),
                "SQS": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["sqs:SendMessage"],
                            resources=[
                                notifications.notification_queue.queue_arn,
                                notifications.error_queue.queue_arn
                            ]
                        )
                    ]
                ),
                "STS": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["sts:GetCallerIdentity"],
                            resources=["*"]
                        )
                    ]
                )
            }
        )
        storage.exec_log_table.grant_write_data(validate_role)

        self.validate_fn = _lambda.Function(
            self, "ValidateFn",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handler.handler",
            code=_lambda.Code.from_asset("lambdas/validate"),
            role=validate_role,
            timeout=Duration.seconds(900),
            memory_size=256,
            environment={
                "EXEC_LOG_TABLE": storage.exec_log_table.table_name,
            }
        )

        # Embed Function role and function
        embed_role = iam.Role(
            self, "EmbedRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            inline_policies={
                **lambda_base_policies,
                "Bedrock": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["bedrock:InvokeModel"],
                            resources=["*"]
                        )
                    ]
                ),
                "Textract": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["textract:GetDocumentAnalysis"],
                            resources=["*"]
                        )
                    ]
                ),
                "SQS": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["sqs:SendMessage"],
                            resources=[
                                notifications.notification_queue.queue_arn,
                                notifications.error_queue.queue_arn
                            ]
                        )
                    ]
                ),
                "STS": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["sts:GetCallerIdentity"],
                            resources=["*"]
                        )
                    ]
                )
            }
        )
        storage.exec_log_table.grant_write_data(embed_role)

        self.embed_fn = _lambda.Function(
            self, "EmbedFn",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handler.handler",
            code=_lambda.Code.from_asset("lambdas/embed"),
            role=embed_role,
            timeout=Duration.seconds(300),
            memory_size=512,
            environment={
                "EXEC_LOG_TABLE": storage.exec_log_table.table_name,
                "NOTIFICATION_QUEUE_URL": notifications.notification_queue.queue_url,
                "ERROR_QUEUE_URL": notifications.error_queue.queue_url,
            }
        )

        # Load Function role and function
        load_role = iam.Role(
            self, "LoadRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            inline_policies={
                **lambda_base_policies,
                "SQS": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["sqs:SendMessage"],
                            resources=[
                                notifications.notification_queue.queue_arn,
                                notifications.success_queue.queue_arn
                            ]
                        )
                    ]
                ),
                "STS": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["sts:GetCallerIdentity"],
                            resources=["*"]
                        )
                    ]
                )
            }
        )
        storage.documents_table.grant_read_write_data(load_role)
        storage.exec_log_table.grant_write_data(load_role)

        self.load_fn = _lambda.Function(
            self, "LoadFn",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handler.handler",
            code=_lambda.Code.from_asset("lambdas/load"),
            role=load_role,
            timeout=Duration.seconds(60),
            memory_size=256,
            environment={
                "TABLE_NAME": storage.documents_table.table_name,
                "EXEC_LOG_TABLE": storage.exec_log_table.table_name,
                "NOTIFICATION_QUEUE_URL": notifications.notification_queue.queue_url,
                "SUCCESS_QUEUE_URL": notifications.success_queue.queue_url,
            }
        )

        # Log Function role and function
        log_role = iam.Role(
            self, "LogRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            inline_policies=lambda_base_policies
        )
        storage.exec_log_table.grant_write_data(log_role)

        self.log_fn = _lambda.Function(
            self, "LogFn",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handler.handler",
            code=_lambda.Code.from_asset("lambdas/log"),
            role=log_role,
            timeout=Duration.seconds(30),
            memory_size=128,
            environment={
                "TABLE_NAME": storage.exec_log_table.table_name,
            }
        )

        # Notification Function role and function
        notify_role = iam.Role(
            self, "NotifyRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            inline_policies={
                **lambda_base_policies,
                "SQS": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["sqs:SendMessage"],
                            resources=[
                                notifications.notification_queue.queue_arn,
                                notifications.success_queue.queue_arn,
                                notifications.error_queue.queue_arn
                            ]
                        )
                    ]
                )
            }
        )
        storage.exec_log_table.grant_write_data(notify_role)

        self.notify_fn = _lambda.Function(
            self, "NotifyFn",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handler.handler",
            code=_lambda.Code.from_asset("lambdas/notify"),
            role=notify_role,
            timeout=Duration.seconds(60),
            memory_size=256,
            environment={
                "EXEC_LOG_TABLE": storage.exec_log_table.table_name,
                "NOTIFICATION_QUEUE_URL": notifications.notification_queue.queue_url,
                "SUCCESS_QUEUE_URL": notifications.success_queue.queue_url,
                "ERROR_QUEUE_URL": notifications.error_queue.queue_url,
            }
        )

        # Trigger Function role and function
        trigger_role = iam.Role(
            self, "TriggerRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            inline_policies=lambda_base_policies
        )

        self.trigger_role = trigger_role  # Store for later use
        self.trigger_fn = None  # Will be created after state machine

        # Query Function role and function
        query_role = iam.Role(
            self, "QueryRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            inline_policies={
                **lambda_base_policies,
                "Bedrock": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["bedrock:InvokeModel"],
                            resources=["*"]
                        )
                    ]
                )
            }
        )
        storage.documents_table.grant_read_data(query_role)

        self.query_fn = _lambda.Function(
            self, "QueryFn",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="handler.handler",
            code=_lambda.Code.from_asset("lambdas/query"),
            role=query_role,
            timeout=Duration.seconds(120),
            memory_size=512,
            environment={
                "TABLE_NAME": storage.documents_table.table_name,
            }
        )

class StateMachineConstruct(Construct):
    """Step Functions state machine and related resources."""
    
    def __init__(self, scope: Construct, id: str, storage: StorageConstruct, lambda_fns: LambdaConstruct, **kwargs) -> None:
        super().__init__(scope, id)

        # State machine role
        self.state_machine_role = iam.Role(
            self,
            "StateMachineRole",
            assumed_by=iam.ServicePrincipal("states.amazonaws.com"),
            inline_policies={
                "LambdaInvoke": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["lambda:InvokeFunction"],
                            resources=[
                                lambda_fns.init_db_fn.function_arn,
                                lambda_fns.validate_fn.function_arn,
                                lambda_fns.embed_fn.function_arn,
                                lambda_fns.load_fn.function_arn,
                                lambda_fns.notify_fn.function_arn,
                            ],
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
                ),
                "S3Access": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                "s3:GetObject",
                                "s3:GetObjectVersion",
                                "s3:GetBucketLocation",
                                "s3:ListBucket"
                            ],
                            resources=[
                                storage.raw_bucket.bucket_arn,
                                f"{storage.raw_bucket.bucket_arn}/*"
                            ],
                        )
                    ]
                ),
                "IAMPassRole": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["iam:PassRole"],
                            resources=["*"],
                            conditions={
                                "StringEquals": {
                                    "iam:PassedToService": "textract.amazonaws.com"
                                }
                            }
                        )
                    ]
                )
            },
        )

        # Grant S3 permissions
        storage.raw_bucket.grant_read(self.state_machine_role)
        storage.textract_bucket.grant_read_write(self.state_machine_role)

        # Step Functions workflow with comprehensive error handling
        # Define main processing steps without individual error handlers first
        main_processing_steps = sfn.Chain.start(
            tasks.LambdaInvoke(
                self, "InitDb",
                lambda_function=lambda_fns.init_db_fn,
                retry_on_service_exceptions=True,
                result_path="$.initDb"
            )
        ).next(
            tasks.CallAwsService(
                self, "ExtractText",
                service="textract",
                action="startDocumentAnalysis",
                iam_resources=["*"],
                parameters={
                    "DocumentLocation": {
                        "S3Object": {
                            "Bucket": sfn.JsonPath.string_at("$.bucket"),
                            "Name": sfn.JsonPath.string_at("$.key")
                        }
                    },
                    "FeatureTypes": ["TABLES", "FORMS"]
                },
                result_path="$.textract"
            )
        ).next(
            sfn.Wait(
                self, "WaitForTextract",
                time=sfn.WaitTime.duration(Duration.seconds(120))
            )
        ).next(
            tasks.LambdaInvoke(
                self, "Validate",
                lambda_function=lambda_fns.validate_fn,
                payload=sfn.TaskInput.from_object({
                    "textractJobId": sfn.JsonPath.string_at("$.textract.JobId"),
                    "bucket": sfn.JsonPath.string_at("$.bucket"),
                    "key": sfn.JsonPath.string_at("$.key"),
                    "runId": sfn.JsonPath.string_at("$.runId")
                }),
                result_path="$.validated"
            )
        ).next(
            tasks.LambdaInvoke(
                self, "Embed",
                lambda_function=lambda_fns.embed_fn,
                payload=sfn.TaskInput.from_object({
                    "textractJobId": sfn.JsonPath.string_at("$.textract.JobId"),
                    "bucket": sfn.JsonPath.string_at("$.bucket"),
                    "key": sfn.JsonPath.string_at("$.key"),
                    "documentId": sfn.JsonPath.string_at("$.initDb.Payload.documentId"),
                    "runId": sfn.JsonPath.string_at("$.runId")
                }),
                result_path="$.embedded"
            )
        ).next(
            tasks.LambdaInvoke(
                self, "Load",
                lambda_function=lambda_fns.load_fn,
                payload=sfn.TaskInput.from_object({
                    "documentId": sfn.JsonPath.string_at("$.initDb.Payload.documentId"),
                    "embedded": sfn.JsonPath.object_at("$.embedded.Payload"),
                    "runId": sfn.JsonPath.string_at("$.runId")
                }),
                result_path="$.loaded"
            )
        ).next(
            # Success notification
            tasks.LambdaInvoke(
                self, "NotifySuccess",
                lambda_function=lambda_fns.notify_fn,
                payload=sfn.TaskInput.from_object({
                    "runId": sfn.JsonPath.string_at("$.runId"),
                    "status": "SUCCESS",
                    "documentInfo": {
                        "bucket": sfn.JsonPath.string_at("$.bucket"),
                        "key": sfn.JsonPath.string_at("$.key"),
                        "documentId": sfn.JsonPath.string_at("$.initDb.Payload.documentId")
                    },
                    "processingResults": {
                        "chunkCount": sfn.JsonPath.number_at("$.embedded.Payload.chunk_count"),
                        "textLength": sfn.JsonPath.number_at("$.embedded.Payload.text_length")
                    }
                }),
                result_path="$.notification"
            )
        )

        # Comprehensive error notification handler
        error_notification_step = tasks.LambdaInvoke(
            self, "NotifyError",
            lambda_function=lambda_fns.notify_fn,
            payload=sfn.TaskInput.from_object({
                "runId": sfn.JsonPath.string_at("$.runId"),
                "status": "FAILED",
                "documentInfo": {
                    "bucket": sfn.JsonPath.string_at("$.bucket"),
                    "key": sfn.JsonPath.string_at("$.key"),
                    "documentId": sfn.JsonPath.string_at("$.initDb.Payload.documentId")
                },
                "error": sfn.JsonPath.string_at("$.Error"),
                "failedStep": sfn.JsonPath.string_at("$.Cause"),
                "errorDetails": sfn.JsonPath.object_at("$.error")
            })
        )

        # Use Parallel construct for robust error handling
        workflow_definition = sfn.Parallel(
            self, "MainWorkflowWithErrorHandling",
            comment="RAG Pipeline with comprehensive error notifications"
        ).branch(
            main_processing_steps
        ).add_catch(
            error_notification_step,
            errors=["States.ALL"],
            result_path="$.error"
        )

        # Create state machine
        self.state_machine = sfn.StateMachine(
            self, "EtlStateMachine",
            definition=workflow_definition,
            timeout=Duration.minutes(30),
            role=self.state_machine_role,
        )

class RagDemoStack(Stack):
    """End‑to‑end demo stack: KMS + S3 → Textract → Validate → Embed → Load(DynamoDB)"""

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # Create storage resources
        storage = StorageConstruct(self, "Storage")

        # Create notification resources
        notifications = NotificationConstruct(self, "Notifications")

        # Create Lambda functions
        lambda_fns = LambdaConstruct(self, "Lambda", storage, notifications)

        # Create state machine
        state_machine = StateMachineConstruct(self, "StateMachine", storage, lambda_fns)

        # Create trigger function after state machine
        lambda_fns.trigger_role.add_to_policy(
            iam.PolicyStatement(
                actions=["states:StartExecution"],
                resources=[state_machine.state_machine.state_machine_arn]
            )
        )

        lambda_fns.trigger_fn = _lambda.Function(
            self,
            "TriggerFn",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="index.handler",
            code=_lambda.Code.from_inline("""
import boto3
import json
import logging
import os
import uuid

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sfn = boto3.client('stepfunctions')
STATE_MACHINE_ARN = os.environ['STATE_MACHINE_ARN']

def handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")
    
    try:
        record = event['Records'][0]
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        
        # Generate unique runId for tracking
        run_id = str(uuid.uuid4())
        
        logger.info(f"Processing file: s3://{bucket}/{key} with runId: {run_id}")
        
        execution = sfn.start_execution(
            stateMachineArn=STATE_MACHINE_ARN,
            input=json.dumps({
                "bucket": bucket,
                "key": key,
                "runId": run_id
            })
        )
        logger.info(f"Started execution: {execution['executionArn']}")
        
        return {
            'statusCode': 200,
            'body': f'Started execution {execution["executionArn"]} for s3://{bucket}/{key} with runId: {run_id}'
        }
    except Exception as e:
        logger.error(f"Error processing event: {str(e)}")
        raise
"""),
            role=lambda_fns.trigger_role,
            timeout=Duration.seconds(30),
            memory_size=128,
            environment={
                "STATE_MACHINE_ARN": state_machine.state_machine.state_machine_arn
            }
        )

        # Store resources for post-deployment configuration
        self.raw_bucket = storage.raw_bucket
        self.trigger_fn = lambda_fns.trigger_fn

        # Add project tags
        for resource in [storage.raw_bucket, storage.textract_bucket]:
            Tags.of(resource).add("project", "rag-demo")
            Tags.of(resource).add("env", "dev")
