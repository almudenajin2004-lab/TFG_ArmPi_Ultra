"""Hace que Gazebo y RViz dibujen con la grafica NVIDIA en portatiles con
grafica hibrida (modo "on-demand"): sin esto, todo lo que se lanza usa la
integrada (AMD/Intel), que va mucho mas justa y ademas gasta RAM del sistema.

Uso en un launch:
    from gpu_nvidia import acciones_gpu_nvidia
    LaunchDescription([*acciones_gpu_nvidia(), ...resto...])

Argumento de launch: gpu_nvidia:=true|false (por defecto true si el driver
de NVIDIA esta cargado; en un equipo sin NVIDIA no hace nada).
"""
import os

from launch.actions import DeclareLaunchArgument, SetEnvironmentVariable
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration

_EGL_NVIDIA = '/usr/share/glvnd/egl_vendor.d/10_nvidia.json'


def acciones_gpu_nvidia():
    hay_nvidia = os.path.exists('/proc/driver/nvidia')
    usar = IfCondition(LaunchConfiguration('gpu_nvidia'))
    acciones = [
        DeclareLaunchArgument(
            'gpu_nvidia', default_value='true' if hay_nvidia else 'false',
            description='Dibujar Gazebo/RViz con la grafica NVIDIA (PRIME offload)'),
        # Ventanas (GLX): Gazebo GUI y RViz.
        SetEnvironmentVariable('__NV_PRIME_RENDER_OFFLOAD', '1', condition=usar),
        SetEnvironmentVariable('__GLX_VENDOR_LIBRARY_NAME', 'nvidia', condition=usar),
    ]
    # Render sin ventana (EGL): la camara de Gazebo con gui:=false.
    if os.path.exists(_EGL_NVIDIA):
        acciones.append(SetEnvironmentVariable(
            '__EGL_VENDOR_LIBRARY_FILENAMES', _EGL_NVIDIA, condition=usar))
    return acciones
