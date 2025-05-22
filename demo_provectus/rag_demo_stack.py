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
            memory_size=512,
            vpc=vpc,
            security_groups=[cluster.connections.security_groups[0]],
            environment={
                "DB_SECRET_NAME": db_secret.secret_name,
                "CLUSTER_ARN": cluster.cluster_identifier,
            },
        )
        secret.grant_read(load_fn)  # Grant read access using the actual Secret
        load_fn.add_to_role_policy(
            iam.PolicyStatement(
                actions=["rds-data:ExecuteStatement", "rds-data:BatchExecuteStatement"],
                resources=["*"],  # Using wildcard since we need to access the cluster through the Data API
            )
        )

        # ──────────────────────────
        # 8. Step Functions definition
        # ──────────────────────────
        # Only stub states here (Textract wiring skipped for brevity)
        validate_task = tasks.LambdaInvoke(
            self,
            "Validate",
            lambda_function=validate_fn,
            result_path="$.validated",
        )

        embed_task = tasks.LambdaInvoke(
            self,
            "Embed",
            lambda_function=embed_fn,
            result_path="$.embedded",
        )
        validate_task.next(embed_task)

        load_task = tasks.LambdaInvoke(
            self,
            "LoadVectors",
            lambda_function=load_fn,
            result_path="$.loaded",
        )
        embed_task.next(load_task)

        state_machine = sfn.StateMachine(
            self,
            "EtlStateMachine",
            definition=validate_task,
            timeout=Duration.minutes(30),
        )
