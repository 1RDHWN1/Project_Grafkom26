"""
=============================================================
  FILE: gl_engine.py
  Fungsi: Berisi fungsi matematika pembantu (lerp, smoothstep)
          serta fungsi untuk menggambar primitif OpenGL 
          (box, sphere, cylinder) dengan Quadric yang DIIOPTIMASI.
=============================================================
"""

import math
from OpenGL.GL import *
from OpenGL.GLU import *

# ───────────────────────────────────────────────────────────
# 1. FUNGSI MATEMATIKA & INTERPOLASI
# ───────────────────────────────────────────────────────────

def lerp(a, b, t):
    """Linear interpolation sederhana."""
    return a + (b - a) * t

def lerp3(c1, c2, t):
    """Linear interpolation untuk RGB / Tuple dengan 3 nilai."""
    return tuple(lerp(a, b, t) for a, b in zip(c1, c2))

def clamp(v, lo, hi):
    """Membatasi nilai agar tidak kurang dari 'lo' dan tidak lebih dari 'hi'."""
    return max(lo, min(hi, v))

def smoothstep(t):
    """Interpolasi halus, cocok untuk transisi cahaya dan warna."""
    t = clamp(t, 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)

def ease_sine(t):
    """Transisi berbentuk kurva sinus (halus di awal dan akhir)."""
    return -(math.cos(math.pi * clamp(t, 0.0, 1.0)) - 1.0) / 2.0

# ───────────────────────────────────────────────────────────
# 2. OPTIMASI QUADRIC (SOLUSI ANTI-LAG)
# ───────────────────────────────────────────────────────────
# Menyimpan satu instance Quadric di memori global.
# Menghindari alokasi/dealokasi Quadric setiap frame yang bikin drop FPS.
_GLOBAL_QUADRIC = None
_SPHERE_LISTS = {}
_CYLINDER_LISTS = {}

def get_quadric():
    global _GLOBAL_QUADRIC
    if _GLOBAL_QUADRIC is None:
        _GLOBAL_QUADRIC = gluNewQuadric()
        gluQuadricNormals(_GLOBAL_QUADRIC, GLU_SMOOTH)
    return _GLOBAL_QUADRIC

def get_sphere_list(sl, st):
    key = (int(sl), int(st))
    list_id = _SPHERE_LISTS.get(key)
    if list_id is None:
        list_id = glGenLists(1)
        _SPHERE_LISTS[key] = list_id
        glNewList(list_id, GL_COMPILE)
        gluSphere(get_quadric(), 1.0, sl, st)
        glEndList()
    return list_id

def get_cylinder_list(sl):
    key = int(sl)
    list_id = _CYLINDER_LISTS.get(key)
    if list_id is None:
        list_id = glGenLists(1)
        _CYLINDER_LISTS[key] = list_id
        glNewList(list_id, GL_COMPILE)
        q = get_quadric()
        gluCylinder(q, 1.0, 1.0, 1.0, sl, 1)
        gluDisk(q, 0, 1.0, sl, 1)
        glTranslatef(0, 0, 1.0)
        gluDisk(q, 0, 1.0, sl, 1)
        glEndList()
    return list_id

def warm_geometry_cache(sphere_keys=(), cylinder_segments=()):
    for sl, st in sphere_keys:
        get_sphere_list(sl, st)
    for sl in cylinder_segments:
        get_cylinder_list(sl)

# ───────────────────────────────────────────────────────────
# 3. FUNGSI MATERIAL OPENGL
# ───────────────────────────────────────────────────────────

def set_mat(r, g, b, spec=0.25, shin=35.0, emit=(0.0, 0.0, 0.0)):
    """Mengatur material warna, pantulan cahaya (specular), dan emisi."""
    glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT,  [r * 0.40, g * 0.40, b * 0.40, 1.0])
    glMaterialfv(GL_FRONT_AND_BACK, GL_DIFFUSE,  [r, g, b, 1.0])
    glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, [spec, spec, spec, 1.0])
    glMaterialf (GL_FRONT_AND_BACK, GL_SHININESS, shin)
    glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, list(emit) + [1.0])

# ───────────────────────────────────────────────────────────
# 4. FUNGSI MENGGAMBAR BENTUK 3D (PRIMITIF)
# ───────────────────────────────────────────────────────────

def draw_box(cx, cy, cz, sx, sy, sz, color, shin=32.0, spec=0.25, emit=(0.0, 0.0, 0.0)):
    """Menggambar kubus/balok 3D."""
    r, g, b = color
    set_mat(r, g, b, spec=spec, shin=shin, emit=emit)
    hx, hy, hz = sx / 2.0, sy / 2.0, sz / 2.0
    
    glPushMatrix()
    glTranslatef(cx, cy, cz)
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
        for v in vs:
            glVertex3f(*v)
            
    glEnd()
    glPopMatrix()
    
    # Reset emisi agar tidak mempengaruhi objek lain yang di-render selanjutnya
    glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, [0.0, 0.0, 0.0, 1.0])

def draw_sph(cx, cy, cz, r, sl=18, st=10, color=(1.0, 1.0, 1.0), emit=(0.0, 0.0, 0.0), shin=40.0, spec=0.3):
    """Menggambar bola 3D dengan material (untuk planet, matahari, daun pohon)."""
    set_mat(*color, spec=spec, shin=shin, emit=emit)
    glPushMatrix()
    glTranslatef(cx, cy, cz)
    glScalef(r, r, r)
    
    glCallList(get_sphere_list(sl, st))
    
    glMaterialfv(GL_FRONT_AND_BACK, GL_EMISSION, [0.0, 0.0, 0.0, 1.0])
    glPopMatrix()

def draw_cyl(cx, cy, cz, br, tr, h, sl=10, color=(0.5, 0.5, 0.5)):
    """Menggambar silinder tegak (untuk batang pohon, tiang lampu)."""
    set_mat(*color, spec=0.1, shin=8.0)
    glPushMatrix()
    glTranslatef(cx, cy, cz)
    
    # PUTAR 90 DERAJAT AGAR SILINDER BERDIRI TEGAK KE ATAS (SUMBU Y)
    glRotatef(-90, 1, 0, 0)

    q = get_quadric()
    if abs(br - tr) < 1e-6:
        glScalef(br, br, h)
        glCallList(get_cylinder_list(sl))
    else:
        gluCylinder(q, br, tr, h, sl, 1)
        gluDisk(q, 0, br, sl, 1)
        glTranslatef(0, 0, h)
        gluDisk(q, 0, tr, sl, 1)
    
    glPopMatrix()

def raw_sph(cx, cy, cz, r, sl=14, st=8):
    """Menggambar bola tanpa mengatur material (biasanya untuk halo/cahaya transparan)."""
    glPushMatrix()
    glTranslatef(cx, cy, cz)
    glScalef(r, r, r)
    
    glCallList(get_sphere_list(sl, st))
    
    glPopMatrix()
