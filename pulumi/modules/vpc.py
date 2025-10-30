"""
VPC Module - Creates VPC, subnets, internet gateway, and routing
All resources deployed in the specified region (default: ap-south-2)
"""
import pulumi_aws as aws

def create_vpc(config):
    """Create VPC with public and private subnets"""
    
    project_name = config["project_name"]
    common_tags = config["common_tags"]
    network_config = config["network_config"]
    
    # VPC
    vpc = aws.ec2.Vpc("jwt-vpc",
        cidr_block=network_config["vpc_cidr"],
        enable_dns_hostnames=True,
        enable_dns_support=True,
        tags={**common_tags, "Name": f"{project_name}-vpc"}
    )
    
    # Public subnets for ALB
    public_subnets = []
    for i, (cidr, az) in enumerate(zip(network_config["public_subnet_cidrs"], 
                                      network_config["availability_zones"])):
        subnet = aws.ec2.Subnet(f"public-subnet-{i+1}",
            vpc_id=vpc.id,
            cidr_block=cidr,
            availability_zone=az,
            map_public_ip_on_launch=True,
            tags={**common_tags, "Name": f"{project_name}-public-{i+1}", "Type": "Public"}
        )
        public_subnets.append(subnet)
    
    # Private subnets for EC2 instances
    private_subnets = []
    for i, (cidr, az) in enumerate(zip(network_config["private_subnet_cidrs"], 
                                      network_config["availability_zones"])):
        subnet = aws.ec2.Subnet(f"private-subnet-{i+1}",
            vpc_id=vpc.id,
            cidr_block=cidr,
            availability_zone=az,
            tags={**common_tags, "Name": f"{project_name}-private-{i+1}", "Type": "Private"}
        )
        private_subnets.append(subnet)
    
    # Internet Gateway
    igw = aws.ec2.InternetGateway("jwt-igw",
        vpc_id=vpc.id,
        tags={**common_tags, "Name": f"{project_name}-igw"}
    )
    
    # Route table for public subnets
    public_route_table = aws.ec2.RouteTable("public-rt",
        vpc_id=vpc.id,
        routes=[
            aws.ec2.RouteTableRouteArgs(
                cidr_block="0.0.0.0/0",
                gateway_id=igw.id,
            )
        ],
        tags={**common_tags, "Name": f"{project_name}-public-rt"}
    )
    
    # Associate public subnets with route table
    for i, subnet in enumerate(public_subnets):
        aws.ec2.RouteTableAssociation(f"public-rta-{i+1}",
            subnet_id=subnet.id,
            route_table_id=public_route_table.id
        )
    
    # NAT Gateway for private subnets (required for internet access)
    nat_eip = aws.ec2.Eip("nat-eip",
        domain="vpc",  # Use domain="vpc" for VPC EIPs
        tags={**common_tags, "Name": f"{project_name}-nat-eip"}
    )
    
    nat_gateway = aws.ec2.NatGateway("nat-gw",
        allocation_id=nat_eip.id,
        subnet_id=public_subnets[0].id,
        tags={**common_tags, "Name": f"{project_name}-nat-gw"}
    )
    
    # Private route table (with NAT for internet access)
    private_route_table = aws.ec2.RouteTable("private-rt",
        vpc_id=vpc.id,
        routes=[
            aws.ec2.RouteTableRouteArgs(
                cidr_block="0.0.0.0/0",
                nat_gateway_id=nat_gateway.id,
            )
        ],
        tags={**common_tags, "Name": f"{project_name}-private-rt"}
    )
    
    # Associate private subnets with private route table
    for i, subnet in enumerate(private_subnets):
        aws.ec2.RouteTableAssociation(f"private-rta-{i+1}",
            subnet_id=subnet.id,
            route_table_id=private_route_table.id
        )
    
    return {
        "vpc": vpc,
        "public_subnets": public_subnets,
        "private_subnets": private_subnets,
        "internet_gateway": igw,
        "nat_gateway": nat_gateway,
        "nat_eip": nat_eip,
        "public_route_table": public_route_table,
        "private_route_table": private_route_table
    }