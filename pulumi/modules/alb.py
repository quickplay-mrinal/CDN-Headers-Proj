"""
Application Load Balancer Module - Creates ALB, target group, and listener
All resources deployed in the specified region (default: ap-south-2)
"""
import pulumi_aws as aws

def create_alb(config, public_subnet_ids, security_group_id):
    """Create Application Load Balancer with target group and listener"""
    
    project_name = config["project_name"]
    common_tags = config["common_tags"]
    
    # Application Load Balancer
    alb = aws.lb.LoadBalancer("jwt-alb",
        name=f"{project_name}-alb",
        load_balancer_type="application",
        subnets=public_subnet_ids,
        security_groups=[security_group_id],
        enable_deletion_protection=False,  # Allow deletion for demo
        tags={**common_tags, "Name": f"{project_name}-alb"}
    )
    
    # Target Group
    target_group = aws.lb.TargetGroup("jwt-tg",
        name=f"{project_name}-tg",
        port=80,
        protocol="HTTP",
        vpc_id=None,  # Will be set by the caller
        target_type="instance",
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
    
    # ALB Listener - Simple HTTP forwarding (JWT validation handled by CloudFront)
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
        tags=common_tags
    )
    
    return {
        "alb": alb,
        "target_group": target_group,
        "alb_listener": alb_listener
    }

def create_target_group_with_vpc(config, vpc_id):
    """Create target group with VPC ID and improved health check settings"""
    
    project_name = config["project_name"]
    common_tags = config["common_tags"]
    
    target_group = aws.lb.TargetGroup("jwt-tg",
        name=f"{project_name}-tg",
        port=80,
        protocol="HTTP",
        vpc_id=vpc_id,
        target_type="instance",
        health_check=aws.lb.TargetGroupHealthCheckArgs(
            enabled=True,
            healthy_threshold=2,
            interval=30,  # Standard interval
            matcher="200",
            path="/",  # Use root path for initial health check
            port="traffic-port",
            protocol="HTTP",
            timeout=5,  # Standard timeout
            unhealthy_threshold=3,  # More tolerance for temporary failures
        ),
        # Deregistration delay for graceful shutdown
        deregistration_delay=30,
        tags={**common_tags, "Name": f"{project_name}-tg"}
    )
    
    return target_group

def attach_asg_to_target_group(asg_name, target_group_arn):
    """Attach Auto Scaling Group to Target Group"""
    
    return aws.autoscaling.Attachment("jwt-asg-attachment",
        autoscaling_group_name=asg_name,
        lb_target_group_arn=target_group_arn
    )