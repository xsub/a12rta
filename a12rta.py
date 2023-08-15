#!/usr/bin/env python3
# A12RTA: AnotherOne 2 Rule Them All
# Script tails logs on N-boxes (ssh)
# (c)2023 Pawel.Suchanecki@gmail.com

import argparse
import asyncio
import datetime
import time
import os
from asyncio.queues import Queue
from fabric import Connection
import yaml
from functools import wraps

def handle_run_errors(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except TimeoutError as e:
            host = args[1]
            print(f"ERROR: Connection to {host['host']} timed out after {host['login_timeout']} seconds.")
            error_file_path = f"errors-{host['host']}.log"
            with open(error_file_path, 'a') as error_file:
                error_file.write(f"ERROR: Connection to {host['host']} timed out after {host['login_timeout']} seconds.")
                error_file.write(f"Timestamp: {datetime.datetime.now()}\n")
                error_file.write(f"Host: {host['host']}\n")
                error_file.write(f"Error: {str(e)}\n")
                error_file.write("---------\n")
            print(f"Error details written to {os.path.abspath(error_file_path)}")
            return
        except Exception as e:
            host = args[1]
            if hasattr(e, 'result'):
                error_file_path = f"errors-{host['host']}.log"
                with open(error_file_path, "a") as error_file:
                    error_file.write("ERROR: Error executing command on host {host['host']}: Encountered a bad command exit code!")
                    error_file.write(f"Timestamp: {datetime.datetime.now()}\n")
                    error_file.write(f"Command: '{e.result.command}'\n")
                    error_file.write(f"Exit code: {e.result.exited}\n")
                    error_file.write(f"Stdout: {e.result.stdout}\n")
                    error_file.write(f"Stderr: {e.result.stderr}\n")
                    error_file.write("-----\n")
                print(f"ERROR: Error executing command on host {host['host']}: Encountered a bad command exit code!")
                print(f" +-- TS: {datetime.datetime.now()}")
                print(f" +-- CMD: '{e.result.command}'")
                print(f" +-- EXIT CODE: {e.result.exited}")
                print(f" +-- LOG FILE: Error details written to {os.path.abspath(error_file_path)}")
                print(f"Error details written to {os.path.abspath(error_file_path)}")
                return
    return wrapper

@handle_run_errors
async def producer(queue: Queue, host: dict):
    conn = Connection(
        host['host'],
        user=host['user'],
        connect_kwargs={'key_filename': host['key_filename'], 'timeout': host['login_timeout']}
    )
  
    print(f"Making connection to host {host['host']}, monitoring {host['log_file']}")
   
    try:
        # Test the connection by running a simple command
        conn.run('echo "test"', hide='both')
    except Exception as e:
        print(f"ERROR: Failed to connect to {host['host']}: {e}")
        return
   
    with conn.cd('/tmp'):
        print(f"SUCCESS: connected to {host['host']}.")
        tail_cmd = f"{host['root_access_type']} tail -n {host['buffer_lines']} {host['log_file']}"
        old_data = ()
        while True:
            channel = conn.run(command=tail_cmd, hide='both')
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

