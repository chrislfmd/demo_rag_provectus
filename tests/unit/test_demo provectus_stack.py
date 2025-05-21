import aws_cdk as core
import aws_cdk.assertions as assertions

from demo provectus.demo provectus_stack import DemoProvectusStack

# example tests. To run these tests, uncomment this file along with the example
# resource in demo provectus/demo provectus_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = DemoProvectusStack(app, "demo-provectus")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
