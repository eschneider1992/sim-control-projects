import matplotlib.animation as animation
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d import axes3d
import numpy as np
import scipy.integrate as integrate

'''
TODO
'''

# Set up constants
MASS = 2                 # Mass (Kg)
G = 9.8                  # Gravity acceleration (m/s**2)
SIM_LENGTH = 10          # Seconds
SAMPLES_PER_SECOND = 30  # Used in the solver

def main():

    # Set up initial conditions
    position_0 = np.array([1.0,  1.5, 2.5])  # Initial (x, y, z) position (m)
    velocity_0 = np.array([0.0, -0.1, 0.5])  # Initial (x, y, z) velocity (m/s)

    initial = np.hstack((position_0, velocity_0))
    t_span = np.linspace(0, SIM_LENGTH, SIM_LENGTH * SAMPLES_PER_SECOND)
    zout = integrate.odeint(falling_point_ode, initial, t_span)

    animate_point(t_span, zout[:, 0:3])


def falling_point_ode(Z, t):
    zout = np.hstack((Z[3:], np.array([0, 0, -G])))
    return zout


def animate_point(t_span, xyz, scale=1.0):
    '''
    Takes the points in time ((N,) array) and the (x, y, z) points of the mass
    ((N, 3) array) and creates a plot that shows the point motion.

    scale is a float that will scale the playback speed. At 2 the playback will
    happen at twice the actual speedl
    '''
    assert 0.01 < scale < 100
    dt = np.average(np.diff(t_span)) / scale

    # Attaching 3D axis to the figure
    figure = plt.figure()
    axes = figure.add_subplot(111, projection='3d')
    
    # Setting the axes properties
    axes.set_aspect('equal')
    axes.grid()
    axes.set_xlim3d([min(np.min(xyz[:, 0]), -1), max(np.max(xyz[:, 0]), 1)])
    axes.set_ylim3d([min(np.min(xyz[:, 1]), -1), max(np.max(xyz[:, 1]), 1)])
    axes.set_zlim3d([min(np.min(xyz[:, 2]), -1), max(np.max(xyz[:, 2]), 1)])
    axes.view_init(elev=0.0, azim=0.0)
    axes.set_xlabel('X')
    axes.set_ylabel('Y')
    axes.set_zlabel('Z')

    point, = axes.plot([0.0], [0.0], [0.0], 'o', markersize=MASS * 10)
    time_text = axes.text(0.9, 0.9, 0.9, '', transform=axes.transAxes)

    def initialize_animation():
        point.set_data([0.0], [0.0])
        point.set_3d_properties([0.0])
        time_text.set_text('')
        return point, time_text

    def animate(i):
        point.set_data(xyz[i, 0], xyz[i, 1])
        point.set_3d_properties(xyz[i, 2])
        time_text.set_text('time={:.1f}s'.format(i * dt))
        return point, time_text

    pendulumAnimation = animation.FuncAnimation(
        figure,
        animate,
        np.arange(1, xyz.shape[0]),
        interval=int(dt * 1e3),
        blit=True,
        init_func=initialize_animation)

    plt.show()


if __name__ == '__main__':
    main()
