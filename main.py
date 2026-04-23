"""
=============================================================
  SIMULASI GERHANA 3D - Kota + Luar Angkasa
  Engine : PyOpenGL + pygame
  Cara install :
    pip install PyOpenGL PyOpenGL_accelerate pygame numpy
  Cara jalankan :
    python eclipse_simulation.py
=============================================================
  KONTROL :
    SCROLL UP/DOWN  - Pindah antara scene kota dan luar angkasa
    MOUSE DRAG      - Putar kamera (orbit mode)
    F               - Toggle Free Camera (terbang bebas)
    W/A/S/D         - Gerak maju/kiri/mundur/kanan (free cam)
    Q/E_key         - Naik/turun (free cam)
    SHIFT           - Terbang lebih cepat (free cam)
    E               - Picu / Percepat Gerhana Matahari
    L               - Picu / Percepat Gerhana Bulan
    R               - Reset ke kondisi normal
    SPACE           - Percepat semua gerhana yang sedang aktif
    ESC             - Keluar
=============================================================
"""

import math
import random
import sys
import time

import numpy as np

try:
    import pygame
    from pygame.locals import *
    from OpenGL.GL import *
    from OpenGL.GLU import *
except ImportError:
    print("=" * 55)
    print("  Library belum terinstall. Jalankan perintah ini:")
    print("  pip install PyOpenGL PyOpenGL_accelerate pygame numpy")
    print("=" * 55)
    sys.exit(1)

# ─────────────────────────── KONSTANTA ───────────────────────────

WIDTH, HEIGHT = 1280, 720
FPS = 60
TITLE = "Simulasi Gerhana 3D - OpenGL Python"

# Warna langit multi-fase
SKY_DAY         = (0.53, 0.81, 0.92)
SKY_DUSK_EARLY  = (0.85, 0.60, 0.35)   # fajar/senja awal gerhana
SKY_DUSK_MID    = (0.45, 0.18, 0.22)   # gerhana mendalam
SKY_NIGHT       = (0.01, 0.01, 0.06)
FOG_DAY         = (0.53, 0.81, 0.92)
FOG_DUSK        = (0.40, 0.20, 0.15)
FOG_NIGHT       = (0.0,  0.0,  0.03)

# Siklus gerhana otomatis
ECLIPSE_CYCLE_DURATION  = 60.0   # detik per siklus (solar)
LUNAR_CYCLE_DURATION    = 80.0   # detik per siklus (lunar)
SOLAR_PHASE_OFFSET      = 0.0
LUNAR_PHASE_OFFSET      = 40.0   # mulai lebih lama dari solar

# ─────────────────────────── UTILITAS ────────────────────────────

def lerp(a, b, t):
    return a + (b - a) * t

def lerp_color(c1, c2, t):
    return tuple(lerp(a, b, t) for a, b in zip(c1, c2))

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def normalize(v):
    n = math.sqrt(sum(x * x for x in v))
    return tuple(x / n for x in v) if n > 0 else v

def smoothstep(t):
    """Easing: halus masuk dan keluar (cubic)."""
    t = clamp(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)

def smootherstep(t):
    """Easing: lebih halus lagi (quintic)."""
    t = clamp(t, 0.0, 1.0)
    return t * t * t * (t * (t * 6 - 15) + 10)

def ease_in_out_sine(t):
    """Easing berbasis sinus, cocok untuk efek cahaya."""
    return -(math.cos(math.pi * t) - 1) / 2

def ease_out_expo(t):
    """Easing cepat masuk, lambat keluar."""
    if t >= 1.0: return 1.0
    return 1.0 - math.pow(2, -10 * t)

def bell_curve(t, center=0.5, width=0.35):
    """Kurva lonceng: naik ke puncak di `center`, lalu turun."""
    x = (t - center) / width
    return math.exp(-0.5 * x * x)

# ─────────────────────────── OPENGL HELPERS ──────────────────────

def gl_color3(r, g, b):
    glColor3f(r, g, b)

def gl_color4(r, g, b, a):
    glColor4f(r, g, b, a)

def draw_box(cx, cy, cz, sx, sy, sz, color, shininess=30):
    r, g, b = color
    hx, hy, hz = sx / 2, sy / 2, sz / 2

    glMaterialfv(GL_FRONT, GL_AMBIENT_AND_DIFFUSE, [r, g, b, 1.0])
    glMaterialfv(GL_FRONT, GL_SPECULAR,            [0.3, 0.3, 0.3, 1.0])
    glMaterialf(GL_FRONT, GL_SHININESS, shininess)

    glPushMatrix()
    glTranslatef(cx, cy, cz)
    glBegin(GL_QUADS)

    glNormal3f(0, 1, 0)
    glVertex3f(-hx, hy, -hz); glVertex3f(hx, hy, -hz)
    glVertex3f(hx, hy,  hz); glVertex3f(-hx, hy,  hz)

    glNormal3f(0, -1, 0)
    glVertex3f(-hx, -hy,  hz); glVertex3f(hx, -hy,  hz)
    glVertex3f(hx, -hy, -hz); glVertex3f(-hx, -hy, -hz)

    glNormal3f(0, 0, 1)
    glVertex3f(-hx, -hy, hz); glVertex3f(hx, -hy, hz)
    glVertex3f(hx,  hy, hz); glVertex3f(-hx,  hy, hz)

    glNormal3f(0, 0, -1)
    glVertex3f(-hx,  hy, -hz); glVertex3f(hx,  hy, -hz)
    glVertex3f(hx, -hy, -hz); glVertex3f(-hx, -hy, -hz)

    glNormal3f(-1, 0, 0)
    glVertex3f(-hx, -hy, -hz); glVertex3f(-hx, -hy, hz)
    glVertex3f(-hx,  hy,  hz); glVertex3f(-hx,  hy, -hz)

    glNormal3f(1, 0, 0)
    glVertex3f(hx, -hy,  hz); glVertex3f(hx, -hy, -hz)
    glVertex3f(hx,  hy, -hz); glVertex3f(hx,  hy,  hz)

    glEnd()
    glPopMatrix()

def draw_sphere(cx, cy, cz, radius, slices=24, stacks=12, color=(1,1,1),
                emissive=(0,0,0), shininess=50):
    glPushMatrix()
    glTranslatef(cx, cy, cz)
    r, g, b = color
    glMaterialfv(GL_FRONT, GL_AMBIENT_AND_DIFFUSE, [r, g, b, 1.0])
    glMaterialfv(GL_FRONT, GL_EMISSION,            list(emissive) + [1.0])
    glMaterialfv(GL_FRONT, GL_SPECULAR,            [0.6, 0.6, 0.6, 1.0])
    glMaterialf(GL_FRONT, GL_SHININESS, shininess)
    quad = gluNewQuadric()
    gluSphere(quad, radius, slices, stacks)
    gluDeleteQuadric(quad)
    glMaterialfv(GL_FRONT, GL_EMISSION, [0, 0, 0, 1])
    glPopMatrix()

def draw_cylinder(cx, cy, cz, base_r, top_r, height, slices=12,
                  color=(0.5, 0.5, 0.5)):
    glPushMatrix()
    glTranslatef(cx, cy, cz)
    r, g, b = color
    glMaterialfv(GL_FRONT, GL_AMBIENT_AND_DIFFUSE, [r, g, b, 1.0])
    glMaterialfv(GL_FRONT, GL_SPECULAR,            [0.1, 0.1, 0.1, 1.0])
    glMaterialf(GL_FRONT, GL_SHININESS, 10)
    quad = gluNewQuadric()
    gluCylinder(quad, base_r, top_r, height, slices, 1)
    gluDeleteQuadric(quad)
    glPopMatrix()

def draw_sphere_raw(cx, cy, cz, r, slices=20, stacks=10, color=None):
    if color:
        glColor4f(*color)
    glPushMatrix()
    glTranslatef(cx, cy, cz)
    q = gluNewQuadric()
    gluSphere(q, r, slices, stacks)
    gluDeleteQuadric(q)
    glPopMatrix()

# ─────────────────────────── KELAS MOBIL ─────────────────────────

class Car:
    COLORS = [
        (0.8, 0.1, 0.1), (0.1, 0.3, 0.8), (0.1, 0.7, 0.2),
        (0.9, 0.7, 0.1), (0.8, 0.8, 0.8), (0.15,0.15,0.15),
        (0.7, 0.3, 0.8), (0.9, 0.5, 0.1),
    ]

    def __init__(self, x, z, direction, lane_z):
        self.x = x
        self.z = z
        self.direction = direction
        self.lane_z = lane_z
        self.speed = random.uniform(0.25, 0.5)
        self.color = random.choice(self.COLORS)
        self.stopped = False
        self.width  = 1.8
        self.height = 1.2
        self.length = 3.8
        self._angle = {'px': 0, 'nx': 180, 'pz': 90, 'nz': -90}[direction]

    def update(self, dt, traffic_lights):
        self.stopped = self._check_stop(traffic_lights)
        if not self.stopped:
            speed = self.speed * 20
            if self.direction == 'px':
                self.x += speed * dt
                if self.x > 220: self.x = -220
            elif self.direction == 'nx':
                self.x -= speed * dt
                if self.x < -220: self.x = 220
            elif self.direction == 'pz':
                self.z += speed * dt
                if self.z > 220: self.z = -220
            elif self.direction == 'nz':
                self.z -= speed * dt
                if self.z < -220: self.z = 220

    def _check_stop(self, traffic_lights):
        stop_dist = 12
        intersections = [0, 100, -100]
        for ix in intersections:
            for iz in intersections:
                if self.direction in ('px', 'nx'):
                    dx = ix - self.x
                    if 2 < abs(dx) < stop_dist and abs(self.z - iz) < 10:
                        if (self.direction == 'px' and dx > 0) or \
                           (self.direction == 'nx' and dx < 0):
                            tl = self._find_tl(traffic_lights, ix, iz)
                            if tl and tl.state != 'green':
                                return True
                else:
                    dz = iz - self.z
                    if 2 < abs(dz) < stop_dist and abs(self.x - ix) < 10:
                        if (self.direction == 'pz' and dz > 0) or \
                           (self.direction == 'nz' and dz < 0):
                            tl = self._find_tl(traffic_lights, ix, iz)
                            if tl and tl.state != 'green':
                                return True
        return False

    def _find_tl(self, traffic_lights, ix, iz):
        best = None; bd = 9999
        for tl in traffic_lights:
            d = math.sqrt((tl.x - ix)**2 + (tl.z - iz)**2)
            if d < 20 and d < bd:
                best = tl; bd = d
        return best

    def draw(self, dark_t):
        glPushMatrix()
        glTranslatef(self.x, 0, self.z)
        glRotatef(self._angle, 0, 1, 0)
        c = self.color
        draw_box(0, 0.6, 0, self.length, self.height, self.width, c, 60)
        draw_box(0, 1.4, 0, self.length * 0.65, 0.7, self.width * 0.9,
                 (0.1, 0.15, 0.2), 80)
        for sz in [-0.6, 0.6]:
            draw_box(self.length/2 + 0.05, 0.65, sz, 0.1, 0.35, 0.4,
                     (1.0, 1.0, 0.9), 10)
        br = (1.0, 0.1, 0.05) if self.stopped else (0.6, 0.0, 0.0)
        for sz in [-0.6, 0.6]:
            draw_box(-self.length/2 - 0.05, 0.65, sz, 0.1, 0.3, 0.35, br, 10)
        for wx, wz in [(1.2, 1.0), (1.2, -1.0), (-1.2, 1.0), (-1.2, -1.0)]:
            draw_cylinder(wx, 0.3, wz, 0.28, 0.28, 0.18, color=(0.1, 0.1, 0.1))
        glPopMatrix()

# ─────────────────────────── LAMPU LALU LINTAS ───────────────────

class TrafficLight:
    PHASES = [('green', 4.0), ('yellow', 1.2), ('red', 3.5)]

    def __init__(self, x, z, phase_offset=0.0):
        self.x = x; self.z = z
        self.state = 'green'
        self._phase_idx = 0
        self._timer = phase_offset % sum(d for _, d in self.PHASES)
        acc = 0
        for i, (s, d) in enumerate(self.PHASES):
            acc += d
            if self._timer < acc:
                self._phase_idx = i
                self._timer = self._timer - (acc - d)
                self.state = s
                break

    def update(self, dt):
        self._timer += dt
        dur = self.PHASES[self._phase_idx][1]
        if self._timer >= dur:
            self._timer -= dur
            self._phase_idx = (self._phase_idx + 1) % len(self.PHASES)
            self.state = self.PHASES[self._phase_idx][0]

    def draw(self):
        draw_cylinder(self.x, 0, self.z, 0.18, 0.18, 10, color=(0.15,0.15,0.15))
        draw_box(self.x, 11, self.z, 1.0, 3.2, 0.8, (0.08, 0.08, 0.08))
        r_em = (1.0, 0.0, 0.0) if self.state == 'red'    else (0.0,0.0,0.0)
        y_em = (1.0, 0.8, 0.0) if self.state == 'yellow' else (0.0,0.0,0.0)
        g_em = (0.0, 1.0, 0.0) if self.state == 'green'  else (0.0,0.0,0.0)
        draw_sphere(self.x, 12.4, self.z - 0.05, 0.32, 12, 8, (0.6,0.0,0.0), r_em, 20)
        draw_sphere(self.x, 11.0, self.z - 0.05, 0.32, 12, 8, (0.5,0.4,0.0), y_em, 20)
        draw_sphere(self.x,  9.6, self.z - 0.05, 0.32, 12, 8, (0.0,0.5,0.0), g_em, 20)

# ─────────────────────────── GEDUNG ──────────────────────────────

class Building:
    FACADE_COLORS = [
        (0.27, 0.35, 0.43), (0.20, 0.28, 0.38), (0.35, 0.40, 0.48),
        (0.18, 0.26, 0.34), (0.30, 0.38, 0.46), (0.25, 0.30, 0.38),
    ]

    def __init__(self, x, z, w, d, h):
        self.x = x; self.z = z
        self.w = w; self.d = d; self.h = h
        self.color = random.choice(self.FACADE_COLORS)
        self.lit_windows = [
            (random.uniform(-w/2+1, w/2-1),
             random.uniform(2, h-2),
             random.uniform(-d/2+1, d/2-1),
             random.random() > 0.4)
            for _ in range(int(w * h / 18))
        ]

    def draw(self, dark_t):
        draw_box(self.x, self.h/2, self.z, self.w, self.h, self.d, self.color, 40)
        gc = lerp_color((0.4,0.55,0.7), (0.0,0.0,0.1), dark_t)
        draw_box(self.x, self.h/2, self.z,
                 self.w + 0.1, self.h + 0.1, self.d + 0.1, gc, 90)
        if dark_t > 0.25:
            for wx, wy, wz, lit in self.lit_windows:
                if lit:
                    intensity = smoothstep(dark_t) * random.uniform(0.8, 1.0)
                    wc = lerp_color((0,0,0), (1.0, 0.95, 0.6), intensity)
                    draw_box(self.x + wx, self.h/2 + wy - self.h/2,
                             self.z + wz, 0.6, 0.9, 0.1, wc, 5)

# ─────────────────────────── KOTA ────────────────────────────────

class City:
    def __init__(self):
        self.buildings = []
        self.traffic_lights = []
        self.cars = []
        self.street_lamps = []
        self._build()

    def _build(self):
        random.seed(42)
        zones = [
            (-80, -80, 12, 40, 40, 1.2), ( 80, -80, 12, 40, 40, 1.0),
            (-80,  80, 12, 40, 40, 1.1), ( 80,  80, 12, 40, 40, 1.3),
            (-160, 0, 8, 30, 60, 0.9),   ( 160, 0, 8, 30, 60, 0.9),
            (0, -160, 8, 60, 30, 0.85),  (0,  160, 8, 60, 30, 0.85),
        ]
        for cx, cz, count, sx, sz, sc in zones:
            for _ in range(count):
                bw = random.uniform(10, 22) * sc
                bd = random.uniform(10, 22) * sc
                bh = random.uniform(30, 120) * sc
                bx = cx + random.uniform(-sx, sx)
                bz = cz + random.uniform(-sz, sz)
                if abs(bx) < 14 or abs(bz) < 14: continue
                if abs(abs(bx)-100) < 14 or abs(abs(bz)-100) < 14: continue
                self.buildings.append(Building(bx, bz, bw, bd, bh))

        offsets = [(8, 8), (-8, 8), (8, -8), (-8, -8)]
        for ix in [0, 100, -100]:
            for iz in [0, 100, -100]:
                for ox, oz in offsets:
                    ph = random.uniform(0, 8.7)
                    self.traffic_lights.append(TrafficLight(ix + ox, iz + oz, ph))

        for i in range(14):
            self.cars.append(Car(random.uniform(-200,200),  4.5, 'px',  4.5))
            self.cars.append(Car(random.uniform(-200,200), -4.5, 'nx', -4.5))
        for i in range(14):
            self.cars.append(Car( 4.5, random.uniform(-200,200), 'pz',  4.5))
            self.cars.append(Car(-4.5, random.uniform(-200,200), 'nz', -4.5))
        for z_base in [96, 104, -96, -104]:
            d = 'px' if z_base > 0 else 'nx'
            for i in range(8):
                self.cars.append(Car(random.uniform(-200,200), z_base, d, z_base))
        for x_base in [96, 104, -96, -104]:
            d = 'pz' if x_base > 0 else 'nz'
            for i in range(8):
                self.cars.append(Car(x_base, random.uniform(-200,200), d, x_base))

        for i in range(-18, 19, 3):
            for side in [-11, 11]:
                self.street_lamps.append((i*10, 0, side))
                self.street_lamps.append((side, 0, i*10))

    def update(self, dt):
        for tl in self.traffic_lights: tl.update(dt)
        for car in self.cars:          car.update(dt, self.traffic_lights)

    def draw_ground(self, dark_t):
        road_c  = lerp_color((0.18,0.18,0.18),(0.05,0.05,0.08), dark_t)
        walk_c  = lerp_color((0.35,0.32,0.28),(0.12,0.10,0.10), dark_t)
        grass_c = lerp_color((0.22,0.40,0.18),(0.04,0.08,0.04), dark_t)
        mark_c  = lerp_color((0.9, 0.85,0.0), (0.4, 0.35,0.0), dark_t)

        draw_box(0, -0.5, 0, 500, 1, 500, grass_c, 10)
        for z_pos in [0, 100, -100]:
            draw_box(0, 0.05, z_pos, 440, 0.1, 20, road_c, 5)
            for xi in range(-21, 22):
                draw_box(xi*20, 0.06, z_pos, 8, 0.1, 0.25, mark_c, 5)
        for x_pos in [0, 100, -100]:
            draw_box(x_pos, 0.05, 0, 20, 0.1, 440, road_c, 5)
            for zi in range(-21, 22):
                draw_box(x_pos, 0.06, zi*20, 0.25, 0.1, 8, mark_c, 5)
        for z_pos in [0, 100, -100]:
            for side in [-12, 12]:
                draw_box(0, 0.3, z_pos + side, 440, 0.6, 4, walk_c, 5)
        for x_pos in [0, 100, -100]:
            for side in [-12, 12]:
                draw_box(x_pos + side, 0.3, 0, 4, 0.6, 440, walk_c, 5)

    def draw_street_lamps(self, dark_t):
        pole_c  = (0.2, 0.2, 0.2)
        base_em = lerp_color((0,0,0), (1.0,0.95,0.7), clamp(dark_t*2, 0, 1))
        for lx, _, lz in self.street_lamps:
            draw_cylinder(lx, 0, lz, 0.15, 0.15, 9, color=pole_c)
            draw_sphere(lx, 9.5, lz, 0.5, 8, 6, (0.9, 0.85, 0.6), base_em, 10)

    def draw_trees(self, dark_t):
        trunk_c = lerp_color((0.36,0.22,0.10),(0.15,0.09,0.04), dark_t)
        leaf_c  = lerp_color((0.18,0.50,0.12),(0.04,0.12,0.03), dark_t)
        for lx, _, lz in self.street_lamps[::3]:
            tx, tz = lx + 1.5, lz + 1.5
            draw_cylinder(tx, 0, tz, 0.3, 0.3, 4, color=trunk_c)
            draw_sphere(tx, 5.5, tz, 2.0, 10, 8, leaf_c, (0,0,0), 10)

    def draw(self, dark_t):
        self.draw_ground(dark_t)
        for b in self.buildings:      b.draw(dark_t)
        for tl in self.traffic_lights: tl.draw()
        for car in self.cars:          car.draw(dark_t)
        self.draw_street_lamps(dark_t)
        self.draw_trees(dark_t)

# ─────────────────────────── SCENE LUAR ANGKASA ──────────────────

class SpaceScene:
    def __init__(self):
        random.seed(7)
        self.stars = [
            (random.uniform(-2000, 2000),
             random.uniform(-2000, 2000),
             random.uniform(-2000, 2000),
             random.uniform(1.0, 3.5))
            for _ in range(4000)
        ]
        self.moon_angle   = 0.0
        self.moon_orbit_r = 250.0

    def update(self, dt, eclipse_t, lunar_t, moon_target_angle):
        """Posisi bulan dikontrol oleh main simulation."""
        # Interpolasi smooth ke target angle
        diff = moon_target_angle - self.moon_angle
        # Normalize ke -pi..pi agar rotasi searah
        while diff >  math.pi: diff -= 2 * math.pi
        while diff < -math.pi: diff += 2 * math.pi
        self.moon_angle += diff * min(1.0, dt * 1.5)

    def draw(self, eclipse_t, lunar_t, eclipse_intensity):
        # Bintang — redup saat siang, terang saat gerhana
        star_bright = clamp(0.3 + eclipse_intensity * 0.7, 0.1, 1.0)
        glDisable(GL_LIGHTING)
        glPointSize(2.0)
        glBegin(GL_POINTS)
        for sx, sy, sz, brightness in self.stars:
            b = (brightness / 3.5) * star_bright
            glColor3f(b, b, b)
            glVertex3f(sx, sy, sz)
        glEnd()
        glEnable(GL_LIGHTING)

        # Matahari dengan corona yang tumbuh saat gerhana akan terjadi
        sun_em_int = lerp(3.0, 1.5, eclipse_intensity)
        draw_sphere(-600, 0, 0, 90, 32, 16,
                    (1.0, 0.92, 0.4),
                    (1.0 * sun_em_int, 0.85 * sun_em_int, 0.3 * sun_em_int), 10)

        # Corona matahari — membesar & lebih terang menjelang gerhana
        corona_scale = lerp(1.0, 2.5, smootherstep(eclipse_intensity))
        glDisable(GL_LIGHTING)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)
        glColor4f(1.0, 0.7, 0.2, lerp(0.06, 0.18, eclipse_intensity))
        draw_sphere_raw(-600, 0, 0, 130 * corona_scale, 24, 12)
        glColor4f(1.0, 0.5, 0.1, lerp(0.04, 0.12, eclipse_intensity))
        draw_sphere_raw(-600, 0, 0, 170 * corona_scale, 20, 10)
        glColor4f(1.0, 0.3, 0.05, lerp(0.0, 0.07, eclipse_intensity))
        draw_sphere_raw(-600, 0, 0, 220 * corona_scale, 16, 8)
        glDisable(GL_BLEND)
        glEnable(GL_LIGHTING)

        # Bumi
        draw_sphere(300, 0, 0, 80, 48, 24, (0.10, 0.35, 0.75), (0, 0, 0), 80)
        glDisable(GL_LIGHTING)
        draw_sphere_raw(300, 0, 0, 81, 24, 12, (0.18, 0.50, 0.14, 0.7))
        glEnable(GL_LIGHTING)

        # Bulan
        moon_x = 300 + self.moon_orbit_r * math.cos(self.moon_angle)
        moon_y =        self.moon_orbit_r * math.sin(self.moon_angle) * 0.3
        mc = lerp_color((0.82, 0.80, 0.74), (0.55, 0.12, 0.05), lunar_t)
        me = lerp_color((0, 0, 0), (0.4, 0.05, 0.0), lunar_t)
        draw_sphere(moon_x, moon_y, 0, 22, 32, 16, mc, me, 20)

        # Umbra shadow cone saat gerhana matahari
        if eclipse_t > 0.05:
            self._draw_shadow_cone(moon_x, moon_y, eclipse_t)

        # Penumbra gerhana bulan (bayangan bumi)
        if lunar_t > 0.05:
            self._draw_lunar_shadow(moon_x, moon_y, lunar_t)

    def _draw_shadow_cone(self, mx, my, t):
        alpha = smoothstep(t) * 0.45
        glDisable(GL_LIGHTING)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        # Kerucut umbra
        glColor4f(0, 0, 0, alpha)
        glBegin(GL_TRIANGLE_FAN)
        glVertex3f(mx, my, 0)
        steps = 20
        for i in range(steps + 1):
            ang = 2 * math.pi * i / steps
            glVertex3f(300 + 25 * math.cos(ang), 25 * math.sin(ang), 0)
        glEnd()
        # Halo penumbra lebih besar, lebih transparan
        glColor4f(0, 0, 0.05, alpha * 0.4)
        glBegin(GL_TRIANGLE_FAN)
        glVertex3f(mx, my, 0)
        for i in range(steps + 1):
            ang = 2 * math.pi * i / steps
            glVertex3f(300 + 55 * math.cos(ang), 55 * math.sin(ang), 0)
        glEnd()
        glDisable(GL_BLEND)
        glEnable(GL_LIGHTING)

    def _draw_lunar_shadow(self, mx, my, t):
        """Bayangan bumi menyelimuti bulan (gerhana bulan)."""
        alpha = smoothstep(t) * 0.7
        glDisable(GL_LIGHTING)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glColor4f(0.1, 0.0, 0.0, alpha)
        draw_sphere_raw(mx, my, 0, 23, 24, 12)
        glDisable(GL_BLEND)
        glEnable(GL_LIGHTING)

# ─────────────────────────── FREE CAMERA ─────────────────────────

class FreeCamera:
    """Kamera bebas terbang dengan WASD + mouse look."""
    def __init__(self):
        self.pos   = [0.0, 80.0, 300.0]
        self.yaw   = 180.0   # derajat — arah menghadap -Z
        self.pitch = -10.0   # derajat — sedikit ke bawah
        self.speed = 60.0
        self.sens  = 0.18
        self._locked = False

    def apply(self):
        glLoadIdentity()
        # Hitung forward vector
        y = math.radians(self.yaw)
        p = math.radians(self.pitch)
        fx = math.sin(y) * math.cos(p)
        fy = math.sin(p)
        fz = -math.cos(y) * math.cos(p)
        # Titik lihat
        tx = self.pos[0] + fx
        ty = self.pos[1] + fy
        tz = self.pos[2] + fz
        gluLookAt(self.pos[0], self.pos[1], self.pos[2],
                  tx, ty, tz, 0, 1, 0)

    def update(self, dt, keys, mouse_rel, active):
        if not active:
            return
        # Rotasi kamera
        dx, dy = mouse_rel
        self.yaw   += dx * self.sens
        self.pitch  = clamp(self.pitch - dy * self.sens, -89.0, 89.0)

        # Hitung arah
        y = math.radians(self.yaw)
        p = math.radians(self.pitch)
        fx = math.sin(y) * math.cos(p)
        fy = math.sin(p)
        fz = -math.cos(y) * math.cos(p)
        # Right vector
        rx =  math.cos(y)
        ry =  0.0
        rz =  math.sin(y)

        spd = self.speed * (5.0 if keys[K_LSHIFT] or keys[K_RSHIFT] else 1.0)
        move = spd * dt

        if keys[K_w]:
            self.pos[0] += fx * move; self.pos[1] += fy * move; self.pos[2] += fz * move
        if keys[K_s]:
            self.pos[0] -= fx * move; self.pos[1] -= fy * move; self.pos[2] -= fz * move
        if keys[K_a]:
            self.pos[0] -= rx * move; self.pos[2] -= rz * move
        if keys[K_d]:
            self.pos[0] += rx * move; self.pos[2] += rz * move
        if keys[K_q]:
            self.pos[1] -= move
        if keys[K_e]:
            self.pos[1] += move

# ─────────────────────────── ECLIPSE CONTROLLER ──────────────────

class EclipseController:
    """
    Mengatur siklus gerhana otomatis + kontrol manual.
    Siklus:
        idle  → approach → peak → recede → idle
    Setiap siklus memiliki durasi total CYCLE_DURATION detik.
    Tombol manual: mempercepat siklus saat ini (fast-forward x5).
    """
    # Fase: (nama, fraksi waktu dari total siklus)
    PHASES = [
        ('idle',     0.30),   # 30% waktu normal (tidak gerhana)
        ('approach', 0.25),   # 25% transisi masuk
        ('peak',     0.20),   # 20% puncak gerhana
        ('recede',   0.25),   # 25% transisi keluar
    ]

    def __init__(self, cycle_duration, start_phase='idle', start_frac=0.0):
        self.cycle_duration = cycle_duration
        self._phase_names  = [p[0] for p in self.PHASES]
        self._phase_fracs  = [p[1] for p in self.PHASES]
        # Waktu total per fase
        self._phase_dur    = [f * cycle_duration for f in self._phase_fracs]
        # State
        self._phase_idx    = self._phase_names.index(start_phase)
        self._phase_timer  = start_frac * self._phase_dur[self._phase_idx]
        self.intensity     = 0.0   # 0..1, seberapa dalam gerhana
        self.boosted       = False  # apakah fast-forward aktif

    def boost(self):
        """Tombol ditekan: aktifkan fast-forward."""
        self.boosted = True

    def release_boost(self):
        self.boosted = False

    def update(self, dt):
        speed_mul = 5.0 if self.boosted else 1.0
        self._phase_timer += dt * speed_mul

        # Cek apakah fase selesai
        phase_dur = self._phase_dur[self._phase_idx]
        while self._phase_timer >= phase_dur:
            self._phase_timer -= phase_dur
            self._phase_idx = (self._phase_idx + 1) % len(self.PHASES)
            phase_dur = self._phase_dur[self._phase_idx]

        # Hitung intensitas berdasarkan fase
        phase_name = self._phase_names[self._phase_idx]
        t = self._phase_timer / phase_dur if phase_dur > 0 else 0.0

        if phase_name == 'idle':
            self.intensity = 0.0
        elif phase_name == 'approach':
            # Naik perlahan dengan ease-in-out sine
            self.intensity = ease_in_out_sine(t)
        elif phase_name == 'peak':
            # Di puncak, sedikit berfluktuasi (efek corona)
            flicker = 0.015 * math.sin(self._phase_timer * 3.7)
            self.intensity = clamp(1.0 + flicker, 0.95, 1.05)
        elif phase_name == 'recede':
            # Turun dengan ease (lebih lambat di awal, cepat di akhir)
            self.intensity = ease_in_out_sine(1.0 - t)

        self.intensity = clamp(self.intensity, 0.0, 1.0)

    @property
    def phase(self):
        return self._phase_names[self._phase_idx]

    @property
    def phase_progress(self):
        phase_dur = self._phase_dur[self._phase_idx]
        return self._phase_timer / phase_dur if phase_dur > 0 else 0.0

    @property
    def moon_target_angle(self):
        """Sudut target bulan berdasarkan fase gerhana matahari."""
        phase_name = self._phase_names[self._phase_idx]
        t = self.phase_progress
        # Orbit normal: bulan mengelilingi orbit -pi..pi
        # Saat gerhana matahari: bulan di -pi/2 (di antara matahari dan bumi)
        normal_angle = self._phase_timer * 0.008 + 1.0
        eclipse_angle = -math.pi / 2

        if phase_name == 'idle':
            return normal_angle
        elif phase_name == 'approach':
            return lerp(normal_angle, eclipse_angle, ease_in_out_sine(t))
        elif phase_name == 'peak':
            return eclipse_angle
        elif phase_name == 'recede':
            return lerp(eclipse_angle, normal_angle + 0.5, ease_in_out_sine(t))
        return normal_angle

# ─────────────────────────── RENDERER UTAMA ──────────────────────

class EclipseSimulation:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(TITLE)
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), DOUBLEBUF | OPENGL)
        pygame.display.set_icon(pygame.Surface((32, 32)))

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_LIGHT1)
        glEnable(GL_COLOR_MATERIAL)
        glEnable(GL_NORMALIZE)
        glShadeModel(GL_SMOOTH)
        glEnable(GL_FOG)

        self._setup_projection()

        # ── Scroll / scene blend ──
        self.scroll_t        = 0.0
        self.target_scroll_t = 0.0

        # ── Eclipse controllers (loop otomatis) ──
        self.solar_ctrl = EclipseController(ECLIPSE_CYCLE_DURATION,
                                            'idle', 0.0)
        self.lunar_ctrl = EclipseController(LUNAR_CYCLE_DURATION,
                                            'idle', 0.3)   # offset agar tidak barengan

        # Nilai terakhir intensitas yang sudah di-smooth (untuk transisi langit)
        self._smooth_solar = 0.0
        self._smooth_lunar = 0.0

        # Warna langit yang di-smooth
        self._sky_r = list(SKY_DAY)

        # ── Kamera ──
        self.free_cam_active = False
        self.free_cam        = FreeCamera()
        self.orbit_pitch     = 25.0
        self.orbit_yaw       = 30.0
        self.mouse_down      = False
        self.last_mouse      = (0, 0)

        # Scene objects
        self.city  = City()
        self.space = SpaceScene()

        # Font
        self.font_big  = pygame.font.SysFont('Arial', 22, bold=True)
        self.font_sm   = pygame.font.SysFont('Arial', 15)
        self.clock     = pygame.time.Clock()
        self.running   = True
        self.sim_time  = 0.0

        # Tombol boost (SPACE)
        self._space_held = False

    def _setup_projection(self):
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(60.0, WIDTH / HEIGHT, 0.5, 8000.0)
        glMatrixMode(GL_MODELVIEW)

    # ───── Pencahayaan ─────

    def _setup_lights(self, dark_t):
        """Setup pencahayaan dinamis berdasarkan fase gerhana."""
        et = self._smooth_solar
        lt = self._smooth_lunar

        # Warna matahari berubah: putih → oranye merah saat gerhana
        sun_col_r = lerp(1.00, 0.75, et)
        sun_col_g = lerp(0.97, 0.35, et)
        sun_col_b = lerp(0.88, 0.15, et)
        sun_brightness = max(0.0, 1.0 - dark_t * 0.97)

        glLightfv(GL_LIGHT0, GL_POSITION,  [200.0, 400.0, 150.0, 0.0])
        glLightfv(GL_LIGHT0, GL_DIFFUSE,
                  [sun_col_r * sun_brightness, sun_col_g * sun_brightness,
                   sun_col_b * sun_brightness, 1.0])
        glLightfv(GL_LIGHT0, GL_AMBIENT,
                  [max(0.02, 0.25 * (1 - dark_t)),
                   max(0.02, 0.22 * (1 - dark_t)),
                   max(0.04, 0.28 * (1 - dark_t)), 1.0])
        glLightfv(GL_LIGHT0, GL_SPECULAR,
                  [sun_brightness * 0.5 * sun_col_r,
                   sun_brightness * 0.5 * sun_col_g,
                   sun_brightness * 0.4 * sun_col_b, 1.0])

        city_glow = dark_t * 0.35
        glLightfv(GL_LIGHT1, GL_POSITION, [0.0, 1.0, 0.0, 0.0])
        glLightfv(GL_LIGHT1, GL_DIFFUSE,
                  [city_glow * 0.8, city_glow * 0.7, city_glow * 0.4, 1.0])
        glLightfv(GL_LIGHT1, GL_AMBIENT,  [0.0, 0.0, 0.0, 1.0])

    def _setup_fog(self, dark_t):
        # Warna fog multi-tahap
        if dark_t < 0.5:
            fog_color = lerp_color(FOG_DAY, FOG_DUSK, dark_t * 2)
        else:
            fog_color = lerp_color(FOG_DUSK, FOG_NIGHT, (dark_t - 0.5) * 2)
        fc = list(fog_color) + [1.0]
        glFogfv(GL_FOG_COLOR, fc)
        glFogf(GL_FOG_MODE, GL_LINEAR)
        fog_near = lerp(250.0, 80.0, dark_t)
        fog_far  = lerp(700.0, 350.0, dark_t)
        glFogf(GL_FOG_START, fog_near)
        glFogf(GL_FOG_END,   fog_far)

    # ───── Update ─────

    def _update(self, dt):
        self.sim_time += dt

        # Scroll
        self.scroll_t += (self.target_scroll_t - self.scroll_t) * min(1.0, dt * 5.0)
        self.scroll_t  = clamp(self.scroll_t, 0.0, 1.0)

        # Boost
        solar_boost = self._space_held
        lunar_boost = self._space_held

        if solar_boost: self.solar_ctrl.boost()
        else:           self.solar_ctrl.release_boost()
        if lunar_boost: self.lunar_ctrl.boost()
        else:           self.lunar_ctrl.release_boost()

        # Update controllers
        self.solar_ctrl.update(dt)
        self.lunar_ctrl.update(dt)

        # Smooth intensitas (menghindari lompatan kasar)
        smooth_rate = 3.0
        self._smooth_solar += (self.solar_ctrl.intensity - self._smooth_solar) * min(1.0, dt * smooth_rate)
        self._smooth_lunar += (self.lunar_ctrl.intensity - self._smooth_lunar) * min(1.0, dt * smooth_rate)

        # Warna langit yang di-interpolasi dengan multi-tahap
        dark_t_raw = max(self._smooth_solar, self._smooth_lunar)
        et = self._smooth_solar

        # Langit saat gerhana matahari: siang → senja → malam
        if dark_t_raw < 0.35:
            target_sky = lerp_color(SKY_DAY, SKY_DUSK_EARLY, dark_t_raw / 0.35)
        elif dark_t_raw < 0.65:
            target_sky = lerp_color(SKY_DUSK_EARLY, SKY_DUSK_MID, (dark_t_raw - 0.35) / 0.30)
        else:
            target_sky = lerp_color(SKY_DUSK_MID, SKY_NIGHT, (dark_t_raw - 0.65) / 0.35)

        # Smooth perubahan warna langit
        sky_smooth = min(1.0, dt * 1.5)
        for i in range(3):
            self._sky_r[i] += (target_sky[i] - self._sky_r[i]) * sky_smooth

        # Update moon angle di space scene
        moon_target = self.solar_ctrl.moon_target_angle
        self.space.update(dt, self._smooth_solar, self._smooth_lunar, moon_target)

        # Update city
        self.city.update(dt)

        # Free cam
        if self.free_cam_active:
            keys = pygame.key.get_pressed()
            mouse_rel = pygame.mouse.get_rel() if pygame.mouse.get_focused() else (0, 0)
            self.free_cam.update(dt, keys, mouse_rel, True)

    def _dark_t(self):
        return max(self._smooth_solar, self._smooth_lunar)

    # ───── Kamera ─────

    def _camera_city_orbit(self):
        dist = lerp(180.0, 600.0, self.scroll_t)
        elev = lerp(40.0, 200.0, self.scroll_t)
        pitch_rad = math.radians(self.orbit_pitch)
        yaw_rad   = math.radians(self.orbit_yaw)
        cx = dist * math.cos(pitch_rad) * math.sin(yaw_rad)
        cz = dist * math.cos(pitch_rad) * math.cos(yaw_rad)
        cy = elev + dist * math.sin(pitch_rad) * 0.5
        glLoadIdentity()
        gluLookAt(cx, cy, cz, 0, lerp(20, 80, self.scroll_t), 0, 0, 1, 0)

    def _camera_space(self):
        glLoadIdentity()
        gluLookAt(0, 80, 600, -100, 0, 0, 0, 1, 0)

    # ───── Render ─────

    def _draw_sky_background(self):
        sky_space = (0.0, 0.0, 0.02)
        sky_c = lerp_color(tuple(self._sky_r), sky_space, self.scroll_t)
        glClearColor(*sky_c, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

    def _draw_city_scene(self, dark_t):
        if self.scroll_t > 0.98:
            return
        self.city.draw(dark_t)

        # Matahari di kota
        sun_x = 200 * math.cos(self.sim_time * 0.04)
        sun_y = 150 + 30 * math.sin(self.sim_time * 0.02)
        sun_z = 200 * math.sin(self.sim_time * 0.04) - 300
        # Warna matahari: cerah → oranye → merah saat gerhana
        sr = lerp(1.0, 0.9,  self._smooth_solar)
        sg = lerp(0.9, 0.35, self._smooth_solar)
        sb = lerp(0.5, 0.05, self._smooth_solar)
        sun_size = lerp(18, 14, self._smooth_solar)
        glDisable(GL_LIGHTING)
        glColor3f(sr, sg, sb)
        draw_sphere_raw(sun_x, sun_y, sun_z, sun_size, 16, 10)

        # Halo matahari menjelang gerhana
        if self._smooth_solar > 0.1:
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE)
            alpha = self._smooth_solar * 0.25
            glColor4f(sr, sg * 0.5, 0.0, alpha)
            draw_sphere_raw(sun_x, sun_y, sun_z, sun_size * 1.6, 12, 8)
            glColor4f(sr, sg * 0.3, 0.0, alpha * 0.5)
            draw_sphere_raw(sun_x, sun_y, sun_z, sun_size * 2.4, 10, 6)
            glDisable(GL_BLEND)

        glEnable(GL_LIGHTING)

        # Bulan di kota (terlihat saat cukup gelap)
        if dark_t > 0.1:
            mc = lerp_color((0.85, 0.82, 0.76), (0.6, 0.12, 0.04), self._smooth_lunar)
            me = lerp_color((0,0,0),(0.4,0.05,0.0), self._smooth_lunar)
            draw_sphere(-sun_x * 0.3, sun_y * 0.8, sun_z * 0.3 - 50,
                        8, 20, 10, mc, me, 20)

    def _draw_space_scene(self):
        if self.scroll_t < 0.02:
            return
        self._camera_space()
        self._setup_lights(self._dark_t())
        self.space.draw(self._smooth_solar, self._smooth_lunar, self._smooth_solar)

    def _render(self):
        dark_t = self._dark_t()

        self._draw_sky_background()
        self._setup_fog(dark_t)
        self._setup_lights(dark_t)

        # Kamera
        if self.free_cam_active:
            self.free_cam.apply()
        else:
            self._camera_city_orbit()

        self._draw_city_scene(dark_t)

        if self.scroll_t > 0.05:
            glDisable(GL_FOG)
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            self._draw_space_scene()
            glDisable(GL_BLEND)
            glEnable(GL_FOG)

        self._overlay_hud(dark_t)
        pygame.display.flip()

    def _overlay_hud(self, dark_t):
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, WIDTH, HEIGHT, 0, -1, 1)
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_LIGHTING)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        surf.fill((0, 0, 0, 0))

        labels = []

        # Status gerhana
        solar_phase = self.solar_ctrl.phase
        lunar_phase = self.lunar_ctrl.phase

        if solar_phase != 'idle':
            pct = int(self._smooth_solar * 100)
            phase_labels = {
                'approach': 'Mendekat', 'peak': 'PUNCAK',
                'recede': 'Berlalu', 'idle': ''
            }
            labels.append((
                f"☀ GERHANA MATAHARI — {pct}% [{phase_labels.get(solar_phase,'')}]",
                (255, 200, 80)
            ))

        if lunar_phase != 'idle':
            pct = int(self._smooth_lunar * 100)
            phase_labels = {
                'approach': 'Mendekat', 'peak': 'PUNCAK',
                'recede': 'Berlalu', 'idle': ''
            }
            labels.append((
                f"🌙 GERHANA BULAN — {pct}% [{phase_labels.get(lunar_phase,'')}]",
                (255, 120, 70)
            ))

        # Kontrol hint
        if self.free_cam_active:
            labels.append(("📷 FREE CAM — W/A/S/D gerak | Q/E naik-turun | SHIFT cepat | F keluar", (180, 255, 180)))
        else:
            labels.append(("[F] Free Camera  [Drag] Putar  [Scroll] Kota↔Angkasa  [SPACE] Percepat Gerhana  [R] Reset", (200, 200, 200)))

        if self.scroll_t < 0.05:
            labels.append(("↓ Scroll ke bawah → Keluar Angkasa", (170, 200, 255)))
        elif self.scroll_t > 0.95:
            labels.append(("↑ Scroll ke atas → Kembali ke Kota", (170, 255, 200)))

        y_off = 10
        for text, color in labels:
            ts = self.font_sm.render(text, True, color)
            # Background semi-transparan untuk keterbacaan
            bg = pygame.Surface((ts.get_width() + 12, ts.get_height() + 4), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 110))
            surf.blit(bg, (5, y_off - 2))
            surf.blit(ts, (11, y_off))
            y_off += 24

        # Judul besar saat puncak gerhana
        if self._smooth_solar > 0.5:
            alpha_title = int(smoothstep((self._smooth_solar - 0.5) * 2) * 255)
            title_surf = self.font_big.render("GERHANA MATAHARI TOTAL", True, (255, 200, 60))
            title_surf.set_alpha(alpha_title)
            surf.blit(title_surf, (WIDTH//2 - title_surf.get_width()//2, HEIGHT//2 - 50))

        if self._smooth_lunar > 0.5:
            alpha_title = int(smoothstep((self._smooth_lunar - 0.5) * 2) * 255)
            title_surf = self.font_big.render("GERHANA BULAN TOTAL", True, (255, 100, 60))
            title_surf.set_alpha(alpha_title)
            surf.blit(title_surf, (WIDTH//2 - title_surf.get_width()//2, HEIGHT//2 - 20))

        # Progress bar gerhana di bawah layar
        self._draw_progress_bars(surf)

        data = pygame.image.tostring(surf, "RGBA", True)
        tex = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, tex)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, WIDTH, HEIGHT, 0,
                     GL_RGBA, GL_UNSIGNED_BYTE, data)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glEnable(GL_TEXTURE_2D)
        glColor4f(1, 1, 1, 1)
        glBegin(GL_QUADS)
        glTexCoord2f(0,0); glVertex2f(0, HEIGHT)
        glTexCoord2f(1,0); glVertex2f(WIDTH, HEIGHT)
        glTexCoord2f(1,1); glVertex2f(WIDTH, 0)
        glTexCoord2f(0,1); glVertex2f(0, 0)
        glEnd()
        glDisable(GL_TEXTURE_2D)
        glDeleteTextures([tex])

        glDisable(GL_BLEND)
        glEnable(GL_LIGHTING)
        glEnable(GL_DEPTH_TEST)
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()

    def _draw_progress_bars(self, surf):
        """Progress bar siklus gerhana di bagian bawah layar."""
        bar_w  = 280
        bar_h  = 12
        margin = 20
        y_base = HEIGHT - 50

        controllers = [
            (self.solar_ctrl, "☀ Solar Eclipse", (255, 200, 80),  margin),
            (self.lunar_ctrl, "🌙 Lunar Eclipse", (255, 130, 80), WIDTH - margin - bar_w),
        ]

        for ctrl, label, color, x in controllers:
            # Label
            ls = self.font_sm.render(label, True, color)
            surf.blit(ls, (x, y_base - 18))

            # Background bar
            bg_rect = pygame.Surface((bar_w, bar_h), pygame.SRCALPHA)
            bg_rect.fill((30, 30, 30, 160))
            surf.blit(bg_rect, (x, y_base))

            # Fill intensitas
            fill_w = int(bar_w * ctrl.intensity)
            if fill_w > 0:
                fill = pygame.Surface((fill_w, bar_h), pygame.SRCALPHA)
                # Gradient warna
                for px in range(fill_w):
                    t = px / bar_w
                    r = int(lerp(color[0] * 0.4, color[0], t))
                    g = int(lerp(color[1] * 0.4, color[1], t))
                    b = int(lerp(color[2] * 0.4, color[2], t))
                    pygame.draw.line(fill, (r, g, b, 200), (px, 0), (px, bar_h - 1))
                surf.blit(fill, (x, y_base))

            # Border
            pygame.draw.rect(surf, (*color, 120), (x, y_base, bar_w, bar_h), 1)

            # Penanda fase
            phases = EclipseController.PHASES
            acc = 0.0
            for ph_name, ph_frac in phases:
                acc += ph_frac
                if acc < 1.0:
                    px = x + int(bar_w * acc)
                    pygame.draw.line(surf, (200, 200, 200, 100), (px, y_base), (px, y_base + bar_h))

    # ───── Event ─────

    def _handle_events(self, dt):
        for event in pygame.event.get():
            if event.type == QUIT:
                self.running = False
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    self.running = False
                elif event.key == K_f:
                    self.free_cam_active = not self.free_cam_active
                    if self.free_cam_active:
                        
                        pygame.event.set_grab(True)        
                        pygame.mouse.set_visible(False)   
                        # Reset rel mouse agar tidak lompat
                        pygame.mouse.get_rel()
                    else:
                        pygame.event.set_grab(False)       
                        pygame.mouse.set_visible(True)     
                elif event.key == K_SPACE:
                    self._space_held = True
                elif event.key == K_r:
                    # Reset: paksa ke fase idle
                    self.solar_ctrl._phase_idx = 0
                    self.solar_ctrl._phase_timer = 0.0
                    self.lunar_ctrl._phase_idx = 0
                    self.lunar_ctrl._phase_timer = 0.0
                elif event.key == K_UP:
                    self.target_scroll_t = max(0.0, self.target_scroll_t - 0.15)
                elif event.key == K_DOWN:
                    self.target_scroll_t = min(1.0, self.target_scroll_t + 0.15)
            elif event.type == KEYUP:
                if event.key == K_SPACE:
                    self._space_held = False
            elif event.type == MOUSEBUTTONDOWN:
                if not self.free_cam_active:
                    if event.button == 1:
                        self.mouse_down = True
                        self.last_mouse = event.pos
                    elif event.button == 4:
                        self.target_scroll_t = max(0.0, self.target_scroll_t - 0.12)
                    elif event.button == 5:
                        self.target_scroll_t = min(1.0, self.target_scroll_t + 0.12)
            elif event.type == MOUSEBUTTONUP:
                if event.button == 1:
                    self.mouse_down = False
            elif event.type == MOUSEMOTION:
                if not self.free_cam_active and self.mouse_down:
                    dx = event.pos[0] - self.last_mouse[0]
                    dy = event.pos[1] - self.last_mouse[1]
                    self.orbit_yaw   += dx * 0.4
                    self.orbit_pitch  = clamp(self.orbit_pitch + dy * 0.3, 5.0, 70.0)
                    self.last_mouse   = event.pos

    def run(self):
        print("=" * 65)
        print("  SIMULASI GERHANA 3D — OpenGL Python (Updated)")
        print("=" * 65)
        print("  [F]      Toggle Free Camera (terbang bebas)")
        print("  W/A/S/D  Gerak maju/kiri/mundur/kanan (free cam)")
        print("  Q / E    Naik / turun (free cam)")
        print("  SHIFT    Terbang lebih cepat (free cam)")
        print("  SCROLL   Zoom kota ↔ Luar angkasa")
        print("  DRAG     Putar kamera (orbit mode)")
        print("  SPACE    Percepat gerhana (tahan)")
        print("  R        Reset siklus gerhana")
        print("  ESC      Keluar")
        print("-" * 65)
        print("  Gerhana terjadi otomatis dalam siklus. SPACE = fast-forward.")
        print("=" * 65)

        prev_time = time.time()
        while self.running:
            cur_time  = time.time()
            dt        = min(cur_time - prev_time, 0.05)
            prev_time = cur_time

            self._handle_events(dt)
            self._update(dt)
            self._render()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()

# ─────────────────────────── ENTRY POINT ─────────────────────────

if __name__ == '__main__':
    sim = EclipseSimulation()
    sim.run()