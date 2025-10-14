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
    # aws_logs as logs,
    aws_iam as iam,
    TimeZone # Added for cron with timezone support
)
from constructs import Construct
import os


class DevopsScheduledLambdasStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # 🔔 SNS Topic for workflow alerts
        alert_topic = sns.Topic(
            self,
            "DevopsScheduledWorkflowAlerts",
            display_name="Devops Scheduled Lambda Workflow Alerts",
        )

        # (Optional) Add email subscription
        alert_topic.add_subscription(subs.EmailSubscription("jeremy.pumphrey@nih.gov"))

        # 🧱 Helper function to create Lambdas
        def create_lambda(name: str):
            return _lambda.Function(
                self,
                name,
                runtime=_lambda.Runtime.PYTHON_3_13,
                handler=f"{name}.lambda_handler",
                code=_lambda.Code.from_asset(os.path.join("lambdas")),
                timeout=Duration.seconds(300),
            )

        # 🧩 Lambdas
        lambda1 = create_lambda("find_expensive_lambdas")
        lambda1.role.add_managed_policy(
            iam.ManagedPolicy.from_aws_managed_policy_name("AWSLambda_ReadOnlyAccess")
        )

        lambda2 = create_lambda("lambda2")
        lambda3 = create_lambda("lambda3")

        # 🪄 Step Function tasks (each with retries)
        step1 = tasks.LambdaInvoke(
            self,
            "Run Lambda 1",
            lambda_function=lambda1,
            # output_path="$.Payload",
            result_path="$.output",
        ).add_retry(
            max_attempts=2,
            interval=Duration.seconds(10),
            backoff_rate=2.0,
            errors=["Lambda.ServiceException", "Lambda.AWSLambdaException"],
        )

        step2 = tasks.LambdaInvoke(
            self, "Run Lambda 2", lambda_function=lambda2, result_path="$.output"
        ).add_retry(max_attempts=2, interval=Duration.seconds(10), backoff_rate=2.0)

        step3 = tasks.LambdaInvoke(
            self, "Run Lambda 3", lambda_function=lambda3, result_path="$.output"
        ).add_retry(max_attempts=2, interval=Duration.seconds(10), backoff_rate=2.0)

        # ✅ Step Status notification
        step1_notify = tasks.SnsPublish(
            self,
            "Post Step 1 Notification",
            topic=alert_topic,
            message=sfn.TaskInput.from_json_path_at("$.output.Payload"),
            subject="find_expensive_lambdas Step Complete",
        )
        step2_notify = tasks.SnsPublish(
            self,
            "Post Step 2 Notification",
            topic=alert_topic,
            message=sfn.TaskInput.from_json_path_at("$.output.Payload"),
            subject="Lambda Workflow Step 2 Complete",
        )
        step3_notify = tasks.SnsPublish(
            self,
            "Post Step 3 Notification",
            topic=alert_topic,
            # message=sfn.TaskInput.from_json_path_at("$."),
            message=sfn.TaskInput.from_json_path_at("$.output.Payload"),
            subject="Lambda Workflow Step 3 Complete",
        )

        # ✅ Success notification
        success_notify = tasks.SnsPublish(
            self,
            "Send Success Notification",
            topic=alert_topic,
            message=sfn.TaskInput.from_text(
                "✅ Step Function workflow completed successfully."
            ),
            subject="Scheduled Lambda Workflow Success",
        )

        # 🧨 Failure notification
        failure_notify = tasks.SnsPublish(
            self,
            "Send Failure Notification",
            topic=alert_topic,
            message=sfn.TaskInput.from_text(
                "⚠️ Step Function workflow failed. Check CloudWatch logs for details."
            ),
            subject="Scheduled Lambda Workflow Failure",
        )

        # Create the sequential chain for each Branch of the Parallel state
        branch_1_chain = sfn.Chain.start(step1).next(step1_notify)
        branch_2_chain = sfn.Chain.start(step2).next(step2_notify)
        branch_3_chain = sfn.Chain.start(step3).next(step3_notify)

        # Create a Parallel state and add the branches
        parallel_state = sfn.Parallel(
            self, "DevopsScheduledWorkflowParallel", comment="Runs tasks in parallel"
        )
        parallel_state.branch(branch_1_chain)
        # parallel_state.branch(branch_2_chain) # Uncomment to run in parallel
        # parallel_state.branch(branch_3_chain) # Uncomment to run in parallel

        # Chain the states to form the state machine definition
        definition = parallel_state.next(success_notify)

        # Create the State Machine
        state_machine = sfn.StateMachine(
            self,
            "DevopsScheduledWorkflow",
            definition_body=sfn.DefinitionBody.from_chainable(definition),
            # state_machine_name="MyParallelWorkflow"
        )

        # Sequential workflow
        # # 🧭 Define workflow sequence
        # definition_chain = (
        #     step1
        #     .next(step_notify)
        #     .next(step2)
        #     # .next(step_notify)
        #     .next(step3)
        #     # .next(step_notify)
        #     .next(success_notify)
        # )

        # # ⚙️ State Machine (modern CDK style)
        # state_machine = sfn.StateMachine(
        #     self,
        #     "DevopsScheduledWorkflow",
        #     definition_body=sfn.DefinitionBody.from_chainable(definition_chain),
        #     timeout=Duration.minutes(15),
        # )

        # 🕒 EventBridge rule (runs hourly)
        events.Rule(
            self,
            "DevopsRunScheduleRule",
            # schedule=events.Schedule.rate(Duration.hours(1)), #run hourly
            schedule=events.Schedule.cron(time_zone=TimeZone.AMERICA_NEW_YORK, minute="0", hour="09", month="*", week_day="MON", year="*"),  # Every Monday at 9am Eastern
            targets=[targets.SfnStateMachine(state_machine)],
        )
