# Script to diagnose and fix 503 Service Temporarily Unavailable errors

Write-Host "503 Error Troubleshooting - CloudFront JWT Security" -ForegroundColor Red
Write-Host "====================================================" -ForegroundColor Red

# Get Pulumi outputs
Write-Host "Getting deployment information..." -ForegroundColor Yellow

try {
    $ALB_DNS = pulumi stack output alb_dns_name
    $TARGET_GROUP_ARN = pulumi stack output target_group_arn
    $VPC_ID = pulumi stack output vpc_id
    $REGION = pulumi stack output region
    
    Write-Host "Region: $REGION" -ForegroundColor Green
    Write-Host "ALB DNS: $ALB_DNS" -ForegroundColor Green
    Write-Host "Target Group ARN: $TARGET_GROUP_ARN" -ForegroundColor Green
    Write-Host ""
    
} catch {
    Write-Host "Failed to get Pulumi outputs. Make sure the stack is deployed." -ForegroundColor Red
    exit 1
}

# Step 1: Check Target Group Registration
Write-Host "Step 1: Checking Target Group Registration" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan

try {
    $targetHealth = aws elbv2 describe-target-health --target-group-arn $TARGET_GROUP_ARN --region $REGION --output json | ConvertFrom-Json
    
    if ($targetHealth.TargetHealthDescriptions.Count -eq 0) {
        Write-Host "PROBLEM FOUND: No targets registered in target group!" -ForegroundColor Red
        Write-Host "This is the cause of the 503 error." -ForegroundColor Red
        Write-Host ""
        
        # Check Auto Scaling Group
        Write-Host "Checking Auto Scaling Group..." -ForegroundColor Yellow
        $asgName = "cloudfront-jwt-security-asg"
        $asgInfo = aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names $asgName --region $REGION --output json 2>$null | ConvertFrom-Json
        
        if ($asgInfo.AutoScalingGroups.Count -gt 0) {
            $asg = $asgInfo.AutoScalingGroups[0]
            Write-Host "ASG Found: $($asg.AutoScalingGroupName)" -ForegroundColor Green
            Write-Host "Desired Capacity: $($asg.DesiredCapacity)" -ForegroundColor Green
            Write-Host "Current Instances: $($asg.Instances.Count)" -ForegroundColor Green
            
            if ($asg.Instances.Count -eq 0) {
                Write-Host "PROBLEM: No instances in Auto Scaling Group!" -ForegroundColor Red
                Write-Host "SOLUTION: Check launch template and subnet configuration" -ForegroundColor Yellow
            } else {
                Write-Host "PROBLEM: Instances exist but not registered with target group!" -ForegroundColor Red
                Write-Host "SOLUTION: Check target group attachment" -ForegroundColor Yellow
                
                # Show instance details
                foreach ($instance in $asg.Instances) {
                    $instanceId = $instance.InstanceId
                    $lifecycleState = $instance.LifecycleState
                    $healthStatus = $instance.HealthStatus
                    
                    Write-Host "Instance $instanceId - $lifecycleState/$healthStatus" -ForegroundColor White
                }
            }
        } else {
            Write-Host "PROBLEM: Auto Scaling Group not found!" -ForegroundColor Red
        }
        
    } else {
        Write-Host "Targets found: $($targetHealth.TargetHealthDescriptions.Count)" -ForegroundColor Green
        
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

# Step 2: Test ALB Directly
Write-Host "Step 2: Testing ALB Response" -ForegroundColor Cyan
Write-Host "============================" -ForegroundColor Cyan

Write-Host "Testing ALB root path..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://$ALB_DNS" -UseBasicParsing -TimeoutSec 10 -ErrorAction SilentlyContinue
    Write-Host "ALB Response: $($response.StatusCode) - $($response.StatusDescription)" -ForegroundColor Green
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    Write-Host "ALB Error: $statusCode - $($_.Exception.Message)" -ForegroundColor Red
    
    if ($statusCode -eq 503) {
        Write-Host "CONFIRMED: 503 Service Temporarily Unavailable" -ForegroundColor Red
        Write-Host "This means no healthy targets are available." -ForegroundColor Red
    }
}

Write-Host ""

# Step 3: Check Instance Health
Write-Host "Step 3: Checking Instance Health" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

try {
    # Get instances from ASG
    $asgName = "cloudfront-jwt-security-asg"
    $asgInfo = aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names $asgName --region $REGION --output json 2>$null | ConvertFrom-Json
    
    if ($asgInfo.AutoScalingGroups.Count -gt 0) {
        $instances = $asgInfo.AutoScalingGroups[0].Instances
        
        foreach ($instance in $instances) {
            $instanceId = $instance.InstanceId
            Write-Host "Checking instance $instanceId..." -ForegroundColor Yellow
            
            # Get instance details
            $instanceInfo = aws ec2 describe-instances --instance-ids $instanceId --region $REGION --output json | ConvertFrom-Json
            $instanceDetail = $instanceInfo.Reservations[0].Instances[0]
            
            $state = $instanceDetail.State.Name
            $publicIp = $instanceDetail.PublicIpAddress
            $privateIp = $instanceDetail.PrivateIpAddress
            
            Write-Host "  State: $state" -ForegroundColor White
            Write-Host "  Public IP: $publicIp" -ForegroundColor White
            Write-Host "  Private IP: $privateIp" -ForegroundColor White
            
            if ($state -eq "running" -and $publicIp) {
                # Test instance directly
                Write-Host "  Testing instance directly..." -ForegroundColor Yellow
                try {
                    $instanceResponse = Invoke-WebRequest -Uri "http://$publicIp" -UseBasicParsing -TimeoutSec 5 -ErrorAction SilentlyContinue
                    Write-Host "  Instance Response: $($instanceResponse.StatusCode)" -ForegroundColor Green
                } catch {
                    Write-Host "  Instance Error: $($_.Exception.Message)" -ForegroundColor Red
                    Write-Host "  PROBLEM: Instance not responding on port 80" -ForegroundColor Red
                }
            }
        }
    }
} catch {
    Write-Host "Failed to check instances: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""

# Step 4: Solutions
Write-Host "Step 4: Solutions for 503 Error" -ForegroundColor Cyan
Write-Host "===============================" -ForegroundColor Cyan

Write-Host ""
Write-Host "IMMEDIATE FIXES:" -ForegroundColor Green
Write-Host "===============" -ForegroundColor Green

Write-Host "1. Manually register instances with target group:" -ForegroundColor Yellow
Write-Host "   # Get instance IDs from ASG" -ForegroundColor Gray
Write-Host "   aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names cloudfront-jwt-security-asg --region $REGION" -ForegroundColor Gray
Write-Host "   # Register instance manually" -ForegroundColor Gray
Write-Host "   aws elbv2 register-targets --target-group-arn $TARGET_GROUP_ARN --targets Id=<instance-id>,Port=80 --region $REGION" -ForegroundColor Gray

Write-Host ""
Write-Host "2. Restart Auto Scaling Group:" -ForegroundColor Yellow
Write-Host "   aws autoscaling update-auto-scaling-group --auto-scaling-group-name cloudfront-jwt-security-asg --desired-capacity 0 --region $REGION" -ForegroundColor Gray
Write-Host "   # Wait 30 seconds" -ForegroundColor Gray
Write-Host "   aws autoscaling update-auto-scaling-group --auto-scaling-group-name cloudfront-jwt-security-asg --desired-capacity 2 --region $REGION" -ForegroundColor Gray

Write-Host ""
Write-Host "3. Redeploy with fixed configuration:" -ForegroundColor Yellow
Write-Host "   pulumi up --refresh" -ForegroundColor Gray

Write-Host ""
Write-Host "ROOT CAUSE ANALYSIS:" -ForegroundColor Green
Write-Host "===================" -ForegroundColor Green

Write-Host "Common causes of 503 errors:" -ForegroundColor Yellow
Write-Host "• Auto Scaling Group not attached to target group" -ForegroundColor White
Write-Host "• Instances failing health checks" -ForegroundColor White
Write-Host "• Security groups blocking ALB → EC2 communication" -ForegroundColor White
Write-Host "• User data script failing to start Apache" -ForegroundColor White
Write-Host "• Wrong subnet configuration" -ForegroundColor White

Write-Host ""
Write-Host "PREVENTION:" -ForegroundColor Green
Write-Host "===========" -ForegroundColor Green

Write-Host "• Use separate ASG attachment resource" -ForegroundColor White
Write-Host "• Start with EC2 health checks, then switch to ELB" -ForegroundColor White
Write-Host "• Ensure security groups allow ALB → EC2 on port 80" -ForegroundColor White
Write-Host "• Test user data script independently" -ForegroundColor White
Write-Host "• Use public subnets for simplified architecture" -ForegroundColor White

Write-Host ""
Write-Host "Next step: Run the manual registration command above or redeploy." -ForegroundColor Green