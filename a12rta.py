#!/usr/bin/env python3
# A12RTA v2: AnotherOne 2 Rule Them All (Refactored)
# Asynchroniczny monitor logów z auto-reconnectem, strumieniowaniem i multiplexingiem.

import argparse
import asyncio
import asyncssh
import datetime
import logging
import signal
import yaml
import re
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

    @field_validator('log_files', mode='before')
    @classmethod
    def parse_log_files(cls, v):
        return [v] if isinstance(v, str) else v

async def tail_file(host_config: HostConfig, log_file: str, conn: asyncssh.SSHClientConnection, queue: asyncio.Queue):
    cmd = f"{host_config.root_access_type} tail -n {host_config.buffer_lines} -F {log_file}"
    logging.info(f"[{host_config.host}] Rozpoczynam nasłuch {log_file}")
    
    regexes = [re.compile(f) for f in host_config.filters] if host_config.filters else []

    try:
        async with conn.create_process(cmd) as process:
            async for line in process.stdout:
                line = line.strip()
                if not line:
                    continue
                
                if regexes and not any(r.search(line) for r in regexes):
                    continue

                await queue.put((host_config.host, log_file, line))

    except asyncssh.Error as e:
        logging.error(f"[{host_config.host}] Błąd SSH odczytu {log_file}: {e}")
    except Exception as e:
        logging.error(f"[{host_config.host}] Nieoczekiwany błąd odczytu {log_file}: {e}")


async def tail_local_file(host_config: HostConfig, log_file: str, queue: asyncio.Queue):
    cmd = f"{host_config.root_access_type} tail -n {host_config.buffer_lines} -F {log_file}"
    logging.info(f"[{host_config.host}] Rozpoczynam nasłuch lokalny {log_file}")
    
    regexes = [re.compile(f) for f in host_config.filters] if host_config.filters else []

    while True:
        try:
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            async for line in process.stdout:
                line = line.decode('utf-8', errors='replace').strip()
                if not line:
                    continue
                
                if regexes and not any(r.search(line) for r in regexes):
                    continue

                await queue.put((host_config.host, log_file, line))
                
        except asyncio.CancelledError:
            if 'process' in locals():
                try:
                    process.terminate()
                except:
                    pass
            break
        except Exception as e:
            logging.error(f"[{host_config.host}] Błąd lokalnego odczytu {log_file}: {e}")
            await asyncio.sleep(5)

async def local_worker(host_config: HostConfig, queue: asyncio.Queue):
    msg = f"Inicjalizacja nasłuchu na localhost ({host_config.host})."
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

            logging.info(f"[{host_config.host}] Łączenie...")
            
            async with asyncssh.connect(**connect_kwargs) as conn:
                msg = f"Połączono pomyślnie z {host_config.host}."
                logging.info(msg)
                print(msg)
                
                tasks = [
                    asyncio.create_task(tail_file(host_config, log, conn, queue))
                    for log in host_config.log_files
                ]
                
                await asyncio.gather(*tasks)
                
        except asyncssh.Error as e:
            msg = f"[{host_config.host}] Błąd połączenia/rozłączenie: {e}. Ponawiam za 10s..."
            logging.error(msg)
            print(f"BŁĄD: {msg}")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logging.error(f"[{host_config.host}] Błąd: {e}")
        
        await asyncio.sleep(10)

async def consumer(queue: asyncio.Queue):
    try:
        while True:
            host, log_file, data = await queue.get()
            dt = datetime.datetime.now()
            print(f"@{dt:%Y-%m-%d %H:%M:%S} {host}:{log_file}:\n{data}\n-----", flush=True)
            queue.task_done()
    except asyncio.CancelledError:
        pass

async def main(filename: str):
    try:
        with open(filename) as f:
            raw_config = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Brak pliku konfiguracyjnego {filename}")
        return

    hosts = []
    for idx, item in enumerate(raw_config):
        if 'log_file' in item and 'log_files' not in item:
            item['log_files'] = [item.pop('log_file')]
        
        try:
            hosts.append(HostConfig(**item))
        except ValidationError as e:
            print(f"Błąd konfiguracji dla hosta #{idx}:\n{e}")
            continue

    if not hosts:
        print("Brak poprawnej konfiguracji hostów. Kończenie pracy.")
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
        print("\nPrzerwano pętlę główną. Oczekiwanie na czyste zamknięcie...")
    finally:
        for w in workers:
            w.cancel()
        consumer_task.cancel()
        await asyncio.gather(*workers, consumer_task, return_exceptions=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--filename', type=str, default='hosts.yml', help='Plik YAML z konfiguracją.')
    args = parser.parse_args()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    main_task = loop.create_task(main(args.filename))
    
    def shutdown_handler():
        print("Otrzymano sygnał zamknięcia (Ctrl+C). Wyłączanie...")
        main_task.cancel()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, shutdown_handler)
        except NotImplementedError:
            pass

    try:
        loop.run_until_complete(main_task)
    except asyncio.CancelledError:
        print("Pomyślnie zamknięto.")
    finally:
        loop.close()