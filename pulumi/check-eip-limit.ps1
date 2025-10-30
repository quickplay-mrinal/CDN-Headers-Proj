# Script to check Elastic IP usage and provide solutions

Write-Host "Elastic IP Limit Check" -ForegroundColor Cyan
Write-Host "======================" -ForegroundColor Cyan

# Get current region
try {
    $REGION = pulumi stack output region 2>$null
    if (-not $REGION) {
        $REGION = "ap-south-2"  # Default region
    }
} catch {
    $REGION = "ap-south-2"  # Default region
}

Write-Host "Checking EIP usage in region: $REGION" -ForegroundColor Yellow
Write-Host ""

# Check current EIP usage
try {
    Write-Host "Current Elastic IP Addresses:" -ForegroundColor Cyan
    $eips = aws ec2 describe-addresses --region $REGION --output json | ConvertFrom-Json
    
    if ($eips.Addresses.Count -eq 0) {
        Write-Host "No Elastic IP addresses found" -ForegroundColor Green
    } else {
        Write-Host "Found $($eips.Addresses.Count) Elastic IP addresses:" -ForegroundColor Yellow
        
        foreach ($eip in $eips.Addresses) {
            $publicIp = $eip.PublicIp
            $allocationId = $eip.AllocationId
            $instanceId = if ($eip.InstanceId) { $eip.InstanceId } else { "Not attached" }
            $associationId = if ($eip.AssociationId) { $eip.AssociationId } else { "Not associated" }
            
            Write-Host "  IP: $publicIp (Allocation: $allocationId)" -ForegroundColor White
            Write-Host "    Instance: $instanceId" -ForegroundColor Gray
            Write-Host "    Association: $associationId" -ForegroundColor Gray
            Write-Host ""
        }
    }
    
    # Check EIP limit
    Write-Host "Checking EIP service limits..." -ForegroundColor Cyan
    try {
        $limits = aws service-quotas get-service-quota --service-code ec2 --quota-code L-0263D0A3 --region $REGION --output json 2>$null | ConvertFrom-Json
        if ($limits) {
            $limit = $limits.Quota.Value
            $used = $eips.Addresses.Count
            Write-Host "EIP Limit: $used/$limit used" -ForegroundColor $(if ($used -ge $limit) { "Red" } else { "Green" })
        } else {
            Write-Host "Default EIP limit: 5 per region" -ForegroundColor Yellow
            Write-Host "Current usage: $($eips.Addresses.Count)/5" -ForegroundColor $(if ($eips.Addresses.Count -ge 5) { "Red" } else { "Green" })
        }
    } catch {
        Write-Host "Default EIP limit: 5 per region" -ForegroundColor Yellow
        Write-Host "Current usage: $($eips.Addresses.Count)/5" -ForegroundColor $(if ($eips.Addresses.Count -ge 5) { "Red" } else { "Green" })
    }
    
} catch {
    Write-Host "Failed to check EIP usage: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "Solutions for EIP Limit Issues:" -ForegroundColor Cyan
Write-Host "==============================" -ForegroundColor Cyan

Write-Host ""
Write-Host "Option 1: Release Unused EIPs" -ForegroundColor Yellow
Write-Host "------------------------------" -ForegroundColor Yellow
Write-Host "Check for unattached EIPs and release them:" -ForegroundColor White
Write-Host "  aws ec2 describe-addresses --region $REGION --query 'Addresses[?AssociationId==null]'" -ForegroundColor Gray
Write-Host "  aws ec2 release-address --allocation-id <allocation-id> --region $REGION" -ForegroundColor Gray

Write-Host ""
Write-Host "Option 2: Use Simplified Architecture (Recommended)" -ForegroundColor Green
Write-Host "---------------------------------------------------" -ForegroundColor Green
Write-Host "Deploy without NAT Gateway using public subnets:" -ForegroundColor White
Write-Host "  1. Copy __main___simple.py to __main__.py" -ForegroundColor Gray
Write-Host "  2. This avoids NAT Gateway and EIP requirements" -ForegroundColor Gray
Write-Host "  3. EC2 instances will be in public subnets with direct internet access" -ForegroundColor Gray
Write-Host "  4. Still secure with proper security groups" -ForegroundColor Gray

Write-Host ""
Write-Host "Option 3: Request EIP Limit Increase" -ForegroundColor Yellow
Write-Host "------------------------------------" -ForegroundColor Yellow
Write-Host "Request limit increase through AWS Support:" -ForegroundColor White
Write-Host "  1. Go to AWS Support Center" -ForegroundColor Gray
Write-Host "  2. Create case for 'Service limit increase'" -ForegroundColor Gray
Write-Host "  3. Select 'EC2 Elastic IPs'" -ForegroundColor Gray
Write-Host "  4. Request increase to 10-20 EIPs" -ForegroundColor Gray

Write-Host ""
Write-Host "Option 4: Use Different Region" -ForegroundColor Yellow
Write-Host "-----------------------------" -ForegroundColor Yellow
Write-Host "Deploy in a different region with available EIPs:" -ForegroundColor White
Write-Host "  .\deploy.ps1 -Region us-east-1" -ForegroundColor Gray
Write-Host "  .\deploy.ps1 -Region us-west-2" -ForegroundColor Gray

Write-Host ""
Write-Host "Recommended Action:" -ForegroundColor Green
Write-Host "==================" -ForegroundColor Green
Write-Host "Use Option 2 (Simplified Architecture) for this demo:" -ForegroundColor White
Write-Host ""
Write-Host "  # Switch to simplified version" -ForegroundColor Gray
Write-Host "  Copy-Item __main___simple.py __main__.py" -ForegroundColor Gray
Write-Host "  pulumi up" -ForegroundColor Gray
Write-Host ""
Write-Host "This provides the same JWT security functionality without NAT Gateway costs or EIP limits." -ForegroundColor Green