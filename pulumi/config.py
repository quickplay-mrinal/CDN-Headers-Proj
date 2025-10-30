"""
Configuration module for CloudFront Function + JWT Security Infrastructure
Handles region selection and common configuration settings
"""
import pulumi

def get_config():
    """Get configuration settings for the infrastructure"""
    config = pulumi.Config()
    
    # Get project and stack information
    project_name = pulumi.get_project()
    stack_name = pulumi.get_stack()
    
    # Region configuration - default to ap-south-2 (Hyderabad)
    # Note: CloudFront is global but all other resources will be in ap-south-2
    aws_region = config.get("aws_region") or "ap-south-2"
    
    # Availability zones for ap-south-2
    availability_zones = {
        "ap-south-2": ["ap-south-2a", "ap-south-2b", "ap-south-2c"],
        "us-east-1": ["us-east-1a", "us-east-1b", "us-east-1c"],
        "us-west-2": ["us-west-2a", "us-west-2b", "us-west-2c"],
        "eu-west-1": ["eu-west-1a", "eu-west-1b", "eu-west-1c"]
    }
    
    # Get AZs for the selected region
    azs = availability_zones.get(aws_region, ["ap-south-2a", "ap-south-2b"])
    
    # Common tags for all resources
    common_tags = {
        "Project": project_name,
        "Stack": stack_name,
        "Purpose": "CloudFront-JWT-Security",
        "Region": aws_region,
        "ManagedBy": "Pulumi"
    }
    
    # Network configuration
    network_config = {
        "vpc_cidr": "10.0.0.0/16",
        "public_subnet_cidrs": ["10.0.1.0/24", "10.0.2.0/24"],
        "private_subnet_cidrs": ["10.0.3.0/24", "10.0.4.0/24"],
        "availability_zones": azs[:2]  # Use first 2 AZs
    }
    
    # EC2 configuration
    ec2_config = {
        "instance_type": "t3.micro",
        "min_size": 2,
        "max_size": 4,
        "desired_capacity": 2
    }
    
    # CloudFront configuration (Global service)
    cloudfront_config = {
        "price_class": "PriceClass_100",  # North America and Europe only
        "cache_policy_id": "4135ea2d-6df8-44a3-9df3-4b5a84be39ad"  # CachingDisabled
    }
    
    return {
        "project_name": project_name,
        "stack_name": stack_name,
        "aws_region": aws_region,
        "common_tags": common_tags,
        "network_config": network_config,
        "ec2_config": ec2_config,
        "cloudfront_config": cloudfront_config
    }

def get_ami_id(region):
    """Get the appropriate AMI ID for the region (fallback function)"""
    # Amazon Linux 2 AMI IDs by region (known working AMIs)
    # These are fallback AMIs in case dynamic lookup fails
    ami_mapping = {
        "ap-south-2": "ami-0ad21ae1d0696ad58",  # Amazon Linux 2 in ap-south-2 (Hyderabad)
        "us-east-1": "ami-0c02fb55956c7d316",   # Amazon Linux 2 in us-east-1 (N. Virginia)
        "us-west-2": "ami-0c2d3e23f757b5d84",   # Amazon Linux 2 in us-west-2 (Oregon)
        "eu-west-1": "ami-0c9c942bd7bf113a2",   # Amazon Linux 2 in eu-west-1 (Ireland)
        "ap-south-1": "ami-0f58b397bc5c1f2e8"   # Amazon Linux 2 in ap-south-1 (Mumbai) - fallback
    }
    
    # If the requested region is not in mapping, try to use a fallback
    if region not in ami_mapping:
        print(f"Warning: AMI mapping not found for region {region}, using us-east-1 as fallback")
        return ami_mapping["us-east-1"]
    
    return ami_mapping[region]

def print_config_info():
    """Print configuration information for debugging"""
    config = get_config()
    
    print(f"Region: {config['aws_region']}")
    print(f"Project: {config['project_name']}")
    print(f"Stack: {config['stack_name']}")
    print(f"VPC CIDR: {config['network_config']['vpc_cidr']}")
    print(f"Availability Zones: {config['network_config']['availability_zones']}")
    print(f"Instance Type: {config['ec2_config']['instance_type']}")
    print(f"CloudFront Price Class: {config['cloudfront_config']['price_class']}")