# QP-IAC CDN Headers Project - Network Architecture

## 🏗️ High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                 INTERNET                                        │
└─────────────────────────┬───────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           AWS CLOUDFRONT (CDN)                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐            │
│  │   Edge Location │    │   Edge Location │    │   Edge Location │            │
│  │   (US-East-1)   │    │   (EU-West-1)   │    │   (AP-South-1)  │            │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘            │
│                                    │                                           │
│  Distribution ID: E3MDA7NNMYC761   │                                           │
│  Domain: d8lo8nw3jettu.cloudfront.net                                          │
└────────────────────────────────────┼───────────────────────────────────────────┘
                                     │
                                     ▼ HTTPS/HTTP
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              AWS VPC (10.0.0.0/16)                             │
│                                                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │                          PUBLIC SUBNETS                                     │ │
│  │                                                                             │ │
│  │  ┌──────────────────────┐              ┌──────────────────────┐            │ │
│  │  │   Public Subnet 1    │              │   Public Subnet 2    │            │ │
│  │  │   (10.0.1.0/24)      │              │   (10.0.2.0/24)      │            │ │
│  │  │   AZ: us-east-1a     │              │   AZ: us-east-1b     │            │ │
│  │  │                      │              │                      │            │ │
│  │  │  ┌─────────────────┐ │              │ ┌─────────────────┐  │            │ │
│  │  │  │       ALB       │ │              │ │    NAT Gateway  │  │            │ │
│  │  │  │ (Internet-Facing)│ │              │ │                 │  │            │ │
│  │  │  │ Port: 80/443    │ │              │ │                 │  │            │ │
│  │  │  └─────────────────┘ │              │ └─────────────────┘  │            │ │
│  │  └──────────────────────┘              └──────────────────────┘            │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
│                                     │                                           │
│                                     ▼ Port 8000                                 │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │                         PRIVATE SUBNETS                                     │ │
│  │                                                                             │ │
│  │  ┌──────────────────────┐              ┌──────────────────────┐            │ │
│  │  │  Private Subnet 1    │              │  Private Subnet 2    │            │ │
│  │  │   (10.0.3.0/24)      │              │   (10.0.4.0/24)      │            │ │
│  │  │   AZ: us-east-1a     │              │   AZ: us-east-1b     │            │ │
│  │  │                      │              │                      │            │ │
│  │  │ ┌─────────────────┐  │              │ ┌─────────────────┐  │            │ │
│  │  │ │  ECS Fargate    │  │              │ │  ECS Fargate    │  │            │ │
│  │  │ │     Task 1      │  │              │ │     Task 2      │  │            │ │
│  │  │ │ FastAPI App     │  │              │ │ FastAPI App     │  │            │ │
│  │  │ │ Port: 8000      │  │              │ │ Port: 8000      │  │            │ │
│  │  │ └─────────────────┘  │              │ └─────────────────┘  │            │ │
│  │  └──────────────────────┘              └──────────────────────┘            │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            AWS MANAGED SERVICES                                 │
│                                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                │
│  │ Secrets Manager │  │   CloudWatch    │  │   Lambda        │                │
│  │                 │  │                 │  │                 │                │
│  │ • JWT Secret    │  │ • ECS Logs      │  │ • JWT Generator │                │
│  │ • API Key       │  │ • ALB Metrics   │  │ • CF Functions  │                │
│  │ • Auto Rotation │  │ • Dashboards    │  │ • Rotation      │                │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘                │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 🔄 Data Flow Diagram

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Client    │    │ CloudFront  │    │     ALB     │    │ ECS Fargate │
│  Browser    │    │    CDN      │    │Load Balancer│    │   Tasks     │
└──────┬──────┘    └──────┬──────┘    └──────┬──────┘    └──────┬──────┘
       │                  │                  │                  │
       │ 1. HTTPS Request │                  │                  │
       ├─────────────────►│                  │                  │
       │                  │                  │                  │
       │                  │ 2. Origin Request│                  │
       │                  ├─────────────────►│                  │
       │                  │   (with headers) │                  │
       │                  │                  │                  │
       │                  │                  │ 3. Route to Task │
       │                  │                  ├─────────────────►│
       │                  │                  │   Port 8000      │
       │                  │                  │                  │
       │                  │                  │ 4. Response      │
       │                  │                  │◄─────────────────┤
       │                  │                  │                  │
       │                  │ 5. Cached Response│                 │
       │                  │◄─────────────────┤                  │
       │                  │                  │                  │
       │ 6. Final Response│                  │                  │
       │◄─────────────────┤                  │                  │
       │                  │                  │                  │
```

## 🔐 Security Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              SECURITY LAYERS                                    │
│                                                                                 │
│  Layer 1: CloudFront Security                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │ • CloudFront Functions (Request Validation)                                │ │
│  │ • Custom Headers (X-CDN-Auth)                                              │ │
│  │ • HTTPS Enforcement                                                        │ │
│  │ • Geographic Restrictions (Optional)                                       │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
│  Layer 2: Network Security                                                     │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │ • VPC Isolation (10.0.0.0/16)                                             │ │
│  │ • Security Groups (Port-based Access Control)                             │ │
│  │ • Private Subnets (ECS Tasks)                                             │ │
│  │ • NAT Gateway (Outbound Internet Access)                                  │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                 │
│  Layer 3: Application Security                                                 │
│  ┌─────────────────────────────────────────────────────────────────────────────┐ │
│  │ • JWT Token Validation                                                     │ │
│  │ • API Authentication                                                       │ │
│  │ • Secrets Manager Integration                                              │ │
│  │ • Automatic Secret Rotation (30 days)                                     │ │
│  └─────────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 📊 Component Details

### CloudFront Distribution
- **Distribution ID**: E3MDA7NNMYC761
- **Domain**: d8lo8nw3jettu.cloudfront.net
- **Price Class**: PriceClass_100 (US, Canada, Europe)
- **Cache Behaviors**: 
  - Default: Redirect to HTTPS
  - /api/*: No caching
  - /health: Short caching (30s)

### Application Load Balancer
- **DNS**: qp-iac-cdn-headers-alb-748420320.us-east-1.elb.amazonaws.com
- **Type**: Internet-facing Application Load Balancer
- **Listeners**: HTTP (80) → Forward to Target Group
- **Health Check**: /health endpoint

### ECS Fargate Service
- **Cluster**: qp-iac-cdn-headers-cluster
- **Service**: qp-iac-cdn-headers-service
- **Task Definition**: qp-iac-cdn-headers-task
- **Desired Count**: 2 tasks
- **CPU/Memory**: 256 CPU, 512 MB Memory

### VPC Configuration
- **CIDR**: 10.0.0.0/16
- **Public Subnets**: 10.0.1.0/24, 10.0.2.0/24
- **Private Subnets**: 10.0.3.0/24, 10.0.4.0/24
- **Availability Zones**: us-east-1a, us-east-1b

## 🔄 Traffic Flow Patterns

### 1. Normal User Request
```
User → CloudFront → ALB → ECS Task → Response
```

### 2. API Request with JWT
```
User → CloudFront (Header Validation) → ALB → ECS Task (JWT Validation) → Response
```

### 3. Health Check Flow
```
ALB Health Check → ECS Task /health → 200 OK
```

### 4. Secret Rotation Flow
```
Lambda (Scheduled) → Secrets Manager → Update Secret → Notify ECS
```

## 🎯 Key Features Demonstrated

### ✅ **Scalability**
- Multi-AZ deployment
- Auto-scaling ECS tasks
- Global CDN distribution

### ✅ **Security**
- Multi-layer security (CDN, Network, Application)
- JWT authentication
- Automatic secret rotation
- Private subnet isolation

### ✅ **High Availability**
- Load balancer across multiple AZs
- ECS service with desired count
- CloudFront global edge locations

### ✅ **Monitoring & Observability**
- CloudWatch logs and metrics
- ALB access logs
- ECS task monitoring
- Custom dashboards

## 📈 Performance Characteristics

### **Latency**
- CloudFront Edge: < 50ms globally
- ALB to ECS: < 10ms
- Application Response: < 100ms

### **Throughput**
- ALB: Up to 25,000 requests/second
- ECS Tasks: Configurable based on CPU/Memory
- CloudFront: Unlimited (with caching)

### **Availability**
- Target: 99.9% uptime
- Multi-AZ redundancy
- Automatic failover

## 🔧 Infrastructure as Code

All infrastructure is defined using **Pulumi** with Python:
- **Declarative**: Infrastructure defined as code
- **Version Controlled**: All changes tracked in Git
- **Reproducible**: Deploy identical environments
- **Automated**: CI/CD pipeline ready

## 🎪 Demo Scenarios

### 1. **Basic Connectivity**
- Access main page via CloudFront
- Test health endpoint
- Verify load balancing

### 2. **JWT Authentication**
- Login to get JWT token
- Access protected endpoints
- Test token expiration

### 3. **CDN Validation**
- Show header injection
- Demonstrate caching behavior
- Test geographic distribution

### 4. **Security Features**
- Secret rotation demonstration
- Network isolation verification
- Security group validation

### 5. **Monitoring & Logging**
- CloudWatch dashboards
- ECS task logs
- ALB metrics

This architecture provides a production-ready, scalable, and secure foundation for your CDN Headers Project! 🚀