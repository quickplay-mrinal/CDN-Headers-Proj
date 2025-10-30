# Troubleshooting script for CloudFront JWT Security Infrastructure

Write-Host "CloudFront JWT Security - Troubleshooting Script" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

# Get Pulumi outputs
Write-Host "Getting deployment information..." -ForegroundColor Yellow

try {
    $ALB_DNS = pulumi stack output alb_dns_name
    $TARGET_GROUP_ARN = pulumi stack output target_group_arn
    $VPC_ID = pulumi stack output vpc_id
    $REGION = pulumi stack output region
    $NAT_GATEWAY_ID = pulumi stack output nat_gateway_id
    $NAT_EIP = pulumi stack output nat_eip
    
    Write-Host "Region: $REGION" -ForegroundColor Green
    Write-Host "ALB DNS: $ALB_DNS" -ForegroundColor Green
    Write-Host "Target Group ARN: $TARGET_GROUP_ARN" -ForegroundColor Green
    Write-Host "VPC ID: $VPC_ID" -ForegroundColor Green
    Write-Host "NAT Gateway ID: $NAT_GATEWAY_ID" -ForegroundColor Green
    Write-Host "NAT Gateway EIP: $NAT_EIP" -ForegroundColor Green
    Write-Host ""
    
} catch {
    Write-Host "Failed to get Pulumi outputs. Make sure the stack is deployed." -ForegroundColor Red
    exit 1
}

# Test ALB health
Write-Host "Testing ALB Health..." -ForegroundColor Cyan
Write-Host "--------------------" -ForegroundColor Cyan

Write-Host "Testing ALB direct access..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://$ALB_DNS" -UseBasicParsing -TimeoutSec 10 -ErrorAction SilentlyContinue
    Write-Host "ALB Response: $($response.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "ALB Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "Testing ALB health endpoint..." -ForegroundColor Yellow
try {
    $healthResponse = Invoke-WebRequest -Uri "http://$ALB_DNS/health" -UseBasicParsing -TimeoutSec 10 -ErrorAction SilentlyContinue
    Write-Host "Health Check Response: $($healthResponse.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "Health Check Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# Check target group health
Write-Host "Checking Target Group Health..." -ForegroundColor Cyan
Write-Host "------------------------------" -ForegroundColor Cyan

try {
    $targetHealth = aws elbv2 describe-target-health --target-group-arn $TARGET_GROUP_ARN --region $REGION --output json | ConvertFrom-Json
    
    if ($targetHealth.TargetHealthDescriptions.Count -eq 0) {
        Write-Host "No targets registered in target group!" -ForegroundColor Red
    } else {
        foreach ($target in $targetHealth.TargetHealthDescriptions) {
            $instanceId = $target.Target.Id
            $port = $target.Target.Port
            $health = $target.TargetHealth.State
            $reason = $target.TargetHealth.Reason
            
            if ($health -eq "healthy") {
                Write-Host "Instance $instanceId`:$port - $health" -ForegroundColor Green
            } else {
                Write-Host "Instance $instanceId`:$port - $health ($reason)" -ForegroundColor Red
            }
        }
    }
} catch {
    Write-Host "Failed to check target health: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# Check Auto Scaling Group
Write-Host "Checking Auto Scaling Group..." -ForegroundColor Cyan
Write-Host "-----------------------------" -ForegroundColor Cyan

try {
    $asgName = "cloudfront-jwt-security-asg"  # Default ASG name
    $asgInfo = aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names $asgName --region $REGION --output json | ConvertFrom-Json
    
    if ($asgInfo.AutoScalingGroups.Count -gt 0) {
        $asg = $asgInfo.AutoScalingGroups[0]
        Write-Host "ASG Name: $($asg.AutoScalingGroupName)" -ForegroundColor Green
        Write-Host "Desired Capacity: $($asg.DesiredCapacity)" -ForegroundColor Green
        Write-Host "Current Instances: $($asg.Instances.Count)" -ForegroundColor Green
        
        foreach ($instance in $asg.Instances) {
            $instanceId = $instance.InstanceId
            $lifecycleState = $instance.LifecycleState
            $healthStatus = $instance.HealthStatus
            
            if ($lifecycleState -eq "InService" -and $healthStatus -eq "Healthy") {
                Write-Host "Instance $instanceId - $lifecycleState/$healthStatus" -ForegroundColor Green
            } else {
                Write-Host "Instance $instanceId - $lifecycleState/$healthStatus" -ForegroundColor Yellow
            }
        }
    } else {
        Write-Host "Auto Scaling Group not found!" -ForegroundColor Red
    }
} catch {
    Write-Host "Failed to check ASG: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# Security Group Check
Write-Host "Checking Security Groups..." -ForegroundColor Cyan
Write-Host "--------------------------" -ForegroundColor Cyan

try {
    $ALB_SG_ID = pulumi stack output alb_security_group_id
    $EC2_SG_ID = pulumi stack output ec2_security_group_id
    
    Write-Host "ALB Security Group: $ALB_SG_ID" -ForegroundColor Green
    Write-Host "EC2 Security Group: $EC2_SG_ID" -ForegroundColor Green
    
    # Check ALB security group rules
    $albSgRules = aws ec2 describe-security-groups --group-ids $ALB_SG_ID --region $REGION --output json | ConvertFrom-Json
    Write-Host "ALB SG Ingress Rules:" -ForegroundColor Yellow
    foreach ($rule in $albSgRules.SecurityGroups[0].IpPermissions) {
        Write-Host "  Port $($rule.FromPort)-$($rule.ToPort) from $($rule.IpRanges[0].CidrIp)" -ForegroundColor White
    }
    
    # Check EC2 security group rules
    $ec2SgRules = aws ec2 describe-security-groups --group-ids $EC2_SG_ID --region $REGION --output json | ConvertFrom-Json
    Write-Host "EC2 SG Ingress Rules:" -ForegroundColor Yellow
    foreach ($rule in $ec2SgRules.SecurityGroups[0].IpPermissions) {
        if ($rule.UserIdGroupPairs.Count -gt 0) {
            Write-Host "  Port $($rule.FromPort)-$($rule.ToPort) from SG $($rule.UserIdGroupPairs[0].GroupId)" -ForegroundColor White
        }
    }
    
} catch {
    Write-Host "Failed to check security groups: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# Check NAT Gateway
Write-Host "Checking NAT Gateway..." -ForegroundColor Cyan
Write-Host "---------------------" -ForegroundColor Cyan

try {
    $natInfo = aws ec2 describe-nat-gateways --nat-gateway-ids $NAT_GATEWAY_ID --region $REGION --output json | ConvertFrom-Json
    
    if ($natInfo.NatGateways.Count -gt 0) {
        $nat = $natInfo.NatGateways[0]
        $state = $nat.State
        $subnetId = $nat.SubnetId
        
        if ($state -eq "available") {
            Write-Host "NAT Gateway State: $state" -ForegroundColor Green
            Write-Host "NAT Gateway Subnet: $subnetId" -ForegroundColor Green
            Write-Host "NAT Gateway EIP: $($nat.NatGatewayAddresses[0].PublicIp)" -ForegroundColor Green
        } else {
            Write-Host "NAT Gateway State: $state" -ForegroundColor Yellow
        }
    } else {
        Write-Host "NAT Gateway not found!" -ForegroundColor Red
    }
} catch {
    Write-Host "Failed to check NAT Gateway: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# Recommendations
Write-Host "Troubleshooting Recommendations:" -ForegroundColor Cyan
Write-Host "===============================" -ForegroundColor Cyan

Write-Host "1. If targets are unhealthy:" -ForegroundColor Yellow
Write-Host "   - Check if EC2 instances are running Apache on port 80" -ForegroundColor White
Write-Host "   - Verify security group allows ALB to reach EC2 on port 80" -ForegroundColor White
Write-Host "   - Check if user data script completed successfully" -ForegroundColor White
Write-Host "   - Verify NAT Gateway is available for internet access" -ForegroundColor White
Write-Host "   - Check /health endpoint: curl http://instance-ip/health" -ForegroundColor White

Write-Host ""
Write-Host "2. If no targets are registered:" -ForegroundColor Yellow
Write-Host "   - Verify Auto Scaling Group is attached to target group" -ForegroundColor White
Write-Host "   - Check if instances are launching in correct subnets" -ForegroundColor White

Write-Host ""
Write-Host "3. If ALB returns 502 errors:" -ForegroundColor Yellow
Write-Host "   - All targets are unhealthy or no targets registered" -ForegroundColor White
Write-Host "   - Check target group health check settings" -ForegroundColor White

Write-Host ""
Write-Host "4. To check instance logs:" -ForegroundColor Yellow
Write-Host "   aws logs describe-log-groups --region $REGION" -ForegroundColor White
Write-Host "   aws ssm start-session --target <instance-id> --region $REGION" -ForegroundColor White

Write-Host ""
Write-Host "Troubleshooting complete!" -ForegroundColor Green