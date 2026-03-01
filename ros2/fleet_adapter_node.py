import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from sensor_msgs.msg import LaserScan
import time
import requests
import threading

class FleetAdapter(Node):
    def __init__(self):
        super().__init__('fleet_adapter_node')
        
        self.cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel_safe', 10)
        self.scan_sub = self.create_subscription(LaserScan, '/scan', self.scan_cb, 10)
        
        self.ngrok_url = ERP_URL
        self.obstacle_detected = False
        self.is_patrolling = False
        
        self.thread = threading.Thread(target=self.poll_loop, daemon=True)
        self.thread.start()
        
        self.create_timer(0.1, self.motor_timer_callback)
        self.get_logger().info("Threaded Fleet Adapter Started...")

    def scan_cb(self, msg):
        mid = len(msg.ranges) // 2
        front_ranges = msg.ranges[mid-30 : mid+30]
        valid_hits = [r for r in front_ranges if r > 0.1]
        self.obstacle_detected = any(d < 0.5 for d in valid_hits)

    def poll_loop(self):
        """ This runs in the background and checks the internet """
        while True:
            try:
                response = requests.get(f"{self.ngrok_url}/robot/get-command", timeout=2.0)
                if response.json().get("action") == "patrol":
                    self.get_logger().info("Patrol Command Received!")
                    self.is_patrolling = True
            except Exception as e:
                pass
            time.sleep(1.0)

    def motor_timer_callback(self):
        if not self.is_patrolling:
            return

        now = time.time()
        twist = Twist()

        if self.turning:
            if now < self.turn_end_time:
                twist.angular.z = 1.0
                self.cmd_vel_pub.publish(twist)
                return
            else:
                self.turning = False
                self.obstacle_detected = False

        if self.obstacle_detected:
            self.get_logger().warn("Obstacle! Starting 180° turn")
            self.turning = True
            self.turn_end_time = now + 3.0
            return

        twist.linear.x = 0.2
        self.cmd_vel_pub.publish(twist)


def main():
    rclpy.init()
    node = FleetAdapter()
    rclpy.spin(node)
    rclpy.shutdown()


if __name__ == "__main__":
    main()