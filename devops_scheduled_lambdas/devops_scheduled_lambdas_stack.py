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
    aws_logs as logs,
    aws_iam as iam,
)
from constructs import Construct
import os


class DevopsScheduledLambdasStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # sfn_role = iam.Role(
        #     self, "StepFunctionExecutionRole",
        #     assumed_by=iam.ServicePrincipal("states.amazonaws.com"),
        #     description="Execution role for DevopsScheduledLambdasStack Step Function",
        # )

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
        # lambda1.grant_invoke(sfn_role)

        lambda2 = create_lambda("lambda2")
        # lambda2.grant_invoke(sfn_role)
        
        lambda3 = create_lambda("lambda3")
        # lambda2.grant_invoke(sfn_role)

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
            subject="find_expensive_lambdas Results",
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

        # set logging for the state machine
        # log_group = logs.LogGroup(
        #     self,
        #     "DevopsScheduledWorkflowLogGroup",
        #     # log_group_name="/aws/vendedlogs/states/DevopsScheduledWorkflowLogGroup", # Recommended prefix for Step Functions logs
        #     retention=logs.RetentionDays.ONE_MONTH,
        # )
        # log_group.grant_write(sfn_role)
        # # sfn_role.add_managed_policy(
        # #     iam.ManagedPolicy.from_aws_managed_policy_name("CloudWatchLogsFullAccess")
        # # )
        # sfn_role.add_to_policy(
        #     iam.PolicyStatement(
        #         actions=[
        #             "logs:CreateLogStream",
        #             "logs:PutLogEvents",
        #             "logs:CreateLogDelivery",
        #             "logs:GetLogDelivery",
        #             "logs:UpdateLogDelivery",
        #             "logs:DeleteLogDelivery",
        #             "logs:ListLogDeliveries",
        #             "logs:PutResourcePolicy",
        #             "logs:DescribeResourcePolicies",
        #             "logs:DescribeLogGroups",
        #             "logs:CreateLogGroup",
        #             "logs:CreateLogStream",
        #             "logs:PutLogEvents",
        #             "logs:DescribeLogStreams",
        #         ],
        #         resources=[log_group.log_group_arn],
        #     )
        # )

        # Create the State Machine
        state_machine = sfn.StateMachine(
            self,
            "DevopsScheduledWorkflow",
            definition_body=sfn.DefinitionBody.from_chainable(definition),
            # state_machine_name="MyParallelWorkflow",
            # role=sfn_role,
            # logs=sfn.LogOptions(
            #     destination=log_group,
            #     level=sfn.LogLevel.ALL,
            #     include_execution_data=True,
            # ),
        )

        # 🕒 EventBridge rule (runs hourly)
        events.Rule(
            self,
            "DevopsRunScheduleRule",
            # schedule=events.Schedule.rate(Duration.hours(1)), #run hourly
            schedule=events.Schedule.cron(
                minute="0",
                hour="14",  # 2pm UTC = 9am Eastern
                month="*",
                week_day="MON",
                year="*",
            ),  # Every Monday at 9am Eastern
            targets=[targets.SfnStateMachine(state_machine)],
        )
