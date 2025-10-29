"""VPC and networking resources"""

import pulumi
import pulumi_aws as aws
from config import PROJECT_NAME, VPC_CIDR, PUBLIC_SUBNET_CIDRS, PRIVATE_SUBNET_CIDRS, COMMON_TAGS

def create_vpc():
    """Create VPC with public and private subnets"""
    
    # Create VPC
    vpc = aws.ec2.Vpc(
        f"{PROJECT_NAME}-vpc",
        cidr_block=VPC_CIDR,
        enable_dns_hostnames=True,
        enable_dns_support=True,
        tags={**COMMON_TAGS, "Name": f"{PROJECT_NAME}-vpc"}
    )
    
    # Create Internet Gateway
    igw = aws.ec2.InternetGateway(
        f"{PROJECT_NAME}-igw",
        vpc_id=vpc.id,
        tags={**COMMON_TAGS, "Name": f"{PROJECT_NAME}-igw"}
    )
    
    # Get availability zones
    azs = aws.get_availability_zones(state="available")
    
    # Create public subnets
    public_subnets = []
    for i, cidr in enumerate(PUBLIC_SUBNET_CIDRS):
        subnet = aws.ec2.Subnet(
            f"{PROJECT_NAME}-public-subnet-{i+1}",
            vpc_id=vpc.id,
            cidr_block=cidr,
            availability_zone=azs.names[i],
            map_public_ip_on_launch=True,
            tags={**COMMON_TAGS, "Name": f"{PROJECT_NAME}-public-subnet-{i+1}"}
        )
        public_subnets.append(subnet)
    
    # Create private subnets
    private_subnets = []
    for i, cidr in enumerate(PRIVATE_SUBNET_CIDRS):
        subnet = aws.ec2.Subnet(
            f"{PROJECT_NAME}-private-subnet-{i+1}",
            vpc_id=vpc.id,
            cidr_block=cidr,
            availability_zone=azs.names[i],
            tags={**COMMON_TAGS, "Name": f"{PROJECT_NAME}-private-subnet-{i+1}"}
        )
        private_subnets.append(subnet)
    
    # Create NAT Gateways
    nat_gateways = []
    for i, subnet in enumerate(public_subnets):
        eip = aws.ec2.Eip(
            f"{PROJECT_NAME}-nat-eip-{i+1}",
            domain="vpc",
            tags={**COMMON_TAGS, "Name": f"{PROJECT_NAME}-nat-eip-{i+1}"}
        )
        
        nat_gw = aws.ec2.NatGateway(
            f"{PROJECT_NAME}-nat-gw-{i+1}",
            allocation_id=eip.id,
            subnet_id=subnet.id,
            tags={**COMMON_TAGS, "Name": f"{PROJECT_NAME}-nat-gw-{i+1}"}
        )
        nat_gateways.append(nat_gw)
    
    # Create route tables
    public_rt = aws.ec2.RouteTable(
        f"{PROJECT_NAME}-public-rt",
        vpc_id=vpc.id,
        tags={**COMMON_TAGS, "Name": f"{PROJECT_NAME}-public-rt"}
    )
    
    # Public route to IGW
    aws.ec2.Route(
        f"{PROJECT_NAME}-public-route",
        route_table_id=public_rt.id,
        destination_cidr_block="0.0.0.0/0",
        gateway_id=igw.id
    )
    
    # Associate public subnets with public route table
    for i, subnet in enumerate(public_subnets):
        aws.ec2.RouteTableAssociation(
            f"{PROJECT_NAME}-public-rta-{i+1}",
            subnet_id=subnet.id,
            route_table_id=public_rt.id
        )
    
    # Create private route tables and routes
    for i, (subnet, nat_gw) in enumerate(zip(private_subnets, nat_gateways)):
        private_rt = aws.ec2.RouteTable(
            f"{PROJECT_NAME}-private-rt-{i+1}",
            vpc_id=vpc.id,
            tags={**COMMON_TAGS, "Name": f"{PROJECT_NAME}-private-rt-{i+1}"}
        )
        
        aws.ec2.Route(
            f"{PROJECT_NAME}-private-route-{i+1}",
            route_table_id=private_rt.id,
            destination_cidr_block="0.0.0.0/0",
            nat_gateway_id=nat_gw.id
        )
        
        aws.ec2.RouteTableAssociation(
            f"{PROJECT_NAME}-private-rta-{i+1}",
            subnet_id=subnet.id,
            route_table_id=private_rt.id
        )
    
    return {
        "vpc_id": vpc.id,
        "public_subnet_ids": [subnet.id for subnet in public_subnets],
        "private_subnet_ids": [subnet.id for subnet in private_subnets],
        "vpc": vpc
    }