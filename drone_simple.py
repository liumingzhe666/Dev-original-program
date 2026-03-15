# drone_simple.py
import time
import json
import random
import sqlite3
import csv
import math
import threading
from datetime import datetime
from typing import Dict, List, Optional

# 简单的控制台输出配置
import sys
import os


class DroneState:
    """无人机状态数据类"""

    def __init__(self):
        self.timestamp = time.time()
        self.position_x = 0.0
        self.position_y = 2.0
        self.position_z = 0.0
        self.velocity_x = 0.0
        self.velocity_y = 0.0
        self.velocity_z = 0.0
        self.yaw = 0.0
        self.battery = 100
        self.cpu_usage = 20
        self.memory_usage = 30
        self.target_x = 0.0
        self.target_y = 2.0
        self.target_z = 0.0

    def update(self):
        """更新状态"""
        self.timestamp = time.time()

        # 随机改变目标点
        if random.random() < 0.05:  # 5%的概率改变目标
            self.target_x = random.uniform(-10, 10)
            self.target_y = random.uniform(1.5, 8)
            self.target_z = random.uniform(-10, 10)
            print(f"🎯 新目标点: ({self.target_x:.2f}, {self.target_y:.2f}, {self.target_z:.2f})")

        # 计算朝向目标的方向
        dx = self.target_x - self.position_x
        dy = self.target_y - self.position_y
        dz = self.target_z - self.position_z

        # 计算距离
        distance = math.sqrt(dx * dx + dy * dy + dz * dz)

        if distance > 0.5:
            # 向目标移动
            speed = min(2.0, distance / 5)
            if distance > 0:
                self.velocity_x = (dx / distance) * speed
                self.velocity_y = (dy / distance) * speed
                self.velocity_z = (dz / distance) * speed
        else:
            # 在目标点附近随机移动
            self.velocity_x = random.uniform(-0.3, 0.3)
            self.velocity_y = random.uniform(-0.1, 0.1)
            self.velocity_z = random.uniform(-0.3, 0.3)

        # 添加一些随机扰动
        self.velocity_x += random.uniform(-0.1, 0.1)
        self.velocity_y += random.uniform(-0.05, 0.05)
        self.velocity_z += random.uniform(-0.1, 0.1)

        # 更新位置
        self.position_x += self.velocity_x * 0.1
        self.position_y += self.velocity_y * 0.1
        self.position_z += self.velocity_z * 0.1

        # 限制在有效范围内
        self.position_x = max(-12, min(12, self.position_x))
        self.position_y = max(1, min(10, self.position_y))
        self.position_z = max(-12, min(12, self.position_z))

        # 计算偏航角（根据运动方向）
        if abs(self.velocity_x) > 0.01 or abs(self.velocity_z) > 0.01:
            target_yaw = math.degrees(math.atan2(self.velocity_x, self.velocity_z))
            # 平滑偏航角变化
            yaw_diff = (target_yaw - self.yaw + 180) % 360 - 180
            self.yaw += yaw_diff * 0.1
            self.yaw = self.yaw % 360

        # 电池缓慢下降
        self.battery = max(0, self.battery - random.uniform(0, 0.2))

        # CPU和内存随机波动
        self.cpu_usage = min(100, max(5, self.cpu_usage + random.uniform(-2, 2)))
        self.memory_usage = min(100, max(10, self.memory_usage + random.uniform(-1, 1)))

    def to_dict(self):
        return {
            'timestamp': self.timestamp,
            'position_x': round(self.position_x, 2),
            'position_y': round(self.position_y, 2),
            'position_z': round(self.position_z, 2),
            'velocity_x': round(self.velocity_x, 2),
            'velocity_y': round(self.velocity_y, 2),
            'velocity_z': round(self.velocity_z, 2),
            'yaw': round(self.yaw, 1),
            'battery': int(self.battery),
            'cpu_usage': int(self.cpu_usage),
            'memory_usage': int(self.memory_usage)
        }

    def to_string(self):
        """返回格式化的字符串"""
        return (f"[{datetime.fromtimestamp(self.timestamp).strftime('%H:%M:%S')}] "
                f"📍位置:({self.position_x:6.2f},{self.position_y:6.2f},{self.position_z:6.2f}) | "
                f"⚡速度:({self.velocity_x:5.2f},{self.velocity_y:5.2f},{self.velocity_z:5.2f}) | "
                f"🧭偏航:{self.yaw:6.1f}° | "
                f"🔋电量:{int(self.battery):3d}% | "
                f"💻CPU:{int(self.cpu_usage):3d}% | "
                f"📊内存:{int(self.memory_usage):3d}%")


class DataSaver:
    """数据保存类"""

    def __init__(self, use_sqlite=True, use_csv=True, use_json=True):
        self.use_sqlite = use_sqlite
        self.use_csv = use_csv
        self.use_json = use_json
        self.conn = None
        self.csv_file = None
        self.csv_writer = None
        self.json_file = None

        self._init_storage()

    def _init_storage(self):
        """初始化存储"""
        try:
            # SQLite
            if self.use_sqlite:
                self.conn = sqlite3.connect('drone_data.db', check_same_thread=False)
                cursor = self.conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS drone_states (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp REAL,
                        position_x REAL,
                        position_y REAL,
                        position_z REAL,
                        velocity_x REAL,
                        velocity_y REAL,
                        velocity_z REAL,
                        yaw REAL,
                        battery INTEGER,
                        cpu_usage INTEGER,
                        memory_usage INTEGER
                    )
                ''')
                self.conn.commit()
                print("✅ SQLite数据库初始化成功")

            # CSV
            if self.use_csv:
                file_exists = os.path.exists('drone_data.csv')
                self.csv_file = open('drone_data.csv', 'a', newline='', encoding='utf-8')
                self.csv_writer = csv.writer(self.csv_file)
                if not file_exists:
                    self.csv_writer.writerow([
                        'timestamp', 'position_x', 'position_y', 'position_z',
                        'velocity_x', 'velocity_y', 'velocity_z', 'yaw',
                        'battery', 'cpu_usage', 'memory_usage'
                    ])
                print("✅ CSV文件初始化成功")

            # JSON
            if self.use_json:
                self.json_file = open('drone_data.json', 'a', encoding='utf-8')
                print("✅ JSON文件初始化成功")

        except Exception as e:
            print(f"❌ 存储初始化失败: {e}")

    def save(self, state_dict):
        """保存数据"""
        try:
            # SQLite
            if self.use_sqlite and self.conn:
                cursor = self.conn.cursor()
                cursor.execute('''
                    INSERT INTO drone_states (
                        timestamp, position_x, position_y, position_z,
                        velocity_x, velocity_y, velocity_z, yaw,
                        battery, cpu_usage, memory_usage
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    state_dict['timestamp'],
                    state_dict['position_x'], state_dict['position_y'], state_dict['position_z'],
                    state_dict['velocity_x'], state_dict['velocity_y'], state_dict['velocity_z'],
                    state_dict['yaw'],
                    state_dict['battery'], state_dict['cpu_usage'], state_dict['memory_usage']
                ))
                self.conn.commit()

            # CSV
            if self.use_csv and self.csv_writer:
                self.csv_writer.writerow([
                    state_dict['timestamp'],
                    state_dict['position_x'], state_dict['position_y'], state_dict['position_z'],
                    state_dict['velocity_x'], state_dict['velocity_y'], state_dict['velocity_z'],
                    state_dict['yaw'],
                    state_dict['battery'], state_dict['cpu_usage'], state_dict['memory_usage']
                ])
                self.csv_file.flush()

            # JSON
            if self.use_json and self.json_file:
                self.json_file.write(json.dumps(state_dict) + '\n')
                self.json_file.flush()

        except Exception as e:
            print(f"❌ 保存数据失败: {e}")

    def close(self):
        """关闭所有连接"""
        if self.conn:
            self.conn.close()
        if self.csv_file:
            self.csv_file.close()
        if self.json_file:
            self.json_file.close()
        print("📁 所有文件已关闭")


def clear_screen():
    """清屏"""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header():
    """打印标题"""
    print("=" * 100)
    print(" 🚁 无人机实时状态模拟系统".ljust(50) + "按 Ctrl+C 停止".rjust(48))
    print("=" * 100)


def print_footer(stats):
    """打印底部统计"""
    print("-" * 100)
    print(f" 📊 统计: 总记录数: {stats['count']} | "
          f"平均电量: {stats['avg_battery']:.1f}% | "
          f"平均CPU: {stats['avg_cpu']:.1f}% | "
          f"平均内存: {stats['avg_memory']:.1f}%")
    print("=" * 100)


def main():
    """主函数"""
    state = DroneState()
    saver = DataSaver(use_sqlite=True, use_csv=True, use_json=True)

    # 统计变量
    record_count = 0
    battery_sum = 0
    cpu_sum = 0
    memory_sum = 0

    print_header()
    print("系统初始化完成，开始数据采集...\n")

    try:
        while True:
            # 更新状态
            state.update()
            state_dict = state.to_dict()

            # 保存数据
            saver.save(state_dict)

            # 更新统计
            record_count += 1
            battery_sum += state_dict['battery']
            cpu_sum += state_dict['cpu_usage']
            memory_sum += state_dict['memory_usage']

            # 计算平均
            stats = {
                'count': record_count,
                'avg_battery': battery_sum / record_count,
                'avg_cpu': cpu_sum / record_count,
                'avg_memory': memory_sum / record_count
            }

            # 清屏并显示
            clear_screen()
            print_header()
            print(f"当前状态: {state.to_string()}")
            print(f"目标位置: ({state.target_x:.2f}, {state.target_y:.2f}, {state.target_z:.2f})")
            print_footer(stats)

            # 等待0.1秒
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\n\n🛑 收到停止信号，正在保存数据...")
        saver.close()

        print(f"\n✅ 运行完成！")
        print(f"📈 总共采集了 {record_count} 条数据")
        print(f"📁 数据已保存到: drone_data.db, drone_data.csv, drone_data.json")
        print(f"💾 文件位置: {os.getcwd()}")


def show_recent_data():
    """显示最近的数据"""
    try:
        conn = sqlite3.connect('drone_data.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM drone_states")
        count = cursor.fetchone()[0]

        print(f"\n📊 数据库中有 {count} 条记录")

        if count > 0:
            print("\n📋 最近10条记录:")
            cursor.execute("""
                    SELECT timestamp, position_x, position_y, position_z, battery 
                    FROM drone_states 
                    ORDER BY timestamp DESC 
                    LIMIT 10
                """)
            for row in cursor.fetchall():
                dt = datetime.fromtimestamp(row[0])
                print(f"   {dt.strftime('%H:%M:%S')} - "
                      f"位置:({row[1]:6.2f},{row[2]:6.2f},{row[3]:6.2f}) "
                      f"电量:{row[4]:3d}%")

        conn.close()

    except Exception as e:
        print(f"❌ 读取数据失败: {e}")


if __name__ == "__main__":
    # 检查命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == '--show':
        show_recent_data()
    else:
        main()