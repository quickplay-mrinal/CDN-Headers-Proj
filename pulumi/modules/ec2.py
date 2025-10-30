"""
EC2 Module - Creates launch template and auto scaling group
All resources deployed in the specified region (default: ap-south-2)
"""
import pulumi_aws as aws
import base64
from .ami import get_latest_amazon_linux_ami

def create_user_data(config):
    """Create user data script for EC2 instances"""
    project_name = config["project_name"]
    aws_region = config["aws_region"]
    
    user_data = f"""#!/bin/bash
# Update system
yum update -y

# Install and configure Apache
yum install -y httpd
systemctl enable httpd
systemctl start httpd

# Verify Apache is running
systemctl status httpd

# Install CloudWatch agent
yum install -y amazon-cloudwatch-agent

# Create log directory
mkdir -p /var/log/jwt-demo

# Create main web page
cat > /var/www/html/index.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>JWT Security Demo - Backend Service</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            margin: 0; 
            padding: 40px; 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            overflow: hidden;
        }}
        .header {{ 
            background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%);
            color: white;
            padding: 30px; 
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
        }}
        .header p {{
            margin: 10px 0 0 0;
            font-size: 1.2em;
            opacity: 0.9;
        }}
        .info {{ 
            margin: 0; 
            padding: 25px; 
            background: #f8f9fa; 
            border-left: 4px solid #4CAF50;
        }}
        .info h3 {{
            color: #2c3e50;
            margin-top: 0;
        }}
        .badge {{
            display: inline-block;
            background: #e3f2fd;
            color: #1976d2;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 0.9em;
            margin: 5px 5px 5px 0;
        }}
        .success {{
            background: #d4edda;
            color: #155724;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
            border-left: 4px solid #28a745;
        }}
        .server-info {{
            background: white;
            padding: 25px;
            border-top: 1px solid #eee;
        }}
        .grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-top: 20px;
        }}
        @media (max-width: 600px) {{
            .grid {{
                grid-template-columns: 1fr;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>JWT Security Demo</h1>
            <p>Backend Service Protected by CloudFront JWT Validation</p>
        </div>
        
        <div class="success">
            <h3>Authentication Successful!</h3>
            <p>This request was validated by CloudFront Function with JWT token.</p>
        </div>
        
        <div class="info">
            <h3>Security Features</h3>
            <div class="grid">
                <div>
                    <span class="badge">JWT Validation</span>
                    <span class="badge">Edge Security</span>
                    <span class="badge">Zero Downtime</span>
                </div>
                <div>
                    <span class="badge">Industry Standard</span>
                    <span class="badge">Scalable</span>
                    <span class="badge">Cost Effective</span>
                </div>
            </div>
        </div>
        
        <div class="server-info">
            <h3>Server Information</h3>
            <div class="grid">
                <div>
                    <p><strong>Region:</strong> {aws_region}</p>
                    <p><strong>Project:</strong> {project_name}</p>
                    <p><strong>Instance ID:</strong> <span id="instance-id">Loading...</span></p>
                </div>
                <div>
                    <p><strong>Timestamp:</strong> <span id="timestamp"></span></p>
                    <p><strong>Auth Method:</strong> CloudFront JWT Function</p>
                    <p><strong>Status:</strong> <span style="color: #28a745;">Secure</span></p>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Display current timestamp
        document.getElementById('timestamp').textContent = new Date().toLocaleString();
        
        // Try to get instance metadata
        fetch('/latest/meta-data/instance-id')
            .then(response => response.text())
            .then(data => document.getElementById('instance-id').textContent = data)
            .catch(() => document.getElementById('instance-id').textContent = 'Not available');
    </script>
</body>
</html>
EOF

# Create health check endpoint
cat > /var/www/html/health << 'EOF'
OK
EOF

# Create detailed health check endpoint
cat > /var/www/html/health-detail << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>Health Check Detail</title>
</head>
<body>
    <h1>Server Health Check</h1>
    <p><strong>Status:</strong> OK</p>
    <p><strong>Timestamp:</strong> <script>document.write(new Date().toISOString());</script></p>
    <p><strong>Server:</strong> Apache/Amazon Linux</p>
    <p><strong>Region:</strong> {aws_region}</p>
</body>
</html>
EOF

# Create API endpoint for header inspection
cat > /var/www/html/api << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>JWT Headers API</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        .success {{ background: #d4edda; padding: 15px; border-radius: 5px; color: #155724; }}
        .info {{ background: #e8f4fd; padding: 15px; border-radius: 5px; margin: 10px 0; }}
        pre {{ background: #f8f9fa; padding: 15px; border-radius: 5px; overflow-x: auto; }}
    </style>
</head>
<body>
    <div class="success">
        <h2>JWT API Endpoint</h2>
        <p>This endpoint shows JWT validation headers added by CloudFront Function</p>
    </div>
    
    <div class="info">
        <h3>Expected Headers from CloudFront Function:</h3>
        <pre>
x-validated-user: demo-user
x-auth-method: jwt-cloudfront-function  
x-jwt-validated: true
        </pre>
    </div>

    <div class="info">
        <h3>Request Information:</h3>
        <p><strong>Timestamp:</strong> <span id="timestamp"></span></p>
        <p><strong>Region:</strong> {aws_region}</p>
        <p><strong>Validation:</strong> CloudFront JWT Function</p>
    </div>

    <script>
        document.getElementById('timestamp').textContent = new Date().toISOString();
    </script>
</body>
</html>
EOF

# Set proper permissions
chown -R apache:apache /var/www/html
chmod -R 755 /var/www/html

# Restart Apache and verify
systemctl restart httpd
systemctl status httpd

# Test Apache is responding
curl -f http://localhost/ || echo "Apache not responding locally" >> /var/log/jwt-demo/startup.log

# Log startup completion
echo "$(date): JWT Security Demo server setup complete!" >> /var/log/jwt-demo/startup.log

# Configure CloudWatch agent (basic configuration)
cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << 'EOF'
{{
    "logs": {{
        "logs_collected": {{
            "files": {{
                "collect_list": [
                    {{
                        "file_path": "/var/log/httpd/access_log",
                        "log_group_name": "/aws/ec2/{project_name}/httpd/access",
                        "log_stream_name": "{{instance_id}}"
                    }},
                    {{
                        "file_path": "/var/log/httpd/error_log",
                        "log_group_name": "/aws/ec2/{project_name}/httpd/error",
                        "log_stream_name": "{{instance_id}}"
                    }}
                ]
            }}
        }}
    }}
}}
EOF

# Start CloudWatch agent
/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl -a fetch-config -m ec2 -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json -s

# Final status check and signal completion
systemctl is-active httpd && echo "Apache is running" || echo "Apache failed to start"

# Test local health endpoint
curl -f http://localhost/health && echo "Health endpoint working" || echo "Health endpoint failed"

# Setup completed - no CloudFormation signaling needed with Pulumi

echo "JWT Security Demo server setup complete!"
echo "$(date): Setup completed successfully" >> /var/log/jwt-demo/startup.log
"""
    
    return base64.b64encode(user_data.encode()).decode()

def create_ec2_resources(config, security_group_id, instance_profile_name, subnet_ids, target_group_arn=None):
    """Create EC2 launch template and auto scaling group with proper target group attachment"""
    
    project_name = config["project_name"]
    common_tags = config["common_tags"]
    aws_region = config["aws_region"]
    ec2_config = config["ec2_config"]
    
    # Get the latest Amazon Linux AMI for the current region
    ami_id = get_latest_amazon_linux_ami()
    
    # Create user data
    user_data = create_user_data(config)
    
    # Launch Template
    launch_template = aws.ec2.LaunchTemplate("jwt-lt",
        name_prefix=f"{project_name}-lt-",
        image_id=ami_id,
        instance_type=ec2_config["instance_type"],
        vpc_security_group_ids=[security_group_id],
        iam_instance_profile=aws.ec2.LaunchTemplateIamInstanceProfileArgs(
            name=instance_profile_name
        ),
        user_data=user_data,
        tag_specifications=[
            aws.ec2.LaunchTemplateTagSpecificationArgs(
                resource_type="instance",
                tags={**common_tags, "Name": f"{project_name}-instance"}
            )
        ],
        tags={**common_tags, "Name": f"{project_name}-lt"}
    )
    
    # Auto Scaling Group (without target group initially)
    asg = aws.autoscaling.Group("jwt-asg",
        name=f"{project_name}-asg",
        vpc_zone_identifiers=subnet_ids,
        health_check_type="EC2",  # Start with EC2 health checks
        health_check_grace_period=300,  # Standard grace period
        min_size=ec2_config["min_size"],
        max_size=ec2_config["max_size"],
        desired_capacity=ec2_config["desired_capacity"],
        launch_template=aws.autoscaling.GroupLaunchTemplateArgs(
            id=launch_template.id,
            version="$Latest"
        ),
        tags=[
            aws.autoscaling.GroupTagArgs(
                key="Name",
                value=f"{project_name}-asg-instance",
                propagate_at_launch=True
            ),
            aws.autoscaling.GroupTagArgs(
                key="Project",
                value=project_name,
                propagate_at_launch=True
            )
        ]
    )
    
    # Separate target group attachment for better reliability
    asg_attachment = None
    if target_group_arn:
        asg_attachment = aws.autoscaling.Attachment("jwt-asg-attachment",
            autoscaling_group_name=asg.name,
            lb_target_group_arn=target_group_arn
        )
    
    return {
        "launch_template": launch_template,
        "auto_scaling_group": asg,
        "asg_attachment": asg_attachment,
        "ami_id": ami_id
    }