import json


def lambda_handler(event, context):
    print("Lambda 1 running...")
    return {"step": "one", "next": "lambda2"}
