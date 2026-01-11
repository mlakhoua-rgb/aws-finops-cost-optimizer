# AWS FinOps Cost Optimizer

[![Terraform](https://img.shields.io/badge/Terraform-1.6+-623CE4?logo=terraform)](https://www.terraform.io/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python)](https://www.python.org/)
[![AWS](https://img.shields.io/badge/AWS-Cloud-FF9900?logo=amazon-aws)](https://aws.amazon.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![AI-Augmented](https://img.shields.io/badge/AI--Augmented-Manus%20AI-blueviolet)](https://www.manus.im/)

**AI-Augmented FinOps: Demonstrating Strategic Cost Management for AWS Infrastructure**

This repository showcases a comprehensive, generic AWS FinOps toolkit developed with AI assistance to demonstrate cost optimization, resource management, and automated savings strategies. The project illustrates how platform engineering leaders can leverage AI agents for accelerated development while maintaining human oversight of financial governance and production environments.

**Purpose:** Educational example demonstrating FinOps best practices, cost visibility, and automated optimization for AWS infrastructure. All code is generic, reusable, and safe for public sharing.

**Repository:** [https://github.com/mlakhoua-rgb/aws-finops-cost-optimizer](https://github.com/mlakhoua-rgb/aws-finops-cost-optimizer)

---

## 🤖 AI-Augmented Development Approach

### Human-AI Collaboration Model

This FinOps toolkit was developed using an orchestrated AI collaboration model where experienced platform engineering leaders leverage AI agents for specific development tasks while maintaining strategic oversight of financial governance and cost management policies.

**AI Agents Used:**
- **Manus AI**: Primary agent for Python script development, Lambda function creation, and Terraform module design
- **Claude**: Code review, architecture validation, FinOps best practices, and security analysis
- **Gemini**: Data analysis, cost trend identification, and optimization recommendations
- **Perplexity**: Research on AWS Cost Explorer API, pricing models, and industry FinOps standards
- **ChatGPT**: Rapid prototyping, troubleshooting, and CloudWatch dashboard design

**Human Oversight:**
- Strategic cost management policies and budget accountability
- Financial governance and approval workflows
- Cost allocation strategies and chargeback models
- Vendor negotiations and contract management
- Stakeholder communication and executive reporting

### FinOps Best Practices with AI Integration

This repository demonstrates how AI agents can be integrated into FinOps workflows for:

- **Automated Cost Analysis**: AI-assisted generation of cost reports with human validation of findings
- **Resource Optimization**: AI-powered identification of savings opportunities with human approval of changes
- **Tagging Enforcement**: Automated tagging policies with human-defined governance rules
- **Anomaly Detection**: AI-augmented cost anomaly identification with human investigation
- **Documentation Generation**: AI-powered creation of cost reports and optimization recommendations

**Key Principle**: Experienced platform leaders orchestrate AI agents to accelerate FinOps operations while maintaining accountability for financial decisions and budget management that should never be fully automated without human oversight.

---

## 🎯 Project Overview

This toolkit provides a complete set of tools for implementing FinOps practices on AWS. It enables organizations to gain cost visibility, identify savings opportunities, and automate cost optimization actions—all while maintaining financial governance and control.

**Key Features:**
- **Cost Analysis Scripts**: Python tools to query AWS Cost Explorer and generate detailed cost reports
- **Resource Tagging Automation**: Lambda functions to enforce tagging policies and improve cost allocation
- **Automated Optimization**: Scheduled Lambda functions to stop/start resources and clean up waste
- **Cost Monitoring**: CloudWatch dashboards and alarms for proactive cost management
- **Infrastructure as Code**: Complete Terraform deployment for the entire toolkit
- **Right-Sizing Recommendations**: Identify over-provisioned resources and optimization opportunities
- **Budget Alerts**: Automated notifications when spending exceeds thresholds

---

## 🏗️ Architecture Overview

The FinOps toolkit consists of several integrated components that work together to provide comprehensive cost management capabilities.

### Component Architecture

The system is organized into four main layers that enable end-to-end cost optimization. The **Analysis Layer** uses Python scripts and AWS Cost Explorer API to generate cost reports, identify unused resources, and provide right-sizing recommendations. The **Automation Layer** deploys Lambda functions for resource tagging, EC2 scheduling, and snapshot cleanup, all triggered by CloudWatch Events. The **Monitoring Layer** provides CloudWatch dashboards for cost visualization, budget alarms for threshold notifications, and SNS topics for alert distribution. Finally, the **Infrastructure Layer** uses Terraform to deploy all components with proper IAM roles, security policies, and least-privilege access controls.

### Data Flow

Cost data flows from AWS services through Cost Explorer API to analysis scripts that generate reports and recommendations. These insights trigger automated actions through Lambda functions, which modify resources based on defined policies. All actions are logged to CloudWatch, and cost metrics are continuously monitored against budgets. When anomalies or threshold breaches occur, SNS notifications alert stakeholders for human review and approval.

---

## 📦 Technology Stack

### Core Technologies
- **Python 3.11+**: Analysis scripts and Lambda functions
- **Boto3**: AWS SDK for Python
- **Terraform 1.6+**: Infrastructure as Code
- **AWS Lambda**: Serverless automation
- **AWS Cost Explorer**: Cost and usage data API

### AWS Services
- **Cost Explorer**: Cost analysis and reporting
- **Lambda**: Automated optimization functions
- **CloudWatch**: Monitoring, dashboards, and alarms
- **SNS**: Alert notifications
- **EventBridge**: Scheduled automation triggers
- **IAM**: Security and access control
- **S3**: Report storage and archival

### Development Tools
- **Git**: Version control
- **GitHub Actions**: CI/CD automation
- **Pytest**: Unit testing for Python code
- **Checkov**: Terraform security scanning
- **Pre-commit**: Code quality hooks

---

## 🚀 Getting Started

### Prerequisites

**Required Tools:**
- Python 3.11 or higher
- Terraform 1.6 or higher
- AWS CLI 2.x
- Git for version control

**AWS Account Requirements:**
- AWS account with appropriate permissions
- IAM user with programmatic access
- Cost Explorer API enabled (may incur small charges)
- Sufficient service quotas for Lambda, CloudWatch, and SNS

**Permissions Required:**
The IAM user needs permissions for:
- Cost Explorer (read access to cost and usage data)
- Lambda (create, update, and invoke functions)
- CloudWatch (create dashboards, alarms, and log groups)
- SNS (create topics and subscriptions)
- EC2 (describe instances, stop/start instances, manage snapshots)
- S3 (create buckets, read/write objects)
- IAM (create roles and policies for Lambda execution)
- EventBridge (create rules for scheduled triggers)

---

## 📊 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/mlakhoua-rgb/aws-finops-cost-optimizer.git
cd aws-finops-cost-optimizer
```

### 2. Configure AWS Credentials

```bash
# Option 1: Using AWS CLI
aws configure

# Option 2: Using environment variables
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_DEFAULT_REGION="us-east-1"
```

### 3. Install Python Dependencies

```bash
cd scripts
pip install -r requirements.txt
```

### 4. Run Cost Analysis

```bash
# Generate a cost report for the last 30 days
python cost_analysis.py --days 30 --output report.csv

# Identify unused resources
python unused_resources.py --output unused.json

# Get right-sizing recommendations
python rightsizing_recommendations.py --output recommendations.json
```

### 5. Deploy Infrastructure with Terraform

```bash
cd terraform/environments/dev

# Copy example configuration
cp terraform.tfvars.example terraform.tfvars

# Edit with your values
nano terraform.tfvars

# Initialize Terraform
terraform init

# Review the plan
terraform plan

# Deploy the infrastructure
terraform apply
```

---

## 🔧 Key Components

### Cost Analysis Scripts

**Location:** `scripts/`

The cost analysis scripts provide comprehensive visibility into AWS spending patterns and identify optimization opportunities.

#### cost_analysis.py

Queries AWS Cost Explorer API to generate detailed cost reports by service, region, account, and custom tags. Supports multiple output formats (CSV, JSON, Excel) and date range filtering.

**Usage:**
```bash
python cost_analysis.py --days 30 --group-by SERVICE --output monthly_costs.csv
```

**Features:**
- Cost breakdown by service, region, or tag
- Month-over-month comparison
- Cost trend analysis
- Custom date range queries
- Multiple output formats

#### unused_resources.py

Identifies AWS resources that are running but not being used, such as idle EC2 instances, unattached EBS volumes, and unused Elastic IPs.

**Usage:**
```bash
python unused_resources.py --region us-east-1 --output unused.json
```

**Detects:**
- Idle EC2 instances (low CPU utilization)
- Unattached EBS volumes
- Unused Elastic IPs
- Old EBS snapshots
- Idle RDS instances

#### rightsizing_recommendations.py

Analyzes EC2 instance utilization metrics to provide right-sizing recommendations, helping to reduce costs by matching instance types to actual workload requirements.

**Usage:**
```bash
python rightsizing_recommendations.py --days 14 --output recommendations.json
```

**Provides:**
- Over-provisioned instance identification
- Alternative instance type recommendations
- Estimated monthly savings
- Utilization metrics (CPU, memory, network)

---

### Lambda Functions

**Location:** `lambda/`

Automated functions that execute cost optimization actions on a scheduled basis or in response to events.

#### auto_tagger

Enforces tagging policies by automatically tagging untagged resources with default values. Improves cost allocation and chargeback accuracy.

**Trigger:** EventBridge rule (hourly)

**Actions:**
- Scans for untagged EC2 instances, volumes, and snapshots
- Applies default tags (Environment, Owner, CostCenter)
- Sends notification for manual review
- Logs all tagging actions

#### scheduler

Stops and starts EC2 instances based on defined schedules to reduce costs during non-business hours.

**Trigger:** EventBridge rules (cron expressions)

**Actions:**
- Stops instances with "AutoStop" tag at defined times
- Starts instances with "AutoStart" tag at defined times
- Supports multiple time zones
- Sends notifications on schedule execution

#### snapshot_cleanup

Identifies and deletes old EBS snapshots that exceed retention policies, reducing storage costs.

**Trigger:** EventBridge rule (daily)

**Actions:**
- Identifies snapshots older than retention period
- Excludes snapshots with "Retain" tag
- Deletes eligible snapshots
- Sends summary report via SNS

---

### Terraform Infrastructure

**Location:** `terraform/`

Complete Infrastructure as Code deployment for the entire FinOps toolkit, including Lambda functions, CloudWatch dashboards, and monitoring.

#### Modules

**cost_explorer**: IAM roles and policies for Cost Explorer access  
**lambda**: Lambda function deployment with proper execution roles  
**cloudwatch**: Dashboards, alarms, and log groups

#### Environments

**dev**: Development environment with reduced retention and lower thresholds  
**prod**: Production environment with full retention and production thresholds

**Deployment:**
```bash
cd terraform/environments/prod
terraform init
terraform plan
terraform apply
```

---

### CloudWatch Dashboards

**Location:** `dashboards/`

Pre-built CloudWatch dashboards for visualizing cost metrics and monitoring optimization progress.

#### cost_overview_dashboard.json

Comprehensive cost overview with widgets for:
- Total monthly spend
- Cost by service (top 10)
- Cost by region
- Cost trend (last 90 days)
- Budget vs. actual spending

**Import:**
```bash
aws cloudwatch put-dashboard --dashboard-name FinOps-Overview --dashboard-body file://dashboards/cost_overview_dashboard.json
```

---

## 📈 Usage Examples

### Example 1: Monthly Cost Report

Generate a detailed cost report for the last month, grouped by service:

```bash
python scripts/cost_analysis.py --days 30 --group-by SERVICE --output monthly_report.csv
```

**Output:** CSV file with columns: Service, Cost, Percentage, Change from Previous Month

### Example 2: Identify Unused Resources

Find all unused resources in your AWS account to identify savings opportunities:

```bash
python scripts/unused_resources.py --all-regions --output unused.json
```

**Output:** JSON file listing all idle EC2 instances, unattached volumes, and unused Elastic IPs with estimated monthly savings.

### Example 3: Right-Size EC2 Instances

Analyze EC2 utilization over the last 14 days and get right-sizing recommendations:

```bash
python scripts/rightsizing_recommendations.py --days 14 --threshold 20 --output recommendations.json
```

**Output:** JSON file with instance IDs, current types, recommended types, and estimated monthly savings.

### Example 4: Deploy Automated Tagging

Deploy the auto-tagging Lambda function to enforce tagging policies:

```bash
cd terraform/environments/dev
terraform init
terraform apply -target=module.lambda.aws_lambda_function.auto_tagger
```

**Result:** Lambda function deployed and scheduled to run hourly, automatically tagging untagged resources.

---

## 🔒 Security Best Practices

This toolkit follows AWS security best practices and implements least-privilege access controls.

**IAM Policies:**
- Lambda execution roles have minimal required permissions
- Cost Explorer access is read-only by default
- Resource modification requires explicit permissions
- All actions are logged to CloudWatch for audit trails

**Data Protection:**
- Cost reports are stored in encrypted S3 buckets
- SNS topics use encryption at rest
- Lambda environment variables are encrypted with KMS
- No sensitive data is logged or exposed

**Access Control:**
- Terraform state is stored in encrypted S3 backend
- IAM roles use trust policies to prevent unauthorized access
- MFA can be required for sensitive operations
- CloudTrail logs all API calls for compliance

---

## 💰 Cost Estimation

Running this FinOps toolkit incurs minimal AWS costs, typically far less than the savings it generates.

**Estimated Monthly Costs:**

| Service | Usage | Estimated Cost |
|---------|-------|----------------|
| Cost Explorer API | ~100 requests/month | $1.00 |
| Lambda | ~2,000 invocations/month | $0.40 |
| CloudWatch Logs | ~1 GB/month | $0.50 |
| CloudWatch Dashboards | 3 dashboards | $9.00 |
| SNS | ~100 notifications/month | $0.10 |
| S3 Storage | ~5 GB reports | $0.12 |
| **Total** | | **~$11.12/month** |

**Expected Savings:**
Based on typical implementations, this toolkit can identify savings of $500-$5,000+ per month, providing an ROI of 50x-500x.

---

## 🧪 Testing

The repository includes comprehensive unit tests for all Python scripts and Lambda functions.

**Run Tests:**
```bash
cd scripts
pytest tests/ -v --cov=. --cov-report=html
```

**Test Coverage Goals:**
- Scripts: 80%+
- Lambda functions: 85%+
- Overall: 80%+

---

## 📚 Documentation

Additional documentation is available in the `docs/` directory:

- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)**: Detailed architecture and design decisions
- **[DEPLOYMENT.md](docs/DEPLOYMENT.md)**: Step-by-step deployment guide
- **[TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)**: Common issues and solutions
- **[CONTRIBUTING.md](CONTRIBUTING.md)**: Guidelines for contributing to the project

---

## 🤝 Contributing

Contributions are welcome! This is an educational project designed to help the community learn FinOps best practices.

**How to Contribute:**
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure your code follows the existing style and includes appropriate tests.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

This project was developed with AI assistance from Manus AI, Claude, Gemini, and other AI agents, demonstrating how experienced platform engineering leaders can leverage AI to accelerate development while maintaining strategic oversight and financial governance.

**Disclaimer:** This is a generic, educational example. All configurations, thresholds, and policies should be customized for your specific organization's needs. No proprietary information or employer-specific content is included.

---

## 📫 Contact

**Author:** Mohamed Ben Lakhoua  
**LinkedIn:** [linkedin.com/in/benlakhoua](https://linkedin.com/in/benlakhoua)  
**Email:** mo@metafive.one  
**GitHub:** [github.com/mlakhoua-rgb](https://github.com/mlakhoua-rgb)

---

*This repository demonstrates AI-augmented FinOps practices for AWS cost optimization. It showcases how platform engineering leaders can use AI agents as collaborators while maintaining human oversight of financial governance and strategic cost management decisions.*

**Last Updated:** January 2026
