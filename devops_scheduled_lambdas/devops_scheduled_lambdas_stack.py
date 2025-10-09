from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as _lambda,
    aws_events as events,
    aws_events_targets as targets,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
)
from constructs import Construct
import os

class DevopsScheduledLambdasStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # Lambda helper
        def create_lambda(name: str):
            return _lambda.Function(
                self, name,
                runtime=_lambda.Runtime.PYTHON_3_13,
                handler="{}.handler".format(name),
                code=_lambda.Code.from_asset(os.path.join("lambdas")),
                timeout=Duration.seconds(30)
            )

        # Create the three Lambdas
        lambda1 = create_lambda("lambda1")
        lambda2 = create_lambda("lambda2")
        lambda3 = create_lambda("lambda3")

        # Step Function Tasks
        step1 = tasks.LambdaInvoke(
            self, "Invoke Lambda 1",
            lambda_function=lambda1,
            output_path="$.Payload"
        )

        step2 = tasks.LambdaInvoke(
            self, "Invoke Lambda 2",
            lambda_function=lambda2,
            output_path="$.Payload"
        )

        step3 = tasks.LambdaInvoke(
            self, "Invoke Lambda 3",
            lambda_function=lambda3,
            output_path="$.Payload"
        )

        # Chain: step1 → step2 → step3
        definition = step1.next(step2).next(step3)

        # Create the State Machine
        state_machine = sfn.StateMachine(
            self, "ScheduledWorkflow",
            definition=definition,
            timeout=Duration.minutes(5)
        )

        # EventBridge rule to trigger the workflow on a schedule
        rule = events.Rule(
            self, "HourlySchedule",
            schedule=events.Schedule.rate(Duration.hours(1)),
            targets=[targets.SfnStateMachine(state_machine)]
        )
