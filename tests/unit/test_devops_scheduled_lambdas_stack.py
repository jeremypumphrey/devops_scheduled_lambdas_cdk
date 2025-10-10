import aws_cdk as core
import aws_cdk.assertions as assertions

from devops_scheduled_lambdas.devops_scheduled_lambdas_stack import (
    DevopsScheduledLambdasStack,
)


# example tests. To run these tests, uncomment this file along with the example
# resource in devops_scheduled_lambdas/devops_scheduled_lambdas_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = DevopsScheduledLambdasStack(app, "devops-scheduled-lambdas")
    template = assertions.Template.from_stack(stack)


#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
