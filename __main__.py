"""Main Pulumi program for CDN Headers Project"""

import pulumi
from modules.vpc import create_vpc
from modules.secrets import create_secrets_and_rotation
from modules.alb import create_alb
from modules.ecs import create_ecs_service
from modules.cloudfront import create_cloudfront_distribution
from modules.lambda_functions import create_lambda_functions
from config import PROJECT_NAME, COMMON_TAGS

def main():
    """Main function to orchestrate infrastructure deployment"""
    
    # Create VPC and networking
    vpc_resources = create_vpc()
    
    # Create secrets and rotation
    secrets_resources = create_secrets_and_rotation()
    
    # Create ALB
    alb_resources = create_alb(
        vpc_id=vpc_resources["vpc_id"],
        public_subnet_ids=vpc_resources["public_subnet_ids"],
        jwt_secret_arn=secrets_resources["jwt_secret_arn"]
    )
    
    # Create ECS service for the application
    ecs_resources = create_ecs_service(
        vpc_id=vpc_resources["vpc_id"],
        private_subnet_ids=vpc_resources["private_subnet_ids"],
        alb_target_group_arn=alb_resources["target_group_arn"],
        jwt_secret_arn=secrets_resources["jwt_secret_arn"]
    )
    
    # Create Lambda functions for CloudFront
    lambda_resources = create_lambda_functions(
        jwt_secret_arn=secrets_resources["jwt_secret_arn"]
    )
    
    # Create CloudFront distribution
    cloudfront_resources = create_cloudfront_distribution(
        alb_dns_name=alb_resources["alb_dns_name"],
        cloudfront_function_arn=lambda_resources["cloudfront_function_arn"]
    )
    
    # Export important values
    pulumi.export("vpc_id", vpc_resources["vpc_id"])
    pulumi.export("alb_dns_name", alb_resources["alb_dns_name"])
    pulumi.export("cloudfront_domain_name", cloudfront_resources["domain_name"])
    pulumi.export("cloudfront_distribution_id", cloudfront_resources["distribution_id"])
    pulumi.export("jwt_secret_arn", secrets_resources["jwt_secret_arn"])
    pulumi.export("api_key_secret_arn", secrets_resources["api_key_secret_arn"])

if __name__ == "__main__":
    main()