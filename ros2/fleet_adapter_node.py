import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from sensor_msgs.msg import LaserScan
import time
import requests
import threading
import os

class FleetAdapter(Node):
    def __init__(self):
        super().__init__('fleet_adapter_node')

        # Parameters (configurable via CLI or ROS launch)
        self.declare_parameter('wms_url', 'https://noncolorable-fluctuatingly-lael.ngrok-free.dev')
        self.declare_parameter('cmd_vel_topic', '/cmd_vel')
        self.declare_parameter('scan_topic', '/scan')
        self.declare_parameter('poll_interval', 2.0)

        self.wms_url = self.get_parameter('wms_url').get_parameter_value().string_value.rstrip('/')
        cmd_vel_topic = self.get_parameter('cmd_vel_topic').get_parameter_value().string_value
        scan_topic = self.get_parameter('scan_topic').get_parameter_value().string_value
        self.poll_interval = self.get_parameter('poll_interval').get_parameter_value().double_value

        self.headers = {
            "ngrok-skip-browser-warning": "true",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        # Publishers and Subscribers
        self.cmd_vel_pub = self.create_publisher(Twist, cmd_vel_topic, 10)
        self.scan_sub = self.create_subscription(LaserScan, scan_topic, self.scan_cb, 10)

        # Robot & Task State
        self.obstacle_detected = False
        self.turning = False
        self.turn_end_time = 0.0
        
        self.current_task = None
        self.task_state = "IDLE"  # IDLE, MOVING_TO_PICKUP, AT_PICKUP, MOVING_TO_DROP, COMPLETED
        self.state_start_time = 0.0

        # Background thread for polling WMS
        self.poll_thread = threading.Thread(target=self.poll_loop, daemon=True)
        self.poll_thread.start()

        # Motion control loop (10Hz)
        self.create_timer(0.1, self.motion_timer_callback)

        self.get_logger().info("==========================================")
        self.get_logger().info(" Fleet Adapter Node Initialized")
        self.get_logger().info(f" WMS URL: {self.wms_url}")
        self.get_logger().info(f" cmd_vel Topic: {cmd_vel_topic}")
        self.get_logger().info(f" scan Topic: {scan_topic}")
        self.get_logger().info("==========================================")

    def scan_cb(self, msg: LaserScan):
        """Processes LiDAR data to detect obstacles in front"""
        if not msg.ranges:
            return

        total_points = len(msg.ranges)
        # Check both 0-index centered (TB3) and middle-index centered lidars
        front_window = 25
        
        # TB3 style: 0 deg is front (indices 0..25 and total-25..total)
        tb3_front = msg.ranges[:front_window] + msg.ranges[-front_window:]
        # Middle index style:
        mid = total_points // 2
        mid_front = msg.ranges[max(0, mid - front_window): min(total_points, mid + front_window)]
        
        all_front = [r for r in (tb3_front + mid_front) if 0.15 < r < 3.5]
        
        if all_front:
            min_dist = min(all_front)
            self.obstacle_detected = min_dist < 0.45
        else:
            self.obstacle_detected = False

    def update_wms_status(self, task_id: str, status: str):
        """Sends status update back to FastAPI WMS"""
        try:
            url = f"{self.wms_url}/robot/update-status?task_id={task_id}"
            payload = {"status": status}
            res = requests.post(url, json=payload, headers=self.headers, timeout=3.0)
            self.get_logger().info(f"Reported status '{status}' to WMS -> Response: {res.status_code}")
        except Exception as e:
            self.get_logger().warn(f"Failed to update status to WMS: {e}")

    def poll_loop(self):
        """Continuously polls WMS for new assigned tasks"""
        while rclpy.ok():
            if self.task_state == "IDLE":
                try:
                    res = requests.get(f"{self.wms_url}/robot/get-task", headers=self.headers, timeout=3.0)
                    if res.status_code == 200:
                        data = res.json()
                        task_id = data.get("task_id")
                        if task_id:
                            self.get_logger().info("------------------------------------------")
                            self.get_logger().info(f" NEW TASK RECEIVED! Task ID: {task_id}")
                            self.get_logger().info(f" Item: {data.get('item_code')} | Rack: {data.get('rack')} | Bin: {data.get('bin')}")
                            self.get_logger().info(f" Pickup: {data.get('pickup')} -> Drop: {data.get('drop')}")
                            self.get_logger().info("------------------------------------------")

                            self.current_task = data
                            self.task_state = "MOVING_TO_PICKUP"
                            self.state_start_time = time.time()
                            self.update_wms_status(task_id, "MOVING_TO_PICKUP")
                except Exception as e:
                    self.get_logger().debug(f"WMS poll error: {e}")

            time.sleep(self.poll_interval)

    def motion_timer_callback(self):
        """Controls vehicle movement according to task phase and obstacle avoidance"""
        twist = Twist()
        now = time.time()

        if self.task_state == "IDLE":
            self.cmd_vel_pub.publish(twist)
            return

        # Phase 1: Moving to Pickup (drive ~6 seconds)
        if self.task_state == "MOVING_TO_PICKUP":
            elapsed = now - self.state_start_time
            if elapsed > 6.0:
                self.task_state = "AT_PICKUP"
                self.state_start_time = now
                self.cmd_vel_pub.publish(twist)  # Stop
                self.get_logger().info(" Arrived at Pickup / Rack! Loading item...")
                self.update_wms_status(self.current_task["task_id"], "PICKUP_REACHED")
                return

            self.navigate_with_avoidance(twist, now)

        # Phase 2: At Pickup (dwell 2.5 seconds to simulate loading)
        elif self.task_state == "AT_PICKUP":
            elapsed = now - self.state_start_time
            if elapsed > 2.5:
                self.task_state = "MOVING_TO_DROP"
                self.state_start_time = now
                self.get_logger().info(" Item loaded! Moving to Drop / Assembly station...")
                self.update_wms_status(self.current_task["task_id"], "MOVING_TO_DROP")
                return

            self.cmd_vel_pub.publish(twist)

        # Phase 3: Moving to Drop (drive ~6 seconds)
        elif self.task_state == "MOVING_TO_DROP":
            elapsed = now - self.state_start_time
            if elapsed > 6.0:
                self.task_state = "COMPLETED"
                self.state_start_time = now
                self.cmd_vel_pub.publish(twist)  # Stop
                self.get_logger().info(" Arrived at Drop location! Delivery Complete.")
                self.update_wms_status(self.current_task["task_id"], "COMPLETED")
                return

            self.navigate_with_avoidance(twist, now)

        # Phase 4: Completed
        elif self.task_state == "COMPLETED":
            self.cmd_vel_pub.publish(twist)
            self.task_state = "IDLE"
            self.current_task = None
            self.get_logger().info(" Robot is IDLE and ready for next task.")

    def navigate_with_avoidance(self, twist: Twist, now: float):
        """Simple reactive navigation with obstacle avoidance"""
        if self.turning:
            if now < self.turn_end_time:
                twist.angular.z = 0.8
                self.cmd_vel_pub.publish(twist)
                return
            else:
                self.turning = False
                self.obstacle_detected = False

        if self.obstacle_detected:
            self.get_logger().warn("Obstacle detected ahead! Turning to avoid...")
            self.turning = True
            self.turn_end_time = now + 1.8
            twist.linear.x = 0.0
            twist.angular.z = 0.8
            self.cmd_vel_pub.publish(twist)
            return

        twist.linear.x = 0.22
        twist.angular.z = 0.0
        self.cmd_vel_pub.publish(twist)


def main(args=None):
    rclpy.init(args=args)
    node = FleetAdapter()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.cmd_vel_pub.publish(Twist())  # Stop motors on shutdown
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()