"""
IAM Module - Creates IAM roles and policies for EC2 instances
All resources deployed in the specified region (default: ap-south-2)
"""
import pulumi_aws as aws
import json

def create_iam_resources(config):
    """Create IAM role and instance profile for EC2 instances"""
    
    project_name = config["project_name"]
    common_tags = config["common_tags"]
    
    # IAM Role for EC2 instances
    ec2_role = aws.iam.Role("ec2-role",
        name=f"{project_name}-ec2-role",
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
    
    # Attach SSM managed instance core policy for remote access
    aws.iam.RolePolicyAttachment("ec2-ssm-policy",
        role=ec2_role.name,
        policy_arn="arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
    )
    
    # Attach CloudWatch agent policy for monitoring
    aws.iam.RolePolicyAttachment("ec2-cloudwatch-policy",
        role=ec2_role.name,
        policy_arn="arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
    )
    
    # Custom policy for additional permissions if needed
    ec2_custom_policy = aws.iam.Policy("ec2-custom-policy",
        name=f"{project_name}-ec2-custom-policy",
        description="Custom policy for EC2 instances in JWT security demo",
        policy=json.dumps({
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                        "logs:DescribeLogStreams"
                    ],
                    "Resource": "arn:aws:logs:*:*:*"
                }
            ]
        }),
        tags=common_tags
    )
    
    # Attach custom policy to role
    aws.iam.RolePolicyAttachment("ec2-custom-policy-attachment",
        role=ec2_role.name,
        policy_arn=ec2_custom_policy.arn
    )
    
    # Instance profile
    ec2_instance_profile = aws.iam.InstanceProfile("ec2-profile",
        name=f"{project_name}-ec2-profile",
        role=ec2_role.name,
        tags=common_tags
    )
    
    return {
        "ec2_role": ec2_role,
        "ec2_instance_profile": ec2_instance_profile,
        "ec2_custom_policy": ec2_custom_policy
    }