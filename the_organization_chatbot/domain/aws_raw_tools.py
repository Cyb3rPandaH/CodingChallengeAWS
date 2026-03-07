'''
AWS Tools Module for the organization Chatbot
This module provides utility functions and classes for interacting with AWS services.
'''

# Import necessary libraries
from botocore.exceptions import ClientError
import json

from the_organization_chatbot.infrastructure.aws_client import get_aws_client

# Function to list S3 buckets for an account
def list_s3_buckets(
	max_buckets: int | None = None,
	continuation_token: str | None = None,
	prefix: str | None = None,
	bucket_region: str | None = None,
) -> dict:
	'''
	List S3 buckets from the configured AWS endpoint (Moto in local development)
	using the v2-style ListBuckets request parameters.

	Parameters:
	- max_buckets (int, optional): Maximum number of buckets to return.
	- continuation_token (str, optional): Token for paginated bucket listing.
	- prefix (str, optional): Filter bucket names by prefix.
	- bucket_region (str, optional): Limit results to a specific AWS region code.
	
	Returns:
	- dict: A JSON-friendly response with Buckets, Owner, ContinuationToken,
	  Prefix, and Count.

	References:
	- https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3/client/list_buckets.html
	- https://docs.aws.amazon.com/AmazonS3/latest/API/API_ListBuckets.html
	'''

    # Raw response example	
	# {
    #     'ResponseMetadata': {
    #         'RequestId': 'jxArT1pND0L8fPf4H99hCdNZ1WCvuLbLBlQNWE59KPaEJYFtx81A', 
    #         'HTTPStatusCode': 200, 
    #         'HTTPHeaders': {
    #             'server': 'Werkzeug/3.1.5 Python/3.13.12', 
    #             'date': 'Tue, 17 Feb 2026 04:57:19 GMT', 
    #             'x-amzn-requestid': 'jxArT1pND0L8fPf4H99hCdNZ1WCvuLbLBlQNWE59KPaEJYFtx81A', 
    #             'content-type': 'application/xml', 
    #             'content-length': '619', 
    #             'access-control-allow-origin': '*', 
    #             'connection': 'close'
    #             }, 
    #         'RetryAttempts': 0
    #         }, 
	# 	'Buckets': [
	# 	    {
	# 		    'Name': 'retail-web-assets', 
	# 			'CreationDate': datetime.datetime(2026, 2, 17, 3, 54, 3, tzinfo=tzutc())
	# 		}, 
	# 		{
	# 		    'Name': 'retail-orders-private', 
	# 			'CreationDate': datetime.datetime(2026, 2, 17, 3, 54, 3, tzinfo=tzutc())
	# 		}, 
	# 		{
	# 		    'Name': 'retail-sensitive-public', 
	# 			'CreationDate': datetime.datetime(2026, 2, 17, 3, 54, 3, tzinfo=tzutc())
	# 		}, 
	# 		{
	# 		    'Name': 'retail-security-audit', 
	# 			'CreationDate': datetime.datetime(2026, 2, 17, 3, 54, 3, tzinfo=tzutc())
	# 		}
	# 	], 
	# 	'Owner': {
	# 	    'DisplayName': 'webfile', 
	# 		'ID': 'bcaf1ffd86f41161ca5fb16fd081034f'
	# 		}
	# }

	# Get S3 client configured for AWS/Moto endpoint
	s3 = get_aws_client(service="s3")

	# Build request parameters dynamically so only provided filters are sent
	request_params = {}
	if max_buckets is None and (
		continuation_token is not None or
		prefix is not None or
		bucket_region is not None
	):
		# Align with docs behavior when using filters/pagination hints without explicit max-buckets.
		max_buckets = 10000

	if max_buckets is not None:
		request_params["MaxBuckets"] = max_buckets
	if continuation_token is not None:
		request_params["ContinuationToken"] = continuation_token
	if prefix is not None:
		request_params["Prefix"] = prefix
	if bucket_region is not None:
		request_params["BucketRegion"] = bucket_region

	# List buckets
	try:
		response = s3.list_buckets(**request_params)
		#print(response)
	except ClientError as error:
		error_code = error.response.get("Error", {}).get("Code", "")
		raise RuntimeError(f"Error listing S3 buckets: {error_code}") from error

	# Convert response into JSON-serializable structure for tool usage in chat flows
	buckets = []
	for bucket in response.get("Buckets", []):
		bucket_item = {
			"Name": bucket.get("Name"),
			"CreationDate": (
				bucket.get("CreationDate").isoformat()
				if bucket.get("CreationDate") is not None
				else None
			)
		}
		buckets.append(bucket_item)

	return {
		"Buckets": buckets,
		"Owner": response.get("Owner", {}),
		"Count": len(buckets),
		#"RawResponse": response,
	}

# Function to list objects in a specific S3 bucket (ListObjectsV2)
def list_bucket_objects_v2(
	bucket_name: str,
	continuation_token: str | None = None,
	delimiter: str | None = None,
	encoding_type: str | None = None,
	fetch_owner: bool | None = None,
	max_keys: int | None = None,
	prefix: str | None = None,
	start_after: str | None = None,
	request_payer: str | None = None,
	expected_bucket_owner: str | None = None,
	optional_object_attributes: list[str] | None = None,
) -> dict:
	'''
	List objects in a bucket using ListObjectsV2 and return a JSON-friendly
	response structure for chatbot tool use.

	Parameters:
	- bucket_name (str): Name of the S3 bucket.
	- continuation_token (str, optional): Token for paginated listing.
	- delimiter (str, optional): Delimiter used to group keys (for example '/').
	- encoding_type (str, optional): Response encoding type (for example 'url').
	- fetch_owner (bool, optional): Include owner info in each object entry.
	- max_keys (int, optional): Maximum number of keys to return (up to 1000).
	- prefix (str, optional): Filter keys that begin with this prefix.
	- start_after (str, optional): Start listing after this key.
	- request_payer (str, optional): Request payer value ('requester').
	- expected_bucket_owner (str, optional): Expected AWS account ID of bucket owner.
	- optional_object_attributes (list[str], optional): Optional fields such as
	  ['RestoreStatus'].

	Returns:
	- dict: JSON-friendly ListObjectsV2 response.

	References:
	- https://docs.aws.amazon.com/AmazonS3/latest/API/API_ListObjectsV2.html
	- https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3/client/list_objects_v2.html
	'''

	# Raw response example
	# {
	# 	'ResponseMetadata': {
	# 		'RequestId': 'wn7npXbxKWAf6aQ0CRA8pyEUDpR5cdtQDIY31MWfWIeoGJjRu5jq', 
	# 		'HTTPStatusCode': 200, 
	# 		'HTTPHeaders': {
	# 			'server': 'Werkzeug/3.1.5 Python/3.13.12', 
	# 			'date': 'Tue, 17 Feb 2026 07:27:33 GMT', 
	# 			'x-amzn-requestid': 'wn7npXbxKWAf6aQ0CRA8pyEUDpR5cdtQDIY31MWfWIeoGJjRu5jq', 
	# 			'content-type': 'application/xml', 
	# 			'content-length': '808', 
	# 			'access-control-allow-origin': '*', 
	# 			'connection': 'close'
	# 		}, 
	# 		'RetryAttempts': 0
	# 	}, 
	# 	'IsTruncated': False, 
	# 	'Contents': [
	# 		{
	# 			'Key': 'exports/customer_pii.csv', 
	# 			'LastModified': datetime.datetime(2026, 2, 17, 7, 1, 33, tzinfo=tzutc()), 
	# 			'ETag': '"a81fdedd75c699917eee8c5117e1de04"', 
	# 			'ChecksumAlgorithm': ['CRC32'], 
	# 			'Size': 97, 
	# 			'StorageClass': 'STANDARD'
	# 		}, 
	# 		{
	# 			'Key': 'exports/payment_tokens.json', 
	# 			'LastModified': datetime.datetime(2026, 2, 17, 7, 1, 33, tzinfo=tzutc()), 
	# 			'ETag': '"61897c6197ef52e9e30a3eb6042c9e0d"', 
	# 			'ChecksumAlgorithm': ['CRC32'], 
	# 			'Size': 96, 
	# 			'StorageClass': 'STANDARD'
	# 		}
	# 	], 
	# 	'Name': 'retail-sensitive-public', 
	# 	'Prefix': '', 
	# 	'MaxKeys': 1000, 
	# 	'EncodingType': 'url', 
	# 	'KeyCount': 2
	# }

	# Validate required parameter
	if not bucket_name:
		raise ValueError("bucket_name is required")

	# Get S3 client configured for AWS/Moto endpoint
	s3 = get_aws_client(service="s3")

	# Build request parameters dynamically so optional fields are only sent when provided
	request_params = {
		"Bucket": bucket_name,
	}
	if continuation_token is not None:
		request_params["ContinuationToken"] = continuation_token
	if delimiter is not None:
		request_params["Delimiter"] = delimiter
	if encoding_type is not None:
		request_params["EncodingType"] = encoding_type
	if fetch_owner is not None:
		request_params["FetchOwner"] = fetch_owner
	if max_keys is not None:
		request_params["MaxKeys"] = max_keys
	if prefix is not None:
		request_params["Prefix"] = prefix
	if start_after is not None:
		request_params["StartAfter"] = start_after
	if request_payer is not None:
		request_params["RequestPayer"] = request_payer
	if expected_bucket_owner is not None:
		request_params["ExpectedBucketOwner"] = expected_bucket_owner
	if optional_object_attributes is not None:
		request_params["OptionalObjectAttributes"] = optional_object_attributes

	# List objects in bucket
	try:
		response = s3.list_objects_v2(**request_params)
		#print(response)
	except ClientError as error:
		error_code = error.response.get("Error", {}).get("Code", "")
		raise RuntimeError(f"Error listing objects for bucket '{bucket_name}': {error_code}") from error

	# Normalize Contents objects to ensure JSON-safe output
	contents = []
	for item in response.get("Contents", []):
		normalized_item = {
			"Key": item.get("Key"),
			"LastModified": (
				item.get("LastModified").isoformat()
				if item.get("LastModified") is not None
				else None
			),
			"ETag": item.get("ETag"),
			"ChecksumAlgorithm": item.get("ChecksumAlgorithm"),
			"Size": item.get("Size"),
			"StorageClass": item.get("StorageClass"),
		}

		owner = item.get("Owner")
		if owner is not None:
			normalized_item["Owner"] = {
				"DisplayName": owner.get("DisplayName"),
				"ID": owner.get("ID"),
			}

		contents.append(normalized_item)

	return {
		"Name": response.get("Name"),
		"Prefix": response.get("Prefix"),
		"MaxKeys": response.get("MaxKeys"),
		"KeyCount": response.get("KeyCount", len(contents)),
		"IsTruncated": response.get("IsTruncated", False),
		"EncodingType": response.get("EncodingType"),
		"Contents": contents,
		#"RawResponse": response,
	}

# Function to get access control list (ACL) for a specific S3 bucket
def get_bucket_acl(bucket_name: str, expected_bucket_owner: str | None = None) -> dict:
	'''
	Get the ACL for a specific S3 bucket from the configured AWS endpoint (Moto in local development).
	This follows the GetBucketAcl v2 response concepts (AccessControlPolicy with Owner and Grants).

	Parameters:
	- bucket_name (str): Name of the S3 bucket.
	- expected_bucket_owner (str, optional): Expected AWS account ID for bucket owner validation.

	Returns:
	- dict: JSON-friendly ACL response including AccessControlPolicy, Owner, and Grants.

	References:
	- https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetBucketAcl.html
	- https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3/client/get_bucket_acl.html
	'''

	# Raw response example

	# {
	# 	'ResponseMetadata': {
	# 		'RequestId': 'E0rscTILyEDJtZgtQLq3RNRTiT13aXLoaY1hvbw2xBOJX3szeeAB', 
	# 		'HTTPStatusCode': 200, 
	# 		'HTTPHeaders': {
	# 			'server': 'Werkzeug/3.1.5 Python/3.13.12', 
	# 			'date': 'Tue, 17 Feb 2026 05:27:32 GMT', 
	# 			'x-amzn-requestid': 'E0rscTILyEDJtZgtQLq3RNRTiT13aXLoaY1hvbw2xBOJX3szeeAB', 
	# 			'content-type': 'application/xml', 
	# 			'content-length': '773', 
	# 			'access-control-allow-origin': '*', 
	# 			'connection': 'close'
	# 			}, 
	# 		'RetryAttempts': 0
	# 	}, 
	# 	'Owner': {
	# 		'DisplayName': 'webfile', 
	# 		'ID': '75aa57f09aa0c8caeab4f8c24e99d10f8e7faeebf76c078efc7c6caea54ba06a'
	# 	}, 
	# 	'Grants': [
	# 		{
	# 			'Grantee': {
	# 				'ID': '75aa57f09aa0c8caeab4f8c24e99d10f8e7faeebf76c078efc7c6caea54ba06a', 
	# 				'Type': 'CanonicalUser'
	# 			}, 
	# 			'Permission': 'FULL_CONTROL'
	# 		}, 
	# 		{
	# 			'Grantee': {
	# 				'Type': 'Group', 
	# 				'URI': 'http://acs.amazonaws.com/groups/global/AllUsers'
	# 			}, 
	# 			'Permission': [<Element '{http://s3.amazonaws.com/doc/2006-03-01/}Permission' at 0x10e59d850>, <Element '{http://s3.amazonaws.com/doc/2006-03-01/}Permission' at 0x10e59dbc0>]
	# 		}
	# 	]
	# }

	# Validate required parameter
	if not bucket_name:
		raise ValueError("bucket_name is required")

	# Get S3 client configured for AWS/Moto endpoint
	s3 = get_aws_client(service="s3")

	# Build request parameters dynamically so optional owner check is only sent when provided
	request_params = {
		"Bucket": bucket_name,
	}
	if expected_bucket_owner is not None:
		request_params["ExpectedBucketOwner"] = expected_bucket_owner

	# Get bucket ACL
	try:
		response = s3.get_bucket_acl(**request_params)
		#print(response)
	except ClientError as error:
		error_code = error.response.get("Error", {}).get("Code", "")
		raise RuntimeError(f"Error getting bucket ACL for '{bucket_name}': {error_code}") from error

	# Normalize owner fields
	owner = response.get("Owner", {})
	normalized_owner = {
		"DisplayName": owner.get("DisplayName"),
		"ID": owner.get("ID"),
	}

	# Normalize grant fields for chatbot/tool consumption
	normalized_grants = []
	for grant in response.get("Grants", []):
		grantee = grant.get("Grantee", {})
		permission = grant.get("Permission")
		if isinstance(permission, list):
			normalized_permission = []
			for permission_item in permission:
				permission_text = getattr(permission_item, "text", None)
				if permission_text is not None:
					normalized_permission.append(permission_text)
				else:
					normalized_permission.append(str(permission_item))
		else:
			normalized_permission = permission

		normalized_grants.append(
			{
				"Grantee": {
					"ID": grantee.get("ID"),
					"Type": grantee.get("Type"),
					"URI": grantee.get("URI"),
				},
				"Permission": normalized_permission,
			}
		)

	return {
		"Bucket": bucket_name,
		"AccessControlPolicy": {
			"Owner": normalized_owner,
			"AccessControlList": {
				"Grants": normalized_grants,
			},
		},
		"GrantsCount": len(normalized_grants),
		#"RawResponse": response,
	}

# Function to get bucket metadata configuration (S3 Metadata v2)
def get_bucket_metadata_configuration(
	bucket_name: str,
	expected_bucket_owner: str | None = None,
) -> dict:
	'''
	Retrieve S3 Metadata configuration for a general purpose bucket.

	Parameters:
	- bucket_name (str): Bucket name.
	- expected_bucket_owner (str, optional): Expected AWS account ID for owner validation.

	Returns:
	- dict: Raw API response for GetBucketMetadataConfiguration.

	References:
	- https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetBucketMetadataConfiguration.html
	'''
	
	# raw resposne example
	# {
	# 	'ResponseMetadata': {
	# 		'RequestId': '9ewfKZ6Ev55sAzWYyZUuTiz5IqGEBfI5L2tDohP3rgR5AZxgJ33f', 
	# 		'HTTPStatusCode': 200, 
	# 		'HTTPHeaders': {
	# 			'server': 'Werkzeug/3.1.5 Python/3.13.12', 
	# 			'date': 'Tue, 17 Feb 2026 06:25:43 GMT', 
	# 			'x-amzn-requestid': '9ewfKZ6Ev55sAzWYyZUuTiz5IqGEBfI5L2tDohP3rgR5AZxgJ33f', 
	# 			'content-type': 'application/xml', 
	# 			'content-length': '893', 
	# 			'access-control-allow-origin': '*', 
	# 			'connection': 'close'
	# 		}, 
	# 		'RetryAttempts': 0
	# 	}, 
	# 	'GetBucketMetadataConfigurationResult': {}
	# }

	# Validate required parameter
	if not bucket_name:
		raise ValueError("bucket_name is required")

	# Get S3 client configured for AWS/Moto endpoint
	s3 = get_aws_client(service="s3")

	# Build request parameters
	request_params = {
		"Bucket": bucket_name,
	}
	if expected_bucket_owner is not None:
		request_params["ExpectedBucketOwner"] = expected_bucket_owner

	# Resolve SDK method dynamically so we can return a clear message if unsupported
	get_metadata_method = getattr(s3, "get_bucket_metadata_configuration", None)
	if get_metadata_method is None:
		raise RuntimeError(
			"get_bucket_metadata_configuration is not available in the current boto3/botocore version"
		)

	try:
		response = get_metadata_method(**request_params)
		#print(response)
	except ClientError as error:
		error_code = error.response.get("Error", {}).get("Code", "")
		raise RuntimeError(
			f"Error getting metadata configuration for bucket '{bucket_name}': {error_code}"
		) from error
	except Exception as error:
		raise RuntimeError(
			"GetBucketMetadataConfiguration is not supported by the current endpoint or SDK"
		) from error

	return {
		"Bucket": bucket_name,
		"GetBucketMetadataConfigurationResult": response.get("MetadataConfigurationResult", {}),
		#"RawResponse": response,
	}

# Function to get bucket policy for a specific S3 bucket
def get_bucket_policy(
	bucket_name: str,
	expected_bucket_owner: str | None = None,
) -> dict:
	'''
	Return the policy of a specified bucket.

	Parameters:
	- bucket_name (str): The bucket name to get the bucket policy for.
	- expected_bucket_owner (str, optional): The expected AWS account ID of the bucket owner.

	Returns:
	- dict: JSON-friendly response including parsed Policy and raw response details.

	References:
	- https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetBucketPolicy.html
	- https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3/client/get_bucket_policy.html
	'''

	# raw response example for bucket with policy

	# {
	# 	'ResponseMetadata': {
	# 		'RequestId': 'W6GeJOCWiIl2PUeOrpSVMvasyqok41WZNGRSZjDixsgzPmudwBH0', 
	# 		'HTTPStatusCode': 200, 
	# 		'HTTPHeaders': {
	# 			'server': 'Werkzeug/3.1.5 Python/3.13.12', 
	# 			'date': 'Tue, 17 Feb 2026 07:01:57 GMT', 
	# 			'x-amzn-requestid': 'W6GeJOCWiIl2PUeOrpSVMvasyqok41WZNGRSZjDixsgzPmudwBH0', 
	# 			'content-type': 'application/xml', 
	# 			'content-length': '218', 
	# 			'access-control-allow-origin': '*', 
	# 			'connection': 'close'
	# 		}, 
	# 		'RetryAttempts': 0
	# 	}, 
	# 	'Policy': '{"Version": "2012-10-17", "Statement": [{"Sid": "AllowPublicReadWriteForTesting", "Effect": "Allow", "Principal": "*", "Action": ["s3:GetObject", "s3:PutObject"], "Resource": "arn:aws:s3:::retail-sensitive-public/*"}]}'
	# }

	# Validate required parameter
	if not bucket_name:
		raise ValueError("bucket_name is required")

	# Get S3 client configured for AWS/Moto endpoint
	s3 = get_aws_client(service="s3")

	# Build request parameters dynamically so optional owner check is only sent when provided
	request_params = {
		"Bucket": bucket_name,
	}
	if expected_bucket_owner is not None:
		request_params["ExpectedBucketOwner"] = expected_bucket_owner

	# Get bucket policy
	try:
		response = s3.get_bucket_policy(**request_params)
		#print(f"response: {response}")
	except ClientError as error:
		error_code = error.response.get("Error", {}).get("Code", "")
		if error_code == "NoSuchBucketPolicy":
			return {
				"Bucket": bucket_name,
				"HasPolicy": False,
				"Policy": None,
				"RawPolicy": None,
			}
		raise RuntimeError(f"Error getting bucket policy for '{bucket_name}': {error_code}") from error

	raw_policy = response.get("Policy")
	try:
		parsed_policy = json.loads(raw_policy) if raw_policy else None
	except (TypeError, json.JSONDecodeError):
		parsed_policy = None

	return {
		"Bucket": bucket_name,
		"HasPolicy": raw_policy is not None,
		"Policy": parsed_policy,
		"RawPolicy": raw_policy,
		#"RawResponse": response,
	}

# Function to get bucket policy status for a specific S3 bucket
def get_bucket_policy_status(
	bucket_name: str,
	expected_bucket_owner: str | None = None,
) -> dict:
	'''
	Retrieve the policy status for an S3 bucket (whether the bucket policy is public).

	Parameters:
	- bucket_name (str): The bucket name to get policy status for.
	- expected_bucket_owner (str, optional): Expected AWS account ID for owner validation.

	Returns:
	- dict: JSON-friendly response including PolicyStatus.IsPublic.

	References:
	- https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetBucketPolicyStatus.html
	- https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3/client/get_bucket_policy_status.html
	'''

	# Validate required parameter
	if not bucket_name:
		raise ValueError("bucket_name is required")

	# Get S3 client configured for AWS/Moto endpoint
	s3 = get_aws_client(service="s3")

	# Build request parameters dynamically so optional owner check is only sent when provided
	request_params = {
		"Bucket": bucket_name,
	}
	if expected_bucket_owner is not None:
		request_params["ExpectedBucketOwner"] = expected_bucket_owner

	# Resolve SDK method dynamically so we can return a clear message if unsupported
	get_policy_status_method = getattr(s3, "get_bucket_policy_status", None)
	if get_policy_status_method is None:
		raise RuntimeError(
			"get_bucket_policy_status is not available in the current boto3/botocore version"
		)

	# Get bucket policy status
	try:
		response = get_policy_status_method(**request_params)
	except ClientError as error:
		error_code = error.response.get("Error", {}).get("Code", "")
		if error_code == "NoSuchBucketPolicy":
			return {
				"Bucket": bucket_name,
				"PolicyStatus": {
					"IsPublic": False,
				},
			}
		raise RuntimeError(f"Error getting bucket policy status for '{bucket_name}': {error_code}") from error
	except Exception as error:
		raise RuntimeError(
			"GetBucketPolicyStatus is not supported by the current endpoint or SDK"
		) from error

	policy_status = response.get("PolicyStatus", {})
	return {
		"Bucket": bucket_name,
		"PolicyStatus": {
			"IsPublic": bool(policy_status.get("IsPublic", False)),
		},
		#"RawResponse": response,
	}

# Function to describe all EC2 instances in the configured AWS account/endpoint
def describe_instances(
	instance_ids: list[str] | None = None,
	filters: list[dict] | None = None,
	dry_run: bool | None = None,
	max_results: int | None = None,
	next_token: str | None = None,
) -> dict:
	'''
	Describe EC2 instances from the configured AWS endpoint (Moto in local development).

	Parameters:
	- instance_ids (list[str], optional): Specific instance IDs to describe.
	- filters (list[dict], optional): EC2 filters in boto3 format, for example
	  [{"Name": "instance-state-name", "Values": ["running"]}].

	  Other filters include but are not limited to:
	  - dns-name - The public DNS name of the instance.
	  - private-dns-name - The private IPv4 DNS name of the instance.
	  - image-id - The ID of the image used to launch the instance.
	  - instance-type - The type of instance (for example, t2.micro).
	  - network-interface.private-dns-name - The private DNS name of the network interface.
	  - ip-address - The public IPv4 address of the instance.
	  - network-interface.addresses.private-ip-address - The private IPv4 address associated with the network interface.
	  - network-interface.private-ip-address - The private IPv4 address.
	  - network-interface.public-dns-name - The public DNS name.

	- dry_run (bool, optional): Checks permissions without making the request.
	- max_results (int, optional): Maximum number of items to return.
	- next_token (str, optional): Token from a previous paginated request.

	Returns:
	- dict: JSON-friendly response including Reservations and NextToken.

	References:
	- https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_DescribeInstances.html
	- https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2/client/describe_instances.html
	'''

	# Raw response example
	# {
	# 	'Reservations': [
	# 		{
	# 			'ReservationId': 'r-713861cf95a664d8a', 
	# 			'OwnerId': '123456789012', 
	# 			'Groups': [], 
	# 			'Instances': [
	# 				{
	# 					'Architecture': 'x86_64', 
	# 					'BlockDeviceMappings': [
	# 						{
	# 							'DeviceName': '/dev/sda1', 
	# 							'Ebs': {
	# 								'AttachTime': datetime.datetime(2026, 2, 17, 7, 1, 33, tzinfo=tzutc()), 
	# 								'DeleteOnTermination': True, 
	# 								'Status': 'attached', 
	# 								'VolumeId': 'vol-7d95070beab64e9b5'
	# 							}
	# 						}
	# 					], 
	# 					'ClientToken': '2e2ea4c5-c91a-45e2-bcea-fa74a2f3c99b', 
	# 					'EbsOptimized': False, 
	# 					'Hypervisor': 'xen', 
	# 					'NetworkInterfaces': [
	# 						{
	# 							'Association': {}, 
	# 							'Attachment': {
	# 								'AttachTime': datetime.datetime(2026, 2, 17, 7, 1, 33, tzinfo=tzutc()), 
	# 								'AttachmentId': 'eni-attach-8bf4d9f61ec4346c4', 
	# 								'DeleteOnTermination': False, 
	# 								'DeviceIndex': 0, 
	# 								'Status': 'attached', 
	# 								'NetworkCardIndex': 0
	# 							}, 
	# 							'Description': 'Primary network interface', 
	# 							'Groups': [
	# 								{
	# 									'GroupId': 'sg-50839e06eb2c31862', 
	# 									'GroupName': 'retail-web-sg'
	# 								}
	# 							], 
	# 							'Ipv6Addresses': [], 
	# 							'MacAddress': '02:00:00:5002x:22702x:21202x', 
	# 							'NetworkInterfaceId': 'eni-7eafaba2c51205b68', 
	# 							'OwnerId': '123456789012', 
	# 							'PrivateIpAddress': '10.42.10.10', 
	# 							'PrivateIpAddresses': [
	# 								{
	# 									'Primary': True, 
	# 									'PrivateIpAddress': '10.42.10.10'
	# 								}
	# 							], 
	# 							'SourceDestCheck': True, 
	# 							'Status': 'in-use', 
	# 							'SubnetId': 'subnet-1a1eb022b8e3d5b2d', 
	# 							'VpcId': 'vpc-3a110a921317abd34', 
	# 							'InterfaceType': 'interface'
	# 						}
	# 					], 
	# 					'RootDeviceName': '/dev/sda1', 
	# 					'RootDeviceType': 'ebs', 
	# 					'SecurityGroups': [
	# 						{
	# 							'GroupId': 'sg-50839e06eb2c31862', 
	# 							'GroupName': 'retail-web-sg'
	# 						}
	# 					], 
	# 					'SourceDestCheck': True, 
	# 					'SriovNetSupport': 'simple', 
	# 					'StateReason': {
	# 						'Code': '', 
	# 						'Message': ''
	# 					}, 
	# 					'VirtualizationType': 'paravirtual', 
	# 					'HibernationOptions': {}, 
	# 					'MetadataOptions': {
	# 						'State': 'applied', 
	# 						'HttpTokens': 'optional', 
	# 						'HttpPutResponseHopLimit': 1, 
	# 						'HttpEndpoint': 'enabled', 
	# 						'HttpProtocolIpv6': 'disabled', 
	# 						'InstanceMetadataTags': 'disabled'
	# 					}, 
	# 					'InstanceId': 'i-aab816317a8471f01', 
	# 					'ImageId': 'ami-0c55b159cbfafe1f0', 
	# 					'State': {
	# 						'Code': 16, 
	# 						'Name': 'running'
	# 					}, 
	# 					'PrivateDnsName': 'ip-10-42-10-10.ec2.internal', 
	# 					'StateTransitionReason': '', 
	# 					'KeyName': 'retail-challenge-key', 
	# 					'AmiLaunchIndex': 0, 
	# 					'ProductCodes': [], 
	# 					'InstanceType': 't3.micro', 
	# 					'LaunchTime': datetime.datetime(2026, 2, 17, 7, 1, 33, tzinfo=tzutc()), 
	# 					'Placement': {
	# 						'GroupName': '', 
	# 						'Tenancy': 'default', 
	# 						'AvailabilityZone': 'us-east-1f'
	# 					}, 
	# 					'KernelId': 'None', 
	# 					'Monitoring': {
	# 						'State': 'disabled'
	# 					}, 
	# 					'SubnetId': 'subnet-1a1eb022b8e3d5b2d', 
	# 					'VpcId': 'vpc-3a110a921317abd34', 
	# 					'PrivateIpAddress': '10.42.10.10'
	# 				}
	# 			]
	# 		}, 
	# 		{
	# 			'ReservationId': 'r-1ac81.......
	# 		}
	# 	], 
	# 	'ResponseMetadata': {
	# 		'RequestId': 'request-id', 
	# 		'HTTPStatusCode': 200, 
	# 		'HTTPHeaders': {
	# 			'server': 'Werkzeug/3.1.5 Python/3.13.12, amazon.com', 
	# 			'date': 'Tue, 17 Feb 2026 13:35:42 GMT', 
	# 			'content-type': 'text/xml', 
	# 			'x-amzn-requestid': '8djoBRubSA62Fs2t8pYSUnUQttKtuyMBTT73pNH0hNyTFLUwWtW7', 
	# 			'content-length': '6123', 
	# 			'access-control-allow-origin': '*', 
	# 			'connection': 'close'
	# 		}, 
	# 		'RetryAttempts': 0
	# 	}
	# }

	# Validate incompatible parameters based on API contract
	if instance_ids is not None and max_results is not None:
		raise ValueError("instance_ids and max_results cannot be used together")

	# Get EC2 client configured for AWS/Moto endpoint
	ec2 = get_aws_client(service="ec2")

	# Build request parameters dynamically so only provided filters are sent
	request_params = {}
	if instance_ids is not None:
		request_params["InstanceIds"] = instance_ids
	if filters is not None:
		request_params["Filters"] = filters
	if dry_run is not None:
		request_params["DryRun"] = dry_run
	if max_results is not None:
		request_params["MaxResults"] = max_results
	if next_token is not None:
		request_params["NextToken"] = next_token

	# Describe EC2 instances
	try:
		response = ec2.describe_instances(**request_params)
		#print(response)
	except ClientError as error:
		error_code = error.response.get("Error", {}).get("Code", "")
		raise RuntimeError(f"Error describing EC2 instances: {error_code}") from error

	# Convert datetime-like fields recursively so output is JSON-serializable
	def _json_safe(value):
		if isinstance(value, dict):
			return {key: _json_safe(item) for key, item in value.items()}
		if isinstance(value, list):
			return [_json_safe(item) for item in value]
		if hasattr(value, "isoformat"):
			try:
				return value.isoformat()
			except TypeError:
				return value
		return value

	normalized_reservations = _json_safe(response.get("Reservations", []))

	instance_count = 0
	for reservation in normalized_reservations:
		instance_count += len(reservation.get("Instances", []))

	return {
		"Reservations": normalized_reservations,
		"ReservationsCount": len(normalized_reservations),
		"InstancesCount": instance_count,
		"NextToken": response.get("NextToken"),
		#"RawResponse": response,
	}

# Function to describe Instance Types
def describe_instance_types(
	instance_types: list[str] | None = None,
	filters: list[dict] | None = None,
	dry_run: bool | None = None,
	max_results: int | None = None,
	next_token: str | None = None,
) -> dict:
	'''
	Describe EC2 instance types from the configured AWS endpoint (Moto in local development).

	Parameters:
	- instance_types (list[str], optional): Specific instance type names to describe.
	- filters (list[dict], optional): EC2 filters in boto3 format, for example
	  [{"Name": "instance-type", "Values": ["t3.micro", "t3.small"]}].
	- dry_run (bool, optional): Checks permissions without making the request.
	- max_results (int, optional): Maximum number of items to return (5-100).
	- next_token (str, optional): Token from a previous paginated request.

	Returns:
	- dict: JSON-friendly response including InstanceTypes and NextToken.

	References:
	- https://docs.aws.amazon.com/AWSEC2/latest/APIReference/API_DescribeInstanceTypes.html
	- https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2/client/describe_instance_types.html
	'''

	# Get EC2 client configured for AWS/Moto endpoint
	ec2 = get_aws_client(service="ec2")

	# Build request parameters dynamically so only provided filters are sent
	request_params = {}
	if instance_types is not None:
		request_params["InstanceTypes"] = instance_types
	if filters is not None:
		request_params["Filters"] = filters
	if dry_run is not None:
		request_params["DryRun"] = dry_run
	if max_results is not None:
		request_params["MaxResults"] = max_results
	if next_token is not None:
		request_params["NextToken"] = next_token

	# Describe EC2 instance types
	try:
		response = ec2.describe_instance_types(**request_params)
		#print(response)
	except ClientError as error:
		error_code = error.response.get("Error", {}).get("Code", "")
		raise RuntimeError(f"Error describing EC2 instance types: {error_code}") from error

	# Convert datetime-like fields recursively so output is JSON-serializable
	def _json_safe(value):
		if isinstance(value, dict):
			return {key: _json_safe(item) for key, item in value.items()}
		if isinstance(value, list):
			return [_json_safe(item) for item in value]
		if hasattr(value, "isoformat"):
			try:
				return value.isoformat()
			except TypeError:
				return value
		return value

	normalized_instance_types = _json_safe(response.get("InstanceTypes", []))

	return {
		"InstanceTypes": normalized_instance_types,
		"InstanceTypesCount": len(normalized_instance_types),
		"NextToken": response.get("NextToken"),
		#"RawResponse": response,
	}

