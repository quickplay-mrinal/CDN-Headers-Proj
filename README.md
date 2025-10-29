# QP-IAC CDN Headers Project

A production-ready AWS infrastructure project that implements secure ALB communication with JWT validation, automatic secrets rotation, and interactive FastAPI application.

## 🏗️ Architecture Overview

This project creates a complete infrastructure stack including:

- **Application Load Balancer (ALB)** with JWT validation ready
- **ECS Fargate Service** running an interactive FastAPI application
- **AWS Secrets Manager** with automatic 30-day rotation
- **VPC** with public/private subnets and NAT gateways
- **Complete IAM roles** and security groups
- **CloudWatch logging** and monitoring

## 🔧 Components

### Infrastructure Components

1. **VPC & Networking** (`modules/vpc.py`)
   - VPC with public and private subnets
   - Internet Gateway and NAT Gateways
   - Route tables and security groups

2. **Secrets Management** (`modules/secrets.py`)
   - JWT secret with automatic rotation
   - API key management
   - Lambda function for secret rotation

3. **Application Load Balancer** (`modules/alb.py`)
   - ALB with JWT validation
   - Target groups for ECS services
   - Security groups and listener rules

4. **ECS Service** (`modules/ecs.py`)
   - Fargate cluster and service
   - Task definitions with proper IAM roles
   - CloudWatch logging

5. **CloudFront Distribution** (`modules/cloudfront.py`)
   - Custom cache behaviors
   - CloudFront functions for validation
   - Access logging and monitoring

6. **Lambda Functions** (`modules/lambda_functions.py`)
   - CloudFront function for request validation
   - Lambda@Edge for origin request processing
   - JWT token generator API

### Application Components

1. **FastAPI Application** (`app/main.py`)
   - Interactive web interface
   - JWT authentication endpoints
   - Protected API routes
   - Header debugging tools

## 🚀 Quick Deployment

### Prerequisites
```bash
# Install dependencies
pip install -r requirements.txt

# Configure AWS CLI
aws configure

# Install Pulumi (if not installed)
# Follow: https://www.pulumi.com/docs/get-started/install/
```

### Deploy Infrastructure
```bash
# Setup Pulumi stack
export PULUMI_CONFIG_PASSPHRASE=""
pulumi stack init dev
pulumi config set aws:region us-east-1

# Deploy core infrastructure (recommended)
pulumi up --program __main_core__.py

# Alternative: Deploy with CloudFront (advanced)
pulumi up

# Get outputs
pulumi stack output
```

## 🔐 Security Features

### JWT Validation
- JWT tokens generated with rotating secrets
- Token validation at CloudFront and ALB levels
- Automatic token expiration handling

### Secrets Rotation
- Automatic rotation every 30 days
- Zero-downtime secret updates
- Integration with ALB and application

### Header Validation
- CloudFront functions validate incoming requests
- Custom headers added for CDN identification
- Request ID tracking for debugging

## 📊 Monitoring & Logging

### CloudWatch Integration
- CloudFront access logs
- ECS application logs
- Lambda function logs
- Custom metrics and alarms

### Dashboards
- CloudFront performance metrics
- Application health monitoring
- Error rate tracking

## 🧪 Testing

### Interactive Web Interface
Access the deployed application through the CloudFront URL to:

1. **Login & Get JWT Token**
   - Username: `admin`
   - Password: `password123`

2. **Test Protected Endpoints**
   - User information retrieval
   - Protected API access
   - Header validation

3. **Debug Headers**
   - View all request headers
   - Check CDN validation status
   - Monitor request processing

### API Endpoints

- `GET /` - Interactive web interface
- `GET /health` - Health check
- `POST /auth/login` - User authentication
- `GET /auth/me` - User information
- `GET /api/protected` - Protected resource
- `GET /debug/headers` - Header debugging
- `GET /api/status` - API status

## 🔄 Secrets Rotation

The system automatically rotates secrets every 30 days:

1. **JWT Secret Rotation**
   - New secret generated
   - ALB updated with new secret
   - Old secret deprecated gracefully

2. **API Key Rotation**
   - CDN authentication keys updated
   - CloudFront functions updated
   - Zero-downtime rotation

## 📈 Scaling

### Horizontal Scaling
- ECS service auto-scaling based on CPU/memory
- ALB distributes traffic across multiple tasks
- CloudFront global edge locations

### Vertical Scaling
- Adjustable ECS task CPU/memory
- Configurable ALB capacity
- Lambda function memory optimization

## 🛠️ Configuration

### Environment Variables
- `JWT_SECRET_ARN` - ARN of JWT secret in Secrets Manager
- `PORT` - Application port (default: 8000)
- `ENVIRONMENT` - Deployment environment

### Pulumi Configuration
- `aws:region` - AWS region for deployment
- Custom configurations in `config.py`

## 🔍 Troubleshooting

### Common Issues

1. **JWT Validation Failures**
   - Check secret rotation status
   - Verify token expiration
   - Review CloudWatch logs

2. **CloudFront Issues**
   - Check function deployment
   - Verify origin configuration
   - Review access logs

3. **ECS Service Issues**
   - Check task health
   - Review security groups
   - Verify IAM permissions

### Debugging Tools

1. **Header Debug Endpoint**
   ```bash
   curl https://your-cloudfront-domain/debug/headers
   ```

2. **Health Check**
   ```bash
   curl https://your-cloudfront-domain/health
   ```

3. **CloudWatch Logs**
   - ECS task logs: `/ecs/qp-iac-cdn-headers`
   - Lambda logs: `/aws/lambda/qp-iac-cdn-headers-*`

## 📝 Resource Naming Convention

All resources follow the naming pattern: `qp-iac-cdn-headers-<resource-type>`

Examples:
- `qp-iac-cdn-headers-vpc`
- `qp-iac-cdn-headers-alb`
- `qp-iac-cdn-headers-distribution`

## 🧹 Cleanup

To destroy all resources:

```bash
pulumi destroy
```

## 📚 Additional Resources

- [AWS CloudFront Documentation](https://docs.aws.amazon.com/cloudfront/)
- [AWS Secrets Manager](https://docs.aws.amazon.com/secretsmanager/)
- [Pulumi AWS Provider](https://www.pulumi.com/registry/packages/aws/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.