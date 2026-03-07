'''
Chatbot module for coding challenge. This module defines the main chatbot class and its interactions with AWS services.

References:
- https://dev.to/sreeni5018/building-a-simple-conversational-chatbot-llm-application-with-langchain-4f8h
- https://docs.langchain.com/oss/python/integrations/chat/openai
- https://docs.langchain.com/oss/python/langchain/tools#customize-tool-properties
'''

# import necessary libraries
import json
import os
from typing import Any
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

from the_organization_chatbot.domain.aws_raw_tools import list_s3_buckets, list_bucket_objects_v2, get_bucket_acl, get_bucket_metadata_configuration, get_bucket_policy, get_bucket_policy_status, describe_instances, describe_instance_types 
from the_organization_chatbot.infrastructure.tracing import PostgresConversationTracer


# Load environment variables from .env file
load_dotenv()

# Define tools
@tool
def list_s3_buckets_tool() -> dict:
    '''
    Tool function to list S3 buckets in the AWS account. 
    This function can be called by the chatbot when it needs to provide information about the S3 buckets available for an AWS account.

    Returns:
        A dictionary containing the list of S3 buckets and related information.
        The dictionary includes the following keys:
        - "Buckets": A list of dictionaries, each containing information about a bucket.
            - "Name": The name of the bucket.
            - "CreationDate": The date and time when the bucket was created.
        - "Owner": A dict containing information about the owner of the buckets.
        - "Count": The total number of buckets.
    '''
    # Call the list_s3_buckets function from aws_raw_tools to get the list of S3 buckets
    return list_s3_buckets()

@tool
def list_bucket_objects_tool(bucket_name: str) -> dict:
    '''
    Tool function to list objects in a specific S3 bucket. 
    This function can be called by the chatbot when it needs to provide information about the objects within a specific S3 bucket.

    Parameters:
        bucket_name (str): The name of the S3 bucket for which to list objects. 
    Returns:
        A dictionary containing the list of objects in the specified S3 bucket and related information.
        The dictionary includes the following keys:
        - "Name": The name of the bucket.
        - "KeyCount": The total number of objects in the bucket.
        - "Contents": A list of dictionaries, each containing information about an object in the bucket.
            - "Key": The key (name) of the object. It includes the full path of the object within the bucket.
            - "LastModified": The date and time when the object was last modified.
            - "ETag": The ETag of the object, which is a hash of the object's content.
            - "ChecksumAlgorithm": The algorithm used to calculate the checksum of the object.
            - "Size": The size of the object in bytes.
            - "StorageClass": The storage class of the object (e.g., STANDARD, GLACIER, etc.).
    '''
    # Call the list_bucket_objects function from aws_raw_tools to get the list of objects in the specified S3 bucket
    return list_bucket_objects_v2(bucket_name=bucket_name)

@tool
def get_bucket_acl_tool(bucket_name: str) -> dict:
    '''
    Tool function to get the access control list (ACL) for a specific S3 bucket. 
    This function can be called by the chatbot when it needs to provide information about the permissions and access control settings of a specific S3 bucket.

    Parameters:
        bucket_name (str): The name of the S3 bucket for which to get the ACL. 
    Returns:
        A dictionary containing the ACL information for the specified S3 bucket.
        The dictionary includes the following keys:
        - "Bucket": The name of the bucket.
        - "AccessControlList": A list of dictionaries, each containing information about a grant in the ACL.
            - "Grantee": A dictionary containing information about the grantee of the permission.
                - "ID": Grantee ID (if the grantee is an AWS account).
                -"Type": The type of grantee (e.g., "CanonicalUser", "Group", etc.).
                - "URI": The URI of the grantee (if the grantee is a group).
            - "Permission": List of permissions granted (e.g., "READ", "WRITE", etc.).
        - "GrantCount": The total number of grants in the ACL.
    '''
    # Call the get_bucket_acl function from aws_raw_tools to get the ACL for the specified S3 bucket
    return get_bucket_acl(bucket_name=bucket_name)

@tool
def get_bucket_metadata_configuration_tool(bucket_name: str) -> dict:
    '''
    Tool function to get the metadata configuration for a specific general purpose S3 bucket. 
    This function can be called by the chatbot when it needs to provide information about the metadata settings of a specific S3 bucket.

    Parameters:
        bucket_name (str): The name of the S3 bucket for which to get the metadata configuration. 
    Returns:
        A dictionary containing the metadata configuration for the specified S3 bucket.
        The dictionary includes the following keys:
        - "Bucket": The name of the bucket.
        - "GetBucketMetadataConfigurationResult": A dictionary containing the metadata configuration settings for the bucket.
    '''
    # Call the get_bucket_metadata_configuration function from aws_raw_tools to get the metadata configuration for the specified S3 bucket
    return get_bucket_metadata_configuration(bucket_name=bucket_name)

@tool
def get_bucket_policy_tool(bucket_name: str) -> dict:
    '''
    Tool function to get the bucket policy for a specific S3 bucket. 
    This function can be called by the chatbot when it needs to provide information about the bucket policy of a specific S3 bucket.

    Parameters:
        bucket_name (str): The name of the S3 bucket for which to get the bucket policy. 
    Returns:
        A dictionary containing the bucket policy for the specified S3 bucket.
        The dictionary includes the following keys:
        - "Bucket": The name of the bucket.
        - "HasPolicy": A boolean indicating whether the bucket has a policy attached or not.
        - "Policy": A dictionary containing the bucket policy settings for the bucket.
            - "Version": The version of the bucket policy.
            - "Statement": A list of dictionaries, each containing information about a statement in the bucket policy.
                - "Sid": The statement ID (if provided).
                - "Effect": The effect of the statement (e.g., "Allow", "Deny", etc.).
                - "Principal": A dictionary containing information about the principal to which the statement applies.
                - "Action": List of actions that are allowed or denied by the statement (e.g., "s3:GetObject", "s3:PutObject", etc.).
                - "Resource": Resource to which the statement applies (e.g., "arn:aws:s3:::example-bucket/*").
    '''
    # Call the get_bucket_policy function from aws_raw_tools to get the bucket policy for the specified S3 bucket
    return get_bucket_policy(bucket_name=bucket_name)

@tool
def get_bucket_policy_status_tool(bucket_name: str) -> dict:
    '''
    Tool function to get the bucket policy status for a specific S3 bucket. 
    This function can be called by the chatbot when it needs to provide information about the bucket policy status of a specific S3 bucket.

    Parameters:
        bucket_name (str): The name of the S3 bucket for which to get the bucket policy status. 
    Returns:
        A dictionary containing the bucket policy status for the specified S3 bucket.
        The dictionary includes the following keys:
        - "Bucket": The name of the bucket.
        - "PolicyStatus": A dictionary containing the bucket policy status for the bucket.
            - "IsPublic": A boolean indicating whether the bucket is public or not based on its bucket policy.
    '''
    # Call the get_bucket_policy_status function from aws_raw_tools to get the bucket policy status for the specified S3 bucket
    return get_bucket_policy_status(bucket_name=bucket_name)

@tool
def describe_instances_tool(instance_ids=None, filters=None) -> dict:
    '''
    Tool function to describe EC2 instances in the AWS account. 
    This function can be called by the chatbot when it needs to provide information about the EC2 instances available for an AWS account.
    All the parameters defined for the describe_instances function in aws_raw_tools are optional, so this tool does not require any parameters. 
    
    Optional Parameters:      
      - instance_ids: A list of EC2 instance IDs to describe. If not provided, all instances will be described.
      - filters: A list of dictionaries specifying the filters to apply when describing instances. Each dictionary should contain a "Name" key and a "Values" key.
        For example: [{"Name": "instance-state-name", "Values": ["running"]}]
            Filters are very important because they allow to narrow down the results and get information about specific instances based on criteria such as:
                - dns-name - The public DNS name of the instance.
                - private-dns-name - The private IPv4 DNS name of the instance.
                - image-id - The ID of the image used to launch the instance.
                - instance-type - The type of instance (for example, t2.micro).
                - private-dns-name - The private DNS name of the instance.
                - ip-address - The public IPv4 address of the instance.
                - private-ip-address - The private IPv4 address associated with the instance.
                - public-dns-name - The public DNS name.

    Returns:
        A dictionary containing the list of EC2 instances and related information.
        The dictionary includes the following keys:
        - "Reservations": A list of dictionaries, each containing information about a reservation.
            - "ReservationId": The ID of the reservation.
            - "OwnerId": The ID of the owner of the reservation.
            - "Instances": A list of dictionaries, each containing information about an EC2 instance.
                - "Architecture": The architecture of the instance (e.g., "x86_64", "arm64", etc.).
                - "BlockDeviceMappings": A list of dictionaries, each containing information about a block device mapping for the instance.
                - "ClientToken": The client token used when launching the instance.
                - "EbsOptimized": A boolean indicating whether the instance is EBS-optimized or not.
                - "Hypervisor": The hypervisor type of the instance (e.g.,
                - "NetworkInterfaces": A list of dictionaries, each containing information about a network interface attached to the instance.
                - "RootDeviceName": The name of the root device for the instance.
                - "RootDeviceType": The type of root device for the instance (e.g., "ebs", "instance-store", etc.).
                - "SecurityGroups": A list of dictionaries containing information about the security groups associated with the instance.
                - "InstanceId": The ID of the instance.
                - "ImageId": The ID of the image used to launch the instance.
                - "State": A dictionary containing information about the state of the instance.
                - "InstanceType": The type of instance (e.g., "t2.micro").
                - "SubnetId": The ID of the subnet in which the instance is running.
                - "VpcId": The ID of the VPC in which the instance is running.
                - "PromivateIpAddress": The private IPv4 address of the instance.
                - "KeyName": The name of the key pair used to launch the instance.
        - "ReservationsCount": The total number of reservations returned by the describe_instances call.
        - "InstancesCount": The total number of instances returned by the describe_instances call.
    '''
    # Call the describe_instances function from aws_raw_tools to get the list of EC2 instances
    return describe_instances(instance_ids=instance_ids, filters=filters)

@tool
def describe_instance_types_tool(instance_type_names=None, filters=None) -> dict:
    '''
    Tool function to describe EC2 instance types available in the AWS account. 
    This function can be called by the chatbot when it needs to provide information about the EC2 instance types available for an AWS account.
    All the parameters defined for the describe_instance_types function in aws_raw_tools are optional, so this tool does not require any parameters. 
    
    Optional Parameters:      
      - instance_type_names: A list of EC2 instance type names to describe. If not provided, all instance types will be described.
      - filters: A list of dictionaries specifying the filters to apply when describing instance types. Each dictionary should contain a "Name" key and a "Values" key.
        For example: [{"Name": "instance-type", "Values": ["t3.micro", "t3.small"]}].

    Returns:
        A dictionary containing the list of EC2 instance types and related information.
        The dictionary includes the following keys:
        - "InstanceTypes": A list of dictionaries, each containing information about an EC2 instance type.
            - "InstanceType": The name of the instance type (e.g., "t2.micro").
            - "ProcessorInfo": A dictionary containing information about the processor of the instance type.
            - "MemoryInfo": A dictionary containing information about the memory of the instance type.
            - "NetworkInfo": A dictionary containing information about the network performance of the instance type.
        - "InstanceTypesCount": The total number of instance types returned by the describe_instance_types call.
    '''
    # Call the describe_instance_types function from aws_raw_tools to get the list of EC2 instance types
    return describe_instance_types(instance_type_names=instance_type_names, filters=filters)

# Define the chatbot class
class TheOrganizationChatbot:
    def __init__(
        self,
        model: str | None = None,
        temperature: float | None = None,
        trace_id: str | None = None,
        tracer: PostgresConversationTracer | None = None,
    ):

        resolved_model = model or os.getenv("OPENAI_MODEL", "gpt-5-mini")

        resolved_api_key = os.getenv("OPENAI_API_KEY")
        if not resolved_api_key:
            raise ValueError("OPENAI_API_KEY is required")

        resolved_temperature = temperature if temperature is not None else float(os.getenv("TEMPERATURE", 0.0))

        self.trace_id = trace_id
        self.tracer = tracer
        self.model_name = resolved_model
        self.last_generation_stats = {
            "llm_rounds": 0,
            "tool_rounds": 0,
            "unique_tools_executed": [],
        }

        max_tool_rounds_env = os.getenv("MAX_TOOL_ROUNDS", "5")
        try:
            self.max_tool_rounds = max(1, int(max_tool_rounds_env))
        except ValueError:
            self.max_tool_rounds = 5

        # Initialize the ChatOpenAI instance with the specified model and base URL
        self.chat = ChatOpenAI(
            model=resolved_model,
            temperature=resolved_temperature,
            api_key=resolved_api_key,
            stream_usage=True,
        ).bind_tools(tools=[list_s3_buckets_tool,
                            list_bucket_objects_tool,
                            get_bucket_acl_tool,
                            get_bucket_metadata_configuration_tool,
                            get_bucket_policy_tool,
                            get_bucket_policy_status_tool,
                            describe_instances_tool,
                            describe_instance_types_tool])
        
        # Load the system prompt for the chatbot
        self.system_prompt = self._load_system_prompt()

    def _trace(self, event_type: str, payload: dict[str, Any]) -> None:
        # Tracing captures user input, prepared prompt context, model outputs, requested tools, tool results, and final assistant output.
        if self.tracer is None:
            return

        trace_payload = dict(payload)
        trace_payload["trace_id"] = self.trace_id
        self.tracer.log_event(event_type=event_type, payload=trace_payload)

    def _load_system_prompt(self) -> str:
        prompt_path = os.path.join(os.path.dirname(__file__), "chatbot_system_prompt.md")
        try:
            with open(prompt_path, "r", encoding="utf-8") as prompt_file:
                return prompt_file.read().strip()
        except FileNotFoundError:
            return "You are a helpful assistant that provides information about the context of an AWS account."

    def generate_response(self, user_input: str) -> str:
        '''
        Generate a response from the chatbot based on user input.

        Parameters:
            user_input (str): The input message from the user.
        Returns:
            response (str): The generated response from the chatbot.
        '''
        # Define the prompt template for the chatbot
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human", "{user_input}")
        ])

        # Reset per-turn diagnostics used by evaluation reporting.
        llm_rounds = 0
        tool_round = 0
        executed_tools = set()

        # Trace the exact user message received for this turn.
        self._trace(
            event_type="user_input",
            payload={
                "user_input": user_input,
            },
        )

        # Trace the prepared prompt context sent to the model.
        self._trace(
            event_type="prompt_prepared",
            payload={
                "system_prompt": self.system_prompt,
                "user_input": user_input,
            },
        )

        messages = prompt.format_messages(user_input=user_input)
        response = self.chat.invoke(messages)
        llm_rounds += 1

        # Trace the model's first response before any tool execution.
        self._trace(
            event_type="model_response_initial",
            payload={
                "model": self.model_name,
                "content": getattr(response, "content", None),
                "tool_calls": getattr(response, "tool_calls", None),
            },
        )

        tool_map = {
            list_s3_buckets_tool.name: list_s3_buckets_tool,
            list_bucket_objects_tool.name: list_bucket_objects_tool,
            get_bucket_acl_tool.name: get_bucket_acl_tool,
            get_bucket_metadata_configuration_tool.name: get_bucket_metadata_configuration_tool,
            get_bucket_policy_tool.name: get_bucket_policy_tool,
            get_bucket_policy_status_tool.name: get_bucket_policy_status_tool,
            describe_instances_tool.name: describe_instances_tool,
            describe_instance_types_tool.name: describe_instance_types_tool,
        }

        while getattr(response, "tool_calls", None) and tool_round < self.max_tool_rounds:
            tool_round += 1
            tool_messages = []

            for tool_call in response.tool_calls:
                tool_name = tool_call.get("name")
                tool_args = tool_call.get("args", {})
                selected_tool = tool_map.get(tool_name)

                # Trace which tool the model requested and with what arguments.
                self._trace(
                    event_type="tool_call_requested",
                    payload={
                        "tool_round": tool_round,
                        "tool_name": tool_name,
                        "tool_args": tool_args,
                        "tool_call_id": tool_call.get("id", ""),
                    },
                )

                if selected_tool is None:
                    tool_result = {"error": f"Unknown tool requested: {tool_name}"}
                else:
                    try:
                        tool_result = selected_tool.invoke(tool_args)
                        executed_tools.add(tool_name)
                    except Exception as error:
                        tool_result = {"error": str(error)}

                # Trace the tool execution result returned to the model.
                self._trace(
                    event_type="tool_call_result",
                    payload={
                        "tool_round": tool_round,
                        "tool_name": tool_name,
                        "tool_call_id": tool_call.get("id", ""),
                        "tool_result": tool_result,
                    },
                )

                tool_messages.append(
                    ToolMessage(
                        content=json.dumps(tool_result, default=str),
                        tool_call_id=tool_call.get("id", ""),
                    )
                )

            messages = messages + [response] + tool_messages
            response = self.chat.invoke(messages)
            llm_rounds += 1

            # Trace the model response after receiving tool outputs.
            self._trace(
                event_type="model_response_after_tools",
                payload={
                    "tool_round": tool_round,
                    "model": self.model_name,
                    "content": getattr(response, "content", None),
                    "tool_calls": getattr(response, "tool_calls", None),
                },
            )

        # Trace the final assistant output returned to the terminal.
        self._trace(
            event_type="assistant_output",
            payload={
                "content": getattr(response, "content", None),
            },
        )

        self.last_generation_stats = {
            "llm_rounds": llm_rounds,
            "tool_rounds": tool_round,
            "unique_tools_executed": sorted(executed_tools),
        }

        return response