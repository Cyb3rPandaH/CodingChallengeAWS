'''
This module defines the AWS client configuration for the organization chatbot application. 
It includes a function to create a baseline client configuration that can be used across different AWS services. 
The configuration parameters are loaded from environment variables, allowing for flexibility and customization without modifying the code.
'''

# Import necessary libraries
from botocore.config import Config

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def _get_env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return int(value)

# Define client-specific config. Reference: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html
def get_baseline_client_config() -> Config:
    '''
    Function to define client-specific config for AWS clients. This function can be extended to include additional configuration parameters as needed.

    Returns:
        baseline_client_config (Config): A botocore Config object with the specified configuration parameters.
    '''
    # Define config
    try:
        baseline_client_config = Config(
            region_name=os.getenv("AWS_REGION", "us-east-1"), # N. Virginia. Reference: https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Concepts.RegionsAndAvailabilityZones.html
            retries={
                'total_max_attempts': _get_env_int("TOTAL_MAX_ATTEMPTS", 4), # If not provided, it will default to the value specified in the service model, typically 4.
                'mode': os.getenv("RETRY_MODE", "standard")
            },
            connect_timeout=_get_env_int("CONNECT_TIMEOUT", 60), # in seconds. Default is 60
            read_timeout=_get_env_int("READ_TIMEOUT", 60), # in seconds. Default is 60
            max_pool_connections=_get_env_int("MAX_POOL_CONN", 10) # Dafault is 10
        )
    except Exception as e:
        print(f"Error creating baseline client config: {e}")
        raise

    return baseline_client_config