"""
╔══════════════════════════════════════════════════════════════════╗
║     SIMULASI GERHANA 3D  v5-FIXED  —  OpenGL + PyGame           ║
╠══════════════════════════════════════════════════════════════════╣
║  PERBAIKAN:                                                      ║
║  - Gedung berwarna-warni (bug GL_COLOR_MATERIAL difix)           ║
║  - Matahari & Bulan JELAS terlihat di langit kota               ║
║  - Matahari digambar di layer langit (depth disabled)           ║
║  - Bulan muncul sejak awal dengan ukuran besar                  ║
║  - Sinar & halo matahari benar-benar terlihat                   ║
╠══════════════════════════════════════════════════════════════════╣
║  [F] Free Cam | W/A/S/D Q/E SHIFT | Scroll Kota<->Angkasa       ║
║  SPACE (tahan) Percepat x5 | R Reset | ESC Keluar               ║
╚══════════════════════════════════════════════════════════════════╝
"""

import math, random, sys, time

try:
    import pygame
    from pygame.locals import *
    from OpenGL.GL import *
    from OpenGL.GLU import *
except ImportError:
    print("pip install PyOpenGL PyOpenGL_accelerate pygame numpy")
    sys.exit(1)

# ══════════════════════════════════════════════════════════════════
#  KONSTANTA
# ══════════════════════════════════════════════════════════════════

WIDTH, HEIGHT   = 1280, 720
FPS             = 60
TITLE           = "Simulasi Gerhana 3D v5-Fixed"

SKY_DAY         = (0.38, 0.68, 0.92)
SKY_DUSK_EARLY  = (0.80, 0.45, 0.20)
SKY_DUSK_MID    = (0.35, 0.10, 0.18)
SKY_NIGHT       = (0.01, 0.01, 0.05)
FOG_DAY         = (0.50, 0.75, 0.92)
FOG_DUSK        = (0.38, 0.18, 0.12)
FOG_NIGHT       = (0.00, 0.00, 0.03)

ECLIPSE_CYCLE   = 55.0
LUNAR_CYCLE     = 75.0

# Matahari di langit kota — jauh di belakang, tinggi, besar
SUN_ORBIT_R_H   = 260.0    # radius horizontal orbit
SUN_ORBIT_R_V   = 160.0    # radius vertikal orbit
SUN_SPEED       = 0.018    # rad/s
SUN_R           = 55.0     # radius disk matahari (besar & jelas)
MOON_R_CITY     = 30.0     # radius disk bulan di kota (besar & jelas)
SUN_DIST        = -900.0   # jarak matahari dari kamera (jauh di belakang)

# Scene luar angkasa
EARTH_ORBIT_R   = 500.0
EARTH_ORBIT_SPD = 0.012
MOON_ORBIT_R    = 110.0
MOON_ORBIT_SPD  = 0.09

# ══════════════════════════════════════════════════════════════════
#  UTILITAS
# ══════════════════════════════════════════════════════════════════

def lerp(a, b, t):      return a + (b - a) * t
def lerp3(c1, c2, t):   return tuple(lerp(a, b, t) for a, b in zip(c1, c2))
def clamp(v, lo, hi):   return max(lo, min(hi, v))
def smoothstep(t):
    t = clamp(t, 0, 1); return t * t * (3 - 2*t)
def smootherstep(t):
    t = clamp(t, 0, 1); return t*t*t*(t*(t*6-15)+10)
def ease_sine(t):
    return -(math.cos(math.pi * clamp(t, 0, 1)) - 1) / 2

# ══════════════════════════════════════════════════════════════════
#  GL PRIMITIF — TANPA GL_COLOR_MATERIAL (fix warna gedung)
# ══════════════════════════════════════════════════════════════════

def set_mat(r, g, b, spec=0.3, shin=40, emit=(0,0,0)):
    """Set material OpenGL. Tidak bergantung pada glColor."""
    glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT,  [r*0.35, g*0.35, b*0.35, 1.0])
    glMaterialfv(GL_FRONT_AND_BACK, GL_DIFFUSE,  [r, g, b, 1.0])
    glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, [spec]*3 + [1.0])
    glMaterialf (GL_FRONT_AND_BACK, GL_SHININESS, shin)
    glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, list(emit) + [1.0])

def draw_box(cx, cy, cz, sx, sy, sz, color, shininess=35, spec=0.3, emit=(0,0,0)):
    r, g, b = color
    set_mat(r, g, b, spec=spec, shin=shininess, emit=emit)
    hx, hy, hz = sx/2, sy/2, sz/2
    glPushMatrix(); glTranslatef(cx, cy, cz)
    glBegin(GL_QUADS)
    for nx, ny, nz, verts in [
        ( 0, 1, 0, [(-hx, hy,-hz),( hx, hy,-hz),( hx, hy, hz),(-hx, hy, hz)]),
        ( 0,-1, 0, [(-hx,-hy, hz),( hx,-hy, hz),( hx,-hy,-hz),(-hx,-hy,-hz)]),
        ( 0, 0, 1, [(-hx,-hy, hz),( hx,-hy, hz),( hx, hy, hz),(-hx, hy, hz)]),
        ( 0, 0,-1, [(-hx, hy,-hz),( hx, hy,-hz),( hx,-hy,-hz),(-hx,-hy,-hz)]),
        (-1, 0, 0, [(-hx,-hy,-hz),(-hx,-hy, hz),(-hx, hy, hz),(-hx, hy,-hz)]),
        ( 1, 0, 0, [( hx,-hy, hz),( hx,-hy,-hz),( hx, hy,-hz),( hx, hy, hz)]),
    ]:
        glNormal3f(nx, ny, nz)
        for v in verts: glVertex3f(*v)
    glEnd(); glPopMatrix()
    glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, [0,0,0,1])

def draw_sphere_lit(cx, cy, cz, radius, sl=24, st=12,
                    color=(1,1,1), emit=(0,0,0), shin=50, spec=0.6):
    """Sphere dengan lighting penuh."""
    r, g, b = color
    set_mat(r, g, b, spec=spec, shin=shin, emit=emit)
    glPushMatrix(); glTranslatef(cx, cy, cz)
    q = gluNewQuadric(); gluQuadricNormals(q, GLU_SMOOTH)
    gluSphere(q, radius, sl, st); gluDeleteQuadric(q)
    glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, [0,0,0,1])
    glPopMatrix()

def draw_cylinder(cx, cy, cz, br, tr, h, sl=12, color=(0.5,0.5,0.5)):
    r, g, b = color; set_mat(r, g, b, spec=0.1, shin=10)
    glPushMatrix(); glTranslatef(cx, cy, cz)
    q = gluNewQuadric()
    gluCylinder(q, br, tr, h, sl, 1)
    gluDisk(q, 0, br, sl, 1)
    glTranslatef(0, 0, h); gluDisk(q, 0, tr, sl, 1)
    gluDeleteQuadric(q); glPopMatrix()

def raw_sphere(cx, cy, cz, r, sl=16, st=10):
    """Sphere TANPA material — pakai glColor4f sebelum memanggil ini."""
    glPushMatrix(); glTranslatef(cx, cy, cz)
    q = gluNewQuadric(); gluSphere(q, r, sl, st); gluDeleteQuadric(q)
    glPopMatrix()

# ══════════════════════════════════════════════════════════════════
#  MATAHARI DI LANGIT KOTA
#  FIX: digambar di AWAL frame dengan depth test DIMATIKAN
#  sehingga selalu terlihat di belakang semua objek kota
# ══════════════════════════════════════════════════════════════════

def draw_city_sun(sx, sy, sz, solar_t, dark_t, sim_time):
    """
    Gambar matahari di langit — HARUS dipanggil sebelum objek kota,
    dengan GL_DEPTH_TEST nonaktif agar selalu tampak di 'langit'.
    """
    base_bright = max(0.0, 1.0 - dark_t * 0.88)
    if base_bright < 0.01 and solar_t < 0.1:
        return

    # Warna matahari: kuning terang → oranye gelap saat gerhana
    sr = lerp(1.00, 0.92, solar_t)
    sg = lerp(0.98, 0.45, solar_t)
    sb = lerp(0.72, 0.06, solar_t)

    # Nonaktifkan depth test dan lighting untuk layer langit
    glDisable(GL_DEPTH_TEST)
    glDisable(GL_LIGHTING)
    glEnable(GL_BLEND)

    # ── HALO berlapis (additive blend) ────────────────────────────
    glBlendFunc(GL_SRC_ALPHA, GL_ONE)
    halo_data = [
        (SUN_R * 9.0,  0.008), (SUN_R * 7.0,  0.015),
        (SUN_R * 5.2,  0.030), (SUN_R * 3.8,  0.058),
        (SUN_R * 2.8,  0.095), (SUN_R * 2.1,  0.145),
        (SUN_R * 1.65, 0.210), (SUN_R * 1.30, 0.280),
    ]
    for rr, aa in halo_data:
        fade = rr / (SUN_R * 9.0)
        gc   = sg * lerp(0.50, 0.95, fade)
        bc   = sb * lerp(0.18, 0.65, fade)
        glColor4f(sr, gc, bc, aa * base_bright)
        raw_sphere(sx, sy, sz, rr, 16, 10)

    # ── SINAR berputar (24 sinar: 12 panjang + 12 pendek) ─────────
    if dark_t < 0.90 and base_bright > 0.03:
        ray_alpha = base_bright * (1.0 - solar_t * 0.78) * 0.62
        ray_len   = SUN_R * lerp(6.0, 1.5, solar_t)
        ray_w     = SUN_R * 0.20
        rot       = sim_time * 3.5

        glBlendFunc(GL_SRC_ALPHA, GL_ONE)

        for i in range(12):
            ang = math.radians(i * 30 + rot)
            ox  = math.cos(ang) * SUN_R * 1.10
            oy  = math.sin(ang) * SUN_R * 1.10
            ex2 = sx + math.cos(ang) * (SUN_R * 1.10 + ray_len)
            ey2 = sy + math.sin(ang) * (SUN_R * 1.10 + ray_len)
            pw  = math.cos(ang + math.pi/2) * ray_w * 0.5
            ph  = math.sin(ang + math.pi/2) * ray_w * 0.5

            glBegin(GL_TRIANGLES)
            glColor4f(sr, sg, sb * 0.5, ray_alpha)
            glVertex3f(sx + ox - pw, sy + oy - ph, sz)
            glVertex3f(sx + ox + pw, sy + oy + ph, sz)
            glColor4f(sr, sg * 0.3, 0.0, 0.0)
            glVertex3f(ex2, ey2, sz)
            glEnd()

        # Sinar pendek di antara sinar panjang
        for i in range(12):
            ang  = math.radians(i * 30 + 15 + rot * 0.65)
            rl2  = ray_len * 0.42
            ox   = math.cos(ang) * SUN_R * 1.10
            oy   = math.sin(ang) * SUN_R * 1.10
            ex2  = sx + math.cos(ang) * (SUN_R * 1.10 + rl2)
            ey2  = sy + math.sin(ang) * (SUN_R * 1.10 + rl2)
            pw   = math.cos(ang + math.pi/2) * ray_w * 0.28
            ph   = math.sin(ang + math.pi/2) * ray_w * 0.28
            glBegin(GL_TRIANGLES)
            glColor4f(sr, sg, sb * 0.4, ray_alpha * 0.52)
            glVertex3f(sx + ox - pw, sy + oy - ph, sz)
            glVertex3f(sx + ox + pw, sy + oy + ph, sz)
            glColor4f(1.0, 0.5, 0.1, 0.0)
            glVertex3f(ex2, ey2, sz)
            glEnd()

    glDisable(GL_BLEND)

    # ── DISK matahari solid ────────────────────────────────────────
    # Kembali aktifkan lighting untuk disk agar terlihat 3D
    glEnable(GL_LIGHTING)
    glEnable(GL_DEPTH_TEST)  # aktifkan kembali tapi disk di far-plane

    em_s = lerp(6.0, 0.15, solar_t) * base_bright
    draw_sphere_lit(sx, sy, sz, SUN_R, 32, 18,
                    color=(sr, sg, sb),
                    emit=(sr * em_s, sg * em_s * 0.85, sb * em_s * 0.30),
                    shin=5, spec=0.0)

    glDisable(GL_DEPTH_TEST)
    glDisable(GL_LIGHTING)
    glEnable(GL_BLEND)

    # ── KORONA gerhana ─────────────────────────────────────────────
    if solar_t > 0.38:
        ct = smoothstep((solar_t - 0.38) / 0.62)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)
        for rr, aa, cg, cb in [
            (SUN_R * 1.65, 0.35 * ct, sg * 0.65, sb * 0.12),
            (SUN_R * 2.00, 0.26 * ct, sg * 0.48, sb * 0.06),
            (SUN_R * 2.50, 0.18 * ct, sg * 0.32, 0.03),
            (SUN_R * 3.20, 0.10 * ct, sg * 0.20, 0.00),
            (SUN_R * 4.20, 0.05 * ct, sg * 0.12, 0.00),
        ]:
            glColor4f(sr, cg, cb, aa)
            raw_sphere(sx, sy, sz, rr, 22, 14)

        # Cincin kilat berputar
        if solar_t > 0.60:
            ft   = smoothstep((solar_t - 0.60) / 0.40)
            rot2 = sim_time * 0.20
            for i in range(16):
                ang    = math.radians(i * 22.5 + rot2 * 57.3)
                r_off  = SUN_R * lerp(1.68, 1.76, 0.5 + 0.5 * math.sin(sim_time * 1.7 + i))
                fr_r   = SUN_R * lerp(0.08, 0.16, ft)
                glColor4f(1.0, sg * 0.55, 0.02, 0.24 * ft)
                raw_sphere(sx + math.cos(ang)*r_off,
                           sy + math.sin(ang)*r_off,
                           sz, fr_r, 8, 5)

        # PROMINENSI plasma merah
        if solar_t > 0.62:
            pt = smoothstep((solar_t - 0.62) / 0.38)
            for i in range(10):
                ang   = i * (math.pi / 5) + sim_time * 0.14
                plen  = SUN_R * (lerp(0.60, 1.15, pt) + 0.28 * math.sin(sim_time * 2.0 + i))
                hw    = SUN_R * 0.13
                px_b  = sx + math.cos(ang) * SUN_R * 1.06
                py_b  = sy + math.sin(ang) * SUN_R * 1.06
                px_t  = sx + math.cos(ang) * (SUN_R * 1.06 + plen)
                py_t  = sy + math.sin(ang) * (SUN_R * 1.06 + plen)
                ppx   = math.cos(ang + math.pi/2) * hw
                ppy   = math.sin(ang + math.pi/2) * hw
                glBegin(GL_TRIANGLES)
                glColor4f(1.00, 0.28, 0.04, 0.75 * pt)
                glVertex3f(px_b - ppx, py_b - ppy, sz)
                glVertex3f(px_b + ppx, py_b + ppy, sz)
                glColor4f(1.00, 0.62, 0.12, 0.0)
                glVertex3f(px_t, py_t, sz)
                glEnd()
                if pt > 0.5:
                    for bdir in (-1, 1):
                        ba  = ang + bdir * 0.42
                        bl  = plen * 0.35
                        bx2 = px_t + math.cos(ba) * bl
                        by2 = py_t + math.sin(ba) * bl
                        bw2 = hw * 0.40
                        bpx = math.cos(ba + math.pi/2) * bw2
                        bpy = math.sin(ba + math.pi/2) * bw2
                        glBegin(GL_TRIANGLES)
                        glColor4f(1.0, 0.35, 0.06, 0.42 * pt)
                        glVertex3f(px_t - bpx, py_t - bpy, sz)
                        glVertex3f(px_t + bpx, py_t + bpy, sz)
                        glColor4f(1.0, 0.65, 0.15, 0.0)
                        glVertex3f(bx2, by2, sz)
                        glEnd()

    # Diamond ring effect
    if 0.84 < solar_t < 0.99:
        dr_t = smoothstep((solar_t - 0.84) / 0.15)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)
        glColor4f(1.0, 0.98, 0.92, 0.92 * dr_t)
        raw_sphere(sx + SUN_R * 0.97, sy + SUN_R * 0.12, sz, SUN_R * 0.20, 12, 8)
        glColor4f(1.0, 0.95, 0.85, 0.52 * dr_t)
        raw_sphere(sx + SUN_R * 0.97, sy + SUN_R * 0.12, sz, SUN_R * 0.48, 10, 6)

    glDisable(GL_BLEND)
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)


# ══════════════════════════════════════════════════════════════════
#  BULAN DI LANGIT KOTA
#  FIX: selalu terlihat, tidak perlu dark_t tinggi, ukuran besar
# ══════════════════════════════════════════════════════════════════

def draw_city_moon(mx, my, mz, lunar_t, dark_t, solar_t, sim_time):
    """
    Bulan di langit kota:
    - Terlihat dari awal (vis = 0.35 + dark_t * 0.65)
    - Disk abu besar dengan halo dan kawah
    - Merah saat gerhana bulan
    - Saat gerhana matahari: siluet hitam bergerak di depan matahari
    """
    # Bulan selalu ada setidaknya sedikit terlihat
    vis = clamp(0.30 + dark_t * 0.70, 0.30, 1.0)

    # Warna bulan
    mc = lerp3((0.92, 0.90, 0.84), (0.72, 0.16, 0.06), lunar_t)

    # Gambar di layer langit (depth test off)
    glDisable(GL_DEPTH_TEST)
    glDisable(GL_LIGHTING)
    glEnable(GL_BLEND)

    # ── HALO bulan ────────────────────────────────────────────────
    halo_col = lerp3((0.60, 0.70, 0.98), (0.85, 0.18, 0.06), lunar_t)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    for rr, aa in [
        (MOON_R_CITY * 4.5, 0.022), (MOON_R_CITY * 3.2, 0.045),
        (MOON_R_CITY * 2.4, 0.078), (MOON_R_CITY * 1.75, 0.120),
        (MOON_R_CITY * 1.32, 0.175),
    ]:
        glColor4f(halo_col[0], halo_col[1], halo_col[2], aa * vis)
        raw_sphere(mx, my, mz, rr, 14, 8)

    # Halo merah ekstra saat gerhana bulan
    if lunar_t > 0.12:
        lt = smoothstep(lunar_t)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)
        for rr, aa in [
            (MOON_R_CITY * 2.1, 0.22 * lt),
            (MOON_R_CITY * 1.55, 0.30 * lt),
            (MOON_R_CITY * 1.25, 0.22 * lt),
        ]:
            glColor4f(0.90, 0.12, 0.04, aa * vis)
            raw_sphere(mx, my, mz, rr, 14, 8)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    glDisable(GL_BLEND)

    # ── DISK bulan solid ──────────────────────────────────────────
    glEnable(GL_LIGHTING)
    glEnable(GL_DEPTH_TEST)

    # Emisi agar bulan terlihat jelas bahkan saat langit terang
    ambient_em = lerp(0.28, 0.05, dark_t) * vis
    lunar_em   = lerp(0.0, 0.80, lunar_t) * vis
    em_r = mc[0] * (ambient_em + lunar_em * mc[0])
    em_g = mc[1] * (ambient_em + lunar_em * mc[1])
    em_b = mc[2] * (ambient_em + lunar_em * mc[2])

    draw_sphere_lit(mx, my, mz, MOON_R_CITY, 28, 16,
                    color=mc,
                    emit=(em_r, em_g, em_b),
                    shin=22, spec=0.10)

    glDisable(GL_DEPTH_TEST)
    glDisable(GL_LIGHTING)
    glEnable(GL_BLEND)

    # ── TERMINATOR (sisi gelap bulan) ─────────────────────────────
    if lunar_t < 0.15:
        term_off = MOON_R_CITY * lerp(0.32, 0.0, lunar_t / 0.15)
        term_al  = lerp(0.68, 0.0, lunar_t / 0.15) * vis
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glColor4f(0.0, 0.0, 0.02, term_al)
        raw_sphere(mx - term_off, my, mz, MOON_R_CITY * 1.06, 22, 12)

    # ── KAWAH bulan ───────────────────────────────────────────────
    cr_col = lerp3((0.55, 0.52, 0.48), (0.42, 0.09, 0.04), lunar_t)
    craters = [
        (0.42, 0.28, 0.22), (-0.28, 0.38, 0.16),
        (0.18, -0.32, 0.19), (-0.38, -0.20, 0.14),
        (0.52, -0.14, 0.12),
    ]
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    for fx, fy, fr in craters:
        depth = math.sqrt(max(0, 1.0 - fx*fx - fy*fy))
        cx2   = mx + fx * MOON_R_CITY
        cy2   = my + fy * MOON_R_CITY
        cz2   = mz + depth * MOON_R_CITY * 0.88
        cr    = fr * MOON_R_CITY
        glColor4f(cr_col[0], cr_col[1], cr_col[2], 0.32 * vis)
        raw_sphere(cx2, cy2, cz2, cr, 10, 6)
        glColor4f(min(cr_col[0]*1.35,1), min(cr_col[1]*1.25,1),
                  min(cr_col[2]*1.2,1), 0.18 * vis)
        raw_sphere(cx2, cy2, cz2, cr * 1.20, 8, 5)

    glDisable(GL_BLEND)
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)


# ══════════════════════════════════════════════════════════════════
#  SILUET BULAN DI DEPAN MATAHARI (gerhana matahari)
# ══════════════════════════════════════════════════════════════════

def draw_moon_over_sun(sx, sy, sz, solar_t, sim_time):
    """Disk hitam bulan yang menutupi matahari saat gerhana solar."""
    if solar_t < 0.32:
        return
    ct = smoothstep((solar_t - 0.32) / 0.68)

    # Bulan bergerak dari kanan ke tengah matahari
    offset   = lerp(SUN_R * 2.4, 0.0, ct)
    vert_off = SUN_R * 0.08 * math.sin(sim_time * 0.035)
    bx = sx + offset
    by = sy + vert_off
    bz = sz

    sil_r = MOON_R_CITY * lerp(1.8, 2.5, ct)

    glDisable(GL_DEPTH_TEST)
    glDisable(GL_LIGHTING)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    # Disk hitam utama
    glColor4f(0.0, 0.0, 0.01, clamp(ct * 1.5, 0, 1))
    raw_sphere(bx, by, bz, sil_r, 26, 16)

    # Tepi reddish dari korona
    glBlendFunc(GL_SRC_ALPHA, GL_ONE)
    glColor4f(0.22, 0.04, 0.01, 0.20 * ct)
    raw_sphere(bx, by, bz, sil_r * 1.10, 22, 14)

    glDisable(GL_BLEND)
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_LIGHTING)


# ══════════════════════════════════════════════════════════════════
#  GEDUNG — WARNA PENUH (fix GL_COLOR_MATERIAL)
# ══════════════════════════════════════════════════════════════════

class Building:
    # 8 palet warna cerah dan berbeda
    PALETTE = [
        ((0.80, 0.64, 0.42), (0.95, 0.84, 0.58), (1.00, 0.78, 0.28)),  # krem/emas
        ((0.28, 0.42, 0.68), (0.42, 0.58, 0.85), (0.60, 0.88, 1.00)),  # biru baja
        ((0.68, 0.28, 0.28), (0.82, 0.44, 0.38), (1.00, 0.58, 0.42)),  # merah bata
        ((0.28, 0.55, 0.36), (0.40, 0.72, 0.50), (0.62, 1.00, 0.62)),  # hijau sage
        ((0.55, 0.38, 0.68), (0.70, 0.52, 0.88), (0.92, 0.72, 1.00)),  # ungu lavender
        ((0.22, 0.40, 0.55), (0.35, 0.55, 0.72), (0.52, 0.82, 1.00)),  # teal
        ((0.68, 0.50, 0.28), (0.85, 0.66, 0.38), (1.00, 0.84, 0.42)),  # oranye tua
        ((0.38, 0.38, 0.45), (0.56, 0.56, 0.62), (0.80, 0.88, 0.98)),  # abu kaca
    ]
    TYPES = ['tower', 'slab', 'stepped', 'tapered']

    def __init__(self, x, z, w, d, h):
        self.x = x; self.z = z
        self.w = w; self.d = d; self.h = h
        p = random.choice(self.PALETTE)
        self.cl = p[0]   # dinding utama
        self.ch = p[1]   # aksen atas
        self.ca = p[2]   # pita horizontal
        self.btype = random.choice(self.TYPES)
        self.windows = []
        rows = max(2, int(h / 5.5))
        cols = max(2, int(w / 3.8))
        for row in range(rows):
            for col in range(cols):
                wx  = -w/2 + (col + 0.5) * (w/cols) + random.uniform(-0.25, 0.25)
                wy  = 2.5 + row * (h - 4) / max(rows - 1, 1)
                lit = random.random() > 0.32
                flk = random.random() > 0.82
                fp  = random.random() * 6.28
                self.windows.append((wx, wy, lit, flk, fp))
        self.has_ant  = h > 58 and random.random() > 0.38
        self.has_sign = h > 40 and random.random() > 0.55

    def draw(self, dark_t, sim_time=0.0):
        h = self.h
        cl = lerp3(self.cl, tuple(x * 0.22 for x in self.cl), dark_t)
        ch = lerp3(self.ch, tuple(x * 0.18 for x in self.ch), dark_t)
        ca = lerp3(self.ca, tuple(x * 0.16 for x in self.ca), dark_t)

        if   self.btype == 'slab':    self._slab(cl, ch, ca, dark_t)
        elif self.btype == 'stepped': self._stepped(cl, ch, ca)
        elif self.btype == 'tapered': self._tapered(cl, ch, ca, dark_t)
        else:                         self._tower(cl, ch, ca, dark_t)

        for frac in [0.33, 0.66, 1.0]:
            draw_box(self.x, frac*h, self.z, self.w+0.55, 0.65, self.d+0.55, ca, 62, 0.55)

        if self.has_ant:
            draw_cylinder(self.x, h, self.z, 0.18, 0.10, 14, 6,
                          lerp3((0.58,0.58,0.62), (0.18,0.18,0.22), dark_t))
            ant_em = lerp3((0,0,0), (1.0,0.10,0.10), clamp(dark_t*2, 0, 1))
            draw_sphere_lit(self.x, h+14.5, self.z, 0.45, 8, 6,
                            (0.90,0.10,0.10), ant_em, 20)

        if self.has_sign and dark_t > 0.08:
            sign_em = lerp3((0,0,0), self.ca, clamp(dark_t * 2.5, 0, 1))
            draw_box(self.x + self.w*0.5 + 0.8, h*0.72, self.z,
                     0.15, 5.5, self.d*0.55, self.ca, 15, 0.1, emit=sign_em)

        if dark_t > 0.08:
            for wx, wy, lit, flk, fp in self.windows:
                if not lit: continue
                fl = (0.85 + 0.15 * math.sin(sim_time * 5.8 + fp)) if flk else 1.0
                intensity = smoothstep(dark_t) * lerp(0.65, 1.0, random.random()) * fl
                wc  = lerp3((0,0,0), (1.00, 0.96, 0.68), intensity) \
                      if sum(self.ca) > 2.1 \
                      else lerp3((0,0,0), (0.72, 0.90, 1.00), intensity)
                em2 = wc if intensity > 0.42 else (0,0,0)
                for dz_off in [self.d/2 + 0.08, -self.d/2 - 0.08]:
                    draw_box(self.x + wx, wy, self.z + dz_off,
                             1.05, 1.25, 0.13, wc, 4, 0.0, emit=em2)

    def _tower(self, cl, ch, ca, dt):
        draw_box(self.x, self.h/2, self.z, self.w, self.h, self.d, cl, 40)
        gc = lerp3((0.42,0.58,0.82), (0.04,0.04,0.14), dt)
        draw_box(self.x, self.h/2, self.z,
                 self.w+0.18, self.h+0.12, self.d+0.18, gc, 96, 0.72)

    def _slab(self, cl, ch, ca, dt):
        h = self.h
        draw_box(self.x, h*0.425, self.z, self.w*1.65, h*0.85, self.d*0.60, cl, 35)
        draw_box(self.x, h*0.925, self.z, self.w*0.90, h*0.15, self.d*0.60, ch, 50)
        gc = lerp3((0.48,0.64,0.84), (0.04,0.04,0.12), dt)
        draw_box(self.x, h*0.425, self.z,
                 self.w*1.65+0.22, h*0.85, self.d*0.60+0.22, gc, 92, 0.68)

    def _stepped(self, cl, ch, ca):
        h = self.h
        draw_box(self.x, h*0.30, self.z, self.w,        h*0.60, self.d,        cl, 35)
        draw_box(self.x, h*0.70, self.z, self.w*0.70,   h*0.40, self.d*0.70,   ch, 46)
        draw_box(self.x, h*0.92, self.z, self.w*0.40,   h*0.16, self.d*0.40,   ca, 56)

    def _tapered(self, cl, ch, ca, dt):
        h = self.h
        draw_box(self.x, h*0.25, self.z, self.w,        h*0.50, self.d,        cl, 35)
        draw_box(self.x, h*0.65, self.z, self.w*0.75,   h*0.30, self.d*0.75,   ch, 46)
        draw_box(self.x, h*0.87, self.z, self.w*0.45,   h*0.24, self.d*0.45,   ca, 56)
        draw_cylinder(self.x, h, self.z, self.w*0.14, 0.0, h*0.14, 8,
                      lerp3(ca, (0.18,0.18,0.18), dt))


# ══════════════════════════════════════════════════════════════════
#  KENDARAAN
# ══════════════════════════════════════════════════════════════════

class Car:
    COLORS = [
        (0.92, 0.12, 0.12), (0.12, 0.32, 0.92), (0.10, 0.80, 0.22),
        (0.98, 0.80, 0.08), (0.96, 0.96, 0.96), (0.10, 0.10, 0.10),
        (0.80, 0.28, 0.92), (0.98, 0.52, 0.08), (0.08, 0.80, 0.85),
        (0.98, 0.32, 0.58), (0.42, 0.72, 0.22), (0.88, 0.72, 0.42),
    ]
    ROOF = [
        (0.70,0.06,0.06),(0.06,0.20,0.72),(0.06,0.60,0.14),
        (0.80,0.62,0.04),(0.72,0.72,0.72),(0.22,0.22,0.22),
        (0.60,0.14,0.72),(0.78,0.34,0.04),(0.04,0.62,0.66),
        (0.78,0.18,0.42),(0.28,0.56,0.12),(0.68,0.54,0.28),
    ]

    def __init__(self, x, z, direction):
        self.x = x; self.z = z; self.direction = direction
        self.speed   = random.uniform(0.20, 0.50)
        idx          = random.randint(0, len(self.COLORS)-1)
        self.color   = self.COLORS[idx]
        self.roof_c  = self.ROOF[idx]
        self.stopped = False
        self.w = 1.8; self.h = 1.25; self.l = 4.0
        self._angle  = {'px':0,'nx':180,'pz':90,'nz':-90}[direction]
        self._wr     = 0.0

    def update(self, dt, tls):
        self.stopped = self._chk(tls)
        if not self.stopped:
            spd = self.speed * 20 * dt
            self._wr = (self._wr + spd * 28) % 360
            if   self.direction == 'px': self.x += spd; self.x = self.x if self.x < 220 else -220
            elif self.direction == 'nx': self.x -= spd; self.x = self.x if self.x > -220 else 220
            elif self.direction == 'pz': self.z += spd; self.z = self.z if self.z < 220 else -220
            elif self.direction == 'nz': self.z -= spd; self.z = self.z if self.z > -220 else 220

    def _chk(self, tls):
        for ix in [0,100,-100]:
            for iz in [0,100,-100]:
                if self.direction in ('px','nx'):
                    dx = ix - self.x
                    if 2 < abs(dx) < 12 and abs(self.z-iz) < 10:
                        if (self.direction=='px' and dx>0) or (self.direction=='nx' and dx<0):
                            tl = next((t for t in tls if math.sqrt((t.x-ix)**2+(t.z-iz)**2)<20),None)
                            if tl and tl.state != 'green': return True
                else:
                    dz = iz - self.z
                    if 2 < abs(dz) < 12 and abs(self.x-ix) < 10:
                        if (self.direction=='pz' and dz>0) or (self.direction=='nz' and dz<0):
                            tl = next((t for t in tls if math.sqrt((t.x-ix)**2+(t.z-iz)**2)<20),None)
                            if tl and tl.state != 'green': return True
        return False

    def draw(self, dark_t):
        glPushMatrix(); glTranslatef(self.x, 0, self.z); glRotatef(self._angle, 0, 1, 0)
        c  = self.color; rc = self.roof_c
        draw_box(0, 0.625, 0, self.l, self.h, self.w, c, 62)
        draw_box(0, 1.42, 0, self.l*0.60, 0.72, self.w*0.88, (0.06,0.10,0.20), 92, 0.75)
        draw_box(0, 0.90, 0, self.l+0.02, 0.18, self.w+0.02, rc, 40, 0.4)
        draw_box( self.l/2+0.06, 0.38, 0, 0.20, 0.52, self.w*0.72,
                 lerp3(c,(0.14,0.14,0.14),0.55), 22)
        draw_box(-self.l/2-0.06, 0.38, 0, 0.20, 0.52, self.w*0.72,
                 lerp3(c,(0.14,0.14,0.14),0.55), 22)
        hl_em = lerp3((0,0,0), (1.00,0.98,0.88), clamp(dark_t*3.5, 0, 1))
        for sz in (-0.62, 0.62):
            draw_box(self.l/2+0.08, 0.68, sz, 0.11, 0.34, 0.40,
                     (1.00,0.98,0.90), 8, 0.1, emit=hl_em)
        bc   = (1.00,0.08,0.05) if self.stopped else (0.52,0.0,0.0)
        b_em = lerp3((0,0,0), bc, clamp(dark_t*2.5, 0, 1))
        for sz in (-0.62, 0.62):
            draw_box(-self.l/2-0.08, 0.68, sz, 0.11, 0.30, 0.35, bc, 8, 0.0, emit=b_em)
        for wx, wz in [(1.22,0.96),(1.22,-0.96),(-1.22,0.96),(-1.22,-0.96)]:
            glPushMatrix(); glTranslatef(wx, 0.14, wz)
            glRotatef(90, 0, 1, 0); glRotatef(self._wr, 1, 0, 0)
            draw_cylinder(0, 0, -0.09, 0.30, 0.30, 0.18, 12, (0.09,0.09,0.09))
            draw_cylinder(0, 0, -0.04, 0.18, 0.18, 0.10,  8, (0.58,0.58,0.64))
            glPopMatrix()
        glPopMatrix()


# ══════════════════════════════════════════════════════════════════
#  LAMPU LALU LINTAS
# ══════════════════════════════════════════════════════════════════

class TrafficLight:
    PHASES = [('green',4.0),('yellow',1.2),('red',3.5)]
    def __init__(self, x, z, offset=0.0):
        self.x = x; self.z = z; self.state = 'green'; self._pi = 0
        self._t = offset % 8.7; acc = 0
        for i,(s,d) in enumerate(self.PHASES):
            acc += d
            if self._t < acc: self._pi=i; self._t-=(acc-d); self.state=s; break
    def update(self, dt):
        self._t += dt
        if self._t >= self.PHASES[self._pi][1]:
            self._t -= self.PHASES[self._pi][1]
            self._pi = (self._pi+1)%3; self.state = self.PHASES[self._pi][0]
    def draw(self):
        draw_cylinder(self.x, 0, self.z, 0.16, 0.16, 10, 8, (0.12,0.12,0.12))
        draw_box(self.x, 11, self.z, 0.85, 3.0, 0.72, (0.06,0.06,0.06))
        for y,bc,sn in [(12.3,(0.7,0,0),'red'),(11.0,(0.6,0.5,0),'yellow'),(9.7,(0,0.6,0),'green')]:
            em = bc if self.state==sn else (0,0,0)
            draw_sphere_lit(self.x, y, self.z-0.04, 0.30, 10, 7, bc, em, 20)


# ══════════════════════════════════════════════════════════════════
#  KOTA
# ══════════════════════════════════════════════════════════════════

class City:
    def __init__(self):
        self.buildings=[]; self.tls=[]; self.cars=[]; self.lamps=[]; self._build()

    def _build(self):
        random.seed(42)
        zones=[
            (-75,-75,14,38,38,1.25),(75,-75,14,38,38,1.05),(-75,75,14,38,38,1.15),(75,75,14,38,38,1.35),
            (-155,0,9,28,55,0.90),(155,0,9,28,55,0.90),(0,-155,9,55,28,0.82),(0,155,9,55,28,0.82),
            (-75,0,4,20,20,0.70),(75,0,4,20,20,0.70),(0,-75,4,20,20,0.70),(0,75,4,20,20,0.70),
        ]
        for cx,cz,cnt,sx,sz,sc in zones:
            for _ in range(cnt):
                bw=random.uniform(9,20)*sc; bd=random.uniform(9,20)*sc; bh=random.uniform(25,115)*sc
                bx=cx+random.uniform(-sx,sx); bz=cz+random.uniform(-sz,sz)
                if abs(bx)<15 or abs(bz)<15: continue
                if abs(abs(bx)-100)<15 or abs(abs(bz)-100)<15: continue
                self.buildings.append(Building(bx,bz,bw,bd,bh))
        for ix in [0,100,-100]:
            for iz in [0,100,-100]:
                for ox,oz in [(8,8),(-8,8),(8,-8),(-8,-8)]:
                    self.tls.append(TrafficLight(ix+ox,iz+oz,random.uniform(0,8.7)))
        for _ in range(16):
            self.cars+=[Car(random.uniform(-200,200),4.5,'px'),Car(random.uniform(-200,200),-4.5,'nx')]
        for _ in range(16):
            self.cars+=[Car(4.5,random.uniform(-200,200),'pz'),Car(-4.5,random.uniform(-200,200),'nz')]
        for zb in [96,104,-96,-104]:
            d='px' if zb>0 else 'nx'
            for _ in range(8): self.cars.append(Car(random.uniform(-200,200),zb,d))
        for xb in [96,104,-96,-104]:
            d='pz' if xb>0 else 'nz'
            for _ in range(8): self.cars.append(Car(xb,random.uniform(-200,200),d))
        for i in range(-20,21,4):
            for side in [-12,12]: self.lamps+=[(i*10,0,side),(side,0,i*10)]

    def update(self, dt):
        for tl in self.tls: tl.update(dt)
        for c  in self.cars: c.update(dt, self.tls)

    def draw(self, dark_t, sim_time=0.0):
        self._ground(dark_t)
        for b  in self.buildings: b.draw(dark_t, sim_time)
        for tl in self.tls:       tl.draw()
        for c  in self.cars:      c.draw(dark_t)
        self._lamps(dark_t)
        self._trees(dark_t)
        self._park(dark_t)

    def _ground(self, dt):
        rc=lerp3((0.17,0.17,0.17),(0.04,0.04,0.07),dt)
        wc=lerp3((0.38,0.34,0.28),(0.10,0.09,0.09),dt)
        gc=lerp3((0.20,0.42,0.16),(0.04,0.08,0.03),dt)
        mk=lerp3((0.92,0.88,0.10),(0.38,0.35,0.04),dt)
        draw_box(0,-0.5,0,520,1,520,gc,5)
        draw_box(0,0.02,0,28,0.1,28,lerp3((0.50,0.48,0.42),(0.12,0.11,0.10),dt),10)
        for zp in [0,100,-100]:
            draw_box(0,0.05,zp,450,0.12,22,rc,5)
            for xi in range(-22,23): draw_box(xi*20,0.07,zp,8,0.1,0.28,mk,4)
            for side in [-12,12]: draw_box(0,0.32,zp+side,450,0.65,4,wc,8)
        for xp in [0,100,-100]:
            draw_box(xp,0.05,0,22,0.12,450,rc,5)
            for zi in range(-22,23): draw_box(xp,0.07,zi*20,0.28,0.1,8,mk,4)
            for side in [-12,12]: draw_box(xp+side,0.32,0,4,0.65,450,wc,8)

    def _lamps(self, dt):
        pc=lerp3((0.22,0.22,0.24),(0.08,0.08,0.10),dt)
        em=lerp3((0,0,0),(1.00,0.95,0.72),clamp(dt*2.4,0,1))
        for lx,_,lz in self.lamps:
            draw_cylinder(lx,0,lz,0.14,0.14,8.5,8,pc)
            draw_box(lx+0.7,8.8,lz,1.4,0.14,0.14,pc)
            draw_sphere_lit(lx+1.2,9.1,lz,0.50,8,6,(0.94,0.90,0.65),em,10)

    def _trees(self, dt):
        tc=lerp3((0.38,0.23,0.10),(0.14,0.08,0.03),dt)
        lc=lerp3((0.16,0.52,0.14),(0.03,0.10,0.02),dt)
        fc=lerp3((0.92,0.50,0.62),(0.28,0.12,0.18),dt)
        for i,(lx,_,lz) in enumerate(self.lamps[::4]):
            tx,tz=lx+2.0,lz+2.0
            draw_cylinder(tx,0,tz,0.28,0.28,3.8,8,tc)
            draw_sphere_lit(tx,6.2,tz,2.5,10,8,lc,(0,0,0),10)
            if i%3==0: draw_sphere_lit(tx,7.2,tz,1.1,8,6,fc,(0,0,0),15)

    def _park(self, dt):
        gc=lerp3((0.18,0.50,0.12),(0.04,0.10,0.02),dt)
        draw_box(0,0.12,0,22,0.25,22,gc,5)
        draw_cylinder(0,0.38,0,4.5,4.5,0.4,16,lerp3((0.55,0.52,0.48),(0.15,0.14,0.13),dt))
        draw_sphere_lit(0,1.5,0,0.8,12,8,lerp3((0.52,0.62,0.80),(0.12,0.15,0.25),dt),(0,0,0),60)


# ══════════════════════════════════════════════════════════════════
#  SCENE LUAR ANGKASA
# ══════════════════════════════════════════════════════════════════

class SpaceScene:
    def __init__(self):
        random.seed(7)
        self.stars=[(random.uniform(-3000,3000),random.uniform(-3000,3000),
                     random.uniform(-3000,3000),random.uniform(0.5,1.0)) for _ in range(6000)]
        self.earth_angle=0.0; self.moon_angle=0.0; self.earth_tilt=23.5

    def update(self, dt, solar_t, lunar_t, speed_mul=1.0):
        self.earth_angle += EARTH_ORBIT_SPD * dt * speed_mul
        self.moon_angle  += MOON_ORBIT_SPD  * dt * speed_mul

    def get_positions(self):
        ex=EARTH_ORBIT_R*math.cos(self.earth_angle)
        ey=EARTH_ORBIT_R*math.sin(self.earth_angle)*0.06
        ez=EARTH_ORBIT_R*math.sin(self.earth_angle)
        inc=math.radians(5.1)
        mx=ex+MOON_ORBIT_R*math.cos(self.moon_angle)
        my=ey+MOON_ORBIT_R*math.sin(self.moon_angle)*math.sin(inc)
        mz=ez+MOON_ORBIT_R*math.sin(self.moon_angle)*math.cos(inc)
        return (ex,ey,ez),(mx,my,mz)

    def draw(self, solar_t, lunar_t, sim_time):
        ep,mp=self.get_positions(); ex,ey,ez=ep; mx,my,mz=mp
        glDisable(GL_LIGHTING); glPointSize(2.0); glBegin(GL_POINTS)
        for sx,sy,sz,br in self.stars:
            b=br*(0.80+0.20*math.sin(sim_time*1.5+sx*0.01))
            glColor3f(b,b,b*0.95); glVertex3f(sx,sy,sz)
        glEnd(); glEnable(GL_LIGHTING)
        si=4.0
        draw_sphere_lit(0,0,0,95,36,18,(1.0,0.95,0.42),(si,si*0.88,si*0.30),5)
        glDisable(GL_LIGHTING); glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA,GL_ONE)
        pulse=1.0+0.06*math.sin(sim_time*1.3)+0.03*math.sin(sim_time*2.7)
        base_ct=1.0-solar_t*0.5
        for rr,aa in [(130,0.090),(165,0.058),(205,0.035),(250,0.018)]:
            glColor4f(1.0,0.70,0.20,aa*base_ct*pulse); raw_sphere(0,0,0,rr,20,10)
        if solar_t>0.08:
            ct=smoothstep(solar_t)
            for rr,aa,cg,cb in [(115,0.16*ct,0.82,0.25),(155,0.11*ct,0.58,0.10),
                                 (200,0.07*ct,0.38,0.04),(255,0.040*ct,0.22,0.00)]:
                glColor4f(1.0,cg,cb,aa*pulse); raw_sphere(0,0,0,rr,20,10)
            if solar_t>0.70:
                pt=smoothstep((solar_t-0.70)/0.30)
                for i in range(8):
                    ang=i*(math.pi/4)+sim_time*0.15
                    px=105*math.cos(ang); pz=105*math.sin(ang)
                    pl=lerp(32,60,pt)+15*math.sin(sim_time*2.1+i)
                    glColor4f(1.0,0.35,0.05,0.42*pt)
                    glBegin(GL_TRIANGLES)
                    glVertex3f(px-5*math.sin(ang),0,pz+5*math.cos(ang))
                    glVertex3f(px+5*math.sin(ang),0,pz-5*math.cos(ang))
                    glColor4f(1.0,0.60,0.10,0.0)
                    glVertex3f(px+pl*math.cos(ang),0,pz+pl*math.sin(ang))
                    glEnd()
        glDisable(GL_BLEND); glEnable(GL_LIGHTING)
        glPushMatrix(); glTranslatef(ex,ey,ez)
        glRotatef(self.earth_tilt,0,0,1); glRotatef(sim_time*15,0,1,0)
        set_mat(0.10,0.35,0.75,spec=0.6,shin=90)
        q=gluNewQuadric(); gluQuadricNormals(q,GLU_SMOOTH); gluSphere(q,68,48,24); gluDeleteQuadric(q)
        glDisable(GL_LIGHTING); glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA)
        for lon,lat in [(20,10),(80,30),(-100,40),(-60,-15),(135,-25),(30,-20)]:
            glColor4f(0.18,0.52,0.14,0.72)
            glPushMatrix(); glRotatef(lon,0,1,0); glRotatef(lat,1,0,0)
            raw_sphere(0,0,0,69.8,12,8); glPopMatrix()
        glColor4f(0.95,0.97,1.0,0.28); raw_sphere(0,0,0,71.5,32,16)
        glColor4f(0.30,0.55,0.95,0.10); raw_sphere(0,0,0,74.0,24,12)
        glDisable(GL_BLEND); glEnable(GL_LIGHTING); glPopMatrix()
        mc=lerp3((0.82,0.80,0.74),(0.55,0.12,0.05),lunar_t)
        me=lerp3((0,0,0),(0.42,0.06,0.01),lunar_t)
        draw_sphere_lit(mx,my,mz,19,28,14,mc,me,20)
        glDisable(GL_LIGHTING); glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA)
        for i in range(5):
            ang=i*1.25; cx2=mx+12*math.cos(ang); cy2=my+5*math.sin(ang); cz2=mz+10*math.sin(ang*0.7)
            glColor4f(0.30,0.28,0.26,0.28); raw_sphere(cx2,cy2,cz2,4,8,5)
        glDisable(GL_BLEND); glEnable(GL_LIGHTING)
        if solar_t>0.05: self._solar_shadow(ex,ey,ez,mx,my,mz,solar_t)
        if lunar_t>0.05: self._lunar_shadow(ex,ey,ez,mx,my,mz,lunar_t)
        self._orbit_paths(ex,ey,ez)

    def _solar_shadow(self,ex,ey,ez,mx,my,mz,t):
        alpha=smoothstep(t)*0.62; sr=lerp(5,42,smoothstep(t))
        glDisable(GL_LIGHTING); glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA)
        shx=ex+(mx-ex)*0.9; shy=ey+(my-ey)*0.9; shz=ez+(mz-ez)*0.9
        glColor4f(0,0,0.02,alpha); glBegin(GL_TRIANGLE_FAN); glVertex3f(shx,shy,shz)
        for i in range(29):
            a=2*math.pi*i/28; glVertex3f(shx+sr*math.cos(a),shy+sr*0.3*math.sin(a),shz+sr*math.sin(a))
        glEnd()
        glColor4f(0,0,0,alpha*0.40); glBegin(GL_TRIANGLE_FAN); glVertex3f(mx,my,mz)
        for i in range(29):
            a=2*math.pi*i/28; glVertex3f(ex+sr*0.5*math.cos(a),ey+sr*0.14*math.sin(a),ez+sr*0.5*math.sin(a))
        glEnd()
        glDisable(GL_BLEND); glEnable(GL_LIGHTING)

    def _lunar_shadow(self,ex,ey,ez,mx,my,mz,t):
        alpha=smoothstep(t)*0.82
        glDisable(GL_LIGHTING); glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA)
        glColor4f(0.06,0.0,0.0,alpha*0.88); raw_sphere(mx,my,mz,20.5,20,12)
        glColor4f(0.32,0.04,0.02,alpha*0.42); raw_sphere(mx,my,mz,22.5,16,10)
        glColor4f(0,0,0,alpha*0.26); glBegin(GL_TRIANGLE_FAN); glVertex3f(ex,ey,ez)
        for i in range(21):
            a=2*math.pi*i/20; glVertex3f(mx+26*math.cos(a),my+10*math.sin(a),mz+26*math.sin(a))
        glEnd()
        glDisable(GL_BLEND); glEnable(GL_LIGHTING)

    def _orbit_paths(self,ex,ey,ez):
        glDisable(GL_LIGHTING); glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA)
        glColor4f(0.4,0.6,0.8,0.15); glBegin(GL_LINE_LOOP)
        for i in range(80):
            a=2*math.pi*i/80; glVertex3f(EARTH_ORBIT_R*math.cos(a),0,EARTH_ORBIT_R*math.sin(a))
        glEnd()
        glColor4f(0.7,0.7,0.75,0.12); glBegin(GL_LINE_LOOP)
        for i in range(60):
            a=2*math.pi*i/60; glVertex3f(ex+MOON_ORBIT_R*math.cos(a),ey,ez+MOON_ORBIT_R*math.sin(a))
        glEnd()
        glDisable(GL_BLEND); glEnable(GL_LIGHTING)


# ══════════════════════════════════════════════════════════════════
#  FREE CAMERA
# ══════════════════════════════════════════════════════════════════

class FreeCamera:
    def __init__(self):
        self.pos=[0.0,80.0,280.0]; self.yaw=180.0; self.pitch=-12.0
        self.speed=65.0; self.sens=0.17
    def apply(self):
        glLoadIdentity()
        y=math.radians(self.yaw); p=math.radians(self.pitch)
        fx=math.sin(y)*math.cos(p); fy=math.sin(p); fz=-math.cos(y)*math.cos(p)
        gluLookAt(*self.pos,self.pos[0]+fx,self.pos[1]+fy,self.pos[2]+fz,0,1,0)
    def update(self,dt,keys,mdx,mdy):
        self.yaw+=mdx*self.sens; self.pitch=clamp(self.pitch-mdy*self.sens,-89,89)
        y=math.radians(self.yaw); p=math.radians(self.pitch)
        fx=math.sin(y)*math.cos(p); fy=math.sin(p); fz=-math.cos(y)*math.cos(p)
        rx=math.cos(y); rz=math.sin(y)
        spd=self.speed*(5.0 if (keys[K_LSHIFT] or keys[K_RSHIFT]) else 1.0)*dt
        if keys[K_w]:  self.pos[0]+=fx*spd;self.pos[1]+=fy*spd;self.pos[2]+=fz*spd
        if keys[K_s]:  self.pos[0]-=fx*spd;self.pos[1]-=fy*spd;self.pos[2]-=fz*spd
        if keys[K_a]:  self.pos[0]-=rx*spd;self.pos[2]-=rz*spd
        if keys[K_d]:  self.pos[0]+=rx*spd;self.pos[2]+=rz*spd
        if keys[K_q]:  self.pos[1]-=spd
        if keys[K_e]:  self.pos[1]+=spd


# ══════════════════════════════════════════════════════════════════
#  ECLIPSE CONTROLLER
# ══════════════════════════════════════════════════════════════════

class EclipseController:
    PHASES=[('idle',0.28),('approach',0.24),('peak',0.20),('recede',0.28)]
    def __init__(self,dur,start='idle',frac=0.0):
        self.dur=dur
        self._names=[p[0] for p in self.PHASES]
        self._durs=[p[1]*dur for p in self.PHASES]
        self._pi=self._names.index(start)
        self._t=frac*self._durs[self._pi]
        self.intensity=0.0; self.boosted=False
    def update(self,dt):
        spd=5.0 if self.boosted else 1.0; self._t+=dt*spd
        while self._t>=self._durs[self._pi]:
            self._t-=self._durs[self._pi]; self._pi=(self._pi+1)%4
        t=self._t/self._durs[self._pi] if self._durs[self._pi]>0 else 0
        n=self._names[self._pi]
        if   n=='idle':     self.intensity=0.0
        elif n=='approach': self.intensity=ease_sine(t)
        elif n=='peak':     self.intensity=clamp(1.0+0.012*math.sin(self._t*4.1),0.95,1.05)
        elif n=='recede':   self.intensity=ease_sine(1.0-t)
        self.intensity=clamp(self.intensity,0.0,1.0)
    @property
    def phase(self): return self._names[self._pi]


# ══════════════════════════════════════════════════════════════════
#  SIMULASI UTAMA
# ══════════════════════════════════════════════════════════════════

class EclipseSimulation:
    def __init__(self):
        pygame.init(); pygame.display.set_caption(TITLE)
        self.screen = pygame.display.set_mode((WIDTH,HEIGHT), DOUBLEBUF|OPENGL)

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING); glEnable(GL_LIGHT0); glEnable(GL_LIGHT1)
        # KRITIS: matikan GL_COLOR_MATERIAL agar warna gedung dari set_mat bekerja benar
        glDisable(GL_COLOR_MATERIAL)
        glEnable(GL_NORMALIZE)
        glShadeModel(GL_SMOOTH)
        glEnable(GL_FOG); glFogi(GL_FOG_MODE, GL_LINEAR)
        glHint(GL_PERSPECTIVE_CORRECTION_HINT, GL_NICEST)

        glMatrixMode(GL_PROJECTION); glLoadIdentity()
        gluPerspective(58.0, WIDTH/HEIGHT, 0.5, 12000.0)
        glMatrixMode(GL_MODELVIEW)

        self.scroll_t=0.0; self.target_st=0.0
        self.solar_ctrl=EclipseController(ECLIPSE_CYCLE,'idle',0.0)
        self.lunar_ctrl=EclipseController(LUNAR_CYCLE,  'idle',0.38)
        self._ss=0.0; self._sl=0.0; self._sky=list(SKY_DAY)
        self.free_cam=False; self.fcam=FreeCamera()
        self.o_pitch=22.0; self.o_yaw=35.0; self.mouse_dn=False; self.last_m=(0,0)
        self.sim_time=0.0; self.sun_angle=0.3
        self.space_yaw=30.0; self.space_pitch=15.0
        self.city=City(); self.space=SpaceScene()
        self.font_b=pygame.font.SysFont('Arial',22,bold=True)
        self.font_s=pygame.font.SysFont('Arial',14)
        self.clock=pygame.time.Clock(); self.running=True; self._boost=False

    def _lights(self, dark_t, sun_pos=None):
        et=self._ss
        sr=lerp(1.0,0.72,et); sg=lerp(0.96,0.32,et); sb=lerp(0.86,0.12,et)
        bri=max(0.0, 1.0-dark_t*0.97)
        pos=list(sun_pos)+[0.0] if sun_pos else [300,500,200,0]
        glLightfv(GL_LIGHT0,GL_POSITION,pos)
        glLightfv(GL_LIGHT0,GL_DIFFUSE, [sr*bri,sg*bri,sb*bri,1])
        glLightfv(GL_LIGHT0,GL_AMBIENT, [max(0.02,0.22*(1-dark_t)),
                                          max(0.02,0.20*(1-dark_t)),
                                          max(0.04,0.26*(1-dark_t)),1])
        glLightfv(GL_LIGHT0,GL_SPECULAR,[sr*bri*0.5,sg*bri*0.5,sb*bri*0.4,1])
        glow=dark_t*0.35
        glLightfv(GL_LIGHT1,GL_POSITION,[0,1,0,0])
        glLightfv(GL_LIGHT1,GL_DIFFUSE, [glow*0.82,glow*0.65,glow*0.38,1])
        glLightfv(GL_LIGHT1,GL_AMBIENT, [0,0,0,1])

    def _fog(self, dark_t):
        fc=lerp3(FOG_DAY,FOG_DUSK,dark_t*2) if dark_t<0.5 \
           else lerp3(FOG_DUSK,FOG_NIGHT,(dark_t-0.5)*2)
        glFogfv(GL_FOG_COLOR, list(fc)+[1])
        glFogf(GL_FOG_START, lerp(265,88,dark_t))
        glFogf(GL_FOG_END,   lerp(760,385,dark_t))

    def _update(self, dt):
        self.sim_time+=dt; self.sun_angle+=SUN_SPEED*dt
        self.scroll_t+=(self.target_st-self.scroll_t)*min(1.0,dt*4.5)
        self.scroll_t=clamp(self.scroll_t,0.0,1.0)
        self.solar_ctrl.boosted=self._boost; self.lunar_ctrl.boosted=self._boost
        self.solar_ctrl.update(dt); self.lunar_ctrl.update(dt)
        sm=2.5
        self._ss+=(self.solar_ctrl.intensity-self._ss)*min(1.0,dt*sm)
        self._sl+=(self.lunar_ctrl.intensity-self._sl)*min(1.0,dt*sm)
        dt_raw=max(self._ss,self._sl)
        if dt_raw<0.35:   tgt=lerp3(SKY_DAY,SKY_DUSK_EARLY,dt_raw/0.35)
        elif dt_raw<0.65: tgt=lerp3(SKY_DUSK_EARLY,SKY_DUSK_MID,(dt_raw-0.35)/0.30)
        else:             tgt=lerp3(SKY_DUSK_MID,SKY_NIGHT,(dt_raw-0.65)/0.35)
        for i in range(3): self._sky[i]+=(tgt[i]-self._sky[i])*min(1.0,dt*1.2)
        self.space.update(dt,self._ss,self._sl,speed_mul=5.0 if self._boost else 1.0)
        self.city.update(dt)
        if self.free_cam:
            keys=pygame.key.get_pressed(); dx,dy=pygame.mouse.get_rel()
            self.fcam.update(dt,keys,dx,dy)

    def _dark_t(self): return max(self._ss,self._sl)

    def _sun_pos(self):
        """Posisi matahari di langit kota — orbit eliptik, selalu di atas horizon."""
        sa = self.sun_angle
        sx =  SUN_ORBIT_R_H * math.cos(sa)
        sy =  SUN_ORBIT_R_V * math.sin(sa)
        sz =  SUN_DIST   # jauh di belakang kota
        # Pastikan di atas horizon minimal 2x radius
        min_y = SUN_R * 2.2
        if sy < min_y:
            sy = min_y + abs(sy - min_y) * 0.25
        return sx, sy, sz

    def _cam_city(self):
        d=lerp(175.0,550.0,self.scroll_t); e=lerp(38.0,180.0,self.scroll_t)
        pr=math.radians(self.o_pitch); yr=math.radians(self.o_yaw)
        cx=d*math.cos(pr)*math.sin(yr); cz=d*math.cos(pr)*math.cos(yr)
        cy=e+d*math.sin(pr)*0.5
        glLoadIdentity(); gluLookAt(cx,cy,cz,0,lerp(18,70,self.scroll_t),0,0,1,0)

    def _cam_space(self):
        dist=900; pr=math.radians(self.space_pitch); yr=math.radians(self.space_yaw)
        cx=dist*math.cos(pr)*math.sin(yr); cy=dist*math.sin(pr)
        cz=dist*math.cos(pr)*math.cos(yr)
        ep,_=self.space.get_positions(); lx=ep[0]*0.4; ly=ep[1]*0.4; lz=ep[2]*0.4
        glLoadIdentity(); gluLookAt(cx,cy,cz,lx,ly,lz,0,1,0)

    def _draw_city(self, dark_t):
        if self.scroll_t > 0.98: return

        sx, sy, sz = self._sun_pos()
        self._lights(dark_t, sun_pos=(sx, sy, sz))

        # ── LANGKAH 1: Gambar LANGIT (matahari & bulan) DULU ──────
        # Depth test dimatikan di dalam fungsi ini
        draw_city_sun(sx, sy, sz, self._ss, dark_t, self.sim_time)

        # Posisi bulan: berlawanan sisi dari matahari
        moon_sx = sx * (-0.55) - 18
        moon_sy = sy *   0.65  + 25
        moon_sz = sz *   0.42  - 40

        draw_city_moon(moon_sx, moon_sy, moon_sz,
                       self._sl, dark_t, self._ss, self.sim_time)

        # Siluet bulan menutupi matahari (gerhana solar)
        if self._ss > 0.32:
            draw_moon_over_sun(sx, sy, sz, self._ss, self.sim_time)

        # ── LANGKAH 2: Gambar KOTA di atas langit ─────────────────
        glEnable(GL_DEPTH_TEST)  # pastikan depth test aktif untuk kota
        self.city.draw(dark_t, self.sim_time)

    def _draw_space(self):
        if self.scroll_t < 0.02: return
        glDisable(GL_FOG)
        glLightfv(GL_LIGHT0,GL_POSITION,[0,0,0,1.0])
        glLightfv(GL_LIGHT0,GL_DIFFUSE, [1.5,1.4,1.1,1])
        glLightfv(GL_LIGHT0,GL_AMBIENT, [0.02,0.02,0.03,1])
        glLightfv(GL_LIGHT0,GL_SPECULAR,[0.8,0.8,0.7,1])
        glLightf(GL_LIGHT0,GL_CONSTANT_ATTENUATION,1.0)
        glLightf(GL_LIGHT0,GL_LINEAR_ATTENUATION,0.0)
        glLightf(GL_LIGHT0,GL_QUADRATIC_ATTENUATION,0.0)
        glLightfv(GL_LIGHT1,GL_DIFFUSE,[0,0,0,1])
        self.space.draw(self._ss,self._sl,self.sim_time)
        glEnable(GL_FOG)

    def _render(self):
        dark_t=self._dark_t(); st=self.scroll_t
        sky=lerp3(tuple(self._sky),(0.0,0.0,0.01),smoothstep(st))
        glClearColor(*sky,1.0); glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
        self._fog(dark_t); self._lights(dark_t)
        if self.free_cam: self.fcam.apply()
        elif st < 0.5:    self._cam_city()
        else:             self._cam_space()
        if st < 0.95:     self._draw_city(dark_t)
        if st > 0.10:
            glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA)
            self._cam_space(); self._draw_space(); glDisable(GL_BLEND)
        self._hud(dark_t); pygame.display.flip()

    def _hud(self, dark_t):
        glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
        glOrtho(0,WIDTH,HEIGHT,0,-1,1); glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
        glDisable(GL_DEPTH_TEST); glDisable(GL_LIGHTING)
        glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA,GL_ONE_MINUS_SRC_ALPHA)
        surf=pygame.Surface((WIDTH,HEIGHT),pygame.SRCALPHA); surf.fill((0,0,0,0))
        ps={'approach':'Mendekat','peak':'PUNCAK','recede':'Berlalu','idle':''}
        labels=[]
        if self.solar_ctrl.phase!='idle':
            labels.append((f"GERHANA MATAHARI  {int(self._ss*100)}%  [{ps[self.solar_ctrl.phase]}]",(255,215,80)))
        if self.lunar_ctrl.phase!='idle':
            labels.append((f"GERHANA BULAN  {int(self._sl*100)}%  [{ps[self.lunar_ctrl.phase]}]",(255,135,75)))
        if self.free_cam:
            labels.append(("FREE CAM — W/A/S/D  Q/E  SHIFT cepat  F keluar",(160,255,160)))
        else:
            labels.append(("[F]FreeCam  [Drag]Putar  [Scroll]Kota<->Angkasa  [SPACE]x5  [R]Reset",(190,190,190)))
        if self.scroll_t<0.05:   labels.append(("Scroll bawah -> Luar Angkasa",(160,205,255)))
        elif self.scroll_t>0.92: labels.append(("Scroll atas -> Kembali ke Kota",(160,255,205)))
        y=10
        for txt,col in labels:
            ts=self.font_s.render(txt,True,col)
            bg=pygame.Surface((ts.get_width()+14,ts.get_height()+5),pygame.SRCALPHA)
            bg.fill((0,0,0,118)); surf.blit(bg,(5,y-2)); surf.blit(ts,(12,y)); y+=22
        if self._ss>0.55:
            a=int(smoothstep((self._ss-0.55)*2.2)*255)
            ts=self.font_b.render("GERHANA MATAHARI TOTAL",True,(255,215,62)); ts.set_alpha(a)
            surf.blit(ts,(WIDTH//2-ts.get_width()//2,HEIGHT//2-55))
        if self._sl>0.55:
            a=int(smoothstep((self._sl-0.55)*2.2)*255)
            ts=self.font_b.render("GERHANA BULAN TOTAL",True,(255,110,68)); ts.set_alpha(a)
            surf.blit(ts,(WIDTH//2-ts.get_width()//2,HEIGHT//2-20))
        bw,bh,mg=270,11,20; yb=HEIGHT-48
        for ctrl,label,col,x in [
            (self.solar_ctrl,"Gerhana Matahari",(255,205,80),mg),
            (self.lunar_ctrl,"Gerhana Bulan",   (255,130,80),WIDTH-mg-bw)]:
            ls=self.font_s.render(label,True,col); surf.blit(ls,(x,yb-17))
            bg=pygame.Surface((bw,bh),pygame.SRCALPHA); bg.fill((25,25,25,155)); surf.blit(bg,(x,yb))
            fw=int(bw*ctrl.intensity)
            if fw>0:
                fill=pygame.Surface((fw,bh),pygame.SRCALPHA)
                for px in range(fw):
                    t2=px/bw; r=int(lerp(col[0]*0.35,col[0],t2))
                    g=int(lerp(col[1]*0.35,col[1],t2)); b=int(lerp(col[2]*0.35,col[2],t2))
                    pygame.draw.line(fill,(r,g,b,200),(px,0),(px,bh-1))
                surf.blit(fill,(x,yb))
            pygame.draw.rect(surf,(*col,110),(x,yb,bw,bh),1)
        data=pygame.image.tostring(surf,"RGBA",True)
        tex=glGenTextures(1); glBindTexture(GL_TEXTURE_2D,tex)
        glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA,WIDTH,HEIGHT,0,GL_RGBA,GL_UNSIGNED_BYTE,data)
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MIN_FILTER,GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAG_FILTER,GL_LINEAR)
        glEnable(GL_TEXTURE_2D); glColor4f(1,1,1,1)
        glBegin(GL_QUADS)
        glTexCoord2f(0,0);glVertex2f(0,HEIGHT); glTexCoord2f(1,0);glVertex2f(WIDTH,HEIGHT)
        glTexCoord2f(1,1);glVertex2f(WIDTH,0);  glTexCoord2f(0,1);glVertex2f(0,0)
        glEnd()
        glDisable(GL_TEXTURE_2D); glDeleteTextures([tex])
        glDisable(GL_BLEND); glEnable(GL_LIGHTING); glEnable(GL_DEPTH_TEST)
        glMatrixMode(GL_PROJECTION); glPopMatrix(); glMatrixMode(GL_MODELVIEW); glPopMatrix()

    def _events(self, dt):
        for ev in pygame.event.get():
            if ev.type==QUIT: self.running=False
            elif ev.type==KEYDOWN:
                if ev.key==K_ESCAPE: self.running=False
                elif ev.key==K_f:
                    self.free_cam=not self.free_cam
                    if self.free_cam: pygame.event.set_grab(True);pygame.mouse.set_visible(False);pygame.mouse.get_rel()
                    else: pygame.event.set_grab(False);pygame.mouse.set_visible(True)
                elif ev.key==K_SPACE: self._boost=True
                elif ev.key==K_r:
                    for c in [self.solar_ctrl,self.lunar_ctrl]: c._pi=0;c._t=0.0
                elif ev.key in (K_UP,K_PAGEUP):    self.target_st=max(0.0,self.target_st-0.18)
                elif ev.key in (K_DOWN,K_PAGEDOWN): self.target_st=min(1.0,self.target_st+0.18)
            elif ev.type==KEYUP:
                if ev.key==K_SPACE: self._boost=False
            elif ev.type==MOUSEBUTTONDOWN:
                if not self.free_cam:
                    if ev.button==1: self.mouse_dn=True;self.last_m=ev.pos
                    elif ev.button==4: self.target_st=max(0.0,self.target_st-0.13)
                    elif ev.button==5: self.target_st=min(1.0,self.target_st+0.13)
            elif ev.type==MOUSEBUTTONUP:
                if ev.button==1: self.mouse_dn=False
            elif ev.type==MOUSEMOTION:
                if not self.free_cam and self.mouse_dn:
                    dx=ev.pos[0]-self.last_m[0]; dy=ev.pos[1]-self.last_m[1]
                    if self.scroll_t>0.5:
                        self.space_yaw+=dx*0.38; self.space_pitch=clamp(self.space_pitch+dy*0.28,-45,70)
                    else:
                        self.o_yaw+=dx*0.38; self.o_pitch=clamp(self.o_pitch+dy*0.28,5,72)
                    self.last_m=ev.pos

    def run(self):
        print("╔══════════════════════════════════════════════════════╗")
        print("║    SIMULASI GERHANA 3D v5-Fixed  —  OpenGL Python   ║")
        print("╠══════════════════════════════════════════════════════╣")
        print("║  [F]   Free Camera  |  W/A/S/D  Q/E  SHIFT-cepat   ║")
        print("║  Drag  Putar kamera |  Scroll   Kota <-> Angkasa    ║")
        print("║  SPACE Percepat x5  |  R Reset  |  ESC Keluar       ║")
        print("╠══════════════════════════════════════════════════════╣")
        print("║  PERBAIKAN:                                         ║")
        print("║  - Gedung berwarna-warni (8 palet)                  ║")
        print("║  - Matahari BESAR & JELAS di langit kota            ║")
        print("║  - Bulan JELAS terlihat sejak awal                  ║")
        print("║  - Sinar & halo matahari terlihat                   ║")
        print("║  - Gerhana OTOMATIS looping                         ║")
        print("╚══════════════════════════════════════════════════════╝")
        prev=time.time()
        while self.running:
            now=time.time(); dt=min(now-prev,0.05); prev=now
            self._events(dt); self._update(dt); self._render()
            self.clock.tick(FPS)
        pygame.quit(); sys.exit()

if __name__=='__main__':
    EclipseSimulation().run()