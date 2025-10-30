# Deployment Status Monitor for CloudFront JWT Security Infrastructure

param(
    [switch]$Watch = $false,
    [int]$RefreshInterval = 30
)

Write-Host "CloudFront JWT Security - Deployment Status Monitor" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan

function Get-DeploymentStatus {
    Write-Host "$(Get-Date -Format 'HH:mm:ss') - Checking deployment status..." -ForegroundColor Yellow
    
    try {
        # Get basic stack info
        $stackInfo = pulumi stack --show-urns 2>$null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Stack not found or not deployed" -ForegroundColor Red
            return $false
        }
        
        # Get stack outputs
        $outputs = @{}
        try {
            $outputJson = pulumi stack output --json 2>$null | ConvertFrom-Json
            $outputs = $outputJson
        } catch {
            Write-Host "No outputs available yet" -ForegroundColor Yellow
            return $false
        }
        
        Write-Host ""
        Write-Host "Infrastructure Status:" -ForegroundColor Green
        Write-Host "--------------------" -ForegroundColor Green
        
        # VPC Status
        if ($outputs.vpc_id) {
            Write-Host "VPC: $($outputs.vpc_id)" -ForegroundColor Green
        } else {
            Write-Host "VPC: Not created" -ForegroundColor Red
        }
        
        # NAT Gateway Status
        if ($outputs.nat_gateway_id) {
            Write-Host "NAT Gateway: $($outputs.nat_gateway_id)" -ForegroundColor Green
            if ($outputs.nat_eip) {
                Write-Host "NAT EIP: $($outputs.nat_eip)" -ForegroundColor Green
            }
        } else {
            Write-Host "NAT Gateway: Not created" -ForegroundColor Red
        }
        
        # ALB Status
        if ($outputs.alb_dns_name) {
            Write-Host "ALB: $($outputs.alb_dns_name)" -ForegroundColor Green
            
            # Test ALB health
            try {
                $response = Invoke-WebRequest -Uri "http://$($outputs.alb_dns_name)/health" -UseBasicParsing -TimeoutSec 5 -ErrorAction SilentlyContinue
                Write-Host "ALB Health: OK ($($response.StatusCode))" -ForegroundColor Green
            } catch {
                Write-Host "ALB Health: Not ready (targets may be unhealthy)" -ForegroundColor Yellow
            }
        } else {
            Write-Host "ALB: Not created" -ForegroundColor Red
        }
        
        # CloudFront Status
        if ($outputs.cloudfront_domain_name) {
            Write-Host "CloudFront: $($outputs.cloudfront_domain_name)" -ForegroundColor Green
        } else {
            Write-Host "CloudFront: Not created" -ForegroundColor Red
        }
        
        # Target Group Health
        if ($outputs.target_group_arn -and $outputs.region) {
            try {
                $targetHealth = aws elbv2 describe-target-health --target-group-arn $outputs.target_group_arn --region $outputs.region --output json 2>$null | ConvertFrom-Json
                
                if ($targetHealth.TargetHealthDescriptions.Count -eq 0) {
                    Write-Host "Targets: No targets registered" -ForegroundColor Yellow
                } else {
                    $healthyCount = ($targetHealth.TargetHealthDescriptions | Where-Object { $_.TargetHealth.State -eq "healthy" }).Count
                    $totalCount = $targetHealth.TargetHealthDescriptions.Count
                    
                    if ($healthyCount -eq $totalCount -and $totalCount -gt 0) {
                        Write-Host "Targets: $healthyCount/$totalCount healthy" -ForegroundColor Green
                    } elseif ($healthyCount -gt 0) {
                        Write-Host "Targets: $healthyCount/$totalCount healthy (some still starting)" -ForegroundColor Yellow
                    } else {
                        Write-Host "Targets: $healthyCount/$totalCount healthy (all unhealthy)" -ForegroundColor Red
                    }
                }
            } catch {
                Write-Host "Targets: Unable to check health" -ForegroundColor Yellow
            }
        }
        
        Write-Host ""
        
        # Deployment readiness check
        $isReady = $outputs.alb_dns_name -and $outputs.cloudfront_domain_name
        
        if ($isReady) {
            Write-Host "Deployment Status: READY" -ForegroundColor Green
            Write-Host ""
            Write-Host "Test URLs:" -ForegroundColor Cyan
            Write-Host "  ALB Health: http://$($outputs.alb_dns_name)/health" -ForegroundColor White
            Write-Host "  ALB Direct: http://$($outputs.alb_dns_name)" -ForegroundColor White
            Write-Host "  CloudFront: https://$($outputs.cloudfront_domain_name)" -ForegroundColor White
            
            if ($outputs.sample_jwt_token) {
                Write-Host ""
                Write-Host "Test with JWT:" -ForegroundColor Cyan
                Write-Host "  curl -H 'Authorization: Bearer $($outputs.sample_jwt_token)' https://$($outputs.cloudfront_domain_name)" -ForegroundColor White
            }
        } else {
            Write-Host "Deployment Status: IN PROGRESS" -ForegroundColor Yellow
        }
        
        return $isReady
        
    } catch {
        Write-Host "Error checking deployment status: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Main execution
if ($Watch) {
    Write-Host "Watching deployment status (refresh every $RefreshInterval seconds)..." -ForegroundColor Blue
    Write-Host "Press Ctrl+C to stop watching" -ForegroundColor Blue
    Write-Host ""
    
    do {
        $isReady = Get-DeploymentStatus
        
        if ($isReady) {
            Write-Host ""
            Write-Host "Deployment is ready! Stopping watch mode." -ForegroundColor Green
            break
        }
        
        Write-Host ""
        Write-Host "Waiting $RefreshInterval seconds before next check..." -ForegroundColor Blue
        Start-Sleep -Seconds $RefreshInterval
        Clear-Host
        Write-Host "CloudFront JWT Security - Deployment Status Monitor" -ForegroundColor Cyan
        Write-Host "===================================================" -ForegroundColor Cyan
        
    } while ($true)
} else {
    Get-DeploymentStatus | Out-Null
}

Write-Host ""
Write-Host "Status check complete!" -ForegroundColor Green