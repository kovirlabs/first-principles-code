# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Evan Gress

"""controls.py - feedback control calculations (P, PD, PID).

Control theory keeps systems on target despite disturbances. These helpers
compute a PID controller's output, characterise a second-order system's
response (natural frequency, damping, overshoot), and simulate a closed loop
so you can watch a controller settle - the kind of thing you would otherwise do
in MATLAB's Control System Toolbox or Simulink.
"""

import math

import numpy as np


class Controls:
    """P, PD, PID, and response-characterisation calculations."""

    def pid_output(self, *, error, integral, derivative, kp, ki=0.0, kd=0.0):
        """Single PID control output: u = Kp*e + Ki*integral + Kd*derivative.

        Set ``ki``/``kd`` to zero to get P or PD control - the same formula
        covers all three controller types.

        :param error: current error e = setpoint - measurement
        :param integral: accumulated integral of the error over time
        :param derivative: rate of change of the error
        :param kp: proportional gain
        :param ki: integral gain, defaults to 0 (no integral action)
        :param kd: derivative gain, defaults to 0 (no derivative action)
        :returns: controller output (command) u
        """
        return kp * error + ki * integral + kd * derivative

    def damping_from_overshoot(self, *, percent_overshoot):
        """Damping ratio that produces a given step-response overshoot.

        Inverts  %OS = exp(-zeta*pi / sqrt(1-zeta^2)) * 100.

        :param percent_overshoot: desired overshoot [%] (e.g. 5 for 5%)
        :returns: required damping ratio zeta [-]
        """
        ln_os = math.log(percent_overshoot / 100.0)
        return -ln_os / math.sqrt(math.pi ** 2 + ln_os ** 2)

    def settling_time(self, *, damping_ratio, natural_frequency, tolerance=0.02):
        """Approximate settling time of a second-order system.

        t_s ~= -ln(tolerance) / (zeta * omega_n).  The default 2% tolerance is
        the textbook convention.

        :param damping_ratio: damping ratio zeta [-]
        :param natural_frequency: undamped natural frequency omega_n [rad/s]
        :param tolerance: settling band as a fraction, defaults to 0.02 (2%)
        :returns: settling time [s]
        """
        return -math.log(tolerance) / (damping_ratio * natural_frequency)

    def simulate_pid_first_order(
        self, *, setpoint, time_constant, gain, kp, ki=0.0, kd=0.0,
        dt=0.01, duration=10.0,
    ):
        """Simulate a PID loop controlling a first-order plant.

        The plant is  tau * y' + y = gain * u  (a motor, a heater, a tank...).
        We step it forward in time with a simple Euler integration so you can
        plot or inspect how the controlled output approaches the setpoint.

        :param setpoint: target value the controller should reach
        :param time_constant: plant time constant tau [s]
        :param gain: plant steady-state gain (output per unit input)
        :param kp: proportional gain
        :param ki: integral gain, defaults to 0
        :param kd: derivative gain, defaults to 0
        :param dt: simulation time step [s], defaults to 0.01
        :param duration: total simulated time [s], defaults to 10
        :returns: tuple (time array [s], output array) as numpy arrays
        """
        steps = int(duration / dt)
        time = np.linspace(0.0, duration, steps)
        output = np.zeros(steps)

        integral = 0.0          # running sum of error*dt
        previous_error = 0.0    # for the derivative term

        # March forward one time step at a time.
        for i in range(1, steps):
            error = setpoint - output[i - 1]
            integral += error * dt
            derivative = (error - previous_error) / dt

            # Controller decides the command u from the current error state.
            command = self.pid_output(
                error=error, integral=integral, derivative=derivative,
                kp=kp, ki=ki, kd=kd,
            )

            # Plant responds: Euler step of  y' = (gain*u - y) / tau.
            dydt = (gain * command - output[i - 1]) / time_constant
            output[i] = output[i - 1] + dydt * dt

            previous_error = error

        return time, output
