#!/bin/bash

# Git Repository Setup Script for CDN-Headers-Proj
set -e

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "❌ .env file not found. Please create it with your Git credentials."
    exit 1
fi

# Repository configuration
REPO_NAME="CDN-Headers-Proj"
REPO_DESCRIPTION="AWS CDN Headers Project with CloudFront, ALB, JWT validation and secrets rotation using Pulumi"

echo "🚀 Setting up Git repository for CDN-Headers-Proj"
echo "Repository: $REPO_NAME"
echo "Username: $GIT_USERNAME"
echo "Branch: $DEFAULT_BRANCH"

# Initialize git repository if not already initialized
if [ ! -d .git ]; then
    echo "📦 Initializing Git repository..."
    git init
    git branch -M $DEFAULT_BRANCH
else
    echo "📦 Git repository already initialized"
fi

# Configure git user (local to this repo)
echo "👤 Configuring Git user..."
git config user.name "$GIT_USERNAME"
git config user.email "$GIT_USERNAME@users.noreply.github.com"

# Add all files
echo "📁 Adding files to Git..."
git add .

# Create initial commit
echo "💾 Creating initial commit..."
if git diff --staged --quiet; then
    echo "ℹ️ No changes to commit"
else
    git commit -m "Initial commit: CDN Headers Project with Pulumi infrastructure

Features:
- CloudFront distribution with custom functions
- Application Load Balancer with JWT validation
- ECS Fargate service with FastAPI application
- AWS Secrets Manager with automatic rotation
- Lambda functions for request processing
- Complete monitoring and logging setup
- Interactive web interface for testing

All resources prefixed with qp-iac- as requested."
fi

# Create GitHub repository using GitHub CLI if available
if command -v gh &> /dev/null; then
    echo "🐙 Creating GitHub repository using GitHub CLI..."
    
    # Login with token
    echo "$GIT_TOKEN" | gh auth login --with-token
    
    # Create repository
    gh repo create "$REPO_NAME" --public --description "$REPO_DESCRIPTION" --source=. --remote=origin --push
    
    echo "✅ Repository created and pushed using GitHub CLI!"
    
else
    echo "🐙 GitHub CLI not found. Creating repository manually..."
    
    # Create repository using GitHub API
    echo "📡 Creating GitHub repository via API..."
    
    REPO_PAYLOAD=$(cat <<EOF
{
    "name": "$REPO_NAME",
    "description": "$REPO_DESCRIPTION",
    "private": false,
    "auto_init": false,
    "gitignore_template": "Python",
    "license_template": "mit"
}
EOF
)

    # Create repository
    RESPONSE=$(curl -s -H "Authorization: token $GIT_TOKEN" \
        -H "Accept: application/vnd.github.v3+json" \
        -d "$REPO_PAYLOAD" \
        "https://api.github.com/user/repos")
    
    # Check if repository was created successfully
    if echo "$RESPONSE" | grep -q '"clone_url"'; then
        echo "✅ Repository created successfully!"
        
        # Extract clone URL
        CLONE_URL=$(echo "$RESPONSE" | grep '"clone_url"' | sed 's/.*"clone_url": "\([^"]*\)".*/\1/')
        
        # Add remote origin
        echo "🔗 Adding remote origin..."
        git remote add origin "$CLONE_URL"
        
        # Push to GitHub
        echo "⬆️ Pushing to GitHub..."
        git push -u origin $DEFAULT_BRANCH
        
        echo "✅ Code pushed to GitHub successfully!"
        
    else
        echo "❌ Failed to create repository. Response:"
        echo "$RESPONSE"
        
        # Try to add remote manually if repository might already exist
        echo "🔄 Attempting to add remote manually..."
        MANUAL_URL="https://github.com/$GIT_USERNAME/$REPO_NAME.git"
        
        if git remote get-url origin &>/dev/null; then
            echo "ℹ️ Remote origin already exists"
        else
            git remote add origin "$MANUAL_URL"
        fi
        
        echo "⬆️ Attempting to push..."
        git push -u origin $DEFAULT_BRANCH
    fi
fi

# Display repository information
echo ""
echo "🎉 Git repository setup completed!"
echo "📍 Repository URL: https://github.com/$GIT_USERNAME/$REPO_NAME"
echo "🌿 Branch: $DEFAULT_BRANCH"
echo ""
echo "🔗 Quick links:"
echo "   - Repository: https://github.com/$GIT_USERNAME/$REPO_NAME"
echo "   - Clone URL: https://github.com/$GIT_USERNAME/$REPO_NAME.git"
echo "   - Issues: https://github.com/$GIT_USERNAME/$REPO_NAME/issues"
echo "   - Actions: https://github.com/$GIT_USERNAME/$REPO_NAME/actions"
echo ""
echo "📋 Next steps:"
echo "1. Visit your repository on GitHub"
echo "2. Add repository topics/tags for better discoverability"
echo "3. Set up branch protection rules if needed"
echo "4. Configure GitHub Actions for CI/CD (optional)"
echo "5. Add collaborators if working in a team"