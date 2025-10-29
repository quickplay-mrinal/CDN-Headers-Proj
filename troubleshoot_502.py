#!/usr/bin/env python3
"""
Troubleshoot 502 Bad Gateway error for CloudFront
"""

import subprocess
import sys
import os
import requests
import time

def run_command(command):
    """Run shell command"""
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e.stderr}")
        return None

def test_alb_directly():
    """Test ALB directly to see if it's working"""
    print("🔍 Testing ALB directly...")
    
    alb_dns = "qp-iac-cdn-headers-alb-748420320.us-east-1.elb.amazonaws.com"
    
    try:
        # Test HTTP
        response = requests.get(f"http://{alb_dns}", timeout=10)
        print(f"✅ ALB HTTP Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ ALB is working correctly")
            return True
        else:
            print(f"❌ ALB returned status {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ ALB connection failed: {e}")
        return False

def test_ecs_health():
    """Check ECS service health"""
    print("🐳 Checking ECS service health...")
    
    # Get ECS service status
    result = run_command("aws ecs describe-services --cluster qp-iac-cdn-headers-cluster --services qp-iac-cdn-headers-service --query 'services[0].{Status:status,Running:runningCount,Desired:desiredCount}' --output table")
    
    if result:
        print("ECS Service Status:")
        print(result)
        return True
    else:
        print("❌ Could not get ECS service status")
        return False

def fix_cloudfront_config():
    """Fix CloudFront configuration"""
    print("🔧 Fixing CloudFront configuration...")
    
    # Set environment
    os.environ["PULUMI_CONFIG_PASSPHRASE"] = ""
    
    print("📡 Updating CloudFront distribution...")
    print("Removing default_root_object and fixing error pages...")
    
    # Update the stack
    result = run_command("pulumi up --yes")
    
    if result:
        print("✅ CloudFront configuration updated!")
        print("⏱️ CloudFront changes may take 5-15 minutes to propagate.")
        return True
    else:
        print("❌ CloudFront update failed!")
        return False

def wait_for_cloudfront():
    """Wait for CloudFront to propagate changes"""
    print("⏱️ Waiting for CloudFront to propagate changes...")
    
    cloudfront_url = "https://d8lo8nw3jettu.cloudfront.net"
    
    for i in range(10):  # Try for 10 minutes
        try:
            print(f"🔄 Attempt {i+1}/10: Testing CloudFront...")
            response = requests.get(cloudfront_url, timeout=10)
            
            if response.status_code == 200:
                print("✅ CloudFront is now working!")
                return True
            elif response.status_code == 502:
                print("⏳ Still getting 502, waiting...")
            else:
                print(f"🔄 Status: {response.status_code}, waiting...")
                
        except requests.exceptions.RequestException as e:
            print(f"🔄 Connection issue: {e}")
        
        if i < 9:  # Don't sleep on last iteration
            time.sleep(60)  # Wait 1 minute between attempts
    
    print("❌ CloudFront still not working after 10 minutes")
    return False

def main():
    print("🚨 CloudFront 502 Bad Gateway Troubleshooter")
    print("=" * 50)
    
    # Step 1: Test ALB directly
    alb_working = test_alb_directly()
    
    if not alb_working:
        print("\n❌ ALB is not working. Check ECS service first.")
        test_ecs_health()
        print("\n🔧 Recommended actions:")
        print("1. Check ECS service logs: aws logs tail /ecs/qp-iac-cdn-headers --follow")
        print("2. Check ALB target group health in AWS Console")
        print("3. Verify security groups allow traffic")
        return False
    
    # Step 2: Fix CloudFront configuration
    print(f"\n✅ ALB is working. The issue is with CloudFront configuration.")
    print("The problem: CloudFront is looking for /index.html but FastAPI serves at /")
    
    confirm = input("\nFix CloudFront configuration? (y/N): ")
    if confirm.lower() != 'y':
        print("❌ Fix cancelled.")
        return False
    
    if not fix_cloudfront_config():
        return False
    
    # Step 3: Wait for propagation
    print(f"\n⏱️ CloudFront changes are propagating...")
    print("This can take 5-15 minutes globally.")
    
    wait_confirm = input("Wait and test CloudFront propagation? (y/N): ")
    if wait_confirm.lower() == 'y':
        return wait_for_cloudfront()
    else:
        print("✅ Configuration updated. Test manually in 10-15 minutes.")
        return True

if __name__ == "__main__":
    success = main()
    
    if success:
        print("\n🎉 Troubleshooting completed successfully!")
        print("\n🌐 Test your application:")
        print("- CloudFront: https://d8lo8nw3jettu.cloudfront.net")
        print("- Direct ALB: http://qp-iac-cdn-headers-alb-748420320.us-east-1.elb.amazonaws.com")
    else:
        print("\n❌ Troubleshooting failed. Check the steps above.")
    
    sys.exit(0 if success else 1)