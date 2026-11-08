# Test report

Environment: `ap-south-1`, two Availability Zones, Auto Scaling group `ha-web-asg` (min 2, desired 2, max 4), ALB `ha-alb`, RDS MySQL `ha-db` (single-AZ).
Tools: Windows PowerShell for request monitoring and load generation, AWS console for observation. Times below are IST unless marked UTC (the console shows UTC in some places).

## Summary

| # | Test | Outcome |
|---|---|---|
| 1 | Instance termination | Passed |
| 2 | Load-based scale-out | Passed: automatic scale-out from 2 to 4 instances |
| 3 | Simulated AZ capacity loss | Passed: no failed requests in captured output |
| 4 | Database restart | Web tier stayed up; database unavailable about 14 seconds; data preserved |
| 5 | Security checks | Passed |

## Test 1: instance termination

- **Objective:** confirm the site survives the loss of one web server and the Auto Scaling group replaces it.
- **Method:** a PowerShell loop requested the site every second and printed the time, instance ID and AZ. One instance of `ha-web-asg` was terminated from the console.
- **Expected:** requests continue to be served by the remaining instance; a replacement launches automatically.
- **Observed:** requests continued to be served by the surviving instance and the Auto Scaling group launched a replacement. Timing is visible in the evidence screenshot.
- **Evidence:** `screenshots/test1-instance-termination-1.png`, `screenshots/test1-instance-termination-2.png`

## Test 2: load-based scale-out

- **Objective:** confirm the Auto Scaling group adds capacity under sustained load without manual action.
- **Method:** 10 parallel PowerShell jobs sent continuous requests to the ALB's `/health` page. Scaling policy: target tracking on ALB request count per target, target value 30, warmup 120 seconds.
- **Expected:** the policy's high alarm triggers and the group launches additional instances up to the maximum of 4.
- **Observed:**
  - The alarm `TargetTracking-ha-web-asg-AlarmHigh` entered the ALARM state at 11:25 UTC (16:55 IST) and the policy changed desired capacity from 2 to 4.
  - Two new instances launched within about 11 seconds of the alarm and were in "waiting for instance warm up" in the Activity tab.
  - The target group then showed 4 of 4 targets healthy, 0 unhealthy.
  - The dashboard shows request count and healthy host count rising together, CPU peaking near 19% (below the 50% CPU alarm threshold), so the scale-out came from the request-count policy rather than the CPU alarm. Unhealthy host count briefly rose while the new targets passed their first health checks.
- **Limitations:** scale-in back to 2 instances was not captured. The first load attempt earlier in the session did not trigger scaling (see issues below).
- **Evidence:** `screenshots/test2-asg-activity.png`, `screenshots/test2-dashboard-load.png`, `screenshots/test2-target-group-scaled.png`, `screenshots/Asg_scaling_policy.png`

## Test 3: simulated AZ capacity loss

- **Objective:** confirm the application keeps serving when one AZ's application capacity is unavailable.
- **Method:** with the monitor loop running, `private-app-subnet-a` was removed from the Auto Scaling group's subnet list, forcing all capacity into AZ b. The subnet was later added back.
- **Expected:** requests continue from AZ b; the group relocates capacity.
- **Observed:**
  - At 12:56 requests were served alternately by instances in `ap-south-1a` and `ap-south-1b`.
  - By 12:58 every response came from an instance in `ap-south-1b`.
  - No failed requests appear in the captured output. The monitor was restarted between 12:56 and 12:58, so about two minutes of that window were not recorded.
  - The Auto Scaling group view shows the `ap-south-1a` instance terminating while two instances were in service in `ap-south-1b`.
- **Limitation:** this simulates losing application capacity in one AZ. It is not a real AWS outage and does not test the database or load balancer nodes in that AZ.
- **Evidence:** `screenshots/test3-az-failure-monitor.png`, `screenshots/test3-asg-instances-1b.png`

## Test 4: database restart

- **Objective:** observe application behaviour during a database restart and confirm data persistence.
- **Method:** a note was added, then the RDS instance was rebooted while a monitor printed web and database status every two seconds.
- **Expected:** the web tier stays up (its health check does not use the database); the page reports the database as unavailable during the restart and recovers afterwards; saved notes remain.
- **Observed:**
  - The database showed as unavailable from 12:43:07 and was available again by 12:43:21, about 14 seconds.
  - The web tier reported OK on every check throughout the restart.
  - RDS events recorded the instance shutdown and restart at 12:43.
  - The note added before the restart was still present afterwards, along with older notes written by instances that had since been replaced.
- **Limitation:** the database is single-AZ, so this is a restart test, not a Multi-AZ failover test.
- **Evidence:** `screenshots/test4-restart-monitor.png`, `screenshots/test4-rds-events.png`, `screenshots/test4-notes-preserved.png`

## Test 5: security checks

- **Objective:** confirm only intended ports are reachable from the internet.
- **Method:** `Test-NetConnection` from a laptop outside AWS.

| Check | Expected | Observed |
|---|---|---|
| ALB port 80 | Open | TcpTestSucceeded: True |
| ALB port 22 | Closed | TCP connect failed, TcpTestSucceeded: False |
| RDS port 3306 | Closed | TCP connect failed; the endpoint resolved to a private address (10.0.21.113) |

- **Note:** instances launch in private subnets with public IP assignment disabled by design; a per-instance public IP check was not captured.
- **Evidence:** `screenshots/test5-security-checks.png`

## Issues encountered and fixes

| Issue | Cause | Fix |
|---|---|---|
| RDS password rejected | Password contained a disallowed symbol (`/ ' " @`) | Used a letters-and-numbers password |
| Application showed "Database unavailable" | Password and parameter name mismatch, then a connection timeout | Re-saved the password in Parameter Store under the exact name the app reads; corrected the database security group so `app-sg` could reach port 3306 |
| Alarm created on the wrong metric | Picked a client-error (4XX) metric filtered to one AZ | Recreated alarms on load-balancer-level metrics |
| CloudShell unavailable | Not enabled for the account | Used PowerShell on a laptop for monitoring and load tests |
| Standby (Multi-AZ) option unavailable for RDS | Account or plan limitation | Documented single-AZ database as a known limitation |
| First load test did not trigger scale-out | Scaling configuration and traffic had to be verified | Checked the scaling policy, alarm state and that requests reached the ALB, then reran the load; the policy then scaled out automatically |
