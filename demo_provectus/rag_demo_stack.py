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
)
from constructs import Construct


class RagDemoStack(Stack):
    """End‑to‑end demo stack: KMS + S3 → Textract → Validate → Embed → Load(pgvector)"""

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # ──────────────────────────
        # 1. Encryption key
        # ──────────────────────────
        data_key = kms.Key(
            self, "DataKey",
            alias="alias/ragDemoKms",
            enable_key_rotation=True,
            description="CMK for RAG demo data",
        )

        # ──────────────────────────
        # 2. Buckets
        # ──────────────────────────
        raw_bucket = s3.Bucket(
            self, "RawPdfBucket",
            bucket_name="rag-demo-raw-pdf-v2",
            versioned=True,
            encryption=s3.BucketEncryption.KMS,
            encryption_key=data_key,
            lifecycle_rules=[
                s3.LifecycleRule(
                    transitions=[
                        s3.Transition(
                            storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                            transition_after=Duration.days(30),
                        )
                    ]
                )
            ],
            removal_policy=RemovalPolicy.DESTROY,
        )

        textract_bucket = s3.Bucket(
            self, "TextractJsonBucket",
            bucket_name="rag-demo-textract-json-v2",
            versioned=True,
            encryption=s3.BucketEncryption.KMS,
            encryption_key=data_key,
            removal_policy=RemovalPolicy.DESTROY,
        )

        for b in (raw_bucket, textract_bucket):
            Tags.of(b).add("project", "rag-demo")
            Tags.of(b).add("env", "dev")

        # ──────────────────────────
        # 3. VPC & Aurora pgvector
        # ──────────────────────────
        vpc = ec2.Vpc(
            self, "RagDemoVpc",
            max_azs=2,  # Use 2 AZs for high availability
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

        db_secret = rds.Credentials.from_generated_secret(
            secret_name="ragDemoDbSecret",
            username="pgadmin",
        )

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
        # 4. Shared Lambda role
        # ──────────────────────────
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
                )
            },
        )
        data_key.grant_encrypt_decrypt(fn_role)
        raw_bucket.grant_read(fn_role)
        textract_bucket.grant_read_write(fn_role)

        # ──────────────────────────
        # 5. Validate Lambda
        # ──────────────────────────
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

        # 6. Embed Lambda
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

        # 7. Load Lambda
        # Get the actual Secret from credentials
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
        # Grant RDS Data API permissions
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

        # 8. ExecLog DynamoDB Table
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

        # 9. Log Lambda
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
        # 10. SNS Topic for Failures
        # ──────────────────────────
        failure_topic = sns.Topic(
            self,
            "FailureTopic",
            topic_name="rag-demo-failures",
            display_name="RAG Demo Pipeline Failures",
            master_key=data_key,
        )

        # ──────────────────────────
        # 11. Step Functions definition
        # ──────────────────────────
        # Add error handling and notifications to each task
        validate_task = tasks.LambdaInvoke(
            self,
            "Validate",
            lambda_function=validate_fn,
            result_path="$.validated",
        ).add_catch(
            errors=["States.ALL"],
            handler=tasks.SnsPublish(
                self, "ValidateFailureNotification",
                topic=failure_topic,
                message=sfn.TaskInput.from_object({
                    "error": sfn.JsonPath.string_at("$.Cause"),
                    "state": "Validate",
                    "runId": sfn.JsonPath.string_at("$$.Execution.Id"),
                    "s3Key": sfn.JsonPath.string_at("$.s3Key"),
                    "timestamp": sfn.JsonPath.string_at("$$.State.EnteredTime")
                }),
                subject="RAG Demo Pipeline - Validation Failed",
                result_path="$.notified"
            ),
            result_path="$.error"
        )

        embed_task = tasks.LambdaInvoke(
            self,
            "Embed",
            lambda_function=embed_fn,
            result_path="$.embedded",
        ).add_catch(
            errors=["States.ALL"],
            handler=tasks.SnsPublish(
                self, "EmbedFailureNotification",
                topic=failure_topic,
                message=sfn.TaskInput.from_object({
                    "error": sfn.JsonPath.string_at("$.Cause"),
                    "state": "Embed",
                    "runId": sfn.JsonPath.string_at("$$.Execution.Id"),
                    "s3Key": sfn.JsonPath.string_at("$.s3Key"),
                    "timestamp": sfn.JsonPath.string_at("$$.State.EnteredTime")
                }),
                subject="RAG Demo Pipeline - Embedding Failed",
                result_path="$.notified"
            ),
            result_path="$.error"
        )
        validate_task.next(embed_task)

        load_task = tasks.LambdaInvoke(
            self,
            "LoadVectors",
            lambda_function=load_fn,
            result_path="$.loaded",
        ).add_catch(
            errors=["States.ALL"],
            handler=tasks.SnsPublish(
                self, "LoadFailureNotification",
                topic=failure_topic,
                message=sfn.TaskInput.from_object({
                    "error": sfn.JsonPath.string_at("$.Cause"),
                    "state": "LoadVectors",
                    "runId": sfn.JsonPath.string_at("$$.Execution.Id"),
                    "s3Key": sfn.JsonPath.string_at("$.s3Key"),
                    "timestamp": sfn.JsonPath.string_at("$$.State.EnteredTime")
                }),
                subject="RAG Demo Pipeline - Loading Failed",
                result_path="$.notified"
            ),
            result_path="$.error"
        )
        embed_task.next(load_task)

        # Add logging task with error handling
        log_task = tasks.LambdaInvoke(
            self,
            "LogExecution",
            lambda_function=log_fn,
            result_path="$.logged",
            payload=sfn.TaskInput.from_object({
                "runId": sfn.JsonPath.string_at("$$.Execution.Id"),
                "s3Key": sfn.JsonPath.string_at("$.s3Key"),
                "status": "SUCCEEDED",
                "startTs": sfn.JsonPath.string_at("$$.Execution.StartTime"),
                "endTs": sfn.JsonPath.string_at("$$.State.EnteredTime"),
                "rowCount": sfn.JsonPath.number_at("$.loaded.Payload.rowCount")
            })
        ).add_catch(
            errors=["States.ALL"],
            handler=tasks.SnsPublish(
                self, "LogFailureNotification",
                topic=failure_topic,
                message=sfn.TaskInput.from_object({
                    "error": sfn.JsonPath.string_at("$.Cause"),
                    "state": "LogExecution",
                    "runId": sfn.JsonPath.string_at("$$.Execution.Id"),
                    "s3Key": sfn.JsonPath.string_at("$.s3Key"),
                    "timestamp": sfn.JsonPath.string_at("$$.State.EnteredTime")
                }),
                subject="RAG Demo Pipeline - Logging Failed",
                result_path="$.notified"
            ),
            result_path="$.error"
        )
        load_task.next(log_task)

        state_machine = sfn.StateMachine(
            self,
            "EtlStateMachine",
            definition=validate_task,
            timeout=Duration.minutes(30),
        )
