## LT(LaunchTemplate) Manager

### Purpose
This code is to update AMI of Launch Template easy.  
1. Search for latest AMI using SSM parameter stores
2. Comparing current AMI and target AMI.
3. If it needs to be update, update and set default version.
 

 ### Target
- CodeDeploy Launch Template AMI
- ECS Launch Template AMI