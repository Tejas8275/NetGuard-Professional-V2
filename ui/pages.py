import datetime
"""
Phase 4 Step 3 — UX polish: activity/status feedback, button spacing,
and Treeview readability, on top of the Phase 3 SOC redesign.

Status labels that main.py already updates live during operations
(self.diag_status, self.scanner_status, self.security_score_label) are
now wrapped in a bordered "pill" container (ui.widgets._status_pill) so
the existing live text/color changes main.py makes (e.g. "Scanning…
N/254 hosts") are visually more prominent. Treeviews get a cosmetic
row-hover highlight (ui.widgets._enable_tree_hover) layered on top of
existing severity tags — no data or tag logic changed.

No logic changed: same Treeview `columns` tuples (order/names), same
`tag_configure` calls, same `command=` callback bindings, same widget
attribute names that main.py reaches into directly.

Scope discipline: only this file changes. Every page-builder method keeps
its exact name and signature:
  - diagnostics()
  - network_scanner_page()
  - monitor_page()
  - map_page()
  - system_page()
  - security_page()
  - alerts()
  - history()
  - reports()
  - settings()

Widget attribute names preserved verbatim (main.py depends on these):
  self.diag_status, self.target, self.pv, self.diag_last, self.out,
  self.scanner_status, self.scan_target, self.scan_progress,
  self.scan_tree, self.scanner_count, self.ml, self.ms, self.graph,
  self.mlog, self.map_status, self.map, self.sys_cards, self.system_output,
  self.system_running, self.security_score_label, self.security_summary,
  self.security_tree, self.security_output, self.alert_stats,
  self.alert_filter, self.at, self.ht, self.report_summary, self.rep,
  self.tv.

Note on "disabled while running": main.py's run()/do_*()/scan methods
start background threads and don't currently call back into these pages
to toggle button state while a job is in flight, so real disable-on-run
isn't wired without touching main.py (out of scope here). The button
style now supports a proper 'disabled' visual state (ui/widgets.py) so
this is ready to use the moment any button is explicitly disabled.

Theme handling: same pattern as ui/widgets.py and ui/dashboard.py — reads
`styles.T` dynamically instead of importing a frozen `T` binding, so live
theme switching (main.py's apply_theme() writes to `_styles.T`) keeps
working correctly.
"""
import tkinter as tk
from tkinter import ttk

import ui.styles as styles
from ui.styles import THEMES
from core.version import APP_VERSION
from core.network_core import info


class PagesMixin:
    def _section_header(self, parent, icon, text, bg=None):
        """Small reusable visual helper (local to this file only) for a
        consistent SOC-style section header: accent icon + uppercase
        muted label. Purely cosmetic — no state, no callbacks."""
        T = styles.T
        bg = bg or T['panel']
        row = tk.Frame(parent, bg=bg); row.pack(fill='x', padx=16, pady=(14, 7))
        tk.Frame(row, bg=T['accent'], width=3, height=16).pack(side='left', padx=(0, 9))
        self.L(row, icon, 10, True, T['accent'], bg).pack(side='left', padx=(0, 8))
        self.L(row, text, 9, True, T['muted'], bg).pack(side='left')
        return row

    def diagnostics(self):
        T = styles.T
        p = self.pages['Diagnostics']

        self.L(p, 'Diagnostic Operations', 18, True).pack(anchor='w', padx=18, pady=(12, 2))
        self.L(p, 'Run targeted connectivity and network diagnostics without leaving the operations console.', 9, False, T['muted']).pack(anchor='w', padx=18, pady=(0, 12))

        # Target / controls panel
        control = tk.Frame(p, bg=T['panel'], highlightthickness=1, highlightbackground=T['border'])
        control.pack(fill='x', padx=18, pady=(0, 12))

        top = tk.Frame(control, bg=T['panel']); top.pack(fill='x', padx=16, pady=(14, 10))
        self.L(top, '◈  TARGET CONFIGURATION', 9, True, T['muted'], T['panel']).pack(side='left')
        _diag_wrap, self.diag_status = self._status_pill(top, '● READY', T['good'], icon='')
        _diag_wrap.pack(side='right')

        tk.Frame(control, bg=T['border'], height=1).pack(fill='x', padx=16)

        context = tk.Frame(control, bg=T['panel']); context.pack(fill='x', padx=16, pady=(10, 0))
        for label, value, color in [
            ('EXECUTION', 'LOCAL', T['good']),
            ('RECORDING', 'HISTORY ENABLED', T['accent']),
            ('ALERTING', 'ABNORMAL RESULTS', T['warn']),
        ]:
            item = tk.Frame(context, bg=T['panel3'], highlightthickness=1, highlightbackground=T['border'])
            item.pack(side='left', padx=(0, 8), pady=0)
            self.L(item, label, 7, True, T['muted'], T['panel3']).pack(side='left', padx=(9, 5), pady=6)
            self.L(item, value, 7, True, color, T['panel3']).pack(side='left', padx=(0, 9), pady=6)

        fields = tk.Frame(control, bg=T['panel']); fields.pack(fill='x', padx=16, pady=(12, 12))
        self.target = tk.StringVar(value='google.com'); self.pv = tk.StringVar(value='443')

        self.L(fields, 'TARGET / HOST', 8, True, T['muted'], T['panel']).pack(side='left', padx=(0, 8))
        ttk.Entry(fields, textvariable=self.target, width=27).pack(side='left', ipady=3)
        self.L(fields, 'PORT', 8, True, T['muted'], T['panel']).pack(side='left', padx=(20, 8))
        ttk.Entry(fields, textvariable=self.pv, width=8).pack(side='left', ipady=3)

        # Primary diagnostics
        actions = tk.Frame(control, bg=T['panel']); actions.pack(fill='x', padx=16, pady=(0, 16))
        self.L(actions, 'DIAGNOSTIC TESTS', 8, True, T['muted'], T['panel']).pack(anchor='w', pady=(0, 8))
        btn_row = tk.Frame(actions, bg=T['panel']); btn_row.pack(fill='x')
        tests = [
            ('◉  PING', self.do_ping),
            ('⌁  DNS LOOKUP', self.do_dns),
            ('◆  PORT CHECK', self.do_port),
            ('↗  TRACEROUTE', self.do_trace),
            ('▣  CONNECTIONS', self.do_conns),
            ('▤  NET INFO', self.do_info)
        ]
        for label, fn in tests:
            ttk.Button(btn_row, text=label, command=fn).pack(side='left', padx=(0, 6))

        # Output workspace
        output_shell = tk.Frame(p, bg=T['panel'], highlightthickness=1, highlightbackground=T['border'])
        output_shell.pack(fill='both', expand=True, padx=18, pady=(0, 12))

        oh = tk.Frame(output_shell, bg=T['panel']); oh.pack(fill='x', padx=16, pady=(13, 8))
        self.L(oh, '▣', 10, True, T['accent'], T['panel']).pack(side='left', padx=(0, 8))
        self.L(oh, 'DIAGNOSTIC OUTPUT', 9, True, T['muted'], T['panel']).pack(side='left')
        self.diag_last = self.L(oh, 'No test executed', 8, False, T['muted'], T['panel'])
        self.diag_last.pack(side='right')

        tk.Frame(output_shell, bg=T['border'], height=1).pack(fill='x', padx=16)

        self.out = self.box(output_shell)
        self.out.pack_forget()
        # Re-parenting is not possible for an existing Tk widget, so the box is
        # created directly inside the output shell and its existing return value is
        # retained for run()/finish().
        f = tk.Frame(output_shell, bg=T['panel2']); f.pack(fill='both', expand=True, padx=16, pady=(12, 16))
        self.out = tk.Text(f, bg=T['panel2'], fg=T['text'], insertbackground=T['text'],
                            font=('Consolas', 9), relief='flat', wrap='word', padx=12, pady=10)
        s = ttk.Scrollbar(f, command=self.out.yview); self.out.configure(yscrollcommand=s.set)
        self.out.pack(side='left', fill='both', expand=True); s.pack(side='right', fill='y')

        output_actions = tk.Frame(output_shell, bg=T['panel'])
        output_actions.pack(fill='x', padx=16, pady=(0, 12))
        self.L(output_actions, 'Live results remain available in History and Reports.', 8, False, T['muted'], T['panel']).pack(side='left')
        ttk.Button(output_actions, text='CLEAR OUTPUT', command=lambda: self.out.delete('1.0', 'end')).pack(side='right')

        footer = tk.Frame(p, bg=T['bg']); footer.pack(fill='x', padx=18, pady=(0, 10))
        self.L(footer, 'Results are automatically recorded in History and included in Reports. Abnormal results create Alerts.', 8, False, T['muted'], T['bg']).pack(anchor='w')

    def network_scanner_page(self):
        T = styles.T
        p = self.pages['Network Scanner']

        self.L(p, 'Network Discovery', 18, True).pack(anchor='w', padx=18, pady=(12, 2))
        self.L(p, 'Discover devices, assess exposed services, and review network risk from one focused SOC workspace.', 9, False, T['muted']).pack(anchor='w', padx=18, pady=(0, 12))

        # --- Operational summary -------------------------------------------------
        summary = tk.Frame(p, bg=T['bg'])
        summary.pack(fill='x', padx=18, pady=(0, 12))

        def metric_card(parent, title, value, key, accent):
            card = tk.Frame(parent, bg=T['panel'], highlightthickness=1, highlightbackground=T['border'])
            card.pack(side='left', fill='x', expand=True, padx=(0, 8))
            tk.Frame(card, bg=accent, height=3).pack(fill='x')
            inner = tk.Frame(card, bg=T['panel']); inner.pack(fill='both', expand=True, padx=13, pady=(9, 10))
            self.L(inner, title, 8, True, T['muted'], T['panel']).pack(anchor='w')
            lab = self.L(inner, value, 18, True, T['text'], T['panel']); lab.pack(anchor='w', pady=(3, 0))
            setattr(self, key, lab)
            return lab

        metric_card(summary, 'DISCOVERED DEVICES', '0', 'scan_devices_metric', T['accent'])
        metric_card(summary, 'HIGH / CRITICAL', '0', 'scan_risk_metric', T['bad'])
        metric_card(summary, 'OPEN PORTS', '0', 'scan_ports_metric', T['warn'])
        metric_card(summary, 'SCAN STATE', 'READY', 'scan_state_metric', T['good'])

        # --- Scan controls --------------------------------------------------------
        controls = tk.Frame(p, bg=T['panel'], highlightthickness=1, highlightbackground=T['border'])
        controls.pack(fill='x', padx=18, pady=(0, 12))

        head = tk.Frame(controls, bg=T['panel']); head.pack(fill='x', padx=16, pady=(13, 8))
        self.L(head, '◈  SCAN CONTROL', 9, True, T['muted'], T['panel']).pack(side='left')
        _scan_wrap, self.scanner_status = self._status_pill(head, '● READY', T['good'], icon='')
        _scan_wrap.pack(side='right')

        tk.Frame(controls, bg=T['border'], height=1).pack(fill='x', padx=16)

        bar = tk.Frame(controls, bg=T['panel']); bar.pack(fill='x', padx=16, pady=(12, 10))
        self.L(bar, 'TARGET RANGE', 8, True, T['muted'], T['panel']).pack(side='left', padx=(0, 8))
        self.scan_target = tk.StringVar(value='192.168.1.')
        ttk.Entry(bar, textvariable=self.scan_target, width=24).pack(side='left', ipady=3)
        self.L(bar, 'PROFILE', 8, True, T['muted'], T['panel']).pack(side='left', padx=(12, 6))
        self.scan_profile = tk.StringVar(value='Standard')
        ttk.Combobox(bar, textvariable=self.scan_profile, values=['Quick Discovery', 'Standard', 'Deep Analysis'], state='readonly', width=17).pack(side='left', ipady=3)
        ttk.Button(bar, text='⌁  START SCAN', command=self.start_network_scan).pack(side='left', padx=(10, 5))
        self.scan_progress = ttk.Progressbar(bar, orient='horizontal', mode='determinate', maximum=254, length=180)
        self.scan_progress.pack(side='left', padx=8)
        ttk.Button(bar, text='CANCEL', command=self.cancel_network_scan).pack(side='left', padx=4)
        ttk.Button(bar, text='AUTO DETECT', command=self.auto_detect_network).pack(side='left', padx=4)

        scope = tk.Frame(controls, bg=T['panel']); scope.pack(fill='x', padx=16, pady=(0, 10))
        self.L(scope, 'SCAN SAFEGUARD', 8, True, T['muted'], T['panel']).pack(side='left', padx=(0, 8))
        self.L(scope, '● PRIVATE /24 NETWORKS ONLY', 8, True, T['good'], T['panel']).pack(side='left')
        self.L(scope, 'Authorized local discovery with bounded concurrency.', 8, False, T['muted'], T['panel']).pack(side='right')

        actions = tk.Frame(controls, bg=T['panel']); actions.pack(fill='x', padx=16, pady=(0, 13))
        self.L(actions, 'OPERATIONS', 8, True, T['muted'], T['panel']).pack(side='left', padx=(0, 10))
        ttk.Button(actions, text='EXPORT CSV', command=self.export_scan_csv).pack(side='left', padx=(0, 5))
        ttk.Button(actions, text='UPDATE VENDOR DB', command=self.update_vendor_database).pack(side='left', padx=5)
        self.L(actions, 'Quick skips hostname/port checks • Standard balances speed and context • Deep limits concurrency', 8, False, T['muted'], T['panel']).pack(side='right')
        self.scan_comparison = self.L(controls, 'Compare with the previous completed scan after running a scan.', 8, False, T['muted'], T['panel'])
        self.scan_comparison.pack(anchor='w', padx=16, pady=(0, 10))

        baseline_row = tk.Frame(controls, bg=T['panel'])
        baseline_row.pack(fill='x', padx=16, pady=(0, 12))
        self.L(baseline_row, 'BASELINE', 8, True, T['muted'], T['panel']).pack(side='left', padx=(0, 8))
        self.baseline_name = tk.StringVar(value='')
        ttk.Entry(baseline_row, textvariable=self.baseline_name, width=20).pack(side='left', ipady=3)
        ttk.Button(baseline_row, text='SAVE CURRENT', command=self.save_scan_baseline).pack(side='left', padx=(6, 14))
        self.L(baseline_row, 'SAVED', 8, True, T['muted'], T['panel']).pack(side='left', padx=(0, 6))
        self.baseline_selected = tk.StringVar(value='')
        self.baseline_selector = ttk.Combobox(baseline_row, textvariable=self.baseline_selected, values=[], state='readonly', width=20)
        self.baseline_selector.pack(side='left', ipady=3)
        ttk.Button(baseline_row, text='COMPARE', command=self.compare_selected_baseline).pack(side='left', padx=6)
        self.baseline_status = self.L(controls, 'Save a completed scan as a trusted baseline for later comparison.', 8, False, T['muted'], T['panel'])
        self.baseline_status.pack(anchor='w', padx=16, pady=(0, 10))

        # --- Results + inspector --------------------------------------------------
        body = tk.Frame(p, bg=T['bg'])
        body.pack(fill='both', expand=True, padx=18, pady=(0, 12))

        shell = tk.Frame(body, bg=T['panel'], highlightthickness=1, highlightbackground=T['border'])
        shell.pack(side='left', fill='both', expand=True, padx=(0, 10))

        th = tk.Frame(shell, bg=T['panel']); th.pack(fill='x', padx=16, pady=(13, 8))
        self.L(th, '▦', 10, True, T['accent'], T['panel']).pack(side='left', padx=(0, 8))
        self.L(th, 'DISCOVERED DEVICES', 9, True, T['muted'], T['panel']).pack(side='left')
        self.scanner_count = self.L(th, 'READY', 8, True, T['muted'], T['panel']); self.scanner_count.pack(side='right')
        tk.Frame(shell, bg=T['border'], height=1).pack(fill='x', padx=16)

        table = tk.Frame(shell, bg=T['panel2']); table.pack(fill='both', expand=True, padx=16, pady=(12, 16))
        cols = ('IP', 'MAC', 'HOSTNAME', 'PORTS', 'RISK SCORE', 'LEVEL')
        self.scan_tree = ttk.Treeview(table, columns=cols, show='headings', selectmode='browse')
        widths = {'IP': 135, 'MAC': 150, 'HOSTNAME': 185, 'PORTS': 210, 'RISK SCORE': 105, 'LEVEL': 105}
        for c in cols:
            self.scan_tree.heading(c, text=c)
            self.scan_tree.column(c, width=widths[c], anchor='w')
        self.scan_tree.tag_configure('critical', foreground=T['bad'])
        self.scan_tree.tag_configure('high', foreground=T['bad'])
        self.scan_tree.tag_configure('medium', foreground=T['warn'])
        self.scan_tree.tag_configure('low', foreground=T['good'])
        sb = ttk.Scrollbar(table, orient='vertical', command=self.scan_tree.yview)
        self.scan_tree.configure(yscrollcommand=sb.set)
        self.scan_tree.pack(side='left', fill='both', expand=True); sb.pack(side='right', fill='y')
        self._enable_tree_hover(self.scan_tree)

        # Selection inspector: purely GUI-side, reads the existing result row.
        inspector = tk.Frame(body, bg=T['panel'], width=285, highlightthickness=1, highlightbackground=T['border'])
        inspector.pack(side='right', fill='y'); inspector.pack_propagate(False)
        ih = tk.Frame(inspector, bg=T['panel']); ih.pack(fill='x', padx=14, pady=(13, 8))
        self.L(ih, '◈', 10, True, T['accent'], T['panel']).pack(side='left', padx=(0, 7))
        self.L(ih, 'DEVICE INSPECTOR', 9, True, T['muted'], T['panel']).pack(side='left')
        tk.Frame(inspector, bg=T['border'], height=1).pack(fill='x', padx=14)
        self.scan_inspector = tk.Text(inspector, height=16, bg=T['panel2'], fg=T['text'],
                                      insertbackground=T['text'], font=('Consolas', 9), relief='flat',
                                      wrap='word', padx=12, pady=12, state='disabled')
        self.scan_inspector.pack(fill='both', expand=True, padx=14, pady=14)

        self.L(inspector, 'Select a discovered device to inspect its address, vendor, services and risk.',
               8, False, T['muted'], T['panel']).pack(fill='x', padx=14, pady=(0, 14))

        def inspect_selected(_event=None):
            sel = self.scan_tree.selection()
            self.scan_inspector.configure(state='normal'); self.scan_inspector.delete('1.0', 'end')
            if not sel:
                self.scan_inspector.insert('1.0', 'No device selected.\n\nSelect a row from the discovery table.')
            else:
                values = self.scan_tree.item(sel[0], 'values')
                if values:
                    ip, mac, hostname, ports, risk, level = values
                    self.scan_inspector.insert('1.0',
                        f'IP ADDRESS\n{ip}\n\n'
                        f'MAC ADDRESS\n{mac}\n\n'
                        f'HOSTNAME\n{hostname}\n\n'
                        f'OPEN PORTS\n{ports or "None detected"}\n\n'
                        f'RISK SCORE\n{risk}\n\n'
                        f'RISK LEVEL\n{level}')
            self.scan_inspector.configure(state='disabled')

        self.scan_tree.bind('<<TreeviewSelect>>', inspect_selected)

        # GUI-only live summary: reads what is already displayed, never invents data.
        def refresh_scan_summary():
            try:
                children = self.scan_tree.get_children()
                high = critical = open_ports = 0
                for item in children:
                    vals = self.scan_tree.item(item, 'values')
                    if not vals: continue
                    level = str(vals[5]).upper() if len(vals) > 5 else ''
                    if level == 'CRITICAL': critical += 1
                    elif level == 'HIGH': high += 1
                    if len(vals) > 3 and str(vals[3]).strip() not in ('', 'None', 'None detected', '—'):
                        open_ports += len([x for x in str(vals[3]).split(',') if x.strip()])
                self.scan_devices_metric.config(text=str(len(children)))
                self.scan_risk_metric.config(text=str(high + critical), fg=T['bad'] if high + critical else T['good'])
                self.scan_ports_metric.config(text=str(open_ports), fg=T['warn'] if open_ports else T['good'])
                state = 'SCANNING' if getattr(self, 'scan_running', False) else ('RESULTS' if children else 'READY')
                self.scan_state_metric.config(text=state, fg=T['accent'] if state == 'SCANNING' else T['good'])
                self.after(700, refresh_scan_summary)
            except Exception:
                pass

        refresh_scan_summary()

        footer = tk.Frame(p, bg=T['bg']); footer.pack(fill='x', padx=18, pady=(0, 10))
        self.L(footer, 'Tip: run Auto Detect before scanning on Wi-Fi/Ethernet. New devices are checked against the existing device history.',
               8, False, T['muted'], T['bg']).pack(anchor='w')

    def monitor_page(self):
        T = styles.T
        p = self.pages['Live Monitor']

        self.L(p, 'Live Network Monitor', 18, True).pack(anchor='w', padx=18, pady=(12, 2))
        self.L(p, 'Latency sampling uses ICMP ping; HTTPS confirms connectivity when ping is blocked.', 9, False, T['muted']).pack(anchor='w', padx=18, pady=(0, 12))

        status_bar = tk.Frame(p, bg=T['panel'], highlightthickness=1, highlightbackground=T['border'])
        status_bar.pack(fill='x', padx=18, pady=(0, 12))
        r = tk.Frame(status_bar, bg=T['panel']); r.pack(fill='x', padx=16, pady=14)
        self.ml = self.L(r, '-- ms', 26, True, T['accent'], T['panel']); self.ml.pack(side='left', padx=(0, 20))
        self.ms = self.L(r, 'STOPPED', 10, True, T['muted'], T['panel']); self.ms.pack(side='left')

        chart_shell = tk.Frame(p, bg=T['panel'], highlightthickness=1, highlightbackground=T['border'])
        chart_shell.pack(fill='x', padx=18, pady=(0, 12))
        self._section_header(chart_shell, '◒', 'LATENCY (ms)')
        self.graph = tk.Canvas(chart_shell, bg=T['panel2'], height=300, highlightthickness=0)
        self.graph.pack(fill='x', padx=16, pady=(0, 16))

        self.L(p, 'MONITOR LOG', 8, True, T['muted']).pack(anchor='w', padx=18, pady=(0, 4))
        self.mlog = self.box(p)

    def map_page(self):
        T = styles.T
        p = self.pages['Network Map']

        self.L(p, 'Network Topology', 18, True).pack(
            anchor='w', padx=18, pady=(12, 2)
        )
        self.L(
            p, 'SOC network visibility and discovered-host topology.',
            9, False, T['muted']
        ).pack(anchor='w', padx=18, pady=(0, 10))

        cards = tk.Frame(p, bg=T['bg'])
        cards.pack(fill='x', padx=18, pady=(0, 10))
        self.map_kpis = {}

        def kpi(title, value, key, accent):
            card = tk.Frame(
                cards, bg=T['panel'],
                highlightthickness=1, highlightbackground=T['border']
            )
            card.pack(side='left', fill='both', expand=True, padx=(0, 8))
            tk.Frame(card, bg=accent, height=3).pack(fill='x')
            body = tk.Frame(card, bg=T['panel'])
            body.pack(fill='both', expand=True, padx=12, pady=8)
            self.L(body, title, 8, True, T['muted'], T['panel']).pack(anchor='w')
            value_label = self.L(
                body, value, 15, True, T['text'], T['panel']
            )
            value_label.pack(anchor='w', pady=(3, 0))
            self.map_kpis[key] = value_label

        kpi('DISCOVERED DEVICES', '0', 'devices', T['accent'])
        kpi('HIGH / CRITICAL', '0', 'high', T['bad'])
        kpi('MEDIUM RISK', '0', 'medium', T['warn'])
        kpi('GATEWAY', '--', 'gateway', T['good'])
        kpi('MAP STATUS', 'READY', 'status', T['muted'])

        toolbar = tk.Frame(
            p, bg=T['panel'],
            highlightthickness=1, highlightbackground=T['border']
        )
        toolbar.pack(fill='x', padx=18, pady=(0, 10))

        ttk.Button(
            toolbar, text='↻ REFRESH MAP', command=self.drawmap
        ).pack(side='left', padx=12, pady=9)

        self.map_status = self.L(
            toolbar, '● READY — run Network Scanner to populate topology.',
            8, True, T['muted'], T['panel']
        )
        self.map_status.pack(side='right', padx=14)

        legend = tk.Frame(p, bg=T['bg'])
        legend.pack(fill='x', padx=18, pady=(0, 10))
        self.L(legend, 'TOPOLOGY LEGEND', 8, True, T['muted'], T['bg']).pack(side='left', padx=(0, 10))
        for label, color in [('LOW RISK', T['good']), ('MEDIUM RISK', T['warn']), ('HIGH / CRITICAL', T['bad'])]:
            chip = tk.Frame(legend, bg=T['panel3'], highlightthickness=1, highlightbackground=T['border'])
            chip.pack(side='left', padx=(0, 7))
            tk.Label(chip, text='●', font=('Segoe UI', 8), fg=color, bg=T['panel3']).pack(side='left', padx=(8, 4), pady=5)
            self.L(chip, label, 7, True, T['text'], T['panel3']).pack(side='left', padx=(0, 8), pady=5)

        shell = tk.Frame(
            p, bg=T['panel'],
            highlightthickness=1, highlightbackground=T['border']
        )
        shell.pack(fill='both', expand=True, padx=18, pady=(0, 10))

        self.L(
            shell, '◎  NETWORK TOPOLOGY', 9, True,
            T['muted'], T['panel']
        ).pack(anchor='w', padx=14, pady=(10, 6))

        self.map = tk.Canvas(
            shell, bg=T['panel2'], highlightthickness=0
        )
        self.map.pack(fill='both', expand=True, padx=14, pady=(0, 14))

        self.after(250, self.drawmap)

    def drawmap(self):
        c = self.map
        c.delete('all')
        T = styles.T

        w = max(c.winfo_width(), 900)
        h = max(c.winfo_height(), 520)

        try:
            info_data = info()
        except Exception:
            info_data = {}

        gateway = str(info_data.get('Gateway', 'Unavailable'))
        dns = str(info_data.get('DNS', 'Unavailable'))
        local_ip = str(info_data.get('Local IP', 'Unavailable'))
        devices = list(getattr(self, 'scan_results', []) or [])

        # Subtle SOC grid.
        for x in range(0, w, 40):
            c.create_line(x, 0, x, h, fill=T['border'])
        for y in range(0, h, 40):
            c.create_line(0, y, w, y, fill=T['border'])

        # Core topology.
        core_y = 92
        core_x = [w * .16, w * .39, w * .62, w * .85]
        core_nodes = [
            ('LOCAL HOST', local_ip),
            ('GATEWAY', gateway),
            ('DNS', dns),
            ('EXTERNAL', 'Internet')
        ]

        for i in range(3):
            c.create_line(
                core_x[i] + 70, core_y,
                core_x[i + 1] - 70, core_y,
                fill=T['accent'], width=2
            )

        for x, (title, value) in zip(core_x, core_nodes):
            outline = T['good'] if title == 'GATEWAY' else T['accent']
            c.create_oval(
                x - 70, core_y - 34, x + 70, core_y + 34,
                fill=T['panel'], outline=outline, width=2
            )
            c.create_text(
                x, core_y - 8, text=title,
                fill=T['text'], font=('Segoe UI', 8, 'bold')
            )
            c.create_text(
                x, core_y + 12, text=value[:20],
                fill=T['muted'], font=('Consolas', 7)
            )

        if not devices:
            c.create_text(
                w / 2, h / 2 - 12,
                text='NO DISCOVERED DEVICES',
                fill=T['muted'], font=('Segoe UI', 12, 'bold')
            )
            c.create_text(
                w / 2, h / 2 + 15,
                text='Run Network Scanner, then select REFRESH MAP.',
                fill=T['muted'], font=('Segoe UI', 9)
            )
        else:
            c.create_text(
                24, 165, text=f'DISCOVERED HOSTS  •  {len(devices)}',
                anchor='w', fill=T['muted'],
                font=('Segoe UI', 8, 'bold')
            )

            cols = min(5, max(1, int((w - 70) / 175)))
            box_w, box_h = 160, 82
            gap_x, gap_y = 12, 14

            for i, d in enumerate(devices[:35]):
                row, col = divmod(i, cols)
                x = 24 + col * (box_w + gap_x)
                y = 192 + row * (box_h + gap_y)
                cx = x + box_w / 2

                risk = str(d.get('risk', '')).upper()
                if risk in ('HIGH', 'CRITICAL'):
                    accent = T['bad']
                elif risk in ('MEDIUM', 'WARNING'):
                    accent = T['warn']
                else:
                    accent = T['good']

                c.create_line(
                    core_x[1], core_y + 34, cx, y,
                    fill=T['border'], width=1
                )
                c.create_rectangle(
                    x, y, x + box_w, y + box_h,
                    fill=T['panel'], outline=accent, width=1
                )
                c.create_oval(
                    x + 10, y + 10, x + 18, y + 18,
                    fill=accent, outline=''
                )

                host = str(d.get('hostname') or 'Unknown')
                ip = str(d.get('ip') or 'Unknown')
                ports = str(d.get('ports') or '-')

                c.create_text(
                    x + 27, y + 14, text=host[:18],
                    anchor='w', fill=T['text'],
                    font=('Segoe UI', 8, 'bold')
                )
                c.create_text(
                    cx, y + 36, text=ip[:23],
                    fill=T['accent'], font=('Consolas', 7)
                )
                c.create_text(
                    cx, y + 59,
                    text=f'{risk or "LOW"}  •  PORTS {ports[:12]}',
                    fill=accent, font=('Segoe UI', 7, 'bold')
                )

        high = sum(
            1 for d in devices
            if str(d.get('risk', '')).upper() in ('HIGH', 'CRITICAL')
        )
        medium = sum(
            1 for d in devices
            if str(d.get('risk', '')).upper() in ('MEDIUM', 'WARNING')
        )

        if hasattr(self, 'map_kpis'):
            self.map_kpis['devices'].config(text=str(len(devices)))
            self.map_kpis['high'].config(text=str(high))
            self.map_kpis['medium'].config(text=str(medium))
            self.map_kpis['gateway'].config(text=gateway[:18])
            self.map_kpis['status'].config(
                text='ONLINE' if devices else 'READY',
                fg=T['good'] if devices else T['muted']
            )

        if hasattr(self, 'map_status'):
            self.map_status.config(
                text=(
                    f'● {len(devices)} HOST(S) DISCOVERED  •  '
                    f'GATEWAY {gateway[:18]}  •  '
                    f'{datetime.datetime.now():%H:%M:%S}'
                ),
                fg=T['good'] if devices else T['muted']
            )

    def system_page(self):
        T = styles.T
        p = self.pages['System Monitor']
        self.L(p, 'Advanced System Performance Monitor', 18, True).pack(anchor='w', padx=18, pady=(12, 3))
        self.L(p, 'Live CPU, RAM, disk and network health monitoring.', 9, False, T['muted']).pack(anchor='w', padx=18, pady=(0, 12))

        cards = tk.Frame(p, bg=T['bg'])
        cards.pack(fill='x', padx=14, pady=(0, 10))
        self.sys_cards = {}
        icons = {'cpu': '▤', 'ram': '▣', 'disk': '◈', 'net': '◉'}
        for title, key in [('CPU', 'cpu'), ('MEMORY', 'ram'), ('DISK', 'disk'), ('NETWORK', 'net')]:
            f = tk.Frame(cards, bg=T['panel'], highlightthickness=1, highlightbackground=T['border'])
            f.pack(side='left', fill='both', expand=True, padx=5)
            head = tk.Frame(f, bg=T['panel']); head.pack(fill='x', padx=14, pady=(12, 0))
            self.L(head, icons.get(key, '•'), 10, True, T['accent'], T['panel']).pack(side='left', padx=(0, 6))
            self.L(head, title, 9, True, T['muted'], T['panel']).pack(side='left')
            v = self.L(f, '--', 20, True, T['text'], T['panel'])
            v.pack(anchor='w', padx=14, pady=(6, 14))
            self.sys_cards[key] = v

        bar = tk.Frame(p, bg=T['panel'], highlightthickness=1, highlightbackground=T['border'])
        bar.pack(fill='x', padx=18, pady=(0, 12))
        btn_row = tk.Frame(bar, bg=T['panel']); btn_row.pack(fill='x', padx=8, pady=9)
        ttk.Button(btn_row, text='🔄 RUN SYSTEM CHECK', command=self.system_scan).pack(side='left', padx=6)
        ttk.Button(btn_row, text='▶ LIVE SYSTEM MONITOR', command=self.start_system_monitor).pack(side='left', padx=6)
        ttk.Button(btn_row, text='■ STOP', command=self.stop_system_monitor).pack(side='left', padx=6)
        self.system_running = False

        self.L(p, 'SYSTEM CHECK OUTPUT', 8, True, T['muted']).pack(anchor='w', padx=18, pady=(0, 4))
        self.system_output = self.box(p)

    def security_page(self):
        T = styles.T
        p = self.pages['Security Center']
        self.L(p, 'Security Operations Center', 18, True).pack(anchor='w', padx=18, pady=(12, 3))
        self.L(p, 'Security posture analysis based on discovered devices, exposed ports, and local connection data.', 9, False, T['muted']).pack(anchor='w', padx=18, pady=(0, 12))

        bar = tk.Frame(p, bg=T['panel'], highlightthickness=1, highlightbackground=T['border'])
        bar.pack(fill='x', padx=18, pady=(0, 12))
        row = tk.Frame(bar, bg=T['panel']); row.pack(fill='x', padx=8, pady=10)
        ttk.Button(row, text='🔍 RUN SECURITY CHECK', command=self.security_scan).pack(side='left', padx=8)
        _sec_wrap, self.security_score_label = self._status_pill(row, 'SECURITY SCORE: --', T['muted'])
        _sec_wrap.pack(side='left', padx=12)
        self.security_summary = self.L(row, 'Run a check after network discovery.', 9, False, T['muted'], T['panel']); self.security_summary.pack(side='left', padx=8)

        context = tk.Frame(p, bg=T['bg']); context.pack(fill='x', padx=18, pady=(0, 12))
        for label, value, color in [
            ('DISCOVERY INPUT', 'LOCAL SCAN RESULTS', T['accent']),
            ('PORT ANALYSIS', 'RISK WEIGHTED', T['warn']),
            ('INCIDENT ROUTING', 'ALERTS ENABLED', T['good']),
        ]:
            item = tk.Frame(context, bg=T['panel3'], highlightthickness=1, highlightbackground=T['border'])
            item.pack(side='left', padx=(0, 8))
            self.L(item, label, 7, True, T['muted'], T['panel3']).pack(side='left', padx=(9, 5), pady=6)
            self.L(item, value, 7, True, color, T['panel3']).pack(side='left', padx=(0, 9), pady=6)

        body = tk.Frame(p, bg=T['panel'], highlightthickness=1, highlightbackground=T['border']); body.pack(fill='both', expand=True, padx=18, pady=(0, 12))
        self._section_header(body, '◆', 'SECURITY FINDINGS')
        tk.Frame(body, bg=T['border'], height=1).pack(fill='x', padx=14)
        table = tk.Frame(body, bg=T['panel2']); table.pack(fill='both', expand=True, padx=14, pady=(10, 14))
        cols = ('SEVERITY', 'DEVICE', 'IP', 'FINDING', 'PORTS')
        self.security_tree = ttk.Treeview(table, columns=cols, show='headings', selectmode='browse')
        widths = {'SEVERITY': 100, 'DEVICE': 180, 'IP': 135, 'FINDING': 420, 'PORTS': 120}
        for c in cols:
            self.security_tree.heading(c, text=c); self.security_tree.column(c, width=widths[c], anchor='w')
        sb = ttk.Scrollbar(table, orient='vertical', command=self.security_tree.yview); self.security_tree.configure(yscrollcommand=sb.set)
        self.security_tree.pack(side='left', fill='both', expand=True); sb.pack(side='right', fill='y')
        self._enable_tree_hover(self.security_tree)

        output_shell = tk.Frame(p, bg=T['panel'], highlightthickness=1, highlightbackground=T['border'])
        output_shell.pack(fill='x', padx=18, pady=(0, 12))
        self._section_header(output_shell, '▤', 'SECURITY CHECK OUTPUT')
        self.security_output = self.box(output_shell); self.security_output.configure(height=7)

    def alerts(self):
        T = styles.T
        p = self.pages['Alerts']
        self.L(p, 'Network Alerts', 18, True).pack(anchor='w', padx=18, pady=(12, 3))
        self.L(p, 'Diagnostics, health scans and live monitoring automatically feed this incident stream.', 9, False, T['muted']).pack(anchor='w', padx=18, pady=(0, 10))

        bar = tk.Frame(p, bg=T['bg']); bar.pack(fill='x', padx=18, pady=(0, 8))
        ttk.Button(bar, text='✓ ACKNOWLEDGE SELECTED', command=self.ack_alert).pack(side='left', padx=(0, 6))
        ttk.Button(bar, text='🧹 CLEAR ALERTS', command=self.clear_alerts).pack(side='left', padx=(0, 6))
        ttk.Button(bar, text='📄 EXPORT INCIDENTS', command=self.export_alerts).pack(side='left')

        stats = tk.Frame(p, bg=T['bg']); stats.pack(fill='x', padx=18, pady=(0, 8))
        self.alert_stats = {}
        for key, title in [('CRITICAL', 'CRITICAL'), ('HIGH', 'HIGH'), ('WARNING', 'WARNING'), ('MEDIUM', 'MEDIUM'), ('LOW', 'LOW'), ('ACK', 'ACKNOWLEDGED')]:
            f = tk.Frame(stats, bg=T['panel'], highlightbackground=T['border'], highlightthickness=1); f.pack(side='left', fill='x', expand=True, padx=3)
            self.L(f, title, 8, True, T['muted'], T['panel']).pack(anchor='w', padx=10, pady=(8, 0))
            lbl = self.L(f, '0', 16, True, T['text'], T['panel']); lbl.pack(anchor='w', padx=10, pady=(1, 8)); self.alert_stats[key] = lbl

        bar = tk.Frame(p, bg=T['panel'], highlightthickness=1, highlightbackground=T['border']); bar.pack(fill='x', padx=18, pady=(0, 10))
        filter_row = tk.Frame(bar, bg=T['panel']); filter_row.pack(fill='x', padx=10, pady=8)
        self.alert_filter = tk.StringVar(value='ALL')
        ttk.Label(filter_row, text='FILTER', background=T['panel'], foreground=T['muted']).pack(side='left', padx=(0, 6))
        cb = ttk.Combobox(filter_row, textvariable=self.alert_filter, values=['ALL', 'CRITICAL', 'HIGH', 'WARNING', 'MEDIUM', 'LOW', 'ACK'], state='readonly', width=12)
        cb.pack(side='left', padx=(0, 10)); cb.bind('<<ComboboxSelected>>', lambda e: self.filter_alerts())
        ttk.Button(filter_row, text='✓ ACKNOWLEDGE SELECTED', command=self.ack_alert).pack(side='left', padx=(0, 6))
        ttk.Button(filter_row, text='🧹 CLEAR ACKNOWLEDGED', command=self.clear_acknowledged).pack(side='left', padx=(0, 6))
        ttk.Button(filter_row, text='CLEAR ALL', command=self.clear_alerts).pack(side='left', padx=(0, 6))
        ttk.Button(filter_row, text='📄 EXPORT INCIDENTS', command=self.export_alerts).pack(side='left')

        table_shell = tk.Frame(p, bg=T['panel'], highlightthickness=1, highlightbackground=T['border'])
        table_shell.pack(fill='both', expand=True, padx=18, pady=(0, 12))
        self._section_header(table_shell, '!', 'INCIDENT STREAM')
        table = tk.Frame(table_shell, bg=T['panel2'])
        table.pack(fill='both', expand=True, padx=14, pady=(0, 14))
        self.at = ttk.Treeview(table, columns=('time', 'sev', 'msg', 'source'), show='headings', selectmode='extended')
        for c, h, w in [('time', 'Time', 150), ('sev', 'Severity', 110), ('msg', 'Message', 650), ('source', 'Source', 150)]:
            self.at.heading(c, text=h); self.at.column(c, width=w)
        self.at.tag_configure('CRITICAL', foreground=T['bad']); self.at.tag_configure('HIGH', foreground=T['warn']); self.at.tag_configure('WARNING', foreground=T['warn']); self.at.tag_configure('MEDIUM', foreground=T['warn']); self.at.tag_configure('ACK', foreground=T['muted'])
        sb = ttk.Scrollbar(table, orient='vertical', command=self.at.yview)
        self.at.configure(yscrollcommand=sb.set)
        self.at.pack(side='left', fill='both', expand=True); sb.pack(side='right', fill='y')
        self._enable_tree_hover(self.at)
        self.refresh_alert_summary()

    def history(self):
        T = styles.T
        p = self.pages['History']

        self.L(p, 'Security Audit History', 18, True).pack(
            anchor='w', padx=18, pady=(12, 3)
        )
        self.L(
            p,
            'Chronological audit trail of diagnostics, scans, system checks and security operations.',
            9, False, T['muted']
        ).pack(anchor='w', padx=18, pady=(0, 10))

        # Live audit KPIs
        kpi_row = tk.Frame(p, bg=T['bg'])
        kpi_row.pack(fill='x', padx=18, pady=(0, 10))
        self.history_kpis = {}

        def kpi(title, value, key, accent):
            card = tk.Frame(kpi_row, bg=T['panel'], highlightthickness=1,
                            highlightbackground=T['border'])
            card.pack(side='left', fill='both', expand=True, padx=(0, 8))
            tk.Frame(card, bg=accent, height=3).pack(fill='x')
            inner = tk.Frame(card, bg=T['panel'])
            inner.pack(fill='both', expand=True, padx=12, pady=8)
            self.L(inner, title, 8, True, T['muted'], T['panel']).pack(anchor='w')
            lab = self.L(inner, value, 17, True, T['text'], T['panel'])
            lab.pack(anchor='w', pady=(3, 0))
            self.history_kpis[key] = lab

        kpi('TOTAL EVENTS', '0', 'total', T['accent'])
        kpi('TODAY', '0', 'today', T['good'])
        kpi('SCANS', '0', 'scans', T['accent'])
        kpi('ALERT-RELATED', '0', 'alerts', T['warn'])

        # Operations bar
        bar = tk.Frame(p, bg=T['panel'], highlightthickness=1,
                       highlightbackground=T['border'])
        bar.pack(fill='x', padx=18, pady=(0, 10))

        row1 = tk.Frame(bar, bg=T['panel'])
        row1.pack(fill='x', padx=12, pady=9)

        self.L(row1, 'FILTER', 8, True, T['muted'], T['panel']).pack(side='left', padx=(0, 7))

        self.history_filter = ttk.Combobox(
            row1,
            values=['ALL', 'SCAN', 'SYSTEM', 'NETWORK', 'SECURITY', 'ALERT', 'OTHER'],
            state='readonly',
            width=14
        )
        self.history_filter.set('ALL')
        self.history_filter.pack(side='left', padx=(0, 8))
        self.history_filter.bind('<<ComboboxSelected>>', lambda e: self.filter_history())

        self.history_search_var = tk.StringVar()
        search = ttk.Entry(
            row1,
            textvariable=self.history_search_var,
            width=32
        )
        search.pack(side='left', padx=(0, 8))
        search.bind('<KeyRelease>', lambda e: self.filter_history())

        ttk.Button(
            row1, text='↻ REFRESH',
            command=self.filter_history
        ).pack(side='left', padx=(0, 6))

        ttk.Button(
            row1, text='📄 EXPORT JSON',
            command=self.export
        ).pack(side='left', padx=(0, 6))

        ttk.Button(
            row1, text='🧹 CLEAR',
            command=self.clear
        ).pack(side='left')

        self.history_state = self.L(
            row1, 'AUDIT STREAM READY', 8, True, T['good'], T['panel']
        )
        self.history_state.pack(side='right')

        # Main workspace
        workspace = tk.Frame(p, bg=T['bg'])
        workspace.pack(fill='both', expand=True, padx=18, pady=(0, 10))

        left = tk.Frame(workspace, bg=T['panel'], highlightthickness=1,
                        highlightbackground=T['border'])
        left.pack(side='left', fill='both', expand=True, padx=(0, 8))

        self.L(
            left, 'AUDIT EVENT STREAM', 9, True, T['muted'], T['panel']
        ).pack(anchor='w', padx=14, pady=(11, 7))

        self.ht = ttk.Treeview(
            left,
            columns=('time', 'act', 'res'),
            show='headings',
            selectmode='browse'
        )
        for c, h, w in [
            ('time', 'TIMESTAMP', 175),
            ('act', 'EVENT / ACTION', 210),
            ('res', 'RESULT / DETAILS', 650)
        ]:
            self.ht.heading(c, text=h)
            self.ht.column(c, width=w, minwidth=80)

        self.ht.tag_configure('SCAN', foreground=T['accent'])
        self.ht.tag_configure('SECURITY', foreground=T['bad'])
        self.ht.tag_configure('ALERT', foreground=T['warn'])
        self.ht.tag_configure('SYSTEM', foreground=T['good'])
        self.ht.tag_configure('NETWORK', foreground=T['accent'])
        self.ht.tag_configure('OTHER', foreground=T['text'])

        self.ht.pack(fill='both', expand=True, padx=14, pady=(0, 14))
        self._enable_tree_hover(self.ht)
        self.ht.bind('<<TreeviewSelect>>', lambda e: self.show_history_details())

        right = tk.Frame(workspace, bg=T['panel'], highlightthickness=1,
                         highlightbackground=T['border'], width=315)
        right.pack(side='right', fill='both')
        right.pack_propagate(False)

        self.L(
            right, 'EVENT DETAILS', 9, True, T['muted'], T['panel']
        ).pack(anchor='w', padx=14, pady=(11, 7))

        self.history_details = self.box(right)
        self.history_details.pack(fill='both', expand=True, padx=14, pady=(0, 14))

        self.update_history_summary()
        self.filter_history()

    def _history_items(self):
        items = []
        for x in getattr(self, 'hist', []):
            if not isinstance(x, dict):
                continue
            items.append({
                'time': str(x.get('time', '')),
                'action': str(x.get('action', '')),
                'result': str(x.get('result', ''))
            })
        return items

    def _history_category(self, action):
        a = action.upper()
        if 'ALERT' in a:
            return 'ALERT'
        if any(k in a for k in ('SECURITY', 'RISK', 'THREAT')):
            return 'SECURITY'
        if any(k in a for k in ('SCAN', 'DIAGNOSTIC', 'HEALTH')):
            return 'SCAN'
        if any(k in a for k in ('NETWORK', 'PING', 'DNS', 'PORT', 'DEVICE')):
            return 'NETWORK'
        if any(k in a for k in ('SYSTEM', 'MONITOR')):
            return 'SYSTEM'
        return 'OTHER'

    def filter_history(self):
        if not hasattr(self, 'ht'):
            return

        selected = self.history_filter.get() if hasattr(self, 'history_filter') else 'ALL'
        query = self.history_search_var.get().strip().lower() if hasattr(self, 'history_search_var') else ''

        for iid in self.ht.get_children():
            self.ht.delete(iid)

        shown = 0
        for x in reversed(self._history_items()):
            category = self._history_category(x['action'])
            haystack = f"{x['time']} {x['action']} {x['result']}".lower()

            if selected != 'ALL' and category != selected:
                continue
            if query and query not in haystack:
                continue

            iid = self.ht.insert(
                '', 'end',
                values=(
                    x['time'],
                    x['action'],
                    x['result'][:220].replace('\n', ' ')
                ),
                tags=(category,)
            )
            shown += 1

        self.history_state.config(
            text=f'{shown} EVENT{"S" if shown != 1 else ""} DISPLAYED',
            fg=styles.T['accent'] if shown else styles.T['muted']
        )
        self.update_history_summary()

    def show_history_details(self):
        if not hasattr(self, 'history_details'):
            return
        selected = self.ht.selection()
        self.history_details.delete('1.0', 'end')

        if not selected:
            self.history_details.insert(
                '1.0',
                'Select an event from the audit stream to inspect its details.'
            )
            return

        vals = self.ht.item(selected[0], 'values')
        if len(vals) < 3:
            return

        category = self._history_category(str(vals[1]))
        details = (
            f'EVENT CATEGORY\n{category}\n\n'
            f'TIMESTAMP\n{vals[0]}\n\n'
            f'ACTION\n{vals[1]}\n\n'
            f'RESULT / DETAILS\n{vals[2]}'
        )
        self.history_details.insert('1.0', details)

    def update_history_summary(self):
        if not hasattr(self, 'history_kpis'):
            return

        items = self._history_items()
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        today_count = sum(1 for x in items if x['time'].startswith(today))

        scans = sum(
            1 for x in items
            if self._history_category(x['action']) == 'SCAN'
        )
        alerts = sum(
            1 for x in items
            if self._history_category(x['action']) in ('ALERT', 'SECURITY')
        )

        self.history_kpis['total'].config(text=str(len(items)))
        self.history_kpis['today'].config(text=str(today_count))
        self.history_kpis['scans'].config(text=str(scans))
        self.history_kpis['alerts'].config(text=str(alerts))

    def reports(self):
        T = styles.T
        p = self.pages['Reports']
        self.L(p, 'Reports & Documentation', 18, True).pack(anchor='w', padx=18, pady=(12, 3))
        self.L(p, 'Unified view of health scans, diagnostics, alerts and monitoring history.', 9, False, T['muted']).pack(anchor='w', padx=18, pady=(0, 10))

        bar = tk.Frame(p, bg=T['panel'], highlightthickness=1, highlightbackground=T['border']); bar.pack(fill='x', padx=18, pady=(0, 10))
        row = tk.Frame(bar, bg=T['panel']); row.pack(fill='x', padx=10, pady=9)
        ttk.Button(row, text='🔄 REFRESH SUMMARY', command=self.update_report_summary).pack(side='left', padx=(0, 6))
        ttk.Button(row, text='📄 EXPORT UNIFIED REPORT', command=self.report).pack(side='left', padx=(0, 6))
        ttk.Button(row, text='📦 EXPORT JSON', command=self.export_unified_json).pack(side='left')

        export_context = tk.Frame(p, bg=T['bg']); export_context.pack(fill='x', padx=18, pady=(0, 10))
        for label, value, color in [
            ('REPORT SCOPE', 'UNIFIED LOCAL DATA', T['accent']),
            ('FORMATS', 'TEXT + JSON', T['good']),
            ('PERSISTENCE', 'NO CLOUD UPLOAD', T['muted']),
        ]:
            item = tk.Frame(export_context, bg=T['panel3'], highlightthickness=1, highlightbackground=T['border'])
            item.pack(side='left', padx=(0, 8))
            self.L(item, label, 7, True, T['muted'], T['panel3']).pack(side='left', padx=(9, 5), pady=6)
            self.L(item, value, 7, True, color, T['panel3']).pack(side='left', padx=(0, 9), pady=6)

        workspace = tk.Frame(p, bg=T['bg'])
        workspace.pack(fill='both', expand=True, padx=18, pady=(0, 12))
        summary_shell = tk.Frame(workspace, bg=T['panel'], highlightthickness=1, highlightbackground=T['border'])
        summary_shell.pack(side='left', fill='both', expand=True, padx=(0, 8))
        self._section_header(summary_shell, '▣', 'UNIFIED SUMMARY')
        self.report_summary = self.box(summary_shell)

        raw_shell = tk.Frame(workspace, bg=T['panel'], highlightthickness=1, highlightbackground=T['border'])
        raw_shell.pack(side='left', fill='both', expand=True)
        self._section_header(raw_shell, '▤', 'RAW HEALTH REPORT')
        self.rep = self.box(raw_shell); self.rep.config(height=8)
        self.update_report_summary()

    def settings(self):
        T = styles.T
        p = self.pages['Settings']

        self.L(p, 'Settings & Themes', 18, True).pack(
            anchor='w', padx=18, pady=(12, 3)
        )
        self.L(
            p,
            'Configure console appearance and review security-engine status.',
            9, False, T['muted']
        ).pack(anchor='w', padx=18, pady=(0, 12))

        # Appearance panel
        appearance = tk.Frame(
            p, bg=T['panel'],
            highlightthickness=1, highlightbackground=T['border']
        )
        appearance.pack(fill='x', padx=18, pady=(0, 12))

        self._section_header(appearance, '◈', 'APPEARANCE')
        tk.Frame(appearance, bg=T['border'], height=1).pack(fill='x', padx=14)

        row = tk.Frame(appearance, bg=T['panel'])
        row.pack(fill='x', padx=16, pady=14)

        self.L(
            row, 'ACTIVE THEME', 8, True, T['muted'], T['panel']
        ).pack(side='left', padx=(0, 12))

        self.tv = tk.StringVar(value='Midnight Blue')
        theme_box = ttk.Combobox(
            row,
            textvariable=self.tv,
            values=list(THEMES),
            state='readonly',
            width=25
        )
        theme_box.pack(side='left')

        ttk.Button(
            row,
            text='APPLY THEME NOW',
            command=self.apply_theme
        ).pack(side='left', padx=12)

        self.settings_theme_status = self.L(
            row, '● READY', 8, True, T['good'], T['panel']
        )
        self.settings_theme_status.pack(side='right')

        appearance_context = tk.Frame(appearance, bg=T['panel'])
        appearance_context.pack(fill='x', padx=16, pady=(0, 14))
        for label, value, color in [
            ('APPLY MODE', 'NO RESTART', T['good']),
            ('SCOPE', 'THIS CONSOLE', T['accent']),
            ('PROTECTION', 'DATA UNCHANGED', T['muted']),
        ]:
            item = tk.Frame(appearance_context, bg=T['panel3'], highlightthickness=1, highlightbackground=T['border'])
            item.pack(side='left', padx=(0, 8))
            self.L(item, label, 7, True, T['muted'], T['panel3']).pack(side='left', padx=(9, 5), pady=6)
            self.L(item, value, 7, True, color, T['panel3']).pack(side='left', padx=(0, 9), pady=6)

        thresholds = tk.Frame(
            p, bg=T['panel'],
            highlightthickness=1, highlightbackground=T['border']
        )
        thresholds.pack(fill='x', padx=18, pady=(0, 12))
        self._section_header(thresholds, '◌', 'HEALTH THRESHOLDS')
        self.L(
            thresholds,
            'Set when latency and packet loss change from healthy to warning or critical. Values are saved locally.',
            8, False, T['muted'], T['panel']
        ).pack(anchor='w', padx=16, pady=(0, 8))
        threshold_row = tk.Frame(thresholds, bg=T['panel'])
        threshold_row.pack(fill='x', padx=16, pady=(0, 12))
        self.health_threshold_vars = {}
        for key, label, unit in (
            ('latency_warning_ms', 'LATENCY WARNING', 'ms'),
            ('latency_critical_ms', 'LATENCY CRITICAL', 'ms'),
            ('packet_loss_warning_pct', 'LOSS WARNING', '%'),
            ('packet_loss_critical_pct', 'LOSS CRITICAL', '%'),
        ):
            field = tk.Frame(threshold_row, bg=T['panel3'], highlightthickness=1, highlightbackground=T['border'])
            field.pack(side='left', fill='x', expand=True, padx=(0, 10))
            self.L(field, label, 8, True, T['muted'], T['panel3']).pack(anchor='w', padx=10, pady=(8, 0))
            variable = tk.StringVar(value=f'{self.health_thresholds[key]:g}')
            self.health_threshold_vars[key] = variable
            entry_row = tk.Frame(field, bg=T['panel3'])
            entry_row.pack(fill='x', padx=10, pady=(4, 9))
            ttk.Entry(entry_row, textvariable=variable, width=9).pack(side='left', ipady=3)
            self.L(entry_row, unit, 8, True, T['muted'], T['panel3']).pack(side='left', padx=6)
        ttk.Button(threshold_row, text='SAVE THRESHOLDS', command=self.save_health_thresholds).pack(side='left', padx=(2, 10), pady=(14, 0))
        self.health_threshold_status = self.L(thresholds, '● Default health thresholds active.', 8, True, T['good'], T['panel'])
        self.health_threshold_status.pack(anchor='w', padx=16, pady=(0, 12))

        retention = tk.Frame(
            p, bg=T['panel'],
            highlightthickness=1, highlightbackground=T['border']
        )
        retention.pack(fill='x', padx=18, pady=(0, 12))
        self._section_header(retention, '◷', 'LOCAL DATA RETENTION')
        self.L(
            retention,
            'Choose how many newest audit events and incidents remain in local storage. Reducing a limit asks before older records are removed.',
            8, False, T['muted'], T['panel']
        ).pack(anchor='w', padx=16, pady=(0, 8))
        retention_row = tk.Frame(retention, bg=T['panel'])
        retention_row.pack(fill='x', padx=16, pady=(0, 10))
        self.retention_limit_vars = {}
        for key, label in (('history', 'AUDIT EVENTS'), ('alerts', 'INCIDENTS')):
            field = tk.Frame(retention_row, bg=T['panel3'], highlightthickness=1, highlightbackground=T['border'])
            field.pack(side='left', padx=(0, 22))
            self.L(field, label, 8, True, T['muted'], T['panel3']).pack(anchor='w', padx=10, pady=(8, 0))
            variable = tk.StringVar(value=str(self.retention_limits[key]))
            self.retention_limit_vars[key] = variable
            ttk.Combobox(field, textvariable=variable, values=['100', '200', '500', '1000'], state='readonly', width=8).pack(anchor='w', padx=10, pady=(4, 9))
        ttk.Button(retention_row, text='SAVE RETENTION', command=self.save_retention_limits).pack(side='left', padx=(8, 12), pady=(14, 0))
        self.retention_status = self.L(retention, '● Default local retention: 200 audit events and 200 incidents.', 8, True, T['good'], T['panel'])
        self.retention_status.pack(anchor='w', padx=16, pady=(0, 12))

        # Status cards
        cards = tk.Frame(p, bg=T['bg'])
        cards.pack(fill='x', padx=18, pady=(0, 12))

        def status_card(title, value, detail, accent):
            card = tk.Frame(
                cards, bg=T['panel'],
                highlightthickness=1, highlightbackground=T['border']
            )
            card.pack(side='left', fill='both', expand=True, padx=(0, 8))
            tk.Frame(card, bg=accent, height=3).pack(fill='x')

            body = tk.Frame(card, bg=T['panel'])
            body.pack(fill='both', expand=True, padx=13, pady=11)

            self.L(
                body, title, 8, True, T['muted'], T['panel']
            ).pack(anchor='w')
            self.L(
                body, value, 13, True, accent, T['panel']
            ).pack(anchor='w', pady=(5, 2))
            self.L(
                body, detail, 8, False, T['muted'], T['panel']
            ).pack(anchor='w')

        status_card(
            'SECURITY ENGINE', 'ONLINE',
            'Core protection services available', T['good']
        )
        status_card(
            'THEME ENGINE', 'LIVE',
            'Changes apply without restart', T['accent']
        )
        status_card(
            'AUTHENTICATION', 'READY',
            'Secure login service active', T['good']
        )

        # Information / theme list
        bottom = tk.Frame(p, bg=T['bg'])
        bottom.pack(fill='both', expand=True, padx=18, pady=(0, 10))

        info_panel = tk.Frame(
            bottom, bg=T['panel'],
            highlightthickness=1, highlightbackground=T['border']
        )
        info_panel.pack(side='left', fill='both', expand=True, padx=(0, 8))

        self._section_header(info_panel, '●', 'CONSOLE INFORMATION')

        info = tk.Frame(info_panel, bg=T['panel'])
        info.pack(fill='x', padx=16, pady=(2, 14))

        rows = [
            ('PRODUCT', 'NETGUARD PRO'),
            ('VERSION', f'v{APP_VERSION}'),
            ('SECURITY ENGINE', 'ONLINE'),
            ('CONNECTION', 'ENCRYPTED'),
            ('CONFIGURATION', 'LOCAL'),
        ]

        for label, value in rows:
            r = tk.Frame(info, bg=T['panel'])
            r.pack(fill='x', pady=4)
            self.L(
                r, label, 8, True, T['muted'], T['panel']
            ).pack(side='left')
            self.L(
                r, value, 8, True,
                T['good'] if value in ('ONLINE', 'ENCRYPTED')
                else T['text'],
                T['panel']
            ).pack(side='right')

        themes_panel = tk.Frame(
            bottom, bg=T['panel'],
            highlightthickness=1, highlightbackground=T['border']
        )
        themes_panel.pack(side='right', fill='both', expand=True)

        self._section_header(themes_panel, '◆', 'AVAILABLE THEMES')

        theme_info = tk.Frame(themes_panel, bg=T['panel'])
        theme_info.pack(fill='x', padx=16, pady=(0, 14))

        theme_descriptions = {
            'Midnight Blue': 'Default SOC / high-contrast dark console',
            'Cyber Purple': 'Purple cyber-operations visual profile',
            'Emerald SOC': 'Green security-operations visual profile',
        }

        for name in THEMES:
            r = tk.Frame(theme_info, bg=T['panel'])
            r.pack(fill='x', pady=5)

            dot = tk.Canvas(
                r, width=10, height=10,
                bg=T['panel'], highlightthickness=0
            )
            dot.pack(side='left', padx=(0, 8))
            dot.create_oval(
                1, 1, 9, 9,
                fill=T['accent'] if name == self.tv.get() else T['muted'],
                outline=''
            )

            self.L(
                r, name, 8, True, T['text'], T['panel']
            ).pack(side='left')
            self.L(
                r, theme_descriptions[name], 7, False,
                T['muted'], T['panel']
            ).pack(side='right')

        self.L(
            p,
            'Theme selection changes the visual console only. Authentication, scanning, monitoring and stored data remain unchanged.',
            8, False, T['muted']
        ).pack(anchor='w', padx=18, pady=(0, 8))
