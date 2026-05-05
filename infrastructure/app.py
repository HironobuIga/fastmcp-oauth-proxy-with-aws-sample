#!/usr/bin/env python3
import os

import aws_cdk as cdk

from cognito_stack import CognitoStack

app = cdk.App()

CognitoStack(
    app,
    "FastmcpCognitoSampleStack",
    env=cdk.Environment(
        account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
        region=os.environ.get("CDK_DEFAULT_REGION", "ap-northeast-1"),
    ),
)

app.synth()
