#!/usr/bin/env python3
"""
Validation script to test the modular Pulumi infrastructure
Tests configuration and module imports without deploying
"""

import sys
import os

def test_imports():
    """Test that all modules can be imported successfully"""
    print("Testing module imports...")
    
    try:
        from config import get_config, print_config_info, get_ami_id
        print("✓ config module imported successfully")
        
        from modules.vpc import create_vpc
        print("✓ vpc module imported successfully")
        
        from modules.security_groups import create_security_groups
        print("✓ security_groups module imported successfully")
        
        from modules.iam import create_iam_resources
        print("✓ iam module imported successfully")
        
        from modules.ec2 import create_ec2_resources, create_user_data
        print("✓ ec2 module imported successfully")
        
        from modules.ami import get_latest_amazon_linux_ami, get_latest_ubuntu_ami
        print("✓ ami module imported successfully")
        
        from modules.alb import create_target_group_with_vpc, attach_asg_to_target_group
        print("✓ alb module imported successfully")
        
        from modules.cloudfront import create_jwt_function, create_cloudfront_distribution, create_sample_jwt
        print("✓ cloudfront module imported successfully")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def test_configuration():
    """Test configuration functionality"""
    print("\nTesting configuration...")
    
    try:
        from config import get_config
        
        config = get_config()
        print(f"✓ Configuration loaded for region: {config['aws_region']}")
        print(f"✓ VPC CIDR: {config['network_config']['vpc_cidr']}")
        print(f"✓ Instance Type: {config['ec2_config']['instance_type']}")
        print(f"✓ Availability Zones: {config['network_config']['availability_zones']}")
        
        return True
        
    except Exception as e:
        print(f"✗ Configuration error: {e}")
        return False

def test_user_data():
    """Test user data generation"""
    print("\nTesting user data generation...")
    
    try:
        from config import get_config
        from modules.ec2 import create_user_data
        
        config = get_config()
        user_data = create_user_data(config)
        
        if user_data and len(user_data) > 0:
            print("✓ User data generated successfully")
            print(f"✓ User data length: {len(user_data)} characters")
            return True
        else:
            print("✗ User data generation failed")
            return False
            
    except Exception as e:
        print(f"✗ User data error: {e}")
        return False

def test_jwt_sample():
    """Test JWT sample generation"""
    print("\nTesting JWT sample generation...")
    
    try:
        from modules.cloudfront import create_sample_jwt
        
        jwt_token = create_sample_jwt()
        
        if jwt_token and len(jwt_token.split('.')) == 3:
            print("✓ JWT token generated successfully")
            print(f"✓ JWT token format: {len(jwt_token.split('.'))} parts")
            return True
        else:
            print("✗ JWT token generation failed")
            return False
            
    except Exception as e:
        print(f"✗ JWT generation error: {e}")
        return False

def main():
    """Run all validation tests"""
    print("CloudFront Function + JWT Security - Module Validation")
    print("=" * 55)
    
    tests = [
        test_imports,
        test_configuration,
        test_user_data,
        test_jwt_sample
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 55)
    print(f"Validation Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ All validation tests passed! Infrastructure is ready for deployment.")
        return True
    else:
        print("✗ Some validation tests failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)