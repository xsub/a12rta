#!/usr/bin/env python3
# A12RTA v2: AnotherOne 2 Rule Them All (Refactored)
# Asynchronous log monitor with auto-reconnect, streaming and multiplexing.

import argparse
import asyncio
import asyncssh
import datetime
import logging
import signal
import yaml
import re
import os
from pathlib import Path
import json
from pydantic import BaseModel, ValidationError, field_validator
from typing import List, Optional

logging.basicConfig(filename='a12rta.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class HostConfig(BaseModel):
    host: str
    user: Optional[str] = None
    is_localhost: bool = False
    key_filename: Optional[str] = None
    log_files: List[str]
    buffer_lines: int = 10
    root_access_type: str = "sudo"
    filters: Optional[List[str]] = None
    output_format: str = "compact"  # Options: compact, iso8601, json

    @field_validator('log_files', mode='before')
    @classmethod
    def parse_log_files(cls, v):
        return [v] if isinstance(v, str) else v

READ_CHUNK = 4 * 1024 * 1024

async def tail_file(host_config: HostConfig, log_file: str, conn: asyncssh.SSHClientConnection, queue: asyncio.Queue):
    logging.info(f"[{host_config.host}] Starting to poll {log_file}")
    regexes = [re.compile(f) for f in host_config.filters] if host_config.filters else []

    offset = None

    while True:
        try:
            cmd_size = f"{host_config.root_access_type} sh -c 'wc -c < {log_file}'"
            res_size = await conn.run(cmd_size, check=False)
            if res_size.exit_status != 0:
                await asyncio.sleep(1)
                continue

            try:
                size = int(res_size.stdout.strip())
            except ValueError:
                await asyncio.sleep(1)
                continue

            if offset is None:
                offset = size
                await asyncio.sleep(1)
                continue

            if size < offset:
                offset = 0
            if size == offset:
                await asyncio.sleep(1)
                continue

            cmd_data = f"{host_config.root_access_type} sh -c 'tail -c +{offset + 1} {log_file} | head -c {READ_CHUNK}'"
            res_data = await conn.run(cmd_data, encoding=None, check=False)

            if res_data.exit_status != 0 and not res_data.stdout:
                await asyncio.sleep(1)
                continue

            data = res_data.stdout
            if not data:
                await asyncio.sleep(1)
                continue

            nl = data.rfind(b'\n')
            if nl < 0:
                await asyncio.sleep(1)
                continue

            lines_data = data[:nl].decode('utf-8', errors='replace')
            offset = offset + nl + 1

            for line in lines_data.splitlines():
                line = line.strip()
                if not line:
                    continue
                if regexes and not any(r.search(line) for r in regexes):
                    continue
                await queue.put((host_config, log_file, line))

        except asyncio.CancelledError:
            break
        except asyncssh.Error as e:
            logging.error(f"[{host_config.host}] SSH read error on {log_file}: {e}")
            raise
        except Exception as e:
            logging.error(f"[{host_config.host}] Unexpected read error on {log_file}: {e}")

        await asyncio.sleep(1)

async def tail_local_file(host_config: HostConfig, log_file: str, queue: asyncio.Queue):
    logging.info(f"[{host_config.host}] Starting to poll locally {log_file}")
    
    regexes = [re.compile(f) for f in host_config.filters] if host_config.filters else []

    offset = None
    p = Path(log_file)

    while True:
        try:
            if not p.exists():
                await asyncio.sleep(1)
                continue

            size = p.stat().st_size

            if offset is None:
                offset = size
                await asyncio.sleep(1)
                continue

            if size < offset:
                offset = 0
            if size == offset:
                await asyncio.sleep(1)
                continue

            with p.open("rb") as fh:
                fh.seek(offset)
                data = fh.read(READ_CHUNK)
                
            nl = data.rfind(b'\n')
            if nl < 0:
                await asyncio.sleep(1)
                continue

            lines_data = data[:nl].decode('utf-8', errors='replace')
            offset = offset + nl + 1

            for line in lines_data.splitlines():
                line = line.strip()
                if not line:
                    continue
                if regexes and not any(r.search(line) for r in regexes):
                    continue
                await queue.put((host_config, log_file, line))
                
        except asyncio.CancelledError:
            break
        except Exception as e:
            logging.error(f"[{host_config.host}] Local read error on {log_file}: {e}")
            await asyncio.sleep(5)

        await asyncio.sleep(1)

async def local_worker(host_config: HostConfig, queue: asyncio.Queue):
    msg = f"Initializing localhost tailing ({host_config.host})."
    logging.info(msg)
    print(msg)
    
    tasks = [
        asyncio.create_task(tail_local_file(host_config, log, queue))
        for log in host_config.log_files
    ]
    
    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        for t in tasks:
            t.cancel()

async def host_worker(host_config: HostConfig, queue: asyncio.Queue):
    while True:
        try:
            connect_kwargs = {
                "host": host_config.host,
                "username": host_config.user,
                "known_hosts": None,
            }
            if host_config.key_filename:
                connect_kwargs["client_keys"] = [host_config.key_filename]

            logging.info(f"[{host_config.host}] Connecting...")
            
            async with asyncssh.connect(**connect_kwargs) as conn:
                msg = f"Successfully connected to {host_config.host}."
                logging.info(msg)
                print(msg)
                
                tasks = [
                    asyncio.create_task(tail_file(host_config, log, conn, queue))
                    for log in host_config.log_files
                ]
                
                await asyncio.gather(*tasks)
                
        except asyncssh.Error as e:
            msg = f"[{host_config.host}] Connection error/disconnected: {e}. Retrying in 10s..."
            logging.error(msg)
            print(f"ERROR: {msg}")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logging.error(f"[{host_config.host}] Error: {e}")
        
        await asyncio.sleep(10)

async def consumer(queue: asyncio.Queue):
    try:
        while True:
            host_config, log_file, data = await queue.get()
            dt = datetime.datetime.now()
            
            if host_config.output_format == "json":
                output = json.dumps({
                    "timestamp": dt.isoformat(),
                    "host": host_config.host,
                    "file": log_file,
                    "message": data
                })
                print(output, flush=True)
            elif host_config.output_format == "iso8601":
                print(f"[{dt.isoformat()}] {host_config.host} -> {log_file} | {data}", flush=True)
            else: # compact default
                print(f"@{dt:%Y-%m-%d %H:%M:%S} {host_config.host}:{log_file}:\n{data}\n-----", flush=True)
                
            queue.task_done()
    except asyncio.CancelledError:
        pass

async def main(filename: str):
    try:
        with open(filename) as f:
            raw_config = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Configuration file not found: {filename}")
        return

    hosts = []
    for idx, item in enumerate(raw_config):
        if 'log_file' in item and 'log_files' not in item:
            item['log_files'] = [item.pop('log_file')]
        
        try:
            hosts.append(HostConfig(**item))
        except ValidationError as e:
            print(f"Configuration error for host #{idx}:\n{e}")
            continue

    if not hosts:
        print("No valid host configuration found. Exiting.")
        return

    queue = asyncio.Queue()
    consumer_task = asyncio.create_task(consumer(queue))
    workers = []
    for host in hosts:
        if getattr(host, 'is_localhost', False) or host.host in ('localhost', '127.0.0.1'):
            workers.append(asyncio.create_task(local_worker(host, queue)))
        else:
            workers.append(asyncio.create_task(host_worker(host, queue)))

    try:
        await asyncio.gather(*workers)
    except asyncio.CancelledError:
        print("\nMain loop interrupted. Waiting for graceful shutdown...")
    finally:
        for w in workers:
            w.cancel()
        consumer_task.cancel()
        await asyncio.gather(*workers, consumer_task, return_exceptions=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--filename', type=str, default='hosts.yml', help='YAML file containing host configurations.')
    args = parser.parse_args()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    main_task = loop.create_task(main(args.filename))
    
    def shutdown_handler():
        print("Shutdown signal received (Ctrl+C). Shutting down...")
        main_task.cancel()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, shutdown_handler)
        except NotImplementedError:
            pass

    try:
        loop.run_until_complete(main_task)
    except asyncio.CancelledError:
        print("Successfully shut down.")
    finally:
        loop.close()