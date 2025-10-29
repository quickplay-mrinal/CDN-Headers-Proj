#!/usr/bin/env python3
"""
Quick fix for CloudFront header validation issue
"""

import subprocess
import sys
import os

def run_command(command):
    """Run shell command"""
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e.stderr}")
        return False

def fix_cloudfront():
    """Fix CloudFront configuration"""
    
    print("🔧 Fixing CloudFront Header Validation Issue")
    print("=" * 50)
    
    # Set environment
    os.environ["PULUMI_CONFIG_PASSPHRASE"] = ""
    
    print("📡 Updating CloudFront distribution...")
    print("This will temporarily disable CloudFront functions to allow access.")
    
    # Update the stack
    success = run_command("pulumi up --yes")
    
    if success:
        print("\n✅ CloudFront fix applied successfully!")
        print("\n🌐 Your site should now be accessible at:")
        print("https://d8lo8nw3jettu.cloudfront.net")
        print("\n⏱️ Note: CloudFront changes may take 5-15 minutes to propagate globally.")
        print("\n🧪 Test the site:")
        print("1. Open https://d8lo8nw3jettu.cloudfront.net in your browser")
        print("2. You should see the login interface")
        print("3. Try logging in with admin/password123")
        
        return True
    else:
        print("❌ Fix failed!")
        return False

def main():
    print("🚨 CloudFront Header Validation Fix")
    print("This will update your CloudFront distribution to allow normal browser access.")
    
    confirm = input("\nProceed with the fix? (y/N): ")
    if confirm.lower() != 'y':
        print("❌ Fix cancelled.")
        return False
    
    return fix_cloudfront()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)