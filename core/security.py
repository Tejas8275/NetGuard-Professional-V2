"""Pure security helpers used by the local network scanner."""
import re
import socket

SCAN_SERVICES = {
    21: 'FTP', 22: 'SSH', 23: 'Telnet', 25: 'SMTP', 53: 'DNS', 80: 'HTTP',
    139: 'NetBIOS', 143: 'IMAP', 443: 'HTTPS', 445: 'SMB', 3306: 'MySQL',
    3389: 'RDP', 8000: 'HTTP-Server', 8080: 'HTTP-Proxy'
}


def scan_ports(host):
    opened = []
    for p, service in SCAN_SERVICES.items():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            if s.connect_ex((host, p)) == 0:
                opened.append(f'{p} ({service})')
            s.close()
        except:
            pass
    return ', '.join(opened) if opened else 'No exposed services'


def parse_open_ports(ports):
    """Return numeric port identifiers from scanner display text.

    The scanner intentionally displays friendly values such as ``22 (SSH)``.
    Consumers must not compare that display value directly to ``"22"``.
    """
    if not ports or str(ports).strip().lower() in {'none', 'no exposed services'}:
        return []
    return [int(match) for match in re.findall(r'(?<!\d)(\d{1,5})(?!\d)', str(ports))]


def calculate_risk(ports):
    """Calculate a security risk score based on exposed ports.
    Returns severity with score for SOC-style reporting.
    """
    port_list = parse_open_ports(ports)
    if not port_list:
        return 'LOW (0)'
    score = 0

    # High impact exposed services
    critical_ports = {23: 35, 3389: 35, 445: 30, 21: 25}
    medium_ports = {22: 15, 25: 15, 110: 10, 143: 10}

    for p in port_list:
        if p in critical_ports:
            score += critical_ports[p]
        elif p in medium_ports:
            score += medium_ports[p]
        else:
            score += 5

    # More exposed ports increase attack surface
    if len(port_list) >= 5:
        score += 15

    score = min(score, 100)

    if score >= 80:
        level = 'CRITICAL'
    elif score >= 60:
        level = 'HIGH'
    elif score >= 30:
        level = 'MEDIUM'
    else:
        level = 'LOW'

    return f'{level} ({score})'


def security_findings_for_ports(ports):
    """Return actionable findings as ``(severity, message, port)`` tuples."""
    messages = {
        23: ('CRITICAL', 'Telnet exposed — clear-text remote access should be disabled.'),
        445: ('HIGH', 'SMB exposed — review Windows file sharing and firewall rules.'),
        3389: ('HIGH', 'RDP exposed — restrict remote desktop to trusted networks.'),
        21: ('HIGH', 'FTP exposed — prefer SFTP/FTPS where possible.'),
        22: ('MEDIUM', 'SSH exposed — verify strong authentication and access restrictions.'),
        80: ('LOW', 'Common service port 80 is exposed; verify it is intentional.'),
        53: ('LOW', 'Common service port 53 is exposed; verify it is intentional.'),
        443: ('INFO', 'HTTPS service detected. Verify certificates and intended exposure.'),
    }
    return [(severity, message, str(port)) for port in parse_open_ports(ports)
            if (severity_message := messages.get(port))
            for severity, message in [severity_message]]
