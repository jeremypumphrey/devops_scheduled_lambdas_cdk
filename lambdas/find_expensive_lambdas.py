import boto3
import os

lambda_client = boto3.client("lambda")


def lambda_handler(event, context):
    """
    Lambda handler to list all functions in the current AWS account/region
    that have SnapStart or Provisioned Concurrency enabled.
    """

    region = os.environ.get("AWS_REGION", "us-east-1")
    paginator = lambda_client.get_paginator("list_functions")
    response_iterator = paginator.paginate()

    report = []

    for page in response_iterator:
        for fn in page["Functions"]:
            fn_name = fn["FunctionName"]
            arn = fn["FunctionArn"]
            # print(f"Checking function: {fn_name} ARN: {arn}")

            # --- Check SnapStart ---
            snapstart_enabled = False
            try:
                cfg = lambda_client.get_function_configuration(FunctionName=fn_name)
                snap_cfg = cfg.get("SnapStart", {})
                if snap_cfg.get("ApplyOn", "None").lower() != "none":
                    snapstart_enabled = True
                    print(f"Function: {fn_name} has SnapStart enabled")
            except Exception as e:
                print(f"⚠️ Error checking SnapStart for {fn_name}: {e}")

            # --- Check Provisioned Concurrency ---
            provisioned_enabled = False

            try:
                # Get provisioned concurrency config for the function
                pc_config = lambda_client.list_provisioned_concurrency_configs(
                    FunctionName=fn_name
                )
                if pc_config["ProvisionedConcurrencyConfigs"]:
                    print(f"Function: {fn_name} has Provisioned Concurrency enabled.")
                    provisioned_enabled = True
                    for config in pc_config["ProvisionedConcurrencyConfigs"]:
                        print(
                            f"  Alias/Version: {config['Qualifier']}, Provisioned Concurrent Executions: {config['RequestedProvisionedConcurrencyCount']}"
                        )
            except lambda_client.exceptions.ResourceNotFoundException:
                # No provisioned concurrency configured for this function
                # print(f"No Provisioned Concurrency for {fn_name}")
                pass
            except Exception as e:
                print(f"⚠️ Error checking Provisioned Concurrency for {fn_name}: {e}")

            # If either SnapStart or Provisioned Concurrency is enabled, add to report
            if snapstart_enabled or provisioned_enabled:
                report.append(
                    {
                        "Region": region,
                        "FunctionName": fn_name,
                        "Arn": arn,
                        "SnapStart": snapstart_enabled,
                        "ProvisionedConcurrency": provisioned_enabled,
                    }
                )

    return {
        "Summary": f"Found {len(report)} function(s) with SnapStart or Provisioned Concurrency enabled.",
        "Functions": report,
    }
