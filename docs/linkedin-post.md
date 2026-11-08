# LinkedIn post draft

Attach the architecture diagram and one test screenshot (the database restart monitor or the Auto Scaling activity screenshot work well). Put the GitHub link in the first comment.

---

I built and tested a highly available three-tier architecture on AWS, then tore it down to keep costs near zero.

What I built:
- Multi-AZ VPC with public, private app and private database tiers
- Application Load Balancer with health checks, Auto Scaling group for self-healing and request-based scaling
- RDS MySQL in isolated private subnets, no public access
- Chained security groups, no SSH (Session Manager only), secrets in Parameter Store
- CloudWatch logs, metrics, alarms with email alerts and a dashboard

What I tested:
- Terminated an instance under live traffic: requests kept flowing while the Auto Scaling group launched a replacement
- Simulated losing one AZ's capacity: no failed requests in my captured output, all traffic served from the other AZ
- Restarted the database: web tier stayed up, the database was back in about 14 seconds, data intact
- Sustained load: a target-tracking policy scaled the group from 2 to 4 instances automatically

What I would change for production: Multi-AZ database, one NAT gateway per AZ, HTTPS with ACM and WAF. My database ran single-AZ in this build, and I documented that honestly.

Next: rebuilding the same stack with Terraform and a CI/CD pipeline.

I am a cloud and infrastructure engineer (AWS Solutions Architect Associate track) looking for remote cloud engineering roles. Repo with diagrams, test report and runbook in the comments.

#AWS #CloudEngineering #Infrastructure #HighAvailability #CloudWatch
