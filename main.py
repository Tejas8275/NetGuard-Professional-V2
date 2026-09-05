import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import socket, subprocess, platform, threading, datetime, json, re, os, time, shutil, csv, urllib.request, random
try:
    import psutil
except ImportError:
    psutil = None
from pathlib import Path
try:
 from mac_vendor_lookup import MacLookup
except ImportError:
 MacLookup=None

# --- Phase 1 refactor: pure logic moved to core/, pure style data to ui/ ---
# Behavior is unchanged; these are the same objects/functions, just relocated
# and imported. See REFACTOR_PLAN.md for details.
from ui.styles import THEMES, T, F_BRAND, F_PAGE_TITLE, F_SECTION_LABEL, F_NAV, F_CLOCK
import ui.styles as _styles  # used by apply_theme() to update the shared global

from core.network_core import (
    cmd, ping, latency, loss, info, dnslookup, port, trace, conns,
    internet_check, https_latency, is_private_scan_prefix, health_assessment,
)
from core.security import (
    calculate_risk, scan_ports as _core_scan_ports,
    security_findings_for_ports,
)
from core.scanner import scan_profile, scan_subnet
from core.alerts import (
    acknowledge_alert_rows, filtered_alert_rows, normalize_alert_rows, remove_acknowledged_alert_rows,
)
from core.health_settings import DEFAULT_HEALTH_THRESHOLDS, normalize_health_thresholds
from core.retention import DEFAULT_RETENTION_LIMITS, normalize_retention_limits, retain_latest
from core.baselines import normalize_baseline_name, normalize_baselines, save_baseline
from core.scan_comparison import (
    compare_scans, comparison_report_lines, comparison_statuses,
    comparison_summary, device_identity,
)
from core.logging_config import get_logger
from core.version import APP_VERSION
from core.auth import (
    PASSWORD_SCRYPT_N, PASSWORD_SCRYPT_R, PASSWORD_SCRYPT_P,
    password_hash as _core_password_hash, verify_password as _core_verify_password,
    valid_password as _core_valid_password, can_perform as _core_can_perform,
)
from core.storage import (
    load_users as _core_load_users, save_users as _core_save_users,
    load_app_state as _core_load_app_state, save_app_state as _core_save_app_state,
)

MAC_VENDORS={
 '00:1A:11':'Google','00:1B:63':'Apple','00:1C:B3':'Apple','00:1E:C2':'Apple',
 '00:50:56':'VMware','00:0C:29':'VMware','08:00:27':'Oracle VirtualBox',
 '00:15:5D':'Microsoft Hyper-V','B8:27:EB':'Raspberry Pi','DC:A6:32':'Raspberry Pi',
 '00:1C:42':'RouterBOARD','E0:63:DA':'Ubiquiti','FC:EC:DA':'Ubiquiti'
}

from ui.widgets import GuiWidgetsMixin
from ui.dashboard import DashboardMixin
from ui.pages import PagesMixin

LOGGER=get_logger()

class App(GuiWidgetsMixin, DashboardMixin, PagesMixin, tk.Tk):
 def __init__(self):
  super().__init__();self.geometry('1280x820');self.minsize(1050,700);self.configure(bg=T['bg']);self.hist=[];self.alert_rows=[];self.health_thresholds=dict(DEFAULT_HEALTH_THRESHOLDS);self.retention_limits=dict(DEFAULT_RETENTION_LIMITS);self.scan_baselines={};self.last_baseline_comparison={'new':[],'gone':[],'changed':[]};self.previous_scan_results=[];self.last_scan_comparison={'new':[],'gone':[],'changed':[]};self.monitor=False;self.points=[];self.scan_cancel=threading.Event();self.scan_running=False;self.system_running=False;self.mac_lookup=None;self.known_devices=set();self.security_findings=[];self.security_score=100;self.active_diagnostics=set()
  try:self.iconbitmap(default=str(Path(__file__).with_name('netguard.ico')))
  except tk.TclError:pass
  self.style();self.protocol('WM_DELETE_WINDOW',self.on_close);self.show_login()

 def _load_users(self):
  """Load locally registered users. Passwords are never stored in plaintext.
  Delegates to core.storage (Phase 1 relocation; logic unchanged)."""
  return _core_load_users()

 def _save_users(self,users):
  """Delegates to core.storage (Phase 1 relocation; logic unchanged)."""
  _core_save_users(users)

 def _password_hash(self,password,salt=None):
  """Delegates to core.auth (Phase 1 relocation; logic unchanged)."""
  return _core_password_hash(password,salt)

 def _valid_password(self,password):
  """Delegates to core.auth (Phase 1 relocation; logic unchanged)."""
  return _core_valid_password(password)

 def _authenticate(self,username,password):
  username=username.strip()
  users=self._load_users()
  rec=users.get(username.lower())
  if not isinstance(rec,dict): return None
  if _core_verify_password(password,rec.get('salt'),rec.get('password_hash')):
   return {'username':rec.get('username',username),'role':rec.get('role','Viewer'),'created_at':rec.get('created_at','')}
  return None

 def _require_permission(self, action):
  """Guard active network operations using the authenticated local role."""
  role=getattr(self,'current_user',{}).get('role','Viewer')
  if _core_can_perform(role,action): return True
  action_name={'network_scan':'network discovery scans','security_scan':'Security Center checks'}.get(action,'this action')
  messagebox.showerror('Administrator permission required',f'{action_name.capitalize()} are restricted to Administrator accounts. Current role: {role}.')
  return False

 def _finish_login(self,d,user):
  self.current_user=user
  self.unbind('<Return>')
  self._clear_window(); self.build(); self.load_state(); self.deiconify(); self.after(300,self.refresh)

 def _auth_header(self, title, subtitle):
  h=tk.Frame(self,bg=T['panel'],height=66);h.pack(fill='x');h.pack_propagate(False)
  brand=tk.Frame(h,bg=T['panel']);brand.pack(side='left',fill='y',padx=20)
  self.L(brand,'🛡',20,True,T['accent'],T['panel']).pack(side='left',padx=(0,8))
  self.L(brand,'NETGUARD PRO',15,True,T['text'],T['panel']).pack(side='left')
  self.L(brand,'  PROFESSIONAL SOC',8,True,T['accent'],T['panel']).pack(side='left',pady=(5,0))
  self.L(h,'NETWORK & SECURITY OPERATIONS CONSOLE',8,False,T['muted'],T['panel']).pack(side='left',pady=(5,0))
  self.L(h,'● AUTHENTICATION',8,True,T['good'],T['panel']).pack(side='right',padx=18)
  self.L(h,title,9,True,T['muted'],T['panel']).pack(side='right',padx=10)

 def _auth_footer(self):
  f=tk.Frame(self,bg=T['panel'],height=34);f.pack(side='bottom',fill='x');f.pack_propagate(False)
  self.L(f,'NETGUARD PRO  •  SECURE LOCAL AUTHENTICATION',8,False,T['muted'],T['panel']).pack(side='left',padx=18)
  self.L(f,'Protected session',8,True,T['good'],T['panel']).pack(side='right',padx=18)

 def show_login(self):
  self.unbind('<Return>'); self._clear_window(); self.title('NetGuard Pro — Sign in'); self.configure(bg=T['bg']); self.resizable(True,True); self.minsize(1050,700); self.geometry('1280x820'); self.deiconify()

  # ============================================================
  # Premium SOC login layout + animations. Everything below is
  # scoped to this method (or to small helper closures inside it)
  # so nothing outside show_login()/login-page widgets is touched.
  # show_signup()/_auth_header()/_auth_footer()/_authenticate()/
  # _password_hash()/_valid_password() are all untouched.
  #
  # Animation lifecycle: every self.after() call in this screen is
  # routed through schedule() below and tracked in after_ids, so
  # stop_login_animations() can cancel all of them the instant the
  # person logs in or navigates to signup — no stray callbacks keep
  # running (or erroring against destroyed widgets) once we leave
  # this screen.
  #
  # Visual-polish pass (final): every SOC info panel now shares one
  # builder (make_panel) so borders, accent bars, and padding are
  # pixel-identical across panels; the login card gets a soft accent
  # halo + slightly smaller footprint so it (and the left column's
  # panel stack) comfortably fit inside the 1050x700 minsize without
  # clipping or overlapping; buttons/inputs get their own scoped ttk
  # styles ('Login.*') for hover/pressed/focus feedback, so nothing
  # in ui/widgets.py's shared TButton/TEntry styles is touched and
  # every other screen keeps its exact current look.
  # ============================================================
  login_state = {'active': True}
  after_ids = []

  def schedule(delay, fn):
   if not login_state['active']:
    return None
   try:
    aid = self.after(delay, fn)
   except Exception:
    return None
   after_ids.append(aid)
   return aid

  def stop_login_animations():
   login_state['active'] = False
   for aid in after_ids:
    try: self.after_cancel(aid)
    except Exception: pass
   after_ids.clear()

  # ---- scoped ttk styles for this screen only ------------------------
  # New style *names* ('Login.TEntry', 'Login.TButton', 'LoginGhost.TButton')
  # so the shared 'TEntry'/'TButton' styles other screens use (defined in
  # ui/widgets.py) are left completely untouched.
  accent_hover = self._lerp_hex(T['accent'], '#ffffff', 0.16)
  login_style = ttk.Style(self)
  login_style.configure('Login.TEntry', fieldbackground=T['panel2'], foreground=T['text'],
                         insertcolor=T['accent'], borderwidth=1, relief='flat',
                         bordercolor=T['border'], lightcolor=T['border'], darkcolor=T['border'],
                         padding=(10, 8))
  login_style.map('Login.TEntry',
                   bordercolor=[('focus', T['accent'])],
                   lightcolor=[('focus', T['accent'])],
                   darkcolor=[('focus', T['accent'])])
  login_style.configure('Login.TButton', background=T['accent'], foreground='#04121c',
                         padding=(13, 10), font=('Segoe UI', 10, 'bold'), borderwidth=0,
                         relief='flat', focuscolor=T['accent'])
  login_style.map('Login.TButton',
                   background=[('disabled', T['panel2']), ('pressed', T['accent_soft']), ('active', accent_hover)],
                   foreground=[('disabled', T['muted']), ('pressed', '#04121c'), ('active', '#04121c')],
                   relief=[('pressed', 'flat'), ('active', 'flat')])
  login_style.configure('LoginGhost.TButton', background=T['panel2'], foreground=T['text'],
                         padding=(13, 9), font=('Segoe UI', 9, 'bold'), borderwidth=1,
                         relief='flat', focuscolor=T['accent'],
                         bordercolor=T['border'], lightcolor=T['border'], darkcolor=T['border'])
  login_style.map('LoginGhost.TButton',
                   background=[('pressed', T['nav_hover']), ('active', T['nav_hover'])],
                   foreground=[('pressed', T['text']), ('active', T['text'])],
                   bordercolor=[('pressed', T['accent']), ('active', T['accent'])],
                   lightcolor=[('pressed', T['accent']), ('active', T['accent'])],
                   darkcolor=[('pressed', T['accent']), ('active', T['accent'])])

  root = tk.Frame(self, bg=T['bg']); root.pack(fill='both', expand=True)

  # ---------------- LEFT: branding / security status ----------------
  left = tk.Frame(root, bg=T['panel3']); left.pack(side='left', fill='both', expand=True)

  # ---- 1. Animated cyber network background --------------------
  # Slow-drifting nodes on a Canvas, connected by lines when close
  # together — a classic "network map" motif for the branding side.
  bgcanvas = tk.Canvas(left, bg=T['panel3'], highlightthickness=0)
  bgcanvas.place(relx=0, rely=0, relwidth=1, relheight=1)
  nodes = []
  NODE_COUNT = 22
  LINK_DIST = 150

  def init_nodes():
   w = max(bgcanvas.winfo_width(), 700); h = max(bgcanvas.winfo_height(), 700)
   nodes.clear()
   for _ in range(NODE_COUNT):
    nodes.append({'x': random.uniform(0, w), 'y': random.uniform(0, h),
                  'vx': random.uniform(-0.25, 0.25), 'vy': random.uniform(-0.2, 0.2)})

  def animate_network():
   if not login_state['active'] or not bgcanvas.winfo_exists():
    return
   w = bgcanvas.winfo_width(); h = bgcanvas.winfo_height()
   if w < 10 or h < 10:
    schedule(80, animate_network); return
   if not nodes:
    init_nodes()
   bgcanvas.delete('all')
   step = 40
   for gx in range(0, w, step):
    for gy in range(0, h, step):
     bgcanvas.create_oval(gx, gy, gx + 1, gy + 1, fill=T['border'], outline='')
   for n in nodes:
    n['x'] += n['vx']; n['y'] += n['vy']
    if n['x'] < 0 or n['x'] > w: n['vx'] *= -1; n['x'] = max(0, min(w, n['x']))
    if n['y'] < 0 or n['y'] > h: n['vy'] *= -1; n['y'] = max(0, min(h, n['y']))
   for i in range(len(nodes)):
    for j in range(i + 1, len(nodes)):
     a, b = nodes[i], nodes[j]
     dist = ((a['x'] - b['x']) ** 2 + (a['y'] - b['y']) ** 2) ** 0.5
     if dist < LINK_DIST:
      color = T['accent'] if dist < LINK_DIST * 0.4 else T['border']
      bgcanvas.create_line(a['x'], a['y'], b['x'], b['y'], fill=color, width=1)
   for n in nodes:
    bgcanvas.create_oval(n['x'] - 2, n['y'] - 2, n['x'] + 2, n['y'] + 2, fill=T['accent'], outline='')
   schedule(60, animate_network)

  bgcanvas.bind('<Configure>', lambda _e: (nodes.clear(), animate_network()))
  schedule(50, animate_network)

  left_content = tk.Frame(left, bg=T['panel3']); left_content.place(relx=0.5, rely=0.5, anchor='center')

  # ---- shared panel builder: every bordered SOC info panel below ----
  # (auth status / threats / system status / AI / system info) is built
  # through this one helper so borders, accent-bar treatment and inner
  # padding are identical across all of them (consistent card sizing),
  # and so the vertical gap between panels is one predictable constant
  # (PANEL_GAP) that's easy to trim for smaller windows.
  PANEL_GAP = 9

  def make_panel(accent_color, top_pad=PANEL_GAP):
   box = tk.Frame(left_content, bg=T['panel'], highlightthickness=1, highlightbackground=T['border'])
   box.pack(fill='x', pady=(top_pad, 0))
   bar = tk.Frame(box, bg=T['panel']); bar.pack(side='left', fill='y')
   tk.Frame(bar, bg=accent_color, width=3).pack(side='left', fill='y')
   tk.Frame(bar, bg=self._lerp_hex(T['panel'], accent_color, 0.35), width=1).pack(side='left', fill='y')
   panel_inner = tk.Frame(box, bg=T['panel']); panel_inner.pack(side='left', fill='both', expand=True, padx=13, pady=8)
   return panel_inner

  self.L(left_content, '🛡', 26, True, T['accent'], T['panel3']).pack(pady=(0, 3))
  self.L(left_content, 'NETGUARD PRO', 28, True, T['text'], T['panel3']).pack()
  self.L(left_content, 'SECURE OPERATIONS CONSOLE', 10, True, T['accent'], T['panel3']).pack(pady=(4, 18))

  self.L(left_content, 'Enterprise-grade network monitoring, threat\ndetection and incident response — unified in a\nsingle professional security operations console.',
         10, False, T['muted'], T['panel3']).pack(pady=(0, 16))

  for line in ('◉  Real-time network health monitoring', '◆  Automated vulnerability & risk scoring', '⌕  Live device discovery and topology mapping', '!  Centralized alerting and incident history'):
   self.L(left_content, line, 10, True, T['text'], T['panel3']).pack(anchor='w', pady=2)

  # ---- 4. Security terminal boot text (line-by-line) --------------
  term = tk.Text(left_content, height=5, width=46, bg=T['panel'], fg=T['good'],
                 font=('Consolas', 9), relief='flat', bd=0, highlightthickness=1,
                 highlightbackground=T['border'], state='disabled', padx=10, pady=7)
  term.pack(fill='x', pady=(14, 9))
  boot_lines = [
   '> Initializing security engine...',
   '> Loading threat database...',
   '> Checking encryption...',
   '> Firewall active...',
   '> Authentication ready',
  ]

  def boot_type(i=0):
   if not login_state['active'] or not term.winfo_exists():
    return
   if i < len(boot_lines):
    term.config(state='normal')
    term.insert('end', boot_lines[i] + '\n')
    term.see('end')
    term.config(state='disabled')
    schedule(420, lambda: boot_type(i + 1))
   else:
    schedule(600, ready_cycle)
  schedule(500, boot_type)

  # ---- 5. Secure status animation (cycling READY dots) ------------
  ready_lbl = self.L(left_content, '🔒 Secure Authentication System', 9, True, T['good'], T['panel3'])
  ready_lbl.pack(anchor='w')

  def ready_cycle(n=0):
   if not login_state['active'] or not ready_lbl.winfo_exists():
    return
   dots = '.' * (n % 4)
   ready_lbl.config(text=f'🔒 Secure Authentication System — READY{dots}')
   schedule(450, lambda: ready_cycle(n + 1))

  status_inner = make_panel(T['good'], top_pad=11)
  statusdot = tk.Canvas(status_inner, width=8, height=8, bg=T['panel'], highlightthickness=0); statusdot.pack(side='left', padx=(0, 8))
  statusdot_id = statusdot.create_oval(1, 1, 7, 7, fill=T['good'], outline='')
  self.L(status_inner, 'AUTHENTICATION SERVICES', 8, True, T['text'], T['panel']).pack(side='left')
  self.L(status_inner, 'READY', 8, True, T['good'], T['panel']).pack(side='right')

  def pulse_status_dot(on=True):
   if not login_state['active'] or not statusdot.winfo_exists():
    return
   color = T['good'] if on else self._dim(T['good'], 0.55)
   try: statusdot.itemconfig(statusdot_id, fill=color)
   except Exception: return
   schedule(700, lambda: pulse_status_dot(not on))
  schedule(300, pulse_status_dot)

  # ---- 6. Threats-blocked-today counter (animated 0 -> 1248) ------
  threat_inner = make_panel(T['accent'])
  self.L(threat_inner, 'THREATS BLOCKED TODAY', 8, True, T['muted'], T['panel']).pack(side='left')
  threat_val = self.L(threat_inner, '0', 16, True, T['accent'], T['panel']); threat_val.pack(side='right')

  def animate_threat_counter(n=0, target=1248, steps=36):
   if not login_state['active'] or not threat_val.winfo_exists():
    return
   t = n / steps
   eased = 1 - (1 - t) ** 3
   val = target if n >= steps else int(target * eased)
   try: threat_val.config(text=f'{val:,}')
   except Exception: return
   if n < steps:
    schedule(30, lambda: animate_threat_counter(n + 1, target, steps))
  schedule(650, animate_threat_counter)

  # ---- 7. System status panel ---------------------------------------
  sys_status_inner = make_panel(T['good'])
  for s_label, s_value in (('FIREWALL', 'ACTIVE'), ('ENCRYPTION', 'ENABLED'), ('MONITORING', 'ONLINE'), ('AUTHENTICATION', 'READY')):
   s_item = tk.Frame(sys_status_inner, bg=T['panel']); s_item.pack(side='left', expand=True, fill='x')
   self.L(s_item, s_label, 7, True, T['muted'], T['panel']).pack(anchor='w')
   self.L(s_item, s_value, 8, True, T['good'], T['panel']).pack(anchor='w', pady=(1, 0))

  # ---- 8. NetGuard AI panel (subtle typing animation) ----------------
  ai_inner = make_panel(T['accent'])
  ai_header = tk.Frame(ai_inner, bg=T['panel']); ai_header.pack(fill='x', anchor='w')
  self.L(ai_header, '🤖', 9, False, T['accent'], T['panel']).pack(side='left', padx=(0, 6))
  self.L(ai_header, 'NETGUARD AI', 8, True, T['text'], T['panel']).pack(side='left')
  ai_text = self.L(ai_inner, '', 8, False, T['muted'], T['panel']); ai_text.configure(justify='left', anchor='w'); ai_text.pack(anchor='w', fill='x', pady=(5, 0))

  ai_lines = ['System analysis complete.', 'No active threats detected.']

  def ai_type(line_i=0, char_i=0, shown=''):
   if not login_state['active'] or not ai_text.winfo_exists():
    return
   if line_i >= len(ai_lines):
    return
   line = ai_lines[line_i]
   if char_i <= len(line):
    try: ai_text.config(text=shown + line[:char_i])
    except Exception: return
    schedule(28, lambda: ai_type(line_i, char_i + 1, shown))
   else:
    schedule(450, lambda: ai_type(line_i + 1, 0, shown + line + '\n'))
  schedule(1300, ai_type)

  # ---- 9. System information panel -----------------------------------
  # Rebuilt on the same 3-column layout as the System Status panel
  # above it (label-over-value, identical fonts/padding) so the two
  # read as one consistent family instead of two different treatments.
  sysinfo_inner = make_panel(T['border'])
  for i_label, i_value, i_color in (('VERSION', f'NETGUARD PRO v{APP_VERSION}', T['text']), ('SECURITY ENGINE', 'ONLINE', T['good']), ('CONNECTION', 'ENCRYPTED', T['good'])):
   i_item = tk.Frame(sysinfo_inner, bg=T['panel']); i_item.pack(side='left', expand=True, fill='x')
   self.L(i_item, i_label, 7, True, T['muted'], T['panel']).pack(anchor='w')
   self.L(i_item, i_value, 8, True, i_color, T['panel']).pack(anchor='w', pady=(1, 0))

  # ---------------- RIGHT: centered glass login card ----------------
  right = tk.Frame(root, bg=T['bg'], width=480); right.pack(side='right', fill='y'); right.pack_propagate(False)
  card_outer = tk.Frame(right, bg=T['bg']); card_outer.place(relx=0.5, rely=0.5, anchor='center')

  # Soft accent "glow" halo behind the card: a slightly larger frame in
  # a dim accent tint peeking out 2px around the card on every side —
  # the closest a plain Tk frame can get to a blurred neon glow.
  card_halo = tk.Frame(card_outer, bg=self._lerp_hex(T['bg'], T['accent'], 0.16)); card_halo.pack()

  # "Glass" panel: a bordered, slightly-elevated surface with a thin
  # accent-colored outline standing in for rounded/translucent glass
  # (plain Tk frames can't do true rounded corners or blur, so this
  # uses layered borders + a top accent strip for the same visual cue
  # used elsewhere in the app's card system).
  card = tk.Frame(card_halo, bg=T['panel'], width=380, height=560, highlightthickness=1, highlightbackground=T['bg'])
  card.pack(padx=2, pady=2); card.pack_propagate(False)
  accent_strip = tk.Frame(card, bg=T['bg'], height=3); accent_strip.pack(fill='x')

  inner = tk.Frame(card, bg=T['panel']); inner.pack(fill='both', expand=True, padx=34, pady=26)

  # ---- 2. Shield logo pulse/glow -----------------------------------
  shield_wrap = tk.Frame(inner, bg=T['panel'], width=68, height=68); shield_wrap.pack(pady=(0, 4)); shield_wrap.pack_propagate(False)
  glow = tk.Canvas(shield_wrap, width=68, height=68, bg=T['panel'], highlightthickness=0); glow.place(x=0, y=0)
  shield_lbl = tk.Label(shield_wrap, text='🛡', font=('Segoe UI', 25, 'bold'), fg=T['accent'], bg=T['panel']); shield_lbl.place(relx=0.5, rely=0.5, anchor='center')

  def pulse_shield(state={'v': 0.0, 'dir': 1}):
   if not login_state['active'] or not glow.winfo_exists():
    return
   state['v'] += 0.05 * state['dir']
   if state['v'] >= 1: state['v'] = 1.0; state['dir'] = -1
   if state['v'] <= 0: state['v'] = 0.0; state['dir'] = 1
   glow.delete('all')
   r = 21 + state['v'] * 9
   ring = self._lerp_hex(T['panel'], T['accent'], 0.25 + 0.35 * state['v'])
   cx = cy = 34
   glow.create_oval(cx - r, cy - r, cx + r, cy + r, outline=ring, width=2)
   glow.create_oval(cx - r + 7, cy - r + 7, cx + r - 7, cy + r - 7, outline=ring, width=1)
   shield_lbl.config(fg=self._lerp_hex(T['accent'], T['text'], 0.3 * state['v']))
   schedule(55, pulse_shield)
  schedule(60, pulse_shield)

  self.L(inner, 'NETGUARD PRO', 17, True, T['text'], T['panel']).pack(pady=(4, 2))
  self.L(inner, 'Secure Authentication', 9, True, T['muted'], T['panel']).pack(pady=(0, 22))

  # ---- Input fields: accent glow ring on focus ------------------------
  # Each entry sits inside a thin wrapper frame; on focus the wrapper's
  # highlight border switches from the hairline border color to a 2px
  # accent ring (and back on blur), layered on top of the existing
  # Login.TEntry focus border color for a clearer "active field" cue.
  def focus_glow(wrap):
   def on_in(_e=None):
    try: wrap.configure(highlightbackground=T['accent'], highlightcolor=T['accent'], highlightthickness=2)
    except Exception: pass
   def on_out(_e=None):
    try: wrap.configure(highlightbackground=T['border'], highlightcolor=T['border'], highlightthickness=1)
    except Exception: pass
   return on_in, on_out

  self.L(inner, 'U S E R N A M E', 8, True, T['muted'], T['panel']).pack(anchor='w')
  u_wrap = tk.Frame(inner, bg=T['panel'], highlightthickness=1, highlightbackground=T['border']); u_wrap.pack(fill='x', pady=(6, 14))
  u=tk.StringVar(value='admin'); ue=ttk.Entry(u_wrap,textvariable=u,style='Login.TEntry'); ue.pack(fill='x',ipady=5,padx=1,pady=1)
  u_in, u_out = focus_glow(u_wrap); ue.bind('<FocusIn>', u_in); ue.bind('<FocusOut>', u_out)

  self.L(inner, 'P A S S W O R D', 8, True, T['muted'], T['panel']).pack(anchor='w')
  pw=tk.StringVar(); prow=tk.Frame(inner,bg=T['panel']); prow.pack(fill='x',pady=(6,9))
  pw_wrap = tk.Frame(prow, bg=T['panel'], highlightthickness=1, highlightbackground=T['border']); pw_wrap.pack(side='left', fill='x', expand=True)
  e=ttk.Entry(pw_wrap,textvariable=pw,show='•',style='Login.TEntry'); e.pack(fill='x',ipady=5,padx=1,pady=1)
  pw_in, pw_out = focus_glow(pw_wrap); e.bind('<FocusIn>', pw_in); e.bind('<FocusOut>', pw_out)
  show_state={'visible':False}
  def toggle_password():
   show_state['visible']=not show_state['visible']; e.configure(show='' if show_state['visible'] else '•'); eye.config(text='HIDE' if show_state['visible'] else 'SHOW')
  eye=tk.Button(prow,text='SHOW',command=toggle_password,bg=T['panel2'],fg=T['muted'],activebackground=T['nav_hover'],activeforeground=T['accent'],relief='flat',bd=0,font=('Segoe UI',8,'bold'),padx=9); eye.pack(side='right',padx=(7,0))

  msg=self.L(inner,'Sign in to continue.',8,False,T['muted'],T['panel']); msg.pack(anchor='w',pady=(0,16))

  def submit():
   user=self._authenticate(u.get(),pw.get())
   if user:
    stop_login_animations()
    self._finish_login(self,user)
   else:
    msg.config(text='Invalid username or password.',fg=T['bad']); pw.set(''); e.focus_set()

  def go_signup():
   stop_login_animations()
   self.show_signup()

  ttk.Button(inner,text='LOGIN',command=submit,style='Login.TButton').pack(fill='x',pady=(0,10),ipady=6)
  ttk.Button(inner,text='NEW USER  •  CREATE ACCOUNT',command=go_signup,style='LoginGhost.TButton').pack(fill='x',ipady=5)

  divider = tk.Frame(inner, bg=T['border'], height=1); divider.pack(fill='x', pady=(20, 11))
  lock_row = tk.Frame(inner, bg=T['panel']); lock_row.pack()
  self.L(lock_row, '🔒', 9, False, T['good'], T['panel']).pack(side='left', padx=(0, 6))
  self.L(lock_row, 'Encrypted Connection', 8, True, T['good'], T['panel']).pack(side='left')

  # ---- 3. Login card entrance animation ----------------------------
  # Background/left side is already animating; the card itself fades
  # its halo, border and top strip in from the page background color
  # to the accent color as it settles into its centered resting spot,
  # giving a "materializing" entrance instead of popping in instantly.
  # (The card no longer slides between two different rely fractions —
  # it settles at a single, always-on-screen centered position so it
  # can never end up partially off-window at the 700px minimum height.)
  def animate_card_entrance(step=0, steps=16):
   if not login_state['active'] or not card.winfo_exists():
    return
   t = step / steps
   eased = 1 - (1 - t) ** 3
   try:
    fade_border = self._lerp_hex(T['bg'], T['accent'], eased)
    fade_halo = self._lerp_hex(T['bg'], T['accent'], 0.16 * eased)
    card.configure(highlightbackground=fade_border)
    accent_strip.configure(bg=fade_border)
    card_halo.configure(bg=fade_halo)
   except Exception:
    return
   if step < steps:
    schedule(16, lambda: animate_card_entrance(step + 1, steps))
   else:
    card.configure(highlightbackground=T['accent']); accent_strip.configure(bg=T['accent'])
    card_halo.configure(bg=self._lerp_hex(T['bg'], T['accent'], 0.16))
  schedule(120, animate_card_entrance)

  self.bind('<Return>',lambda _e:submit()); ue.focus_set()

 def show_signup(self):
  self.unbind('<Return>'); self._clear_window(); self.title('NetGuard Pro — Create Account'); self.configure(bg=T['bg']); self.resizable(True,True); self.minsize(1050,700); self.geometry('1280x820'); self.deiconify()
  self._auth_header('CREATE ACCOUNT','Local User Registration')
  body=tk.Frame(self,bg=T['bg']); body.pack(fill='both',expand=True,padx=28,pady=24)
  left=tk.Frame(body,bg=T['panel'],highlightthickness=1,highlightbackground=T['border']); left.pack(side='left',fill='both',expand=True,padx=(0,12))
  self.L(left,'CREATE YOUR ACCOUNT',24,True,T['text'],T['panel']).pack(anchor='w',padx=40,pady=(48,6))
  self.L(left,'Join the NetGuard Pro security operations console.',10,False,T['muted'],T['panel']).pack(anchor='w',padx=40)
  self.L(left,'PASSWORD REQUIREMENTS',10,True,T['accent'],T['panel']).pack(anchor='w',padx=40,pady=(42,12))
  for text in ('✓ Minimum 12 characters','✓ At least one uppercase letter','✓ At least one lowercase letter','✓ At least one number and symbol','✓ Passwords are stored only as secure hashes'):
   self.L(left,text,10,False,T['muted'] if text.startswith('✓') else T['text'],T['panel']).pack(anchor='w',padx=40,pady=4)
  info=tk.Frame(left,bg=T['panel2'],highlightthickness=1,highlightbackground=T['border']); info.pack(side='bottom',fill='x',padx=40,pady=40)
  self.L(info,'ROLES',9,True,T['text'],T['panel2']).pack(anchor='w',padx=14,pady=(12,3))
  self.L(info,'Admin  •  Analyst  •  Viewer',9,False,T['muted'],T['panel2']).pack(anchor='w',padx=14,pady=(0,12))
  right=tk.Frame(body,bg=T['panel'],width=500,highlightthickness=1,highlightbackground=T['border']); right.pack(side='right',fill='y'); right.pack_propagate(False)
  self.L(right,'ACCOUNT DETAILS',18,True,T['text'],T['panel']).pack(anchor='w',padx=38,pady=(40,22))
  self.L(right,'Username',9,True,T['muted'],T['panel']).pack(anchor='w',padx=38); uv=tk.StringVar(); ue=ttk.Entry(right,textvariable=uv); ue.pack(fill='x',padx=38,pady=(6,14),ipady=4)
  self.L(right,'Password',9,True,T['muted'],T['panel']).pack(anchor='w',padx=38); pv=tk.StringVar(); pe=ttk.Entry(right,textvariable=pv,show='•'); pe.pack(fill='x',padx=38,pady=(6,14),ipady=4)
  self.L(right,'Confirm Password',9,True,T['muted'],T['panel']).pack(anchor='w',padx=38); cv=tk.StringVar(); ce=ttk.Entry(right,textvariable=cv,show='•'); ce.pack(fill='x',padx=38,pady=(6,14),ipady=4)
  self.L(right,'Role',9,True,T['muted'],T['panel']).pack(anchor='w',padx=38); role=tk.StringVar(value='Admin'); cb=ttk.Combobox(right,textvariable=role,values=['Admin'],state='disabled'); cb.pack(fill='x',padx=38,pady=(6,14),ipady=4)
  status=self.L(right,'',8,False,T['muted'],T['panel']); status.pack(anchor='w',padx=38,pady=(0,10))
  def create():
   username=uv.get().strip(); password=pv.get(); confirm=cv.get(); users=self._load_users()
   if users: status.config(text='Initial setup is complete. Sign in with an administrator to manage users.',fg=T['bad']); return
   if not username: status.config(text='Username is required.',fg=T['bad']); return
   if username.lower() in users: status.config(text='Username already exists.',fg=T['bad']); return
   if not re.fullmatch(r'[A-Za-z0-9_.-]{3,32}',username): status.config(text='Username must be 3–32 characters: letters, numbers, _, ., - only.',fg=T['bad']); return
   if not self._valid_password(password): status.config(text='Password needs 12+ chars, uppercase, lowercase, number, and symbol.',fg=T['bad']); return
   if password!=confirm: status.config(text='Password confirmation does not match.',fg=T['bad']); return
   salt,digest=self._password_hash(password); users[username.lower()]={'username':username,'password_hash':digest,'salt':salt,'role':'Admin','created_at':datetime.datetime.now().astimezone().isoformat(timespec='seconds')}
   try:self._save_users(users)
   except Exception as ex: status.config(text=f'Could not save account: {ex}',fg=T['bad']); return
   status.config(text=f'Administrator account "{username}" created. Return to sign in.',fg=T['good']); uv.set('');pv.set('');cv.set('');role.set('Admin'); ue.focus_set()
  ttk.Button(right,text='CREATE ACCOUNT',command=create).pack(fill='x',padx=38,pady=(0,10),ipady=5)
  ttk.Button(right,text='← BACK TO SIGN IN',command=self.show_login).pack(fill='x',padx=38,ipady=5)
  self.L(right,'Account creation date is recorded automatically.',8,False,T['muted'],T['panel']).pack(anchor='center',pady=(18,3))
  self.L(right,'Your password is never stored in plain text.',8,False,T['muted'],T['panel']).pack(anchor='center')
  self._auth_footer(); self.bind('<Return>',lambda _e:create()); ue.focus_set()

 def show(self,n):
  for f in self.pages.values():f.pack_forget()
  self.pages[n].pack(fill='both',expand=True);self.active_page=n
  for name,row in self.nav_rows.items():
   active=name==n;bg=T['nav_active'] if active else T['sidebar'];fg=T['text'] if active else T['muted']
   row.configure(bg=bg);row.label.configure(bg=bg,fg=fg);row.winfo_children()[0].configure(bg=T['accent'] if active else bg)
  self.page_title_label.config(text=n.upper());self.page_subtitle.config(text={'Dashboard':'Real-time connectivity, performance and troubleshooting overview','Live Monitor':'Continuous network health and latency monitoring'}.get(n,'Network & security operations'))
  if n=='Live Monitor':self.start_monitor()
 def box(self,p):
  f=tk.Frame(p,bg=T['panel2']);f.pack(fill='both',expand=True,padx=12,pady=10);x=tk.Text(f,bg=T['panel2'],fg=T['text'],insertbackground='white',font=('Consolas',9),relief='flat',wrap='word');s=ttk.Scrollbar(f,command=x.yview);x.configure(yscrollcommand=s.set);x.pack(side='left',fill='both',expand=True);s.pack(side='right',fill='y');return x
 def run(self,name,fn):
  if name in self.active_diagnostics:
   if hasattr(self,'diag_status'):self.diag_status.config(text='● TEST ALREADY RUNNING',fg=T['warn'])
   return
  self.active_diagnostics.add(name)
  if hasattr(self,'diag_status'):self.diag_status.config(text='● TEST RUNNING',fg=T['accent'])
  def w():
   try:r=fn()
   except Exception as e:
    LOGGER.exception('Diagnostic job failed: %s',name)
    r='ERROR: '+str(e)
   self.after(0,lambda:self.finish(name,r))
  threading.Thread(target=w,daemon=True).start()
 def finish(self,n,r):
  self.active_diagnostics.discard(n)
  self.out.delete('1.0','end');self.out.insert('1.0',r)
  self.record(n,r)
  sev=None
  low=r.lower()
  if 'error:' in low or 'failed' in low or 'timeout' in low or 'closed / filtered' in low or 'unreachable' in low:
   sev='CRITICAL' if ('error:' in low or 'unreachable' in low or 'failed' in low) else 'WARNING'
  if sev:
   self.alert(sev,f'{n}: abnormal result detected',source='Diagnostics')
  else:
   self.add_dashboard_event('DIAG',f'{n} completed successfully')
  if hasattr(self,'diag_status'):
   self.diag_status.config(text=('● ALERT CREATED' if sev else '● TEST COMPLETE'),
                           fg=T['bad'] if sev=='CRITICAL' else T['warn'] if sev else T['good'])
  if hasattr(self,'diag_last'):
   self.diag_last.config(text=f'{n} • {datetime.datetime.now().strftime("%H:%M:%S")}')
  self.update_report_summary()
 def do_ping(self):self.run('Ping Test',lambda:ping(self.target.get(),4))
 def do_dns(self):self.run('DNS Lookup',lambda:dnslookup(self.target.get()))
 def do_port(self):
  try:p=int(self.pv.get())
  except:messagebox.showerror('Port','Enter a valid port');return
  self.run('Port Check',lambda:f'{self.target.get()}:{p}\nStatus: {port(self.target.get(),p)}')
 def do_trace(self):self.run('Traceroute',lambda:trace(self.target.get()))
 def do_conns(self):self.run('Active Connections',conns)
 def do_info(self):self.run('Network Information',lambda:'\n'.join(f'{k}: {v}' for k,v in info().items()))

 def get_mac(self,host):
  try:
   out=subprocess.check_output(['arp','-a',host],text=True,stderr=subprocess.DEVNULL)
   for part in out.split():
    if '-' in part and len(part)==17:
     return part.replace('-',':').upper()
  except:
   pass
  return 'Unknown'

 def mac_vendor(self,mac):
  if mac=='Unknown':return 'Unknown'
  try:
   if self.mac_lookup is None and MacLookup:self.mac_lookup=MacLookup()
   if self.mac_lookup:
    vendor=self.mac_lookup.lookup(mac)
    if vendor:return vendor
  except Exception:
   pass
  return MAC_VENDORS.get(mac.upper()[:8],'Unknown vendor')

 def update_vendor_database(self):
  if not MacLookup:
   messagebox.showinfo('Vendor lookup','Install the updated requirements first to enable the full vendor database.')
   return
  self.scanner_status.config(text='Downloading the MAC vendor database…',fg=T['accent'])
  def worker():
   try:
    lookup=MacLookup();lookup.update_vendors();self.mac_lookup=lookup
    self.after(0,lambda:self.scanner_status.config(text='Vendor database updated successfully.',fg=T['good']))
   except Exception as e:
    error_message=str(e)
    self.after(0,lambda message=error_message:self.scanner_status.config(text=f'Could not update vendor database: {message}',fg=T['bad']))
  threading.Thread(target=worker,daemon=True).start()

 def export_scan_csv(self):
  if not self.scan_tree.get_children():
   messagebox.showinfo('Export scan','Run a scan first; there are no results to export.')
   return
  p=filedialog.asksaveasfilename(defaultextension='.csv',filetypes=[('CSV file','*.csv')],initialfile='NETGUARD_Network_Scan.csv')
  if not p:return
  try:
   with open(p,'w',newline='',encoding='utf-8-sig') as f:
    statuses=comparison_statuses(getattr(self,'last_scan_comparison',{}))
    w=csv.writer(f);w.writerow(('IP Address','MAC Address','Vendor','Hostname','Open Ports','Risk','Comparison Status'))
    for d in getattr(self,'scan_results',[]):w.writerow((d.get('ip',''),d.get('mac',''),d.get('vendor',''),d.get('hostname',''),d.get('ports',''),d.get('risk',''),statuses.get(device_identity(d),'UNCHANGED')))
   messagebox.showinfo('Export scan','Network scan exported successfully.')
  except OSError as e:
   messagebox.showerror('Export scan',f'Could not save the CSV file:\n{e}')

 def valid_scan_prefix(self,prefix):
  return is_private_scan_prefix(prefix)

 def auto_detect_network(self):
  """Select an active private /24 network; never auto-select public ranges."""
  try:
   _,output=cmd(['ipconfig'])
   candidates=[]
   for block in re.split(r'\r?\n\s*\r?\n',output):
    # Ignore VPN/virtual adapters (Cloudflare WARP, VMware, VirtualBox, etc.)
    adapter_name=block.lower()
    ignored=['cloudflare','warp','vpn','virtual','vmware','virtualbox','hyper-v','tunnel']
    if any(x in adapter_name for x in ignored):
     continue
    ip_match=re.search(r'IPv4 Address[^:]*:\s*([0-9.]+)',block,re.I)
    gateway_match=re.search(r'Default Gateway[^:]*:\s*([0-9.]+)',block,re.I)
    if not ip_match or not gateway_match:continue
    ip=ip_match.group(1)
    first,second=map(int,ip.split('.')[:2])
    private=(first==10 or (first==172 and 16<=second<=31) or (first==192 and second==168))
    if private and not ip.startswith('169.254.'):
     candidates.append(ip)
   if not candidates:
    self.scanner_status.config(text='No active private Wi-Fi/Ethernet subnet found. Enter a permitted local subnet manually.',fg=T['warn'])
    return
   ip=candidates[0];prefix='.'.join(ip.split('.')[:3])+'.';self.scan_target.set(prefix)
   self.scanner_status.config(text=f'Auto-detected local subnet: {prefix}0/24',fg=T['good'])
  except Exception as e:
   self.scanner_status.config(text=f'Could not detect subnet: {e}',fg=T['bad'])

 def scan_ports(self,host):
  """Delegates to core.security (Phase 1 relocation; logic unchanged)."""
  return _core_scan_ports(host)

 def calculate_risk(self,ports):
  """Delegates to core.security (Phase 1 relocation; logic/weights unchanged)."""
  return calculate_risk(ports)

 def start_network_scan(self):
  if not self._require_permission('network_scan'):return
  prefix=self.scan_target.get().strip()
  if not self.valid_scan_prefix(prefix):
   messagebox.showerror('Invalid subnet','Enter a private IPv4 /24 prefix, for example: 192.168.1. Public and reserved ranges are not permitted.')
   return
  if self.scan_running:return
  profile_name=self.scan_profile.get();profile=scan_profile(profile_name)
  prefix=prefix.rstrip('.')+'.'
  self.scan_running=True;self.scan_cancel.clear();self.scan_progress['value']=0
  self.scanner_status.config(text=f'{profile_name} scan… 0 / 254 hosts',fg=T['accent'])
  self.previous_scan_results=list(self.scan_results);self.scan_results=[]
  for item in self.scan_tree.get_children():
   self.scan_tree.delete(item)

  def probe_host(host):
   if self.scan_cancel.is_set():return None
   try:
    ping_cmd=['ping','-n','1','-w','200',host] if platform.system()=='Windows' else ['ping','-c','1','-W','1',host]
    result=subprocess.call(ping_cmd,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    if result!=0:return None
    mac=self.get_mac(host)
    vendor=self.mac_vendor(mac)
    if profile['resolve_hostname']:
     try:host_name=socket.gethostbyaddr(host)[0]
     except:host_name='Unknown'
    else:host_name='Not resolved (Quick)'
    if self.scan_cancel.is_set():return None
    ports=self.scan_ports(host) if profile['scan_ports'] else 'Not scanned (Quick profile)'
    risk=self.calculate_risk(ports) if profile['scan_ports'] else 'NOT ASSESSED'
    return {'ip':host,'mac':mac,'vendor':vendor,'hostname':host_name,'ports':ports,'risk':risk}
   except Exception:
    LOGGER.debug('Host probe failed for %s',host,exc_info=True)
    return None

  def worker():
   found=0
   for completed,_index,device in scan_subnet(prefix,probe_host,self.scan_cancel,max_workers=profile['max_workers']):
    if device:
     found+=1;self.scan_results.append(device)
     risk_level=device['risk'].split(' ',1)[0].lower()
     self.after(0,lambda d=device,l=risk_level:self.scan_tree.insert('', 'end', values=(d['ip'],d['mac'],d['hostname'],d['ports'],d['risk'],l.upper()),tags=(l,)))
    self.after(0,lambda current=completed,count=found:self.scan_progress_update(current,count))
   self.after(0,lambda count=found,cancelled=self.scan_cancel.is_set():self.finish_network_scan(count,cancelled))
  threading.Thread(target=worker,daemon=True).start()

 def scan_progress_update(self,current,found):
  self.scan_progress['value']=current
  self.scanner_status.config(text=f'Scanning… {current} / 254 hosts • {found} device(s) found',fg=T['accent'])

 def cancel_network_scan(self):
  if self.scan_running:
   self.scan_cancel.set();self.scanner_status.config(text='Cancelling active checks…',fg=T['warn'])

 def finish_network_scan(self,found,cancelled):
  self.scan_running=False
  state='cancelled' if cancelled else 'completed'
  self.scanner_status.config(text=f'Scan {state} • {found} device(s) found',fg=T['warn'] if cancelled else T['good'])
  if not cancelled:
   self.last_scan_comparison=compare_scans(self.previous_scan_results,self.scan_results);summary=comparison_summary(self.last_scan_comparison)
   if hasattr(self,'scan_comparison'):self.scan_comparison.config(text=summary,fg=T['warn'] if any(self.last_scan_comparison.values()) else T['good'])
   self.check_new_devices()
  else:summary='Comparison unavailable (scan cancelled).'
  self.record('Network Scan',f'{self.scan_profile.get()} scan {state}: {found} device(s) discovered. {summary}')
  self.add_dashboard_event('SCAN',f'Network discovery {state}: {found} device(s) found')
  self.save_state()

 def device_key(self,device):
  mac=str(device.get('mac','Unknown')).upper()
  return f'MAC:{mac}' if mac!='UNKNOWN' else f'IP:{device.get("ip","")}'

 def save_scan_baseline(self):
  if not getattr(self,'scan_results',[]):
   messagebox.showinfo('Save baseline','Run a completed network scan before saving a baseline.');return
  try:name=normalize_baseline_name(self.baseline_name.get())
  except ValueError as error:
   self.baseline_status.config(text=str(error),fg=T['bad']);return
  if name in self.scan_baselines and not messagebox.askyesno('Replace baseline',f'Replace the saved baseline "{name}" with this scan?'):
   return
  self.scan_baselines=save_baseline(self.scan_baselines,name,self.scan_results,datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
  self.baseline_selected.set(name);self._sync_baseline_controls()
  self.last_baseline_comparison=compare_scans(self.scan_baselines[name]['devices'],self.scan_results)
  self.baseline_status.config(text=f'● Baseline "{name}" saved with {len(self.scan_results)} device(s).',fg=T['good'])
  self.record('Scan Baseline',f'Baseline "{name}" saved: {len(self.scan_results)} device(s).')

 def compare_selected_baseline(self):
  name=self.baseline_selected.get()
  if name not in self.scan_baselines:
   self.baseline_status.config(text='Select a saved baseline first.',fg=T['warn']);return
  if not getattr(self,'scan_results',[]):
   self.baseline_status.config(text='Run a completed network scan before comparing.',fg=T['warn']);return
  self.last_baseline_comparison=compare_scans(self.scan_baselines[name]['devices'],self.scan_results)
  summary=comparison_summary(self.last_baseline_comparison)
  self.baseline_status.config(text=f'● Baseline "{name}": {summary}',fg=T['warn'] if any(self.last_baseline_comparison.values()) else T['good'])
  self.record('Baseline Compare',f'Baseline "{name}" compared with current scan. {summary}')

 def _sync_baseline_controls(self):
  if not hasattr(self,'baseline_selector'):return
  names=list(self.scan_baselines)
  self.baseline_selector.config(values=names)
  if self.baseline_selected.get() not in names:self.baseline_selected.set(names[0] if names else '')

 def check_new_devices(self):
  current={self.device_key(device) for device in self.scan_results}
  if self.known_devices:
   new_devices=current-self.known_devices
   for device in self.scan_results:
    if self.device_key(device) in new_devices:
     label=device.get('hostname') if device.get('hostname') not in ('','Unknown') else device.get('ip','Unknown device')
     self.alert('WARNING',f'New device discovered: {label} ({device.get("ip","")})',source='Network Scanner')
   if new_devices:self.scanner_status.config(text=f'Scan completed • {len(current)} device(s), {len(new_devices)} new device alert(s)',fg=T['warn'])
  self.known_devices.update(current)

 def start_monitor(self):
  if self.monitor:return
  self.monitor=True;self.ms.config(text='● MONITORING',fg=T['good']);self.loop()
 def stop_monitor(self):self.monitor=False;self.ms.config(text='STOPPED',fg=T['muted'])
 def loop(self):
  if not self.monitor:return
  def w():
   ok,method,o=internet_check();v=latency(o)
   if v is None and ok:v=https_latency();method='HTTPS latency' if v is not None else method
   self.after(0,lambda:self.monitor_update(v,o,ok,method))
  threading.Thread(target=w,daemon=True).start()
 def monitor_update(self,v,o,online,method):
  if not self.monitor:return
  if v is not None:self.points.append(v);self.points=self.points[-45:]
  if v is not None:
   label=f'{v:.0f} ms';color=T['good'] if v<100 else T['warn'];log=f'OK  {v:.0f} ms';severity='OK';event=f'Live monitor: {v:.0f} ms latency'
  elif online:
   label='ICMP BLOCKED';color=T['warn'];log=f'ONLINE via {method} — ICMP blocked';severity='INFO';event='Live monitor: HTTPS online; ICMP ping blocked'
  else:
   label='OFFLINE';color=T['bad'];log='OFFLINE';severity='CRITICAL';event='Live monitor: connectivity failed'
  self.ml.config(text=label,fg=color);self.ms.config(text='● MONITORING' if online else '● CONNECTION FAILED',fg=T['good'] if online else T['bad'])
  self.mlog.insert('1.0',f'{datetime.datetime.now():%H:%M:%S}  {log}\n')
  self.graph_draw();self.update_dashboard_stats()
  if v is not None or not online:self.add_dashboard_event(severity,event)
  self.after(2000,self.loop)
 def graph_draw(self):
  c=self.graph;c.delete('all');w=max(c.winfo_width(),700);h=300
  for i in range(1,5):c.create_line(20,i*h/5,w-20,i*h/5,fill=T['border'])
  if len(self.points)>1:
   mx=max(max(self.points),100);pts=[]
   for i,v in enumerate(self.points):pts += [25+i*(w-50)/44,h-25-(v/mx)*(h-50)]
   c.create_line(*pts,fill=T['accent'],width=3,smooth=True)
  c.create_text(30,18,text='LATENCY (ms)',fill=T['muted'],anchor='w',font=('Segoe UI',8))
 def drawmap(self):
  c=self.map
  c.delete('all')
  w=max(c.winfo_width(),1000)
  try: info_data=info()
  except Exception: info_data={}
  gateway=info_data.get('Gateway','Unavailable')
  dns=info_data.get('DNS','Unavailable')
  local_ip=info_data.get('Local IP','Unavailable')
  devices=list(getattr(self,'scan_results',[]) or [])[:40]

  # Core path
  core_y=150
  xs=[w*.12,w*.38,w*.64,w*.88]
  core=[('PC',local_ip),('GATEWAY',gateway),('DNS',dns),('INTERNET','External')]
  for i in range(3):
   c.create_line(xs[i]+78,core_y,xs[i+1]-78,core_y,fill=T['accent'],width=4)
  for x,(title,value) in zip(xs,core):
   c.create_oval(x-78,core_y-48,x+78,core_y+48,fill=T['panel'],outline=T['accent'],width=2)
   c.create_text(x,core_y-10,text=title,fill=T['text'],font=('Segoe UI',10,'bold'))
   c.create_text(x,core_y+15,text=str(value)[:22],fill=T['muted'],font=('Consolas',8))

  # Discovered devices
  if devices:
   c.create_text(35,255,text=f'DISCOVERED DEVICES ({len(getattr(self,"scan_results",[]) or [])})',anchor='w',fill=T['muted'],font=('Segoe UI',9,'bold'))
   cols=min(5,max(1,int((w-80)/190)))
   start_y=300; box_w=170; box_h=92; gap_x=15; gap_y=18
   for idx,d in enumerate(devices):
    row,col=divmod(idx,cols)
    x=35+col*(box_w+gap_x); y=start_y+row*(box_h+gap_y)
    cx=x+box_w/2
    c.create_line(xs[1],core_y+48,cx,y,fill=T['border'],width=2)
    risk=str(d.get('risk','')).upper()
    outline=T['bad'] if risk in ('HIGH','CRITICAL') else T['warn'] if risk in ('MEDIUM','WARNING') else T['good']
    c.create_rectangle(x,y,x+box_w,y+box_h,fill=T['panel'],outline=outline,width=2)
    host=str(d.get('hostname') or 'Unknown')
    ip=str(d.get('ip') or 'Unknown')
    mac=str(d.get('mac') or 'Unknown')
    ports=str(d.get('ports') or '-')
    c.create_text(cx,y+14,text=host[:24],fill=T['text'],font=('Segoe UI',9,'bold'))
    c.create_text(cx,y+34,text=ip,fill=T['accent'],font=('Consolas',8))
    c.create_text(cx,y+51,text=mac[:23],fill=T['muted'],font=('Consolas',7))
    c.create_text(cx,y+69,text=f'Risk: {risk or "LOW"}  Ports: {ports[:12]}',fill=outline,font=('Segoe UI',7,'bold'))
  else:
   c.create_text(w/2,320,text='NO DISCOVERED DEVICES',fill=T['muted'],font=('Segoe UI',13,'bold'))
   c.create_text(w/2,350,text='Run Network Scanner first, then click REFRESH MAP.',fill=T['muted'],font=('Segoe UI',9))

  if hasattr(self,'map_status'):
   count=len(getattr(self,'scan_results',[]) or [])
   self.map_status.config(text=f'{count} discovered device(s) • Gateway: {gateway} • Updated {datetime.datetime.now():%H:%M:%S}')
  # Keep the command-center KPI cards synchronized with the topology that
  # was just drawn.  App.drawmap overrides the mixin implementation, so this
  # update belongs here rather than in ui.pages.py.
  if hasattr(self,'map_kpis'):
   all_devices=list(getattr(self,'scan_results',[]) or [])
   high=sum(1 for d in all_devices if str(d.get('risk','')).upper() in ('HIGH','CRITICAL'))
   medium=sum(1 for d in all_devices if str(d.get('risk','')).upper() in ('MEDIUM','WARNING'))
   self.map_kpis['devices'].config(text=str(len(all_devices)))
   self.map_kpis['high'].config(text=str(high),fg=T['bad'] if high else T['good'])
   self.map_kpis['medium'].config(text=str(medium),fg=T['warn'] if medium else T['good'])
   self.map_kpis['gateway'].config(text=str(gateway)[:18])
   self.map_kpis['status'].config(text='ONLINE' if all_devices else 'READY',fg=T['good'] if all_devices else T['muted'])


 def start_system_monitor(self):
  if self.system_running:return
  self.system_running=True
  self.system_loop()

 def stop_system_monitor(self):
  self.system_running=False

 def system_loop(self):
  if not self.system_running:return
  try:
   if psutil:
    cpu=psutil.cpu_percent()
    ram=psutil.virtual_memory().percent
    disk=psutil.disk_usage('/').percent
    net=psutil.net_io_counters()
    self.sys_cards['cpu'].config(text=f'{cpu:.0f}%')
    self.sys_cards['ram'].config(text=f'{ram:.0f}%')
    self.sys_cards['disk'].config(text=f'{disk:.0f}%')
    self.sys_cards['net'].config(text=f'↑ {net.bytes_sent/1024/1024:.1f}MB ↓ {net.bytes_recv/1024/1024:.1f}MB')
   else:
    self.sys_cards['net'].config(text='Install psutil')
  except Exception:
   self.sys_cards['net'].config(text='ERROR')
  self.after(2000,self.system_loop)

 def system_scan(self):
  data=[f'NETGUARD SYSTEM MONITOR v{APP_VERSION}','='*55]
  data.append(f'Hostname: {socket.gethostname()}')
  data.append(f'OS: {platform.platform()}')
  data.append(f'Python: {platform.python_version()}')
  if psutil:
   data.append(f'CPU Usage: {psutil.cpu_percent()}%')
   data.append(f'Memory Usage: {psutil.virtual_memory().percent}%')
   data.append(f'Disk Usage: {psutil.disk_usage("/").percent}%')
  else:
   data.append('Install psutil for advanced monitoring')
  data.append(f'Time: {datetime.datetime.now()}')
  data.append('\nNetwork Connections Snapshot:')
  data.append(conns()[:1500])
  report='\n'.join(data)
  self.system_output.delete('1.0','end')
  self.system_output.insert('1.0',report)
  self.record('System Check',report)
  self.add_dashboard_event('SYSTEM','Advanced system check completed')

 def security_scan(self):
  if not self._require_permission('security_scan'):return
  findings=[]
  devices=getattr(self,'scan_results',[]) or []
  for d in devices:
   ip=str(d.get('ip','Unknown'));name=str(d.get('hostname') or d.get('vendor') or ip)
   ports=str(d.get('ports','None'))
   for severity,message,port_number in security_findings_for_ports(ports):
    findings.append((severity,name,ip,message,port_number))

  # Flag devices with a scanner-provided elevated risk even if ports are unavailable.
  for d in devices:
   risk=str(d.get('risk',''))
   if risk.startswith('HIGH') and not any(f[2]==str(d.get('ip','')) for f in findings):
    findings.append(('HIGH',str(d.get('hostname') or d.get('vendor') or d.get('ip','Unknown')),str(d.get('ip','Unknown')),'Scanner marked this device as high risk. Review its exposed services.',''))

  score=100
  weights={'CRITICAL':30,'HIGH':18,'MEDIUM':10,'LOW':3,'INFO':0}
  for f in findings:score=max(0,score-weights.get(f[0],0))
  self.security_findings=findings;self.security_score=score

  for item in self.security_tree.get_children():self.security_tree.delete(item)
  for sev,name,ip,msg,ports in findings:
   self.security_tree.insert('', 'end', values=(sev,name,ip,msg,ports))

  if score>=90:status='GOOD';fg=T['good']
  elif score>=70:status='ATTENTION';fg=T['warn']
  else:status='AT RISK';fg=T['bad']
  self.security_score_label.config(text=f'SECURITY SCORE: {score}/100 • {status}',fg=fg)
  self.security_summary.config(text=f'{len(devices)} scanned device(s) • {len(findings)} finding(s)')

  result=['NETGUARD SECURITY CHECK','='*55,f'Generated: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',f'Score: {score}/100 ({status})',f'Discovered devices: {len(devices)}',f'Findings: {len(findings)}','']
  if findings:
   result.append('FINDINGS')
   for sev,name,ip,msg,ports in findings:result.append(f'[{sev}] {name} ({ip}) {msg}'+(f' Ports: {ports}' if ports else ''))
  else:
   result.append('No exposed-risk findings were identified from the available scan results.')
  result += ['', 'ACTIVE NETWORK CONNECTIONS', '-'*55, conns()[:2000]]
  report='\n'.join(result)
  self.security_output.delete('1.0','end');self.security_output.insert('1.0',report)

  for sev,name,ip,msg,ports in findings:
   if sev in ('CRITICAL','HIGH'):
    self.alert(sev,f'{name} ({ip}): {msg}',source='Security Center')
  self.record('Security Check',f'Score {score}/100; {len(findings)} finding(s) across {len(devices)} device(s).')
  self.add_dashboard_event('SECURITY',f'Security check completed: {score}/100, {len(findings)} finding(s)')
  self.save_state()

 def apply_theme(self):
  global T
  selected=self.tv.get()
  if selected not in THEMES:return
  T=THEMES[selected];_styles.T=T;self.style()
  self.configure(bg=T['bg'])
  if hasattr(self,'side'):self.side.configure(bg=T['sidebar'])
  for row in getattr(self,'nav_rows',{}).values():
   active=getattr(row,'label',None) and getattr(row.label,'name',None)==getattr(self,'active_page',None)
   bg=T['nav_active'] if active else T['sidebar'];row.configure(bg=bg);row.label.configure(bg=bg);row.winfo_children()[0].configure(bg=T['accent'] if active else bg)
  if hasattr(self,'health_bar'):self.draw_health_bar()
  if hasattr(self,'dash_graph'):self.dashboard_graph_draw()
  if hasattr(self,'monitor_graph'):self.monitor_graph_draw()
  if hasattr(self,'map_canvas'):self.draw_map()
  if hasattr(self,'settings_theme_status'):
   self.settings_theme_status.config(text=f'● {selected.upper()} APPLIED',fg=T['good'])
  self.add_dashboard_event('INFO',f'Theme changed to {selected}.')

 def save_health_thresholds(self):
  raw={key:variable.get() for key,variable in self.health_threshold_vars.items()}
  try:
   self.health_thresholds=normalize_health_thresholds(raw)
  except ValueError as error:
   self.health_threshold_status.config(text=str(error),fg=T['bad']);return
  self._sync_health_threshold_inputs()
  self.health_threshold_status.config(text='● Health thresholds saved locally.',fg=T['good'])
  self.add_dashboard_event('INFO','Health thresholds updated.')
  self.save_state()

 def _sync_health_threshold_inputs(self):
  if not hasattr(self,'health_threshold_vars'):return
  for key,variable in self.health_threshold_vars.items():
   value=self.health_thresholds.get(key,DEFAULT_HEALTH_THRESHOLDS[key])
   variable.set(f'{value:g}')
 def save_retention_limits(self):
  requested=normalize_retention_limits({key:variable.get() for key,variable in self.retention_limit_vars.items()})
  current_history=len(self.hist);current_alerts=len(self.alert_rows)
  would_remove=max(0,current_history-requested['history'])+max(0,current_alerts-requested['alerts'])
  if would_remove and not messagebox.askyesno('Reduce retained records',f'This keeps the newest records and removes {would_remove} older local record(s). Continue?'):
   self._sync_retention_limit_inputs();return
  self.retention_limits=requested
  self.hist=retain_latest(self.hist,requested['history'])
  self.alert_rows=self.alert_rows[:requested['alerts']]
  if hasattr(self,'ht'):self.filter_history()
  self._render_alerts();self.refresh_alert_summary();self.update_report_summary()
  self.retention_status.config(text='● Local retention limits saved.',fg=T['good'])
  self.add_dashboard_event('INFO','Local record retention limits updated.')
  self.save_state()

 def _sync_retention_limit_inputs(self):
  if not hasattr(self,'retention_limit_vars'):return
  for key,variable in self.retention_limit_vars.items():
   variable.set(str(self.retention_limits.get(key,DEFAULT_RETENTION_LIMITS[key])))
  if hasattr(self,'retention_status'):
   self.retention_status.config(text=f"● Local retention: {self.retention_limits['history']} audit events and {self.retention_limits['alerts']} incidents.",fg=T['good'])

 def refresh(self):
  i=info();self.network_info=i;self.update_dashboard_details(i)
  previous_vpn=getattr(self,'last_vpn_status',None);current_vpn=i.get('VPN','NO VPN')
  if previous_vpn is not None and previous_vpn!=current_vpn:self.add_dashboard_event('VPN',f'VPN state changed: {previous_vpn} → {current_vpn}')
  elif previous_vpn is None:self.add_dashboard_event('VPN',f'VPN status: {current_vpn} — {i.get("VPN Details","")}')
  self.last_vpn_status=current_vpn
  self.cards['dns'].config(text=i['DNS'],fg=T['text'] if i['DNS']!='Unavailable' else T['bad']);self.cards['gw'].config(text=i['Gateway'],fg=T['text'] if i['Gateway']!='Unavailable' else T['bad']);self.cards['internet'].config(text='CHECKING',fg=T['muted'])
  def w():
   ok,method,o=internet_check();v=latency(o);l=loss(o)
   if v is None and ok:
    v=https_latency()
    if v is not None:method='HTTPS latency'
   self.after(0,lambda:self.cards_update(ok,v,l,method))
  threading.Thread(target=w,daemon=True).start()
 def cards_update(self,ok,v,l,method='Ping'):
  thresholds=self.health_thresholds
  latency_warning=thresholds['latency_warning_ms'];latency_critical=thresholds['latency_critical_ms']
  loss_warning=thresholds['packet_loss_warning_pct'];loss_critical=thresholds['packet_loss_critical_pct']
  label='🟢 ONLINE' if method=='Ping' else '🟢 ONLINE (HTTPS)' if ok else '🔴 OFFLINE'
  self.cards['internet'].config(text=label,fg=T['good'] if ok else T['bad'])
  self.cards['lat'].config(text=f'{v:.0f} ms' if v is not None else '-- ms',fg=T['good'] if v is not None and v<latency_warning else T['warn'] if v is not None and v<latency_critical else T['bad'])
  if ok and method!='Ping':self.cards['loss'].config(text='ICMP BLOCKED',fg=T['warn'])
  else:self.cards['loss'].config(text=f'{l}%' if l is not None else '-- %',fg=T['good'] if l is not None and l<loss_warning else T['warn'] if l is not None and l<loss_critical else T['bad'])
  self.add_dashboard_event('OK' if ok else 'CRITICAL',f'Internet connectivity: {"ONLINE via "+method if ok else "OFFLINE"}')
  if v is not None:self.add_dashboard_event('OK' if v<100 else 'WARNING',f'Latency measured at {v:.0f} ms')
  if l is not None:self.add_dashboard_event('OK' if l<5 else 'WARNING' if l<=20 else 'CRITICAL',f'Packet loss: {l}%')
  self.update_dashboard_stats()
  if l is not None and l>=loss_critical:self.alert('CRITICAL',f'High packet loss detected: {l}%')
  elif v and v>=latency_warning:self.alert('CRITICAL' if v>=latency_critical else 'WARNING',f'High latency detected: {v:.0f} ms')
 def scan(self):
  def w():
   i=info();ok,method,o=internet_check();v=latency(o);l=loss(o);d=dnslookup('google.com')
   if v is None and ok:
    v=https_latency()
    if v is not None:method='HTTPS latency'
   assessment=health_assessment(i,ok,v,l,'IPv4:' in d,self.health_thresholds)
   score=assessment['score'];status=assessment['status'];insights='\n'.join(f'• {item}' for item in assessment['insights'])
   r=f'NETGUARD SMART HEALTH REPORT\n{"="*65}\n\nSCORE: {score}/100   STATUS: {status}\n\nConnection: {i.get("Connection","Unavailable")}\nAdapter: {i.get("Adapter","Unavailable")}\nLocal IP: {i["Local IP"]}\nGateway: {i["Gateway"]}\nDNS: {i["DNS"]}\nLatency: {f"{v:.0f}" if v is not None else "Unavailable"} ms\nPacket Loss: {l if l is not None else "ICMP blocked"}\nInternet: {"PASS" if ok else "FAIL"} ({method})\nDNS Resolution: {"PASS" if "IPv4:" in d else "FAIL"}\n\nSMART INSIGHTS\n{"-"*65}\n{insights}\n\nTroubleshooting order:\n1. Adapter/IP\n2. Gateway\n3. DNS\n4. Internet\n5. Latency and packet loss\n\nRAW PING\n{"-"*65}\n{o}';self.after(0,lambda:self.showreport(r))
  threading.Thread(target=w,daemon=True).start()
 def showreport(self,r):
  self.dash.delete('1.0','end');self.dash.insert('1.0',r);self.rep.delete('1.0','end');self.rep.insert('1.0',r)
  m=re.search(r'SCORE:\s*(\d+)/100\s+STATUS:\s*([^\n]+)',r)
  if m:
   score=int(m.group(1));status=m.group(2).strip();self.set_health_score(score,status);self.add_dashboard_event('SCAN',f'Health scan completed: {score}/100 — {status}')
  self.update_dashboard_stats();self.update_report_summary();self.record('Full Health Scan',r)
 def alert(self,s,m,source='System'):
  # Suppress duplicate active incidents so repeated checks do not flood the queue.
  for vals in self.alert_rows:
   if len(vals)>=4 and str(vals[1])==str(s) and str(vals[2])==str(m) and str(vals[3])==str(source):
    return None
  self.alert_rows.insert(0,[datetime.datetime.now().strftime('%H:%M:%S'),s,m,source])
  self.alert_rows=self.alert_rows[:self.retention_limits['alerts']]
  self._render_alerts()
  self.add_dashboard_event(s,m)
  self.refresh_alert_summary()
  self.save_state()
  return True
 def record(self,a,r):
  x={'time':datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),'action':a,'result':r};self.hist.append(x);self.hist=retain_latest(self.hist,self.retention_limits['history']);self.ht.insert('',0,values=(x['time'],a,r[:160].replace('\n',' ')));self.save_state()
  if hasattr(self,'report_summary'):self.update_report_summary()

 def save_state(self):
  try:
   _core_save_app_state({'history':retain_latest(self.hist,self.retention_limits['history']),'alerts':self.alert_rows[:self.retention_limits['alerts']],'scan_results':getattr(self,'scan_results',[]),'known_devices':sorted(self.known_devices),'health_thresholds':self.health_thresholds,'retention_limits':self.retention_limits,'scan_baselines':self.scan_baselines,'last_baseline_comparison':self.last_baseline_comparison,'scan_profile':self.scan_profile.get(),'last_scan_comparison':self.last_scan_comparison})
  except Exception:
   pass

 def load_state(self):
  try:
   data=_core_load_app_state()
   self.retention_limits=normalize_retention_limits(data.get('retention_limits'))
   self.hist=retain_latest(data.get('history',[]),self.retention_limits['history'])
   for x in reversed(self.hist):self.ht.insert('',0,values=(x.get('time',''),x.get('action',''),str(x.get('result',''))[:160].replace('\n',' ')))
   self.alert_rows=normalize_alert_rows(data.get('alerts',[])[:self.retention_limits['alerts']])
   try:self.health_thresholds=normalize_health_thresholds(data.get('health_thresholds'))
   except ValueError:self.health_thresholds=dict(DEFAULT_HEALTH_THRESHOLDS)
   if hasattr(self,'scan_profile') and data.get('scan_profile') in ('Quick Discovery','Standard','Deep Analysis'):self.scan_profile.set(data['scan_profile'])
   self._sync_health_threshold_inputs();self._sync_retention_limit_inputs();self._render_alerts();self.alert_count=len(self.alert_rows);self.scan_results=data.get('scan_results',[]);self.scan_baselines=normalize_baselines(data.get('scan_baselines'));self.last_baseline_comparison=data.get('last_baseline_comparison',self.last_baseline_comparison);self._sync_baseline_controls();self.last_scan_comparison=data.get('last_scan_comparison',self.last_scan_comparison);self.known_devices=set(data.get('known_devices',[]))
   if hasattr(self,'alert_stats'):self.refresh_alert_summary()
   if self.hist or self.alert_count:self.add_dashboard_event('INFO',f'Restored {len(self.hist)} history item(s) and {self.alert_count} alert(s).')
  except (OSError,json.JSONDecodeError):
   pass
  self.update_dashboard_stats();self.update_report_summary()

 def on_close(self):
  self.scan_cancel.set();self.monitor=False;self.system_running=False;self.save_state();self.destroy()
 def report(self):
  if not self.dash.get('1.0','end').strip():
   self.scan();return
  now=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
  alerts=self.alert_rows
  lines=[
   'NETGUARD UNIFIED NETWORK OPERATIONS REPORT',
   '='*72,
   f'Generated: {now}',
   '',
   f'Health Score : {getattr(self,"current_score",0)}/100',
   f'Health Status: {getattr(self,"health_status",None).cget("text") if hasattr(self,"health_status") else "Unknown"}',
   f'Alerts       : {len(alerts)}',
   f'History      : {len(self.hist)} events',
   f'Monitor Data : {len(self.points)} latency samples',
   '',
   'NETWORK INFORMATION',
   '-'*72
  ]
  lines += [f'{k}: {v}' for k,v in info().items()]
  lines += ['', 'LATEST SCAN COMPARISON', '-'*72]
  lines += comparison_report_lines(getattr(self,'last_scan_comparison',{}))
  lines += ['', 'ALERTS / INCIDENTS','-'*72]
  for vals in alerts:
   lines.append(' | '.join(map(str,vals)))
  lines += ['', 'HISTORY','-'*72]
  for x in self.hist[-50:]:lines.append(f'{x["time"]} | {x["action"]} | {x["result"][:300].replace(chr(10)," ")}')
  lines += ['', 'RAW HEALTH REPORT','-'*72, self.dash.get('1.0','end').strip()]
  report_text='\n'.join(lines)
  p=filedialog.asksaveasfilename(defaultextension='.txt',filetypes=[('Text report','*.txt')],initialfile='NETGUARD_Unified_Report.txt')
  if p:
   Path(p).write_text(report_text,encoding='utf-8');messagebox.showinfo('Report','Unified NETGUARD report exported successfully.')
 def update_report_summary(self):
  if not hasattr(self,'report_summary'):return
  vals=self.points[-45:]
  alert_count=len(self.alert_rows)
  status=self.health_status.cget('text') if hasattr(self,'health_status') else 'Not scanned'
  avg=(sum(vals)/len(vals)) if vals else None
  i=info()
  s=(f'NETGUARD OPERATIONS SUMMARY\n{"="*55}\n'
     f'Health       : {getattr(self,"current_score",0)}/100 • {status}\n'
     f'Internet     : {self.cards["internet"].cget("text") if hasattr(self,"cards") else "Unknown"}\n'
     f'Latency      : {self.cards["lat"].cget("text") if hasattr(self,"cards") else "Unknown"}\n'
     f'Packet Loss  : {self.cards["loss"].cget("text") if hasattr(self,"cards") else "Unknown"}\n'
     f'Avg Latency  : {avg:.0f} ms\n' if avg is not None else
     f'NETGUARD OPERATIONS SUMMARY\n{"="*55}\nHealth       : {getattr(self,"current_score",0)}/100 • {status}\n'
     f'Internet     : {self.cards["internet"].cget("text") if hasattr(self,"cards") else "Unknown"}\n'
     f'Latency      : {self.cards["lat"].cget("text") if hasattr(self,"cards") else "Unknown"}\n'
     f'Packet Loss  : {self.cards["loss"].cget("text") if hasattr(self,"cards") else "Unknown"}\n'
     f'Avg Latency  : --\n')
  comparison=comparison_summary(getattr(self,'last_scan_comparison',{'new':[],'gone':[],'changed':[]}))
  s+=f'Active Incidents: {alert_count}\nHistory Events : {len(self.hist)}\nMonitor Samples: {len(self.points)}\nLatest Scan    : {comparison}\n\n'
  s+=f'Hostname: {i["Hostname"]}\nLocal IP: {i["Local IP"]}\nGateway : {i["Gateway"]}\nDNS     : {i["DNS"]}'
  self.report_summary.delete('1.0','end');self.report_summary.insert('1.0',s)

 def ack_alert(self):
  sel=self.at.selection()
  if not sel:return
  indexes=[int(str(iid).removeprefix('alert-')) for iid in sel if str(iid).startswith('alert-')]
  changed=acknowledge_alert_rows(self.alert_rows,indexes)
  self._render_alerts();self.add_dashboard_event('INFO',f'{changed} alert(s) acknowledged')
  self.refresh_alert_summary();self.update_report_summary();self.save_state()

 def _render_alerts(self):
  if not hasattr(self,'at'):return
  wanted=getattr(self,'alert_filter',tk.StringVar(value='ALL')).get()
  for iid in self.at.get_children():self.at.delete(iid)
  for index,vals in filtered_alert_rows(self.alert_rows,wanted):
   severity=str(vals[1]) if len(vals)>1 else 'LOW'
   self.at.insert('', 'end', iid=f'alert-{index}', values=vals, tags=(severity,))

 def filter_alerts(self):
  self._render_alerts()
  self.refresh_alert_summary()

 def clear_acknowledged(self):
  self.alert_rows,removed=remove_acknowledged_alert_rows(self.alert_rows)
  self._render_alerts()
  self.add_dashboard_event('INFO',f'Cleared {removed} acknowledged alert(s)')
  self.refresh_alert_summary();self.update_report_summary();self.save_state()

 def refresh_alert_summary(self):
  if not hasattr(self,'alert_stats'):return
  counts={k:0 for k in self.alert_stats}
  for vals in self.alert_rows:
   sev=str(vals[1]) if len(vals)>1 else 'LOW'
   counts[sev]=counts.get(sev,0)+1
  for k,lbl in self.alert_stats.items():lbl.config(text=str(counts.get(k,0)))
  self.alert_count=len(self.alert_rows)
  if hasattr(self,'stat_alert'):self.stat_alert.config(text=str(self.alert_count))

 def clear_alerts(self):
  self.alert_rows=[];self._render_alerts()
  self.add_dashboard_event('INFO','Alert queue cleared')
  self.refresh_alert_summary();self.update_report_summary()
  self.save_state()

 def export_alerts(self):
  p=filedialog.asksaveasfilename(defaultextension='.csv',filetypes=[('CSV file','*.csv')],initialfile='NETGUARD_Alerts.csv')
  if not p:return
  rows=['Time,Severity,Message,Source']
  for vals in self.alert_rows:
   rows.append(','.join('"'+str(v).replace('"','""')+'"' for v in vals))
  Path(p).write_text('\n'.join(rows),encoding='utf-8');messagebox.showinfo('Alerts','Incident list exported successfully.')

 def export_unified_json(self):
  p=filedialog.asksaveasfilename(defaultextension='.json',filetypes=[('JSON file','*.json')],initialfile='NETGUARD_Unified_Report.json')
  if not p:return
  data={'generated':datetime.datetime.now().isoformat(timespec='seconds'),'health':{'score':getattr(self,'current_score',0),'status':self.health_status.cget('text') if hasattr(self,'health_status') else 'Unknown'},'network':info(),'latency_samples':self.points[-100:],'history':self.hist[-100:],'alerts':[dict(zip(('time','severity','message','source'),values)) for values in self.alert_rows],'scan_comparison':getattr(self,'last_scan_comparison',{'new':[],'gone':[],'changed':[]})}
  Path(p).write_text(json.dumps(data,indent=2,default=str),encoding='utf-8');messagebox.showinfo('Report','Unified JSON report exported successfully.')
 def export(self):
  if not self.hist:return
  p=filedialog.asksaveasfilename(defaultextension='.json',filetypes=[('JSON','*.json')]);
  if p:json.dump(self.hist,open(p,'w',encoding='utf-8'),indent=2);messagebox.showinfo('Export','JSON exported.')
 def clear(self):
  self.hist.clear()
  for x in self.ht.get_children():self.ht.delete(x)
  self.save_state()
 def tick(self):self.clock.config(text=datetime.datetime.now().strftime('%d %b %Y  •  %H:%M:%S'));self.after(1000,self.tick)
if __name__=='__main__':App().mainloop()
