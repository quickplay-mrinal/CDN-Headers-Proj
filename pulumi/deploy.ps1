# PowerShell deployment script for CloudFront Function + JWT Security

param(
    [string]$StackName = "dev",
    [string]$Region = "ap-south-2"
)

Write-Host "🚀 CloudFront Function + JWT Security - Deployment Script" -ForegroundColor Cyan
Write-Host "=========================================================" -ForegroundColor Cyan

# Check prerequisites
Write-Host "🔍 Checking prerequisites..." -ForegroundColor Yellow

# Check if Pulumi is installed
try {
    $pulumiVersion = pulumi version
    Write-Host "✅ Pulumi installed: $pulumiVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Pulumi not found. Please install Pulumi CLI first." -ForegroundColor Red
    Write-Host "   Visit: https://www.pulumi.com/docs/get-started/install/" -ForegroundColor Yellow
    exit 1
}

# Check if AWS CLI is configured
try {
    $awsIdentity = aws sts get-caller-identity --output text --query 'Account' 2>$null
    if ($awsIdentity) {
        Write-Host "✅ AWS CLI configured for account: $awsIdentity" -ForegroundColor Green
    } else {
        throw "AWS not configured"
    }
} catch {
    Write-Host "❌ AWS CLI not configured. Please run 'aws configure' first." -ForegroundColor Red
    exit 1
}

# Check if Python is installed
try {
    $pythonVersion = python --version 2>$null
    Write-Host "✅ Python installed: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python not found. Please install Python 3.7+ first." -ForegroundColor Red
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
Write-Host "🏗️ Setting up Pulumi stack: $StackName" -ForegroundColor Yellow
try {
    # Try to select existing stack first
    pulumi stack select $StackName 2>$null
    Write-Host "✅ Selected existing stack: $StackName" -ForegroundColor Green
} catch {
    # Create new stack if it doesn't exist
    try {
        pulumi stack init $StackName
        Write-Host "✅ Created new stack: $StackName" -ForegroundColor Green
    } catch {
        Write-Host "❌ Failed to create stack: $StackName" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""

# Configure stack
Write-Host "⚙️ Configuring stack..." -ForegroundColor Yellow

# Set AWS region
pulumi config set aws:region $Region
pulumi config set aws_region $Region
Write-Host "✅ Set AWS region: $Region" -ForegroundColor Green
Write-Host "ℹ️ All resources will be deployed in $Region (except CloudFront which is global)" -ForegroundColor Blue

Write-Host ""

# Deploy infrastructure
Write-Host "🚀 Deploying infrastructure..." -ForegroundColor Yellow
Write-Host "This may take 10-15 minutes for the first deployment..." -ForegroundColor Blue
Write-Host ""

try {
    pulumi up --yes
    Write-Host ""
    Write-Host "✅ Deployment completed successfully!" -ForegroundColor Green
} catch {
    Write-Host ""
    Write-Host "❌ Deployment failed!" -ForegroundColor Red
    Write-Host "Check the error messages above for details." -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Display outputs
Write-Host "📋 Deployment Information" -ForegroundColor Cyan
Write-Host "=========================" -ForegroundColor Cyan

$outputs = pulumi stack output --json | ConvertFrom-Json

Write-Host "🌐 ALB DNS Name: $($outputs.alb_dns_name)" -ForegroundColor Yellow
Write-Host "🌐 CloudFront Domain: $($outputs.cloudfront_domain_name)" -ForegroundColor Yellow
Write-Host "🔧 CloudFront Function: $($outputs.cloudfront_function_name)" -ForegroundColor Yellow

Write-Host ""

# Display test URLs
Write-Host "🧪 Test URLs and Commands" -ForegroundColor Cyan
Write-Host "=========================" -ForegroundColor Cyan

Write-Host "Direct ALB Access (Insecure):" -ForegroundColor Red
Write-Host "  http://$($outputs.alb_dns_name)" -ForegroundColor White
Write-Host "  ⚠️  This bypasses JWT validation - should be private in production" -ForegroundColor Yellow

Write-Host ""
Write-Host "CloudFront + JWT (Secure):" -ForegroundColor Green
Write-Host "  Without JWT (should fail): https://$($outputs.cloudfront_domain_name)" -ForegroundColor White
Write-Host "  With JWT (PowerShell):" -ForegroundColor White
Write-Host "    `$jwt = '$($outputs.sample_jwt_token)'" -ForegroundColor Gray
Write-Host "    `$headers = @{'Authorization' = 'Bearer ' + `$jwt}" -ForegroundColor Gray
Write-Host "    Invoke-WebRequest -Uri 'https://$($outputs.cloudfront_domain_name)' -Headers `$headers" -ForegroundColor Gray

Write-Host ""

# Offer to run tests
Write-Host "🧪 Ready to test JWT security!" -ForegroundColor Cyan
$runTests = Read-Host "Would you like to run the test script now? (y/N)"

if ($runTests -eq 'y' -or $runTests -eq 'Y') {
    Write-Host ""
    Write-Host "🧪 Running JWT security tests..." -ForegroundColor Yellow
    & ".\scripts\test-approaches.ps1"
} else {
    Write-Host ""
    Write-Host "ℹ️ You can run tests later with: .\scripts\test-approaches.ps1" -ForegroundColor Blue
}

Write-Host ""
Write-Host "🎉 Deployment complete! Your secure CDN with JWT validation is ready." -ForegroundColor Green
Write-Host ""
Write-Host "📚 Next steps:" -ForegroundColor Cyan
Write-Host "  1. Test JWT validation using the URLs above" -ForegroundColor White
Write-Host "  2. Review CloudFront function logs in AWS console" -ForegroundColor White
Write-Host "  3. Run: .\scripts\test-approaches.ps1 for automated testing" -ForegroundColor White
Write-Host "  4. Consider making ALB private for production security" -ForegroundColor White
Write-Host "  5. Clean up when done: pulumi destroy" -ForegroundColor White