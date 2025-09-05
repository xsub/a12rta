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
from collections import deque
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
    print("\n" + msg)
    main_task.cancel()

def handle_run_errors(func):
    @wraps(func)
    async def wrapper(queue: Queue, host: dict):
        try:
            return await func(queue, host)
        except CancelledError:
            # Let cancellations propagate cleanly
            raise
        except TimeoutError:
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

    # Test the connection
    try:
        conn.run('echo "test"', hide='both')
    except Exception as e:
        msg = f"Failed to connect to {host['host']}: {e}"
        logging.error(msg)
        print(msg)
        return

    with conn.cd('/tmp'):
        msg = f"Connected to {host['host']}."
        logging.info(msg)
        print(msg)
        tail_cmd = f"{host['root_access_type']} tail -n {host['buffer_lines']} {host['log_file']}"
        transport = conn.client.get_transport()

        # Fix A: bounded dedupe
        seen = deque(maxlen=host['buffer_lines'])
        seen_set: set[str] = set()

        try:
            while True:
                channel = transport.open_session()
                channel.get_pty()
                channel.exec_command(tail_cmd)
                file_obj = channel.makefile('r')
                try:
                    while True:
                        line = await asyncio.to_thread(file_obj.readline)
                        if not line:
                            break
                        line = line.rstrip('\r\n')

                        if line not in seen_set:
                            # Put a single tuple on the queue
                            await queue.put((host['host'], host['log_file'], line))

                            # Maintain bounded memory
                            if len(seen) == seen.maxlen:
                                removed = seen.popleft()
                                seen_set.discard(removed)
                            seen.append(line)
                            seen_set.add(line)
                except CancelledError:
                    channel.close()
                    raise
                finally:
                    channel.close()

                # Poll interval before fetching a new batch of last N lines
                await asyncio.sleep(1)
        finally:
            conn.close()

async def consumer(queue: Queue):
    try:
        while True:
            item = await queue.get()
            host, log_file, data = item
            dt = datetime.datetime.fromtimestamp(time.time())
            # Compact timestamp, consistent output
            print(f"@{dt:%Y-%m-%d %H:%M:%S} {host}:{log_file}:\n{data}\n-----", flush=True)
            queue.task_done()
    except CancelledError:
        pass

async def main(filename: str):
    with open(filename) as f:
        hosts = yaml.safe_load(f)

    queue: Queue = asyncio.Queue()
    producers = [asyncio.create_task(producer(queue, host)) for host in hosts]
    consumer_task = asyncio.create_task(consumer(queue))

    try:
        await asyncio.gather(*producers)
    except CancelledError:
        print("Main coroutine cancelled. Stopping the event loop.")
    finally:
        consumer_task.cancel()
        # Ensure consumer finishes cleanly
        with contextlib.suppress(CancelledError, Exception):
            await consumer_task

if __name__ == '__main__':
    import contextlib

    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-f',
        '--filename',
        type=str,
        default='hosts.yml',
        help='The YAML file that contains the host configuration.'
    )
    args = parser.parse_args()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    main_task = loop.create_task(main(args.filename))
    # SIGINT (Ctrl+C) graceful shutdown
    try:
        loop.add_signal_handler(signal.SIGINT, lambda: sigint_handler(main_task))
    except NotImplementedError:
        # add_signal_handler may be unavailable on some platforms; ignore.
        pass

    try:
        loop.run_until_complete(main_task)
    except CancelledError:
        print("Main task cancelled.")
    finally:
        loop.close()
