# 🚀 CloudFront Function + JWT Security - Deployment Guide

## 📋 Quick Start

### Option 1: Interactive Deployment (Recommended)
```powershell
cd pulumi
.\select-region.ps1
```

### Option 2: Direct Deployment
```powershell
cd pulumi
.\deploy.ps1 -Region ap-south-2 -StackName dev
```

## 🔧 AMI Resolution

This infrastructure uses **dynamic AMI lookup** to ensure you always get the latest, valid Amazon Linux AMI for your region.

### How it Works:
1. **Primary**: Tries to find the latest Amazon Linux 2023 AMI
2. **Fallback 1**: Falls back to Amazon Linux 2 if AL2023 is not available
3. **Fallback 2**: Uses static AMI mapping for known regions
4. **Ultimate Fallback**: Uses us-east-1 AMI as last resort

### Supported Regions:
- **ap-south-2** (Asia Pacific - Hyderabad) - Default
- **us-east-1** (US East - N. Virginia)
- **us-west-2** (US West - Oregon)
- **eu-west-1** (Europe - Ireland)
- **ap-south-1** (Asia Pacific - Mumbai) - Fallback

## 🛠️ Troubleshooting

### Issue: 502 Bad Gateway / Unhealthy Targets
```
502 Bad Gateway - Target group has no healthy targets
```

**Root Causes & Solutions**:

1. **NAT Gateway Missing**: EC2 instances in private subnets need internet access
   - **Solution**: Infrastructure now includes NAT Gateway for private subnet internet access
   - **Cost**: ~$45/month for NAT Gateway (required for production)

2. **User Data Script Failures**: Package installation fails without internet
   - **Solution**: NAT Gateway enables yum/package manager access
   - **Verification**: Check `/var/log/jwt-demo/startup.log` on instances

3. **Health Check Endpoint**: Target group health checks failing
   - **Solution**: Uses dedicated `/health` endpoint instead of `/`
   - **Test**: `curl http://alb-dns/health` should return "OK"

### Issue: AMI Not Found Error
```
ValidationError: The image id '[ami-xxxxx]' does not exist
```

**Solution**: The infrastructure now uses dynamic AMI lookup, which should resolve this automatically.

### Issue: Region Not Supported
If you get an error about unsupported region:

1. **Check Available Regions**:
   ```bash
   aws ec2 describe-regions --output table
   ```

2. **Update AMI Mapping** in `modules/ami.py`:
   ```python
   # Add your region to the static mapping
   static_mapping = {
       "your-region": "ami-xxxxxxxxx",
       # ... existing mappings
   }
   ```

3. **Find AMI for Your Region**:
   ```bash
   aws ec2 describe-images \
     --owners amazon \
     --filters "Name=name,Values=al2023-ami-*-x86_64" \
     --query 'Images[*].[ImageId,Name,CreationDate]' \
     --output table \
     --region your-region
   ```

## 🧪 Pre-Deployment Validation

Run validation before deployment:
```powershell
cd pulumi
python validate.py
```

Expected output:
```
✓ config module imported successfully
✓ vpc module imported successfully
✓ security_groups module imported successfully
✓ iam module imported successfully
✓ ec2 module imported successfully
✓ ami module imported successfully
✓ alb module imported successfully
✓ cloudfront module imported successfully

✓ Configuration loaded for region: ap-south-2
✓ VPC CIDR: 10.0.0.0/16
✓ Instance Type: t3.micro
✓ Availability Zones: ['ap-south-2a', 'ap-south-2b']

✓ User data generated successfully
✓ User data length: 9516 characters

✓ JWT token generated successfully
✓ JWT token format: 3 parts

Validation Results: 4/4 tests passed
✓ All validation tests passed! Infrastructure is ready for deployment.
```

## 📊 Deployment Timeline

| Step | Duration | Description |
|------|----------|-------------|
| Validation | 30s | Module and configuration validation |
| VPC Creation | 3-4 min | VPC, subnets, IGW, **NAT Gateway**, routing |
| Security Groups | 30s | ALB and EC2 security groups |
| IAM Resources | 1 min | Roles, policies, instance profile |
| ALB Setup | 2-3 min | Load balancer, target group, listener |
| EC2 Resources | 5-7 min | Launch template, ASG, **user data execution** |
| Target Health | 3-5 min | **Waiting for targets to become healthy** |
| CloudFront | 5-10 min | Distribution and function deployment |
| **Total** | **20-25 min** | Complete infrastructure deployment |

**Note**: NAT Gateway adds ~2 minutes to deployment but is **essential** for EC2 internet access.

## 🔐 Security Features Deployed

### Network Security:
- ✅ VPC with public/private subnet isolation
- ✅ Security groups with least privilege access
- ✅ ALB in public subnets, EC2 in private subnets

### Application Security:
- ✅ JWT validation at CloudFront edge
- ✅ Industry-standard JWT token handling
- ✅ Comprehensive error responses for invalid tokens

### Operational Security:
- ✅ IAM roles with minimal required permissions
- ✅ CloudWatch logging integration
- ✅ SSM access for secure instance management

## 🧹 Cleanup

```powershell
cd pulumi
pulumi destroy
pulumi stack rm dev
```

## 📞 Support

If you encounter issues:

1. **Check AWS Credentials**:
   ```bash
   aws sts get-caller-identity
   ```

2. **Verify Region Support**:
   ```bash
   aws ec2 describe-availability-zones --region ap-south-2
   ```

3. **Run Validation**:
   ```bash
   python validate.py
   ```

4. **Check Pulumi Logs**:
   ```bash
   pulumi logs
   ```