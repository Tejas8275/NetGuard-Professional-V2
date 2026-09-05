"""
Pure network diagnostic functions.
Moved verbatim from the original main.py — logic unchanged.
No Tk/GUI dependencies; safe to unit test in isolation.
"""
import ipaddress
import socket, subprocess, platform, re, time, urllib.request
from core.health_settings import normalize_health_thresholds


def cmd(c, timeout=25):
    try:
        p = subprocess.run(c, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or '') + (p.stderr or '')
    except Exception as e:
        return -1, str(e)


def ping(h, n=1):
    return cmd(['ping', '-n' if platform.system() == 'Windows' else '-c', str(n), h], 15)[1]


def latency(s):
    m = re.search(r'Average = (\d+)ms', s, re.I) or re.search(r'(\d+(?:\.\d+)?)\s*ms', s, re.I)
    return float(m.group(1)) if m else None


def loss(s):
    m = re.search(r'(\d+)%\s*loss', s, re.I)
    return int(m.group(1)) if m else None


def parse_windows_ipconfig(output):
    """Extract active-adapter facts from English ``ipconfig /all`` output."""
    adapters = []
    current = None
    pending = None
    header = re.compile(r'^.+\badapter\s+(.+):\s*$', re.I)
    ipv4 = re.compile(r'(?<![\d.])((?:\d{1,3}\.){3}\d{1,3})(?![\d.])')

    def address_value(line):
        found = ipv4.search(line)
        if found:
            return found.group(1), True
        if re.match(r'^[0-9a-f]{0,4}:', line, re.I):
            return line, False
        candidate = line.split(':', 1)[1].strip() if ':' in line else line.strip()
        if ':' in candidate and not candidate.lower().startswith(('connection-specific', 'default gateway', 'dns servers')):
            return candidate, False
        return None, False

    for raw_line in output.splitlines():
        line = raw_line.strip()
        match = header.match(line)
        if match:
            current = {'name': match.group(1), 'ipv4': None, 'gateway': None, 'dns': None, 'connected': True}
            adapters.append(current)
            pending = None
            continue
        if not current:
            continue
        lower = line.lower()
        if 'media state' in lower and 'disconnected' in lower:
            current['connected'] = False
        address, is_ipv4 = address_value(line)
        if 'ipv4 address' in lower and is_ipv4:
            current['ipv4'] = address
            pending = None
        elif 'default gateway' in lower:
            current['gateway'] = address
            pending = 'gateway' if not is_ipv4 else None
        elif 'dns servers' in lower:
            current['dns'] = address
            pending = 'dns' if not is_ipv4 else None
        elif pending and address:
            current[pending] = address
            if is_ipv4:
                pending = None
    return adapters


def active_windows_adapter(output):
    """Choose the usable physical adapter, avoiding disconnected VPN/virtual links."""
    return active_physical_adapter(parse_windows_ipconfig(output))


def active_physical_adapter(adapters):
    """Choose the usable physical adapter from parsed adapter records."""
    ignored = ('warp', 'cloudflare', 'vpn', 'virtual', 'vmware', 'virtualbox', 'hyper-v', 'tunnel', 'loopback')
    candidates = [adapter for adapter in adapters
                  if adapter['connected'] and adapter['ipv4'] and not adapter['ipv4'].startswith('169.254.')
                  and not any(token in adapter['name'].lower() for token in ignored)]
    if not candidates:
        return None
    return sorted(candidates, key=lambda adapter: (adapter['gateway'] is not None, adapter['dns'] is not None), reverse=True)[0]


def detect_vpn(adapters, active_dns=None):
    """Identify active tunnel providers without confusing them with Wi-Fi/Ethernet."""
    warp_dns = ('127.0.2.2', '127.0.2.3', '::ffff:127.0.2.2', '::ffff:127.0.2.3')
    for adapter in adapters:
        name = adapter['name'].lower()
        if adapter['connected'] and ('warp' in name or 'cloudflare' in name):
            return {'active': True, 'label': 'WARP ACTIVE', 'detail': 'Cloudflare WARP tunnel detected'}
    if str(active_dns or '').lower() in warp_dns:
        return {'active': True, 'label': 'WARP ACTIVE', 'detail': f'Cloudflare WARP DNS proxy detected ({active_dns})'}
    for adapter in adapters:
        name = adapter['name'].lower()
        if adapter['connected'] and any(token in name for token in ('vpn', 'tunnel', 'openvpn', 'wireguard')):
            return {'active': True, 'label': 'VPN ACTIVE', 'detail': f'VPN/tunnel adapter detected ({adapter["name"]})'}
    return {'active': False, 'label': 'NO VPN', 'detail': 'No supported VPN tunnel detected'}


def health_assessment(network, online, latency_ms, packet_loss, dns_ok, thresholds=None):
    """Produce a transparent 0–100 health score and plain-language reasons."""
    thresholds = normalize_health_thresholds(thresholds)
    latency_warning = thresholds['latency_warning_ms']
    latency_critical = thresholds['latency_critical_ms']
    loss_warning = thresholds['packet_loss_warning_pct']
    loss_critical = thresholds['packet_loss_critical_pct']
    score = 0
    insights = []
    if network.get('Local IP') not in (None, '', 'Unavailable'):
        score += 15
    else:
        insights.append('No usable local IPv4 address was detected; check the adapter or DHCP.')
    if network.get('Adapter') not in (None, '', 'Unavailable'):
        score += 5
    if network.get('Gateway') not in (None, '', 'Unavailable'):
        score += 15
    else:
        insights.append('No IPv4 gateway was detected; check the router or adapter configuration.')
    if online:
        score += 35
    else:
        insights.append('Internet reachability failed; check the gateway, ISP connection, or captive portal.')
    if dns_ok:
        score += 15
    else:
        insights.append('DNS lookup failed; check DNS server settings or try a known resolver.')
    if latency_ms is not None:
        score += 10 if latency_ms < latency_warning else 6 if latency_ms < latency_critical else 2
        if latency_ms >= latency_critical:
            insights.append(f'Latency is high ({latency_ms:.0f} ms); check congestion, Wi-Fi signal, or ISP routing.')
    else:
        insights.append('Latency could not be measured.')
    if packet_loss is not None:
        score += 5 if packet_loss < loss_warning else 2 if packet_loss < loss_critical else 0
        if packet_loss >= loss_warning:
            insights.append(f'Packet loss is elevated ({packet_loss}%); check Wi-Fi signal, cabling, or congestion.')
    elif online:
        insights.append('ICMP packet loss is unavailable because the network blocks ping; HTTPS connectivity is still working.')
    if not insights:
        insights.append('All primary connectivity checks passed.')
    status = 'HEALTHY' if score >= 80 else 'NEEDS ATTENTION' if score >= 50 else 'PROBLEM'
    return {'score': score, 'status': status, 'insights': insights}


def info():
    h = socket.gethostname()
    try:
        ip = socket.gethostbyname(h)
    except:
        ip = 'Unavailable'
    gw = dns = adapter_name = connection = 'Unavailable'
    vpn = {'label': 'NO VPN', 'detail': 'VPN detection is available on Windows'}
    if platform.system() == 'Windows':
        _, o = cmd(['ipconfig', '/all'])
        adapters = parse_windows_ipconfig(o)
        active = active_physical_adapter(adapters)
        if active:
            ip = active['ipv4'] or ip
            gw = active['gateway'] or 'Unavailable'
            dns = active['dns'] or 'Unavailable'
            adapter_name = active['name']
            connection = 'Wi-Fi' if any(token in active['name'].lower() for token in ('wi-fi', 'wireless', 'wlan')) else 'Ethernet'
        vpn = detect_vpn(adapters, dns)
    return {'Hostname': h, 'Local IP': ip, 'Gateway': gw, 'DNS': dns, 'Adapter': adapter_name, 'Connection': connection, 'VPN': vpn['label'], 'VPN Details': vpn['detail'], 'OS': platform.platform()}


def dnslookup(h):
    try:
        a, b, c = socket.gethostbyname_ex(h)
        return f'Hostname: {a}\nAliases: {", ".join(b) or "None"}\nIPv4:\n' + '\n'.join('  • ' + x for x in c)
    except Exception as e:
        return 'DNS resolution failed: ' + str(e)


def port(h, p):
    s = socket.socket()
    s.settimeout(2)
    try:
        return 'OPEN' if s.connect_ex((h, int(p))) == 0 else 'CLOSED / FILTERED'
    except Exception as e:
        return 'ERROR: ' + str(e)
    finally:
        s.close()


def trace(h):
    return cmd((['tracert', '-d', h] if platform.system() == 'Windows' else ['traceroute', '-n', h]), 50)[1]


def conns():
    return cmd((['netstat', '-ano'] if platform.system() == 'Windows' else ['ss', '-tunap']), 25)[1]


def internet_check():
    """Check connectivity with ICMP first, then DNS and HTTPS fallbacks."""
    ping_output = ping('8.8.8.8', 1)
    ping_ok = ('Reply from' in ping_output) if platform.system() == 'Windows' else ('bytes from' in ping_output)
    if ping_ok:
        return True, 'Ping', ping_output
    try:
        socket.gethostbyname('www.google.com')
        with urllib.request.urlopen('https://www.google.com/generate_204', timeout=5) as response:
            if response.status in (200, 204):
                return True, 'HTTPS', ping_output
    except Exception:
        pass
    return False, 'Unavailable', ping_output


def https_latency():
    """Return a real HTTPS response-time sample when ICMP ping is blocked."""
    try:
        started = time.perf_counter()
        with urllib.request.urlopen('https://www.google.com/generate_204', timeout=6) as response:
            if response.status in (200, 204):
                return (time.perf_counter() - started) * 1000
    except Exception:
        pass
    return None


def is_private_scan_prefix(prefix):
    """Accept only a valid private IPv4 /24 prefix for discovery scans."""
    parts = str(prefix).strip().rstrip('.').split('.')
    if len(parts) != 3:
        return False
    try:
        network = ipaddress.ip_network('.'.join(parts) + '.0/24', strict=True)
    except ValueError:
        return False
    return network.is_private and (
        network.network_address in ipaddress.ip_network('10.0.0.0/8')
        or network.network_address in ipaddress.ip_network('172.16.0.0/12')
        or network.network_address in ipaddress.ip_network('192.168.0.0/16')
    )
