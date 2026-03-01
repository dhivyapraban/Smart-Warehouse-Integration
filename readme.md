# 📦 Integrating ERP in Automated Guided Vehicles (AGVs)

## 🚀 Overview

This project demonstrates an **industry-aligned integration** between:

* **ERP (ERPNext)** – Business layer
* **WMS (Custom Python Service)** – Warehouse execution layer
* **Fleet Adapter (ROS 2 Node)** – Integration layer
* **Nav2 + TurtleBot3** – Robot navigation layer

The system simulates how modern warehouses (e.g., Amazon Robotics-style architecture) integrate enterprise software with autonomous mobile robots.

---

## 🏗️ System Architecture

```
ERPNext (Order Creation UI)
        ↓
WMS (wms.py – Rack/Bin & Destination Logic)
        ↓ REST
Fleet Adapter (ROS 2 Node)
        ↓ ROS 2 Actions
Nav2 (Navigation Stack)
        ↓
TurtleBot3 (Simulation / Robot)
```

### 🔹 Layer Responsibilities

| Layer         | Responsibility                                  |
| ------------- | ----------------------------------------------- |
| ERP           | Order creation, stock entry                     |
| WMS           | Determines pickup (rack/bin) and drop (station) |
| Fleet Adapter | Converts logical locations → coordinates        |
| Nav2          | Path planning & obstacle avoidance              |
| Robot         | Executes motion                                 |

---

## 🎯 Project Objective

To demonstrate:

* Event-driven ERP → WMS → AGV integration
* Logical warehouse locations (rack/bin) mapping to physical coordinates
* Task-based AGV movement (pickup → drop)
* Real-time task status updates
* Industry-style layered separation of responsibilities

---

## 🧠 Industry Alignment

This architecture follows the same principles used in:

* Amazon Robotics fulfillment centers
* SAP EWM + AGV integrations
* VDA-5050 fleet communication standard

Key Design Principle:

> Robots execute tasks.
> WMS decides warehouse logic.
> ERP handles business logic.

---

## 🛠️ Tech Stack

* **ROS 2 (Jazzy)**
* **Nav2 (NavigateToPose)**
* **TurtleBot3**
* **Python (rclpy)**
* **FastAPI / Flask (WMS REST layer)**
* **ERPNext**

---

## ⚙️ How It Works

### 1️⃣ ERP Creates Order

User creates order in ERPNext.

### 2️⃣ WMS Processes Request

WMS determines:

* Pickup location (e.g., `POD_183`)
* Drop location (e.g., `PACK_STATION_03`)

### 3️⃣ Fleet Adapter Executes

* Converts logical location → `(x, y, yaw)`
* Sends goal to `/navigate_to_pose`
* Monitors execution

### 4️⃣ Status Update

Upon completion:

* Fleet Adapter sends status to WMS
* WMS updates task state
* ERP can be notified

---

## 📍 Location Mapping

Logical warehouse locations are stored in:

```
config/area_map.json
```

Example:

```json
{
  "POD_183": [1.5, 0.5, 0.0],
  "PACK_STATION_03": [-1.0, 2.0, 1.57]
}
```

These are installed via ROS package resources and accessed using:

```python
get_package_share_directory('fleet_adapter')
```

---

## ▶️ Running the System

### 1. Build Workspace

```bash
cd ~/ros2_ws
colcon build
source install/setup.bash
```

### 2. Launch Navigation

```bash
export TURTLEBOT3_MODEL=burger
ros2 launch turtlebot3_navigation2 navigation2.launch.py
```

### 3. Run Fleet Adapter

```bash
ros2 run fleet_adapter fleet_adapter_node
```

### 4. Start WMS Service

```bash
python3 wms.py
```

---

## 🔁 Task Flow Example

```json
{
  "pickup": "POD_183",
  "drop": "PACK_STATION_03"
}
```

Execution:

1. Robot navigates to POD_183
2. Robot navigates to PACK_STATION_03
3. Completion status sent to WMS

---

## 📊 Key Features

* Logical-to-physical location translation
* ROS 2 Action-based navigation
* REST-based ERP/WMS integration
* Modular architecture
* Cloud or local deployable
* Industry-inspired task flow

---

## 🧩 Design Decisions

* No Flask inside Fleet Adapter (client-only REST usage)
* WMS as system-of-record for task states
* No hardcoded file paths (uses ROS package share directory)
* Separation between business logic and motion control

---

## 🔮 Future Improvements

* Multi-robot fleet management
* Task queue & resynchronization logic
* MQTT-based event streaming
* Web dashboard for task visualization
* VDA-5050 compliance layer

---

## 📚 Acknowledgment

This project was developed as part of a research-oriented learning initiative to understand real-world integration between ERP systems and autonomous mobile robots.

Conceptual guidance and architectural references were inspired by discussions on ERP–WMS–Fleet–Robot integration patterns.

---

## 👤 Author

**Dhivyapraban**
GitHub: [https://github.com/dhivyapraban](https://github.com/dhivyapraban)
