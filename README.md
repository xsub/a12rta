# a12rta - another one to rule them all
#### A simple Python (asyncio+fabric, producer-consumer pattern based) log monitor for arbitrary number of remote machines.
----

### Example run:

```shell 
➜  a12rta git:(main) ✗ python3.10 a12rta.py                                     
Connection to host purplemanul.ANONYMIZED.TLD, monitoring /var/log/nginx/access.log-20230622
Connection to host refurby, monitoring /var/log/syslog
ERROR: Connection to refurby timed out.
@2023-08-15 00:33:33.810237 purplemanul.ANONYMIZED.TLD:/var/log/nginx/access.log-20230622:
ANONYMIZED_IP - - [14/Aug/2023:22:27:29 +0000] "GET /assets/js/81.a31a5724.js HTTP/1.1" 404 548 "https://purplemanul.ANONYMIZED.TLD/repos/" "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36" "-"
-----
@2023-08-15 00:33:33.810326 purplemanul.ANONYMIZED.TLD:/var/log/nginx/access.log-20230622:
ANONYMIZED_IP - - [14/Aug/2023:22:27:29 +0000] "GET /assets/js/83.b1089bd9.js HTTP/1.1" 404 548 "https://purplemanul.ANONYMIZED.TLD/repos/" "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36" "-"
-----
@2023-08-15 00:33:33.810365 purplemanul.ANONYMIZED.TLD:/var/log/nginx/access.log-20230622:
ANONYMIZED_IP - - [14/Aug/2023:22:27:29 +0000] "GET /assets/js/82.2e896741.js HTTP/1.1" 404 548 "https://purplemanul.ANONYMIZED.TLD/repos/" "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36" "-"
-----
... (similar replacements for each line) ...
-----
@2023-08-15 00:33:33.810660 purplemanul.ANONYMIZED.TLD:/var/log/nginx/access.log-20230622:
ANONYMIZED_IP - - [14/Aug/2023:22:30:25 +0000] "GET /images/logo.png HTTP/1.1" 200 22916 "https://purplemanul.ANONYMIZED.TLD/" "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15" "-"
-----
@2023-08-15 00:33:33.810689 purplemanul.ANONYMIZED.TLD:/var/log/nginx/access.log-20230622:
ANONYMIZED_IP - - [14/Aug/2023:22:30:25 +0000] "GET /assets/img/search.83621669.svg HTTP/1.1" 200 216 "https://purplemanul.ANONYMIZED.TLD/" "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15" "-"
-----
```

### Example config file:

```yaml
- host: purplemanul.ANONYMIZED.TLD
  user: ANONYMIZED_USER
  key_filename: /Users/ANONYMIZED_USER/.ssh/id_rsa
  log_file: /var/log/nginx/access.log-20230622
  delay: 5
  buffer_lines: 10

- host: refurby
  user: ANONYMIZED_USER
  key_filename: /Users/ANONYMIZED_USER/.ssh/id_rsa
  log_file: /var/log/syslog
  delay: 60
  buffer_lines: 5
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
