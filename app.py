#!/usr/bin/env python3
import aws_cdk as cdk

# from aws_cdk import App, Tags
from devops_scheduled_lambdas.devops_scheduled_lambdas_stack import (
    DevopsScheduledLambdasStack,
)

app = cdk.App()
cdk.Tags.of(app).add("Project", "Devops")
DevopsScheduledLambdasStack(app, "DevopsScheduledLambdasStack")
app.synth()
