#!/bin/bash

# QP-IAC CDN Headers Project Deployment Script

set -e

echo "🚀 Starting QP-IAC CDN Headers Project Deployment"

# Check if Pulumi is installed
if ! command -v pulumi &> /dev/null; then
    echo "❌ Pulumi is not installed. Please install Pulumi first."
    echo "Visit: https://www.pulumi.com/docs/get-started/install/"
    exit 1
fi

# Check if AWS CLI is configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS CLI is not configured. Please run 'aws configure' first."
    exit 1
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Initialize Pulumi stack if it doesn't exist
if ! pulumi stack ls | grep -q "dev"; then
    echo "🔧 Initializing Pulumi stack..."
    pulumi stack init dev
fi

# Set AWS region if not set
if ! pulumi config get aws:region &> /dev/null; then
    echo "🌍 Setting AWS region to us-east-1..."
    pulumi config set aws:region us-east-1
fi

# Preview the deployment
echo "👀 Previewing deployment..."
pulumi preview

# Ask for confirmation
read -p "Do you want to proceed with the deployment? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Deployment cancelled."
    exit 1
fi

# Deploy the stack
echo "🚀 Deploying infrastructure..."
pulumi up --yes

# Get stack outputs
echo "📋 Stack outputs:"
pulumi stack output

echo "✅ Deployment completed successfully!"
echo ""
echo "🌐 Access your application at:"
echo "CloudFront URL: https://$(pulumi stack output cloudfront_domain_name)"
echo ""
echo "🔧 Useful commands:"
echo "  - View logs: pulumi logs --follow"
echo "  - Update stack: pulumi up"
echo "  - Destroy stack: pulumi destroy"