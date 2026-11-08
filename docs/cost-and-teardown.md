# Cost and teardown

## Approach
The project was built on a new AWS account using the free plan credits. To keep spending low, billable resources were created only when needed and deleted after testing. The VPC, subnets, route tables, security groups, launch template and IAM role are free and were kept.

## Main cost drivers while running

| Resource | Why it costs money |
|---|---|
| NAT gateway | Hourly charge plus data processed |
| Application Load Balancer | Hourly charge plus capacity units |
| RDS MySQL (single-AZ, small instance) | Hourly instance charge plus storage |
| EC2 instances (2 to 4 small) | Hourly charge while running |
| Public IPv4 addresses | Hourly charge per address (NAT's Elastic IP, ALB nodes) |

## Actual figures from this build

| Item | Value |
|---|---|
| Credits used | About $2.48 per the Billing console (billing data lags, so the final figure may be slightly higher) |
| Running time | About a day and a half (5 to 6 November 2026) for the NAT gateway, ALB and RDS |
| Compute | The Auto Scaling group was scaled to zero overnight to avoid instance charges |
| RDS created | 5 November 2026, about 20:32 IST (from RDS events) |

Evidence: `screenshots/cost-explorer.png`

## Teardown order

Deleting in this order avoids "resource in use" errors:

1. Auto Scaling group `ha-web-asg` (terminates instances, removes its scaling alarms)
2. Application Load Balancer `ha-alb`, then target group `ha-web-tg`
3. RDS instance `ha-db` (no final snapshot, no retained backups for this lab)
4. NAT gateway `ha-nat-a`, wait for Deleted, then release its Elastic IP
5. Optional: dashboard, custom alarms, log group `/ha/app`, DB subnet group

Kept (free): VPC, subnets, route tables, internet gateway, security groups, launch template, IAM role, Parameter Store entry.

## Verification after teardown
- EC2: no running instances, no volumes, no Elastic IPs
- VPC: no NAT gateways
- Load balancers: none
- RDS: no databases

Evidence: `screenshots/teardown-instances.png`

## Production cost notes
- One NAT gateway per AZ improves availability and increases cost.
- Multi-AZ RDS roughly doubles the database instance cost.
- VPC endpoints can reduce NAT data charges for AWS service traffic.
- Reserved capacity or Savings Plans apply once the workload is steady.
