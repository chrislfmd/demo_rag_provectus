#!/usr/bin/env python3
import aws_cdk as cdk
from demo_provectus.rag_demo_stack import RagDemoStack

app = cdk.App()
RagDemoStack(app, "RagDemoStack",
    env=cdk.Environment(
        account='702645448228',  # Your AWS account ID
        region='us-east-1'       # Your AWS region
    )
)

app.synth()
