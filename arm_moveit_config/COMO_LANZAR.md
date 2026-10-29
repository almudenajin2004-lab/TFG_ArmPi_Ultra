# Notas de sesión / cómo retomar

Notas de las sesiones del 2026-09-01/02 (robot real) y 2026-09-03/04 (tenedor,
escena y arranque de percepción). Robot: ArmPi Ultra, Raspberry Pi 5 en
`172.20.10.2` (usuario `pi`; la contraseña no se guarda aquí a propósito —
no subir credenciales al repo. Guárdala tú aparte).

## Cómo lanzar la simulación sola, sin el robot físico

Hardware simulado (`FakeSystem`, ya integrado en el URDF) — no hace falta
`ROS_DOMAIN_ID=100` ni conectarte al Raspberry Pi, eso es solo para el robot
real.

**Una sola terminal — MoveIt + RViz, ya con mesa + persona:**
```bash
cd ~/TFG/tfg_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch arm_moveit_config demo.launch.py
```
Espera a que salga `You can start planning now!`.

Mesa y persona ya no se publican en un segundo paso: desde la sesión
2026-10-28 son links **fijos del propio `robot_description`**
(`config/entorno.xacro`, incluido desde `config/armpi_ultra.urdf.xacro`),
generados a partir de `config/scene_params.yaml`. Al ser parte del mismo
modelo que el brazo, MoveIt los trata igual que a los propios links del
robot: nunca planifica ni ejecuta una trayectoria que los atraviese, tanto
aquí como con el robot real. Para cambiar medidas, edita
`config/scene_params.yaml` y vuelve a lanzar.

Para ver **solo** el entorno (sin el brazo, para ajustar medidas mirando
RViz antes de lanzar todo):
```bash
ros2 launch arm_moveit_config entorno_solo.launch.py
```

⚠️ Para cerrar `demo.launch.py`, usa **Ctrl+C en esa terminal**, no cierres
solo la ventana de RViz — si cierras solo la ventana, `move_group` y el
resto de nodos se quedan corriendo de fondo sin interfaz, y si luego lanzas
otra sesión acabas con nodos duplicados en el grafo de ROS (nos pasó esta
sesión; ver más abajo).

**Maniquí de la persona:** se ve con `maniqui_sentada.stl` (sección
`persona.malla` de `scene_params.yaml`). **Ya no hay silla aparte** (quitada
el 2026-10-28): el STL del maniquí trae su propio taburete, que es solo
visual. Si se deja `archivo: ""`, la persona se ve con sus propias
cajas/esfera de colisión. La altura del asiento es `persona.alto_asiento_m`.

**Mesa y base del robot:** `base_link.STL` baja 6.5 mm por debajo de su
origen, así que el tablero está en `mesa.z_tablero_m: -0.0065` (antes en 0,
se solapaba con la base y MoveIt lo daba como choque). Además, en la SRDF
están desactivadas las colisiones *entre* piezas fijas (base, mesa, piezas
de la persona); la del brazo contra mesa y persona sigue activa.

## Simulación en Gazebo + MoveIt (con cámara)

Desde el 2026-10-29 se usa **Gazebo Fortress** (`ign gazebo`, el que va con
ROS 2 Humble), no Gazebo Classic: Classic está descontinuado (de ahí el
aviso de "gazebo_classic_migration" al abrirlo) y todo lo necesario para
Fortress ya estaba instalado (`ros_gz_sim`, `ros_gz_bridge`,
`gz_ros2_control`).

**Una sola terminal — Gazebo + MoveIt + RViz, enlazados:**
```bash
cd ~/TFG/tfg_ws
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch arm_moveit_config gazebo.launch.py          # gui:=false sin ventana de Gazebo
```
Lo que planifiques y ejecutes en RViz (*Plan & Execute*) lo hace también
el brazo de Gazebo: las articulaciones las mueve `gz_ros2_control` con los
mismos controladores de `config/ros2_controllers.yaml` (`arm_controller`,
`joint_state_broadcaster`), y RViz muestra el estado real de Gazebo.
**No lances a la vez `demo.launch.py`** (serían dos robots y dos
controladores). `demo.launch.py` sigue sirviendo para trabajar solo con
MoveIt, sin física ni cámara.

Ver la imagen de la cámara (otra terminal, con los mismos `source`):
```bash
ros2 run rqt_image_view rqt_image_view /depth_cam/rgb/image_raw
```

La cámara Aurora930 es `camera_connet_link.STL` (link `rgb_camera_link`),
atornillada a `link4`: se mueve con el brazo. En el URDF
(`armpi_ultra_description/urdf/armpi_ultra.xacro`) hay:
- `camara_link` (centro de la lente, X hacia delante = misma dirección que el
  tenedor) y `camara_optical_frame` (convenio de imagen, Z hacia delante, es
  el `frame_id` de las imágenes). Nombres propios a propósito: el driver
  real ya publica `depth_cam_*_optical_frame` y repetirlos chocaría en el
  árbol TF.
- Un sensor RGB-D de Gazebo; `gazebo.launch.py` lo pasa a ROS con **los
  mismos topics que la cámara real** (`/depth_cam/rgb/image_raw`,
  `/depth_cam/rgb/camera_info`, `/depth_cam/depth/image_raw`,
  `/depth_cam/depth_registered/points`), así el código de percepción sirve
  igual en simulación y con el robot.

Cómo está montado: `config/armpi_ultra.urdf.xacro` tiene el argumento
`sim_gazebo` (por defecto `false`); con `true` el hardware de ros2_control
pasa de `mock_components/GenericSystem` a `gz_ros2_control/GazeboSimSystem`
y el robot queda fijado al mundo de Gazebo (`config/mundo.sdf`).

Notas:
- La posición de la lente en la cara de la cámara es aproximada (centro de
  la cara frontal), revisar con la cámara real.
- En Gazebo el maniquí y la mesa se ven en gris liso (sin los colores del
  YAML). El maniquí básico no tiene cara (ni ojos ni boca), así que MediaPipe
  no detectará nada sobre él: para probar la percepción en simulación hará
  falta un maniquí con cara texturizada.

## Robot real (multi-terminal)

### 0. Antes de nada
- El robot y tu PC deben estar en la **misma red WiFi**.
- **Siempre** exporta esto en cada terminal nueva que uses (el robot corre en
  `ROS_DOMAIN_ID=100`; sin esto tu PC y el robot no se ven):
  ```bash
  export ROS_DOMAIN_ID=100
  source /opt/ros/humble/setup.bash
  source ~/TFG/tfg_ws/install/setup.bash
  cd ~/TFG/tfg_ws
  ```

### 1. TF real + puente de joint_states (terminal 1)
El driver del robot publica los joint states en `/controller_manager/joint_states`
(privado del nodo), no en el `/joint_states` estándar. Sin este puente,
`move_group` no ve el estado real y aborta cualquier ejecución.
```bash
ros2 launch arm_moveit_config rsp.launch.py &
ros2 launch arm_moveit_config static_virtual_joint_tfs.launch.py &
python3 src/arm_moveit_config/scripts/joint_states_relay.py &
```

### 2. move_group (terminal 2)
```bash
ros2 launch arm_moveit_config move_group.launch.py
```
Espera al mensaje `You can start planning now!` antes de seguir.

### 3. RViz (terminal 3)
```bash
ros2 launch arm_moveit_config moveit_rviz.launch.py
```

### 4. Escena (mesa + persona)
Ya viene incluida en el `robot_description` que publica `rsp.launch.py`
(paso 1) — no hace falta ningún paso aparte. Ver la nota de arriba.

### 5. Cámara (por SSH al robot) — ⚠️ se calienta, apágala cuando no la uses
Encender:
```bash
ssh pi@172.20.10.2
docker exec -d -u ubuntu -w /home/ubuntu ArmPiUltra /bin/zsh -c \
  'source ~/.zshrc; SHARE=$(ros2 pkg prefix --share peripherals); \
   ros2 launch $SHARE/launch/include/aurora930.launch.py > /tmp/aurora_relaunch.log 2>&1'
```
Ver en el navegador (no en RViz — la imagen sin comprimir se pierde por el
WiFi):
```
http://172.20.10.2:8080/stream_viewer?topic=/depth_cam/rgb/image_raw
```
Apagar cuando termines:
```bash
ssh pi@172.20.10.2
docker exec ArmPiUltra bash -lc "pkill -9 -f aurora930_node; pkill -9 -f 'ros2 launch.*aurora930.launch.py'"
```

## Archivos clave para seguir editando
| Qué | Archivo |
|---|---|
| Medidas mesa/persona | `config/scene_params.yaml` |
| Geometría de la escena (mesa/persona, URDF fijo) | `config/entorno.xacro` |
| Ver solo el entorno, sin el brazo | `launch/entorno_solo.launch.py` + `config/entorno_solo.urdf.xacro` |
| Malla del maniquí | `../simulations/armpi_ultra_description/meshes/maniqui_sentada.stl` |
| Grupo de planificación / punto de control (`tip_link`) | `config/armpi_ultra.srdf` |
| URDF del robot (tenedor, `end_effector_link`) | `../simulations/armpi_ultra_description/urdf/armpi_ultra.xacro` |
| Cinemática propia (constante de longitud de herramienta) | `../driver/kinematics/kinematics/transform.py` |

## Hecho en la sesión del 2026-09-03/04

**Tenedor añadido al URDF (`armpi_ultra.xacro`), ya con la posición buena:**
- `tenedor_link`: colgado directamente de `link5` (no de `end_effector_link`,
  eso era un intento anterior), offset `0` porque la malla de `link5` apenas
  sobresale de su propio origen. Visual **y colisión** usan la malla completa
  del tenedor (`meshes/tenedor_link.stl`, con `scale="0.001 0.001 0.001"`
  porque ese STL concreto está en milímetros, a diferencia del resto del
  robot que está en metros) — cubre toda la pala (~15 cm), no solo el punto
  de montaje.
- `end_effector_link` (frame puro, sin malla) es ahora **el punto funcional
  (TCP)** que usa MoveIt: cuelga de `link5` con offset `z=0.135` m, calculado
  como 13.5 de las 15 "unidades" (cm) de longitud total del tenedor — la
  línea media de los dientes, con 1.5 cm de margen hasta la punta física para
  que el planificador no intente colisionar justo el borde extremo.
- `tip_link` del grupo `arm` en `armpi_ultra.srdf` = `end_effector_link` (no
  `tenedor_link`, que es solo el punto de montaje).
- Limpieza: borrados `armpi_ultra.urdf`, `cp_armpi_ultra.xacro`, `cp.xacro`,
  `gripper.urdf.xacro` y las mallas del gripper mecánico de dos dedos
  (`l_link`, `r_link`, `l_in_link`, `r_in_link`, `l_out_link`, `r_out_link`,
  `gripper_link.STL`, `gripper_link_collision.stl`) — nada de eso se usa ya,
  se comprobó uno a uno que ningún fichero activo los sigue referenciando.

**Escena (`scene_params.yaml` + `publish_scene.py`):**
- Bug encontrado y arreglado: una dimensión negativa en la caja de la mesa
  (`table_width_m`/`table_depth_m`, negativos a propósito como convenio de
  dirección) hacía que `move_group` **abortara el proceso entero** con una
  excepción de C++ sin capturar (`Box dimensions must be non-negative`).
  Arreglado en `publish_scene.py` (usa `abs()` para el tamaño real de la caja,
  pero respeta el signo para calcular hacia qué lado se coloca) — el dato en
  `scene_params.yaml` no se tocó, era intencionado.
- Nuevo: `table_margin_behind_x_m` / `table_margin_behind_y_m` en
  `scene_params.yaml` — la mesa ahora también se extiende un margen hacia
  atrás del origen del robot (antes se quedaba media base del robot sin mesa
  debajo, porque `base_link.STL` se extiende de forma simétrica alrededor de
  su propio origen, no solo hacia donde avanza la mesa).
- `person_box_width_m` corregido de `0.0` (dato tocado sin querer) a `0.60`.

## Pendiente

**Cinemática propia del robot real:** actualizar la constante `tool_link` en
`driver/kinematics/kinematics/transform.py` — la cinemática propia (aparte de
MoveIt) también asume una longitud de herramienta y no se ha tocado todavía.

**Maniquí realista:** desde el 2026-10-28 está **activado un maniquí básico
provisional** (`maniqui_sentada.stl`, trae su propio taburete) con
`escala: 1.29`, `offset_xyz_m: [0.14, 0, -0.45]`, `offset_rpy_deg: [0, 0, 90]`
en `persona.malla` (el STL viene normalizado a 1 m de alto, pies en z=0,
mirando a −Y). El usuario lo va a sustituir por otro mejor: poner el STL
nuevo en `armpi_ultra_description/meshes/`, apuntar `persona.malla.archivo`
y reajustar escala/offsets mirando RViz. La colisión (cajas/esfera) no cambia.
⚠️ Con este maniquí la cara y los antebrazos quedan ~10-13 cm por delante
(hacia el brazo) de la esfera/caja de colisión, porque la malla se inclina
hacia delante y la colisión es una pila vertical — pendiente decidir si se
adelanta la colisión de la cabeza/torso.
⚠️ La pose guardada `home` de la SRDF roza 2.5 mm la cara delantera de la
caja del torso (`tenedor_link` ↔ `persona_torso_link`, en x≈0.30 m), así que
MoveIt la da como estado en colisión. No es por el cambio de la mesa: ya
pasaba. Pendiente: retocar `home` o la caja del torso.

**Más trayectorias hacia la boca:** en RViz, pestaña *Planning* del panel
Motion Planning, se pueden guardar estados con nombre (como `home`/`palito`
que ya existen en la SRDF) y planificar entre ellos. Para algo
repetible/documentable en la memoria del TFG, mejor un pequeño script con
`MoveGroupInterface` que planifique `home → boca_maniqui` y `boca_maniqui →
home`.

## Percepción (cara / boca / plato-comida) — arrancado, sin código todavía

Se estudió `TAZ-TFG_1.pdf` (en `/TFG`, TFG de referencia de Adrián Fortea
Valencia, Zaragoza 2024 — trata exactamente de alimentación asistida con
detección de cara/boca) y se revisó qué trae ya el propio `tfg_ws` de
Hiwonder para reutilizar. Decisiones tomadas con el usuario:

- **Cara + boca**: usar **MediaPipe Face Mesh** (ya hay ejemplos de Hiwonder
  en `src/example/example/mediapipe/include/face_mesh.py` y
  `face_tracking.py`, sobre el topic `depth_cam/rgb/image_raw` de la cámara
  de profundidad Aurora930) en vez del Haar-cascade + landmarks LBF de
  terceros que usó el TFG de referencia. Para abierta/cerrada: **fórmula
  geométrica** (ratio de alturas de labio, como el TFG de referencia) sobre
  los landmarks de labios de MediaPipe — se descartó replicar su CNN
  (Keras/TensorFlow + dataset YawDD) por ser mucho más trabajo para una
  mejora que el propio TFG describe como modesta.
- **Plato / comida**: empezar con **YOLOv8 local** (paquete `yolov8_detect`,
  ya en el repo, corre con OpenVINO en CPU/Raspberry, sin API key ni
  internet). El modelo COCO estándar (`yolov8s`, ya viene comentado en
  `yolov8_detect/launch/yolov8_detect.launch.py`) ya cubre comida común de
  serie (banana, apple, pizza, donut, sandwich, bowl, etc.) sin entrenar
  nada. **Ojo:** el fichero del modelo (`.xml` de OpenVINO) no existe en el
  repo — hay que exportarlo una vez con `ultralytics`
  (`YOLO('yolov8s.pt').export(format='openvino')`) antes de poder usarlo. No
  hay clase "plato" en COCO; si hace falta, Hiwonder ya demuestra el patrón
  con un modelo propio entrenado (`garbage_classification_640s`, que sí tiene
  clase "Plate").
- Descartado por ahora (queda anotado por si se quiere ampliar más adelante):
  identificación abierta de comida vía VLM en la nube, reutilizando el patrón
  de `src/large_models/large_models/vllm_dietitianl.py` + `config.py`
  (Qwen-VL gratis vía OpenRouter, o GPT-4o, o StepFun) — requiere API key e
  internet, se prefirió empezar solo con lo local/offline.

**Se quedó a medias:** se instaló `mediapipe` en un venv de prueba
(`/tmp/.../scratchpad/mp_test_venv`, **efímero, no sobrevive a la sesión**)
para validar la fórmula del ratio de boca con una foto real de la webcam del
PC (`/dev/video0`), pero la webcam no apuntaba a una persona (foto de una
habitación vacía) — no se llegó a probar. Nada de código de percepción se ha
escrito todavía, solo la investigación y las decisiones de arriba.

### Plan para la próxima sesión
1. Repetir la prueba de la webcam (colocarse delante, foto boca cerrada +
   foto boca abierta) para fijar bien qué índices de landmark de MediaPipe
   usar y qué umbral de ratio funciona antes de escribir el nodo definitivo.
2. Crear el paquete ROS2 nuevo (p. ej. `feeding_perception`) con el nodo de
   cara+boca basado en `face_mesh.py`, publicando el estado (abierta/cerrada)
   y la posición de la boca — siguiendo el patrón del TFG de referencia
   (TF2 + servicio) para que luego el brazo pueda consultarlo igual que
   consulta hoy la escena.
3. Exportar el modelo YOLOv8 a OpenVINO y montar el launch de
   `yolov8_detect` con las clases de comida relevantes.
4. Más adelante: integrar ambos con la generación de trayectorias del brazo
   (equivalente al capítulo 5 del TFG de referencia), y decidir si hace falta
   VLM en la nube para comida fuera de las 80 clases de COCO.
