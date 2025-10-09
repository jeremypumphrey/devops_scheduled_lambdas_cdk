import json
def handler(event, context):
    print("Lambda 2 running...")
    return {"step": "two", "next": "lambda3"}
