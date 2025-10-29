#!/usr/bin/env python3
"""
Restart ECS service to fix potential container issues
"""

import subprocess
import sys
import time
import json

def run_aws_command(command):
    """Run AWS CLI command"""
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {command}")
        print(f"Error: {e.stderr}")
        return None

def restart_ecs_service():
    """Force restart of ECS service"""
    print("🔄 Restarting ECS Service...")
    
    # Force new deployment
    result = run_aws_command(
        'aws ecs update-service --cluster qp-iac-cdn-headers-cluster '
        '--service qp-iac-cdn-headers-service --force-new-deployment'
    )
    
    if result:
        print("✅ ECS service restart initiated!")
        return True
    else:
        print("❌ Failed to restart ECS service")
        return False

def wait_for_service_stable():
    """Wait for ECS service to become stable"""
    print("⏱️ Waiting for service to stabilize...")
    
    for i in range(10):  # Wait up to 10 minutes
        print(f"🔍 Check {i+1}/10: Getting service status...")
        
        result = run_aws_command(
            'aws ecs describe-services --cluster qp-iac-cdn-headers-cluster '
            '--services qp-iac-cdn-headers-service --query '
            '"services[0].{Status:status,Running:runningCount,Desired:desiredCount}" --output json'
        )
        
        if result:
            try:
                status = json.loads(result)
                print(f"   Status: {status['Status']}")
                print(f"   Running: {status['Running']}/{status['Desired']}")
                
                if status['Running'] == status['Desired'] and status['Running'] > 0:
                    print("✅ Service is stable and healthy!")
                    return True
                    
            except json.JSONDecodeError:
                print("⚠️ Could not parse service status")
        
        if i < 9:  # Don't sleep on last iteration
            print("⏳ Waiting 60 seconds...")
            time.sleep(60)
    
    print("❌ Service did not stabilize within 10 minutes")
    return False

def check_task_logs():
    """Check recent task logs"""
    print("📋 Checking recent task logs...")
    
    try:
        result = subprocess.run(
            'aws logs tail /ecs/qp-iac-cdn-headers --since 5m --format short',
            shell=True, capture_output=True, text=True, timeout=30
        )
        
        if result.stdout:
            print("Recent logs:")
            print(result.stdout[-800:])  # Show last 800 characters
        else:
            print("⚠️ No recent logs found")
            
    except subprocess.TimeoutExpired:
        print("⏱️ Log retrieval timed out")
    except Exception as e:
        print(f"❌ Error retrieving logs: {e}")

def main():
    print("🔄 ECS Service Restart Utility")
    print("=" * 40)
    
    print("This will force a new deployment of your ECS service.")
    print("This can help fix issues with stuck or unhealthy containers.")
    
    confirm = input("\nProceed with ECS service restart? (y/N): ")
    if confirm.lower() != 'y':
        print("❌ Restart cancelled.")
        return False
    
    # Restart service
    if not restart_ecs_service():
        return False
    
    # Wait for stabilization
    if not wait_for_service_stable():
        print("⚠️ Service restart may still be in progress.")
        print("Check AWS Console or run: aws ecs describe-services --cluster qp-iac-cdn-headers-cluster --services qp-iac-cdn-headers-service")
    
    # Check logs
    check_task_logs()
    
    print("\n🧪 Test your application:")
    print("Direct ALB: http://qp-iac-cdn-headers-alb-748420320.us-east-1.elb.amazonaws.com")
    print("CloudFront: https://d8lo8nw3jettu.cloudfront.net")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)