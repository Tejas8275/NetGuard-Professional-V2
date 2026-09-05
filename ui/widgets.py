"""
Phase 4 Step 3 — UX polish: activity/status feedback, button states,
and Treeview readability, on top of the Phase 3/4 SOC redesign.

Redesigns the shared visual foundation: ttk styling (style()), the label
factory (L()), and the application shell (build() — header, sidebar
container, main content area). Adds two new reusable helpers used by
ui/pages.py: _status_pill() (a bordered live-status readout) and
_enable_tree_hover() (a cosmetic Treeview row-hover highlight).

Scope discipline: only this file changes. All existing public entry
points keep their exact names and call signatures:
  - style(self)
  - L(self, p, x, n=10, b=False, c=None, bg=None, variant=None)
    [variant is additive-only; every existing positional call site is
    unaffected]
  - build(self)
and every widget attribute other files/mixins rely on is preserved
verbatim: self.side, self.content, self.clock, self.status_pill,
self.page_title_label, self.page_subtitle, self.pages, self.nav_rows
(plus self.page_title, self.pages_titles, which build() also sets).

IMPORTANT — theme sharing across modules:
main.py keeps its own module-level `T` global (used by all the methods
still defined there) exactly as before. This module cannot see that
global, so it reads the theme through `ui.styles` instead (`styles.T`),
which is the same dict object main.py's `apply_theme()` also writes to
(`_styles.T = T`) whenever the theme changes. This keeps live theme
switching working correctly across the split files without changing any
theming logic.
"""
import tkinter as tk
from tkinter import ttk

import ui.styles as styles


class GuiWidgetsMixin:
    def style(self):
        """Modern ttk styling for a professional SOC console: dark
        Treeview, flat accent buttons with clear hover/pressed states,
        clean entries/combos, and slim accent scrollbars/progressbars."""
        T = styles.T
        s = ttk.Style(self); s.theme_use('clam')

        # --- Notebook / generic containers -------------------------------
        s.configure('TNotebook', background=T['bg'], borderwidth=0)
        s.configure('TNotebook.Tab', background=T['panel'], foreground=T['muted'],
                    padding=(14, 8), font=('Segoe UI', 9, 'bold'), borderwidth=0)
        s.map('TNotebook.Tab',
              background=[('selected', T['panel2'])],
              foreground=[('selected', T['text'])])

        # --- Buttons -------------------------------------------------------
        s.configure('TButton', background=T['accent'], foreground='#04121c',
                    padding=(15, 10), font=('Segoe UI', 9, 'bold'), borderwidth=0,
                    relief='flat', focuscolor=T['accent'])
        s.map('TButton',
              background=[('disabled', T['panel2']), ('pressed', T['accent_soft']), ('active', T['accent_soft'])],
              foreground=[('disabled', T['muted']), ('pressed', 'white'), ('active', 'white')],
              relief=[('pressed', 'flat'), ('active', 'flat')])

        # --- Entries / combos ------------------------------------------------
        s.configure('TEntry', fieldbackground=T['panel2'], foreground=T['text'],
                    insertcolor=T['accent'], borderwidth=1, relief='flat',
                    bordercolor=T['border'], lightcolor=T['border'], darkcolor=T['border'],
                    padding=(10, 7))
        s.map('TEntry',
              bordercolor=[('focus', T['accent'])],
              lightcolor=[('focus', T['accent'])],
              darkcolor=[('focus', T['accent'])])

        s.configure('TCombobox', fieldbackground=T['panel2'], background=T['panel2'],
                    foreground=T['text'], selectbackground=T['accent'],
                    selectforeground='#04121c', arrowcolor=T['muted'],
                    bordercolor=T['border'], lightcolor=T['border'], darkcolor=T['border'],
                    padding=(10, 7))
        s.map('TCombobox',
              fieldbackground=[('readonly', T['panel2'])],
              bordercolor=[('focus', T['accent'])],
              arrowcolor=[('active', T['accent'])])

        # --- Labels (ttk) ----------------------------------------------------
        s.configure('TLabel', background=T['bg'], foreground=T['text'], font=('Segoe UI', 9))

        # --- Treeview: dark, high-contrast rows with a clear selection -----
        s.configure('Treeview', background=T['panel2'], fieldbackground=T['panel2'],
                    foreground=T['text'], rowheight=36, borderwidth=0, relief='flat',
                    font=('Segoe UI', 9))
        s.configure('Treeview.Heading', background=T['panel'], foreground=T['muted'],
                    font=('Segoe UI', 9, 'bold'), borderwidth=0, relief='flat', padding=(12, 11))
        s.map('Treeview.Heading', background=[('active', T['panel'])], foreground=[('active', T['accent'])])
        s.map('Treeview',
              background=[('selected', T['nav_active'])],
              foreground=[('selected', T['text'])])
        s.layout('Treeview', [('Treeview.treearea', {'sticky': 'nswe'})])
        # Reusable hover-row tag; ui/pages.py toggles this on <Motion> so
        # rows light up under the cursor without touching any data logic.
        self._tree_hover_bg = T['nav_hover']

        # --- Progress bar --------------------------------------------------
        s.configure('TProgressbar', background=T['accent'], troughcolor=T['panel2'],
                    borderwidth=0, thickness=8, lightcolor=T['accent'], darkcolor=T['accent'])

        # --- Scrollbars: slim + accent-tinted thumb -------------------------
        s.configure('Vertical.TScrollbar', background=T['scrollbar'], troughcolor=T['panel2'],
                    arrowcolor=T['muted'], borderwidth=0, relief='flat', width=12)
        s.configure('Horizontal.TScrollbar', background=T['scrollbar'], troughcolor=T['panel2'],
                    arrowcolor=T['muted'], borderwidth=0, relief='flat', width=12)
        s.map('Vertical.TScrollbar', background=[('active', T['accent_soft'])])
        s.map('Horizontal.TScrollbar', background=[('active', T['accent_soft'])])

        # --- Checkbuttons / radio (used incidentally by ttk widgets) --------
        s.configure('TCheckbutton', background=T['panel'], foreground=T['text'])
        s.configure('TRadiobutton', background=T['panel'], foreground=T['text'])

    def L(self, p, x, n=10, b=False, c=None, bg=None, variant=None):
        """Label factory. Signature and default behavior are unchanged —
        existing positional calls (p, x, n, b, c, bg) render exactly as
        before. `variant` is an additive, optional style shortcut for new
        SOC-console UI ('title' | 'subtitle' | 'caption' | 'metric' |
        'mono') that only takes effect when explicitly requested."""
        T = styles.T
        variants = {
            'title':    dict(font=('Segoe UI', 18, 'bold'), fg=T['text']),
            'subtitle': dict(font=('Segoe UI', 9, 'normal'), fg=T['muted']),
            'caption':  dict(font=('Segoe UI', 8, 'normal'), fg=T['muted']),
            'metric':   dict(font=('Segoe UI', 22, 'bold'), fg=T['accent']),
            'mono':     dict(font=('Consolas', 9, 'normal'), fg=T['text']),
        }
        if variant in variants:
            v = variants[variant]
            font = v['font']
            fg = c or v['fg']
        else:
            font = ('Segoe UI', n, 'bold' if b else 'normal')
            fg = c or T['text']
        return tk.Label(p, text=x, font=font, fg=fg, bg=bg or T['bg'])

    def _status_pill(self, p, text, color, icon='●'):
        """Reusable bordered 'pill' container for live status text
        (diagnostics status, scanner status, security score, etc). Makes
        the text main.py already updates live (e.g. 'Scanning… N/254
        hosts') visually stand out as an activity indicator. Returns the
        text Label so callers can assign it to the exact same attribute
        main.py expects (self.diag_status, self.scanner_status, ...).
        Pass icon='' to omit the leading dot — useful when the text
        main.py sets already includes its own bullet character."""
        T = styles.T
        wrap = tk.Frame(p, bg=T['panel3'], highlightthickness=1, highlightbackground=T['border'])
        if icon:
            dot = tk.Label(wrap, text=icon, font=('Segoe UI', 8), fg=color, bg=T['panel3'])
            dot.pack(side='left', padx=(10, 5), pady=6)
        lab = tk.Label(wrap, text=text, font=('Segoe UI', 9, 'bold'), fg=color, bg=T['panel3'])
        lab.pack(side='left', padx=(0, 10) if icon else (12, 12), pady=6)
        return wrap, lab

    def _enable_tree_hover(self, tree):
        """Purely cosmetic row-hover highlight for any ttk.Treeview
        (self.scan_tree, self.security_tree, self.at, self.ht). Uses a
        Treeview `tag` toggled on <Motion>/<Leave> — no data, columns,
        or selection behavior is touched, so existing insert/tag logic
        in main.py (e.g. self.at's CRITICAL/HIGH/MEDIUM/ACK tags) is
        completely unaffected; the hover tag is layered independently."""
        T = styles.T
        tree.tag_configure('_hoverrow', background=T['nav_hover'])
        state = {'row': None}

        def on_motion(e):
            row = tree.identify_row(e.y)
            if row == state['row']:
                return
            if state['row']:
                tags = [t for t in tree.item(state['row'], 'tags') if t != '_hoverrow']
                try: tree.item(state['row'], tags=tags)
                except Exception: pass
            if row:
                tags = list(tree.item(row, 'tags'))
                if '_hoverrow' not in tags:
                    tree.item(row, tags=tags + ['_hoverrow'])
            state['row'] = row

        def on_leave(_):
            if state['row']:
                tags = [t for t in tree.item(state['row'], 'tags') if t != '_hoverrow']
                try: tree.item(state['row'], tags=tags)
                except Exception: pass
            state['row'] = None

        tree.bind('<Motion>', on_motion, add='+')
        tree.bind('<Leave>', on_leave, add='+')

    def _clear_window(self):
        for w in self.winfo_children():
            try:
                w.destroy()
            except Exception:
                pass

    def _center_window(self, w=520, h=650):
        self.update_idletasks(); sw = self.winfo_screenwidth(); sh = self.winfo_screenheight(); self.geometry(f'{w}x{h}+{max(0,(sw-w)//2)}+{max(0,(sh-h)//2)}')

    def _dim(self, hex_color, factor=0.45):
        """Blend a hex color toward black by `factor` (0=no change,
        1=black). Small helper for the header status-dot pulse."""
        hex_color = hex_color.lstrip('#')
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        r = int(r * (1 - factor)); g = int(g * (1 - factor)); b = int(b * (1 - factor))
        return f'#{r:02x}{g:02x}{b:02x}'

    def _pulse_status_dot(self):
        """Subtle self-contained breathing animation on the header status
        dot — purely decorative, doesn't touch self.status_pill (the
        text label) or any attribute main.py reads."""
        T = styles.T
        if not hasattr(self, '_status_dot') or not self._status_dot.winfo_exists():
            return
        state = getattr(self, '_pulse_state', False)
        self._pulse_state = not state
        color = self._dim(T['good'], 0.55) if state else T['good']
        try:
            self._status_dot.itemconfig(self._status_dot_id, fill=color)
        except Exception:
            return
        self.after(700, self._pulse_status_dot)

    def build(self):
        """Application shell: top header, sidebar container, main content
        area. Widget attribute names are unchanged so main.py (show(),
        apply_theme(), tick()) and the dashboard/pages mixins keep working
        exactly as before."""
        T = styles.T

        # ===================== HEADER =====================
        h = tk.Frame(self, bg=T['panel'], height=68, highlightthickness=0)
        h.pack(fill='x'); h.pack_propagate(False)

        # Bottom accent hairline under the header for a "console" edge
        tk.Frame(h, bg=T['border'], height=1).pack(side='bottom', fill='x')

        # --- Brand / application title area ---
        brand = tk.Frame(h, bg=T['panel']); brand.pack(side='left', fill='y', padx=24)
        badge = tk.Frame(brand, bg=T['accent'], width=42, height=42)
        badge.pack(side='left', padx=(0, 14), pady=13); badge.pack_propagate(False)
        tk.Label(badge, text='🛡', font=('Segoe UI', 16, 'bold'), fg='#04121c', bg=T['accent']).pack(expand=True)
        title_col = tk.Frame(brand, bg=T['panel']); title_col.pack(side='left', pady=9)
        row1 = tk.Frame(title_col, bg=T['panel']); row1.pack(anchor='w')
        self.L(row1, 'NETGUARD', 16, True, T['text'], T['panel']).pack(side='left')
        self.L(row1, 'PRO', 16, True, T['accent'], T['panel']).pack(side='left', padx=(5, 0))
        tag_row = tk.Frame(title_col, bg=T['panel']); tag_row.pack(anchor='w', pady=(2, 0))
        dot0 = tk.Label(tag_row, text='●', font=('Segoe UI', 6), fg=T['accent'], bg=T['panel']); dot0.pack(side='left')
        self.L(tag_row, ' PROFESSIONAL SOC CONSOLE', 8, True, T['muted'], T['panel']).pack(side='left')

        # Divider between brand block and console subtitle
        tk.Frame(h, bg=T['border'], width=1).pack(side='left', fill='y', pady=20)
        self.L(h, 'NETWORK & SECURITY OPERATIONS CONSOLE', 8, False, T['muted'], T['panel']).pack(side='left', padx=18)

        # --- Status indicator + clock (right side of header) ---
        status_wrap = tk.Frame(h, bg=T['panel3'], highlightthickness=1, highlightbackground=T['border'])
        status_wrap.pack(side='right', padx=22, pady=16)

        clock_col = tk.Frame(status_wrap, bg=T['panel3']); clock_col.pack(side='right', padx=(4, 14), pady=7)
        self.L(clock_col, 'LOCAL TIME', 6, True, T['muted'], T['panel3']).pack(anchor='e')
        self.clock = self.L(clock_col, '', 10, True, T['text'], T['panel3'])
        self.clock.pack(anchor='e')

        tk.Frame(status_wrap, bg=T['border'], width=1).pack(side='right', fill='y', pady=8)

        status_col = tk.Frame(status_wrap, bg=T['panel3']); status_col.pack(side='right', padx=14, pady=7)
        self._status_dot = tk.Canvas(status_col, width=10, height=10, bg=T['panel3'], highlightthickness=0)
        self._status_dot.pack(side='left', padx=(0, 6))
        self._status_dot_id = self._status_dot.create_oval(1, 1, 9, 9, fill=T['good'], outline='')
        self.status_pill = self.L(status_col, 'SYSTEM ONLINE', 8, True, T['good'], T['panel3'])
        self.status_pill.pack(side='left')

        self.tick()
        self._pulse_status_dot()

        # ===================== BODY =====================
        body = tk.Frame(self, bg=T['bg']); body.pack(fill='both', expand=True)

        # --- Sidebar container ---
        self.side = tk.Frame(body, bg=T['sidebar'], width=246, highlightthickness=0)
        self.side.pack(side='left', fill='y'); self.side.pack_propagate(False)
        tk.Frame(body, bg=T['border'], width=1).pack(side='left', fill='y')

        # --- Main content area ---
        self.content = tk.Frame(body, bg=T['bg']); self.content.pack(side='left', fill='both', expand=True)

        self.pages = {}; self.nav_rows = {}
        groups = [('', ['Dashboard']), ('MONITOR', ['Live Monitor']), ('DIAGNOSTICS', ['Diagnostics', 'Network Scanner', 'Network Map']), ('SECURITY', ['Security Center', 'System Monitor']), ('RECORDS', ['Alerts', 'History', 'Reports']), ('SYSTEM', ['Settings'])]
        icons = {'Dashboard': '⌂', 'Live Monitor': '◉', 'Diagnostics': '⌁', 'Network Scanner': '⌕', 'Network Map': '⌖', 'Security Center': '◆', 'System Monitor': '▣', 'Alerts': '!', 'History': '◷', 'Reports': '▤', 'Settings': '⚙'}
        for label, names in groups:
            if label:
                self.L(self.side, label, 8, True, T['muted'], T['sidebar']).pack(anchor='w', padx=22, pady=(16, 6))
            else:
                tk.Frame(self.side, bg=T['sidebar'], height=12).pack(fill='x')
            for n in names: self.make_nav_button(n, icons[n])

        tk.Frame(self.side, bg=T['border'], height=1).pack(side='bottom', fill='x', padx=22, pady=(0, 14))
        status_row = tk.Frame(self.side, bg=T['sidebar']); status_row.pack(side='bottom', fill='x', padx=22, pady=(0, 6))
        sys_dot = tk.Canvas(status_row, width=8, height=8, bg=T['sidebar'], highlightthickness=0); sys_dot.pack(side='left', padx=(0, 8))
        sys_dot.create_oval(1, 1, 7, 7, fill=T['good'], outline='')
        self.L(status_row, 'SYSTEM ONLINE', 8, True, T['good'], T['sidebar']).pack(side='left')

        self.pages_titles = {n: n.upper() for _, ns in groups for n in ns}

        # --- Page title bar (top of content area) ---
        self.page_title = tk.Frame(self.content, bg=T['bg'], height=72); self.page_title.pack(fill='x'); self.page_title.pack_propagate(False)
        title_inner = tk.Frame(self.page_title, bg=T['bg']); title_inner.pack(anchor='w', padx=28, pady=(15, 0), fill='x')
        self.page_title_label = self.L(title_inner, 'DASHBOARD', 20, True, T['text'], T['bg'])
        self.page_title_label.pack(anchor='w')
        self.page_subtitle = self.L(self.page_title, 'Network & security operations', 8, False, T['muted'], T['bg'])
        self.page_subtitle.pack(anchor='w', padx=29)
        tk.Frame(self.page_title, bg=T['border'], height=1).pack(side='bottom', fill='x')

        # --- Page host (actual scrollable/page-swap area) ---
        host = tk.Frame(self.content, bg=T['bg']); host.pack(fill='both', expand=True); self.content = host
        for n in self.pages_titles:
            f = tk.Frame(self.content, bg=T['bg']); self.pages[n] = f

        self.dashboard(); self.diagnostics(); self.network_scanner_page(); self.monitor_page(); self.map_page(); self.security_page(); self.system_page(); self.alerts(); self.history(); self.reports(); self.settings(); self.show('Dashboard')
