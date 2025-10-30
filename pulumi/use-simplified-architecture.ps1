# Script to switch to simplified architecture (public subnets)

Write-Host "Switching to Simplified Architecture" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan

Write-Host "SIMPLIFIED ARCHITECTURE BENEFITS:" -ForegroundColor Green
Write-Host "• Uses public subnets for both ALB and EC2" -ForegroundColor White
Write-Host "• No NAT Gateway required (saves ~$45/month)" -ForegroundColor White
Write-Host "• No Elastic IP limits" -ForegroundColor White
Write-Host "• Direct internet access for EC2 instances" -ForegroundColor White
Write-Host "• Same security through security groups" -ForegroundColor White
Write-Host "• Same JWT validation functionality" -ForegroundColor White
Write-Host ""

# Check if files exist
if (-not (Test-Path "__main___simple.py")) {
    Write-Host "Error: __main___simple.py not found!" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path "modules/vpc_simple.py")) {
    Write-Host "Error: modules/vpc_simple.py not found!" -ForegroundColor Red
    exit 1
}

# Backup current main file if it exists
if (Test-Path "__main__.py") {
    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    Copy-Item "__main__.py" "__main___backup_$timestamp.py" -Force
    Write-Host "Backed up current __main__.py to __main___backup_$timestamp.py" -ForegroundColor Blue
}

# Switch to simplified architecture
try {
    Copy-Item "__main___simple.py" "__main__.py" -Force
    Write-Host "✓ Switched to simplified architecture" -ForegroundColor Green
    
    # Verify the switch
    $content = Get-Content "__main__.py" -Raw
    if ($content -match "create_simple_vpc") {
        Write-Host "✓ Verified: Using simplified VPC module" -ForegroundColor Green
    } else {
        Write-Host "✗ Warning: Main file may not be using simplified VPC" -ForegroundColor Yellow
    }
    
    if ($content -match "public subnets") {
        Write-Host "✓ Verified: Using public subnets for EC2" -ForegroundColor Green
    } else {
        Write-Host "✗ Warning: Main file may not be using public subnets" -ForegroundColor Yellow
    }
    
} catch {
    Write-Host "✗ Failed to switch architecture: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "ARCHITECTURE SUMMARY:" -ForegroundColor Cyan
Write-Host "====================" -ForegroundColor Cyan

Write-Host "VPC Configuration:" -ForegroundColor Yellow
Write-Host "• Public subnets: ALB + EC2 instances" -ForegroundColor White
Write-Host "• Private subnets: Created but unused (for future)" -ForegroundColor White
Write-Host "• Internet Gateway: Direct access for public subnets" -ForegroundColor White
Write-Host "• NAT Gateway: Not created (cost savings)" -ForegroundColor White

Write-Host ""
Write-Host "Security Configuration:" -ForegroundColor Yellow
Write-Host "• ALB Security Group: HTTP/HTTPS from internet" -ForegroundColor White
Write-Host "• EC2 Security Group: HTTP only from ALB" -ForegroundColor White
Write-Host "• CloudFront Function: JWT validation at edge" -ForegroundColor White
Write-Host "• No direct EC2 access: All traffic via ALB" -ForegroundColor White

Write-Host ""
Write-Host "Cost Comparison:" -ForegroundColor Yellow
Write-Host "• NAT Gateway Architecture: ~$77/month" -ForegroundColor Red
Write-Host "• Simplified Architecture: ~$32/month" -ForegroundColor Green
Write-Host "• Monthly Savings: ~$45 (58% reduction)" -ForegroundColor Green

Write-Host ""
Write-Host "READY TO DEPLOY:" -ForegroundColor Green
Write-Host "================" -ForegroundColor Green

Write-Host "Deploy with simplified architecture:" -ForegroundColor White
Write-Host "  .\deploy-simple.ps1" -ForegroundColor Gray
Write-Host ""
Write-Host "Or use standard Pulumi commands:" -ForegroundColor White
Write-Host "  pulumi up" -ForegroundColor Gray

Write-Host ""
Write-Host "Architecture switch complete!" -ForegroundColor Green