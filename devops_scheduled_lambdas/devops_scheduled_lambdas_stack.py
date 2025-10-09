from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as _lambda,
    aws_events as events,
    aws_events_targets as targets,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_sns as sns,
    aws_sns_subscriptions as subs,
)
from constructs import Construct
import os


class ScheduledLambdasStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # 🔔 SNS Topic for workflow alerts
        alert_topic = sns.Topic(
            self, "StepFunctionAlertsTopic",
            display_name="Scheduled Lambda Workflow Alerts"
        )

        # (Optional) Add email subscription
        alert_topic.add_subscription(
            subs.EmailSubscription("your.email@example.com")
        )

        # 🧱 Helper function to create Lambdas
        def create_lambda(name: str):
            return _lambda.Function(
                self, name,
                runtime=_lambda.Runtime.PYTHON_3_13,
                handler=f"{name}.handler",
                code=_lambda.Code.from_asset(os.path.join("lambdas")),
                timeout=Duration.seconds(30)
            )

        # 🧩 Lambdas
        lambda1 = create_lambda("lambda1")
        lambda2 = create_lambda("lambda2")
        lambda3 = create_lambda("lambda3")

        # 🪄 Step Function tasks (each with retries)
        step1 = tasks.LambdaInvoke(
            self, "Run Lambda 1",
            lambda_function=lambda1,
            output_path="$.Payload"
        ).add_retry(
            max_attempts=2,
            interval=Duration.seconds(10),
            backoff_rate=2.0,
            errors=["Lambda.ServiceException", "Lambda.AWSLambdaException"]
        )

        step2 = tasks.LambdaInvoke(
            self, "Run Lambda 2",
            lambda_function=lambda2,
            output_path="$.Payload"
        ).add_retry(
            max_attempts=2,
            interval=Duration.seconds(10),
            backoff_rate=2.0
        )

        step3 = tasks.LambdaInvoke(
            self, "Run Lambda 3",
            lambda_function=lambda3,
            output_path="$.Payload"
        ).add_retry(
            max_attempts=2,
            interval=Duration.seconds(10),
            backoff_rate=2.0
        )

        # ✅ Success notification
        success_notify = tasks.SnsPublish(
            self, "Send Success Notification",
            topic=alert_topic,
            message=sfn.TaskInput.from_text(
                "✅ Step Function workflow completed successfully."
            ),
            subject="Lambda Workflow Success"
        )

        # 🧨 Failure notification
        failure_notify = tasks.SnsPublish(
            self, "Send Failure Notification",
            topic=alert_topic,
            message=sfn.TaskInput.from_text(
                "⚠️ Step Function workflow failed. Check CloudWatch logs for details."
            ),
            subject="Lambda Workflow Failure"
        )

        # 🧭 Define workflow sequence
        definition_chain = (
            step1
            .next(step2)
            .next(step3)
            .next(success_notify)
        ).add_catch(
            failure_notify,
            errors=["States.ALL"],
            result_path="$.error"
        )

        # ⚙️ State Machine (modern CDK style)
        state_machine = sfn.StateMachine(
            self, "DevopsScheduledWorkflow",
            definition_body=sfn.DefinitionBody.from_chainable(definition_chain),
            timeout=Duration.minutes(5)
        )

        # 🕒 EventBridge rule (runs hourly)
        events.Rule(
            self, "DevopsRunScheduleRule",
            # schedule=events.Schedule.rate(Duration.hours(1)),
            schedule=events.Schedule.cron(minute="0", hour="12"),
            targets=[targets.SfnStateMachine(state_machine)]
        )
