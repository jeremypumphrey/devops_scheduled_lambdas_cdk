
# CDK based DevOps Scheduled Lambdas 

This project uses CDK to define and deploy a scheduled Step Function that triggers lambdas for DevOps purposes. The goal is to enable quick and easy deployment of new lambdas used in DevOps. Each lambda will be run in parallel and have an output step to notify of the results as shown here:

![Step Function](./images/StepFN.png)



## Useful commands
* `cdk bootstrap --profile TIER` once per account

* `okta-awscli  --force --profile DEVINT`
* `cdk deploy --profile DEVINT`     deploy updates to DEVINT

* `okta-awscli  --force --profile UAT`
* `cdk deploy --profile UAT`        deploy updates to UAT

* `okta-awscli  --force --profile PROD`
* `cdk deploy --profile PROD`       deploy updates to PROD

