import json


def lambda_handler(event, context):
    print("Lambda 2 running...")
    return {"step": "two", "next": "lambda3"}
