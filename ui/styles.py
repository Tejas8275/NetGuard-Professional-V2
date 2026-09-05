"""
Theme palettes and font constants.
Pure data, no widget logic — this file only defines colors, spacing and
fonts. All existing THEMES keys are preserved exactly (every UI file reads
T['bg'], T['panel'], T['accent'], etc.), so nothing downstream needs to
change.

NOTE: `T` is mutated at runtime by App.apply_theme() (module-level global
swap). Import this module and use `styles.T` / reassign `styles.T` rather
than copying the dict, to preserve the existing "global theme swap" behavior.
"""

# Professional cybersecurity SOC theme.
# Deep navy/black background, dark blue-gray panels, neon cyber-blue accent,
# green/yellow/red status colors, white titles + light-gray secondary text.
THEMES = {
    'Midnight Blue': dict(
        bg='#070b16',            # layered midnight-blue workspace
        panel='#0d1424',         # primary card surface
        panel2='#121d32',        # elevated fields / tables
        panel3='#09101f',        # recessed wells / command areas
        sidebar='#080e1b',       # focused left navigation rail
        nav_hover='#142743',     # interactive navigation hover
        nav_active='#123b68',    # selected navigation treatment
        accent='#35d8ff',        # electric cyan primary accent
        accent_soft='#168ed1',   # pressed / hover accent
        text='#f7fbff',          # high-contrast title text
        muted='#9aabc5',         # readable secondary text
        good='#2be895',          # success / healthy status
        warn='#ffc857',          # warning status
        bad='#ff5c73',           # danger / critical status
        border='#233657',        # crisp hairline borders
        scrollbar='#1b2c49',    # scroll thumb base
        elevated='#16243d',
        glow='#173d65'
    ),
    'Cyber Purple': dict(
        bg='#08050f', panel='#120c1e', panel2='#18112a', panel3='#0d081a', sidebar='#0b0716',
        nav_hover='#221436', nav_active='#33195a', accent='#b566ff', accent_soft='#9333ea',
        text='#f8f5ff', muted='#a99bc4', good='#2fe08a', warn='#f5c344', bad='#ff5577',
        border='#2c1c46', scrollbar='#241735'
    ),
    'Emerald SOC': dict(
        bg='#040d0a', panel='#0a1913', panel2='#0f2118', panel3='#07120d', sidebar='#06110c',
        nav_hover='#102a1f', nav_active='#12402c', accent='#22e0a8', accent_soft='#0ea578',
        text='#f2fbf6', muted='#8fada0', good='#22e07a', warn='#f5c344', bad='#ff4d5e',
        border='#193a2b', scrollbar='#153025'
    )
}

T = THEMES['Midnight Blue']

# Spacing / radius scale (px). Additive — not consumed yet by existing
# widget code, available for the upcoming layout redesign passes.
SPACING_XS = 4
SPACING_SM = 8
SPACING_MD = 12
SPACING_LG = 16
SPACING_XL = 24
SPACING_XXL = 32
RADIUS_SM = 4
RADIUS_MD = 8
RADIUS_LG = 12

F_BRAND = ('Segoe UI', 16, 'bold')
F_PAGE_TITLE = ('Segoe UI', 18, 'bold')
F_SECTION_LABEL = ('Segoe UI', 9, 'bold')
F_NAV = ('Segoe UI', 10, 'bold')
F_CLOCK = ('Consolas', 10, 'bold')

# Additional professional type-scale constants (additive; existing pages
# keep using explicit point sizes via self.L(), these are available for
# future redesign passes without requiring any call-site changes now).
F_MONO = ('Consolas', 9, 'normal')
F_MONO_BOLD = ('Consolas', 9, 'bold')
F_CAPTION = ('Segoe UI', 8, 'normal')
F_METRIC = ('Segoe UI', 22, 'bold')
