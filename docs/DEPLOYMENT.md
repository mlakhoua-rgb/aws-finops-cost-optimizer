# AWS FinOps Cost Optimizer - Deployment Guide

This guide provides step-by-step instructions for deploying the AWS FinOps Cost Optimizer toolkit using Terraform.

## Prerequisites

Before you begin, ensure you have the following prerequisites installed and configured:

- **AWS Account:** An active AWS account with administrative or sufficient IAM permissions.
- **AWS CLI:** The AWS Command Line Interface, configured with your credentials. You can configure it by running `aws configure`.
- **Terraform:** Terraform version 1.6.0 or later.
- **Git:** To clone the repository.
- **Python:** Python 3.11 or later.

## Deployment Steps

### Step 1: Clone the Repository

Clone this repository to your local machine:

```bash
git clone https://github.com/mlakhoua-rgb/aws-finops-cost-optimizer.git
cd aws-finops-cost-optimizer
```

### Step 2: Configure the Terraform Backend (Optional, but Recommended)

For production use, it is highly recommended to configure a remote backend to store the Terraform state file securely. This example uses an S3 bucket.

1.  **Create an S3 Bucket:** Create a unique S3 bucket to store your Terraform state.

    ```bash
    aws s3 mb s3://your-terraform-state-bucket-name
    ```

2.  **Enable Versioning:** Enable versioning on the bucket to keep a history of your state files.

    ```bash
    aws s3api put-bucket-versioning --bucket your-terraform-state-bucket-name --versioning-configuration Status=Enabled
    ```

3.  **Configure the Backend:** Uncomment and update the `backend "s3"` block in `terraform/main.tf` with your bucket name and desired key.

    ```hcl
    terraform {
      # ...
      backend "s3" {
        bucket = "your-terraform-state-bucket-name"
        key    = "finops/terraform.tfstate"
        region = "us-east-1"
        encrypt = true
      }
    }
    ```

### Step 3: Prepare the Terraform Configuration

Navigate to the development environment directory and create a configuration file.

```bash
cd terraform/environments/dev

# Copy the example configuration file
cp terraform.tfvars.example terraform.tfvars
```

Now, edit the `terraform.tfvars` file with your specific values. You must provide your email address for the `owner_email` and `alert_email` variables.

```hcl
# terraform.tfvars

aws_region           = "us-east-1"
environment          = "dev"
project_name         = "aws-finops-optimizer"
owner_email          = "your-email@example.com"
alert_email          = "your-email@example.com"
monthly_budget_limit = 100 # Set your desired budget in USD
# ... other variables
```

### Step 4: Deploy the Infrastructure

Now you can deploy the entire toolkit using Terraform.

1.  **Initialize Terraform:** This will download the necessary providers and configure the backend.

    ```bash
    terraform init
    ```

2.  **Plan the Deployment:** This command shows you what resources Terraform will create, change, or destroy. It's a good practice to review the plan before applying it.

    ```bash
    terraform plan
    ```

3.  **Apply the Configuration:** This command will create all the AWS resources defined in the Terraform code.

    ```bash
    terraform apply
    ```

    Terraform will ask for confirmation. Type `yes` and press Enter.

After the deployment is complete, Terraform will output the names of the created S3 bucket, SNS topic, and the ARN of the Lambda execution role.

### Step 5: Verify the Deployment

1.  **Check AWS Console:** Log in to your AWS Management Console and verify that the following resources have been created:
    -   An S3 bucket for reports.
    -   An SNS topic for alerts.
    -   IAM roles for Lambda execution.
    -   Lambda functions for `auto-tagger`, `scheduler`, and `snapshot-cleanup`.
    -   CloudWatch EventBridge rules to trigger the Lambda functions.
    -   An AWS Budget for cost monitoring.

2.  **Check Lambda Functions:** Navigate to the Lambda console and inspect the newly created functions. You can view their configuration, environment variables, and associated triggers.

3.  **Check CloudWatch:** Go to the CloudWatch console to see the log groups for the Lambda functions and the budget alarm that was created.

## Post-Deployment: Using the Toolkit

Once deployed, the toolkit will start working automatically based on the schedules you've configured.

- **Automated Actions:** The Lambda functions will run on their defined schedules to tag resources, stop/start instances, and clean up snapshots.
- **Cost Analysis:** You can run the Python scripts in the `scripts/` directory manually to perform on-demand cost analysis.
- **Alerts:** You will receive email notifications from SNS if your spending exceeds the budget thresholds you defined.

### Running the Analysis Scripts

To run the analysis scripts, you'll need to install the Python dependencies first:

```bash
cd ../../../scripts
pip install -r requirements.txt

# Example: Get a cost report for the last 7 days
python cost_analysis.py --days 7 --output cost_report.csv
```

## Destroying the Infrastructure

If you want to remove all the resources created by this toolkit, you can use the `terraform destroy` command.

**Warning:** This action is irreversible and will delete all the created resources, including the S3 bucket with your reports.

```bash
cd terraform/environments/dev
terraform destroy
```

Terraform will ask for confirmation. Type `yes` and press Enter.
