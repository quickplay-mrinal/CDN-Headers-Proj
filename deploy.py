#!/usr/bin/env python3
"""
Simple deployment script for CDN Headers Project
"""

import os
import sys
import subprocess
import argparse

def run_command(command):
    """Run shell command and return success status"""
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e.stderr}")
        return False

def deploy_infrastructure(deployment_type="core"):
    """Deploy infrastructure"""
    
    print("🚀 CDN Headers Project Deployment")
    print("=" * 40)
    
    # Set environment
    os.environ["PULUMI_CONFIG_PASSPHRASE"] = ""
    
    # Check if stack exists, create if not
    print("🔧 Setting up Pulumi stack...")
    run_command("pulumi stack select dev 2>/dev/null || pulumi stack init dev")
    run_command("pulumi config set aws:region us-east-1")
    
    # Deploy based on type
    if deployment_type == "core":
        print("📦 Deploying core infrastructure...")
        success = run_command("pulumi up --program __main_core__.py --yes")
    elif deployment_type == "full":
        print("📦 Deploying full infrastructure with CloudFront...")
        success = run_command("pulumi up --yes")
    else:
        print(f"❌ Unknown deployment type: {deployment_type}")
        return False
    
    if success:
        print("\n✅ Deployment completed successfully!")
        print("\n📋 Stack outputs:")
        run_command("pulumi stack output")
        
        print("\n🎯 Next steps:")
        print("1. Wait for ECS service to be healthy")
        print("2. Test: python test_endpoints.py http://$(pulumi stack output alb_dns_name)")
        print("3. Validate: python validate_deployment.py")
        return True
    else:
        print("❌ Deployment failed!")
        return False

def main():
    parser = argparse.ArgumentParser(description='Deploy CDN Headers Project')
    parser.add_argument('--type', choices=['core', 'full'], default='core',
                       help='Deployment type (default: core)')
    parser.add_argument('--destroy', action='store_true',
                       help='Destroy infrastructure instead of deploying')
    
    args = parser.parse_args()
    
    if args.destroy:
        print("🧹 Destroying infrastructure...")
        success = run_command("pulumi destroy --yes")
        if success:
            print("✅ Infrastructure destroyed successfully!")
        else:
            print("❌ Destroy failed!")
        return success
    
    return deploy_infrastructure(args.type)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)