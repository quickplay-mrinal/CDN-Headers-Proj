"""Stable Pulumi program focusing on core functionality without CloudFront complexity"""

import pulumi
from modules.vpc import create_vpc
from modules.secrets import create_secrets_and_rotation
from modules.alb import create_alb
from modules.ecs import create_ecs_service
from config import PROJECT_NAME, COMMON_TAGS

def main():
    """Main function to orchestrate stable infrastructure deployment"""
    
    print("🚀 Deploying Stable CDN Headers Infrastructure")
    print("Components: VPC, ALB, ECS, Secrets Manager")
    print("=" * 60)
    
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
    
    # Export important values
    pulumi.export("vpc_id", vpc_resources["vpc_id"])
    pulumi.export("alb_dns_name", alb_resources["alb_dns_name"])
    pulumi.export("alb_arn", alb_resources["alb_arn"])
    pulumi.export("target_group_arn", alb_resources["target_group_arn"])
    pulumi.export("jwt_secret_arn", secrets_resources["jwt_secret_arn"])
    pulumi.export("api_key_secret_arn", secrets_resources["api_key_secret_arn"])
    pulumi.export("ecs_cluster_arn", ecs_resources["cluster_arn"])
    pulumi.export("ecs_service_name", ecs_resources["service_name"])
    
    # Create application URL
    app_url = pulumi.Output.concat("http://", alb_resources["alb_dns_name"])
    pulumi.export("application_url", app_url)
    
    # Export summary
    pulumi.export("deployment_summary", {
        "status": "stable-deployment-complete",
        "components": [
            "VPC with public/private subnets",
            "Application Load Balancer with JWT validation",
            "ECS Fargate service with FastAPI application", 
            "Secrets Manager with automatic rotation",
            "Complete IAM roles and security groups"
        ],
        "next_steps": [
            "Wait for ECS service to be healthy",
            "Test application at ALB DNS name",
            "Run validation: python validate_deployment.py",
            "Test endpoints: python test_endpoints.py <alb-dns>"
        ]
    })
    
    print("✅ Stable infrastructure deployment completed!")

if __name__ == "__main__":
    main()