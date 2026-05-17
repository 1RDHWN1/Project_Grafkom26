"""
=============================================================
  FILE: main.py
  Fungsi: Entry point utama. Menggabungkan logika fisik 
          luar angkasa dengan visualisasi di scene kota,
          ditambah Kamera Momentum & Audio Crossfade.
=============================================================
"""

import math
import sys
import time
import os  # TAMBAHAN 1: Untuk mengecek file audio ada atau tidak

try:
    import pygame
    from pygame.locals import *
    from OpenGL.GL import *
    from OpenGL.GLU import *
except ImportError:
    print("Error: Library belum lengkap. Jalankan:")
    print("pip install PyOpenGL PyOpenGL_accelerate pygame")
    sys.exit(1)

# Import dari modul custom kita
from config import *
from gl_engine import clamp, lerp, lerp3, smoothstep
from city_scene import City
from space_scene import SpaceScene, EclipseController

# ───────────────────────────────────────────────────────────
# KELAS KAMERA BEBAS (DENGAN MOMENTUM/LICIN)
# ───────────────────────────────────────────────────────────
class FreeCamera:
    def __init__(self):
        self.pos = [0.0, 80.0, 280.0]
        self.vel = [0.0, 0.0, 0.0] # Vektor Kecepatan
        self.yaw = 180.0; self.pitch = -12.0
        self.accel = 350.0  # Kecepatan akselerasi
        self.friction = 0.88 # Friksi (semakin mendekati 1, semakin licin)
        self.sens = 0.17

    def apply(self):
        glLoadIdentity()
        y, p = math.radians(self.yaw), math.radians(self.pitch)
        fx, fy, fz = math.sin(y)*math.cos(p), math.sin(p), -math.cos(y)*math.cos(p)
        gluLookAt(*self.pos, self.pos[0]+fx, self.pos[1]+fy, self.pos[2]+fz, 0, 1, 0)

    def update(self, dt, keys, mdx, mdy):
        self.yaw += mdx * self.sens; self.pitch = clamp(self.pitch - mdy * self.sens, -89, 89)
        y, p = math.radians(self.yaw), math.radians(self.pitch)
        fx, fy, fz = math.sin(y)*math.cos(p), math.sin(p), -math.cos(y)*math.cos(p)
        rx, rz = math.cos(y), math.sin(y)
        
        move_spd = self.accel * (3.0 if (keys[K_LSHIFT] or keys[K_RSHIFT]) else 1.0) * dt
        
        if keys[K_w]: self.vel[0] += fx*move_spd; self.vel[1] += fy*move_spd; self.vel[2] += fz*move_spd
        if keys[K_s]: self.vel[0] -= fx*move_spd; self.vel[1] -= fy*move_spd; self.vel[2] -= fz*move_spd
        if keys[K_a]: self.vel[0] -= rx*move_spd; self.vel[2] -= rz*move_spd
        if keys[K_d]: self.vel[0] += rx*move_spd; self.vel[2] += rz*move_spd
        if keys[K_q]: self.vel[1] -= move_spd
        if keys[K_e]: self.vel[1] += move_spd
            
        self.vel[0] *= self.friction
        self.vel[1] *= self.friction
        self.vel[2] *= self.friction
        
        self.pos[0] += self.vel[0] * dt
        self.pos[1] += self.vel[1] * dt
        self.pos[2] += self.vel[2] * dt


# ───────────────────────────────────────────────────────────
# KELAS UTAMA SIMULASI
# ───────────────────────────────────────────────────────────
class EclipseSimulation:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(TITLE)
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), DOUBLEBUF | OPENGL)
        print("OpenGL Renderer:", glGetString(GL_RENDERER).decode())
        print("OpenGL Vendor:", glGetString(GL_VENDOR).decode())
        print("OpenGL Version:", glGetString(GL_VERSION).decode())
        
        # ========================================================
        # TAMBAHAN 2: INISIALISASI AUDIO BGM
        # ========================================================
        self.audio_ready = False
        try:
            pygame.mixer.init()
            self.ch_city = pygame.mixer.Channel(0)
            self.ch_space = pygame.mixer.Channel(1)
            
            # Pastikan file ada sebelum di-load agar tidak crash
            if os.path.exists('city.mp3') and os.path.exists('space.mp3'):
                self.snd_city = pygame.mixer.Sound('city.mp3')
                self.snd_space = pygame.mixer.Sound('space.mp3')
                
                # Mainkan berulang-ulang
                self.ch_city.play(self.snd_city, loops=-1)
                self.ch_space.play(self.snd_space, loops=-1)
                
                # Setel volume awal (karena mulai di kota, volume kota full)
                self.ch_city.set_volume(1.0)
                self.ch_space.set_volume(0.0)
                self.audio_ready = True
            else:
                print("Info: city.mp3 / space.mp3 tidak ditemukan. BGM dimatikan.")
        except Exception as e:
            print(f"Info: Sistem audio gagal dimuat ({e})")
        # ========================================================

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_LIGHT1)
        glDisable(GL_COLOR_MATERIAL) 
        glEnable(GL_NORMALIZE)
        glShadeModel(GL_SMOOTH)
        glEnable(GL_FOG)
        glFogi(GL_FOG_MODE, GL_LINEAR)
        
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(60.0, WIDTH/HEIGHT, 0.5, 10000.0)
        glMatrixMode(GL_MODELVIEW)

        self.scroll_t  = 0.0
        self.target_st = 0.0
        self.sim_time  = 0.0
        self._boost    = False
        
        self.solar_ctrl = EclipseController('Solar')
        self.lunar_ctrl = EclipseController('Lunar')
        self._ss = 0.0 
        self._sl = 0.0 
        self._sky = list(SKY_DAY)
        
        self.free_cam = False
        self.fcam = FreeCamera()
        self.o_pitch = 22.0
        self.o_yaw   = 35.0
        self.space_yaw   = 30.0
        self.space_pitch = 15.0
        self.mouse_dn = False
        self.last_m   = (0, 0)
        
        self.city  = City()
        self.space = SpaceScene()
        
        self.font_b = pygame.font.SysFont('Arial', 22, bold=True)
        self.font_s = pygame.font.SysFont('Arial', 14)
        self._hud_tex = None
        self._hud_data = None
        self._hud_next_update = 0.0
        self._hud_update_interval = 1.0 / 20.0
        
        self.clock = pygame.time.Clock()
        self.running = True

    def _apply_lights(self, dark_t, sun_pos=None):
        sr, sg, sb = lerp(1.0, 0.72, self._ss), lerp(0.96, 0.32, self._ss), lerp(0.86, 0.12, self._ss)
        bri = max(0.0, 1.0 - dark_t * 0.97)
        pos = list(sun_pos) + [0.0] if sun_pos else [300, 500, 200, 0]
        
        glLightfv(GL_LIGHT0, GL_POSITION, pos)
        glLightfv(GL_LIGHT0, GL_DIFFUSE,  [sr*bri, sg*bri, sb*bri, 1])
        glLightfv(GL_LIGHT0, GL_AMBIENT,  [max(0.05, 0.32*(1-dark_t)), max(0.05, 0.30*(1-dark_t)), max(0.08, 0.38*(1-dark_t)), 1])
        glLightfv(GL_LIGHT0, GL_SPECULAR, [sr*bri*0.4, sg*bri*0.4, sb*bri*0.3, 1])
        
        glow = dark_t * 0.35
        glLightfv(GL_LIGHT1, GL_POSITION, [0, 1, 0, 0])
        glLightfv(GL_LIGHT1, GL_DIFFUSE,  [glow*0.82, glow*0.65, glow*0.38, 1])
        glLightfv(GL_LIGHT1, GL_AMBIENT,  [0, 0, 0, 1])

    def _apply_fog(self, dark_t):
        if dark_t < 0.5: fc = lerp3(FOG_DAY, FOG_DUSK, dark_t * 2)
        else:            fc = lerp3(FOG_DUSK, FOG_NIGHT, (dark_t - 0.5) * 2)
        glFogfv(GL_FOG_COLOR, list(fc) + [1])
        glFogf(GL_FOG_START, lerp(320, 100, dark_t))
        glFogf(GL_FOG_END,   lerp(900, 420, dark_t))

    def _update(self, dt):
        self.sim_time  += dt
        self.scroll_t += (self.target_st - self.scroll_t) * min(1.0, dt * 4.5)
        self.scroll_t = clamp(self.scroll_t, 0.0, 1.0)
        
        # ========================================================
        # TAMBAHAN 3: MENGATUR VOLUME BERDASARKAN SCROLL KAMERA
        # ========================================================
        if self.audio_ready:
            self.ch_city.set_volume(1.0 - self.scroll_t)
            self.ch_space.set_volume(self.scroll_t)
        # ========================================================

        speed_mul = 5.0 if self._boost else 1.0
        self.space.update(dt, speed_mul=speed_mul)
        
        earth_ang = self.space.earth_angle
        moon_ang  = self.space.moon_angle
        sun_ang_rel = earth_ang + math.pi 
        
        self.solar_ctrl.update_from_angles(moon_ang, sun_ang_rel)
        self.lunar_ctrl.update_from_angles(moon_ang, earth_ang)
        
        sm = 2.5
        self._ss += (self.solar_ctrl.intensity - self._ss) * min(1.0, dt * sm)
        self._sl += (self.lunar_ctrl.intensity - self._sl) * min(1.0, dt * sm)
        dt_raw = max(self._ss, self._sl)
        
        if dt_raw < 0.40: tgt = lerp3(SKY_DAY, SKY_DUSK, dt_raw/0.40)
        else:             tgt = lerp3(SKY_DUSK, SKY_NIGHT, (dt_raw-0.40)/0.60)
        for i in range(3): self._sky[i] += (tgt[i] - self._sky[i]) * min(1.0, dt * 1.2)
        
        self.city.update(dt)
        
        if self.free_cam:
            keys = pygame.key.get_pressed()
            dx, dy = pygame.mouse.get_rel() if pygame.mouse.get_focused() else (0,0)
            self.fcam.update(dt, keys, dx, dy)

    def _get_sky_positions(self):
        sa = self.space.earth_angle + math.pi
        sx = 1000.0 * math.cos(sa)
        sz = 1000.0 * math.sin(sa)
        sy = 600.0 + 300.0 * math.sin(sa) 

        ma = self.space.moon_angle
        scale_m = 30.0 / 55.0  
        mx = 1000.0 * scale_m * math.cos(ma)
        mz = 1000.0 * scale_m * math.sin(ma)
        my = (600.0 + 300.0 * math.sin(ma)) * scale_m

        return (sx, sy, sz), (mx, my, mz)

    def _set_camera_city_orbit(self):
        d = lerp(175.0, 550.0, self.scroll_t); e = lerp(38.0, 180.0, self.scroll_t)
        pr = math.radians(self.o_pitch); yr = math.radians(self.o_yaw)
        cx, cz, cy = d * math.cos(pr) * math.sin(yr), d * math.cos(pr) * math.cos(yr), e + d * math.sin(pr) * 0.5
        glLoadIdentity(); gluLookAt(cx, cy, cz, 0, lerp(18, 70, self.scroll_t), 0, 0, 1, 0)

    def _set_camera_space_orbit(self):
        dist = 900; pr = math.radians(self.space_pitch); yr = math.radians(self.space_yaw)
        cx, cy, cz = dist * math.cos(pr) * math.sin(yr), dist * math.sin(pr), dist * math.cos(pr) * math.cos(yr)
        ep, _ = self.space.get_positions()
        glLoadIdentity(); gluLookAt(cx, cy, cz, ep[0]*0.4, ep[1]*0.4, ep[2]*0.4, 0, 1, 0)

    def _render(self):
        dark_t = max(self._ss, self._sl); st = self.scroll_t
        sky = lerp3(tuple(self._sky), (0.0, 0.0, 0.01), smoothstep(st))
        glClearColor(*sky, 1.0); glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        self._apply_fog(dark_t)
        
        (sx, sy, sz), (mx, my, mz) = self._get_sky_positions()
        self._apply_lights(dark_t, sun_pos=(sx, sy, sz))
        
        if self.free_cam: self.fcam.apply()
        elif st < 0.5:    self._set_camera_city_orbit()
        else:             self._set_camera_space_orbit()
        
        if st < 0.95:
            from city_scene import draw_city_sun, draw_city_moon
            
            draw_city_sun(sx, sy, sz, self._ss, dark_t, self.sim_time)
            draw_city_moon(mx, my, mz, self._sl, self._ss, dark_t, self.sim_time)
            
            glEnable(GL_DEPTH_TEST)
            self.city.draw(dark_t, self.sim_time)
            
        if st > 0.10:
            glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            self._set_camera_space_orbit(); glDisable(GL_FOG)
            
            glLightfv(GL_LIGHT0, GL_POSITION, [0, 0, 0, 1.0])
            glLightfv(GL_LIGHT0, GL_DIFFUSE,  [1.5, 1.4, 1.1, 1])
            glLightfv(GL_LIGHT0, GL_AMBIENT,  [0.02, 0.02, 0.03, 1])
            glLightfv(GL_LIGHT0, GL_SPECULAR, [0.8, 0.8, 0.7, 1])
            glLightf(GL_LIGHT0, GL_CONSTANT_ATTENUATION,  1.0)
            glLightf(GL_LIGHT0, GL_LINEAR_ATTENUATION,    0.0)
            glLightf(GL_LIGHT0, GL_QUADRATIC_ATTENUATION, 0.0)
            glLightfv(GL_LIGHT1, GL_DIFFUSE,  [0, 0, 0, 1])
            
            self.space.draw(self._ss, self._sl, self.sim_time)
            glEnable(GL_FOG); glDisable(GL_BLEND)
            
        self._overlay_hud()
        pygame.display.flip()

    def _overlay_hud(self):
        glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
        glOrtho(0, WIDTH, HEIGHT, 0, -1, 1); glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
        glDisable(GL_DEPTH_TEST); glDisable(GL_LIGHTING)
        glEnable(GL_BLEND); glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        should_update = self._hud_data is None or self.sim_time >= self._hud_next_update
        if should_update:
            self._hud_next_update = self.sim_time + self._hud_update_interval
            surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); surf.fill((0, 0, 0, 0))
            ps = {'approach': 'Mendekat', 'peak': 'PUNCAK', 'recede': 'Berlalu', 'idle': ''}
            labels = []

            if self.solar_ctrl.phase != 'idle': labels.append((f"GERHANA MATAHARI {int(self._ss*100)}% [{ps[self.solar_ctrl.phase]}]", (255, 215, 80)))
            if self.lunar_ctrl.phase != 'idle': labels.append((f"GERHANA BULAN {int(self._sl*100)}% [{ps[self.lunar_ctrl.phase]}]", (255, 135, 75)))

            if self.free_cam: labels.append(("FREE CAM AKTIF — W/A/S/D | Q/E | SHIFT | Tekan F untuk Keluar", (160, 255, 160)))
            else: labels.append(("[F] Free Cam  [Drag] Putar  [Scroll] Dimensi  [SPACE] Percepat x5  [R] Reset Orbit", (200, 200, 200)))

            y = 10
            for txt, col in labels:
                ts = self.font_s.render(txt, True, col)
                bg = pygame.Surface((ts.get_width() + 14, ts.get_height() + 5), pygame.SRCALPHA); bg.fill((0, 0, 0, 110))
                surf.blit(bg, (5, y - 2)); surf.blit(ts, (12, y)); y += 22

            if self._ss > 0.55:
                ts = self.font_b.render("GERHANA MATAHARI TOTAL", True, (255, 215, 62)); ts.set_alpha(int(smoothstep((self._ss - 0.55) * 2.2) * 255))
                surf.blit(ts, (WIDTH // 2 - ts.get_width() // 2, HEIGHT // 2 - 55))
            if self._sl > 0.55:
                ts = self.font_b.render("GERHANA BULAN TOTAL", True, (255, 110, 68)); ts.set_alpha(int(smoothstep((self._sl - 0.55) * 2.2) * 255))
                surf.blit(ts, (WIDTH // 2 - ts.get_width() // 2, HEIGHT // 2 - 20))

            bw, bh, mg = 270, 11, 20; yb = HEIGHT - 48
            for ctrl, label, col, x in [(self.solar_ctrl, "Posisi Orbit Matahari", (255, 205, 80), mg), (self.lunar_ctrl, "Posisi Orbit Bulan", (255, 130, 80), WIDTH - mg - bw)]:
                surf.blit(self.font_s.render(label, True, col), (x, yb - 17))
                bg = pygame.Surface((bw, bh), pygame.SRCALPHA); bg.fill((25, 25, 25, 150)); surf.blit(bg, (x, yb))
                fw = int(bw * ctrl.intensity)
                if fw > 0:
                    fill = pygame.Surface((fw, bh), pygame.SRCALPHA)
                    for px in range(fw): pygame.draw.line(fill, (int(lerp(col[0]*0.35, col[0], px/bw)), int(lerp(col[1]*0.35, col[1], px/bw)), int(lerp(col[2]*0.35, col[2], px/bw)), 200), (px, 0), (px, bh - 1))
                    surf.blit(fill, (x, yb))
                pygame.draw.rect(surf, (*col, 105), (x, yb, bw, bh), 1)

            self._hud_data = pygame.image.tostring(surf, "RGBA", True)

        if self._hud_tex is None:
            self._hud_tex = glGenTextures(1)
            glBindTexture(GL_TEXTURE_2D, self._hud_tex)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, WIDTH, HEIGHT, 0, GL_RGBA, GL_UNSIGNED_BYTE, self._hud_data)
        else:
            glBindTexture(GL_TEXTURE_2D, self._hud_tex)
            if should_update:
                glTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, WIDTH, HEIGHT, GL_RGBA, GL_UNSIGNED_BYTE, self._hud_data)
        glEnable(GL_TEXTURE_2D); glColor4f(1, 1, 1, 1)
        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex2f(0, HEIGHT); glTexCoord2f(1, 0); glVertex2f(WIDTH, HEIGHT)
        glTexCoord2f(1, 1); glVertex2f(WIDTH, 0); glTexCoord2f(0, 1); glVertex2f(0, 0)
        glEnd()
        glDisable(GL_TEXTURE_2D)
        glDisable(GL_BLEND); glEnable(GL_LIGHTING); glEnable(GL_DEPTH_TEST)
        glMatrixMode(GL_PROJECTION); glPopMatrix(); glMatrixMode(GL_MODELVIEW); glPopMatrix()

    def _handle_events(self):
        for ev in pygame.event.get():
            if ev.type == QUIT: self.running = False
            elif ev.type == KEYDOWN:
                if ev.key == K_ESCAPE: self.running = False
                elif ev.key == K_f:
                    self.free_cam = not self.free_cam
                    if self.free_cam: 
                        pygame.event.set_grab(True); pygame.mouse.set_visible(False)
                        self.fcam.vel = [0.0, 0.0, 0.0]
                        pygame.mouse.get_rel()
                    else: pygame.event.set_grab(False); pygame.mouse.set_visible(True)
                elif ev.key == K_SPACE: self._boost = True
                elif ev.key == K_r:
                    self.space.earth_angle = 0.0
                    self.space.moon_angle = 0.0
                elif ev.key in (K_UP, K_PAGEUP):    self.target_st = max(0.0, self.target_st - 0.18)
                elif ev.key in (K_DOWN, K_PAGEDOWN): self.target_st = min(1.0, self.target_st + 0.18)
            elif ev.type == KEYUP:
                if ev.key == K_SPACE: self._boost = False
            elif ev.type == MOUSEBUTTONDOWN:
                if not self.free_cam:
                    if ev.button == 1: self.mouse_dn = True; self.last_m = ev.pos
                    elif ev.button == 4: self.target_st = max(0.0, self.target_st - 0.13)
                    elif ev.button == 5: self.target_st = min(1.0, self.target_st + 0.13)
            elif ev.type == MOUSEBUTTONUP:
                if ev.button == 1: self.mouse_dn = False
            elif ev.type == MOUSEMOTION:
                if not self.free_cam and self.mouse_dn:
                    dx, dy = ev.pos[0] - self.last_m[0], ev.pos[1] - self.last_m[1]
                    if self.scroll_t > 0.5: self.space_yaw += dx * 0.38; self.space_pitch = clamp(self.space_pitch + dy * 0.28, -45, 70)
                    else: self.o_yaw += dx * 0.38; self.o_pitch = clamp(self.o_pitch + dy * 0.28, 5, 72)
                    self.last_m = ev.pos

    def run(self):
        print("╔══════════════════════════════════════════════════════╗")
        print("║  SIMULASI GERHANA 3D (Fisika Sinkron + Audio)        ║")
        print("╠══════════════════════════════════════════════════════╣")
        print("║  Sistem Modular Berhasil Dimuat!                     ║")
        print("║  [F]     Free Camera  |  W/A/S/D  Q/E  SHIFT         ║")
        print("║  Drag    Putar kamera |  Scroll   Pindah Dimensi     ║")
        print("║  SPACE   Percepat x5  |  R        Reset Waktu        ║")
        print("╚══════════════════════════════════════════════════════╝")
        
        prev_time = time.time()
        while self.running:
            now = time.time(); dt = min(now - prev_time, 0.05); prev_time = now
            self._handle_events(); self._update(dt); self._render(); self.clock.tick(FPS)
        pygame.quit(); sys.exit()

if __name__ == '__main__':
    EclipseSimulation().run()
