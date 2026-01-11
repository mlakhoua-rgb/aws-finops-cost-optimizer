# AWS FinOps Cost Optimizer - Architecture

This document provides a detailed overview of the system architecture, components, and data flow for the AWS FinOps Cost Optimizer toolkit.

## Guiding Principles

The architecture is designed based on the following principles:

- **Modularity:** Components are loosely coupled and can be deployed independently.
- **Scalability:** The system can scale to handle large AWS environments with many resources.
- **Automation:** Repetitive tasks are automated to reduce manual effort and improve efficiency.
- **Security:** The architecture follows the principle of least privilege and includes security best practices.
- **Cost-Effectiveness:** The toolkit itself is designed to run at a very low cost.

## System Components

The toolkit is composed of four main layers: Analysis, Automation, Monitoring, and Infrastructure.

![Architecture Diagram](https://user-images.githubusercontent.com/12345/123456789-abcdef.png)  
*Note: A proper architecture diagram would be generated and uploaded here.*

### 1. Analysis Layer

This layer is responsible for querying AWS cost and usage data and identifying optimization opportunities.

- **Python Scripts:** A collection of scripts located in the `scripts/` directory.
  - `cost_analysis.py`: Queries the AWS Cost Explorer API to generate detailed cost reports.
  - `unused_resources.py`: Identifies idle or unattached resources like EC2 instances, EBS volumes, and Elastic IPs.
  - `rightsizing_recommendations.py`: Analyzes CloudWatch metrics to suggest more appropriate EC2 instance sizes.
- **AWS Cost Explorer API:** The primary data source for all cost and usage information.

### 2. Automation Layer

This layer consists of serverless functions that perform automated cost-saving actions.

- **AWS Lambda Functions:** Located in the `lambda/` directory.
  - `auto_tagger`: Scans for untagged resources and applies default tags to improve cost allocation.
  - `scheduler`: Stops and starts EC2 instances based on a predefined schedule (e.g., outside of business hours).
  - `snapshot_cleanup`: Deletes old EBS snapshots that are past their retention period.
- **Amazon EventBridge (CloudWatch Events):** Used to trigger the Lambda functions on a schedule (e.g., hourly, daily).

### 3. Monitoring Layer

This layer provides visibility into AWS spending and the effectiveness of the optimization actions.

- **Amazon CloudWatch:**
  - **Dashboards:** Pre-built dashboards to visualize cost trends, spending by service, and budget adherence.
  - **Alarms:** Proactive alerts that trigger when spending exceeds predefined thresholds.
  - **Logs:** Centralized logging for all Lambda functions and scripts for debugging and auditing.
- **Amazon SNS (Simple Notification Service):** Sends notifications for budget alerts and other important events to stakeholders via email or other channels.
- **AWS Budgets:** Used to set spending limits and trigger alerts when costs exceed the budget.

### 4. Infrastructure Layer

This layer defines and deploys all the necessary AWS resources using Infrastructure as Code.

- **Terraform:** The entire infrastructure for the toolkit is defined in Terraform code located in the `terraform/` directory.
  - **Modules:** Reusable modules for deploying Lambda functions, IAM roles, and other components.
  - **Environments:** Separate configurations for `dev` and `prod` environments.
- **AWS IAM (Identity and Access Management):** Defines roles and policies with least-privilege permissions for all components.
- **Amazon S3:** A secure, private bucket is used to store cost reports and Lambda function deployment packages.

## Data Flow

1.  **Cost Data Ingestion:** The `cost_analysis.py` script periodically queries the **AWS Cost Explorer API**.
2.  **Report Generation:** The script processes the data and generates CSV/JSON reports, which are stored in the **S3 bucket**.
3.  **Automated Scans:** The `unused_resources.py` and `rightsizing_recommendations.py` scripts are run (manually or via automation) to identify potential savings.
4.  **Scheduled Automation:** **Amazon EventBridge** triggers the **Lambda functions** on a regular schedule.
5.  **Tagging and Cleanup:** The `auto_tagger` and `snapshot_cleanup` functions scan for and act on non-compliant resources.
6.  **Instance Scheduling:** The `scheduler` function stops or starts instances based on their tags.
7.  **Monitoring and Alerting:** **AWS Budgets** and **CloudWatch Alarms** continuously monitor spending. If a threshold is breached, an alert is sent to an **SNS topic**, which then notifies the configured subscribers (e.g., via email).
8.  **Visualization:** Users can view cost trends and metrics on the **CloudWatch Dashboards**.

## Security Considerations

- **Least Privilege:** All IAM roles for Lambda functions and other services are scoped with the minimum necessary permissions.
- **Encryption:** The S3 bucket for reports and the SNS topics are encrypted at rest.
- **Network Security:** Lambda functions run within the AWS network. If they need to access resources in a VPC, they can be configured with VPC access.
- **Code Security:** The Python scripts and Terraform code can be scanned with static analysis tools (e.g., `bandit`, `tfsec`) to identify potential security issues.
