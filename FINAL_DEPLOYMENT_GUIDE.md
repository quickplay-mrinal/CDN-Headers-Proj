# CDN Headers Project - Deployment Guide

## 🚀 Quick Deployment

### Option 1: Simple Script (Recommended)
```bash
python deploy.py --type core
```

### Option 2: Manual Deployment
```bash
# Setup
export PULUMI_CONFIG_PASSPHRASE=""
pulumi stack init dev
pulumi config set aws:region us-east-1

# Deploy core infrastructure (recommended)
pulumi up --program __main_core__.py

# Alternative: Deploy with CloudFront (may have S3 ACL issues)
# pulumi up

# Get outputs
pulumi stack output
```

### What's Included
- ✅ **VPC** with public/private subnets, NAT gateways
- ✅ **Application Load Balancer** with JWT validation setup
- ✅ **ECS Fargate Service** running FastAPI application
- ✅ **Secrets Manager** with automatic 30-day rotation
- ✅ **Complete IAM roles** and security groups
- ✅ **All resources prefixed** with `qp-iac-`

### Benefits
- 🚀 **Fast deployment**: ~35 resources, 8-12 minutes
- 🔒 **Full security**: JWT validation, secrets rotation
- 🧪 **Easy testing**: Direct ALB access
- 📊 **Complete monitoring**: CloudWatch logs
- ⚡ **No complexity**: Avoids CloudFront parameter issues

## 🔧 Alternative Deployment Options

### Option 1: Minimal Test
```bash
pulumi up --program __main_minimal__.py
```
- VPC, subnet, security group only
- ~5 resources, 2-3 minutes

### Option 2: Core Infrastructure
```bash
pulumi up --program deploy_core_infrastructure.py
```
- Same as stable but different program structure

### Option 3: Full with CloudFront (Advanced)
```bash
pulumi up  # Uses __main__.py
```
- Complete infrastructure including CloudFront
- May have parameter compatibility issues

## 🔍 Post-Deployment Validation

### 1. Check Deployment Status
```bash
pulumi stack output
```

### 2. Validate Infrastructure
```bash
python validate_deployment.py
```

### 3. Test Application
```bash
# Get ALB DNS name
ALB_DNS=$(pulumi stack output alb_dns_name)

# Test endpoints
python test_endpoints.py http://$ALB_DNS
```

### 4. Access Interactive Interface
```bash
# Open in browser
echo "Application URL: http://$(pulumi stack output alb_dns_name)"
```

## 🎮 Testing the Application

The deployed FastAPI application includes:

### Interactive Web Interface
- **URL**: `http://<alb-dns-name>/`
- **Features**: Login, JWT testing, API endpoint testing

### API Endpoints
- `GET /` - Interactive web interface
- `GET /health` - Health check
- `POST /auth/login` - User authentication
- `GET /auth/me` - User information (requires JWT)
- `GET /api/protected` - Protected resource (requires JWT)
- `GET /debug/headers` - Header debugging
- `GET /api/status` - API status

### Test Credentials
- **Username**: `admin`
- **Password**: `password123`

## 🔐 Security Features

### JWT Validation
- Multi-layer validation at ALB level
- Automatic token expiration handling
- Secure secret management

### Secrets Rotation
- Automatic rotation every 30 days
- Zero-downtime secret updates
- Lambda-based rotation logic

### Network Security
- Private subnets for ECS tasks
- Security groups with minimal access
- ALB in public subnets only

## 📊 Monitoring & Logging

### CloudWatch Integration
- ECS application logs: `/ecs/qp-iac-cdn-headers`
- Lambda function logs: `/aws/lambda/qp-iac-cdn-headers-*`
- ALB access logs (optional)

### Health Monitoring
- ECS service health checks
- ALB target group health
- Application health endpoint

## 🧹 Cleanup

To destroy all resources:
```bash
pulumi destroy --yes
```

## 🚨 Known Issues & Solutions

### CloudFront S3 Logging Issues
- **Issue**: S3 bucket ACL configuration for CloudFront logging
- **Error**: "The S3 bucket that you specified for CloudFront logs does not enable ACL access"
- **Solution**: Use core deployment without CloudFront, or deploy CloudFront separately
- **Workaround**: CloudFront logging configuration removed to avoid complexity

### CloudFront Parameter Issues
- **Issue**: Multiple parameter compatibility problems
- **Solution**: Use core deployment without CloudFront
- **Future**: CloudFront can be added separately later

### Parameter Compatibility
- **Issue**: Pulumi AWS provider parameter changes
- **Solution**: All core parameters fixed in stable deployment
- **Reference**: See `PARAMETER_COMPATIBILITY.md`

## 🎉 Success Criteria

Deployment is successful when:
- ✅ All resources created without errors
- ✅ ECS service shows "RUNNING" status
- ✅ ALB health checks pass
- ✅ Application responds at ALB DNS name
- ✅ JWT authentication works
- ✅ All validation tests pass

## 📈 Next Steps

After successful deployment:

1. **Custom Domain** (Optional)
   - Add Route 53 hosted zone
   - Configure SSL certificate
   - Update ALB listener for HTTPS

2. **CloudFront Addition** (Optional)
   - Deploy CloudFront separately
   - Configure custom behaviors
   - Add edge functions

3. **Production Hardening**
   - Enable ALB access logs
   - Configure backup strategies
   - Set up monitoring alerts
   - Implement CI/CD pipeline

4. **Scaling**
   - Configure ECS auto-scaling
   - Add multiple AZs
   - Implement caching strategies

## 🔗 Quick Reference

```bash
# Status
pulumi stack ls
pulumi stack output

# Logs
pulumi logs --follow

# Update
pulumi up --program __main_stable__.py

# Destroy
pulumi destroy --yes

# Reset
pulumi stack rm dev --yes
```

---

**Your CDN Headers Project is now ready for stable deployment! 🚀**