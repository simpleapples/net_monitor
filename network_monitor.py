#!/usr/bin/env python3

import subprocess
import logging
import sys
import time
import argparse
import threading
from datetime import datetime
from pathlib import Path
from typing import Tuple, Dict
from logging.handlers import TimedRotatingFileHandler


class NetworkMonitor:
    
    def __init__(self, log_dir: str = "./logs", timeout: int = 1, targets: Dict = None):
        
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        self.timeout = timeout
        
        self.targets = targets or {
            'ping': '8.8.8.8',
            'dns': 'google.com',
            'tcp': ('google.com', 80)
        }
        
        self._setup_logging()
        
        self.logger.info("Network monitor started")
        self.logger.info(f"Targets: {self.targets}")
        self.logger.info(f"Timeout: {self.timeout}s")
    
    def _setup_logging(self):
        log_file = self.log_dir / "network_monitor.log"
        
        self.logger = logging.getLogger('NetworkMonitor')
        self.logger.setLevel(logging.INFO)
        
        fh = TimedRotatingFileHandler(
            str(log_file),
            when='midnight',
            interval=1,
            backupCount=365,
            encoding='utf-8'
        )
        fh.setLevel(logging.INFO)
        fh.namer = lambda name: name.replace('.log', '') + '.log'
        
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)
        
        self.fh = fh
    
    def check_ping(self) -> Tuple[bool, str]:
        target = self.targets['ping']
        result = subprocess.run(
            ['ping', '-c', '1', '-W', str(self.timeout * 1000), target],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return True, result.stdout
        else:
            error_msg = f"✗ PING {target} failed (return code: {result.returncode})"
            self.logger.error(error_msg)
            # self.logger.error(f"PING output:\n{result.stdout}\n{result.stderr}")
            return False, result.stdout + result.stderr
    
    def check_dns(self) -> Tuple[bool, str]:
        target = self.targets['dns']
        try:
            result = subprocess.run(
                ['dig', '+tries=1', f'+time={self.timeout}', target],
                capture_output=True,
                text=True,
                timeout=self.timeout + 1
            )
            if result.returncode == 0 and 'status: NOERROR' in result.stdout:
                return True, "DNS success"
            else:
                error_msg = f"✗ DNS {target} failed"
                self.logger.error(error_msg)
                # self.logger.error(f"DIG output:\n{result.stdout}\n{result.stderr}")
                return False, error_msg
        except subprocess.TimeoutExpired:
            error_msg = f"✗ DNS {target} timeout"
            self.logger.error(error_msg)
            return False, error_msg
    
    def check_tcp(self) -> Tuple[bool, str]:
        host, port = self.targets['tcp']
        try:
            result = subprocess.run(
                ['nc', '-zv', '-w', str(self.timeout), host, str(port)],
                capture_output=True,
                text=True,
                timeout=self.timeout + 2
            )
            
            if result.returncode == 0 and ('succeeded' in result.stderr or 'succeeded' in result.stdout):
                return True, "TCP success"
            else:
                error_msg = f"✗ TCP {host}:{port} failed"
                self.logger.error(error_msg)
                # self.logger.error(f"NC output:\n{result.stdout}\n{result.stderr}")
                return False, error_msg
        except subprocess.TimeoutExpired:
            error_msg = f"✗ TCP {host}:{port} timeout"
            self.logger.error(error_msg)
            return False, error_msg
    
    def monitor_loop(self):
        ping_thread = threading.Thread(target=lambda: self._loop(self.check_ping), daemon=True)
        dns_thread = threading.Thread(target=lambda: self._loop(self.check_dns), daemon=True)
        tcp_thread = threading.Thread(target=lambda: self._loop(self.check_tcp), daemon=True)
        
        ping_thread.start()
        dns_thread.start()
        tcp_thread.start()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            sys.exit(0)
    
    def _loop(self, check_func):
        while True:
            check_func()
            time.sleep(1)


def main():
    parser = argparse.ArgumentParser(
        description='Network connectivity monitor',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--timeout', type=int, default=1, help='Command timeout in seconds (default: 1)')
    parser.add_argument('--log-dir', type=str, default='./logs', help='Log directory (default: ./logs)')
    parser.add_argument('--ping', type=str, default='8.8.8.8', help='PING target IP (default: 8.8.8.8)')
    parser.add_argument('--dns', type=str, default='google.com', help='DNS query target domain (default: google.com)')
    parser.add_argument('--tcp', type=str, default='google.com:80', help='TCP target host:port (default: google.com:80)')
    
    args = parser.parse_args()
    
    tcp_target = args.tcp.split(':')
    if len(tcp_target) == 2:
        tcp_target = (tcp_target[0], int(tcp_target[1]))
    else:
        tcp_target = ('google.com', 80)
    
    targets = {
        'ping': args.ping,
        'dns': args.dns,
        'tcp': tcp_target
    }
    
    monitor = NetworkMonitor(
        log_dir=args.log_dir,
        timeout=args.timeout,
        targets=targets
    )
    
    monitor.monitor_loop()


if __name__ == '__main__':
    main()
