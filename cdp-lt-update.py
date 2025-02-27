import boto3
import json
import os

# https://docs.aws.amazon.com/AmazonECS/latest/developerguide/retrieve-ecs-optimized_AMI.html#ecs-optimized-ami-parameter-format

# 1. Get the latest AL2023 AMI
parameter_name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-6.1-x86_64"
lt_name = "bys-dev-lt-ec2-cdp"
# ```
# {
#   "Parameter": {
#     "Name": "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-6.1-x86_64",
#     "Type": "String",
#     "Value": "ami-0c7eb81e6fe66fd84",
#     "Version": 101,
#     "LastModifiedDate": "datetime.datetime(2025, 1, 10, 8, 2, 6, 415000, tzinfo=tzlocal())",
#     "ARN": "arn:aws:ssm:ap-northeast-2::parameter/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-6.1-x86_64",
#     "DataType": "text"
#   },
#   .......
# ```

ssm_client = boto3.client("ssm")
ec2_client = boto3.client("ec2")



## GET the parameter value from parameter store ecs
def get_parameter_value(parameter_name):
    try:
        response = ssm_client.get_parameter(
            Name=parameter_name,
            WithDecryption=True
        )
        return response["Parameter"]["Value"]
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
  
  print(f"New ami-id: {parameter_value}")
  print(f"Old ami-id: {old_lt_ami_id}")
  
  if old_lt_ami_id != parameter_value:
    print("Updating the AMI")
    new_launch_template_info = ec2_client.create_launch_template_version(
      SourceVersion=str(old_lt_version),
      LaunchTemplateId=old_lt_id,
      LaunchTemplateData={
          'ImageId': parameter_value,
      },
      VersionDescription='Update AMI to latest using boto3'
    )
    return new_launch_template_info
    
  else:
    print("No need to update the AMI")
    
    
def modify_lt_default_version(new_launch_template_info):
  # Launch Template의 기본 버전 설정
  print(new_launch_template_info["LaunchTemplateVersion"]["LaunchTemplateName"])
  print(new_launch_template_info["LaunchTemplateVersion"]["VersionNumber"])
  ec2_client.modify_launch_template(
      LaunchTemplateName=new_launch_template_info["LaunchTemplateVersion"]["LaunchTemplateName"],
      DefaultVersion=str(new_launch_template_info["LaunchTemplateVersion"]["VersionNumber"]),
  )


if __name__ == "__main__":
    parameter_value = get_parameter_value(parameter_name)
    
    default_launch_template_info = get_lt_info(lt_name)
    
    new_launch_template_info = update_lt_ami(default_launch_template_info, parameter_value)
    
    if new_launch_template_info:
      print(new_launch_template_info)
      modify_lt_default_version(new_launch_template_info)
    
    # lt_id = get_lt_id(lt_name)
    # new_launch_template_version = update_lt_ami(lt_id, parameter_value)
    # print(new_launch_template_version)
    