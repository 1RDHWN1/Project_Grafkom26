"""
=============================================================
  FILE: city_scene.py
  Fungsi: Berisi semua objek yang ada di kota (Gedung, Rumah, 
          Pohon, Mobil, Lampu, dan Matahari/Bulan dari POV Kota).
          Dilengkapi dengan FastCube Display List untuk FPS mulus.
=============================================================
"""

import math
import random
from OpenGL.GL import *
from OpenGL.GLU import *

# Import dari file modular kita sebelumnya
from config import *
from gl_engine import draw_sph, draw_cyl, raw_sph, set_mat, lerp, lerp3, smoothstep, clamp, warm_geometry_cache
# ───────────────────────────────────────────────────────────
# OPTIMASI DISPLAY LIST UNTUK KOTAK (FAST CUBE)
# ───────────────────────────────────────────────────────────
_CUBE_LIST = None
_CLOUD_LIST = None
_CAR_BODY_LIST = None
_CAR_ROOF_LIST = None
_CAR_TRIM_LIST = None
_CAR_HEADLIGHT_LIST = None
_CAR_TAILLIGHT_LIST = None

def init_fast_geometry():
    """Merekam bentuk kubus 1x1x1 ke dalam memori GPU satu kali saja."""
    global _CUBE_LIST, _CLOUD_LIST, _CAR_BODY_LIST, _CAR_ROOF_LIST, _CAR_TRIM_LIST, _CAR_HEADLIGHT_LIST, _CAR_TAILLIGHT_LIST
    if _CUBE_LIST is None:
        _CUBE_LIST = glGenLists(1)
        glNewList(_CUBE_LIST, GL_COMPILE)
        hx, hy, hz = 0.5, 0.5, 0.5
        glBegin(GL_QUADS)
        # Atas, Bawah, Depan, Belakang, Kiri, Kanan
        for nx, ny, nz, vs in [
            ( 0,  1,  0, [(-hx,  hy, -hz), ( hx,  hy, -hz), ( hx,  hy,  hz), (-hx,  hy,  hz)]),
            ( 0, -1,  0, [(-hx, -hy,  hz), ( hx, -hy,  hz), ( hx, -hy, -hz), (-hx, -hy, -hz)]),
            ( 0,  0,  1, [(-hx, -hy,  hz), ( hx, -hy,  hz), ( hx,  hy,  hz), (-hx,  hy,  hz)]),
            ( 0,  0, -1, [(-hx,  hy, -hz), ( hx,  hy, -hz), ( hx, -hy, -hz), (-hx, -hy, -hz)]),
            (-1,  0,  0, [(-hx, -hy, -hz), (-hx, -hy,  hz), (-hx,  hy,  hz), (-hx,  hy, -hz)]),
            ( 1,  0,  0, [( hx, -hy,  hz), ( hx, -hy, -hz), ( hx,  hy, -hz), ( hx,  hy,  hz)]),
        ]:
            glNormal3f(nx, ny, nz)
            for v in vs: glVertex3f(*v)
        glEnd()
        glEndList()

    if _CLOUD_LIST is None:
        _CLOUD_LIST = glGenLists(1)
        glNewList(_CLOUD_LIST, GL_COMPILE)
        for x, y, z, sx, sy, sz in [
            (0.0, 0.0, 0.0, 16.0, 6.0, 12.0),
            (4.0, 3.0, -2.0, 10.0, 8.0, 8.0),
            (-5.0, 2.0, 3.0, 8.0, 6.0, 8.0),
        ]:
            glPushMatrix()
            glTranslatef(x, y, z)
            glScalef(sx, sy, sz)
            glCallList(_CUBE_LIST)
            glPopMatrix()
        glEndList()

    def cube_list_item(x, y, z, sx, sy, sz):
        glPushMatrix()
        glTranslatef(x, y, z)
        glScalef(sx, sy, sz)
        glCallList(_CUBE_LIST)
        glPopMatrix()

    if _CAR_BODY_LIST is None:
        _CAR_BODY_LIST = glGenLists(1)
        glNewList(_CAR_BODY_LIST, GL_COMPILE)
        cube_list_item(0, 0.625, 0, 4.0, 1.25, 1.8)
        glEndList()

    if _CAR_ROOF_LIST is None:
        _CAR_ROOF_LIST = glGenLists(1)
        glNewList(_CAR_ROOF_LIST, GL_COMPILE)
        cube_list_item(0, 1.42, 0, 2.4, 0.72, 1.58)
        glEndList()

    if _CAR_TRIM_LIST is None:
        _CAR_TRIM_LIST = glGenLists(1)
        glNewList(_CAR_TRIM_LIST, GL_COMPILE)
        cube_list_item(0, 0.90, 0, 4.02, 0.18, 1.82)
        glEndList()

    if _CAR_HEADLIGHT_LIST is None:
        _CAR_HEADLIGHT_LIST = glGenLists(1)
        glNewList(_CAR_HEADLIGHT_LIST, GL_COMPILE)
        for sz in (-0.62, 0.62):
            cube_list_item(2.08, 0.68, sz, 0.11, 0.34, 0.40)
        glEndList()

    if _CAR_TAILLIGHT_LIST is None:
        _CAR_TAILLIGHT_LIST = glGenLists(1)
        glNewList(_CAR_TAILLIGHT_LIST, GL_COMPILE)
        for sz in (-0.62, 0.62):
            cube_list_item(-2.08, 0.68, sz, 0.11, 0.30, 0.35)
        glEndList()

def draw_box_fast(cx, cy, cz, sx, sy, sz, color, shin=32.0, spec=0.25, emit=(0,0,0)):
    """Menggambar kotak dengan memanggil list GPU, JAUH lebih cepat dari Immediate Mode."""
    set_mat(*color, spec=spec, shin=shin, emit=emit)
    glPushMatrix()
    glTranslatef(cx, cy, cz)
    glScalef(sx, sy, sz) # Tarik ukuran kubus 1x1 sesuai kebutuhan
    glCallList(_CUBE_LIST)
    glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, [0, 0, 0, 1])
    glPopMatrix()


# ───────────────────────────────────────────────────────────
# KELAS RUMAH
# ───────────────────────────────────────────────────────────
class House:
    WALL_COLORS = [
        (0.95, 0.88, 0.65), (0.92, 0.72, 0.58), (0.72, 0.88, 0.72), (0.72, 0.82, 0.95),
        (0.95, 0.82, 0.72), (0.88, 0.78, 0.95), (0.95, 0.95, 0.75), (0.82, 0.95, 0.88),
        (0.95, 0.72, 0.72), (0.78, 0.88, 0.98),
    ]
    ROOF_COLORS = [
        (0.62, 0.28, 0.22), (0.38, 0.35, 0.48), (0.28, 0.48, 0.32), (0.52, 0.38, 0.28),
        (0.22, 0.32, 0.52), (0.48, 0.28, 0.38), (0.55, 0.45, 0.22), (0.32, 0.42, 0.38),
    ]

    def __init__(self, x, z):
        self.x = x; self.z = z
        self.w = random.uniform(7, 11)
        self.d = random.uniform(7, 11)
        self.h = random.uniform(5, 9)
        self.rot = random.choice([0, 90])
        self.wall_c = random.choice(self.WALL_COLORS)
        self.roof_c = random.choice(self.ROOF_COLORS)
        self.door_c = (self.roof_c[0]*0.3, self.roof_c[1]*0.2, self.roof_c[2]*0.1)
        self.win_c  = (0.75, 0.88, 0.98)
        self.roof_type = random.choice(['gable', 'hip', 'flat'])
        self.has_chimney = random.random() > 0.45
        self.fence_c = (0.85, 0.82, 0.75)

    def draw(self, dark_t):
        wc = lerp3(self.wall_c, tuple(x*0.18 for x in self.wall_c), dark_t)
        rc = lerp3(self.roof_c, tuple(x*0.15 for x in self.roof_c), dark_t)
        dc = lerp3(self.door_c, (0.05,0.04,0.03), dark_t)
        fc = lerp3(self.fence_c,(0.25,0.22,0.20), dark_t)

        glPushMatrix()
        glTranslatef(self.x, 0, self.z)
        glRotatef(self.rot, 0, 1, 0)

        w, d, h = self.w, self.d, self.h

        # Fondasi & Dinding
        fond_c = lerp3((0.68,0.65,0.60),(0.20,0.18,0.16),dark_t)
        draw_box_fast(0, 0.25, 0, w+0.4, 0.5, d+0.4, fond_c, 10)
        draw_box_fast(0, h/2+0.5, 0, w, h, d, wc, 30)

        # Jendela depan
        win_em = lerp3((0,0,0),(0.9,0.88,0.65), clamp(dark_t*2,0,1))
        for wx in (-w*0.25, w*0.25):
            draw_box_fast(wx, h*0.55+0.5, d/2+0.05, w*0.18, h*0.25, 0.12, self.win_c, 15, 0.4, emit=win_em)
            draw_box_fast(wx, h*0.55+0.5, d/2+0.06, w*0.22, h*0.29, 0.08, wc, 20)

        # Pintu
        door_em = lerp3((0,0,0),(0.3,0.25,0.18), clamp(dark_t*1.5,0,1))
        draw_box_fast(0, h*0.28+0.5, d/2+0.05, w*0.18, h*0.45, 0.12, dc, 20, emit=door_em)
        draw_box_fast(0, h*0.28+0.5, d/2+0.06, w*0.22, h*0.49, 0.08, wc, 15)

        # Jendela Samping
        for side, nx in [(d/2+0.05, 1), (-d/2-0.05, -1)]:
            draw_box_fast(0, h*0.55+0.5, side if nx==1 else -side, 0.12, h*0.22, w*0.16, self.win_c, 15, 0.4, emit=win_em)

        # Atap (Manual geometry karena bentuknya segitiga/miring)
        roof_h = h * 0.50
        if self.roof_type == 'gable':
            steps = 2 # Dioptimasi dari 10 ke 2 steps karena flat shading cukup
            for i in range(steps):
                t1 = i/steps; t2=(i+1)/steps
                y1 = h+0.5 + t1*roof_h; y2 = h+0.5 + t2*roof_h
                z1 = (d/2)*(1-t1);      z2 = (d/2)*(1-t2)
                set_mat(*rc, spec=0.2, shin=15)
                glBegin(GL_QUADS)
                glNormal3f(0, z1, d/2)
                glVertex3f(-w/2-0.3, y1, z1+0.3); glVertex3f( w/2+0.3, y1, z1+0.3)
                glVertex3f( w/2+0.3, y2, z2);     glVertex3f(-w/2-0.3, y2, z2)
                glEnd()
                glBegin(GL_QUADS)
                glNormal3f(0, z1, -d/2)
                glVertex3f(-w/2-0.3, y1, -z1-0.3); glVertex3f( w/2+0.3, y1, -z1-0.3)
                glVertex3f( w/2+0.3, y2, -z2);     glVertex3f(-w/2-0.3, y2, -z2)
                glEnd()
            set_mat(*rc, spec=0.2, shin=15)
            for sx2 in (-w/2-0.3, w/2+0.3):
                glBegin(GL_TRIANGLES)
                glNormal3f(-1 if sx2<0 else 1, 0, 0)
                glVertex3f(sx2, h+0.5, d/2+0.3); glVertex3f(sx2, h+0.5, -d/2-0.3); glVertex3f(sx2, h+0.5+roof_h, 0)
                glEnd()

        elif self.roof_type == 'hip':
            top_y = h+0.5+roof_h
            set_mat(*rc, spec=0.2, shin=15)
            for (x1a,z1a,x1b,z1b,x2,z2,nx2,nz2) in [
                (-w/2-0.3,-d/2-0.3, w/2+0.3,-d/2-0.3,  0,-d/2+2,  0,-1),
                (-w/2-0.3, d/2+0.3, w/2+0.3, d/2+0.3,  0, d/2-2,  0, 1),
                (-w/2-0.3,-d/2-0.3,-w/2-0.3, d/2+0.3, -w/2+2,0,  -1, 0),
                ( w/2+0.3,-d/2-0.3, w/2+0.3, d/2+0.3,  w/2-2,0,   1, 0),
            ]:
                glBegin(GL_TRIANGLES)
                glNormal3f(nx2,0.5,nz2)
                glVertex3f(x1a,h+0.5,z1a); glVertex3f(x1b,h+0.5,z1b); glVertex3f(x2,top_y,z2)
                glEnd()
            draw_box_fast(0, top_y-0.2, 0, 0.5, 0.4, 0.5, rc, 20)
        else:
            draw_box_fast(0, h+0.5+0.25, 0, w+0.5, 0.5, d+0.5, rc, 20)
            for px2,pz2,pw2,pd2 in [(0, d/2+0.25, w+0.6, 0.5), (0,-d/2-0.25, w+0.6, 0.5), ( w/2+0.25, 0, 0.5, d+0.6), (-w/2-0.25, 0, 0.5, d+0.6)]:
                draw_box_fast(px2, h+0.5+0.65, pz2, pw2, 0.8, pd2, rc, 20)

        # Cerobong & Pagar
        if self.has_chimney:
            ch_c = lerp3((0.62,0.32,0.25),(0.18,0.09,0.07),dark_t)
            draw_box_fast(w*0.3, h+0.5+roof_h*0.55, -d*0.1, 1.2, roof_h*0.8, 1.2, ch_c, 20)
            draw_box_fast(w*0.3, h+0.5+roof_h*0.95+0.3, -d*0.1, 1.5, 0.4, 1.5, ch_c, 20)
            
        num_posts = int(w/2)
        for pi in range(num_posts+1):
            draw_box_fast(-w/2 + pi*(w/num_posts), 0.8, d/2+0.6, 0.18, 1.2, 0.18, fc, 15)
        draw_box_fast(0, 1.2, d/2+0.6, w+0.1, 0.12, 0.12, fc, 15)
        draw_box_fast(0, 0.6, d/2+0.6, w+0.1, 0.10, 0.10, fc, 15)
        glPopMatrix()

# ───────────────────────────────────────────────────────────
# KELAS GEDUNG TINGGI
# ───────────────────────────────────────────────────────────
class Building:
    PALETTE = [
        ((0.72,0.58,0.42),(0.88,0.76,0.55),(0.98,0.78,0.28)), ((0.28,0.45,0.68),(0.40,0.60,0.85),(0.60,0.88,1.00)),
        ((0.65,0.28,0.28),(0.80,0.42,0.38),(1.00,0.58,0.42)), ((0.28,0.52,0.36),(0.40,0.70,0.50),(0.62,1.00,0.62)),
        ((0.52,0.38,0.65),(0.68,0.52,0.85),(0.92,0.72,1.00)), ((0.22,0.40,0.52),(0.35,0.55,0.70),(0.52,0.82,1.00)),
        ((0.65,0.50,0.28),(0.82,0.65,0.38),(1.00,0.84,0.42)), ((0.38,0.38,0.44),(0.55,0.55,0.62),(0.80,0.88,0.98)),
    ]
    TYPES = ['tower','slab','stepped']

    def __init__(self,x,z,w,d,h):
        self.x=x;self.z=z;self.w=w;self.d=d;self.h=h
        p=random.choice(self.PALETTE)
        self.cl=p[0];self.ch=p[1];self.ca=p[2]
        self.btype=random.choice(self.TYPES)
        self.windows=[]
        rows=max(2,int(h/6)); cols=max(2,int(w/4))
        for row in range(rows):
            for col in range(cols):
                wx=-w/2+(col+0.5)*(w/cols)+random.uniform(-0.2,0.2)
                wy=3+row*(h-4)/max(rows-1,1)
                self.windows.append((wx,wy,random.random()>0.32,random.random()>0.82,random.random()*6.28,random.uniform(0.65,1.0)))
        self.has_ant=h>60 and random.random()>0.4

    def draw(self,dark_t,sim_time=0.0):
        h=self.h
        cl=lerp3(self.cl,tuple(x*0.20 for x in self.cl),dark_t)
        ch=lerp3(self.ch,tuple(x*0.16 for x in self.ch),dark_t)
        ca=lerp3(self.ca,tuple(x*0.14 for x in self.ca),dark_t)
        
        if self.btype=='slab':
            draw_box_fast(self.x,h*0.425,self.z,self.w*1.6,h*0.85,self.d*0.6,cl,32)
            draw_box_fast(self.x,h*0.925,self.z,self.w*0.9,h*0.15,self.d*0.6,ch,48)
            gc=lerp3((0.48,0.64,0.84),(0.04,0.04,0.12),dark_t)
            draw_box_fast(self.x,h*0.425,self.z,self.w*1.6+0.2,h*0.85,self.d*0.6+0.2,gc,90,0.66)
        elif self.btype=='stepped':
            draw_box_fast(self.x,h*0.30,self.z,self.w,h*0.60,self.d,cl,32)
            draw_box_fast(self.x,h*0.70,self.z,self.w*0.70,h*0.40,self.d*0.70,ch,44)
            draw_box_fast(self.x,h*0.92,self.z,self.w*0.40,h*0.16,self.d*0.40,ca,54)
        else: # tower
            draw_box_fast(self.x,self.h/2,self.z,self.w,self.h,self.d,cl,38)
            gc=lerp3((0.40,0.58,0.82),(0.04,0.04,0.14),dark_t)
            draw_box_fast(self.x,self.h/2,self.z,self.w+0.18,self.h+0.1,self.d+0.18,gc,92,0.70)
            
        for frac in [0.33,0.66,1.0]: draw_box_fast(self.x,frac*h,self.z,self.w+0.5,0.6,self.d+0.5,ca,55,0.5)
        
        if self.has_ant:
            draw_cyl(self.x,h,self.z,0.18,0.10,12,6,lerp3((0.55,0.55,0.60),(0.18,0.18,0.22),dark_t))
            draw_sph(self.x,h+12.5,self.z,0.42,8,6,(0.90,0.10,0.10),lerp3((0,0,0),(1.0,0.1,0.1),clamp(dark_t*2,0,1)),18)
            
        if dark_t>0.08:
            for wx,wy,lit,flk,fp,base_intensity in self.windows:
                if not lit: continue
                fl=(0.85+0.15*math.sin(sim_time*5.8+fp)) if flk else 1.0
                intensity=smoothstep(dark_t)*base_intensity*fl
                wc=lerp3((0,0,0),(1.0,0.96,0.68),intensity) if sum(self.ca)>2.1 else lerp3((0,0,0),(0.72,0.90,1.00),intensity)
                em2=wc if intensity>0.42 else (0,0,0)
                draw_box_fast(self.x+wx,wy,self.z+self.d/2+0.07,1.0,1.2,0.12,wc,4,0.0,emit=em2)
                draw_box_fast(self.x+wx,wy,self.z-self.d/2-0.07,1.0,1.2,0.12,wc,4,0.0,emit=em2)

# ───────────────────────────────────────────────────────────
# KELAS POHON
# ───────────────────────────────────────────────────────────
class Tree:
    LEAF_COLORS = [(0.20,0.62,0.18), (0.28,0.72,0.22), (0.15,0.52,0.28), (0.38,0.70,0.25), (0.22,0.58,0.42)]
    FLOWER_COLORS = [(0.98,0.72,0.82), (0.98,0.92,0.65), (0.82,0.72,0.98), (0.98,0.78,0.62), (0.72,0.88,0.98)]

    def __init__(self, x, z, scale=1.0):
        self.x = x; self.z = z; self.scale = scale
        self.leaf_c   = random.choice(self.LEAF_COLORS)
        self.leaf2_c  = tuple(min(1,c*1.15) for c in self.leaf_c)
        self.trunk_c  = (0.42, 0.28, 0.14)
        self.has_flower = random.random() > 0.55
        self.flower_c = random.choice(self.FLOWER_COLORS)
        self.ttype = random.choice(['round','cone','multi'])

    def draw(self, dark_t):
        s = self.scale
        tc = lerp3(self.trunk_c, (0.14,0.09,0.04), dark_t)
        lc = lerp3(self.leaf_c,  (0.04,0.10,0.02), dark_t)
        l2 = lerp3(self.leaf2_c, (0.05,0.12,0.03), dark_t)
        fc = lerp3(self.flower_c,(0.25,0.14,0.18), dark_t)

        if self.ttype == 'round':
            draw_cyl(self.x,0,self.z,0.3*s,0.25*s,3.5*s,8,tc)
            draw_sph(self.x,5*s,self.z,2.5*s,12,8,lc,(0,0,0),8)
            draw_sph(self.x,6.2*s,self.z,1.8*s,10,7,l2,(0,0,0),8)
            if self.has_flower: draw_sph(self.x,7.0*s,self.z,1.0*s,8,6,fc,(0,0,0),12)
        elif self.ttype == 'cone':
            draw_cyl(self.x,0,self.z,0.3*s,0.22*s,4*s,8,tc)
            for i,(yr,rr) in enumerate([(3,2.2),(5,1.6),(7,1.1),(9,0.6)]):
                draw_sph(self.x,yr*s,self.z,rr*s,10,7,lc if i%2==0 else l2,(0,0,0),8)
        else:
            draw_cyl(self.x,0,self.z,0.35*s,0.30*s,3*s,8,tc)
            for dx2,dz2,dy2 in [(1.2,0,4.5),(-1.0,0.8,5.0),(0,-1.1,4.8)]:
                draw_cyl(self.x+dx2*s*0.5,3*s,self.z+dz2*s*0.5,0.22*s,0.18*s,2*s,6,tc)
                draw_sph(self.x+dx2*s,dy2*s,self.z+dz2*s,1.8*s,10,7,lc,(0,0,0),8)
            if self.has_flower: draw_sph(self.x,6.5*s,self.z,0.9*s,8,6,fc,(0,0,0),12)

# ───────────────────────────────────────────────────────────
# KELAS AWAN LOW-POLY
# ───────────────────────────────────────────────────────────
class Cloud:
    def __init__(self, x, y, z):
        self.x = x; self.y = y; self.z = z
        self.speed = random.uniform(5.0, 15.0)
        self.scale = random.uniform(0.8, 1.8)

    def update(self, dt):
        # Awan bergerak lambat ke arah X positif
        self.x += self.speed * dt
        # Kalau sudah melewati batas kota, respawn di ujung sebaliknya
        if self.x > 250: self.x = -250

    def draw(self, dark_t):
        # Warna awan: Putih bersih saat siang, berubah jadi abu-abu gelap saat gerhana
        c = lerp3((0.98, 0.98, 0.98), (0.15, 0.15, 0.18), dark_t)
        s = self.scale

        set_mat(*c, spec=0.0, shin=5)
        glPushMatrix()
        glTranslatef(self.x, self.y, self.z)
        glScalef(s, s, s)
        glCallList(_CLOUD_LIST)
        glPopMatrix()


# ───────────────────────────────────────────────────────────
# KELAS MOBIL & TRAFFIC LIGHT
# ───────────────────────────────────────────────────────────
class Car:
    COLORS=[(0.92,0.12,0.12),(0.12,0.32,0.92),(0.10,0.80,0.22),(0.98,0.80,0.08),
            (0.96,0.96,0.96),(0.10,0.10,0.10),(0.80,0.28,0.92),(0.98,0.52,0.08)]
    ROOF=[(0.70,0.06,0.06),(0.06,0.20,0.72),(0.06,0.60,0.14),(0.80,0.62,0.04),
          (0.72,0.72,0.72),(0.22,0.22,0.22),(0.60,0.14,0.72),(0.78,0.34,0.04)]

    def __init__(self,x,z,direction):
        self.x=x;self.z=z;self.direction=direction
        self.speed=random.uniform(0.20,0.50)
        idx=random.randint(0,len(self.COLORS)-1)
        self.color=self.COLORS[idx];self.roof_c=self.ROOF[idx]
        self.stopped=False; self.w=1.8;self.h=1.25;self.l=4.0
        self._angle={'px':0,'nx':180,'pz':90,'nz':-90}[direction];self._wr=0.0

    def update(self,dt,tls):
        self.stopped=self._chk(tls)
        if not self.stopped:
            spd=self.speed*20*dt; self._wr=(self._wr+spd*28)%360
            if   self.direction=='px': self.x = -220 if self.x+spd > 220 else self.x+spd
            elif self.direction=='nx': self.x = 220 if self.x-spd < -220 else self.x-spd
            elif self.direction=='pz': self.z = -220 if self.z+spd > 220 else self.z+spd
            elif self.direction=='nz': self.z = 220 if self.z-spd < -220 else self.z-spd

    def _chk(self,tls):
        for ix in [0,100,-100]:
            for iz in [0,100,-100]:
                if self.direction in ('px','nx'):
                    dx=ix-self.x
                    if 2<abs(dx)<12 and abs(self.z-iz)<10:
                        if (self.direction=='px' and dx>0) or (self.direction=='nx' and dx<0):
                            tl=next((t for t in tls if math.sqrt((t.x-ix)**2+(t.z-iz)**2)<20),None)
                            if tl and tl.state!='green': return True
                else:
                    dz=iz-self.z
                    if 2<abs(dz)<12 and abs(self.x-ix)<10:
                        if (self.direction=='pz' and dz>0) or (self.direction=='nz' and dz<0):
                            tl=next((t for t in tls if math.sqrt((t.x-ix)**2+(t.z-iz)**2)<20),None)
                            if tl and tl.state!='green': return True
        return False

    def draw(self,dark_t):
        glPushMatrix();glTranslatef(self.x,0,self.z);glRotatef(self._angle,0,1,0)
        c=self.color;rc=self.roof_c
        set_mat(*c, spec=0.25, shin=60)
        glCallList(_CAR_BODY_LIST)
        set_mat(0.06,0.10,0.20, spec=0.72, shin=90)
        glCallList(_CAR_ROOF_LIST)
        set_mat(*rc, spec=0.38, shin=38)
        glCallList(_CAR_TRIM_LIST)
        
        hl=lerp3((0,0,0),(1,0.98,0.88),clamp(dark_t*3.5,0,1))
        set_mat(1,0.98,0.90, spec=0.1, shin=8, emit=hl)
        glCallList(_CAR_HEADLIGHT_LIST)
        glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, [0, 0, 0, 1])
        bc=(1,0.08,0.05) if self.stopped else (0.52,0,0)
        set_mat(*bc, spec=0.0, shin=8, emit=lerp3((0,0,0),bc,clamp(dark_t*2.5,0,1)))
        glCallList(_CAR_TAILLIGHT_LIST)
        glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, [0, 0, 0, 1])
        
        for wx,wz in [(1.22,0.96),(1.22,-0.96),(-1.22,0.96),(-1.22,-0.96)]:
            glPushMatrix();glTranslatef(wx,0.14,wz);glRotatef(90,0,1,0);glRotatef(self._wr,1,0,0)
            draw_cyl(0,0,-0.09,0.30,0.30,0.18,12,(0.09,0.09,0.09))
            glPopMatrix()
        glPopMatrix()

class TrafficLight:
    PHASES=[('green',4.0),('yellow',1.2),('red',3.5)]
    def __init__(self,x,z,offset=0.0):
        self.x=x;self.z=z;self.state='green';self._pi=0
        self._t=offset%8.7;acc=0
        for i,(s,d) in enumerate(self.PHASES):
            acc+=d
            if self._t<acc: self._pi=i;self._t-=(acc-d);self.state=s;break
    def update(self,dt):
        self._t+=dt
        if self._t>=self.PHASES[self._pi][1]:
            self._t-=self.PHASES[self._pi][1];self._pi=(self._pi+1)%3;self.state=self.PHASES[self._pi][0]
    def draw_body(self):
        draw_cyl(self.x,0,self.z,0.16,0.16,10,8,(0.12,0.12,0.12))
        draw_box_fast(self.x,11,self.z,0.85,3.0,0.72,(0.06,0.06,0.06))
    def draw_lights(self):
        for y,bc,sn in [(12.3,(0.7,0,0),'red'),(11.0,(0.6,0.5,0),'yellow'),(9.7,(0,0.6,0),'green')]:
            draw_sph(self.x,y,self.z-0.04,0.30,10,7,bc,bc if self.state==sn else (0,0,0),20)
    def draw(self):
        self.draw_body()
        self.draw_lights()

# ───────────────────────────────────────────────────────────
# CITY MANAGER UTAMA
# ───────────────────────────────────────────────────────────
class City:
    def __init__(self):
        init_fast_geometry() # WAJIB DIPANGGIL! Compile kotak ke GPU
        warm_geometry_cache(
            sphere_keys=[(6,5), (8,6), (10,7), (12,8)],
            cylinder_segments=[4, 6, 8, 12],
        )
        self.buildings=[]; self.houses=[]; self.trees=[]
        self.tls=[]; self.cars=[]; self.lamps=[]
        self.clouds=[]
        self._static_lists = {}
        self._build()

    def _build(self):
        random.seed(42)
        # Gedung Tinggi
        for cx,cz,cnt,sx,sz,sc in [(-65,-65,6,30,30,1.20),(65,-65,6,30,30,1.05),(-65,65,6,30,30,1.10),(65,65,6,30,30,1.28),(-140,0,4,22,42,0.88),(140,0,4,22,42,0.88),(0,-140,4,42,22,0.82),(0,140,4,42,22,0.82)]:
            for _ in range(cnt):
                bx=cx+random.uniform(-sx,sx); bz=cz+random.uniform(-sz,sz)
                if abs(bx)<16 or abs(bz)<16 or abs(abs(bx)-100)<16 or abs(abs(bz)-100)<16: continue
                self.buildings.append(Building(bx,bz,random.uniform(10,20)*sc,random.uniform(10,20)*sc,random.uniform(35,100)*sc))
            for _ in range(8):
                self.clouds.append(Cloud(random.uniform(-250, 250), random.uniform(110, 200), random.uniform(-250, 250)))

        # Rumah & Pohon
        placed_h = []
        for xmn,zmn,xmx,zmx,cnt in [(-140,-140,170,170,16), (140,-140,170,170,14), (-170,140,140,170,14), (140,140,170,170,14), (-170,-60,-100,60,12), (100,-60,170,60,12), (-60,-170,60,-100,10), (-60,100,60,170,10)]:
            for _ in range(cnt*3):
                if len([h for h in placed_h if xmn<=h[0]<=xmx and zmn<=h[1]<=zmx]) >= cnt: break
                hx, hz = random.uniform(min(xmn,xmx),max(xmn,xmx)), random.uniform(min(zmn,zmx),max(zmn,zmx))
                if abs(hx)<15 or abs(hz)<15 or abs(abs(hx)-100)<15 or abs(abs(hz)-100)<15 or any(math.sqrt((hx-px)**2+(hz-pz)**2)<18 for px,pz in placed_h): continue
                placed_h.append((hx,hz)); self.houses.append(House(hx,hz))

        for i in range(-18,19,3):
            for side in [-13,13]:
                if abs(i*10)>12: self.trees+=[Tree(i*10,side,random.uniform(0.8,1.2)), Tree(side,i*10,random.uniform(0.8,1.2))]

        # Trafik & Mobil
        for ix in [0,100,-100]:
            for iz in [0,100,-100]:
                for ox,oz in [(8,8),(-8,8),(8,-8),(-8,-8)]: self.tls.append(TrafficLight(ix+ox,iz+oz,random.uniform(0,8.7)))
        for _ in range(10): self.cars+=[Car(random.uniform(-200,200),4.5,'px'), Car(random.uniform(-200,200),-4.5,'nx'), Car(4.5,random.uniform(-200,200),'pz'), Car(-4.5,random.uniform(-200,200),'nz')]

        # Lampu Jalan
        for i in range(-18,19,3):
            for side in [-12,12]: self.lamps+=[(i*10,0,side),(side,0,i*10)]

    def update(self,dt):
        for tl in self.tls: tl.update(dt)
        for c  in self.cars: c.update(dt,self.tls)
        for cl in self.clouds: cl.update(dt)

    def draw(self,dark_t,sim_time=0.0):
        if PERFORMANCE_STATIC_CITY_CACHE:
            self._draw_static_cached(dark_t)
        else:
            self._draw_static(dark_t, sim_time)

        for tl in self.tls:       tl.draw_lights()
        for c  in self.cars:      c.draw(dark_t)
        for cl in self.clouds:    cl.draw(dark_t)

    def _draw_static(self,dark_t,sim_time=0.0):
        self._ground(dark_t)
        for b  in self.buildings: b.draw(dark_t,sim_time)
        for h  in self.houses:    h.draw(dark_t)
        for t  in self.trees:     t.draw(dark_t)
        for tl in self.tls:       tl.draw_body()
        self._lamps(dark_t)
        self._park(dark_t)

    def _draw_static_cached(self,dark_t):
        bucket_count = max(1, CITY_STATIC_LIGHT_BUCKETS)
        bucket = int(round(clamp(dark_t, 0.0, 1.0) * bucket_count))
        list_id = self._static_lists.get(bucket)

        if list_id is None:
            list_id = glGenLists(1)
            self._static_lists[bucket] = list_id
            bucket_dark = bucket / bucket_count
            glNewList(list_id, GL_COMPILE)
            self._draw_static(bucket_dark, 0.0)
            glEndList()

        glCallList(list_id)

    def _ground(self,dt):
        rc, wc = lerp3((0.18,0.18,0.18),(0.04,0.04,0.07),dt), lerp3((0.42,0.38,0.30),(0.12,0.10,0.09),dt)
        gc, mk = lerp3((0.28,0.58,0.18),(0.05,0.10,0.03),dt), lerp3((0.95,0.92,0.12),(0.38,0.35,0.04),dt)
        pv = lerp3((0.55,0.52,0.45),(0.14,0.12,0.10),dt)

        draw_box_fast(0,-0.5,0,520,1,520,gc,5)
        draw_box_fast(0,0.05,0,26,0.1,26,lerp3((0.32,0.65,0.22),(0.08,0.15,0.04),dt),8)

        for zp in [0,100,-100]:
            draw_box_fast(0,0.05,zp,450,0.12,22,rc,5)
            for xi in range(-22,23): draw_box_fast(xi*20,0.07,zp,8,0.1,0.28,mk,4)
            for side in [-12,12]:
                draw_box_fast(0,0.32,zp+side,450,0.65,4,pv,10)
                draw_box_fast(0,0.12,zp+side,450,0.24,1.5,lerp3((0.25,0.55,0.15),(0.05,0.10,0.03),dt),5)
        for xp in [0,100,-100]:
            draw_box_fast(xp,0.05,0,22,0.12,450,rc,5)
            for zi in range(-22,23): draw_box_fast(xp,0.07,zi*20,0.28,0.1,8,mk,4)
            for side in [-12,12]: draw_box_fast(xp+side,0.32,0,4,0.65,450,pv,10)

    def _lamps(self,dt):
        pc = lerp3((0.30,0.28,0.25),(0.10,0.09,0.08),dt)
        em = lerp3((0,0,0),(1.00,0.82,0.45),clamp(dt*2.2,0,1))
        for lx,_,lz in self.lamps:
            draw_cyl(lx,0,lz,0.14,0.14,8.5,8,pc)
            draw_box_fast(lx+0.7,8.8,lz,1.4,0.14,0.14,pc)
            draw_sph(lx+1.2,9.1,lz,0.55,8,6,(0.98,0.88,0.55),em,10)

    def _park(self,dt):
        gc = lerp3((0.28,0.65,0.18),(0.05,0.13,0.02),dt)
        draw_box_fast(0,0.12,0,22,0.25,22,gc,5)
        draw_box_fast(0,0.2,0,8,0.15,8,lerp3((0.35,0.65,0.95),(0.08,0.16,0.28),dt),60,0.6)
        for bx,bz in [(5,5),(-5,5),(5,-5),(-5,-5)]:
            draw_box_fast(bx,0.55,bz,2.5,0.4,0.8,lerp3((0.55,0.38,0.22),(0.15,0.10,0.06),dt),15)
            for lx2 in (-0.9,0.9): draw_cyl(bx+lx2,0,bz,0.1,0.1,0.55,6,lerp3((0.35,0.28,0.20),(0.10,0.08,0.05),dt))
        for fx,fz,fc in [(3,0,(0.98,0.32,0.48)),(-3,0,(0.98,0.88,0.32)),(0,3,(0.55,0.32,0.98)),(0,-3,(0.32,0.88,0.98)),(2.5,2.5,(0.98,0.62,0.32)),(-2.5,2.5,(0.32,0.98,0.58))]:
            draw_sph(fx,0.8,fz,0.55,6,5,lerp3(fc,tuple(x*0.2 for x in fc),dt),(0,0,0),12)
            draw_cyl(fx,0,fz,0.06,0.06,0.8,4,lerp3((0.25,0.58,0.15),(0.06,0.14,0.04),dt))

# ───────────────────────────────────────────────────────────
# MATAHARI & BULAN (HELPER UNTUK RENDER DI KOTA)
# ───────────────────────────────────────────────────────────
def draw_city_sun(sx, sy, sz, solar_t, dark_t, sim_time):
    """Merender Matahari di langit kota."""
    base_bright = max(0.0, 1.0 - dark_t * 0.88)
    if base_bright < 0.01 and solar_t < 0.1: return
    
    # Warna matahari: Putih Cerah -> Kuning -> Oranye Kemarahan (saat gerhana)
    sr, sg, sb = lerp(1.0, 0.92, solar_t), lerp(0.98, 0.45, solar_t), lerp(0.72, 0.06, solar_t)
    
    glDisable(GL_DEPTH_TEST)
    glDisable(GL_LIGHTING)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE)
    
    # Halo Cahaya Matahari
    for rr, aa in [(SUN_R*9, 0.008), (SUN_R*5, 0.030), (SUN_R*2.5, 0.095), (SUN_R*1.5, 0.210)]:
        glColor4f(sr, sg*lerp(0.5, 0.95, rr/(SUN_R*9)), sb*lerp(0.2, 0.65, rr/(SUN_R*9)), aa * base_bright)
        raw_sph(sx, sy, sz, rr, 14, 8)
        
    glDisable(GL_BLEND)
    glEnable(GL_LIGHTING)
    glEnable(GL_DEPTH_TEST)
    
    # Inti Matahari
    em_s = lerp(6.0, 0.15, solar_t) * base_bright
    draw_sph(sx, sy, sz, SUN_R, 28, 16, (sr, sg, sb), (sr*em_s, sg*em_s*0.85, sb*em_s*0.3), 5, 0.0)


def draw_city_moon(mx, my, mz, lunar_t, solar_t, dark_t, sim_time):
    """Merender Bulan di langit kota secara permanen (Mengikuti Hukum Fisika)."""
    # Berbeda dengan versi awal, visibilitas bulan ini 100% karena dia fisik nyata
    vis = clamp(0.30 + dark_t * 0.70, 0.30, 1.0)
    
    # 1. Warna Dasar Bulan
    base_c = (0.82, 0.80, 0.74)
    
    # 2. Bulan menggelap (jadi siluet) kalau dia lagi menutupi matahari (Gerhana Matahari)
    # Ini efek backlighting yang keren!
    base_c = lerp3(base_c, (0.02, 0.02, 0.02), solar_t) 
    
    # 3. Bulan memerah (Blood Moon) kalau dia lagi ketutupan bayangan Bumi (Gerhana Bulan)
    mc = lerp3(base_c, (0.72, 0.16, 0.06), lunar_t)
    
    # Hitung intensitas emisi/cahaya
    ae = lerp(0.28, 0.05, dark_t) * vis
    le = lerp(0, 0.80, lunar_t) * vis
    
    # GAMBAR BULANNYA! (Depth Test harus nyala agar dia bisa 'menimpa' matahari saat posisinya sama)
    glEnable(GL_DEPTH_TEST) 
    draw_sph(mx, my, mz, MOON_R_CITY, 24, 14, mc, 
             (mc[0]*(ae+le*mc[0]), mc[1]*(ae+le*mc[1]), mc[2]*(ae+le*mc[2])), 22, 0.10)
