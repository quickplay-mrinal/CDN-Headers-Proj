"""
Simplified Pulumi Infrastructure for CloudFront Function + JWT Security
Uses public subnets for EC2 to avoid NAT Gateway and EIP limits
All resources deployed in ap-south-2 region (except CloudFront which is global)
"""
import pulumi
import pulumi_aws as aws

# Import configuration and modules
from config import get_config, print_config_info
from modules.vpc_simple import create_simple_vpc
from modules.security_groups import create_security_groups
from modules.iam import create_iam_resources
from modules.ec2 import create_ec2_resources
from modules.ami import get_latest_amazon_linux_ami
from modules.alb import create_target_group_with_vpc
from modules.cloudfront import create_jwt_function, create_cloudfront_distribution, create_sample_jwt

def main():
    """Main function to deploy the infrastructure"""
    
    # Get configuration
    config = get_config()
    
    # Print configuration info
    print("Deploying CloudFront Function + JWT Security Infrastructure (Simplified)")
    print("=" * 70)
    print_config_info()
    print("Note: Using public subnets for EC2 to avoid NAT Gateway/EIP limits")
    print("=" * 70)
    
    # 1. Create VPC and networking (simplified - no NAT Gateway)
    print("Creating VPC and networking (simplified)...")
    vpc_resources = create_simple_vpc(config)
    vpc = vpc_resources["vpc"]
    public_subnets = vpc_resources["public_subnets"]
    private_subnets = vpc_resources["private_subnets"]
    
    # 2. Create security groups
    print("Creating security groups...")
    security_groups = create_security_groups(config, vpc.id)
    alb_security_group = security_groups["alb_security_group"]
    ec2_security_group = security_groups["ec2_security_group"]
    
    # 3. Create IAM resources
    print("Creating IAM resources...")
    iam_resources = create_iam_resources(config)
    ec2_instance_profile = iam_resources["ec2_instance_profile"]
    
    # 4. Create target group (needs VPC ID)
    print("Creating target group...")
    target_group = create_target_group_with_vpc(config, vpc.id)
    
    # 5. Create ALB
    print("Creating Application Load Balancer...")
    alb = aws.lb.LoadBalancer("jwt-alb",
        name=f"{config['project_name']}-alb",
        load_balancer_type="application",
        subnets=[subnet.id for subnet in public_subnets],
        security_groups=[alb_security_group.id],
        enable_deletion_protection=False,
        tags={**config["common_tags"], "Name": f"{config['project_name']}-alb"}
    )
    
    # ALB Listener
    alb_listener = aws.lb.Listener("jwt-alb-listener",
        load_balancer_arn=alb.arn,
        port="80",
        protocol="HTTP",
        default_actions=[
            aws.lb.ListenerDefaultActionArgs(
                type="forward",
                target_group_arn=target_group.arn
            )
        ],
        tags=config["common_tags"]
    )
    
    # 6. Create EC2 resources in PUBLIC subnets (direct internet access)
    print("Creating EC2 resources in public subnets...")
    ec2_resources = create_ec2_resources(
        config, 
        ec2_security_group.id, 
        ec2_instance_profile.name,
        [subnet.id for subnet in public_subnets],  # Use public subnets
        target_group.arn  # Pass target group ARN directly
    )
    asg = ec2_resources["auto_scaling_group"]
    asg_attachment = ec2_resources["asg_attachment"]
    
    print("Auto Scaling Group created and attached to target group...")
    
    # 7. Create CloudFront Function (Global service)
    print("Creating CloudFront Function for JWT validation...")
    cloudfront_function = create_jwt_function(config)
    
    # 8. Create CloudFront Distribution (Global service)
    print("Creating CloudFront Distribution...")
    cloudfront_distribution = create_cloudfront_distribution(
        config, 
        alb.dns_name, 
        cloudfront_function.arn
    )
    
    # 9. Create sample JWT for testing
    sample_jwt = create_sample_jwt()
    
    # Export outputs
    print("Exporting outputs...")
    
    # Infrastructure outputs
    pulumi.export("region", config["aws_region"])
    pulumi.export("vpc_id", vpc.id)
    pulumi.export("availability_zones", config["network_config"]["availability_zones"])
    pulumi.export("public_subnet_ids", [subnet.id for subnet in public_subnets])
    pulumi.export("private_subnet_ids", [subnet.id for subnet in private_subnets])
    pulumi.export("architecture", "simplified-public-subnets")
    
    # ALB outputs
    pulumi.export("alb_dns_name", alb.dns_name)
    pulumi.export("alb_zone_id", alb.zone_id)
    pulumi.export("target_group_arn", target_group.arn)
    
    # Security Group outputs for debugging
    pulumi.export("alb_security_group_id", alb_security_group.id)
    pulumi.export("ec2_security_group_id", ec2_security_group.id)
    
    # CloudFront outputs (Global)
    pulumi.export("cloudfront_domain_name", cloudfront_distribution.domain_name)
    pulumi.export("cloudfront_distribution_id", cloudfront_distribution.id)
    pulumi.export("cloudfront_function_name", cloudfront_function.name)
    
    # EC2 outputs
    pulumi.export("ami_id", get_latest_amazon_linux_ami())
    pulumi.export("instance_type", config["ec2_config"]["instance_type"])
    
    # Demo URLs
    pulumi.export("demo_urls", {
        "alb_direct_insecure": pulumi.Output.concat("http://", alb.dns_name),
        "alb_health_check": pulumi.Output.concat("http://", alb.dns_name, "/health"),
        "cloudfront_secure": pulumi.Output.concat("https://", cloudfront_distribution.domain_name),
        "api_endpoint": pulumi.Output.concat("https://", cloudfront_distribution.domain_name, "/api")
    })
    
    # Test commands
    pulumi.export("test_commands", {
        "test_without_jwt": pulumi.Output.concat("curl -v https://", cloudfront_distribution.domain_name),
        "test_with_jwt": pulumi.Output.concat("curl -v -H 'Authorization: Bearer ", sample_jwt, "' https://", cloudfront_distribution.domain_name),
        "test_alb_direct": pulumi.Output.concat("curl -v http://", alb.dns_name),
        "test_api_endpoint": pulumi.Output.concat("curl -v -H 'Authorization: Bearer ", sample_jwt, "' https://", cloudfront_distribution.domain_name, "/api")
    })
    
    # Sample JWT token for testing
    pulumi.export("sample_jwt_token", sample_jwt)
    
    print("Infrastructure deployment complete!")
    print(f"Region: {config['aws_region']}")
    print(f"Architecture: Simplified (public subnets, no NAT Gateway)")
    print(f"CloudFront: Global (managed from {config['aws_region']})")

if __name__ == "__main__":
    main()