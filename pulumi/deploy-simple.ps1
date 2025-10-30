# Simplified deployment script that avoids NAT Gateway and EIP limits

param(
    [string]$StackName = "dev",
    [string]$Region = "ap-south-2"
)

Write-Host "CloudFront Function + JWT Security - Simplified Deployment" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "ARCHITECTURE: Public subnets for ALB and EC2 instances" -ForegroundColor Green
Write-Host "BENEFITS: No NAT Gateway, No EIP limits, Lower cost (~$32/month)" -ForegroundColor Green
Write-Host "SECURITY: Maintained through security groups and CloudFront JWT" -ForegroundColor Green
Write-Host ""

# Check prerequisites
Write-Host "Checking prerequisites..." -ForegroundColor Yellow

# Check if Pulumi is installed
try {
    $pulumiVersion = pulumi version
    Write-Host "Pulumi installed: $pulumiVersion" -ForegroundColor Green
} catch {
    Write-Host "Pulumi not found. Please install Pulumi CLI first." -ForegroundColor Red
    Write-Host "   Visit: https://www.pulumi.com/docs/get-started/install/" -ForegroundColor Yellow
    exit 1
}

# Check if AWS CLI is configured
try {
    $awsIdentity = aws sts get-caller-identity --output text --query 'Account' 2>$null
    if ($awsIdentity) {
        Write-Host "AWS CLI configured for account: $awsIdentity" -ForegroundColor Green
    } else {
        throw "AWS not configured"
    }
} catch {
    Write-Host "AWS CLI not configured. Please run 'aws configure' first." -ForegroundColor Red
    exit 1
}

Write-Host ""

# Switch to simplified architecture
Write-Host "Switching to simplified architecture..." -ForegroundColor Yellow
try {
    # Backup current main file if it exists
    if (Test-Path "__main__.py") {
        Copy-Item "__main__.py" "__main___backup.py" -Force
        Write-Host "Backed up current __main__.py to __main___backup.py" -ForegroundColor Blue
    }
    
    # Copy simplified version
    Copy-Item "__main___simple.py" "__main__.py" -Force
    Write-Host "Switched to simplified architecture (no NAT Gateway)" -ForegroundColor Green
} catch {
    Write-Host "Failed to switch architecture: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Install Python dependencies
Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
try {
    pip install -r requirements.txt --quiet
    Write-Host "Dependencies installed successfully" -ForegroundColor Green
} catch {
    Write-Host "Failed to install dependencies" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Validate modules
Write-Host "Validating infrastructure modules..." -ForegroundColor Yellow
try {
    $validationResult = python validate.py
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Module validation passed" -ForegroundColor Green
    } else {
        Write-Host "Module validation failed" -ForegroundColor Red
        Write-Host $validationResult -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Host "Failed to run validation" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Initialize or select Pulumi stack
Write-Host "Setting up Pulumi stack: $StackName" -ForegroundColor Yellow
try {
    # Try to select existing stack first
    pulumi stack select $StackName 2>$null
    Write-Host "Selected existing stack: $StackName" -ForegroundColor Green
} catch {
    # Create new stack if it doesn't exist
    try {
        pulumi stack init $StackName
        Write-Host "Created new stack: $StackName" -ForegroundColor Green
    } catch {
        Write-Host "Failed to create stack: $StackName" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""

# Configure stack
Write-Host "Configuring stack..." -ForegroundColor Yellow

# Set AWS region
pulumi config set aws:region $Region
pulumi config set aws_region $Region
Write-Host "Set AWS region: $Region" -ForegroundColor Green
Write-Host "All resources will be deployed in $Region (except CloudFront which is global)" -ForegroundColor Blue

Write-Host ""

# Deploy infrastructure
Write-Host "Deploying infrastructure..." -ForegroundColor Yellow
Write-Host "This may take 15-20 minutes for the first deployment..." -ForegroundColor Blue
Write-Host "Architecture: Simplified (public subnets, no NAT Gateway)" -ForegroundColor Blue
Write-Host ""

try {
    pulumi up --yes
    Write-Host ""
    Write-Host "Deployment completed successfully!" -ForegroundColor Green
} catch {
    Write-Host ""
    Write-Host "Deployment failed!" -ForegroundColor Red
    Write-Host "Check the error messages above for details." -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Display outputs
Write-Host "Deployment Information" -ForegroundColor Cyan
Write-Host "=====================" -ForegroundColor Cyan

$outputs = pulumi stack output --json | ConvertFrom-Json

Write-Host "ALB DNS Name: $($outputs.alb_dns_name)" -ForegroundColor Yellow
Write-Host "CloudFront Domain: $($outputs.cloudfront_domain_name)" -ForegroundColor Yellow
Write-Host "CloudFront Function: $($outputs.cloudfront_function_name)" -ForegroundColor Yellow
Write-Host "Architecture: $($outputs.architecture)" -ForegroundColor Yellow

Write-Host ""

# Display test URLs
Write-Host "Test URLs and Commands" -ForegroundColor Cyan
Write-Host "=====================" -ForegroundColor Cyan

Write-Host "ALB Health Check:" -ForegroundColor Green
Write-Host "  http://$($outputs.alb_dns_name)/health" -ForegroundColor White

Write-Host ""
Write-Host "CloudFront + JWT (Secure):" -ForegroundColor Green
Write-Host "  Without JWT (should fail): https://$($outputs.cloudfront_domain_name)" -ForegroundColor White
Write-Host "  With JWT (PowerShell):" -ForegroundColor White
Write-Host "    `$jwt = '$($outputs.sample_jwt_token)'" -ForegroundColor Gray
Write-Host "    `$headers = @{'Authorization' = 'Bearer ' + `$jwt}" -ForegroundColor Gray
Write-Host "    Invoke-WebRequest -Uri 'https://$($outputs.cloudfront_domain_name)' -Headers `$headers" -ForegroundColor Gray

Write-Host ""

# Offer to run tests
Write-Host "Ready to test JWT security!" -ForegroundColor Cyan
$runTests = Read-Host "Would you like to run the test script now? (y/N)"

if ($runTests -eq 'y' -or $runTests -eq 'Y') {
    Write-Host ""
    Write-Host "Running JWT security tests..." -ForegroundColor Yellow
    & ".\scripts\test-approaches.ps1"
} else {
    Write-Host ""
    Write-Host "You can run tests later with: .\scripts\test-approaches.ps1" -ForegroundColor Blue
}

Write-Host ""
Write-Host "Deployment complete! Your secure CDN with JWT validation is ready." -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Test JWT validation using the URLs above" -ForegroundColor White
Write-Host "  2. Review CloudFront function logs in AWS console" -ForegroundColor White
Write-Host "  3. Run: .\scripts\test-approaches.ps1 for automated testing" -ForegroundColor White
Write-Host "  4. Clean up when done: pulumi destroy" -ForegroundColor White
Write-Host ""
Write-Host "Note: This simplified architecture uses public subnets for cost savings" -ForegroundColor Blue
Write-Host "      and to avoid EIP limits. Security is maintained through security groups." -ForegroundColor Blue