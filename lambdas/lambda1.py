import json
def handler(event, context):
    print("Lambda 1 running...")
    return {"step": "one", "next": "lambda2"}
