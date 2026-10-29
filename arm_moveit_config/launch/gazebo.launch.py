"""Simulacion completa en Gazebo Fortress + MoveIt + RViz, enlazados: lo que
se planifica y ejecuta en RViz (boton Plan & Execute) lo hace tambien el
brazo de Gazebo, y la camara de la muneca (sensor en
armpi_ultra_description/urdf/armpi_ultra.xacro, colgada de link4) se mueve
con el.

    ros2 launch arm_moveit_config gazebo.launch.py            # con ventana de Gazebo
    ros2 launch arm_moveit_config gazebo.launch.py gui:=false # Gazebo sin ventana
    ros2 run rqt_image_view rqt_image_view /depth_cam/rgb/image_raw

Como funciona:
  - Gazebo carga el robot_description con sim_gazebo:=true: las
    articulaciones las mueve gz_ros2_control (en vez del mock de
    demo.launch.py) con los controladores de config/ros2_controllers.yaml.
  - move_group envia las trayectorias a arm_controller, que ahora vive
    dentro de Gazebo; joint_state_broadcaster publica /joint_states reales
    de Gazebo -> RViz y MoveIt ven exactamente lo que hace la simulacion.
  - ros_gz_bridge pasa /clock y la camara a ROS con los mismos topics que la
    camara real (/depth_cam/...).
No lanzar a la vez que demo.launch.py (serian dos robots/controladores).
"""
import os

import xacro
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, IncludeLaunchDescription,
                            RegisterEventHandler)
from launch.conditions import IfCondition, UnlessCondition
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from moveit_configs_utils import MoveItConfigsBuilder


def generate_launch_description():
    pkg_share = get_package_share_directory('arm_moveit_config')
    gz_sim_share = get_package_share_directory('ros_gz_sim')
    world = os.path.join(pkg_share, 'config', 'mundo.sdf')

    # robot_description para Gazebo (hardware gz_ros2_control).
    urdf_gazebo = xacro.process_file(
        os.path.join(pkg_share, 'config', 'armpi_ultra.urdf.xacro'),
        mappings={'sim_gazebo': 'true'}).toxml()

    # Configuracion de MoveIt de siempre (move_group no necesita saber nada
    # de Gazebo: solo habla con arm_controller y lee /joint_states).
    moveit_config = MoveItConfigsBuilder(
        'armpi_ultra', package_name='arm_moveit_config').to_moveit_configs()

    # El suelo de Gazebo (z=0) es el suelo de la escena: el robot va encima
    # de la mesa.
    scene = xacro.load_yaml(
        os.path.join(pkg_share, 'config', 'scene_params.yaml'))['scene']
    altura_base = scene['mesa']['alto_superficie_m'] - scene['mesa']['z_tablero_m']

    sim_time = {'use_sim_time': True}

    gazebo_con_ventana = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(gz_sim_share, 'launch', 'gz_sim.launch.py')),
        launch_arguments={'gz_args': f'-r {world}'}.items(),
        condition=IfCondition(LaunchConfiguration('gui')),
    )
    gazebo_sin_ventana = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(gz_sim_share, 'launch', 'gz_sim.launch.py')),
        launch_arguments={'gz_args': f'-r -s --headless-rendering {world}'}.items(),
        condition=UnlessCondition(LaunchConfiguration('gui')),
    )

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='log',
        parameters=[{'robot_description': urdf_gazebo}, sim_time],
    )

    insertar_robot = Node(
        package='ros_gz_sim',
        executable='create',
        output='screen',
        arguments=['-topic', 'robot_description', '-name', 'armpi_ultra',
                   '-z', str(altura_base)],
    )

    puente = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        output='log',
        arguments=[
            '/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock',
            '/camara/image@sensor_msgs/msg/Image[ignition.msgs.Image',
            '/camara/depth_image@sensor_msgs/msg/Image[ignition.msgs.Image',
            '/camara/camera_info@sensor_msgs/msg/CameraInfo[ignition.msgs.CameraInfo',
            '/camara/points@sensor_msgs/msg/PointCloud2[ignition.msgs.PointCloudPacked',
        ],
        remappings=[
            ('/camara/image', '/depth_cam/rgb/image_raw'),
            ('/camara/depth_image', '/depth_cam/depth/image_raw'),
            ('/camara/camera_info', '/depth_cam/rgb/camera_info'),
            ('/camara/points', '/depth_cam/depth_registered/points'),
        ],
    )

    # Controladores: se arrancan cuando el robot ya esta dentro de Gazebo
    # (el controller_manager lo crea gz_ros2_control al cargar el modelo).
    joint_state_broadcaster = Node(
        package='controller_manager', executable='spawner',
        arguments=['joint_state_broadcaster', '--controller-manager', '/controller_manager'],
    )
    arm_controller = Node(
        package='controller_manager', executable='spawner',
        arguments=['arm_controller', '--controller-manager', '/controller_manager'],
    )

    move_group = Node(
        package='moveit_ros_move_group',
        executable='move_group',
        output='screen',
        parameters=[moveit_config.to_dict(), sim_time],
    )

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        output='log',
        arguments=['-d', os.path.join(pkg_share, 'config', 'moveit.rviz')],
        parameters=[
            moveit_config.robot_description,
            moveit_config.robot_description_semantic,
            moveit_config.robot_description_kinematics,
            moveit_config.planning_pipelines,
            moveit_config.joint_limits,
            sim_time,
        ],
    )

    return LaunchDescription([
        DeclareLaunchArgument('gui', default_value='true',
                              description='Abrir la ventana de Gazebo'),
        gazebo_con_ventana,
        gazebo_sin_ventana,
        robot_state_publisher,
        puente,
        insertar_robot,
        RegisterEventHandler(OnProcessExit(target_action=insertar_robot,
                                           on_exit=[joint_state_broadcaster])),
        RegisterEventHandler(OnProcessExit(target_action=joint_state_broadcaster,
                                           on_exit=[arm_controller])),
        move_group,
        rviz,
    ])
