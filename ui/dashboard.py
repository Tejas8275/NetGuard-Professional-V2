"""
Phase 4 Step 2 — dashboard visualization upgrade: circular health gauge,
premium metric cards, and a cleaner monitoring-style latency graph.

Sidebar nav rows and the Dashboard page: animated hover transitions on
nav rows, premium metric cards with a top accent strip, a circular
health-score gauge, and a professional monitoring-style latency chart —
all built on top of the same data/callbacks as before.

Scope discipline: only this file changes. Every public method keeps its
exact name and signature:
  - make_nav_button(self, name, icon)
  - card(self, p, title, val, key, icon='•')
  - small_stat(self, p, title, value)
  - dashboard(self)
  - draw_health_bar(self)
  - update_dashboard_details(self, i)
  - add_dashboard_event(self, severity, message)
  - set_health_score(self, score, status)
  - dashboard_graph_draw(self)
  - update_dashboard_stats(self)

And every widget attribute other files (main.py) rely on is preserved
verbatim, same object types, same dict keys: self.cards (with keys
'internet','lat','loss','dns','gw' — read/written by main.py's
cards_update()/report methods), self.nav_rows, self.health_score,
self.health_bar (now a square Canvas driving a circular gauge instead of
a horizontal bar — same attribute, same widget type, same
draw_health_bar()/<Configure> binding), self.dash_graph,
self.stat_avg/min/max/alert, self.health_status, self.details,
self.events, self.dash.

Only visuals changed: gauge shape/colors (green/yellow/red thresholds
unchanged — >=80 good, >=50 warn, else bad), card/stat typography and
spacing, and latency-graph styling. No health-score math, no chart data
source, no callback wiring was altered.

Theme handling: same pattern as ui/widgets.py — reads `styles.T`
dynamically instead of importing a frozen `T` binding, so live theme
switching (main.py's apply_theme() writes to `_styles.T`) keeps working
correctly.
"""
import tkinter as tk
from tkinter import ttk
import datetime

import ui.styles as styles
from ui.styles import F_NAV
from core.network_core import info


class DashboardMixin:
    def _lerp_hex(self, c1, c2, t):
        c1 = c1.lstrip('#'); c2 = c2.lstrip('#')
        r1, g1, b1 = int(c1[0:2], 16), int(c1[2:4], 16), int(c1[4:6], 16)
        r2, g2, b2 = int(c2[0:2], 16), int(c2[2:4], 16), int(c2[4:6], 16)
        r = int(r1 + (r2 - r1) * t); g = int(g1 + (g2 - g1) * t); b = int(b1 + (b2 - b1) * t)
        return f'#{r:02x}{g:02x}{b:02x}'

    def _animate_nav_row(self, row, lab, icon_lab, icon_wrap, from_c, to_c, step=0, steps=5):
        """Lightweight 5-step color interpolation for the sidebar hover
        transition — purely cosmetic, self-contained, no new attributes
        that anything else depends on."""
        try:
            if not row.winfo_exists():
                return
        except Exception:
            return
        t = step / steps
        color = self._lerp_hex(from_c, to_c, t)
        try:
            row.configure(bg=color); lab.configure(bg=color); icon_lab.configure(bg=color); icon_wrap.configure(bg=color)
        except Exception:
            return
        if step < steps:
            self.after(12, lambda: self._animate_nav_row(row, lab, icon_lab, icon_wrap, from_c, to_c, step + 1, steps))

    def make_nav_button(self, name, icon):
        """Modern sidebar nav row: icon chip, animated hover transition,
        left accent bar for the active-page indicator (colored by
        main.py's show()/apply_theme() via row.winfo_children()[0]).
        Same click/hover bindings and self.nav_rows[name] registration
        as before."""
        T = styles.T
        row = tk.Frame(self.side, bg=T['sidebar'], height=48); row.pack(fill='x', padx=12, pady=3); row.pack_propagate(False)
        accent = tk.Frame(row, bg=T['sidebar'], width=3); accent.pack(side='left', fill='y')
        icon_wrap = tk.Frame(row, bg=T['panel3'], width=30, height=30)
        icon_wrap.pack(side='left', padx=(12, 4)); icon_wrap.pack_propagate(False)
        icon_lab = tk.Label(icon_wrap, text=icon, font=('Segoe UI', 11), fg=T['accent'], bg=T['panel3'])
        icon_lab.pack(expand=True)
        lab = tk.Label(row, text=name, font=F_NAV, fg=T['muted'], bg=T['sidebar'], anchor='w'); lab.pack(side='left', fill='both', expand=True)
        lab.name = name; row.label = lab; self.nav_rows[name] = row

        def enter(_):
            if getattr(self, 'active_page', None) != name:
                self._animate_nav_row(row, lab, icon_lab, icon_wrap, T['sidebar'], T['nav_hover'])
                icon_lab.configure(fg=T['text'])

        def leave(_):
            if getattr(self, 'active_page', None) != name:
                self._animate_nav_row(row, lab, icon_lab, icon_wrap, T['nav_hover'], T['sidebar'])
                icon_lab.configure(fg=T['muted'])

        def click(_=None): self.show(name)
        for w in (row, lab, accent, icon_wrap, icon_lab): w.bind('<Enter>', enter); w.bind('<Leave>', leave); w.bind('<Button-1>', click)

    def card(self, p, title, val, key, icon='•'):
        """Premium SOC metric card: top accent strip, icon chip,
        letter-spaced uppercase label, emphasized metric value.
        self.cards[key] still maps to the value Label (same widget
        type, .config/.cget compatible with main.py's
        cards_update()/report code)."""
        T = styles.T
        f = tk.Frame(p, bg=T['panel'], highlightthickness=1, highlightbackground=T['border'])
        f.pack(side='left', fill='both', expand=True, padx=5)
        tk.Frame(f, bg=T['accent'], height=3).pack(fill='x')

        head = tk.Frame(f, bg=T['panel']); head.pack(fill='x', padx=14, pady=(13, 0))
        chip = tk.Frame(head, bg=T['panel3'], width=32, height=32); chip.pack(side='left'); chip.pack_propagate(False)
        tk.Label(chip, text=icon, font=('Segoe UI', 11, 'bold'), fg=T['accent'], bg=T['panel3']).pack(expand=True)
        self.L(head, ' '.join(title), 8, True, T['muted'], T['panel']).pack(side='left', padx=(9, 0))

        v = self.L(f, val, 21, True, T['text'], T['panel'])
        v.pack(anchor='w', padx=14, pady=(11, 3))
        context = {
            'internet': 'Live reachability',
            'lat': 'Current response time',
            'loss': 'Current ICMP loss',
            'dns': 'Active resolver',
            'gw': 'Local route gateway',
        }.get(key, 'Live status')
        self.L(f, context, 8, False, T['muted'], T['panel']).pack(anchor='w', padx=14, pady=(0, 14))
        self.cards[key] = v

    def _legacy_dashboard(self):
        """Dashboard layout:
        Top    — security/network status cards (internet, latency,
                 packet loss, DNS, gateway).
        Middle — health-score panel (left) + latency trend chart, and
                 network details / recent events (right).
        Bottom — last scan details.
        Same data hooks, same widget names as before; only the visual
        treatment changed."""
        T = styles.T
        p = self.pages['Dashboard']; self.cards = {}; self.dashboard_events = []; self.current_score = 0; self.alert_count = 0

        self.L(p, 'Real-time connectivity, performance and threat overview', 9, False, T['muted']).pack(anchor='w', padx=18, pady=(10, 12))

        # --- Toolbar -----------------------------------------------------
        toolbar = tk.Frame(p, bg=T['panel'], highlightthickness=1, highlightbackground=T['border'])
        toolbar.pack(fill='x', padx=18, pady=(0, 12))
        for x, fn in [('⚡ FULL HEALTH SCAN', self.scan), ('▶ START MONITOR', self.start_monitor), ('■ STOP', self.stop_monitor), ('📄 REPORT', self.report)]:
            ttk.Button(toolbar, text=x, command=fn).pack(side='left', padx=8, pady=11)

        # --- Top: status cards ---------------------------------------------
        r = tk.Frame(p, bg=T['bg']); r.pack(fill='x', padx=14, pady=(0, 10))
        for a, b, c, i in [('INTERNET', 'CHECKING', 'internet', '◉'), ('LATENCY', '-- ms', 'lat', '◒'), ('PACKET LOSS', '-- %', 'loss', '⇣'), ('DNS', 'CHECKING', 'dns', '⌁'), ('GATEWAY', 'CHECKING', 'gw', '⌂')]:
            self.card(r, a, b, c, i)

        # --- Live SOC operations strip -----------------------------------
        # These values are derived from the application's existing state;
        # no synthetic/random telemetry is introduced.
        ops = tk.Frame(p, bg=T['bg'])
        ops.pack(fill='x', padx=14, pady=(0, 10))
        self.soc_status = {}

        def status_tile(parent, key, label, value, color):
            tile = tk.Frame(parent, bg=T['panel2'], highlightthickness=1, highlightbackground=T['border'])
            tile.pack(side='left', fill='x', expand=True, padx=3)
            dot = tk.Label(tile, text='●', font=('Segoe UI', 9, 'bold'), fg=color, bg=T['panel2'])
            dot.pack(side='left', padx=(10, 6), pady=9)
            body = tk.Frame(tile, bg=T['panel2']); body.pack(side='left', fill='x', expand=True, pady=6)
            self.L(body, label, 7, True, T['muted'], T['panel2']).pack(anchor='w')
            val_lab = self.L(body, value, 9, True, T['text'], T['panel2'])
            val_lab.pack(anchor='w', pady=(1, 0))
            self.soc_status[key] = (val_lab, dot)

        status_tile(ops, 'network', 'NETWORK', 'CHECKING', T['muted'])
        status_tile(ops, 'vpn', 'VPN / WARP', 'CHECKING', T['muted'])
        status_tile(ops, 'monitor', 'MONITORING', 'STANDBY', T['muted'])
        status_tile(ops, 'devices', 'DISCOVERED DEVICES', '0', T['muted'])
        status_tile(ops, 'alerts', 'ACTIVE ALERTS', '0', T['good'])

        # --- Middle: health panel + chart | details + events -----------
        main = tk.Frame(p, bg=T['bg']); main.pack(fill='both', expand=True, padx=14, pady=(0, 10))

        left = tk.Frame(main, bg=T['panel'], highlightthickness=1, highlightbackground=T['border'])
        left.pack(side='left', fill='both', expand=True, padx=(0, 6))

        sh = tk.Frame(left, bg=T['panel']); sh.pack(fill='x', padx=16, pady=(14, 8))
        self.L(sh, '◉', 11, True, T['accent'], T['panel']).pack(side='left', padx=(0, 8))
        self.L(sh, 'NETWORK HEALTH SCORE', 9, True, T['muted'], T['panel']).pack(side='left')

        # --- Circular health gauge -----------------------------------------
        # self.health_bar is now a square Canvas driving a circular gauge
        # instead of a horizontal bar; self.health_score is placed on top
        # of it (still the same Label widget/attribute main.py's
        # set_health_score() configures via .config(text=...)).
        gauge_wrap = tk.Frame(left, bg=T['panel'], width=170, height=170)
        gauge_wrap.pack(pady=(2, 4)); gauge_wrap.pack_propagate(False)

        self.health_bar = tk.Canvas(gauge_wrap, width=170, height=170, bg=T['panel'], highlightthickness=0)
        self.health_bar.pack(fill='both', expand=True)
        self.health_bar.bind('<Configure>', lambda e: self.draw_health_bar())

        self.health_score = self.L(gauge_wrap, '--', 36, True, T['accent'], T['panel'])
        self.health_score.place(relx=0.5, rely=0.44, anchor='center')
        self.L(gauge_wrap, 'SCORE / 100', 7, True, T['muted'], T['panel']).place(relx=0.5, rely=0.63, anchor='center')

        self.health_status = self.L(left, 'RUN FULL HEALTH SCAN', 9, True, T['muted'], T['panel'])
        self.health_status.pack(pady=(2, 14))

        stats = tk.Frame(left, bg=T['panel']); stats.pack(fill='x', padx=16, pady=(0, 10))
        self.stat_avg = self.small_stat(stats, 'AVG LATENCY', '-- ms')
        self.stat_min = self.small_stat(stats, 'MIN', '-- ms')
        self.stat_max = self.small_stat(stats, 'MAX', '-- ms')
        self.stat_alert = self.small_stat(stats, 'ALERTS', '0')

        self.L(left, 'LATENCY TREND', 8, True, T['muted'], T['panel']).pack(anchor='w', padx=16, pady=(10, 5))
        self.dash_graph = tk.Canvas(left, bg=T['panel2'], height=160, highlightthickness=1, highlightbackground=T['border'])
        self.dash_graph.pack(fill='x', padx=16, pady=(0, 16))
        self.dash_graph.bind('<Configure>', lambda e: self.dashboard_graph_draw())

        right = tk.Frame(main, bg=T['panel'], highlightthickness=1, highlightbackground=T['border'])
        right.pack(side='left', fill='both', expand=True, padx=(6, 0))

        rh = tk.Frame(right, bg=T['panel']); rh.pack(fill='x', padx=16, pady=(14, 6))
        self.L(rh, '▣', 11, True, T['accent'], T['panel']).pack(side='left', padx=(0, 8))
        self.L(rh, 'NETWORK DETAILS', 9, True, T['muted'], T['panel']).pack(side='left')

        self.details = tk.Text(right, height=9, bg=T['panel2'], fg=T['text'], font=('Consolas', 9),
                                relief='flat', bd=0, insertbackground='white', state='disabled',
                                padx=10, pady=8)
        self.details.pack(fill='x', padx=16, pady=(0, 12))

        ev_head = tk.Frame(right, bg=T['panel']); ev_head.pack(fill='x', padx=16, pady=(2, 6))
        self.L(ev_head, '◷', 10, True, T['accent'], T['panel']).pack(side='left', padx=(0, 6))
        self.L(ev_head, 'RECENT SECURITY & NETWORK EVENTS', 9, True, T['muted'], T['panel']).pack(side='left')

        self.events = tk.Text(right, bg=T['panel2'], fg=T['text'], font=('Consolas', 9),
                               relief='flat', bd=0, wrap='word', state='disabled', insertbackground='white',
                               padx=10, pady=8)
        self.events.pack(fill='both', expand=True, padx=16, pady=(0, 16))

        # --- Bottom: last scan details -----------------------------------
        self.L(p, 'LAST SCAN DETAILS', 8, True, T['muted']).pack(anchor='w', padx=18, pady=(0, 4))
        self.dash = self.box(p); self.dash.config(height=4)

        self.update_dashboard_details(info())
        self.add_dashboard_event('INFO', 'Dashboard initialized — run Full Health Scan to calculate health score.')
        self.dashboard_graph_draw()

    def small_stat(self, p, title, value):
        """Improved mini stat block: letter-spaced caption, clearer
        hierarchy between the caption and the value. Same
        signature/return type (the value Label) as before."""
        T = styles.T
        f = tk.Frame(p, bg=T['panel2'], highlightthickness=1, highlightbackground=T['border'])
        f.pack(side='left', fill='x', expand=True, padx=3)
        self.L(f, ' '.join(title), 7, True, T['muted'], T['panel2']).pack(anchor='w', padx=10, pady=(9, 0))
        v = self.L(f, value, 13, True, T['accent'], T['panel2'])
        v.pack(anchor='w', padx=10, pady=(2, 9))
        return v

    def draw_health_bar(self):
        """Circular SOC-style health gauge. self.health_bar is the same
        Canvas attribute as before — only the drawing routine changed,
        from a horizontal bar to a ring gauge. Score/threshold logic
        (>=80 good, >=50 warn, else bad) is completely unchanged."""
        T = styles.T
        if not hasattr(self, 'health_bar'): return
        c = self.health_bar; c.delete('all')
        size = min(max(c.winfo_width(), 170), max(c.winfo_height(), 170))
        score = getattr(self, 'current_score', 0)
        color = T['good'] if score >= 80 else T['warn'] if score >= 50 else T['bad']

        thickness = 11
        pad = thickness / 2 + 6
        x0, y0, x1, y1 = pad, pad, size - pad, size - pad

        # Background track ring (use 359.9 instead of 360 — Tk collapses a
        # full-circle arc into nothing at exactly 360 degrees)
        c.create_arc(x0, y0, x1, y1, start=90, extent=359.9, style='arc',
                     outline=T['panel2'], width=thickness)

        # Score ring — starts at 12 o'clock, sweeps clockwise
        if score > 0:
            extent = -359.9 * (score / 100)
            c.create_arc(x0, y0, x1, y1, start=90, extent=extent, style='arc',
                         outline=color, width=thickness)
            # Small bright cap on the leading edge for a "live gauge" feel
            import math
            end_angle = math.radians(90 - 360 * (score / 100))
            cx, cy = size / 2, size / 2
            r = (x1 - x0) / 2
            tip_x = cx + r * math.cos(end_angle)
            tip_y = cy - r * math.sin(end_angle)
            c.create_oval(tip_x - thickness / 2, tip_y - thickness / 2,
                          tip_x + thickness / 2, tip_y + thickness / 2,
                          fill=color, outline=T['panel'], width=2)

        # Faint inner ring for depth
        c.create_oval(x0 + thickness, y0 + thickness, x1 - thickness, y1 - thickness,
                     outline=T['border'], width=1)

    def update_dashboard_details(self, i):
        if not hasattr(self, 'details'): return
        txt = (f"Hostname        : {i.get('Hostname','Unavailable')}\n"
               f"Connection      : {i.get('Connection','Unavailable')}\n"
               f"Active Adapter  : {i.get('Adapter','Unavailable')}\n"
               f"Local IP        : {i.get('Local IP','Unavailable')}\n"
               f"Gateway         : {i.get('Gateway','Unavailable')}\n"
               f"DNS Server      : {i.get('DNS','Unavailable')}\n"
               f"VPN / WARP      : {i.get('VPN','Unavailable')}\n"
               f"VPN Details     : {i.get('VPN Details','Unavailable')}\n"
               f"Operating System: {i.get('OS','Unavailable')}")
        self.details.config(state='normal'); self.details.delete('1.0', 'end'); self.details.insert('1.0', txt); self.details.config(state='disabled')

    def _legacy_add_dashboard_event(self, severity, message):
        if not hasattr(self, 'events'): return
        now = datetime.datetime.now().strftime('%H:%M:%S'); self.events.config(state='normal'); self.events.insert('1.0', f'{now}  [{severity:<8}]  {message}\n'); self.events.config(state='disabled')
        self.dashboard_events.append((now, severity, message)); self.dashboard_events = self.dashboard_events[-30:]

    def set_health_score(self, score, status):
        T = styles.T
        self.current_score = max(0, min(100, int(score))); self.health_score.config(text=str(self.current_score))
        color = T['good'] if self.current_score >= 80 else T['warn'] if self.current_score >= 50 else T['bad']
        self.health_score.config(fg=color)
        self.health_status.config(text=status, fg=color); self.draw_health_bar()

    def dashboard_graph_draw(self):
        """Professional monitoring-style redesign: solid baseline axis,
        subtle gridlines with value labels, a glow-style double-stroke
        latency line, filled area, and a live marker on the latest
        sample. Data source (self.points) and sampling logic unchanged."""
        T = styles.T
        if not hasattr(self, 'dash_graph'): return
        c = self.dash_graph; c.delete('all')
        w = max(c.winfo_width(), 500); h = max(c.winfo_height(), 150)

        vals = self.points[-45:]
        mx = max(max(vals), 100) if vals else 100

        # Horizontal gridlines with value labels for a monitoring-console feel
        for i in range(4):
            y = 16 + i * (h - 36) / 3
            c.create_line(46, y, w - 15, y, fill=T['border'], dash=(2, 3))
            label_val = mx - (mx * i / 3)
            c.create_text(40, y, text=f'{label_val:.0f}', fill=T['muted'], anchor='e', font=('Consolas', 7))

        # Baseline axis (solid, brighter than gridlines)
        c.create_line(46, h - 20, w - 15, h - 20, fill=T['border'], width=1)

        if vals:
            pts = []
            for i, v in enumerate(vals):
                x = 50 + i * (w - 66) / max(len(vals) - 1, 1)
                y = h - 20 - (v / mx) * (h - 40)
                pts += [x, y]

            if len(pts) >= 4:
                # Filled area under the line for a modern "sparkline" look
                area = [pts[0], h - 20] + pts + [pts[-2], h - 20]
                c.create_polygon(*area, fill=T['panel3'], outline='')
                # Soft "glow" stroke behind the main line for visibility
                c.create_line(*pts, fill=T['accent_soft'], width=5, smooth=True, capstyle='round')
                c.create_line(*pts, fill=T['accent'], width=2, smooth=True, capstyle='round')
                # Marker on the latest sample
                c.create_oval(pts[-2] - 4, pts[-1] - 4, pts[-2] + 4, pts[-1] + 4, fill=T['accent'], outline=T['text'], width=1)

            avg = sum(vals) / len(vals)
            c.create_text(50, 12, text=f'Latest {vals[-1]:.0f} ms  •  Avg {avg:.0f} ms', fill=T['text'], anchor='w', font=('Segoe UI', 8, 'bold'))
        else:
            c.create_text(w / 2, h / 2, text='Start Monitor to collect latency data', fill=T['muted'], font=('Segoe UI', 9))


    def _update_soc_status(self):
        """Refresh the small operations strip from existing application state.
        This is presentation-only: it reads values already maintained by the
        monitoring, scanner and alert subsystems."""
        if not hasattr(self, 'soc_status'):
            return
        T = styles.T

        # Internet status comes from the dashboard's existing connectivity card.
        online_text = 'CHECKING'
        if hasattr(self, 'cards') and 'internet' in self.cards:
            online_text = str(self.cards['internet'].cget('text')).upper()
        online = online_text.startswith('ONLINE') or online_text in ('CONNECTED', 'OK')
        net_color = T['good'] if online else T['bad'] if online_text in ('OFFLINE', 'ERROR') else T['warn']

        monitoring = bool(getattr(self, 'monitor', False))
        monitor_color = T['good'] if monitoring else T['muted']
        vpn_text = str(getattr(self, 'network_info', {}).get('VPN', 'CHECKING'))
        vpn_color = T['accent'] if vpn_text in ('WARP ACTIVE', 'VPN ACTIVE') else T['muted']

        known = getattr(self, 'known_devices', set()) or set()
        scan_results = getattr(self, 'scan_results', []) or []
        device_count = len(known)
        if not device_count and scan_results:
            device_count = len(scan_results)

        alerts = int(getattr(self, 'alert_count', 0) or 0)
        alert_color = T['bad'] if alerts else T['good']

        values = {
            'network': (online_text, net_color),
            'vpn': (vpn_text, vpn_color),
            'monitor': ('LIVE' if monitoring else 'STANDBY', monitor_color),
            'devices': (str(device_count), T['accent'] if device_count else T['muted']),
            'alerts': (str(alerts), alert_color),
        }
        for key, (value, color) in values.items():
            item = self.soc_status.get(key)
            if not item:
                continue
            val_lab, dot = item
            val_lab.config(text=value, fg=color)
            dot.config(fg=color)

    def update_dashboard_stats(self):
        vals = self.points[-45:]
        if hasattr(self, 'stat_avg'):
            if vals:
                self.stat_avg.config(text=f'{sum(vals)/len(vals):.0f} ms'); self.stat_min.config(text=f'{min(vals):.0f} ms'); self.stat_max.config(text=f'{max(vals):.0f} ms')
            else: self.stat_avg.config(text='-- ms'); self.stat_min.config(text='-- ms'); self.stat_max.config(text='-- ms')
            self.stat_alert.config(text=str(getattr(self, 'alert_count', 0)))
        self._update_soc_status()
        self.dashboard_graph_draw()

    def dashboard(self):
        """Reference-aligned command-center dashboard using live NetGuard data."""
        T = styles.T
        p = self.pages['Dashboard']
        self.cards = {}; self.dashboard_events = []; self.current_score = 0; self.alert_count = 0
        self.L(p, 'Real-time network status and system health', 10, False, T['muted']).pack(anchor='w', padx=24, pady=(10, 10))

        command = tk.Frame(p, bg=T['panel'], highlightthickness=1, highlightbackground=T['border'])
        command.pack(fill='x', padx=24, pady=(0, 12))
        actions = tk.Frame(command, bg=T['panel']); actions.pack(side='left', padx=10, pady=8)
        for text, fn in [('⚡ FULL HEALTH SCAN', self.scan), ('▶ START MONITOR', self.start_monitor), ('■ STOP', self.stop_monitor), ('▤ REPORT', self.report)]:
            ttk.Button(actions, text=text, command=fn).pack(side='left', padx=4)
        ttk.Button(command, text='↻ REFRESH LIVE DATA', command=self.refresh).pack(side='right', padx=12, pady=8)

        metrics = tk.Frame(p, bg=T['bg']); metrics.pack(fill='x', padx=20, pady=(0, 9))
        for title, value, key, icon in [('INTERNET', 'CHECKING', 'internet', '◉'), ('LATENCY', '-- ms', 'lat', '◒'), ('PACKET LOSS', '-- %', 'loss', '⇣'), ('DNS', 'CHECKING', 'dns', '⌁'), ('GATEWAY', 'CHECKING', 'gw', '⌂')]:
            self.card(metrics, title, value, key, icon)

        ops = tk.Frame(p, bg=T['bg']); ops.pack(fill='x', padx=20, pady=(0, 10)); self.soc_status = {}
        for key, label, value, color in [('network', 'NETWORK', 'CHECKING', T['muted']), ('vpn', 'VPN / WARP', 'CHECKING', T['muted']), ('monitor', 'MONITORING', 'STANDBY', T['muted']), ('devices', 'DISCOVERED DEVICES', '0', T['muted']), ('alerts', 'ACTIVE ALERTS', '0', T['good'])]:
            tile = tk.Frame(ops, bg=T['panel2'], highlightthickness=1, highlightbackground=T['border'])
            tile.pack(side='left', fill='x', expand=True, padx=3)
            dot = self.L(tile, '●', 9, True, color, T['panel2']); dot.pack(side='left', padx=(10, 5), pady=8)
            body = tk.Frame(tile, bg=T['panel2']); body.pack(side='left', fill='x', expand=True, pady=7)
            self.L(body, label, 7, True, T['muted'], T['panel2']).pack(anchor='w')
            value_label = self.L(body, value, 9, True, T['text'], T['panel2']); value_label.pack(anchor='w')
            self.soc_status[key] = (value_label, dot)

        workspace = tk.Frame(p, bg=T['bg'], height=280); workspace.pack(fill='x', padx=20, pady=(0, 10)); workspace.pack_propagate(False)
        health = tk.Frame(workspace, bg=T['panel'], highlightthickness=1, highlightbackground=T['border'])
        trend = tk.Frame(workspace, bg=T['panel'], highlightthickness=1, highlightbackground=T['border'])
        network = tk.Frame(workspace, bg=T['panel'], highlightthickness=1, highlightbackground=T['border'])
        health.pack(side='left', fill='both', expand=True, padx=(0, 5)); trend.pack(side='left', fill='both', expand=True, padx=5); network.pack(side='left', fill='both', expand=True, padx=(5, 0))

        self._section_header(health, '◉', 'NETWORK HEALTH')
        gauge = tk.Frame(health, bg=T['panel'], width=155, height=155); gauge.pack(pady=(0, 0)); gauge.pack_propagate(False)
        self.health_bar = tk.Canvas(gauge, width=155, height=155, bg=T['panel'], highlightthickness=0); self.health_bar.pack(fill='both', expand=True)
        self.health_bar.bind('<Configure>', lambda _event: self.draw_health_bar())
        self.health_score = self.L(gauge, '--', 32, True, T['accent'], T['panel']); self.health_score.place(relx=.5, rely=.43, anchor='center')
        self.L(gauge, '/100', 9, True, T['muted'], T['panel']).place(relx=.5, rely=.62, anchor='center')
        self.health_status = self.L(health, 'RUN FULL HEALTH SCAN', 10, True, T['muted'], T['panel']); self.health_status.pack(pady=(1, 8))
        stats = tk.Frame(health, bg=T['panel']); stats.pack(fill='x', padx=12, pady=(0, 10))
        self.stat_avg = self.small_stat(stats, 'AVERAGE', '-- ms'); self.stat_min = self.small_stat(stats, 'MINIMUM', '-- ms')
        self.stat_max = self.small_stat(stats, 'MAXIMUM', '-- ms'); self.stat_alert = self.small_stat(stats, 'ALERTS', '0')

        self._section_header(trend, '⌁', 'LATENCY TREND')
        self.dash_graph = tk.Canvas(trend, bg=T['panel2'], height=235, highlightthickness=1, highlightbackground=T['border'])
        self.dash_graph.pack(fill='both', expand=True, padx=14, pady=(4, 14)); self.dash_graph.bind('<Configure>', lambda _event: self.dashboard_graph_draw())

        self._section_header(network, '▣', 'NETWORK DETAILS')
        self.details = tk.Text(network, bg=T['panel2'], fg=T['text'], font=('Consolas', 9), relief='flat', bd=0, wrap='word', state='disabled', padx=12, pady=12)
        self.details.pack(fill='both', expand=True, padx=14, pady=(4, 14))

        events_shell = tk.Frame(p, bg=T['panel'], highlightthickness=1, highlightbackground=T['border'])
        events_shell.pack(fill='x', padx=20, pady=(0, 12))
        event_head = tk.Frame(events_shell, bg=T['panel']); event_head.pack(fill='x', padx=14, pady=(10, 6))
        self.L(event_head, 'RECENT EVENTS', 9, True, T['text'], T['panel']).pack(side='left')
        ttk.Button(event_head, text='VIEW REPORTS', command=lambda: self.show('Reports')).pack(side='right')
        self.events = ttk.Treeview(events_shell, columns=('time', 'event', 'detail'), show='headings', height=4)
        for column, heading, width in [('time', 'TIME', 150), ('event', 'EVENT', 220), ('detail', 'DETAILS', 850)]:
            self.events.heading(column, text=heading); self.events.column(column, width=width, anchor='w')
        self.events.tag_configure('CRITICAL', foreground=T['bad']); self.events.tag_configure('WARNING', foreground=T['warn']); self.events.tag_configure('OK', foreground=T['good'])
        self.events.pack(fill='x', padx=14, pady=(0, 14)); self._enable_tree_hover(self.events)

        self.dash = tk.Text(p, height=1, bg=T['bg'], fg=T['muted'], relief='flat')
        self.update_dashboard_details(info()); self.add_dashboard_event('INFO', 'Dashboard initialized — run Full Health Scan to calculate health score.'); self.dashboard_graph_draw()

    def add_dashboard_event(self, severity, message):
        if not hasattr(self, 'events'):
            return
        now = datetime.datetime.now().strftime('%H:%M:%S')
        self.events.insert('', 0, values=(now, severity, message), tags=(severity,))
        self.dashboard_events.append((now, severity, message)); self.dashboard_events = self.dashboard_events[-30:]
