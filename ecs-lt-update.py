import boto3
import json
import os
import argparse
from os import environ

# https://docs.aws.amazon.com/AmazonECS/latest/developerguide/retrieve-ecs-optimized_AMI.html#ecs-optimized-ami-parameter-format

# Default configuration values
DEFAULT_ECS_PARAMETER = "/aws/service/ecs/optimized-ami/amazon-linux-2023/recommended"
DEFAULT_EC2_PARAMETER = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-6.1-x86_64"
DEFAULT_LT_NAME = "bys-dev-lt-ecs-main"

def parse_args():
    parser = argparse.ArgumentParser(description='Update Launch Template with latest AMI')
    parser.add_argument('--parameter', '-p', 
                        help='SSM Parameter path for AMI (default: from env var or ECS optimized AMI)')
    parser.add_argument('--launch-template', '-lt',
                        help='Launch Template name (default: from env var or bys-dev-lt-ecs-main)')
    parser.add_argument('--ami-type', '-t', choices=['ecs', 'ec2'], default='ecs',
                        help='AMI type: ecs (ECS optimized) or ec2 (standard AL2023)')
    args = parser.parse_args()
    
    # Get parameter name from args, env var, or default
    parameter_name = args.parameter
    if not parameter_name:
        parameter_name = environ.get('AMI_PARAMETER')
    if not parameter_name:
        if args.ami_type == 'ec2':
            parameter_name = DEFAULT_EC2_PARAMETER
        else:
            parameter_name = DEFAULT_ECS_PARAMETER
    
    # Get launch template name from args, env var, or default
    lt_name = args.launch_template
    if not lt_name:
        lt_name = environ.get('LAUNCH_TEMPLATE_NAME', DEFAULT_LT_NAME)
    
    return parameter_name, lt_name

ssm_client = boto3.client("ssm")
ec2_client = boto3.client("ec2")

## GET the parameter value from parameter store ecs
def get_parameter_value(parameter_name):
    try:
        response = ssm_client.get_parameter(
            Name=parameter_name,
            WithDecryption=True
        )
        return json.loads(response["Parameter"]["Value"])
    except Exception as e:
        print(f"Error: {e}")
        raise e # re-raise the exception
   
def get_lt_info(lt_name):
    try:
        default_launch_template_info = ec2_client.describe_launch_template_versions(
            LaunchTemplateName=lt_name,
            Versions=['$Default']
        )
        return default_launch_template_info
    except Exception as e:
        print(f"Error: {e}")
        raise e # re-raise the exception
      
def update_lt_ami(default_launch_template_info, parameter_value):
  
  old_lt_version = default_launch_template_info["LaunchTemplateVersions"][0]["VersionNumber"]
  old_lt_id = default_launch_template_info["LaunchTemplateVersions"][0]["LaunchTemplateId"]
  old_lt_ami_id = default_launch_template_info["LaunchTemplateVersions"][0]["LaunchTemplateData"]["ImageId"]
  
  print(f"Old launch template version: {old_lt_version}")
  print(f"New ami-id: {parameter_value['image_id']}")
  print(f"Old ami-id: {old_lt_ami_id}")
  
  if old_lt_ami_id != parameter_value["image_id"]:
    print("Updating the AMI")
    new_launch_template_info = ec2_client.create_launch_template_version(
      SourceVersion=str(old_lt_version),
      LaunchTemplateId=old_lt_id,
      LaunchTemplateData={
          'ImageId': parameter_value['image_id'],
      },
      VersionDescription='Update AMI to latest using boto3'
    )
    return new_launch_template_info
    
  else:
    print("No need to update the AMI")
    
def modify_lt_default_version(new_launch_template_info):
  # Set the default version for the Launch Template
  print(new_launch_template_info["LaunchTemplateVersion"]["LaunchTemplateName"])
  print(new_launch_template_info["LaunchTemplateVersion"]["VersionNumber"])
  ec2_client.modify_launch_template(
      LaunchTemplateName=new_launch_template_info["LaunchTemplateVersion"]["LaunchTemplateName"],
      DefaultVersion=str(new_launch_template_info["LaunchTemplateVersion"]["VersionNumber"]),
  )

if __name__ == "__main__":
    # Get configuration from args or environment variables
    parameter_name, lt_name = parse_args()
    
    print(f"Using parameter: {parameter_name}")
    print(f"Using launch template: {lt_name}")
    
    parameter_value = get_parameter_value(parameter_name)
    
    default_launch_template_info = get_lt_info(lt_name)
    
    new_launch_template_info = update_lt_ami(default_launch_template_info, parameter_value)
    
    if new_launch_template_info:
      print(new_launch_template_info)
      modify_lt_default_version(new_launch_template_info)