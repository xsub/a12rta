# a12rta - Another One to Rule Them All

[![CI Status](https://github.com/xsub/a12rta/actions/workflows/ci.yml/badge.svg)](https://github.com/xsub/a12rta/actions/workflows/ci.yml)
[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
#### An asynchronous, Python-based log monitoring tool for multiple remote machines, utilizing asyncio, asyncssh, and the producer-consumer pattern. 

### How it Works

A12RTA uses a fully asynchronous producer-consumer architecture, implemented via Python's `asyncio` and the `asyncssh` library. The tool is designed to monitor files efficiently, with features built for scalability and fault tolerance:

*   **Byte-Offset Polling Mechanism**: Instead of keeping expensive subprocesses like `tail -F` running continuously, a12rta tracks the exact byte position (offset) of the end of each log file. During each tick, it jumps to this offset and reads up to 4MB of new data using chunk reading.
*   **Multiplexing**: For remote hosts, only **one** SSH connection is made per server. All multiple monitored logs from the same host are polled asynchronously inside this single session, drastically reducing network and CPU overhead.
*   **Safe Chunking**: It ensures logs are never truncated. The reader stops strictly at the last full newline character (`\n`), deferring any partial lines to the next polling cycle.

#### Architecture Diagram

```mermaid
graph TD;
    subyaml[(hosts.yml)] --> ConfigValidator(Pydantic Configuration)
    ConfigValidator --> Dispatcher(Dispatcher)
    
    Dispatcher -->|Spawns| LocalWorker(Local Worker)
    Dispatcher -->|Spawns| RemoteWorker1(Remote Worker: Host A)
    Dispatcher -->|Spawns| RemoteWorker2(Remote Worker: Host B)
    
    LocalWorker -->|Python IO Seek| LocalLog["/var/log/system.log"]
    
    RemoteWorker1 -->|Single SSH Conn| NodeA(Host A)
    NodeA -->|Offset Polling| LogA1["/var/log/nginx/access.log"]
    NodeA -->|Offset Polling| LogA2["/var/log/nginx/error.log"]
    
    RemoteWorker2 -->|Single SSH Conn| NodeB(Host B)
    NodeB -->|Offset Polling| LogB1["/var/log/syslog"]

    LocalWorker -.-> |Async Queue| ConsumerQueue((Message Queue))
    RemoteWorker1 -.-> |Async Queue| ConsumerQueue
    RemoteWorker2 -.-> |Async Queue| ConsumerQueue
    
    ConsumerQueue --> Formatter(Output Formatter)
    Formatter --> |Compact / ISO8601 / JSON| STDOUT>Standard Output]
```

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
Ctrl+C received. Shutting down.
Main coroutine cancelled. Stopping the event loop.
```

### Example config file:

```yaml
- host: Host_A
  user: almalinux
  key_filename: /Users/pawelsuchanecki/.ssh/id_rsa
  login_timeout: 5
  log_file: /var/log/nginx/access.log-20230622
  delay: 5
  buffer_lines: 10
  root_access_type: sudo

- host: Host_B
  user: pablo
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

0. ~~Handle Exceptions like "Host is down" & shorter timeouts for ssh~~ (Added async auto-reconnect logic)
1. ~~Extend number of monitored log files to arbitrary number per host~~ (Implemented multiplexing over single SSH connection)
2. ~~Add support for localhost (non-ssh)~~ (Implemented local streaming bypassing SSH entirely)
3. ~~Use default values if not defined/overridden for host~~ (Implemented using Pydantic models)
4. ~~Move host configs to .yaml~~
5. ~~Add options for different sorting of message output~~ (Added `output_format` with compact, iso8601, json support)
6. ~~Add (critical) regex based error message filters triggering actions~~ (Implemented Regex client-side filtering)
7. ~~Find how to be able to use `tail -f`, maybe extend Paramiko/Fabric~~ (Migrated to `asyncssh` with advanced byte-offset polling)
8. Serve it as a page from secure host with mini web server (w SSL)
9. How to change password less sudo to more strict sudoers.d policy
10. ~~Update the license to be permissive.~~