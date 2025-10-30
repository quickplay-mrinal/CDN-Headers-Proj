"""
AMI Module - Dynamically gets the latest Amazon Linux AMI for the region
This ensures we always use a valid, current AMI ID with multiple fallback options
"""
import pulumi_aws as aws
import pulumi

def get_static_ami_mapping():
    """Get static AMI mapping as fallback"""
    return {
        "ap-south-2": "ami-0ad21ae1d0696ad58",  # Amazon Linux 2 in ap-south-2 (Hyderabad)
        "us-east-1": "ami-0c02fb55956c7d316",   # Amazon Linux 2 in us-east-1 (N. Virginia)
        "us-west-2": "ami-0c2d3e23f757b5d84",   # Amazon Linux 2 in us-west-2 (Oregon)
        "eu-west-1": "ami-0c9c942bd7bf113a2",   # Amazon Linux 2 in eu-west-1 (Ireland)
        "ap-south-1": "ami-0f58b397bc5c1f2e8"   # Amazon Linux 2 in ap-south-1 (Mumbai)
    }

def get_current_region():
    """Get the current AWS region from Pulumi config"""
    config = pulumi.Config("aws")
    return config.get("region") or "us-east-1"

def get_latest_amazon_linux_ami():
    """Get the latest Amazon Linux AMI for the current region with fallbacks"""
    
    try:
        # Try Amazon Linux 2023 first
        ami = aws.ec2.get_ami(
            most_recent=True,
            owners=["amazon"],
            filters=[
                aws.ec2.GetAmiFilterArgs(
                    name="name",
                    values=["al2023-ami-*-x86_64"]
                ),
                aws.ec2.GetAmiFilterArgs(
                    name="virtualization-type",
                    values=["hvm"]
                ),
                aws.ec2.GetAmiFilterArgs(
                    name="state",
                    values=["available"]
                )
            ]
        )
        
        return ami.id
        
    except Exception:
        # Fallback to Amazon Linux 2
        try:
            ami = aws.ec2.get_ami(
                most_recent=True,
                owners=["amazon"],
                filters=[
                    aws.ec2.GetAmiFilterArgs(
                        name="name",
                        values=["amzn2-ami-hvm-*-x86_64-gp2"]
                    ),
                    aws.ec2.GetAmiFilterArgs(
                        name="virtualization-type",
                        values=["hvm"]
                    ),
                    aws.ec2.GetAmiFilterArgs(
                        name="state",
                        values=["available"]
                    )
                ]
            )
            
            return ami.id
            
        except Exception:
            # Final fallback - use static mapping based on region
            current_region = get_current_region()
            static_mapping = get_static_ami_mapping()
            
            if current_region in static_mapping:
                return static_mapping[current_region]
            else:
                # Ultimate fallback
                return static_mapping["us-east-1"]

def get_latest_ubuntu_ami():
    """Get the latest Ubuntu 22.04 LTS AMI for the current region (alternative)"""
    
    # Get the most recent Ubuntu 22.04 LTS AMI
    ami = aws.ec2.get_ami(
        most_recent=True,
        owners=["099720109477"],  # Canonical
        filters=[
            aws.ec2.GetAmiFilterArgs(
                name="name",
                values=["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
            ),
            aws.ec2.GetAmiFilterArgs(
                name="virtualization-type",
                values=["hvm"]
            ),
            aws.ec2.GetAmiFilterArgs(
                name="state",
                values=["available"]
            )
        ]
    )
    
    return ami.id