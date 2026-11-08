# Highly Available Three-Tier Web Architecture on AWS

A multi-AZ web platform on AWS designed for high availability, fault tolerance and horizontal scalability, with layered network security and built-in monitoring and logging. Built manually in the AWS console, validated with failure and load tests, then torn down to control cost.

![Architecture](architecture/ha-architecture-drawio.png)

## Highlights

- Two Availability Zones in `ap-south-1` (Mumbai), three network tiers: public, private application, private database
- Application Load Balancer with health checks distributing traffic across both AZs
- Auto Scaling group (min 2, max 4) providing self-healing and request-based scaling
- RDS MySQL in isolated private subnets with no public access and encryption at rest
- Chained security groups: internet to ALB to application to database
- No SSH exposed: shell access through AWS Systems Manager Session Manager
- Database password held in SSM Parameter Store (SecureString), read at runtime through an IAM role
- CloudWatch logs, metrics, alarms with SNS email alerts, and a dashboard
- Zero-downtime application rollout using launch template versions and instance refresh

## Design goals and how they are met

| Goal | Implementation |
|---|---|
| High availability | Compute and load balancer span two AZs; traffic only goes to healthy targets |
| Fault tolerance | Auto Scaling replaces failed instances using ELB health checks; the web health check is independent of the database |
| Scalability | Target-tracking policy on ALB request count per target (target value 30), 2 to 4 instances |
| Security | Private app and DB tiers, security-group chaining, no SSH, IMDSv2 only, secrets kept out of code |
| Observability | Application logs and memory/disk metrics via the CloudWatch agent, alarms, dashboard, Logs Insights queries |

## Network design

| Tier | Subnets | Route table | Default route |
|---|---|---|---|
| Public | `public-subnet-a`, `public-subnet-b` | `public-rt` | Internet gateway |
| Private app | `private-app-subnet-a`, `private-app-subnet-b` | `private-app-rt` | NAT gateway |
| Private database | `private-db-subnet-a`, `private-db-subnet-b` | `private-db-rt` | None (local only) |

The VPC's main route table is left unused so that any subnet without an explicit association stays private by default.

## Security model

- Only the load balancer is internet-facing.
- `alb-sg` allows HTTP from the internet. `app-sg` allows HTTP only from `alb-sg`. `db-sg` allows MySQL (3306) only from `app-sg`.
- Instances launch in private subnets with no inbound SSH. Administrative access uses Session Manager.
- Instance metadata is restricted to IMDSv2.
- The instance role carries `AmazonSSMManagedInstanceCore`, `CloudWatchAgentServerPolicy` and `AmazonSSMReadOnlyAccess`.

## Monitoring and logging

- Application log streamed to the `/ha/app` log group (one stream per instance, 7-day retention).
- Memory and disk metrics collected by the CloudWatch agent.
- Alarms to an SNS email topic: unhealthy hosts, high target response time, high ASG CPU, low RDS free storage.
- Dashboard covering request count, healthy and unhealthy hosts, target response time, CPU and database connections.
- Logs Insights query used to show request distribution across instances.

## Validation

Full detail in [docs/test-report.md](docs/test-report.md).

| Test | Method | Result |
|---|---|---|
| Instance failure | Terminated one instance while sending continuous requests | Passed: the surviving instance kept serving requests and the Auto Scaling group launched a replacement |
| Load-based scale-out | Sustained request load against the ALB | Passed: the target-tracking alarm fired and capacity rose from 2 to 4 instances automatically; all 4 targets healthy |
| AZ capacity loss (simulated) | Removed one AZ's subnet from the Auto Scaling group | Passed: no failed requests in the captured output; all responses came from `ap-south-1b` |
| Database restart | Rebooted the RDS instance during traffic | Web tier stayed up; database unavailable for about 14 seconds; saved notes preserved |
| Security checks | Port checks from outside AWS | Port 80 open; ports 22 and 3306 not reachable; database address resolves to a private IP |

## Evidence

Screenshots are in the [screenshots](screenshots/) folder.

| Area | Screenshots |
|---|---|
| Network | [VPC resource map](screenshots/vpc-resource-map.png), [VPC resource map 2](screenshots/vpc-resource-map-2.png), [public route table](screenshots/Public-rt-routes.png), [private app route table](screenshots/private-app-rt.png), [private DB route table](screenshots/private-db-rt-routes.png) |
| Security | [ALB security group](screenshots/alb-sg-inbound.png), [app security group](screenshots/app-sg-inbound.png), [DB security group](screenshots/db-sg-inbound.png), [IAM role](screenshots/iam-role.png) |
| Compute and scaling | [ALB details](screenshots/alb-details.png), [launch template](screenshots/launch-template.png), [Auto Scaling group](screenshots/asg-details.png), [ASG instances](screenshots/asg-instances.png), [scaling policy](screenshots/Asg_scaling_policy.png), [target group healthy](screenshots/target-group-healthy.png) |
| Application | [app with notes](screenshots/app-with-notes.png), [demo 1](screenshots/demo1.png), [demo 2](screenshots/demo%202.png), [requests alternating across instances](screenshots/curl-alternating.png) |
| Database | [RDS details](screenshots/rds-details.png) |
| Monitoring | [log streams](screenshots/log-streams.png), [Logs Insights](screenshots/logs-insights.png), [alarms](screenshots/alarms-list.png), [alarm state](screenshots/alarm-state.png), [dashboard baseline](screenshots/dashboard-baseline.png) |
| Test 1: instance termination | [monitor output 1](screenshots/test1-instance-termination-1.png), [monitor output 2](screenshots/test1-instance-termination-2.png) |
| Test 2: scale-out | [ASG activity](screenshots/test2-asg-activity.png), [dashboard under load](screenshots/test2-dashboard-load.png), [target group scaled](screenshots/test2-target-group-scaled.png) |
| Test 3: AZ capacity loss | [monitor output](screenshots/test3-az-failure-monitor.png), [instances in AZ b](screenshots/test3-asg-instances-1b.png) |
| Test 4: database restart | [restart monitor](screenshots/test4-restart-monitor.png), [RDS events](screenshots/test4-rds-events.png), [notes preserved](screenshots/test4-notes-preserved.png) |
| Test 5: security checks | [port checks](screenshots/test5-security-checks.png) |
| Cost and teardown | [Cost Explorer](screenshots/cost-explorer.png), [teardown](screenshots/teardown-instances.png) |

## Cost and teardown

The stack was built and torn down within a limited window to stay inside free-plan credits. About $2.48 of credits had been used after roughly a day and a half of running (billing data lags, so the final figure may be slightly higher). The main cost drivers were the NAT gateway, Application Load Balancer, RDS and EC2. Details in [docs/cost-and-teardown.md](docs/cost-and-teardown.md).

## Known limitations and next steps

- **Single-AZ database.** RDS ran as a single instance (the standby option was not available on this account). A production deployment would use Multi-AZ so the database survives an AZ failure.
- **Single NAT gateway.** Outbound internet from the app tier is a single point of failure. Production would use one NAT gateway per AZ.
- **HTTP only.** Production would add an ACM certificate, HTTPS listener and Route 53 domain, and attach AWS WAF to the ALB.
- **Broad Parameter Store permission.** The instance role uses a managed read-only policy; production would scope it to the single parameter.
- **AZ failure was simulated** by removing a subnet from the Auto Scaling group, not by a real AWS outage.
- **Scale-in was not captured** in the evidence; only scale-out was observed.
- **Manually built.** The next project rebuilds this stack with Terraform and a CI/CD pipeline.

## Repository structure

```
architecture/   architecture diagram
app/            Flask app (app.py) and EC2 bootstrap script (user-data.sh)
docs/           design decisions, test report, runbook, cost and teardown
screenshots/    evidence
```
