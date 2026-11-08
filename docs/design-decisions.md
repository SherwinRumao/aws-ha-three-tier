# Design decisions

Each entry lists the decision, the alternatives considered, the reason and the trade-off.

## 1. Two Availability Zones, three network tiers
- **Alternatives:** single AZ; three AZs; two tiers.
- **Reason:** two AZs is the minimum for high availability, and separate public, app and database tiers limit what is reachable from the internet.
- **Trade-off:** a third AZ would improve resilience further at higher cost.

## 2. One route table per purpose; main route table left unused
- **Alternatives:** put the internet route in the main route table.
- **Reason:** unassociated subnets fall back to the main table, so an internet route there could make a new subnet public by accident. Keeping it plain means a forgotten subnet is private by default.
- **Trade-off:** slightly more route tables to manage.

## 3. Single NAT gateway
- **Alternatives:** one NAT gateway per AZ; NAT instance; VPC endpoints only.
- **Reason:** cost during a time-limited lab. Servers need outbound access to install packages and call AWS APIs.
- **Trade-off:** if the NAT's AZ fails, outbound access from the other AZ is lost. Inbound user traffic is unaffected. Production would use one per AZ.

## 4. Servers in private subnets behind an ALB
- **Alternatives:** instances in public subnets with public IPs.
- **Reason:** instances are never directly reachable from the internet. The ALB is the only entry point.

## 5. Security groups chained by reference
- **Alternatives:** CIDR-based rules.
- **Reason:** `app-sg` accepts traffic only from `alb-sg` and `db-sg` only from `app-sg`, so access follows the tiers even if IP ranges change.

## 6. Session Manager instead of SSH or a bastion host
- **Alternatives:** bastion host with key pairs; SSH from a fixed IP.
- **Reason:** no inbound ports, no key management, access governed by IAM.

## 7. IMDSv2 required
- **Reason:** reduces exposure of instance credentials to request-forgery attacks.

## 8. Health check independent of the database
- **Alternatives:** health check that queries the database.
- **Reason:** a database problem should not cause the load balancer to mark every web server unhealthy and make the Auto Scaling group cycle healthy instances. `/health` only checks the web process.
- **Trade-off:** the load balancer will keep sending traffic during a database outage; the page shows a clear "Database unavailable" message instead.

## 9. Secrets in SSM Parameter Store (SecureString)
- **Alternatives:** password in user data or source code; Secrets Manager with rotation.
- **Reason:** keeps the password out of the repo and launch template. The instance role reads it at runtime.
- **Trade-off:** Secrets Manager adds rotation but costs more. The role policy is broader than necessary and should be scoped to one parameter in production.

## 10. Target-tracking scaling on request count per target
- **Alternatives:** CPU-based scaling; step scaling.
- **Reason:** request rate reflects web load more directly than CPU for this workload and is easy to trigger in testing.

## 11. User data bootstrap with launch template versions and instance refresh
- **Alternatives:** pre-baked AMI.
- **Reason:** simple and transparent for a first build; new versions roll out with no downtime.
- **Trade-off:** slower instance start than a baked AMI; production would bake an image.

## 12. Single-AZ RDS
- **Alternatives:** Multi-AZ instance deployment.
- **Reason:** Multi-AZ was not available on this account during the build, and it would double the database cost.
- **Trade-off:** the database does not survive an AZ failure. Documented as the first production upgrade.

## 13. HTTP only
- **Reason:** no custom domain was used in this lab.
- **Next step:** ACM certificate, HTTPS listener with redirect, Route 53 and WAF.
