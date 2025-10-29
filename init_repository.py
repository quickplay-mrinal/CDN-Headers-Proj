#!/usr/bin/env python3
"""
Repository initialization script for CDN-Headers-Proj
"""

import os
import sys
import subprocess
import json
import requests
from pathlib import Path

class GitRepositoryManager:
    def __init__(self):
        self.load_env_variables()
        self.repo_name = "CDN-Headers-Proj"
        self.repo_description = "AWS CDN Headers Project with CloudFront, ALB, JWT validation and secrets rotation using Pulumi"
        
    def load_env_variables(self):
        """Load environment variables from .env file"""
        env_file = Path('.env')
        if not env_file.exists():
            print("❌ .env file not found. Please create it with your Git credentials.")
            sys.exit(1)
            
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    os.environ[key] = value
        
        self.git_username = os.getenv('GIT_USERNAME')
        self.git_token = os.getenv('GIT_TOKEN')
        self.default_branch = os.getenv('DEFAULT_BRANCH', 'master')
        
        if not all([self.git_username, self.git_token]):
            print("❌ Missing required environment variables: GIT_USERNAME, GIT_TOKEN")
            sys.exit(1)
    
    def run_command(self, command, check=True, capture_output=False):
        """Run shell command"""
        try:
            if capture_output:
                result = subprocess.run(command, shell=True, check=check, 
                                      capture_output=True, text=True)
                return result.stdout.strip()
            else:
                subprocess.run(command, shell=True, check=check)
                return True
        except subprocess.CalledProcessError as e:
            if capture_output:
                print(f"❌ Command failed: {command}")
                print(f"Error: {e.stderr}")
            return False
    
    def initialize_git_repo(self):
        """Initialize Git repository"""
        print("📦 Initializing Git repository...")
        
        # Check if already initialized
        if Path('.git').exists():
            print("ℹ️ Git repository already initialized")
        else:
            self.run_command("git init")
            self.run_command(f"git branch -M {self.default_branch}")
        
        # Configure git user
        print("👤 Configuring Git user...")
        self.run_command(f'git config user.name "{self.git_username}"')
        self.run_command(f'git config user.email "{self.git_username}@users.noreply.github.com"')
        
        return True
    
    def create_github_repository(self):
        """Create GitHub repository using API"""
        print("🐙 Creating GitHub repository...")
        
        url = "https://api.github.com/user/repos"
        headers = {
            "Authorization": f"token {self.git_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        data = {
            "name": self.repo_name,
            "description": self.repo_description,
            "private": False,
            "auto_init": False,
            "gitignore_template": "Python",
            "license_template": "mit"
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 201:
                repo_data = response.json()
                print(f"✅ Repository created successfully!")
                print(f"📍 Repository URL: {repo_data['html_url']}")
                return repo_data['clone_url']
            elif response.status_code == 422:
                # Repository might already exist
                print("ℹ️ Repository might already exist, continuing...")
                return f"https://github.com/{self.git_username}/{self.repo_name}.git"
            else:
                print(f"❌ Failed to create repository: {response.status_code}")
                print(f"Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error creating repository: {e}")
            return None
    
    def add_and_commit_files(self):
        """Add and commit all files"""
        print("📁 Adding files to Git...")
        
        # Add all files
        self.run_command("git add .")
        
        # Check if there are changes to commit
        result = self.run_command("git diff --staged --quiet", check=False)
        if result:
            print("ℹ️ No changes to commit")
            return True
        
        # Create commit
        print("💾 Creating initial commit...")
        commit_message = """Initial commit: CDN Headers Project with Pulumi infrastructure

Features:
- CloudFront distribution with custom functions
- Application Load Balancer with JWT validation  
- ECS Fargate service with FastAPI application
- AWS Secrets Manager with automatic rotation
- Lambda functions for request processing
- Complete monitoring and logging setup
- Interactive web interface for testing

All resources prefixed with qp-iac- as requested.

Components:
- VPC with public/private subnets
- ALB with JWT validation
- ECS Fargate cluster and service
- CloudFront distribution with custom behaviors
- Lambda functions for CloudFront and rotation
- Secrets Manager with 30-day rotation
- CloudWatch monitoring and dashboards
- GitHub Actions CI/CD pipeline

Usage:
1. Deploy: ./deploy.sh
2. Validate: python validate_deployment.py
3. Test: python test_endpoints.py <cloudfront-url>"""

        self.run_command(f'git commit -m "{commit_message}"')
        return True
    
    def push_to_github(self, clone_url):
        """Push repository to GitHub"""
        print("⬆️ Pushing to GitHub...")
        
        # Add remote origin
        try:
            current_remote = self.run_command("git remote get-url origin", 
                                            check=False, capture_output=True)
            if current_remote:
                print("ℹ️ Remote origin already exists")
            else:
                self.run_command(f"git remote add origin {clone_url}")
        except:
            self.run_command(f"git remote add origin {clone_url}")
        
        # Push to GitHub
        self.run_command(f"git push -u origin {self.default_branch}")
        print("✅ Code pushed to GitHub successfully!")
        
        return True
    
    def setup_repository_settings(self):
        """Setup additional repository settings"""
        print("⚙️ Setting up repository settings...")
        
        # Add topics/tags
        topics = [
            "aws", "pulumi", "cloudfront", "alb", "ecs", "jwt", 
            "secrets-manager", "lambda", "fastapi", "infrastructure-as-code",
            "cdn", "security", "automation", "python", "docker"
        ]
        
        url = f"https://api.github.com/repos/{self.git_username}/{self.repo_name}/topics"
        headers = {
            "Authorization": f"token {self.git_token}",
            "Accept": "application/vnd.github.mercy-preview+json"
        }
        
        data = {"names": topics}
        
        try:
            response = requests.put(url, headers=headers, json=data)
            if response.status_code == 200:
                print("✅ Repository topics added successfully!")
            else:
                print(f"⚠️ Could not add topics: {response.status_code}")
        except Exception as e:
            print(f"⚠️ Error adding topics: {e}")
        
        return True
    
    def display_summary(self):
        """Display setup summary"""
        repo_url = f"https://github.com/{self.git_username}/{self.repo_name}"
        
        print("\n" + "="*70)
        print("🎉 Git repository setup completed successfully!")
        print("="*70)
        print(f"📍 Repository URL: {repo_url}")
        print(f"🌿 Default Branch: {self.default_branch}")
        print(f"👤 Owner: {self.git_username}")
        print("")
        print("🔗 Quick Links:")
        print(f"   - Repository: {repo_url}")
        print(f"   - Clone URL: {repo_url}.git")
        print(f"   - Issues: {repo_url}/issues")
        print(f"   - Actions: {repo_url}/actions")
        print(f"   - Settings: {repo_url}/settings")
        print("")
        print("📋 Next Steps:")
        print("1. Visit your repository on GitHub")
        print("2. Review the README.md for deployment instructions")
        print("3. Set up GitHub Actions secrets for CI/CD:")
        print("   - AWS_ACCESS_KEY_ID")
        print("   - AWS_SECRET_ACCESS_KEY") 
        print("   - PULUMI_ACCESS_TOKEN")
        print("4. Configure branch protection rules (optional)")
        print("5. Add collaborators if working in a team")
        print("")
        print("🚀 Ready to deploy:")
        print("   git clone " + repo_url + ".git")
        print("   cd CDN-Headers-Proj")
        print("   ./deploy.sh")
    
    def run_setup(self):
        """Run complete repository setup"""
        print("🚀 Starting CDN-Headers-Proj Git Repository Setup")
        print(f"📦 Repository: {self.repo_name}")
        print(f"👤 Username: {self.git_username}")
        print(f"🌿 Branch: {self.default_branch}")
        print("="*70)
        
        try:
            # Initialize Git repository
            if not self.initialize_git_repo():
                return False
            
            # Add and commit files
            if not self.add_and_commit_files():
                return False
            
            # Create GitHub repository
            clone_url = self.create_github_repository()
            if not clone_url:
                return False
            
            # Push to GitHub
            if not self.push_to_github(clone_url):
                return False
            
            # Setup repository settings
            self.setup_repository_settings()
            
            # Display summary
            self.display_summary()
            
            return True
            
        except Exception as e:
            print(f"❌ Setup failed: {e}")
            return False

def main():
    # Change to the CDN-Headers-Proj directory
    project_dir = Path(__file__).parent
    os.chdir(project_dir)
    
    # Run repository setup
    manager = GitRepositoryManager()
    success = manager.run_setup()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()