#!/usr/bin/env python3
"""
Quick fix for ECS container - use simple HTTP server
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

def update_ecs_only():
    """Update only the ECS task definition"""
    print("🔧 Quick ECS Fix - Simple HTTP Server")
    print("=" * 50)
    
    # Set environment
    os.environ["PULUMI_CONFIG_PASSPHRASE"] = ""
    
    print("📦 Updating ECS task definition with simple HTTP server...")
    print("This will replace the complex FastAPI setup with a basic working server.")
    
    # Update the stack
    success = run_command("pulumi up --yes")
    
    if success:
        print("✅ ECS task definition updated!")
        return True
    else:
        print("❌ Update failed!")
        return False

def force_ecs_restart():
    """Force ECS service to restart with new task definition"""
    print("🔄 Forcing ECS service restart...")
    
    success = run_command(
        'aws ecs update-service --cluster qp-iac-cdn-headers-cluster '
        '--service qp-iac-cdn-headers-service --force-new-deployment'
    )
    
    if success:
        print("✅ ECS service restart initiated!")
        return True
    else:
        print("❌ Failed to restart ECS service")
        return False

def wait_for_health():
    """Wait for targets to become healthy"""
    print("⏱️ Waiting for targets to become healthy...")
    
    for i in range(10):  # Wait up to 10 minutes
        print(f"🔍 Check {i+1}/10: Testing health...")
        
        try:
            import requests
            response = requests.get(
                "http://qp-iac-cdn-headers-alb-748420320.us-east-1.elb.amazonaws.com/health",
                timeout=5
            )
            
            if response.status_code == 200:
                print("✅ Application is healthy!")
                print(f"Response: {response.text}")
                return True
            else:
                print(f"⏳ Status: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"⏳ Connection issue: {e}")
        
        if i < 9:  # Don't sleep on last iteration
            print("⏳ Waiting 60 seconds...")
            time.sleep(60)
    
    print("⚠️ Health check timeout. Check manually.")
    return False

def main():
    print("🚨 Quick ECS Fix - Simple HTTP Server")
    print("This will replace the complex container setup with a basic working HTTP server.")
    
    confirm = input("\nProceed with quick fix? (y/N): ")
    if confirm.lower() != 'y':
        print("❌ Fix cancelled.")
        return False
    
    # Update ECS task definition
    if not update_ecs_only():
        return False
    
    # Force restart
    if not force_ecs_restart():
        return False
    
    # Wait for health
    if wait_for_health():
        print("\n🎉 Quick fix completed successfully!")
        print("\n🌐 Your application is now accessible:")
        print("- Direct ALB: http://qp-iac-cdn-headers-alb-748420320.us-east-1.elb.amazonaws.com")
        print("- CloudFront: https://d8lo8nw3jettu.cloudfront.net")
        print("\n📋 Available endpoints:")
        print("- / (Main page)")
        print("- /health (Health check)")
        return True
    else:
        print("\n⚠️ Application may still be starting. Test manually in a few minutes.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)