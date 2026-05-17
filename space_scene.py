"""
=============================================================
  FILE: space_scene.py
  Fungsi: Berisi controller gerhana BERBASIS FISIK SUDUT PLANET
          serta visualisasi Luar Angkasa + Efek Bintang Jatuh!
=============================================================
"""

import math
import random
from OpenGL.GL import *
from OpenGL.GLU import *
from config import *
from gl_engine import draw_sph, raw_sph, set_mat, lerp, lerp3, smoothstep, ease_sine, clamp

# ───────────────────────────────────────────────────────────
# KELAS PENGATUR WAKTU GERHANA (ECLIPSE CONTROLLER)
# ───────────────────────────────────────────────────────────
class EclipseController:
    """Mengatur fase gerhana murni dari seberapa dekat sudut Bulan dengan Matahari/Bumi."""
    def __init__(self, name):
        self.name = name
        self.intensity = 0.0
        self.phase = 'idle'
        
    def update_from_angles(self, moon_angle, target_angle):
        # Cari selisih sudut terpendek (antara -PI sampai PI)
        diff = (moon_angle - target_angle + math.pi) % (2 * math.pi) - math.pi
        dist = abs(diff)
        
        PEAK_DIST = 0.15     # Jarak sudut saat gerhana puncak
        ECLIPSE_DIST = 0.55  # Jarak sudut saat gerhana mulai/selesai
        
        if dist < PEAK_DIST:
            self.phase = 'peak'
            self.intensity = clamp(1.0 + 0.01 * math.sin(dist * 100), 0.95, 1.05)
        elif dist < ECLIPSE_DIST:
            self.phase = 'approach' if diff < 0 else 'recede'
            t = (ECLIPSE_DIST - dist) / (ECLIPSE_DIST - PEAK_DIST)
            self.intensity = ease_sine(t)
        else:
            self.phase = 'idle'
            self.intensity = 0.0

# ───────────────────────────────────────────────────────────
# KELAS SCENE LUAR ANGKASA
# ───────────────────────────────────────────────────────────
class SpaceScene:
    def __init__(self):
        random.seed(7)
        self.stars = [
            (random.uniform(-3000, 3000), random.uniform(-3000, 3000),
             random.uniform(-3000, 3000), random.uniform(0.5, 1.0)) 
            for _ in range(5000)
        ]
        self._star_list = None
        
        # --- FITUR BINTANG JATUH ---
        self.shooting_stars = [] 
        
        self.earth_angle = 0.0
        self.moon_angle  = 0.0
        self.earth_tilt  = 23.5
        
        self._orbit_list = None
        self._compile_stars()
        self._compile_orbits()

    def _compile_stars(self):
        self._star_list = glGenLists(1)
        glNewList(self._star_list, GL_COMPILE)
        glBegin(GL_POINTS)
        for sx, sy, sz, br in self.stars:
            glColor3f(br * 0.90, br * 0.95, br)
            glVertex3f(sx, sy, sz)
        glEnd()
        glEndList()

    def _compile_orbits(self):
        self._orbit_list = glGenLists(2)
        
        # Garis Orbit Bumi
        glNewList(self._orbit_list, GL_COMPILE)
        glBegin(GL_LINE_LOOP)
        for i in range(80): 
            glVertex3f(EARTH_ORBIT_R * math.cos(2*math.pi*i/80), 0, EARTH_ORBIT_R * math.sin(2*math.pi*i/80))
        glEnd()
        glEndList()

        # Garis Orbit Bulan
        glNewList(self._orbit_list + 1, GL_COMPILE)
        glBegin(GL_LINE_LOOP)
        for i in range(60): 
            glVertex3f(MOON_ORBIT_R * math.cos(2*math.pi*i/60), 0, MOON_ORBIT_R * math.sin(2*math.pi*i/60))
        glEnd()
        glEndList()

    def update(self, dt, speed_mul=1.0):
        self.earth_angle += EARTH_ORBIT_SPD * dt * speed_mul
        self.moon_angle  += MOON_ORBIT_SPD * dt * speed_mul
        
        # --- LOGIKA BINTANG JATUH ---
        # Peluang muncul bintang jatuh dipengaruhi kecepatan simulasi (SPACE)
        if random.random() < 0.02 * speed_mul:
            sx, sy, sz = random.uniform(-800, 800), random.uniform(-500, 800), random.uniform(-800, 800)
            vx, vy, vz = random.uniform(-1000, 1000), random.uniform(-1000, -500), random.uniform(-1000, 1000)
            life = random.uniform(0.5, 1.2)
            self.shooting_stars.append([sx, sy, sz, vx, vy, vz, life])
            
        # Update posisi bintang jatuh yang sedang melesat
        for ss in self.shooting_stars:
            ss[0] += ss[3] * dt; ss[1] += ss[4] * dt; ss[2] += ss[5] * dt
            ss[6] -= dt
            
        # Hapus bintang yang sisa umurnya sudah habis
        self.shooting_stars = [ss for ss in self.shooting_stars if ss[6] > 0]

    def get_positions(self):
        # Posisi Bumi
        ex = EARTH_ORBIT_R * math.cos(self.earth_angle)
        ey = EARTH_ORBIT_R * math.sin(self.earth_angle) * 0.06
        ez = EARTH_ORBIT_R * math.sin(self.earth_angle)
        
        # Posisi Bulan
        inc = math.radians(5.1)
        mx = ex + MOON_ORBIT_R * math.cos(self.moon_angle)
        my = ey + MOON_ORBIT_R * math.sin(self.moon_angle) * math.sin(inc)
        mz = ez + MOON_ORBIT_R * math.sin(self.moon_angle) * math.cos(inc)
        
        return (ex, ey, ez), (mx, my, mz)

    def draw(self, solar_t, lunar_t, sim_time):
        ep, mp = self.get_positions()
        ex, ey, ez = ep
        mx, my, mz = mp

        # 1. Gambar Bintang Diam
        glDisable(GL_LIGHTING)
        glPointSize(2.0)
        glCallList(self._star_list)
        
        # --- 2. RENDER BINTANG JATUH ---
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)
        glLineWidth(2.0)
        glBegin(GL_LINES)
        for ss in self.shooting_stars:
            glColor4f(1.0, 1.0, 1.0, min(1.0, ss[6])) 
            # Kepala bintang jatuh
            glVertex3f(ss[0], ss[1], ss[2])
            # Ekor bintang jatuh membentang ke belakang
            glVertex3f(ss[0] - ss[3]*0.1, ss[1] - ss[4]*0.1, ss[2] - ss[5]*0.1) 
        glEnd()
        glLineWidth(1.0)
        glDisable(GL_BLEND)
        glEnable(GL_LIGHTING)

        # 3. Gambar Matahari & Corona
        draw_sph(0, 0, 0, 95, 32, 16, (1.0, 0.95, 0.42), (4, 3.5, 1.2), 5, 0)
        
        glDisable(GL_LIGHTING)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE)
        pulse = 1.0 + 0.06 * math.sin(sim_time * 1.3) + 0.03 * math.sin(sim_time * 2.7)
        
        for rr, aa in [(130, 0.09), (165, 0.058), (205, 0.035), (250, 0.018)]:
            glColor4f(1, 0.70, 0.20, aa * (1.0 - solar_t * 0.5) * pulse)
            raw_sph(0, 0, 0, rr, 18, 10)
            
        if solar_t > 0.08:
            for rr, aa, cg, cb in [(115, 0.16, 0.82, 0.25), (155, 0.11, 0.58, 0.10), 
                                   (200, 0.07, 0.38, 0.04), (255, 0.04, 0.22, 0)]:
                glColor4f(1, cg, cb, aa * smoothstep(solar_t) * pulse)
                raw_sph(0, 0, 0, rr, 18, 10)
        glDisable(GL_BLEND)
        glEnable(GL_LIGHTING)

        # 4. Gambar Bumi
        glPushMatrix()
        glTranslatef(ex, ey, ez)
        glRotatef(self.earth_tilt, 0, 0, 1)
        glRotatef(sim_time * 15, 0, 1, 0)
        draw_sph(0, 0, 0, 68, 44, 22, (0.10, 0.35, 0.75), (0,0,0), 88, 0.6)
        
        glDisable(GL_LIGHTING)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        for lon, lat in [(20, 10), (80, 30), (-100, 40), (-60, -15), (135, -25), (30, -20)]:
            glColor4f(0.18, 0.52, 0.14, 0.72)
            glPushMatrix()
            glRotatef(lon, 0, 1, 0)
            glRotatef(lat, 1, 0, 0)
            raw_sph(0, 0, 0, 69.8, 12, 8)
            glPopMatrix()
        glColor4f(0.95, 0.97, 1, 0.28); raw_sph(0, 0, 0, 71.5, 28, 14)
        glColor4f(0.30, 0.55, 0.95, 0.10); raw_sph(0, 0, 0, 74, 22, 12)
        glDisable(GL_BLEND)
        glEnable(GL_LIGHTING)
        glPopMatrix()

        # 5. Gambar Bulan 
        mc = (0.82, 0.80, 0.74)
        mc = lerp3(mc, (0.15, 0.05, 0.05), lunar_t)
        mc = lerp3(mc, (0.05, 0.05, 0.05), solar_t) 
        me = lerp3((0, 0, 0), (0.42, 0.06, 0.01), lunar_t)
        draw_sph(mx, my, mz, 19, 26, 14, mc, me, 20, 0.3)

        # 6. Bayangan & Orbit
        if solar_t > 0.05: self._draw_solar_shadow(ex, ey, ez, mx, my, mz, solar_t)
        if lunar_t > 0.05: self._draw_lunar_shadow(mx, my, mz, lunar_t)
        self._draw_orbit_paths(ex, ey, ez)

    def _draw_solar_shadow(self, ex, ey, ez, mx, my, mz, t):
        alpha = smoothstep(t) * 0.62
        sr = lerp(5, 42, smoothstep(t))
        glDisable(GL_LIGHTING)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        
        glColor4f(0, 0, 0.05, alpha)
        glBegin(GL_TRIANGLE_FAN)
        glVertex3f(mx, my, mz)
        for i in range(29):
            a = 2 * math.pi * i / 28
            glVertex3f(ex + sr * math.cos(a), ey + sr * 0.3 * math.sin(a), ez + sr * math.sin(a))
        glEnd()
        glDisable(GL_BLEND)
        glEnable(GL_LIGHTING)

    def _draw_lunar_shadow(self, mx, my, mz, t):
        alpha = smoothstep(t) * 0.82
        glDisable(GL_LIGHTING)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glColor4f(0.06, 0, 0, alpha * 0.88); raw_sph(mx, my, mz, 20.5, 18, 12)
        glColor4f(0.32, 0.04, 0.02, alpha * 0.42); raw_sph(mx, my, mz, 22.5, 14, 10)
        glDisable(GL_BLEND)
        glEnable(GL_LIGHTING)

    def _draw_orbit_paths(self, ex, ey, ez):
        glDisable(GL_LIGHTING)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        
        glColor4f(0.4, 0.6, 0.8, 0.15)
        glCallList(self._orbit_list)
        
        glColor4f(0.7, 0.7, 0.75, 0.12)
        glPushMatrix()
        glTranslatef(ex, ey, ez)
        glCallList(self._orbit_list + 1)
        glPopMatrix()
        
        glDisable(GL_BLEND)
        glEnable(GL_LIGHTING)
