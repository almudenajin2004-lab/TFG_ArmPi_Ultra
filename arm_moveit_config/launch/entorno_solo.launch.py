"""Ve solo mesa + persona (con su taburete) en RViz, sin el brazo ni MoveIt, para
ajustar las medidas de config/scene_params.yaml "viendo" el resultado antes
de lanzar la simulacion completa (demo.launch.py).

    ros2 launch arm_moveit_config entorno_solo.launch.py
"""
import os

import xacro
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory('arm_moveit_config')
    xacro_file = os.path.join(pkg_share, 'config', 'entorno_solo.urdf.xacro')
    robot_description = {
        'robot_description': xacro.process_file(xacro_file).toxml()
    }

    return LaunchDescription([
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            output='screen',
            parameters=[robot_description],
        ),
        Node(
            package='rviz2',
            executable='rviz2',
            output='screen',
        ),
    ])
