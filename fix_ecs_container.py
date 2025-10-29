#!/usr/bin/env python3
"""
Fix ECS container to use FastAPI instead of nginx
"""

import subprocess
import sys
import os
import time

def run_command(command):
    """Run shell command"""
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e.stderr}")
        return False

def update_infrastructure():
    """Update the infrastructure with fixed ECS container"""
    print("🔧 Updating ECS Task Definition...")
    print("Changing from nginx:latest to Python FastAPI application")
    
    # Set environment
    os.environ["PULUMI_CONFIG_PASSPHRASE"] = ""
    
    # Update the stack
    success = run_command("pulumi up --yes")
    
    if success:
        print("✅ Infrastructure updated successfully!")
        return True
    else:
        print("❌ Infrastructure update failed!")
        return False

def wait_for_deployment():
    """Wait for ECS deployment to complete"""
    print("⏱️ Waiting for ECS deployment to complete...")
    
    for i in range(15):  # Wait up to 15 minutes
        print(f"🔍 Check {i+1}/15: Getting service status...")
        
        result = subprocess.run(
            'aws ecs describe-services --cluster qp-iac-cdn-headers-cluster '
            '--services qp-iac-cdn-headers-service --query '
            '"services[0].{Running:runningCount,Desired:desiredCount,Deployments:deployments[0].status}" --output text',
            shell=True, capture_output=True, text=True
        )
        
        if result.returncode == 0:
            output = result.stdout.strip().split('\t')
            if len(output) >= 3:
                deployment_status = output[0]
                running = output[1]
                desired = output[2]
                
                print(f"   Deployment: {deployment_status}")
                print(f"   Tasks: {running}/{desired}")
                
                if deployment_status == "PRIMARY" and running == desired and int(running) > 0:
                    print("✅ Deployment completed successfully!")
                    return True
        
        if i < 14:  # Don't sleep on last iteration
            print("⏳ Waiting 60 seconds...")
            time.sleep(60)
    
    print("⚠️ Deployment may still be in progress. Check AWS Console.")
    return False

def test_application():
    """Test the application after deployment"""
    print("🧪 Testing application...")
    
    import requests
    
    alb_dns = "qp-iac-cdn-headers-alb-748420320.us-east-1.elb.amazonaws.com"
    
    # Test health endpoint
    try:
        response = requests.get(f"http://{alb_dns}/health", timeout=10)
        if response.status_code == 200:
            print("✅ Health check passed!")
            print(f"Response: {response.json()}")
            
            # Test main page
            response = requests.get(f"http://{alb_dns}/", timeout=10)
            if response.status_code == 200:
                print("✅ Main page accessible!")
                return True
            else:
                print(f"❌ Main page failed: {response.status_code}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection failed: {e}")
    
    return False

def main():
    print("🚨 ECS Container Fix - Replace nginx with FastAPI")
    print("=" * 60)
    
    print("This will:")
    print("1. Update ECS task definition to use Python + FastAPI")
    print("2. Deploy new container with your application code")
    print("3. Wait for deployment to complete")
    print("4. Test the application")
    
    confirm = input("\nProceed with ECS container fix? (y/N): ")
    if confirm.lower() != 'y':
        print("❌ Fix cancelled.")
        return False
    
    # Update infrastructure
    if not update_infrastructure():
        return False
    
    # Wait for deployment
    if not wait_for_deployment():
        print("⚠️ Continuing with testing...")
    
    # Test application
    if test_application():
        print("\n🎉 ECS container fix completed successfully!")
        print("\n🌐 Your application is now accessible:")
        print("- Direct ALB: http://qp-iac-cdn-headers-alb-748420320.us-east-1.elb.amazonaws.com")
        print("- CloudFront: https://d8lo8nw3jettu.cloudfront.net")
        return True
    else:
        print("\n⚠️ Application may still be starting up.")
        print("Wait a few more minutes and test manually.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)