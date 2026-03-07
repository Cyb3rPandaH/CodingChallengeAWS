'''
AWS Client Wrapper. This module provides a wrapper around the boto3 client to create AWS clients with a baseline configuration. 
The configuration parameters are defined in the aws_config module and can be customized using environment variables.
'''

# Import necessary libraries
import boto3
from botocore.client import BaseClient

import os
from dotenv import load_dotenv

try:
    from .aws_config import get_baseline_client_config
except ImportError:
    from aws_config import get_baseline_client_config

# Load environment variables from .env file
load_dotenv()

# Define an AWS client wrapper. Reference: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/core/session.html
def get_aws_client(service: str) -> BaseClient:
    '''
    Get an AWS client for the specified service.

    Parameters:
        service (str): The name of the AWS service for which to create a client (e.g., 's3', 'dynamodb', etc.).
    
    Returns:
        client: A boto3 client object for the specified AWS service, configured with the baseline client configuration.
    '''
    # Define client
    try: 
        client = boto3.client(
            service_name=service, 
            endpoint_url=os.getenv("ENDPOINT_URL") or None,
            config=get_baseline_client_config()
        )
    except Exception as e:
        print(f"Error creating AWS client for service {service}: {e}")
        raise

    return client