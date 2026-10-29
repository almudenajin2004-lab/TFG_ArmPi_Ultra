#!/usr/bin/env python3
"""Puente de topic: republica /controller_manager/joint_states (el topic real
del driver, '~/joint_states' del nodo controller_manager) en /joint_states
(el nombre estandar que esperan robot_state_publisher y move_group).

Necesario porque servo_controller/controller_manager.py publica en un topic
privado del nodo en vez del estandar; sin este puente, move_group nunca ve el
estado real de las articulaciones y aborta cualquier ejecucion de trayectoria
("couldn't receive full current joint state within 1s").

topic_tools/relay no esta instalado en el sistema -> se hace a mano con rclpy.
Uso (con el workspace sourceado, ROS_DOMAIN_ID=100):
    python3 src/arm_moveit_config/scripts/joint_states_relay.py
"""
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState


class JointStatesRelay(Node):
    def __init__(self):
        super().__init__('joint_states_relay')
        self.pub = self.create_publisher(JointState, '/joint_states', 10)
        self.sub = self.create_subscription(
            JointState, '/controller_manager/joint_states', self.cb, 10
        )
        self.get_logger().info('Relaying /controller_manager/joint_states -> /joint_states')

    def cb(self, msg: JointState):
        # El grupo "arm" de MoveIt solo conoce joint1..5 (r_joint, la pinza, no
        # esta en la SRDF) -> filtramos para evitar el spam de errores
        # "Joint 'r_joint' not found in model" en move_group.
        out = JointState()
        out.header = msg.header
        for name, pos in zip(msg.name, msg.position):
            if name != 'r_joint':
                out.name.append(name)
                out.position.append(pos)
        self.pub.publish(out)


def main():
    rclpy.init()
    node = JointStatesRelay()
    rclpy.spin(node)


if __name__ == '__main__':
    main()
