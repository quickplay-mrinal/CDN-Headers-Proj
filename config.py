"""Configuration settings for CDN Headers Project"""

import pulumi

# Project configuration
PROJECT_NAME = "qp-iac-cdn-headers"
ENVIRONMENT = pulumi.get_stack()

# AWS Configuration
AWS_REGION = pulumi.Config("aws").get("region") or "us-east-1"

# Application Configuration
APP_PORT = 8000
HEALTH_CHECK_PATH = "/health"
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Secret rotation configuration
SECRET_ROTATION_DAYS = 30

# CloudFront Configuration
CLOUDFRONT_PRICE_CLASS = "PriceClass_100"  # US, Canada, Europe
CLOUDFRONT_MIN_TTL = 0
CLOUDFRONT_DEFAULT_TTL = 86400  # 1 day
CLOUDFRONT_MAX_TTL = 31536000   # 1 year

# ALB Configuration
ALB_IDLE_TIMEOUT = 60
ALB_DELETION_PROTECTION = False

# VPC Configuration
VPC_CIDR = "10.0.0.0/16"
PUBLIC_SUBNET_CIDRS = ["10.0.1.0/24", "10.0.2.0/24"]
PRIVATE_SUBNET_CIDRS = ["10.0.3.0/24", "10.0.4.0/24"]

# Tags
COMMON_TAGS = {
    "Project": PROJECT_NAME,
    "Environment": ENVIRONMENT,
    "ManagedBy": "Pulumi"
}