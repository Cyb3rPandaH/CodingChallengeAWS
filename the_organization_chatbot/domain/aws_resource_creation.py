'''
This module provides functions to create and manage AWS resources for the organization chatbot application.
It includes functions to create S3 buckets, EC2 instances, and IAM users.
'''

# Import necessary libraries
from botocore.exceptions import ClientError
import json

from the_organization_chatbot.infrastructure.aws_client import get_aws_client

# ************* S3 BUCKET CREATION *************

# Create S3 buckets.
def create_s3_bucket(bucket_name: str,
                     acl: str = "private", # Private bucket by default - other options include "public-read", "public-read-write", "aws-exec-read", "authenticated-read", "bucket-owner-read", "bucket-owner-full-control".
                     #config: dict = None,
                     #grant_full_control=None,
                     #grant_read=None,
                     #grant_read_acp=None,
                     #grant_write_acp=None,
                     #object_lock_enabled_for_bucket=None,
                     object_ownership: str="BucketOwnerEnforced", # Object ownership setting for the bucket. Options include "BucketOwnerEnforced", "ObjectWriter", and "BucketOwnerPreferred".
                     #s3_client=None
                     ):
    
    '''
    Create an S3 bucket with the specified name, ACL and object ownership settings.

    Parameters:
        bucket_name (str): The name of the S3 bucket to create.
        acl (str): The canned ACL to apply to the bucket. Default is "private". Other options include "public-read", "public-read-write", "aws-exec-read", "authenticated-read", "bucket-owner-read", "bucket-owner-full-control". 
        object_ownership (str): The object ownership setting for the bucket. Default is "BucketOwnerEnforced". Other options include "ObjectWriter" and "BucketOwnerPreferred".
    
    Returns:
        None
    
    References:
    - https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3/client/create_bucket.html
    - https://docs.aws.amazon.com/AmazonS3/latest/userguide/acl-overview.html#canned-acl
    - https://docs.aws.amazon.com/AmazonS3/latest/userguide/about-object-ownership.html#object-ownership-overview
    - https://docs.aws.amazon.com/AmazonS3/latest/API/API_control_CreateBucket.html#API_control_CreateBucket_Errors
    '''

    # Get client
    s3 = get_aws_client(service="s3")
    
    # Create empty bucket
    print(f"Creating S3 bucket: {bucket_name} with ACL: {acl}...")
    try:
        s3.create_bucket(
            Bucket=bucket_name,
            ACL=acl,
            ObjectOwnership=object_ownership
        )
    except ClientError as error:
        error_code = error.response.get("Error", {}).get("Code", "")
        status_code = error.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if error_code == "BucketAlreadyExists":
            print(
                f"Bucket name not available: {bucket_name}. "
                "The requested Outposts bucket name is not available because the bucket namespace "
                "is shared by all users of AWS Outposts in this Region. "
                f"HTTP Status Code: {status_code}. Select a different name and try again."
            )
            return
        if error_code == "BucketAlreadyOwnedByYou":
            print(
                f"Bucket already owned by you: {bucket_name}. "
                "The Outposts bucket you tried to create already exists, and you own it. "
                f"HTTP Status Code: {status_code}. Skipping create."
            )
            return
        raise

# ************* FILE CREATION *************

# Create files in S3 buckets
def create_s3_file(bucket_name: str, 
                   file_key: str, 
                   file_content: str, 
                   #s3_client=None
                   ):

    '''
    Create a file in an S3 bucket with the specified content.

    Parameters:
        bucket_name (str): The name of the S3 bucket where the file will be created.
        file_key (str): The key (path) for the file to be created in the S3 bucket.
        file_content (str): The content to be written to the file in the S3 bucket.
    Returns:
        None
    
    References:
    - https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutObject.html
    - https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutObject.html#API_PutObject_Errors
    '''

    # Get client
    s3 = get_aws_client(service="s3")

    # Create file in bucket
    print(f"Creating file: {file_key} in bucket: {bucket_name}...")
    
    try:
        s3.put_object(
            Bucket=bucket_name,
            Key=file_key,
            Body=file_content
        )
    except ClientError as error:
        error_code = error.response.get("Error", {}).get("Code", "")
        if error_code == "EncryptionTypeMismatch":
            print(
                f"Encryption type mismatch for object: {file_key} in bucket: {bucket_name}. "
                "Use matching SSE headers (for example SSE-S3 or SSE-KMS)."
            )
            raise
        if error_code == "InvalidRequest":
            print(
                f"Invalid PutObject request for object: {file_key} in bucket: {bucket_name}. "
                "Verify request headers and parameters."
            )
            raise
        if error_code == "InvalidWriteOffset":
            print(
                f"Invalid write offset for object: {file_key} in bucket: {bucket_name}. "
                "Offset must match current object size."
            )
            raise
        if error_code == "TooManyParts":
            print(
                f"Object has too many parts for key: {file_key} in bucket: {bucket_name}. "
                "Consider rewriting the object or using CopyObject to compact parts."
            )
            raise
        raise


# ************* BUCKET POLICY CREATION *************

# Create bucket policy in S3 buckets
def create_s3_bucket_policy(
    bucket_name: str,
    policy_document: dict,
    expected_bucket_owner: str | None = None,
    confirm_remove_self_bucket_access: bool | None = None,
    checksum_algorithm: str | None = None,
):

    '''
    Create or update a bucket policy for an S3 bucket.

    Parameters:
        bucket_name (str): The name of the S3 bucket where the policy will be applied.
        policy_document (dict): The JSON policy document as a dictionary.
        expected_bucket_owner (str, optional): Expected AWS account ID of the bucket owner.
        confirm_remove_self_bucket_access (bool, optional): Set to True to acknowledge potentially
            removing your own ability to update the policy.
        checksum_algorithm (str, optional): SDK checksum algorithm (CRC32, CRC32C, CRC64NVME,
            SHA1, SHA256).

    Returns:
        None

    References:
    - https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutBucketPolicy.html
    '''

    # Get client
    s3 = get_aws_client(service="s3")

    # Build request parameters dynamically so optional fields are only sent when provided.
    request_params = {
        "Bucket": bucket_name,
        "Policy": json.dumps(policy_document),
    }
    if expected_bucket_owner is not None:
        request_params["ExpectedBucketOwner"] = expected_bucket_owner
    if confirm_remove_self_bucket_access is not None:
        request_params["ConfirmRemoveSelfBucketAccess"] = confirm_remove_self_bucket_access
    if checksum_algorithm is not None:
        request_params["ChecksumAlgorithm"] = checksum_algorithm

    # Apply policy to bucket
    print(f"Applying bucket policy to bucket: {bucket_name}...")
    try:
        s3.put_bucket_policy(**request_params)
    except ClientError as error:
        error_code = error.response.get("Error", {}).get("Code", "")
        if error_code == "NoSuchBucket":
            print(f"Bucket does not exist: {bucket_name}. Cannot apply bucket policy.")
            return
        raise

# ************* EC2 CREATION (START) *************

# Start EC2 Instances
def create_ec2_instance(image_id: str, 
                        instance_type: str, 
                        key_name: str, 
                        security_group_ids: list, 
                        subnet_id: str, 
                        user_data: str,
                        private_ip: str,
                        additional_info: str,
                        min_count: int = 1,
                        max_count: int = 1
                        ):

    '''
    Create an EC2 instance with the specified configuration.

    Parameters:
    - image_id (str): The ID of the AMI to use for the instance.
    - instance_type (str): The type of instance to create (e.g., 't2.micro').
    - key_name (str): The name of the key pair to use for SSH access to the instance.
    - security_group_ids (list): A list of security group IDs to associate with the instance.
    - subnet_id (str): The ID of the subnet in which to launch the instance.
    - user_data (str): The user data to provide when launching the instance. This can be used to run scripts or configure the instance on startup.
    - private_ip (str): The private IP address to assign to the instance. If not specified, an IP address will be automatically assigned.
    - additional_info (str): Additional information to include in the instance launch request.
    - min_count (int, optional): The minimum number of instances to launch. Default is 1.
    - max_count (int, optional): The maximum number of instances to launch. Default is 1.

    Returns:
    - instance: The created EC2 instance object.

    References:
    - https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2/service-resource/create_instances.html
    - https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instance-types.html
    - https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-security-groups.html
    - https://repost.aws/questions/QUsNKLiffNSqq0RgF9i-20_A/invalidamiid-notfound-when-executing-automation
    - https://stackoverflow.com/questions/47012647/unauthorized-operation-error-occurs-when-using-boto3-to-launch-an-ec2-instance-w
    - https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2/client/run_instances.html

    '''
    
    # Get client
    ec2 = get_aws_client(service="ec2")
    
    # Create an instance
    print(f"Creating EC2 instance with image_id: {image_id}, instance_type: {instance_type}...")

    run_instances_payload = {
        "ImageId": image_id,
        "InstanceType": instance_type,
        "KeyName": key_name,
        "SecurityGroupIds": security_group_ids,
        "SubnetId": subnet_id,
        "UserData": user_data,
        "PrivateIpAddress": private_ip,
        "AdditionalInfo": additional_info,
        "MinCount": min_count,
        "MaxCount": max_count
    }

    try:
        response = ec2.run_instances(**run_instances_payload)
        instance = response["Instances"][0]
        return instance

    except ClientError as error:
        error_code = error.response.get("Error", {}).get("Code", "")
        if error_code == "InvalidAMIID.NotFound":
            print(
                f"Invalid AMI ID: {image_id}. "
                "The specified AMI ID does not exist. Verify the AMI ID and try again."
            )
            raise
        if error_code == "UnauthorizedOperation":
            print(
                f"Unauthorized operation for creating EC2 instance with image_id: {image_id}, instance_type: {instance_type}. "
                "You do not have permission to perform this operation. Check your IAM permissions and try again."
            )
            raise
        raise

# ************* IAM CONFIG DEFINITION *************


def create_user(path: str,
                user_name: str,
                permissions_boundary: str,
                tags: list
                ) -> dict:
    
    '''
    Create an IAM user with read-only access.
    
    Parameters:
    - path (str): The path for the user name. For example, "/division_abc/subdivision_xyz/engineering/". If not included, it defaults to a slash (/).
    - user_name (str): The name of the user to create. This is used for login and is not case sensitive. The user name must be unique within the AWS account. If the specified user name already exists, the CreateUser operation fails. This parameter allows (through its regex pattern) a string of characters consisting of upper and lowercase alphanumeric characters with no spaces. You can also include any of the following characters: _+=,.@-
    - permissions_boundary (str): The ARN of the policy that is used to set the permissions boundary for the user. A permissions boundary is an advanced feature for using a managed policy to set the permissions boundary for a user. Permissions boundaries allow you to delegate permissions management to other administrators, while ensuring that the administrators can only grant permissions that are within the boundary. For more information about permissions boundaries, see Permissions boundaries for IAM entities in the IAM User Guide.
    - tags (list): A list of tags that you want to attach to the user. Each tag consists of a key name and an associated value. The user can have a maximum of 50 tags. Each tag key can be up to 128 characters long, and each tag value can be up to 256 characters long. Allowed characters are letters, numbers, and spaces representable in UTF-8. The following characters are allowed in tag keys and values: + - = . _ : / @            
    
    Returns:
    - user: The created IAM user object. Is a dictionary with keys such as "UserName", "UserId", "Arn", "CreateDate", etc.
    
    References:
    - https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/iam.html
    - https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/iam/client/create_user.html
    - https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_identifiers.html
    '''
    
    # Get client
    iam = get_aws_client(service="iam")
    
    # Create a user
    print(f"Creating IAM user: {user_name} with permissions boundary: {permissions_boundary}...")

    try:
        response = iam.create_user(UserName=user_name,
                                   Path=path,
                                   PermissionsBoundary=permissions_boundary,
                                   Tags=tags
                                   )
        return response
    
    except ClientError as error:
            error_code = error.response.get("Error", {}).get("Code", "")
            if error_code != "EntityAlreadyExists":
                raise
            print(f"IAM user already exists: {user_name}. Continuing.")
            existing_user_response = iam.get_user(UserName=user_name)
            return existing_user_response
        
