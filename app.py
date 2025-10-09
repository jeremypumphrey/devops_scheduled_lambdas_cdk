#!/usr/bin/env python3
import aws_cdk as cdk
from devops_scheduled_lambdas.devops_scheduled_lambdas_stack import DevopsScheduledLambdasStack

app = cdk.App()
DevopsScheduledLambdasStack(app, "DevopsScheduledLambdasStack")
app.synth()
