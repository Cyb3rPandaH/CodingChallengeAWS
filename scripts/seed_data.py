'''
This script is used to seed initial data for the organization chatbot application.
It includes S3 buckets and files, as well as seed EC2 instances and IAM users.

References:
- https://docs.getmoto.org/en/latest/docs/configuration/environment_variables.html

'''

# Import necessary libraries
from botocore.exceptions import ClientError
import json
import os
import sys
from dotenv import load_dotenv

# Ensure project root is importable when running this file directly,
# e.g. `python scripts/seed_data.py`.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from the_organization_chatbot.domain.aws_resource_creation import (
    create_ec2_instance,
    create_s3_bucket,
    create_s3_bucket_policy,
    create_s3_file,
    create_user,
)
from the_organization_chatbot.infrastructure.aws_client import get_aws_client

# Load environment variables from .env file
load_dotenv()

# ************* RETAIL SCENARIO SEED VALUES *************

# IAM personas used by the chatbot scenario.
# Each user is created and then attached to the managed policy below.

IAM_USERS = [
    {
        "path": "/retail/admin/",
        "user_name": "retail-admin",
        "permissions_boundary": "arn:aws:iam::aws:policy/ReadOnlyAccess",
        "policy_arn": "arn:aws:iam::aws:policy/AdministratorAccess",
        "tags": [
            {"Key": "team", "Value": "platform"},
            {"Key": "role", "Value": "admin"},
            {"Key": "environment", "Value": "challenge"},
        ],
    },
    {
        "path": "/retail/dev/",
        "user_name": "retail-dev",
        "permissions_boundary": "arn:aws:iam::aws:policy/ReadOnlyAccess",
        "policy_arn": "arn:aws:iam::aws:policy/PowerUserAccess",
        "tags": [
            {"Key": "team", "Value": "engineering"},
            {"Key": "role", "Value": "developer"},
            {"Key": "environment", "Value": "challenge"},
        ],
    },
    {
        "path": "/retail/security/",
        "user_name": "retail-security",
        "permissions_boundary": "arn:aws:iam::aws:policy/ReadOnlyAccess",
        "policy_arn": "arn:aws:iam::aws:policy/SecurityAudit",
        "tags": [
            {"Key": "team", "Value": "security"},
            {"Key": "role", "Value": "analyst"},
            {"Key": "environment", "Value": "challenge"},
        ],
    },
]

NETWORK_CONFIG = {
    "vpc_name": "retail-challenge-vpc",
    "vpc_cidr": "10.42.0.0/16",
    "subnet_cidr": "10.42.10.0/24",
    "key_name": "retail-challenge-key",
}

# Security groups model a common retail setup:
# - web SG open to internet on 80/443
# - db SG restricted to internal subnet only
SECURITY_GROUPS = [
    {
        "name": "retail-web-sg",
        "description": "Retail web security group",
        "ip_permissions": [
            {
                "IpProtocol": "tcp",
                "FromPort": 80,
                "ToPort": 80,
                "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
            },
            {
                "IpProtocol": "tcp",
                "FromPort": 443,
                "ToPort": 443,
                "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
            },
        ],
    },
    {
        "name": "retail-db-sg",
        "description": "Retail database security group",
        "ip_permissions": [
            {
                "IpProtocol": "tcp",
                "FromPort": 5432,
                "ToPort": 5432,
                "IpRanges": [{"CidrIp": "10.42.10.0/24"}],
            }
        ],
    },
]

# Two EC2 instances are created to support multi-hop reasoning:
# one web server and one database server.
EC2_INSTANCES = [
    {
        "name": "retail-web-01",
        "image_id": "ami-0c55b159cbfafe1f0",
        "instance_type": "t3.micro",
        "security_group_name": "retail-web-sg",
        "private_ip": "10.42.10.10",
        "user_data": "#!/bin/bash\necho web-tier",
        "additional_info": "tier:web",
    },
    {
        "name": "retail-db-01",
        "image_id": "ami-0c55b159cbfafe1f0",
        "instance_type": "t3.micro",
        "security_group_name": "retail-db-sg",
        "private_ip": "10.42.10.20",
        "user_data": "#!/bin/bash\necho db-tier",
        "additional_info": "tier:database",
    },
]

# Bucket ACLs are intentionally mixed to support security questions,
# including one intentionally over-permissive sensitive bucket.
BUCKETS_TO_CREATE = [
    ("retail-web-assets", "public-read", "BucketOwnerPreferred"),
    ("retail-orders-private", "private", "BucketOwnerEnforced"),
    ("retail-sensitive-public", "public-read-write", "ObjectWriter"),
    ("retail-security-audit", "private", "BucketOwnerEnforced"),
]

BUCKET_POLICIES = {
    "retail-web-assets": {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowPublicReadBucket",
                "Effect": "Allow",
                "Principal": "*",
                "Action": ["s3:ListBucket"],
                "Resource": "arn:aws:s3:::retail-web-assets",
            },
            {
                "Sid": "AllowPublicReadObjects",
                "Effect": "Allow",
                "Principal": "*",
                "Action": ["s3:GetObject"],
                "Resource": "arn:aws:s3:::retail-web-assets/*",
            },
        ],
    },
    "retail-sensitive-public": {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AllowPublicReadBucketForTesting",
                "Effect": "Allow",
                "Principal": "*",
                "Action": ["s3:ListBucket"],
                "Resource": "arn:aws:s3:::retail-sensitive-public",
            },
            {
                "Sid": "AllowPublicReadWriteObjectsForTesting",
                "Effect": "Allow",
                "Principal": "*",
                "Action": ["s3:GetObject", "s3:PutObject"],
                "Resource": "arn:aws:s3:::retail-sensitive-public/*",
            }
        ],
    }
}

# Template objects used for S3 seeding.
# Placeholders are resolved at runtime after instance IDs and user names are known.
S3_OBJECTS_TEMPLATE = {
    "retail-web-assets": [
        ("site/index.html", "<html><body>Retail Shop</body></html>"),
        ("site/app.js", "console.log('retail frontend');"),
    ],
    "retail-orders-private": [
        ("orders/2026-02-16.json", json.dumps({"orders": 324, "status": "processed"}, indent=2)),
        ("inventory/stock_levels.csv", "sku,qty\nSKU-001,120\nSKU-009,44\n"),
    ],
    "retail-sensitive-public": [
        (
            "exports/customer_pii.csv",
            "customer_id,name,email,ssn\n1,Ana,ana@retail.local,111-22-3333\n2,Bob,bob@retail.local,222-33-4444\n",
        ),
        (
            "exports/payment_tokens.json",
            json.dumps(
                {
                    "token_batch": "tok-2026-02",
                    "count": 2,
                    "note": "INTENTIONALLY INSECURE FOR TESTING",
                },
                indent=2,
            ),
        ),
    ],
    "retail-security-audit": [
        (
            "findings/F-RET-001.json",
            json.dumps(
                {
                    "finding_id": "F-RET-001",
                    "severity": "high",
                    "issue": "Sensitive data bucket has public-read-write ACL",
                    "bucket": "retail-sensitive-public",
                    "affected_instances": ["{WEB_INSTANCE_ID}", "{DB_INSTANCE_ID}"],
                    "owners": ["{SEEDED_USERS}"],
                },
                indent=2,
            ),
        ),
        (
            "incidents/IR-2026-007.md",
            (
                "Incident IR-2026-007\n"
                "- Finding: F-RET-001\n"
                "- Public bucket: retail-sensitive-public\n"
                "- Web server instance: {WEB_INSTANCE_ID}\n"
                "- Database instance: {DB_INSTANCE_ID}\n"
                "- IAM users in scope: {SEEDED_USERS}\n"
            ),
        ),
    ],
}

if __name__ == "__main__":
    try:
        # ************* IAM USER SEEDING *************
        # Create/reuse IAM users from IAM_USERS and ensure each expected policy is attached.
        iam = get_aws_client(service="iam")
        seeded_users = []

        for user_config in IAM_USERS:
            user_response = create_user(
                path=user_config["path"],
                user_name=user_config["user_name"],
                permissions_boundary=user_config["permissions_boundary"],
                tags=user_config["tags"],
            )
            seeded_users.append(user_response.get("User", {}).get("UserName", user_config["user_name"]))

            attached_policies = iam.list_attached_user_policies(
                UserName=user_config["user_name"]
            ).get("AttachedPolicies", [])
            attached_arns = {policy["PolicyArn"] for policy in attached_policies}
            if user_config["policy_arn"] not in attached_arns:
                try:
                    iam.attach_user_policy(
                        UserName=user_config["user_name"],
                        PolicyArn=user_config["policy_arn"],
                    )
                except ClientError as e:
                    if e.response["Error"]["Code"] == "NoSuchEntity" and "aws:policy" in user_config["policy_arn"]:
                        # Moto does not pre-populate AWS managed policies. Create local equivalent.
                        policy_name = user_config["policy_arn"].split("/")[-1]
                        import json
                        try:
                            created = iam.create_policy(
                                PolicyName=policy_name,
                                Path="/",
                                PolicyDocument=json.dumps({
                                    "Version": "2012-10-17",
                                    "Statement": [{"Effect": "Allow", "Action": "*", "Resource": "*"}]
                                })
                            )
                            local_arn = created["Policy"]["Arn"]
                        except ClientError as ce:
                            if ce.response["Error"]["Code"] == "EntityAlreadyExists":
                                sts = get_aws_client(service="sts")
                                account_id = sts.get_caller_identity()["Account"]
                                local_arn = f"arn:aws:iam::{account_id}:policy/{policy_name}"
                            else:
                                raise ce
                        iam.attach_user_policy(
                            UserName=user_config["user_name"],
                            PolicyArn=local_arn,
                        )
                    else:
                        raise e

        # ************* NETWORK + EC2 SEEDING *************
        # Build baseline network resources (key pair, VPC, subnet, security groups)
        # and then create EC2 instances that do not already exist by private IP.
        ec2 = get_aws_client(service="ec2")

        try:
            ec2.create_key_pair(KeyName=NETWORK_CONFIG["key_name"])
        except ClientError as error:
            # Key pair can already exist on reruns; treat duplicate as expected.
            error_code = error.response.get("Error", {}).get("Code", "")
            if error_code != "InvalidKeyPair.Duplicate":
                raise

        vpcs = ec2.describe_vpcs(
            Filters=[{"Name": "tag:Name", "Values": [NETWORK_CONFIG["vpc_name"]]}]
        ).get("Vpcs", [])
        if vpcs:
            vpc_id = vpcs[0]["VpcId"]
        else:
            # Create VPC once and tag it so future runs can discover and reuse it.
            vpc_id = ec2.create_vpc(CidrBlock=NETWORK_CONFIG["vpc_cidr"])["Vpc"]["VpcId"]
            ec2.create_tags(Resources=[vpc_id], Tags=[{"Key": "Name", "Value": NETWORK_CONFIG["vpc_name"]}])

        subnets = ec2.describe_subnets(
            Filters=[
                {"Name": "vpc-id", "Values": [vpc_id]},
                {"Name": "cidr-block", "Values": [NETWORK_CONFIG["subnet_cidr"]]},
            ]
        ).get("Subnets", [])
        if subnets:
            subnet_id = subnets[0]["SubnetId"]
        else:
            # Create one subnet for both web and db instances in this mock scenario.
            subnet_id = ec2.create_subnet(
                VpcId=vpc_id,
                CidrBlock=NETWORK_CONFIG["subnet_cidr"],
            )["Subnet"]["SubnetId"]

        security_group_ids = {}
        for sg_config in SECURITY_GROUPS:
            groups = ec2.describe_security_groups(
                Filters=[
                    {"Name": "vpc-id", "Values": [vpc_id]},
                    {"Name": "group-name", "Values": [sg_config["name"]]},
                ]
            ).get("SecurityGroups", [])

            if groups:
                sg_id = groups[0]["GroupId"]
            else:
                # Create SG if it does not exist.
                sg_id = ec2.create_security_group(
                    GroupName=sg_config["name"],
                    Description=sg_config["description"],
                    VpcId=vpc_id,
                )["GroupId"]

            security_group_ids[sg_config["name"]] = sg_id

            try:
                ec2.authorize_security_group_ingress(
                    GroupId=sg_id,
                    IpPermissions=sg_config["ip_permissions"],
                )
            except ClientError as error:
                # Duplicate ingress rules are expected when the script is rerun.
                error_code = error.response.get("Error", {}).get("Code", "")
                if error_code != "InvalidPermission.Duplicate":
                    raise

        existing_instances_response = ec2.describe_instances(
            Filters=[
                {
                    "Name": "instance-state-name",
                    "Values": ["pending", "running", "stopping", "stopped"],
                }
            ]
        )

        existing_private_ips = set()
        existing_instance_ids = []
        for reservation in existing_instances_response.get("Reservations", []):
            for instance in reservation.get("Instances", []):
                private_ip = instance.get("PrivateIpAddress")
                if private_ip:
                    existing_private_ips.add(private_ip)
                existing_instance_ids.append(instance.get("InstanceId", "i-unknown"))

        seeded_instance_ids = list(existing_instance_ids)
        for instance_config in EC2_INSTANCES:
            # Private IP is used as idempotency guard for instance creation.
            if instance_config["private_ip"] in existing_private_ips:
                continue

            created_instance = create_ec2_instance(
                image_id=instance_config["image_id"],
                instance_type=instance_config["instance_type"],
                key_name=NETWORK_CONFIG["key_name"],
                security_group_ids=[security_group_ids[instance_config["security_group_name"]]],
                subnet_id=subnet_id,
                user_data=instance_config["user_data"],
                private_ip=instance_config["private_ip"],
                additional_info=instance_config["additional_info"],
                min_count=1,
                max_count=1,
            )
            seeded_instance_ids.append(created_instance.get("InstanceId", "i-unknown"))

        # ************* S3 BUCKET + OBJECT SEEDING *************
        # Create buckets first, then upload objects with resolved placeholders.
        for bucket_name, acl, object_ownership in BUCKETS_TO_CREATE:
            create_s3_bucket(
                bucket_name=bucket_name,
                acl=acl,
                object_ownership=object_ownership,
            )

        # Apply scenario bucket policies after buckets are created.
        for bucket_name, policy_document in BUCKET_POLICIES.items():
            create_s3_bucket_policy(
                bucket_name=bucket_name,
                policy_document=policy_document,
            )

        web_instance_id = seeded_instance_ids[0] if seeded_instance_ids else "i-unknown"
        db_instance_id = seeded_instance_ids[1] if len(seeded_instance_ids) > 1 else web_instance_id

        rendered_s3_objects = {}
        for bucket_name, objects in S3_OBJECTS_TEMPLATE.items():
            rendered_s3_objects[bucket_name] = []
            for file_key, file_content in objects:
                # Replace template markers with runtime values for cross-resource linking.
                rendered_content = file_content.replace("{WEB_INSTANCE_ID}", web_instance_id)
                rendered_content = rendered_content.replace("{DB_INSTANCE_ID}", db_instance_id)
                rendered_content = rendered_content.replace("{SEEDED_USERS}", ", ".join(seeded_users))
                rendered_s3_objects[bucket_name].append((file_key, rendered_content))

        for bucket_name, objects in rendered_s3_objects.items():
            for file_key, file_content in objects:
                create_s3_file(
                    bucket_name=bucket_name,
                    file_key=file_key,
                    file_content=file_content,
                )

        print("\nSuccess: Moto server populated with retail challenge data!")
    except Exception as error:
        print(f"\nError: Could not connect to Moto server at {os.getenv('ENDPOINT_URL')}. Is it running?")
        print(f"Details: {error}")
