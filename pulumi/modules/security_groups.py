"""
Security Groups Module - Creates security groups for ALB and EC2 instances
All resources deployed in the specified region (default: ap-south-2)
"""
import pulumi_aws as aws

def create_security_groups(config, vpc_id):
    """Create security groups for ALB and EC2 instances"""
    
    project_name = config["project_name"]
    common_tags = config["common_tags"]
    
    # ALB Security Group
    alb_security_group = aws.ec2.SecurityGroup("alb-sg",
        name_prefix=f"{project_name}-alb-",
        vpc_id=vpc_id,
        description="Security group for Application Load Balancer",
        ingress=[
            aws.ec2.SecurityGroupIngressArgs(
                description="HTTP from anywhere",
                protocol="tcp",
                from_port=80,
                to_port=80,
                cidr_blocks=["0.0.0.0/0"],
            ),
            aws.ec2.SecurityGroupIngressArgs(
                description="HTTPS from anywhere",
                protocol="tcp",
                from_port=443,
                to_port=443,
                cidr_blocks=["0.0.0.0/0"],
            ),
        ],
        egress=[
            aws.ec2.SecurityGroupEgressArgs(
                description="All outbound traffic",
                protocol="-1",
                from_port=0,
                to_port=0,
                cidr_blocks=["0.0.0.0/0"],
            ),
        ],
        tags={**common_tags, "Name": f"{project_name}-alb-sg"}
    )
    
    # EC2 Security Group
    ec2_security_group = aws.ec2.SecurityGroup("ec2-sg",
        name_prefix=f"{project_name}-ec2-",
        vpc_id=vpc_id,
        description="Security group for EC2 instances",
        ingress=[
            aws.ec2.SecurityGroupIngressArgs(
                description="HTTP from ALB",
                protocol="tcp",
                from_port=80,
                to_port=80,
                security_groups=[alb_security_group.id],
            ),
            aws.ec2.SecurityGroupIngressArgs(
                description="HTTPS from ALB",
                protocol="tcp",
                from_port=443,
                to_port=443,
                security_groups=[alb_security_group.id],
            ),
        ],
        egress=[
            aws.ec2.SecurityGroupEgressArgs(
                description="All outbound traffic",
                protocol="-1",
                from_port=0,
                to_port=0,
                cidr_blocks=["0.0.0.0/0"],
            ),
        ],
        tags={**common_tags, "Name": f"{project_name}-ec2-sg"}
    )
    
    return {
        "alb_security_group": alb_security_group,
        "ec2_security_group": ec2_security_group
    }