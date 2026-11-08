# Runbook

Operational procedures for the HA three-tier platform. Alarm notifications go to the `ha-alerts` SNS topic (email).

## Alarm: `ha-unhealthy-hosts`
**Meaning:** at least one target in `ha-web-tg` is failing health checks.
1. EC2 > Target groups > `ha-web-tg` > Targets: identify the unhealthy instance and its AZ.
2. Open Session Manager on that instance and run `sudo systemctl status app` and `sudo tail -50 /var/log/app.log`.
3. If the app is down, `sudo systemctl restart app`. If the instance is unrecoverable, terminate it; the Auto Scaling group replaces it.
4. If all targets are unhealthy, check `app-sg` still allows HTTP from `alb-sg` and that the latest launch template version is not broken (see "Roll back").

## Alarm: `ha-high-response-time`
**Meaning:** average target response time above 1 second.
1. Check the dashboard for a request spike (RequestCount) and the instance count.
2. If load is high and the group is at maximum, raise the maximum or tune the scaling target.
3. If response time is high with normal load, check the database: RDS CPU, DatabaseConnections, and the "DB read error" lines in `/ha/app` logs.

## Alarm: `ha-asg-cpu-high`
**Meaning:** average CPU across the group above 50% for 10 minutes.
1. Check whether the Auto Scaling group is already scaling out (Activity tab).
2. If it is not, review the scaling policy and instance warmup, and the group's maximum capacity.

## Alarm: `ha-rds-low-storage`
**Meaning:** database free storage below 2 GB.
1. Check what is growing (table sizes).
2. Increase allocated storage (RDS > Modify) or clean up data.

## Page shows "Database unavailable"
1. Session Manager into an instance, then `sudo tail -30 /var/log/app.log` and read the last "DB read error".

| Message contains | Likely cause | Action |
|---|---|---|
| `Access denied` | Password in Parameter Store does not match the database | Update `/ha/db_password` to match, then start an instance refresh |
| `Can't connect` / `timed out` | Wrong endpoint, or `db-sg` does not allow `app-sg` on 3306, or database down | Verify endpoint in user data, the `db-sg` inbound rule, and RDS status |
| `ParameterNotFound` | Parameter name mismatch | Create or rename the parameter to `/ha/db_password` |
| `AccessDenied` (SSM) | Instance role missing read access | Attach `AmazonSSMReadOnlyAccess` (or a scoped policy) |

The app caches the password until the instance is replaced, so after changing it run an instance refresh.

## Deploy a new application version
1. EC2 > Launch templates > `ha-web-lt` > Modify template (create new version) with updated user data.
2. Set it as the default version.
3. Auto Scaling group > Instance refresh > Start (minimum healthy 50%, warmup 120 s).
4. Watch Target group health until the refresh reports Successful.

## Roll back
1. Set the previous launch template version as default.
2. Start another instance refresh.

## Query logs
CloudWatch > Logs Insights > log group `/ha/app`:
- Requests per instance: `filter @message like /GET/ | stats count(*) by @logStream`
- Errors over time: `filter @message like /error/ | stats count() by bin(5m)`

## Tear down (lab)
See [cost-and-teardown.md](cost-and-teardown.md) for the order of deletion.
