"""ECS service for the interactive application"""

import pulumi
import pulumi_aws as aws
import json
from config import PROJECT_NAME, APP_PORT, COMMON_TAGS

def create_ecs_service(vpc_id, private_subnet_ids, alb_target_group_arn, jwt_secret_arn):
    """Create ECS service to run the interactive application"""
    
    # Create ECS cluster
    cluster = aws.ecs.Cluster(
        f"{PROJECT_NAME}-cluster",
        name=f"{PROJECT_NAME}-cluster",
        tags={**COMMON_TAGS, "Name": f"{PROJECT_NAME}-cluster"}
    )
    
    # Create security group for ECS tasks
    ecs_sg = aws.ec2.SecurityGroup(
        f"{PROJECT_NAME}-ecs-sg",
        name=f"{PROJECT_NAME}-ecs-sg",
        description="Security group for ECS tasks",
        vpc_id=vpc_id,
        ingress=[
            aws.ec2.SecurityGroupIngressArgs(
                protocol="tcp",
                from_port=APP_PORT,
                to_port=APP_PORT,
                cidr_blocks=["10.0.0.0/16"]  # Only allow traffic from VPC
            )
        ],
        egress=[
            aws.ec2.SecurityGroupEgressArgs(
                protocol="-1",
                from_port=0,
                to_port=0,
                cidr_blocks=["0.0.0.0/0"]
            )
        ],
        tags={**COMMON_TAGS, "Name": f"{PROJECT_NAME}-ecs-sg"}
    )
    
    # Create ECS task execution role
    task_execution_role = aws.iam.Role(
        f"{PROJECT_NAME}-task-execution-role",
        assume_role_policy=json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Action": "sts:AssumeRole",
                "Effect": "Allow",
                "Principal": {
                    "Service": "ecs-tasks.amazonaws.com"
                }
            }]
        }),
        tags={**COMMON_TAGS, "Name": f"{PROJECT_NAME}-task-execution-role"}
    )
    
    # Attach ECS task execution policy
    aws.iam.RolePolicyAttachment(
        f"{PROJECT_NAME}-task-execution-role-policy",
        role=task_execution_role.name,
        policy_arn="arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
    )
    
    # Create ECS task role
    task_role = aws.iam.Role(
        f"{PROJECT_NAME}-task-role",
        assume_role_policy=json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Action": "sts:AssumeRole",
                "Effect": "Allow",
                "Principal": {
                    "Service": "ecs-tasks.amazonaws.com"
                }
            }]
        }),
        tags={**COMMON_TAGS, "Name": f"{PROJECT_NAME}-task-role"}
    )
    
    # Add policy for task to access secrets
    task_policy = aws.iam.RolePolicy(
        f"{PROJECT_NAME}-task-policy",
        role=task_role.id,
        policy=jwt_secret_arn.apply(
            lambda arn: json.dumps({
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Action": [
                        "secretsmanager:GetSecretValue"
                    ],
                    "Resource": arn
                }]
            })
        )
    )
    
    # Create CloudWatch log group
    log_group = aws.cloudwatch.LogGroup(
        f"{PROJECT_NAME}-log-group",
        name=f"/ecs/{PROJECT_NAME}",
        retention_in_days=7,
        tags={**COMMON_TAGS, "Name": f"{PROJECT_NAME}-log-group"}
    )
    
    # Create ECS task definition
    task_definition = aws.ecs.TaskDefinition(
        f"{PROJECT_NAME}-task-definition",
        family=f"{PROJECT_NAME}-task",
        network_mode="awsvpc",
        requires_compatibilities=["FARGATE"],
        cpu="256",
        memory="512",
        execution_role_arn=task_execution_role.arn,
        task_role_arn=task_role.arn,
        container_definitions=pulumi.Output.all(log_group.name, jwt_secret_arn).apply(
            lambda args: json.dumps([{
                "name": f"{PROJECT_NAME}-container",
                "image": "nginx:latest",  # Will be replaced with custom app image
                "portMappings": [{
                    "containerPort": APP_PORT,
                    "protocol": "tcp"
                }],
                "essential": True,
                "logConfiguration": {
                    "logDriver": "awslogs",
                    "options": {
                        "awslogs-group": args[0],
                        "awslogs-region": "us-east-1",
                        "awslogs-stream-prefix": "ecs"
                    }
                },
                "environment": [
                    {
                        "name": "JWT_SECRET_ARN",
                        "value": args[1]
                    },
                    {
                        "name": "PORT",
                        "value": str(APP_PORT)
                    }
                ]
            }])
        ),
        tags={**COMMON_TAGS, "Name": f"{PROJECT_NAME}-task-definition"}
    )
    
    # Create ECS service
    service = aws.ecs.Service(
        f"{PROJECT_NAME}-service",
        name=f"{PROJECT_NAME}-service",
        cluster=cluster.id,
        task_definition=task_definition.arn,
        desired_count=2,
        launch_type="FARGATE",
        network_configuration=aws.ecs.ServiceNetworkConfigurationArgs(
            subnets=private_subnet_ids,
            security_groups=[ecs_sg.id],
            assign_public_ip=False
        ),
        load_balancers=[
            aws.ecs.ServiceLoadBalancerArgs(
                target_group_arn=alb_target_group_arn,
                container_name=f"{PROJECT_NAME}-container",
                container_port=APP_PORT
            )
        ],
        depends_on=[task_definition],
        tags={**COMMON_TAGS, "Name": f"{PROJECT_NAME}-service"}
    )
    
    return {
        "cluster_arn": cluster.arn,
        "service_arn": service.arn,
        "task_definition_arn": task_definition.arn,
        "ecs_security_group_id": ecs_sg.id
    }