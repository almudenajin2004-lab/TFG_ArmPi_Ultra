import os
import sys

from launch import LaunchDescription
from moveit_configs_utils import MoveItConfigsBuilder
from moveit_configs_utils.launches import generate_demo_launch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gpu_nvidia import acciones_gpu_nvidia  # noqa: E402


def generate_launch_description():
    moveit_config = MoveItConfigsBuilder("armpi_ultra", package_name="arm_moveit_config").to_moveit_configs()
    # RViz con la grafica NVIDIA (gpu_nvidia:=false para la integrada).
    return LaunchDescription([*acciones_gpu_nvidia(), generate_demo_launch(moveit_config)])
