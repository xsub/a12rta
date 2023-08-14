#!/usr/bin/env python3
# A12RTA: AnotherOne 2 Rule Them All
# Script tails logs on N-boxes (ssh)
# (c)2023 Pawel.Suchanecki@gmail.com

import argparse
import asyncio
import datetime
import time
from asyncio.queues import Queue
from fabric import Connection
import yaml


async def producer(queue: Queue, host: dict):
    conn = Connection(
        host['host'],
        user=host['user'],
        connect_kwargs={'key_filename': host['key_filename'], 'timeout': 10}
    )
    with conn.cd('/tmp'):
        print(f"Connection to host {host['host']}, monitoring {host['log_file']}")  # Add this line
        tail_cmd = f"sudo tail -n {host['buffer_lines']} {host['log_file']}"
        old_data = ()
        while True:
            try:
                channel = conn.run(command=tail_cmd, hide='both')
            except TimeoutError:
                print(f"ERROR: Connection to {host['host']} timed out.")
                return
            except Exception as e:
                print(f"ERROR: Error executing command on host {host['host']}: {e}")
                return

            data = channel.stdout.splitlines()
            if old_data != data:
                old_d = set(old_data)
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
        print(f"@{dt} {host}:{log_file}:\n{data}\n-----", end='\n', flush=True)
        queue.task_done()


async def main(filename: str):
    with open(filename) as f:
        hosts = yaml.safe_load(f)
    queue = asyncio.Queue()
    producers = [asyncio.create_task(producer(queue, host)) for host in hosts]
    consumer_task = asyncio.create_task(consumer(queue))
    await asyncio.gather(*producers)
    await queue.join()
    consumer_task.cancel()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-f',
        '--filename',
        type=str,
        default='hosts.yml',
        help='The YAML file that contains the host configuration.'
    )
    args = parser.parse_args()

    asyncio.run(main(args.filename))

