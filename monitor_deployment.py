#!/usr/bin/env python3
"""
Monitor ECS deployment progress and test when ready
"""

import subprocess
import sys
import time
import requests
import json

def run_aws_command(command):
    """Run AWS CLI command and return result"""
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None

def check_target_health():
    """Check ALB target group health"""
    print("🎯 Checking target group health...")
    
    result = run_aws_command(
        'aws elbv2 describe-target-health --target-group-arn '
        '$(aws elbv2 describe-target-groups --names qp-iac-cdn-headers-tg --query "TargetGroups[0].TargetGroupArn" --output text) '
        '--output json'
    )
    
    if result:
        try:
            health_data = json.loads(result)
            targets = health_data.get('TargetHealthDescriptions', [])
            
            healthy_count = 0
            total_count = len(targets)
            
            for target in targets:
                target_id = target['Target']['Id']
                health_state = target['TargetHealth']['State']
                reason = target['TargetHealth'].get('Reason', '')
                
                print(f"   Target {target_id}: {health_state}")
                if reason:
                    print(f"     Reason: {reason}")
                
                if health_state == 'healthy':
                    healthy_count += 1
            
            print(f"   Summary: {healthy_count}/{total_count} targets healthy")
            return healthy_count > 0, healthy_count, total_count
            
        except json.JSONDecodeError:
            print("   ❌ Could not parse target health data")
    
    return False, 0, 0

def check_ecs_deployment():
    """Check ECS deployment status"""
    print("🐳 Checking ECS deployment...")
    
    result = run_aws_command(
        'aws ecs describe-services --cluster qp-iac-cdn-headers-cluster '
        '--services qp-iac-cdn-headers-service --output json'
    )
    
    if result:
        try:
            service_data = json.loads(result)
            service = service_data['services'][0]
            
            running_count = service['runningCount']
            desired_count = service['desiredCount']
            
            print(f"   Tasks: {running_count}/{desired_count} running")
            
            # Check deployment status
            deployments = service.get('deployments', [])
            for deployment in deployments:
                status = deployment['status']
                running = deployment['runningCount']
                desired = deployment['desiredCount']
                
                print(f"   Deployment: {status} ({running}/{desired})")
                
                if status == 'PRIMARY' and running == desired:
                    return True
            
        except (json.JSONDecodeError, KeyError):
            print("   ❌ Could not parse ECS service data")
    
    return False

def check_application_logs():
    """Check recent application logs"""
    print("📋 Checking recent logs...")
    
    try:
        result = subprocess.run(
            'aws logs tail /ecs/qp-iac-cdn-headers --since 2m --format short',
            shell=True, capture_output=True, text=True, timeout=15
        )
        
        if result.stdout:
            lines = result.stdout.strip().split('\n')
            recent_lines = lines[-10:]  # Show last 10 lines
            
            for line in recent_lines:
                if any(keyword in line.lower() for keyword in ['error', 'failed', 'exception']):
                    print(f"   ❌ {line}")
                elif any(keyword in line.lower() for keyword in ['started', 'running', 'listening']):
                    print(f"   ✅ {line}")
                else:
                    print(f"   ℹ️ {line}")
        else:
            print("   No recent logs found")
            
    except subprocess.TimeoutExpired:
        print("   ⏱️ Log retrieval timed out")
    except Exception as e:
        print(f"   ❌ Error retrieving logs: {e}")

def test_application():
    """Test application endpoints"""
    print("🧪 Testing application...")
    
    alb_dns = "qp-iac-cdn-headers-alb-748420320.us-east-1.elb.amazonaws.com"
    
    endpoints = [
        ("/health", "Health Check"),
        ("/", "Main Page"),
        ("/api/status", "API Status")
    ]
    
    success_count = 0
    
    for endpoint, name in endpoints:
        try:
            url = f"http://{alb_dns}{endpoint}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                print(f"   ✅ {name}: OK")
                success_count += 1
            else:
                print(f"   ❌ {name}: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"   ❌ {name}: Connection failed ({e})")
    
    return success_count == len(endpoints)

def monitor_deployment():
    """Monitor deployment progress"""
    print("🔄 Monitoring ECS Deployment Progress")
    print("=" * 50)
    
    max_attempts = 20  # 20 minutes max
    attempt = 0
    
    while attempt < max_attempts:
        attempt += 1
        print(f"\n📊 Check {attempt}/{max_attempts} ({time.strftime('%H:%M:%S')})")
        print("-" * 30)
        
        # Check ECS deployment
        ecs_ready = check_ecs_deployment()
        
        # Check target health
        targets_healthy, healthy_count, total_count = check_target_health()
        
        # Check logs
        check_application_logs()
        
        # Test application if targets are healthy
        if targets_healthy:
            print("\n🧪 Targets are healthy, testing application...")
            if test_application():
                print("\n🎉 Deployment completed successfully!")
                print("\n🌐 Your application is now accessible:")
                print("- Direct ALB: http://qp-iac-cdn-headers-alb-748420320.us-east-1.elb.amazonaws.com")
                print("- CloudFront: https://d8lo8nw3jettu.cloudfront.net")
                return True
        
        # Check if we should continue waiting
        if ecs_ready and healthy_count == 0:
            print("⚠️ ECS deployment complete but no healthy targets yet...")
        elif not ecs_ready:
            print("⏳ ECS deployment still in progress...")
        
        if attempt < max_attempts:
            print(f"⏱️ Waiting 60 seconds before next check...")
            time.sleep(60)
    
    print("\n⚠️ Deployment monitoring timed out after 20 minutes.")
    print("The deployment may still be in progress. Check manually:")
    print("- AWS ECS Console: Check service status")
    print("- AWS ALB Console: Check target group health")
    return False

def main():
    print("🔄 ECS Deployment Monitor")
    print("This will monitor your deployment progress and test when ready.")
    
    try:
        return monitor_deployment()
    except KeyboardInterrupt:
        print("\n⏹️ Monitoring stopped by user.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)