# a12rta - Another One to Rule Them All
#### An asynchronous log monitoring tool for multiple remote machines, utilizing asyncio, fabric, and the producer-consumer pattern (Python).
----

### Example run:

```shell 
Connected to Host_A.
Failed to connect to Host_B: timed out
Connected to Host_C.
ERROR: Error executing command on host Host_C: Encountered a bad command exit code!
@2023-08-16 00:52:08.891383 Host_A:/var/log/nginx/access.log-20230622:
ANONYMIZED_IP - - [15/Aug/2023:21:21:21 +0000] "GET / HTTP/1.1" 200 19248 "-" "UserAgent123" "-"
-----
@2023-08-16 00:52:08.891456 Host_A:/var/log/nginx/access.log-20230622:
ANONYMIZED_IP - - [15/Aug/2023:21:21:22 +0000] "GET /images/logo.png HTTP/1.1" 200 22916 "-" "UserAgent123" "-"
-----
@2023-08-16 00:52:08.891477 Host_A:/var/log/nginx/access.log-20230622:
ANONYMIZED_IP - - [15/Aug/2023:21:22:16 +0000] "GET / HTTP/1.1" 404 548 "-" "UserAgent456" "-"
-----
@2023-08-16 00:52:08.891495 Host_A:/var/log/nginx/access.log-20230622:
ANONYMIZED_IP - - [15/Aug/2023:21:42:05 +0000] "GET / HTTP/1.1" 404 146 "-" "UserAgent789" "-"
-----
@2023-08-16 00:52:08.891511 Host_A:/var/log/nginx/access.log-20230622:
ANONYMIZED_IP - - [15/Aug/2023:21:42:06 +0000] "PRI * HTTP/2.0" 400 150 "-" "-" "-"
-----
@2023-08-16 00:52:08.891527 Host_A:/var/log/nginx/access.log-20230622:
ANONYMIZED_IP - - [15/Aug/2023:21:56:22 +0000] "GET /owa/auth/x.js HTTP/1.1" 404 5780 "-" "UserAgentFinal1" "-"
-----
@2023-08-16 00:52:08.891543 Host_A:/var/log/nginx/access.log-20230622:
ANONYMIZED_IP - - [15/Aug/2023:22:09:59 +0000] "GET /webclient/ HTTP/1.1" 404 5780 "-" "UserAgentFinal2" "-"
-----
@2023-08-16 00:52:08.891560 Host_A:/var/log/nginx/access.log-20230622:
ANONYMIZED_IP - - [15/Aug/2023:22:12:52 +0000] "GET / HTTP/1.1" 404 548 "-" "UserAgent789" "-"
-----
@2023-08-16 00:52:08.891577 Host_A:/var/log/nginx/access.log-20230622:
ANONYMIZED_IP - - [15/Aug/2023:22:29:42 +0000] "\x03\x00\x00\x13\x0E\xE0\x00\x00\x00\x00\x00\x01\x00\x08\x00\x02\x00\x00\x00" 400 150 "-" "-" "-"
-----
@2023-08-16 00:52:08.891593 Host_A:/var/log/nginx/access.log-20230622:
ANONYMIZED_IP - - [15/Aug/2023:22:47:36 +0000] "GET / HTTP/1.1" 404 146 "-" "UserAgentFinal3" "-"
-----
```

### Example config file:

```yaml
- host: Host_A
  user: ANONYMIZED_USER_A
  key_filename: /Users/pawelsuchanecki/.ssh/id_rsa
  login_timeout: 5
  log_file: /var/log/nginx/access.log-20230622
  delay: 5
  buffer_lines: 10
  root_access_type: sudo

- host: Host_B
  user: ANONYMIZED_USER_B
  key_filename: /Users/pawelsuchanecki/.ssh/id_rsa
  login_timeout: 3 
  log_file: /var/log/syslog
  delay: 60
  buffer_lines: 5
  root_access_type: sudo

- host: Host_C 
  user: pawel 
  key_filename: /Users/pawelsuchanecki/.ssh/id_rsa
  login_timeout: 8 
  log_file: /var/log/authlog
  delay: 60
  buffer_lines: 5
  root_access_type: doas
```

### TODOs:

0. Handle Exceptions like "Host is down" ~~& shorter timeouts for ssh~~
1. Extend number of monitored log files to arbitrary number per host
2. Add support for localhost (non-ssh)
3. Use default values if not defined/overridden for host
4. ~~Move host configs to .yaml~~
5. Add options for different sorting of message output
6. Add (critical) regex based error message filters triggering actions
7. Find how to be able to use `tail -f`, maybe extend Paramiko/Fabric
8. Serve it as a page from secure host with mini web server (w SSL)
9. How to change password less sudo to more strict sudoers.d policy
10. ~~Update the license to be permissive.~~
