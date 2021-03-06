import argparse
from ast import literal_eval
from collections import deque, namedtuple
import logging
import math
import matplotlib.pyplot as plt
import numpy as np
import sys

from controller import PIDArduino
import plant

LOG_FORMAT = '%(name)s: %(message)s'
Simulation = namedtuple(
    'Simulation',
    ['name', 'controller', 'plant', 'delayed_states', 'timestamps',
     'plant_states', 'sensor_states', 'outputs'])


def simulate_system(args):
    timestamp = 0  # seconds
    delayed_samples_len = max(1, round(args.delay / args.sampletime))

    assert hasattr(plant, args.plant)
    plantClass = getattr(plant, args.plant)

    initial = literal_eval(args.initial_values)
    assert isinstance(initial, dict)
    constants = literal_eval(args.constant_values)
    assert isinstance(constants, dict)

    # Create a simulation for the tuple pid(kp, ki, kd)
    sim = Simulation(
        name='{} PID'.format(args.plant),
        controller=PIDArduino(
            sampletime=args.sampletime,
            kp=float(args.pid[0]),
            ki=float(args.pid[1]),
            kd=float(args.pid[2]),
            out_min=args.out_min,
            out_max=args.out_max,
            time=lambda: timestamp),
        plant=plantClass(initial, constants),
        delayed_states=deque(maxlen=delayed_samples_len),
        timestamps=[],
        plant_states=[],
        sensor_states=[],
        outputs=[],
    )

    # Init delayed_states deque for each simulation
    sim.delayed_states.extend(
        sim.delayed_states.maxlen * [sim.plant.sensable_state]
    )

    # Calculate the allowable output change in a single step
    allowable_change = args.output_rate_limit * args.sampletime

    # Run simulation for specified interval. The (x60) is because args.interval
    # is in minutes and we want seconds
    while timestamp < (args.interval * 60):
        timestamp += args.sampletime

        # Make noise centered around 0 w/ a given stddev
        if args.sensor_noise_std_dev <= 0.0:
            sensor_noise = 0.0
        else:
            sensor_noise = np.random.normal(scale=args.sensor_noise_std_dev)
        sensor_state = sim.delayed_states[0] + sensor_noise

        # Calculates controller reaction
        if args.supress_output:
            output = 0.0
        else:
            # Calculate the next desired output
            output = sim.controller.calc(input_val=sensor_state,
                                         setpoint=args.setpoint,
                                         max_allowable_change=allowable_change)

        # Calculates the effects of the controller output on the next sensor
        # reading
        simulation_update(sim, timestamp, output, args)

    title = '{} simulation, {:.1f}s delay, {:.1f}s sampletime'.format(
        sim.name, args.delay, args.sampletime
    )
    plot_simulation(sim, title)

    # Do if implemented for this plant
    try:
        sim.plant.plot_state_history()
    except AttributeError:
        pass
    try:
        sim.plant.plot_energy()
    except AttributeError:
        pass
    try:
        sim.plant.animate_system()
    except AttributeError:
        pass


def simulation_update(simulation, timestamp, output, args):
    simulation.plant.update(output, duration=args.sampletime)
    # Add a state reading to the delayed_states queue, which bumps an element
    # off the front
    simulation.delayed_states.append(simulation.plant.sensable_state)
    # Make the simulation read the delayed state value
    simulation.sensor_states.append(simulation.delayed_states[0])
    # For the following values just append them to lists of values over time
    simulation.timestamps.append(timestamp)
    simulation.outputs.append(output)
    simulation.plant_states.append(simulation.plant.sensable_state)


def plot_simulation(simulation, title):
    lines = []
    fig, ax1 = plt.subplots()
    upper_limit = 0

    # Create x-axis and first y-axis
    ax1.plot()
    ax1.set_xlabel('time (s)')
    ax1.set_ylabel('sensed value')
    ax1.grid(axis='y', linestyle=':', alpha=0.5)

    # Draw setpoint line
    lines += [plt.axhline(
        y=args.setpoint, color='r', linestyle=':', linewidth=0.9, label='setpoint')]

    # Create second y-axis (power)
    ax2 = ax1.twinx()
    ax2.set_ylabel('output')

    # Plot sensor and output values
    color = 'b'
    lines += ax1.plot(
        simulation.timestamps, simulation.sensor_states, color=color,
        alpha=1.0, label='sensor state')
    lines += ax2.plot(
        simulation.timestamps, simulation.outputs, '--', color=color,
        linewidth=1, alpha=0.7, label='output')

    # Create legend
    labels = [l.get_label() for l in lines]
    offset = math.ceil(4 / 3) * 0.05
    ax1.legend(lines,
               labels,
               loc=9,
               bbox_to_anchor=(0.5, -0.1 - offset),
               ncol=3)
    fig.subplots_adjust(bottom=(0.2 + offset))

    # Set title
    plt.title(title)
    fig.canvas.set_window_title(title)
    plt.show()


'''
Kettle
python sim_tools/sim.py --pid 104 0.8 205 --out-min -0.0 --out-max 100.0 --sampletime 5 --delay 15.0 --setpoint 45.0 --interval 20 --initial-values "{'kettle_temp': 40.0}" --constant-values "{'ambient_temp': 20.0, 'volume': 70.0, 'diameter': 50.0, 'heater_power': 6.0, 'heat_loss_factor': 1.0}" --plant Kettle
Pendulum:
python sim_tools/sim.py --pid 20 0.8 5 --out-min -10.0 --out-max 10.0 --sampletime 0.01 --delay 0.0 --setpoint 0.0 --interval 0.2 --initial-values "{'theta0': 0.3, 'x0': 5}" --constant-values "{'length': 0.5}" --plant InvertedPendulum
python sim_tools/sim.py --pid 20 0.8 5 --out-min -5.0 --out-max 5.0 --sampletime 0.01 --delay 0.01 --setpoint 0.0 --interval 0.2 --initial-values "{'theta_dot0': 0, 'x0': 0}" --constant-values "{'length': 1}" --plant InvertedPendulum --sensor-noise-std-dev 0.005 --output-rate-limit 30
allowable_change 0.3
'''
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-P', '--plant',
        default='Kettle',
        help='the class from plant.py to simulate (e.g. InvertedPendulum)')
    parser.add_argument(
        '-p', '--pid',
        nargs=3,
        metavar=('kp', 'ki', 'kd'),
        default=None,
        help='simulate a PID controller')

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='be verbose')

    parser.add_argument(
        '-s', '--setpoint',
        default=45.0,
        type=float,
        help='target sensor value')
    parser.add_argument(
        '-S', '--supress-output',
        action='store_true',
        help='sets output to 0.0 so you can see system steady state')

    parser.add_argument(
        '-i', '--interval',
        metavar='t',
        default=20,
        type=float,
        help='simulated interval in minutes')
    parser.add_argument(
        '-d', '--delay',
        metavar='t',
        default=15.0,
        type=float,
        help='system response delay in seconds')
    parser.add_argument(
        '--sampletime',
        metavar='t',
        default=5.0,
        type=float,
        help='sensor sample time in seconds')

    parser.add_argument(
        '--out-min',
        default=0.0,
        type=float,
        help='minimum PID controller output')
    parser.add_argument(
        '--out-max',
        default=100.0,
        type=float,
        help='maximum PID controller output')
    parser.add_argument(
        '--sensor-noise-std-dev',
        default=0.0,
        type=float,
        help='Std deviation of gaussian noise applied to the sensor readings')
    parser.add_argument(
        '--output-rate-limit',
        default=1e6,
        type=float,
        help='Limiting rate of output. This will be multiplied by the sample'
             ' time, and the result will cap the output change each timestep.'
             ' If the output is m/s^2, the limit is, by definition, m/s^3')

    parser.add_argument(
        '--constant-values',
        default='{}',
        action='store',
        help='Pass in a dictionary of constants values used throughout the'
        ' simulation as a string, specific to each plant')
    parser.add_argument(
        '--initial-values',
        default='{}',
        action='store',
        help='Pass in a dictionary of initial values as a string, specific'
        ' to each plant')

    if len(sys.argv) == 1:
        parser.print_help()
    else:
        args = parser.parse_args()

        if args.verbose:
            logging.basicConfig(stream=sys.stderr, format=LOG_FORMAT, level=logging.DEBUG)
        if args.pid is not None:
            simulate_system(args)
