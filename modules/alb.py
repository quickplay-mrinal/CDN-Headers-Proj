"""Application Load Balancer resources"""

import pulumi
import pulumi_aws as aws
import json
from config import PROJECT_NAME, ALB_IDLE_TIMEOUT, ALB_DELETION_PROTECTION, APP_PORT, HEALTH_CHECK_PATH, COMMON_TAGS

def create_alb(vpc_id, public_subnet_ids, jwt_secret_arn):
    """Create Application Load Balancer with JWT validation"""
    
    # Create security group for ALB
    alb_sg = aws.ec2.SecurityGroup(
        f"{PROJECT_NAME}-alb-sg",
        name=f"{PROJECT_NAME}-alb-sg",
        description="Security group for ALB",
        vpc_id=vpc_id,
        ingress=[
            aws.ec2.SecurityGroupIngressArgs(
                protocol="tcp",
                from_port=80,
                to_port=80,
                cidr_blocks=["0.0.0.0/0"]
            ),
            aws.ec2.SecurityGroupIngressArgs(
                protocol="tcp",
                from_port=443,
                to_port=443,
                cidr_blocks=["0.0.0.0/0"]
            )
        ],
        egress=[
            aws.ec2.SecurityGroupEgressArgs(
                protocol="-1",
                from_port=0,
                to_port=0,
                cidr_blocks=["0.0.0.0/0"]
            )
        ],
        tags={**COMMON_TAGS, "Name": f"{PROJECT_NAME}-alb-sg"}
    )
    
    # Create ALB
    alb = aws.lb.LoadBalancer(
        f"{PROJECT_NAME}-alb",
        name=f"{PROJECT_NAME}-alb",
        load_balancer_type="application",
        scheme="internet-facing",
        security_groups=[alb_sg.id],
        subnets=public_subnet_ids,
        enable_deletion_protection=ALB_DELETION_PROTECTION,
        idle_timeout=ALB_IDLE_TIMEOUT,
        tags={**COMMON_TAGS, "Name": f"{PROJECT_NAME}-alb"}
    )
    
    # Create target group
    target_group = aws.lb.TargetGroup(
        f"{PROJECT_NAME}-tg",
        name=f"{PROJECT_NAME}-tg",
        port=APP_PORT,
        protocol="HTTP",
        vpc_id=vpc_id,
        target_type="ip",
        health_check=aws.lb.TargetGroupHealthCheckArgs(
            enabled=True,
            healthy_threshold=2,
            unhealthy_threshold=2,
            timeout=5,
            interval=30,
            path=HEALTH_CHECK_PATH,
            matcher="200",
            protocol="HTTP",
            port="traffic-port"
        ),
        tags={**COMMON_TAGS, "Name": f"{PROJECT_NAME}-tg"}
    )
    
    # Create IAM role for ALB to access Secrets Manager
    alb_role = aws.iam.Role(
        f"{PROJECT_NAME}-alb-role",
        assume_role_policy=json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Action": "sts:AssumeRole",
                "Effect": "Allow",
                "Principal": {
                    "Service": "elasticloadbalancing.amazonaws.com"
                }
            }]
        }),
        tags={**COMMON_TAGS, "Name": f"{PROJECT_NAME}-alb-role"}
    )
    
    # Create policy for ALB to access secrets
    alb_policy = aws.iam.RolePolicy(
        f"{PROJECT_NAME}-alb-policy",
        role=alb_role.id,
        policy=jwt_secret_arn.apply(
            lambda arn: json.dumps({
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Action": [
                        "secretsmanager:GetSecretValue"
                    ],
                    "Resource": arn
                }]
            })
        )
    )
    
    # Create Lambda function for JWT validation
    jwt_validation_role = aws.iam.Role(
        f"{PROJECT_NAME}-jwt-validation-role",
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
        tags={**COMMON_TAGS, "Name": f"{PROJECT_NAME}-jwt-validation-role"}
    )
    
    aws.iam.RolePolicyAttachment(
        f"{PROJECT_NAME}-jwt-validation-role-basic-execution",
        role=jwt_validation_role.name,
        policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
    )
    
    jwt_validation_policy = aws.iam.RolePolicy(
        f"{PROJECT_NAME}-jwt-validation-policy",
        role=jwt_validation_role.id,
        policy=jwt_secret_arn.apply(
            lambda arn: json.dumps({
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Action": [
                        "secretsmanager:GetSecretValue"
                    ],
                    "Resource": arn
                }]
            })
        )
    )
    
    jwt_validation_lambda = aws.lambda_.Function(
        f"{PROJECT_NAME}-jwt-validation-lambda",
        name=f"{PROJECT_NAME}-jwt-validation-lambda",
        runtime="python3.11",
        handler="index.lambda_handler",
        role=jwt_validation_role.arn,
        code=pulumi.AssetArchive({
            "index.py": pulumi.StringAsset(get_jwt_validation_lambda_code())
        }),
        environment=aws.lambda_.FunctionEnvironmentArgs(
            variables={
                "JWT_SECRET_ARN": jwt_secret_arn
            }
        ),
        timeout=30,
        tags={**COMMON_TAGS, "Name": f"{PROJECT_NAME}-jwt-validation-lambda"}
    )
    
    # Create ALB listener with JWT validation
    listener = aws.lb.Listener(
        f"{PROJECT_NAME}-listener",
        load_balancer_arn=alb.arn,
        port="80",
        protocol="HTTP",
        default_actions=[
            aws.lb.ListenerDefaultActionArgs(
                type="authenticate-cognito",
                authenticate_cognito=aws.lb.ListenerDefaultActionAuthenticateCognitoArgs(
                    user_pool_arn="",  # Will be set up separately if needed
                    user_pool_client_id="",
                    user_pool_domain=""
                ),
                order=1
            ),
            aws.lb.ListenerDefaultActionArgs(
                type="forward",
                target_group_arn=target_group.arn,
                order=2
            )
        ]
    )
    
    # Create listener rule for JWT validation
    listener_rule = aws.lb.ListenerRule(
        f"{PROJECT_NAME}-jwt-rule",
        listener_arn=listener.arn,
        priority=100,
        actions=[
            aws.lb.ListenerRuleActionArgs(
                type="authenticate-oidc",
                authenticate_oidc=aws.lb.ListenerRuleActionAuthenticateOidcArgs(
                    authorization_endpoint="https://example.com/auth",
                    client_id="dummy",
                    client_secret="dummy",
                    issuer="https://example.com",
                    token_endpoint="https://example.com/token",
                    user_info_endpoint="https://example.com/userinfo"
                ),
                order=1
            ),
            aws.lb.ListenerRuleActionArgs(
                type="forward",
                target_group_arn=target_group.arn,
                order=2
            )
        ],
        conditions=[
            aws.lb.ListenerRuleConditionArgs(
                path_pattern=aws.lb.ListenerRuleConditionPathPatternArgs(
                    values=["/*"]
                )
            )
        ]
    )
    
    return {
        "alb_arn": alb.arn,
        "alb_dns_name": alb.dns_name,
        "target_group_arn": target_group.arn,
        "alb_security_group_id": alb_sg.id,
        "jwt_validation_lambda_arn": jwt_validation_lambda.arn
    }

def get_jwt_validation_lambda_code():
    """Return the Lambda function code for JWT validation"""
    return '''
import json
import jwt
import boto3
import os
from datetime import datetime

def lambda_handler(event, context):
    """Validate JWT token from CloudFront headers"""
    
    try:
        # Get JWT secret from Secrets Manager
        secrets_client = boto3.client('secretsmanager')
        secret_arn = os.environ['JWT_SECRET_ARN']
        
        secret_response = secrets_client.get_secret_value(SecretArn=secret_arn)
        secret_data = json.loads(secret_response['SecretString'])
        jwt_secret = secret_data['jwt_secret_key']
        
        # Extract JWT from headers
        headers = event.get('headers', {})
        auth_header = headers.get('authorization', '')
        
        if not auth_header.startswith('Bearer '):
            return {
                'statusCode': 401,
                'body': json.dumps({'error': 'Missing or invalid authorization header'})
            }
        
        token = auth_header.split(' ')[1]
        
        # Validate JWT
        try:
            payload = jwt.decode(token, jwt_secret, algorithms=['HS256'])
            
            # Check expiration
            if payload.get('exp', 0) < datetime.utcnow().timestamp():
                return {
                    'statusCode': 401,
                    'body': json.dumps({'error': 'Token expired'})
                }
            
            # Token is valid
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'Token valid', 'user': payload.get('sub', 'unknown')})
            }
            
        except jwt.InvalidTokenError as e:
            return {
                'statusCode': 401,
                'body': json.dumps({'error': f'Invalid token: {str(e)}'})
            }
            
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Internal server error: {str(e)}'})
        }
'''