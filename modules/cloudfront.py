"""CloudFront distribution and related resources"""

import pulumi
import pulumi_aws as aws
from config import (
    PROJECT_NAME, 
    CLOUDFRONT_PRICE_CLASS, 
    CLOUDFRONT_MIN_TTL, 
    CLOUDFRONT_DEFAULT_TTL, 
    CLOUDFRONT_MAX_TTL,
    COMMON_TAGS
)

def create_cloudfront_distribution(alb_dns_name, cloudfront_function_arn):
    """Create CloudFront distribution with custom behaviors"""
    
    # Note: Origin Access Control is not applicable for ALB origins
    # OAC is only used for S3, MediaStore, MediaPackageV2, and Lambda origins
    
    # Create CloudFront distribution
    distribution = aws.cloudfront.Distribution(
        f"{PROJECT_NAME}-distribution",
        aliases=[],  # Add custom domain names if needed
        comment=f"CDN for {PROJECT_NAME}",
        # Remove default_root_object since FastAPI serves at root "/"
        enabled=True,
        is_ipv6_enabled=True,
        price_class=CLOUDFRONT_PRICE_CLASS,
        
        # Origin configuration
        origins=[
            aws.cloudfront.DistributionOriginArgs(
                domain_name=alb_dns_name,
                origin_id=f"{PROJECT_NAME}-alb-origin",
                custom_origin_config=aws.cloudfront.DistributionOriginCustomOriginConfigArgs(
                    http_port=80,
                    https_port=443,
                    origin_protocol_policy="http-only",
                    origin_ssl_protocols=["TLSv1.2"]
                ),
                custom_headers=[
                    aws.cloudfront.DistributionOriginCustomHeaderArgs(
                        name="X-CDN-Auth",
                        value="qp-iac-cdn-secret-key"
                    )
                ]
            )
        ],
        
        # Default cache behavior
        default_cache_behavior=aws.cloudfront.DistributionDefaultCacheBehaviorArgs(
            target_origin_id=f"{PROJECT_NAME}-alb-origin",
            viewer_protocol_policy="redirect-to-https",
            allowed_methods=["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"],
            cached_methods=["GET", "HEAD"],
            compress=True,
            
            # Cache settings - using managed policies (no forwarded_values when using cache policies)
            cache_policy_id="4135ea2d-6df8-44a3-9df3-4b5a84be39ad",  # Managed-CachingDisabled
            origin_request_policy_id="88a5eaf4-2fd4-4709-b370-b4c650ea3fcf",  # Managed-CORS-S3Origin
            
            # Function associations temporarily disabled to fix header validation
            # function_associations=[
            #     aws.cloudfront.DistributionDefaultCacheBehaviorFunctionAssociationArgs(
            #         event_type="viewer-request",
            #         function_arn=cloudfront_function_arn
            #     )
            # ]
        ),
        
        # Additional cache behaviors for API endpoints
        ordered_cache_behaviors=[
            aws.cloudfront.DistributionOrderedCacheBehaviorArgs(
                path_pattern="/api/*",
                target_origin_id=f"{PROJECT_NAME}-alb-origin",
                viewer_protocol_policy="https-only",
                allowed_methods=["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"],
                cached_methods=["GET", "HEAD"],
                compress=True,
                
                # No caching for API endpoints
                cache_policy_id="4135ea2d-6df8-44a3-9df3-4b5a84be39ad",  # Managed-CachingDisabled
                origin_request_policy_id="88a5eaf4-2fd4-4709-b370-b4c650ea3fcf",  # Managed-CORS-S3Origin
                
                # Function associations temporarily disabled
                # function_associations=[
                #     aws.cloudfront.DistributionOrderedCacheBehaviorFunctionAssociationArgs(
                #         event_type="viewer-request",
                #         function_arn=cloudfront_function_arn
                #     )
                # ]
            ),
            
            aws.cloudfront.DistributionOrderedCacheBehaviorArgs(
                path_pattern="/health",
                target_origin_id=f"{PROJECT_NAME}-alb-origin",
                viewer_protocol_policy="https-only",
                allowed_methods=["GET", "HEAD"],
                cached_methods=["GET", "HEAD"],
                compress=True,
                
                # Short caching for health checks
                cache_policy_id="658327ea-f89d-4fab-a63d-7e88639e58f6"  # Managed-CachingOptimized
            )
        ],
        
        # Geographic restrictions
        restrictions=aws.cloudfront.DistributionRestrictionsArgs(
            geo_restriction=aws.cloudfront.DistributionRestrictionsGeoRestrictionArgs(
                restriction_type="none"
            )
        ),
        
        # SSL/TLS configuration
        viewer_certificate=aws.cloudfront.DistributionViewerCertificateArgs(
            cloudfront_default_certificate=True
        ),
        
        # Custom error pages - redirect to root for SPA behavior
        custom_error_responses=[
            aws.cloudfront.DistributionCustomErrorResponseArgs(
                error_code=403,
                response_code=200,
                response_page_path="/",
                error_caching_min_ttl=300
            ),
            aws.cloudfront.DistributionCustomErrorResponseArgs(
                error_code=404,
                response_code=200,
                response_page_path="/",
                error_caching_min_ttl=300
            )
        ],
        
        # Note: Logging configuration removed to avoid S3 ACL complexity
        # Can be added later if needed
        
        tags={**COMMON_TAGS, "Name": f"{PROJECT_NAME}-distribution"}
    )
    
    # Note: CloudWatch monitoring can be added later if needed
    # create_cloudfront_monitoring(distribution.id)
    
    return {
        "distribution_id": distribution.id,
        "domain_name": distribution.domain_name,
        "distribution_arn": distribution.arn,
        "hosted_zone_id": distribution.hosted_zone_id
    }

# S3 bucket creation removed to avoid ACL complexity
# CloudFront logging can be configured separately if needed

def create_cloudfront_monitoring(distribution_id):
    """Create CloudWatch monitoring for CloudFront"""
    
    # Create CloudWatch alarms for CloudFront metrics
    aws.cloudwatch.MetricAlarm(
        f"{PROJECT_NAME}-cloudfront-4xx-alarm",
        name=f"{PROJECT_NAME}-cloudfront-4xx-errors",
        metric_name="4xxErrorRate",
        namespace="AWS/CloudFront",
        statistic="Average",
        period=300,
        evaluation_periods=2,
        threshold=5.0,
        comparison_operator="GreaterThanThreshold",
        dimensions={
            "DistributionId": distribution_id
        },
        alarm_actions=[],  # Add SNS topic ARN for notifications
        tags={**COMMON_TAGS, "Name": f"{PROJECT_NAME}-cloudfront-4xx-alarm"}
    )
    
    aws.cloudwatch.MetricAlarm(
        f"{PROJECT_NAME}-cloudfront-5xx-alarm",
        name=f"{PROJECT_NAME}-cloudfront-5xx-errors",
        metric_name="5xxErrorRate",
        namespace="AWS/CloudFront",
        statistic="Average",
        period=300,
        evaluation_periods=2,
        threshold=1.0,
        comparison_operator="GreaterThanThreshold",
        dimensions={
            "DistributionId": distribution_id
        },
        alarm_actions=[],  # Add SNS topic ARN for notifications
        tags={**COMMON_TAGS, "Name": f"{PROJECT_NAME}-cloudfront-5xx-alarm"}
    )
    
    # Create dashboard for CloudFront metrics
    aws.cloudwatch.Dashboard(
        f"{PROJECT_NAME}-cloudfront-dashboard",
        dashboard_name=f"{PROJECT_NAME}-cloudfront-metrics",
        dashboard_body=pulumi.Output.concat('''{
            "widgets": [
                {
                    "type": "metric",
                    "x": 0,
                    "y": 0,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "metrics": [
                            [ "AWS/CloudFront", "Requests", "DistributionId", "''', distribution_id, '''" ],
                            [ ".", "BytesDownloaded", ".", "." ],
                            [ ".", "BytesUploaded", ".", "." ]
                        ],
                        "period": 300,
                        "stat": "Sum",
                        "region": "us-east-1",
                        "title": "CloudFront Traffic"
                    }
                },
                {
                    "type": "metric",
                    "x": 0,
                    "y": 6,
                    "width": 12,
                    "height": 6,
                    "properties": {
                        "metrics": [
                            [ "AWS/CloudFront", "4xxErrorRate", "DistributionId", "''', distribution_id, '''" ],
                            [ ".", "5xxErrorRate", ".", "." ]
                        ],
                        "period": 300,
                        "stat": "Average",
                        "region": "us-east-1",
                        "title": "CloudFront Error Rates"
                    }
                }
            ]
        }''')
    )