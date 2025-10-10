import json


def lambda_handler(event, context):
    print("Lambda 3 running...")
    return {"step": "three", "status": "complete"}
