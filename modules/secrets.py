"""Secrets Manager and rotation resources"""

import pulumi
import pulumi_aws as aws
import json
import secrets
import string
from config import PROJECT_NAME, SECRET_ROTATION_DAYS, COMMON_TAGS

def generate_secret_value(length=32):
    """Generate a secure random secret"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def create_secrets_and_rotation():
    """Create secrets in AWS Secrets Manager with rotation"""
    
    # Create JWT secret
    jwt_secret_value = {
        "jwt_secret_key": generate_secret_value(64),
        "algorithm": "HS256"
    }
    
    jwt_secret = aws.secretsmanager.Secret(
        f"{PROJECT_NAME}-jwt-secret",
        name=f"{PROJECT_NAME}-jwt-secret",
        description="JWT secret key for CDN headers validation",
        tags={**COMMON_TAGS, "Name": f"{PROJECT_NAME}-jwt-secret"}
    )
    
    jwt_secret_version = aws.secretsmanager.SecretVersion(
        f"{PROJECT_NAME}-jwt-secret-version",
        secret_id=jwt_secret.id,
        secret_string=json.dumps(jwt_secret_value)
    )
    
    # Create API key secret
    api_key_secret_value = {
        "api_key": generate_secret_value(32),
        "created_at": "2024-01-01T00:00:00Z"
    }
    
    api_key_secret = aws.secretsmanager.Secret(
        f"{PROJECT_NAME}-api-key-secret",
        name=f"{PROJECT_NAME}-api-key-secret",
        description="API key for CDN to ALB communication",
        tags={**COMMON_TAGS, "Name": f"{PROJECT_NAME}-api-key-secret"}
    )
    
    api_key_secret_version = aws.secretsmanager.SecretVersion(
        f"{PROJECT_NAME}-api-key-secret-version",
        secret_id=api_key_secret.id,
        secret_string=json.dumps(api_key_secret_value)
    )
    
    # Create Lambda execution role for rotation
    rotation_role = aws.iam.Role(
        f"{PROJECT_NAME}-rotation-role",
        assume_role_policy=json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Action": "sts:AssumeRole",
                "Effect": "Allow",
                "Principal": {
                    "Service": "lambda.amazonaws.com"
                }
            }]
        }),
        tags={**COMMON_TAGS, "Name": f"{PROJECT_NAME}-rotation-role"}
    )
    
    # Attach policies to rotation role
    aws.iam.RolePolicyAttachment(
        f"{PROJECT_NAME}-rotation-role-basic-execution",
        role=rotation_role.name,
        policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
    )
    
    rotation_policy = aws.iam.RolePolicy(
        f"{PROJECT_NAME}-rotation-policy",
        role=rotation_role.id,
        policy=pulumi.Output.all(jwt_secret.arn, api_key_secret.arn).apply(
            lambda arns: json.dumps({
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": [
                            "secretsmanager:GetSecretValue",
                            "secretsmanager:UpdateSecretVersionStage",
                            "secretsmanager:PutSecretValue"
                        ],
                        "Resource": arns
                    },
                    {
                        "Effect": "Allow",
                        "Action": [
                            "elbv2:DescribeTargetGroups",
                            "elbv2:DescribeListeners",
                            "elbv2:ModifyListener"
                        ],
                        "Resource": "*"
                    }
                ]
            })
        )
    )
    
    # Create rotation Lambda function
    rotation_lambda = aws.lambda_.Function(
        f"{PROJECT_NAME}-rotation-lambda",
        name=f"{PROJECT_NAME}-rotation-lambda",
        runtime="python3.11",
        handler="index.lambda_handler",
        role=rotation_role.arn,
        code=pulumi.AssetArchive({
            "index.py": pulumi.StringAsset(get_rotation_lambda_code())
        }),
        timeout=60,
        tags={**COMMON_TAGS, "Name": f"{PROJECT_NAME}-rotation-lambda"}
    )
    
    # Grant Secrets Manager permission to invoke Lambda
    aws.lambda_.Permission(
        f"{PROJECT_NAME}-rotation-lambda-permission",
        action="lambda:InvokeFunction",
        function=rotation_lambda.name,
        principal="secretsmanager.amazonaws.com"
    )
    
    # Set up automatic rotation for JWT secret
    aws.secretsmanager.SecretRotation(
        f"{PROJECT_NAME}-jwt-secret-rotation",
        secret_id=jwt_secret.id,
        rotation_lambda_arn=rotation_lambda.arn,
        rotation_rules=aws.secretsmanager.SecretRotationRotationRulesArgs(
            automatically_after_days=SECRET_ROTATION_DAYS
        )
    )
    
    # Set up automatic rotation for API key secret
    aws.secretsmanager.SecretRotation(
        f"{PROJECT_NAME}-api-key-secret-rotation",
        secret_id=api_key_secret.id,
        rotation_lambda_arn=rotation_lambda.arn,
        rotation_rules=aws.secretsmanager.SecretRotationRotationRulesArgs(
            automatically_after_days=SECRET_ROTATION_DAYS
        )
    )
    
    return {
        "jwt_secret_arn": jwt_secret.arn,
        "api_key_secret_arn": api_key_secret.arn,
        "rotation_lambda_arn": rotation_lambda.arn
    }

def get_rotation_lambda_code():
    """Return the Lambda function code for secret rotation"""
    return '''
import json
import boto3
import secrets
import string
from datetime import datetime

def lambda_handler(event, context):
    """Handle secret rotation"""
    
    secrets_client = boto3.client('secretsmanager')
    
    secret_arn = event['Step1']['SecretArn']
    token = event['Step1']['ClientRequestToken']
    step = event['Step1']['Step']
    
    if step == "createSecret":
        create_secret(secrets_client, secret_arn, token)
    elif step == "setSecret":
        set_secret(secrets_client, secret_arn, token)
    elif step == "testSecret":
        test_secret(secrets_client, secret_arn, token)
    elif step == "finishSecret":
        finish_secret(secrets_client, secret_arn, token)
    
    return {"statusCode": 200}

def create_secret(secrets_client, secret_arn, token):
    """Create new secret version"""
    try:
        secrets_client.get_secret_value(SecretArn=secret_arn, VersionStage="AWSPENDING")
        return
    except secrets_client.exceptions.ResourceNotFoundException:
        pass
    
    # Generate new secret
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    new_secret = ''.join(secrets.choice(alphabet) for _ in range(64))
    
    current_secret = secrets_client.get_secret_value(SecretArn=secret_arn, VersionStage="AWSCURRENT")
    current_data = json.loads(current_secret['SecretString'])
    
    if 'jwt_secret_key' in current_data:
        new_data = {
            "jwt_secret_key": new_secret,
            "algorithm": "HS256"
        }
    else:
        new_data = {
            "api_key": new_secret,
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
    
    secrets_client.put_secret_value(
        SecretArn=secret_arn,
        ClientRequestToken=token,
        SecretString=json.dumps(new_data),
        VersionStages=["AWSPENDING"]
    )

def set_secret(secrets_client, secret_arn, token):
    """Set the secret in the service"""
    # In a real implementation, you would update the ALB listener rules here
    pass

def test_secret(secrets_client, secret_arn, token):
    """Test the new secret"""
    # In a real implementation, you would test the new secret here
    pass

def finish_secret(secrets_client, secret_arn, token):
    """Finish the rotation by updating version stages"""
    secrets_client.update_secret_version_stage(
        SecretArn=secret_arn,
        VersionStage="AWSCURRENT",
        ClientRequestToken=token
    )
    
    secrets_client.update_secret_version_stage(
        SecretArn=secret_arn,
        VersionStage="AWSPENDING",
        ClientRequestToken=token,
        RemoveFromVersionId=token
    )
'''