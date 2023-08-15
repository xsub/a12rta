#!/usr/bin/env python3
# A12RTA: AnotherOne 2 Rule Them All
# Script tails logs on N-boxes (ssh)
# (c)2023 Pawel.Suchanecki@gmail.com

import argparse
import asyncio
import datetime
import logging
import time
import os
import signal
import yaml
from asyncio.queues import Queue
from asyncio.exceptions import CancelledError
from fabric import Connection
from functools import wraps


# Initialize the logger
logging.basicConfig(filename='a12rta.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Create a signal handler
def sigint_handler(main_task):
    msg = "Ctrl+C received. Shutting down."
    logging.error(msg)
    print("\n"+msg)
    main_task.cancel()

def handle_run_errors(func):
    @wraps(func)
    async def wrapper(queue: Queue, host: dict):
        try:
            return await func(queue, host)
        except TimeoutError as e:
            msg = f"ERROR: Connection to {host['host']} timed out after {host['login_timeout']} seconds."
            logging.error(msg)
            print(msg)
        except Exception as e:
            if hasattr(e, 'result'):
                msg = f"ERROR: Error executing command on host {host['host']}: Encountered a bad command exit code!"
                logging.error(msg)
                logging.error(f"Command: '{e.result.command}'")
                logging.error(f"Exit code: {e.result.exited}")
                logging.error(f"Stdout: {e.result.stdout}")
                logging.error(f"Stderr: {e.result.stderr}")
                print(msg)
            else:
                msg = f"ERROR: {e}"
                logging.error(msg)
                print(msg)
    return wrapper

@handle_run_errors
async def producer(queue: Queue, host: dict):
    conn = Connection(
        host['host'],
        user=host['user'],
        connect_kwargs={'key_filename': host['key_filename'], 'timeout': host['login_timeout']}
    )

    logging.info(f"Making connection to host {host['host']}, monitoring {host['log_file']}")

    try:
        # Test the connection by running a simple command
        conn.run('echo "test"', hide='both')
    except Exception as e:
        msg=f"Failed to connect to {host['host']}: {e}"
        logging.error(msg)
        print(msg)
        return

    with conn.cd('/tmp'):
        msg=f"Connected to {host['host']}."
        logging.info(msg)
        print(msg) 
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
    try:
        while True:
            line = await queue.get()
            host, log_file, data = line
            dt = datetime.datetime.fromtimestamp(time.time())
            print(f"@{dt} {host}:{log_file}:\n{data}\n-----", end='\n', flush=True)
            queue.task_done()
    except CancelledError:
        pass

async def main(filename: str):
    with open(filename) as f:
        hosts = yaml.safe_load(f)
    queue = asyncio.Queue()
    producers = [asyncio.create_task(producer(queue, host)) for host in hosts]
    consumer_task = asyncio.create_task(consumer(queue))
    try:
        await asyncio.gather(*producers)
    except CancelledError:
        print("Main coroutine cancelled. Stopping the event loop.")
    finally:
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

    loop = asyncio.get_event_loop()
    main_task = loop.create_task(main(args.filename))
    loop.add_signal_handler(signal.SIGINT, lambda: sigint_handler(main_task))
    try:
        loop.run_until_complete(main_task)
    except asyncio.CancelledError:
        print("Main task cancelled.")
    finally:
        loop.close()