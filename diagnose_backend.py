#!/usr/bin/env python3
"""
Comprehensive backend infrastructure diagnostics for 502 errors
"""

import subprocess
import json
import sys
import time
import requests

def run_aws_command(command):
    """Run AWS CLI command and return JSON result"""
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        return json.loads(result.stdout) if result.stdout.strip() else None
    except subprocess.CalledProcessError as e:
        print(f"❌ AWS Command failed: {command}")
        print(f"Error: {e.stderr}")
        return None
    except json.JSONDecodeError:
        print(f"⚠️ Non-JSON response from: {command}")
        return result.stdout.strip() if 'result' in locals() else None

def check_alb_status():
    """Check ALB status and configuration"""
    print("⚖️ Checking Application Load Balancer...")
    
    # Get ALB details
    albs = run_aws_command('aws elbv2 describe-load-balancers --names qp-iac-cdn-headers-alb --output json')
    
    if not albs or not albs.get('LoadBalancers'):
        print("❌ ALB not found!")
        return False
    
    alb = albs['LoadBalancers'][0]
    print(f"✅ ALB Found: {alb['LoadBalancerName']}")
    print(f"   State: {alb['State']['Code']}")
    print(f"   DNS: {alb['DNSName']}")
    print(f"   Scheme: {alb['Scheme']}")
    print(f"   Type: {alb['Type']}")
    
    if alb['State']['Code'] != 'active':
        print(f"❌ ALB is not active! Current state: {alb['State']['Code']}")
        return False
    
    # Check target groups
    target_groups = run_aws_command(f'aws elbv2 describe-target-groups --load-balancer-arn {alb["LoadBalancerArn"]} --output json')
    
    if target_groups and target_groups.get('TargetGroups'):
        for tg in target_groups['TargetGroups']:
            print(f"📋 Target Group: {tg['TargetGroupName']}")
            print(f"   Port: {tg['Port']}")
            print(f"   Protocol: {tg['Protocol']}")
            print(f"   Health Check Path: {tg['HealthCheckPath']}")
            
            # Check target health
            health = run_aws_command(f'aws elbv2 describe-target-health --target-group-arn {tg["TargetGroupArn"]} --output json')
            
            if health and health.get('TargetHealthDescriptions'):
                for target in health['TargetHealthDescriptions']:
                    target_id = target['Target']['Id']
                    health_state = target['TargetHealth']['State']
                    print(f"   Target {target_id}: {health_state}")
                    
                    if health_state != 'healthy':
                        print(f"   ❌ Unhealthy target! Reason: {target['TargetHealth'].get('Reason', 'Unknown')}")
                        if 'Description' in target['TargetHealth']:
                            print(f"   Description: {target['TargetHealth']['Description']}")
            else:
                print("   ❌ No targets found in target group!")
    
    # Check listeners
    listeners = run_aws_command(f'aws elbv2 describe-listeners --load-balancer-arn {alb["LoadBalancerArn"]} --output json')
    
    if listeners and listeners.get('Listeners'):
        for listener in listeners['Listeners']:
            print(f"🎧 Listener: {listener['Port']}/{listener['Protocol']}")
            for action in listener['DefaultActions']:
                print(f"   Action: {action['Type']}")
    
    return alb['State']['Code'] == 'active'

def check_ecs_status():
    """Check ECS cluster and service status"""
    print("\n🐳 Checking ECS Cluster and Service...")
    
    # Check cluster
    clusters = run_aws_command('aws ecs describe-clusters --clusters qp-iac-cdn-headers-cluster --output json')
    
    if not clusters or not clusters.get('clusters'):
        print("❌ ECS Cluster not found!")
        return False
    
    cluster = clusters['clusters'][0]
    print(f"✅ Cluster: {cluster['clusterName']}")
    print(f"   Status: {cluster['status']}")
    print(f"   Active Services: {cluster['activeServicesCount']}")
    print(f"   Running Tasks: {cluster['runningTasksCount']}")
    print(f"   Pending Tasks: {cluster['pendingTasksCount']}")
    
    # Check service
    services = run_aws_command('aws ecs describe-services --cluster qp-iac-cdn-headers-cluster --services qp-iac-cdn-headers-service --output json')
    
    if not services or not services.get('services'):
        print("❌ ECS Service not found!")
        return False
    
    service = services['services'][0]
    print(f"📦 Service: {service['serviceName']}")
    print(f"   Status: {service['status']}")
    print(f"   Desired Count: {service['desiredCount']}")
    print(f"   Running Count: {service['runningCount']}")
    print(f"   Pending Count: {service['pendingCount']}")
    
    if service['runningCount'] == 0:
        print("❌ No running tasks! Service is not healthy.")
        
        # Check service events for errors
        if 'events' in service:
            print("📋 Recent Service Events:")
            for event in service['events'][:5]:  # Show last 5 events
                print(f"   {event['createdAt']}: {event['message']}")
    
    # Check task definition
    task_def_arn = service['taskDefinition']
    task_def = run_aws_command(f'aws ecs describe-task-definition --task-definition {task_def_arn} --output json')
    
    if task_def and task_def.get('taskDefinition'):
        td = task_def['taskDefinition']
        print(f"📋 Task Definition: {td['family']}:{td['revision']}")
        print(f"   CPU: {td['cpu']}")
        print(f"   Memory: {td['memory']}")
        print(f"   Network Mode: {td['networkMode']}")
        
        # Check container definitions
        for container in td['containerDefinitions']:
            print(f"   Container: {container['name']}")
            print(f"     Image: {container['image']}")
            if 'portMappings' in container:
                for port in container['portMappings']:
                    print(f"     Port: {port['containerPort']}/{port.get('protocol', 'tcp')}")
    
    # List running tasks
    tasks = run_aws_command('aws ecs list-tasks --cluster qp-iac-cdn-headers-cluster --service-name qp-iac-cdn-headers-service --output json')
    
    if tasks and tasks.get('taskArns'):
        print(f"🏃 Running Tasks: {len(tasks['taskArns'])}")
        
        # Get task details
        if tasks['taskArns']:
            task_details = run_aws_command(f'aws ecs describe-tasks --cluster qp-iac-cdn-headers-cluster --tasks {" ".join(tasks["taskArns"])} --output json')
            
            if task_details and task_details.get('tasks'):
                for task in task_details['tasks']:
                    print(f"   Task: {task['taskArn'].split('/')[-1]}")
                    print(f"     Status: {task['lastStatus']}")
                    print(f"     Health: {task.get('healthStatus', 'UNKNOWN')}")
                    print(f"     CPU/Memory: {task.get('cpu', 'N/A')}/{task.get('memory', 'N/A')}")
                    
                    # Check container statuses
                    if 'containers' in task:
                        for container in task['containers']:
                            print(f"     Container {container['name']}: {container['lastStatus']}")
                            if container['lastStatus'] != 'RUNNING':
                                print(f"       ❌ Container not running!")
                                if 'reason' in container:
                                    print(f"       Reason: {container['reason']}")
    else:
        print("❌ No running tasks found!")
    
    return service['runningCount'] > 0

def check_security_groups():
    """Check security group configurations"""
    print("\n🔒 Checking Security Groups...")
    
    # Get ALB security groups
    albs = run_aws_command('aws elbv2 describe-load-balancers --names qp-iac-cdn-headers-alb --output json')
    
    if albs and albs.get('LoadBalancers'):
        alb = albs['LoadBalancers'][0]
        
        for sg_id in alb['SecurityGroups']:
            sg = run_aws_command(f'aws ec2 describe-security-groups --group-ids {sg_id} --output json')
            
            if sg and sg.get('SecurityGroups'):
                sg_info = sg['SecurityGroups'][0]
                print(f"🛡️ ALB Security Group: {sg_info['GroupName']} ({sg_id})")
                
                # Check inbound rules
                for rule in sg_info['IpPermissions']:
                    port_range = f"{rule.get('FromPort', 'All')}-{rule.get('ToPort', 'All')}"
                    protocol = rule.get('IpProtocol', 'All')
                    
                    for ip_range in rule.get('IpRanges', []):
                        cidr = ip_range.get('CidrIp', 'N/A')
                        print(f"   Inbound: {protocol}:{port_range} from {cidr}")

def check_application_logs():
    """Check ECS application logs"""
    print("\n📋 Checking Application Logs...")
    
    try:
        # Get recent logs from ECS
        result = subprocess.run(
            'aws logs tail /ecs/qp-iac-cdn-headers --since 10m --format short',
            shell=True, capture_output=True, text=True, timeout=30
        )
        
        if result.stdout:
            print("📋 Recent Application Logs (last 10 minutes):")
            print(result.stdout[-1000:])  # Show last 1000 characters
        else:
            print("⚠️ No recent logs found or log group doesn't exist")
            
    except subprocess.TimeoutExpired:
        print("⏱️ Log retrieval timed out")
    except Exception as e:
        print(f"❌ Error retrieving logs: {e}")

def test_direct_connectivity():
    """Test direct connectivity to ALB"""
    print("\n🌐 Testing Direct ALB Connectivity...")
    
    alb_dns = "qp-iac-cdn-headers-alb-748420320.us-east-1.elb.amazonaws.com"
    
    # Test different endpoints
    endpoints = [
        "/",
        "/health", 
        "/api/status"
    ]
    
    for endpoint in endpoints:
        try:
            url = f"http://{alb_dns}{endpoint}"
            print(f"🔍 Testing: {url}")
            
            response = requests.get(url, timeout=10)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                print(f"   ✅ Success!")
                if len(response.text) < 200:
                    print(f"   Response: {response.text}")
            else:
                print(f"   ❌ Failed: {response.status_code}")
                print(f"   Response: {response.text[:200]}...")
                
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Connection failed: {e}")

def main():
    print("🔍 Backend Infrastructure Diagnostics")
    print("=" * 50)
    
    # Check all components
    alb_ok = check_alb_status()
    ecs_ok = check_ecs_status()
    check_security_groups()
    check_application_logs()
    test_direct_connectivity()
    
    print("\n" + "=" * 50)
    print("📊 Diagnostic Summary:")
    print(f"   ALB Status: {'✅ OK' if alb_ok else '❌ Issues Found'}")
    print(f"   ECS Status: {'✅ OK' if ecs_ok else '❌ Issues Found'}")
    
    if not alb_ok or not ecs_ok:
        print("\n🔧 Recommended Actions:")
        if not ecs_ok:
            print("1. Check ECS service logs: aws logs tail /ecs/qp-iac-cdn-headers --follow")
            print("2. Restart ECS service: aws ecs update-service --cluster qp-iac-cdn-headers-cluster --service qp-iac-cdn-headers-service --force-new-deployment")
            print("3. Check task definition and container image")
        if not alb_ok:
            print("4. Check ALB target group health")
            print("5. Verify security group rules")
            print("6. Check VPC and subnet configuration")
    else:
        print("\n✅ Backend infrastructure appears healthy!")
        print("The 502 error might be application-level or configuration-related.")

if __name__ == "__main__":
    main()