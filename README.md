# a12rta - another one to rule them all
#### A simple Python (asyncio+fabric, producer-consumer pattern based) log monitor for arbitrary number of remote machines.
----

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
10. Update the license to be permissive.
