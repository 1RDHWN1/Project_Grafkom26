import glfw
from OpenGL.GL import *
from OpenGL.GLU import *

def draw_sphere(radius, color):
    glColor3f(color[0], color[1], color[2])
    
    quadric = gluNewQuadric()
    gluSphere(quadric, radius, 32, 32)
def main():
    if not glfw.init():
        return
    
    window = glfw.create_window(800, 600, "Tahap 2: Matahari di Ruang Angkasa", None, None)
    if not window:
        glfw.terminate()
        return

    glfw.make_context_current(window)

    glMatrixMode(GL_PROJECTION)
    gluPerspective(45, (800/600), 0.1, 50.0) 
    glMatrixMode(GL_MODELVIEW)

   
    glEnable(GL_DEPTH_TEST)

    while not glfw.window_should_close(window):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity() 
        glTranslatef(0.0, 0.0, -10.0)

        draw_sphere(1.5, (1.0, 1.0, 0.0))

        glfw.swap_buffers(window)
        glfw.poll_events()

    glfw.terminate()

if __name__ == "__main__":
    main()