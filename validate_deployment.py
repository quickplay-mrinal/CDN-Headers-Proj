#!/usr/bin/env python3
"""
Deployment validation script for QP-IAC CDN Headers Project
"""

import boto3
import json
import sys
import time
from botocore.exceptions import ClientError

class DeploymentValidator:
    def __init__(self, region='us-east-1'):
        self.region = region
        self.project_name = "qp-iac-cdn-headers"
        
        # Initialize AWS clients
        self.ec2 = boto3.client('ec2', region_name=region)
        self.elbv2 = boto3.client('elbv2', region_name=region)
        self.ecs = boto3.client('ecs', region_name=region)
        self.cloudfront = boto3.client('cloudfront')
        self.secrets = boto3.client('secretsmanager', region_name=region)
        self.lambda_client = boto3.client('lambda', region_name=region)
        
    def validate_vpc(self):
        """Validate VPC and networking components"""
        print("🌐 Validating VPC and networking...")
        try:
            # Check VPC
            vpcs = self.ec2.describe_vpcs(
                Filters=[{'Name': 'tag:Name', 'Values': [f'{self.project_name}-vpc']}]
            )
            if not vpcs['Vpcs']:
                print("❌ VPC not found")
                return False
            
            vpc_id = vpcs['Vpcs'][0]['VpcId']
            print(f"✅ VPC found: {vpc_id}")
            
            # Check subnets
            subnets = self.ec2.describe_subnets(
                Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
            )
            public_subnets = [s for s in subnets['Subnets'] if s.get('MapPublicIpOnLaunch')]
            private_subnets = [s for s in subnets['Subnets'] if not s.get('MapPublicIpOnLaunch')]
            
            print(f"✅ Public subnets: {len(public_subnets)}")
            print(f"✅ Private subnets: {len(private_subnets)}")
            
            # Check Internet Gateway
            igws = self.ec2.describe_internet_gateways(
                Filters=[{'Name': 'attachment.vpc-id', 'Values': [vpc_id]}]
            )
            if igws['InternetGateways']:
                print("✅ Internet Gateway attached")
            else:
                print("❌ Internet Gateway not found")
                return False
            
            # Check NAT Gateways
            nat_gws = self.ec2.describe_nat_gateways(
                Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
            )
            print(f"✅ NAT Gateways: {len(nat_gws['NatGateways'])}")
            
            return True
            
        except Exception as e:
            print(f"❌ VPC validation error: {e}")
            return False
    
    def validate_alb(self):
        """Validate Application Load Balancer"""
        print("⚖️ Validating ALB...")
        try:
            # Check ALB
            albs = self.elbv2.describe_load_balancers()
            project_albs = [alb for alb in albs['LoadBalancers'] 
                           if self.project_name in alb['LoadBalancerName']]
            
            if not project_albs:
                print("❌ ALB not found")
                return False
            
            alb = project_albs[0]
            print(f"✅ ALB found: {alb['LoadBalancerName']}")
            print(f"   DNS Name: {alb['DNSName']}")
            print(f"   State: {alb['State']['Code']}")
            
            # Check target groups
            target_groups = self.elbv2.describe_target_groups(
                LoadBalancerArn=alb['LoadBalancerArn']
            )
            print(f"✅ Target groups: {len(target_groups['TargetGroups'])}")
            
            # Check listeners
            listeners = self.elbv2.describe_listeners(
                LoadBalancerArn=alb['LoadBalancerArn']
            )
            print(f"✅ Listeners: {len(listeners['Listeners'])}")
            
            return True
            
        except Exception as e:
            print(f"❌ ALB validation error: {e}")
            return False
    
    def validate_ecs(self):
        """Validate ECS cluster and service"""
        print("🐳 Validating ECS...")
        try:
            # Check cluster
            clusters = self.ecs.describe_clusters(
                clusters=[f'{self.project_name}-cluster']
            )
            
            if not clusters['clusters']:
                print("❌ ECS cluster not found")
                return False
            
            cluster = clusters['clusters'][0]
            print(f"✅ ECS cluster found: {cluster['clusterName']}")
            print(f"   Status: {cluster['status']}")
            print(f"   Active services: {cluster['activeServicesCount']}")
            print(f"   Running tasks: {cluster['runningTasksCount']}")
            
            # Check service
            services = self.ecs.describe_services(
                cluster=cluster['clusterArn'],
                services=[f'{self.project_name}-service']
            )
            
            if services['services']:
                service = services['services'][0]
                print(f"✅ ECS service found: {service['serviceName']}")
                print(f"   Status: {service['status']}")
                print(f"   Desired count: {service['desiredCount']}")
                print(f"   Running count: {service['runningCount']}")
            else:
                print("❌ ECS service not found")
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ ECS validation error: {e}")
            return False
    
    def validate_secrets(self):
        """Validate Secrets Manager"""
        print("🔐 Validating Secrets Manager...")
        try:
            # Check JWT secret
            try:
                jwt_secret = self.secrets.describe_secret(
                    SecretId=f'{self.project_name}-jwt-secret'
                )
                print(f"✅ JWT secret found: {jwt_secret['Name']}")
                
                # Check rotation
                if jwt_secret.get('RotationEnabled'):
                    print("✅ JWT secret rotation enabled")
                else:
                    print("⚠️ JWT secret rotation not enabled")
                    
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    print("❌ JWT secret not found")
                    return False
                raise
            
            # Check API key secret
            try:
                api_secret = self.secrets.describe_secret(
                    SecretId=f'{self.project_name}-api-key-secret'
                )
                print(f"✅ API key secret found: {api_secret['Name']}")
                
                if api_secret.get('RotationEnabled'):
                    print("✅ API key secret rotation enabled")
                else:
                    print("⚠️ API key secret rotation not enabled")
                    
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    print("❌ API key secret not found")
                    return False
                raise
            
            return True
            
        except Exception as e:
            print(f"❌ Secrets validation error: {e}")
            return False
    
    def validate_lambda_functions(self):
        """Validate Lambda functions"""
        print("⚡ Validating Lambda functions...")
        try:
            functions_to_check = [
                f'{self.project_name}-rotation-lambda',
                f'{self.project_name}-jwt-validation-lambda',
                f'{self.project_name}-jwt-generator'
            ]
            
            found_functions = 0
            
            for func_name in functions_to_check:
                try:
                    func = self.lambda_client.get_function(FunctionName=func_name)
                    print(f"✅ Lambda function found: {func_name}")
                    print(f"   Runtime: {func['Configuration']['Runtime']}")
                    print(f"   State: {func['Configuration']['State']}")
                    found_functions += 1
                except ClientError as e:
                    if e.response['Error']['Code'] == 'ResourceNotFoundException':
                        print(f"⚠️ Lambda function not found: {func_name}")
                    else:
                        raise
            
            print(f"✅ Found {found_functions}/{len(functions_to_check)} Lambda functions")
            return found_functions > 0
            
        except Exception as e:
            print(f"❌ Lambda validation error: {e}")
            return False
    
    def validate_cloudfront(self):
        """Validate CloudFront distribution"""
        print("🌍 Validating CloudFront...")
        try:
            # List distributions and find ours
            distributions = self.cloudfront.list_distributions()
            
            project_distributions = []
            for dist in distributions.get('DistributionList', {}).get('Items', []):
                if self.project_name in dist.get('Comment', ''):
                    project_distributions.append(dist)
            
            if not project_distributions:
                print("❌ CloudFront distribution not found")
                return False
            
            dist = project_distributions[0]
            print(f"✅ CloudFront distribution found: {dist['Id']}")
            print(f"   Domain name: {dist['DomainName']}")
            print(f"   Status: {dist['Status']}")
            print(f"   Enabled: {dist['Enabled']}")
            
            # Check origins
            print(f"✅ Origins: {len(dist['Origins']['Items'])}")
            
            # Check cache behaviors
            default_behavior = dist['DefaultCacheBehavior']
            print(f"✅ Default cache behavior configured")
            print(f"   Viewer protocol policy: {default_behavior['ViewerProtocolPolicy']}")
            
            return True
            
        except Exception as e:
            print(f"❌ CloudFront validation error: {e}")
            return False
    
    def run_validation(self):
        """Run all validation checks"""
        print("🔍 Starting QP-IAC CDN Headers Project Deployment Validation")
        print(f"🌍 Region: {self.region}")
        print("=" * 70)
        
        validations = [
            ("VPC & Networking", self.validate_vpc),
            ("Application Load Balancer", self.validate_alb),
            ("ECS Cluster & Service", self.validate_ecs),
            ("Secrets Manager", self.validate_secrets),
            ("Lambda Functions", self.validate_lambda_functions),
            ("CloudFront Distribution", self.validate_cloudfront),
        ]
        
        passed = 0
        total = len(validations)
        
        for validation_name, validation_func in validations:
            print(f"\n📋 Validating: {validation_name}")
            try:
                if validation_func():
                    passed += 1
                    print(f"✅ {validation_name} validation passed")
                else:
                    print(f"❌ {validation_name} validation failed")
            except Exception as e:
                print(f"❌ {validation_name} validation error: {e}")
            
            time.sleep(1)
        
        print("\n" + "=" * 70)
        print(f"🏁 Validation Results: {passed}/{total} components validated successfully")
        
        if passed == total:
            print("🎉 All components validated! Your deployment is ready.")
            print("\n📋 Next steps:")
            print("1. Get your CloudFront domain name: pulumi stack output cloudfront_domain_name")
            print("2. Test the application: python test_endpoints.py https://your-domain")
            print("3. Access the interactive interface in your browser")
            return True
        else:
            print("⚠️  Some components failed validation. Please check the deployment.")
            return False

def main():
    region = 'us-east-1'
    if len(sys.argv) > 1:
        region = sys.argv[1]
    
    validator = DeploymentValidator(region)
    success = validator.run_validation()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()