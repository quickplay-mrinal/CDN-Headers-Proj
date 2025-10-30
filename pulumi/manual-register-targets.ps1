# Manual target registration script to fix 503 errors

Write-Host "Manual Target Registration - Fix 503 Errors" -ForegroundColor Cyan
Write-Host "===========================================" -ForegroundColor Cyan

# Get deployment info
try {
    $TARGET_GROUP_ARN = pulumi stack output target_group_arn
    $REGION = pulumi stack output region
    
    Write-Host "Target Group ARN: $TARGET_GROUP_ARN" -ForegroundColor Green
    Write-Host "Region: $REGION" -ForegroundColor Green
    Write-Host ""
} catch {
    Write-Host "Failed to get Pulumi outputs" -ForegroundColor Red
    exit 1
}

# Get instances from Auto Scaling Group
Write-Host "Finding instances in Auto Scaling Group..." -ForegroundColor Yellow

try {
    $asgName = "cloudfront-jwt-security-asg"
    $asgInfo = aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names $asgName --region $REGION --output json | ConvertFrom-Json
    
    if ($asgInfo.AutoScalingGroups.Count -eq 0) {
        Write-Host "Auto Scaling Group not found!" -ForegroundColor Red
        exit 1
    }
    
    $instances = $asgInfo.AutoScalingGroups[0].Instances
    
    if ($instances.Count -eq 0) {
        Write-Host "No instances found in Auto Scaling Group!" -ForegroundColor Red
        Write-Host "Try increasing desired capacity:" -ForegroundColor Yellow
        Write-Host "aws autoscaling update-auto-scaling-group --auto-scaling-group-name $asgName --desired-capacity 2 --region $REGION" -ForegroundColor Gray
        exit 1
    }
    
    Write-Host "Found $($instances.Count) instances:" -ForegroundColor Green
    
    foreach ($instance in $instances) {
        $instanceId = $instance.InstanceId
        $lifecycleState = $instance.LifecycleState
        $healthStatus = $instance.HealthStatus
        
        Write-Host "  $instanceId - $lifecycleState/$healthStatus" -ForegroundColor White
        
        if ($lifecycleState -eq "InService") {
            Write-Host "    Registering with target group..." -ForegroundColor Yellow
            
            try {
                aws elbv2 register-targets --target-group-arn $TARGET_GROUP_ARN --targets Id=$instanceId,Port=80 --region $REGION
                Write-Host "    ✓ Registered successfully" -ForegroundColor Green
            } catch {
                Write-Host "    ✗ Registration failed: $($_.Exception.Message)" -ForegroundColor Red
            }
        } else {
            Write-Host "    Skipping (not InService)" -ForegroundColor Yellow
        }
    }
    
} catch {
    Write-Host "Failed to get ASG instances: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Waiting for targets to become healthy..." -ForegroundColor Yellow
Write-Host "This may take 2-3 minutes..." -ForegroundColor Blue

# Wait and check target health
$maxWait = 180  # 3 minutes
$waited = 0
$interval = 10

do {
    Start-Sleep -Seconds $interval
    $waited += $interval
    
    try {
        $targetHealth = aws elbv2 describe-target-health --target-group-arn $TARGET_GROUP_ARN --region $REGION --output json | ConvertFrom-Json
        
        $healthyCount = ($targetHealth.TargetHealthDescriptions | Where-Object { $_.TargetHealth.State -eq "healthy" }).Count
        $totalCount = $targetHealth.TargetHealthDescriptions.Count
        
        Write-Host "Target Health: $healthyCount/$totalCount healthy (waited $waited seconds)" -ForegroundColor Yellow
        
        if ($healthyCount -gt 0) {
            Write-Host ""
            Write-Host "✓ Targets are becoming healthy!" -ForegroundColor Green
            break
        }
        
        if ($waited -ge $maxWait) {
            Write-Host ""
            Write-Host "Timeout waiting for healthy targets" -ForegroundColor Red
            break
        }
        
    } catch {
        Write-Host "Error checking target health: $($_.Exception.Message)" -ForegroundColor Red
    }
    
} while ($waited -lt $maxWait)

# Final test
Write-Host ""
Write-Host "Testing ALB after registration..." -ForegroundColor Cyan

try {
    $ALB_DNS = pulumi stack output alb_dns_name
    $response = Invoke-WebRequest -Uri "http://$ALB_DNS" -UseBasicParsing -TimeoutSec 10 -ErrorAction SilentlyContinue
    Write-Host "✓ ALB Response: $($response.StatusCode) - Success!" -ForegroundColor Green
    Write-Host ""
    Write-Host "503 error should be fixed!" -ForegroundColor Green
    Write-Host "Test URL: http://$ALB_DNS" -ForegroundColor White
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    Write-Host "✗ ALB still returning: $statusCode" -ForegroundColor Red
    
    if ($statusCode -eq 503) {
        Write-Host "503 error persists. Check instance health and security groups." -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Manual registration complete!" -ForegroundColor Green