#!/usr/bin/env python3
#A12RTA: AnotherOne 2 Rule Them All
#Script tails logs on N-boxes (ssh)
#(c)2023 Pawel.Suchanecki@gmail.com

import asyncio
import datetime
import time
from fabric import Connection
from asyncio.queues import Queue

hosts = [
    {
        'host': 'purplemanul.puffyclouds.xyz',
        'user': 'almalinux',
        'key_filename': '/Users/pawelsuchanecki/.ssh/id_rsa',
        'log_file': '/var/log/nginx/access.log-20230222',
        'delay': 5,
        'buffer_lines': 10
    },
    {
        'host': 'refurby',
        'user': 'pablo',
        'key_filename': '/Users/pawelsuchanecki/.ssh/id_rsa',
        'log_file': '/var/log/syslog',
        'delay': 60,
        'buffer_lines': 5
    }
]

async def producer(queue: Queue, host: dict):
    conn = Connection(host['host'], user=host['user'], connect_kwargs={'key_filename': host['key_filename']})
    with conn.cd('/tmp'):
        tail_cmd = f"sudo tail -n {host['buffer_lines']} {host['log_file']}"
        old_data = ()
        while True:
            channel = conn.run(command=tail_cmd, hide='both')
            data = channel.stdout.splitlines()
            if old_data != data:
                old_d=set(old_data)
                delta_data = [x for x in data if x not in old_d]
                for d in delta_data:
                    await queue.put((host['host'], host['log_file'], str(d)))
            old_data = data.copy()
            data.clear()
            await asyncio.sleep(host['delay'])
    conn.close()

async def consumer(queue: Queue):
    while True:
        line = await queue.get()
        host, log_file, data = line
        dt = datetime.datetime.fromtimestamp(time.time())
        print (f"@{dt} {host}:{log_file}:\n{data}\n-----", end = '\n', flush = True)
        queue.task_done()

async def main():
    queue = asyncio.Queue()
    producers = [asyncio.create_task(producer(queue, host)) for host in hosts]
    consumer_task = asyncio.create_task(consumer(queue))
    await asyncio.gather(*producers)
    await queue.join()
    consumer_task.cancel()

if __name__ == '__main__':
    asyncio.run(main())


# TODOs:
# 1. Extend number of monitored log files to arbitrary number per host
# 2. Add support for localhost (non-ssh)
# 3. Use default values if not defined/overridden for host
# 4. Move host configs to .yaml
# 5. Add options for different sorting of message output
# 6. Add (critical) regex based error message filters triggering actions
# 7. Find how to be able to use `tail -f`, maybe extend Paramiko/Fabric
# 8. Serve it as a page from secure host with mini web server (w SSL)
# 9. How to change password less sudo to more strict sudoers.d policy
# 10. Update the license to be permissive.

