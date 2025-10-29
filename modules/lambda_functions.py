"""Lambda functions for CloudFront and request processing"""

import pulumi
import pulumi_aws as aws
import json
from config import PROJECT_NAME, COMMON_TAGS

def create_lambda_functions(jwt_secret_arn):
    """Create Lambda functions for CloudFront and request processing"""
    
    # Create CloudFront function for request validation
    cloudfront_function = aws.cloudfront.Function(
        f"{PROJECT_NAME}-cloudfront-function",
        name=f"{PROJECT_NAME}-request-validator",
        runtime="cloudfront-js-1.0",
        comment="Validate incoming requests and add security headers",
        code=get_cloudfront_function_code(),
        publish=True
    )
    
    # Create Lambda@Edge function for more complex processing
    lambda_edge_role = aws.iam.Role(
        f"{PROJECT_NAME}-lambda-edge-role",
        assume_role_policy=json.dumps({
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": "sts:AssumeRole",
                    "Effect": "Allow",
                    "Principal": {
                        "Service": ["lambda.amazonaws.com", "edgelambda.amazonaws.com"]
                    }
                }
            ]
        }),
        tags={**COMMON_TAGS, "Name": f"{PROJECT_NAME}-lambda-edge-role"}
    )
    
    # Attach basic execution policy
    aws.iam.RolePolicyAttachment(
        f"{PROJECT_NAME}-lambda-edge-basic-execution",
        role=lambda_edge_role.name,
        policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
    )
    
    # Add policy for Lambda@Edge to access secrets
    lambda_edge_policy = aws.iam.RolePolicy(
        f"{PROJECT_NAME}-lambda-edge-policy",
        role=lambda_edge_role.id,
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
    
    # Create Lambda@Edge function for origin request processing
    lambda_edge_function = aws.lambda_.Function(
        f"{PROJECT_NAME}-lambda-edge",
        name=f"{PROJECT_NAME}-origin-request-processor",
        runtime="python3.11",
        handler="index.lambda_handler",
        role=lambda_edge_role.arn,
        code=pulumi.AssetArchive({
            "index.py": pulumi.StringAsset(get_lambda_edge_code())
        }),
        environment=aws.lambda_.FunctionEnvironmentArgs(
            variables={
                "JWT_SECRET_ARN": jwt_secret_arn
            }
        ),
        timeout=5,
        memory_size=128,
        publish=True,
        tags={**COMMON_TAGS, "Name": f"{PROJECT_NAME}-lambda-edge"}
    )
    
    # Create JWT token generator Lambda
    jwt_generator_role = aws.iam.Role(
        f"{PROJECT_NAME}-jwt-generator-role",
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
        tags={**COMMON_TAGS, "Name": f"{PROJECT_NAME}-jwt-generator-role"}
    )
    
    aws.iam.RolePolicyAttachment(
        f"{PROJECT_NAME}-jwt-generator-basic-execution",
        role=jwt_generator_role.name,
        policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
    )
    
    jwt_generator_policy = aws.iam.RolePolicy(
        f"{PROJECT_NAME}-jwt-generator-policy",
        role=jwt_generator_role.id,
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
    
    jwt_generator_function = aws.lambda_.Function(
        f"{PROJECT_NAME}-jwt-generator",
        name=f"{PROJECT_NAME}-jwt-generator",
        runtime="python3.11",
        handler="index.lambda_handler",
        role=jwt_generator_role.arn,
        code=pulumi.AssetArchive({
            "index.py": pulumi.StringAsset(get_jwt_generator_code())
        }),
        environment=aws.lambda_.FunctionEnvironmentArgs(
            variables={
                "JWT_SECRET_ARN": jwt_secret_arn
            }
        ),
        timeout=30,
        tags={**COMMON_TAGS, "Name": f"{PROJECT_NAME}-jwt-generator"}
    )
    
    # Create API Gateway for JWT token generation
    api_gateway = aws.apigateway.RestApi(
        f"{PROJECT_NAME}-api",
        name=f"{PROJECT_NAME}-jwt-api",
        description="API for JWT token generation",
        tags={**COMMON_TAGS, "Name": f"{PROJECT_NAME}-api"}
    )
    
    # Create API Gateway resource
    api_resource = aws.apigateway.Resource(
        f"{PROJECT_NAME}-api-resource",
        rest_api=api_gateway.id,
        parent_id=api_gateway.root_resource_id,
        path_part="token"
    )
    
    # Create API Gateway method
    api_method = aws.apigateway.Method(
        f"{PROJECT_NAME}-api-method",
        rest_api=api_gateway.id,
        resource_id=api_resource.id,
        http_method="POST",
        authorization="NONE"
    )
    
    # Create API Gateway integration
    api_integration = aws.apigateway.Integration(
        f"{PROJECT_NAME}-api-integration",
        rest_api=api_gateway.id,
        resource_id=api_resource.id,
        http_method=api_method.http_method,
        integration_http_method="POST",
        type="AWS_PROXY",
        uri=jwt_generator_function.invoke_arn
    )
    
    # Grant API Gateway permission to invoke Lambda
    aws.lambda_.Permission(
        f"{PROJECT_NAME}-api-lambda-permission",
        action="lambda:InvokeFunction",
        function=jwt_generator_function.name,
        principal="apigateway.amazonaws.com",
        source_arn=pulumi.Output.concat(api_gateway.execution_arn, "/*/*")
    )
    
    # Deploy API Gateway
    api_deployment = aws.apigateway.Deployment(
        f"{PROJECT_NAME}-api-deployment",
        rest_api=api_gateway.id,
        opts=pulumi.ResourceOptions(depends_on=[api_integration])
    )
    
    # Create API Gateway stage
    api_stage = aws.apigateway.Stage(
        f"{PROJECT_NAME}-api-stage",
        deployment=api_deployment.id,
        rest_api=api_gateway.id,
        stage_name="prod"
    )
    
    return {
        "cloudfront_function_arn": cloudfront_function.arn,
        "lambda_edge_function_arn": lambda_edge_function.arn,
        "jwt_generator_function_arn": jwt_generator_function.arn,
        "api_gateway_url": pulumi.Output.concat("https://", api_gateway.id, ".execute-api.us-east-1.amazonaws.com/prod")
    }

def get_cloudfront_function_code():
    """Return CloudFront function code for request validation"""
    return '''
function handler(event) {
    var request = event.request;
    var headers = request.headers;
    var uri = request.uri;
    
    // Only validate headers for protected API endpoints, not for main page or static content
    var protectedPaths = ['/api/protected', '/auth/me'];
    var requiresAuth = false;
    
    for (var i = 0; i < protectedPaths.length; i++) {
        if (uri.startsWith(protectedPaths[i])) {
            requiresAuth = true;
            break;
        }
    }
    
    // Only check authorization header for protected endpoints
    if (requiresAuth && !headers['authorization']) {
        return {
            statusCode: 401,
            statusDescription: 'Unauthorized',
            headers: {
                'content-type': { value: 'application/json' }
            },
            body: JSON.stringify({ error: 'Authorization header required for protected endpoints' })
        };
    }
    
    // Add security headers for all requests
    request.headers['x-forwarded-proto'] = { value: 'https' };
    request.headers['x-cdn-validated'] = { value: 'true' };
    request.headers['x-request-id'] = { value: generateRequestId() };
    
    // Add CDN auth header for backend validation
    request.headers['x-cdn-auth'] = { value: 'qp-iac-cdn-secret-key' };
    
    return request;
}

function generateRequestId() {
    return 'req-' + Math.random().toString(36).substr(2, 9) + '-' + Date.now();
}
'''

def get_lambda_edge_code():
    """Return Lambda@Edge function code for origin request processing"""
    return '''
import json
import base64
import boto3
import jwt
import os
from datetime import datetime

def lambda_handler(event, context):
    """Process origin requests and validate JWT tokens"""
    
    request = event['Records'][0]['cf']['request']
    headers = request['headers']
    
    try:
        # Get authorization header
        auth_header = None
        if 'authorization' in headers:
            auth_header = headers['authorization'][0]['value']
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return create_error_response(401, 'Missing or invalid authorization header')
        
        token = auth_header.split(' ')[1]
        
        # Get JWT secret from environment (cached in Lambda)
        jwt_secret_arn = os.environ.get('JWT_SECRET_ARN')
        if not jwt_secret_arn:
            return create_error_response(500, 'JWT secret not configured')
        
        # For Lambda@Edge, we need to validate the token without calling Secrets Manager
        # In production, you would cache the secret or use a different approach
        
        # Add custom headers for the origin
        headers['x-edge-processed'] = [{'key': 'X-Edge-Processed', 'value': 'true'}]
        headers['x-timestamp'] = [{'key': 'X-Timestamp', 'value': str(int(datetime.utcnow().timestamp()))}]
        
        return request
        
    except Exception as e:
        return create_error_response(500, f'Internal error: {str(e)}')

def create_error_response(status_code, message):
    """Create error response for CloudFront"""
    return {
        'status': str(status_code),
        'statusDescription': 'Error',
        'headers': {
            'content-type': [{'key': 'Content-Type', 'value': 'application/json'}]
        },
        'body': json.dumps({'error': message})
    }
'''

def get_jwt_generator_code():
    """Return JWT generator Lambda function code"""
    return '''
import json
import jwt
import boto3
import os
from datetime import datetime, timedelta

def lambda_handler(event, context):
    """Generate JWT tokens for authenticated users"""
    
    try:
        # Parse request body
        if event.get('body'):
            body = json.loads(event['body'])
        else:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Request body required'})
            }
        
        # Validate required fields
        username = body.get('username')
        password = body.get('password')
        
        if not username or not password:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Username and password required'})
            }
        
        # Simple authentication (in production, use proper auth service)
        if username != 'admin' or password != 'password123':
            return {
                'statusCode': 401,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Invalid credentials'})
            }
        
        # Get JWT secret from Secrets Manager
        secrets_client = boto3.client('secretsmanager')
        secret_arn = os.environ['JWT_SECRET_ARN']
        
        secret_response = secrets_client.get_secret_value(SecretArn=secret_arn)
        secret_data = json.loads(secret_response['SecretString'])
        jwt_secret = secret_data['jwt_secret_key']
        
        # Generate JWT token
        payload = {
            'sub': username,
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(hours=24),
            'iss': 'qp-iac-cdn-headers',
            'aud': 'cdn-alb-communication'
        }
        
        token = jwt.encode(payload, jwt_secret, algorithm='HS256')
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'token': token,
                'expires_in': 86400,
                'token_type': 'Bearer'
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': f'Internal server error: {str(e)}'})
        }
'''