"""
Pulumi Infrastructure for CloudFront Function + JWT Security Approach
Deploys AWS resources for secure CDN-to-ALB communication using JWT validation at edge
"""
import pulumi
import pulumi_aws as aws
import json
import base64

# Configuration
config = pulumi.Config()
project_name = pulumi.get_project()
stack_name = pulumi.get_stack()

# Tags for all resources
common_tags = {
    "Project": project_name,
    "Stack": stack_name,
    "Purpose": "CloudFront-JWT-Security"
}

# VPC and Networking
vpc = aws.ec2.Vpc("demo-vpc",
    cidr_block="10.0.0.0/16",
    enable_dns_hostnames=True,
    enable_dns_support=True,
    tags={**common_tags, "Name": f"{project_name}-vpc"}
)

# Public subnets for ALB
public_subnet_1 = aws.ec2.Subnet("public-subnet-1",
    vpc_id=vpc.id,
    cidr_block="10.0.1.0/24",
    availability_zone="us-east-1a",
    map_public_ip_on_launch=True,
    tags={**common_tags, "Name": f"{project_name}-public-1"}
)

public_subnet_2 = aws.ec2.Subnet("public-subnet-2",
    vpc_id=vpc.id,
    cidr_block="10.0.2.0/24",
    availability_zone="us-east-1b",
    map_public_ip_on_launch=True,
    tags={**common_tags, "Name": f"{project_name}-public-2"}
)

# Private subnets for EC2 instances
private_subnet_1 = aws.ec2.Subnet("private-subnet-1",
    vpc_id=vpc.id,
    cidr_block="10.0.3.0/24",
    availability_zone="us-east-1a",
    tags={**common_tags, "Name": f"{project_name}-private-1"}
)

private_subnet_2 = aws.ec2.Subnet("private-subnet-2",
    vpc_id=vpc.id,
    cidr_block="10.0.4.0/24",
    availability_zone="us-east-1b",
    tags={**common_tags, "Name": f"{project_name}-private-2"}
)

# Internet Gateway
igw = aws.ec2.InternetGateway("demo-igw",
    vpc_id=vpc.id,
    tags={**common_tags, "Name": f"{project_name}-igw"}
)

# Route table for public subnets
public_route_table = aws.ec2.RouteTable("public-rt",
    vpc_id=vpc.id,
    routes=[
        aws.ec2.RouteTableRouteArgs(
            cidr_block="0.0.0.0/0",
            gateway_id=igw.id,
        )
    ],
    tags={**common_tags, "Name": f"{project_name}-public-rt"}
)

# Associate public subnets with route table
aws.ec2.RouteTableAssociation("public-rta-1",
    subnet_id=public_subnet_1.id,
    route_table_id=public_route_table.id
)

aws.ec2.RouteTableAssociation("public-rta-2",
    subnet_id=public_subnet_2.id,
    route_table_id=public_route_table.id
)

# Security Groups
alb_security_group = aws.ec2.SecurityGroup("alb-sg",
    name_prefix=f"{project_name}-alb-",
    vpc_id=vpc.id,
    description="Security group for Application Load Balancer",
    ingress=[
        aws.ec2.SecurityGroupIngressArgs(
            protocol="tcp",
            from_port=80,
            to_port=80,
            cidr_blocks=["0.0.0.0/0"],
        ),
        aws.ec2.SecurityGroupIngressArgs(
            protocol="tcp",
            from_port=443,
            to_port=443,
            cidr_blocks=["0.0.0.0/0"],
        ),
    ],
    egress=[
        aws.ec2.SecurityGroupEgressArgs(
            protocol="-1",
            from_port=0,
            to_port=0,
            cidr_blocks=["0.0.0.0/0"],
        ),
    ],
    tags={**common_tags, "Name": f"{project_name}-alb-sg"}
)

ec2_security_group = aws.ec2.SecurityGroup("ec2-sg",
    name_prefix=f"{project_name}-ec2-",
    vpc_id=vpc.id,
    description="Security group for EC2 instances",
    ingress=[
        aws.ec2.SecurityGroupIngressArgs(
            protocol="tcp",
            from_port=80,
            to_port=80,
            security_groups=[alb_security_group.id],
        ),
    ],
    egress=[
        aws.ec2.SecurityGroupEgressArgs(
            protocol="-1",
            from_port=0,
            to_port=0,
            cidr_blocks=["0.0.0.0/0"],
        ),
    ],
    tags={**common_tags, "Name": f"{project_name}-ec2-sg"}
)

# IAM Role for EC2 instances
ec2_role = aws.iam.Role("ec2-role",
    assume_role_policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Action": "sts:AssumeRole",
                "Effect": "Allow",
                "Principal": {
                    "Service": "ec2.amazonaws.com"
                }
            }
        ]
    }),
    tags=common_tags
)

# Attach basic EC2 policy
aws.iam.RolePolicyAttachment("ec2-policy",
    role=ec2_role.name,
    policy_arn="arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
)

# Instance profile
ec2_instance_profile = aws.iam.InstanceProfile("ec2-profile",
    role=ec2_role.name
)

# User data script for EC2 instances
user_data = """#!/bin/bash
yum update -y
yum install -y httpd
systemctl start httpd
systemctl enable httpd

# Create a simple web page
cat > /var/www/html/index.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>CDN Security Demo Backend</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .header { background: #f0f0f0; padding: 20px; border-radius: 5px; }
        .info { margin: 20px 0; padding: 15px; background: #e8f4fd; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 JWT Security Demo - Backend Service</h1>
        <p>This backend service is protected by CloudFront JWT validation</p>
    </div>
    
    <div class="info">
        <h3>Request Headers:</h3>
        <pre id="headers"></pre>
    </div>
    
    <div class="info">
        <h3>Server Info:</h3>
        <p><strong>Instance ID:</strong> <span id="instance-id">Loading...</span></p>
        <p><strong>Timestamp:</strong> <span id="timestamp"></span></p>
    </div>

    <script>
        // Display current timestamp
        document.getElementById('timestamp').textContent = new Date().toISOString();
        
        // Try to get instance metadata (may not work in all environments)
        fetch('/latest/meta-data/instance-id')
            .then(response => response.text())
            .then(data => document.getElementById('instance-id').textContent = data)
            .catch(() => document.getElementById('instance-id').textContent = 'Not available');
    </script>
</body>
</html>
EOF

# Create a simple API endpoint to show headers
cat > /var/www/html/api.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>JWT Validation Demo API</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .success { background: #d4edda; padding: 15px; border-radius: 5px; color: #155724; }
        .info { background: #e8f4fd; padding: 15px; border-radius: 5px; margin: 10px 0; }
    </style>
</head>
<body>
    <div class="success">
        <h2>✅ JWT Validation Successful!</h2>
        <p>This request was validated by CloudFront Function</p>
    </div>
    
    <div class="info">
        <h3>Validated Headers:</h3>
        <p><strong>User:</strong> <span id="user">Loading...</span></p>
        <p><strong>Auth Method:</strong> <span id="auth">Loading...</span></p>
        <p><strong>JWT Validated:</strong> <span id="validated">Loading...</span></p>
    </div>

    <script>
        // This would normally be populated by server-side code
        // For demo purposes, showing static success message
        document.getElementById('user').textContent = 'demo-user';
        document.getElementById('auth').textContent = 'jwt-cloudfront-function';
        document.getElementById('validated').textContent = 'true';
    </script>
</body>
</html>
EOF
"""

# Launch Template for Auto Scaling
launch_template = aws.ec2.LaunchTemplate("demo-lt",
    name_prefix=f"{project_name}-lt-",
    image_id="ami-0c02fb55956c7d316",  # Amazon Linux 2 AMI
    instance_type="t3.micro",
    vpc_security_group_ids=[ec2_security_group.id],
    iam_instance_profile=aws.ec2.LaunchTemplateIamInstanceProfileArgs(
        name=ec2_instance_profile.name
    ),
    user_data=base64.b64encode(user_data.encode()).decode(),
    tags={**common_tags, "Name": f"{project_name}-lt"}
)

# Auto Scaling Group
asg = aws.autoscaling.Group("demo-asg",
    name=f"{project_name}-asg",
    vpc_zone_identifiers=[private_subnet_1.id, private_subnet_2.id],
    target_group_arns=[],  # Will be updated after ALB creation
    health_check_type="ELB",
    health_check_grace_period=300,
    min_size=2,
    max_size=4,
    desired_capacity=2,
    launch_template=aws.autoscaling.GroupLaunchTemplateArgs(
        id=launch_template.id,
        version="$Latest"
    ),
    tags=[
        aws.autoscaling.GroupTagArgs(
            key="Name",
            value=f"{project_name}-asg-instance",
            propagate_at_launch=True
        )
    ]
)

# Application Load Balancer
alb = aws.lb.LoadBalancer("demo-alb",
    name=f"{project_name}-alb",
    load_balancer_type="application",
    subnets=[public_subnet_1.id, public_subnet_2.id],
    security_groups=[alb_security_group.id],
    tags={**common_tags, "Name": f"{project_name}-alb"}
)

# Target Group
target_group = aws.lb.TargetGroup("demo-tg",
    name=f"{project_name}-tg",
    port=80,
    protocol="HTTP",
    vpc_id=vpc.id,
    health_check=aws.lb.TargetGroupHealthCheckArgs(
        enabled=True,
        healthy_threshold=2,
        interval=30,
        matcher="200",
        path="/",
        port="traffic-port",
        protocol="HTTP",
        timeout=5,
        unhealthy_threshold=2,
    ),
    tags={**common_tags, "Name": f"{project_name}-tg"}
)

# Update ASG with target group
asg_attachment = aws.autoscaling.Attachment("asg-attachment",
    autoscaling_group_name=asg.id,
    lb_target_group_arn=target_group.arn
)

# ALB Listener - Simple HTTP listener (no custom header validation)
# CloudFront will handle all authentication via JWT validation
alb_listener = aws.lb.Listener("alb-listener",
    load_balancer_arn=alb.arn,
    port="80",
    protocol="HTTP",
    default_actions=[
        aws.lb.ListenerDefaultActionArgs(
            type="forward",
            target_group_arn=target_group.arn
        )
    ],
    tags=common_tags
)

# CloudFront Function for JWT validation
cloudfront_function_code = """
function handler(event) {
    var request = event.request;
    var headers = request.headers;
    
    // Check for Authorization header with JWT
    if (!headers.authorization) {
        return {
            statusCode: 401,
            statusDescription: 'Unauthorized',
            body: {
                encoding: 'text',
                data: JSON.stringify({
                    error: 'Missing Authorization header',
                    message: 'JWT token required for access'
                })
            },
            headers: {
                'content-type': { value: 'application/json' },
                'cache-control': { value: 'no-cache' }
            }
        };
    }
    
    var authHeader = headers.authorization.value;
    
    // Validate Bearer token format
    if (!authHeader.startsWith('Bearer ')) {
        return {
            statusCode: 401,
            statusDescription: 'Unauthorized',
            body: {
                encoding: 'text',
                data: JSON.stringify({
                    error: 'Invalid Authorization format',
                    message: 'Bearer token required'
                })
            },
            headers: {
                'content-type': { value: 'application/json' },
                'cache-control': { value: 'no-cache' }
            }
        };
    }
    
    var token = authHeader.substring(7); // Remove 'Bearer '
    
    // JWT structure validation (header.payload.signature)
    var parts = token.split('.');
    if (parts.length !== 3) {
        return {
            statusCode: 401,
            statusDescription: 'Unauthorized',
            body: {
                encoding: 'text',
                data: JSON.stringify({
                    error: 'Invalid JWT format',
                    message: 'JWT must have 3 parts (header.payload.signature)'
                })
            },
            headers: {
                'content-type': { value: 'application/json' },
                'cache-control': { value: 'no-cache' }
            }
        };
    }
    
    // Validate base64 encoding of JWT parts
    try {
        // Decode header and payload to validate structure
        var header = JSON.parse(atob(parts[0]));
        var payload = JSON.parse(atob(parts[1]));
        
        // Basic JWT validation
        if (!header.alg || !header.typ) {
            throw new Error('Invalid JWT header');
        }
        
        if (!payload.sub && !payload.user) {
            throw new Error('Invalid JWT payload - missing subject');
        }
        
        // Check expiration if present
        if (payload.exp && payload.exp < Math.floor(Date.now() / 1000)) {
            return {
                statusCode: 401,
                statusDescription: 'Unauthorized',
                body: {
                    encoding: 'text',
                    data: JSON.stringify({
                        error: 'Token expired',
                        message: 'JWT token has expired'
                    })
                },
                headers: {
                    'content-type': { value: 'application/json' },
                    'cache-control': { value: 'no-cache' }
                }
            };
        }
        
    } catch (e) {
        return {
            statusCode: 401,
            statusDescription: 'Unauthorized',
            body: {
                encoding: 'text',
                data: JSON.stringify({
                    error: 'Invalid JWT structure',
                    message: 'JWT parsing failed: ' + e.message
                })
            },
            headers: {
                'content-type': { value: 'application/json' },
                'cache-control': { value: 'no-cache' }
            }
        };
    }
    
    // Add validated user info to request headers for ALB
    request.headers['x-validated-user'] = { value: payload.sub || payload.user || 'unknown' };
    request.headers['x-auth-method'] = { value: 'jwt-cloudfront-function' };
    request.headers['x-jwt-validated'] = { value: 'true' };
    
    return request;
}

// Helper function for base64 decoding (CloudFront Functions don't have Buffer)
function atob(str) {
    // Simple base64 decode for CloudFront Functions
    var chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
    var result = '';
    var i = 0;
    
    str = str.replace(/[^A-Za-z0-9+/]/g, '');
    
    while (i < str.length) {
        var a = chars.indexOf(str.charAt(i++));
        var b = chars.indexOf(str.charAt(i++));
        var c = chars.indexOf(str.charAt(i++));
        var d = chars.indexOf(str.charAt(i++));
        
        var bitmap = (a << 18) | (b << 12) | (c << 6) | d;
        
        result += String.fromCharCode((bitmap >> 16) & 255);
        if (c !== 64) result += String.fromCharCode((bitmap >> 8) & 255);
        if (d !== 64) result += String.fromCharCode(bitmap & 255);
    }
    
    return result;
}
"""

# CloudFront Function for JWT validation
cloudfront_function = aws.cloudfront.Function("jwt-validator",
    name=f"{project_name}-jwt-validator",
    runtime="cloudfront-js-1.0",
    comment="JWT validation function for secure CDN-to-ALB communication",
    publish=True,
    code=cloudfront_function_code
)

# S3 bucket removed - not needed for JWT validation demo

# CloudFront Distribution with JWT Validation
cloudfront_distribution = aws.cloudfront.Distribution("jwt-cloudfront",
    aliases=[],
    comment="Secure CDN with JWT validation at edge",
    default_cache_behavior=aws.cloudfront.DistributionDefaultCacheBehaviorArgs(
        allowed_methods=["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"],
        cached_methods=["GET", "HEAD"],
        target_origin_id="alb-origin",
        compress=True,
        viewer_protocol_policy="redirect-to-https",
        cache_policy_id="4135ea2d-6df8-44a3-9df3-4b5a84be39ad",  # CachingDisabled for demo
        function_associations=[
            aws.cloudfront.DistributionDefaultCacheBehaviorFunctionAssociationArgs(
                event_type="viewer-request",
                function_arn=cloudfront_function.arn
            )
        ]
    ),
    origins=[
        aws.cloudfront.DistributionOriginArgs(
            domain_name=alb.dns_name,
            origin_id="alb-origin",
            custom_origin_config=aws.cloudfront.DistributionOriginCustomOriginConfigArgs(
                http_port=80,
                https_port=443,
                origin_protocol_policy="http-only",
                origin_ssl_protocols=["TLSv1.2"],
                origin_keepalive_timeout=5,
                origin_read_timeout=30
            )
        )
    ],
    restrictions=aws.cloudfront.DistributionRestrictionsArgs(
        geo_restriction=aws.cloudfront.DistributionRestrictionsGeoRestrictionArgs(
            restriction_type="none"
        )
    ),
    viewer_certificate=aws.cloudfront.DistributionViewerCertificateArgs(
        cloudfront_default_certificate=True
    ),
    enabled=True,
    price_class="PriceClass_100",  # Use only North America and Europe for cost optimization
    tags={**common_tags, "Name": f"{project_name}-jwt-cloudfront"}
)

# Outputs
pulumi.export("vpc_id", vpc.id)
pulumi.export("alb_dns_name", alb.dns_name)
pulumi.export("alb_zone_id", alb.zone_id)
pulumi.export("cloudfront_domain_name", cloudfront_distribution.domain_name)
pulumi.export("cloudfront_distribution_id", cloudfront_distribution.id)
pulumi.export("cloudfront_function_name", cloudfront_function.name)
# S3 bucket removed

# Demo URLs and test commands
pulumi.export("demo_urls", {
    "alb_direct_insecure": pulumi.Output.concat("http://", alb.dns_name),
    "cloudfront_secure": pulumi.Output.concat("https://", cloudfront_distribution.domain_name),
})

# Sample JWT for testing (in production, generate proper signed JWTs)
sample_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkZW1vLXVzZXIiLCJuYW1lIjoiSm9obiBEb2UiLCJpYXQiOjE1MTYyMzkwMjIsImV4cCI6OTk5OTk5OTk5OX0.Lf8kFRC6pJaXdIGJsKq7LwbvJsKq7LwbvJsKq7LwbvJs"

pulumi.export("test_commands", {
    "test_without_jwt": pulumi.Output.concat("curl -v https://", cloudfront_distribution.domain_name),
    "test_with_jwt": pulumi.Output.concat("curl -v -H 'Authorization: Bearer ", sample_jwt, "' https://", cloudfront_distribution.domain_name),
    "test_alb_direct": pulumi.Output.concat("curl -v http://", alb.dns_name)
})

pulumi.export("sample_jwt_token", sample_jwt)