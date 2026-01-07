"""MQTT handler for MoeBot device integration"""

import json
import logging
import os
import sys
import paho.mqtt.client as mqtt
from moebot_client import MoeBotClient

_log = logging.getLogger("moebot_mqtt")


class MoeBotMQTT:
    """Bridge MoeBot to MQTT for remote control and status monitoring"""
    
    def __init__(self, device_id: str, device_ip: str, local_key: str,
                 mqtt_host: str, mqtt_port: int = 1883,
                 mqtt_username: str = None, mqtt_password: str = None,
                 mqtt_topic: str = "moebot"):
        """
        Initialize MQTT bridge for MoeBot
        
        Args:
            device_id: MoeBot device ID
            device_ip: MoeBot local IP address
            local_key: MoeBot local key
            mqtt_host: MQTT broker hostname/IP
            mqtt_port: MQTT broker port (default 1883)
            mqtt_username: MQTT username (optional)
            mqtt_password: MQTT password (optional)
            mqtt_topic: Main MQTT topic (commands and stats will be subtopics)
        """
        self.device_id = device_id
        self.device_ip = device_ip
        self.local_key = local_key
        
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.mqtt_username = mqtt_username
        self.mqtt_password = mqtt_password
        self.mqtt_topic = mqtt_topic
        
        self.moebot = None
        self.mqtt_client = None
        self.running = False
        
        # Topic paths
        self.cmnd_topic = f"{mqtt_topic}/cmnd"
        self.stats_topic = f"{mqtt_topic}/stats"
        
        # Track last published values to only publish on changes
        self.last_stats = {}
        
    def _on_mqtt_connect(self, client, userdata, flags, rc):
        """Handle MQTT connection"""
        if rc == 0:
            _log.info("Connected to MQTT broker")
            # Subscribe to command topics
            client.subscribe(f"{self.cmnd_topic}/#")
            _log.info(f"Subscribed to {self.cmnd_topic}/#")
        else:
            _log.error(f"Failed to connect to MQTT broker, rc: {rc}")
    
    def _on_mqtt_message(self, client, userdata, msg):
        """Handle incoming MQTT messages"""
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8').strip().lower()
            
            _log.debug(f"Received MQTT message - Topic: {topic}, Payload: {payload}")
            
            # Parse command topic
            if topic.startswith(f"{self.cmnd_topic}/"):
                command = topic.replace(f"{self.cmnd_topic}/", "")
                self._handle_command(command, payload)
                
        except Exception as e:
            _log.error(f"Error handling MQTT message: {e}")
    
    def _handle_command(self, command: str, payload: str):
        """Handle incoming MQTT commands"""
        try:
            if command == "start":
                spiral = payload.lower() == "spiral"
                _log.info(f"Starting mower (spiral={spiral})")
                self.moebot.start(spiral=spiral)
                self._publish_stat("state", self.moebot.state)
                
            elif command == "pause":
                _log.info("Pausing mower")
                self.moebot.pause()
                self._publish_stat("state", self.moebot.state)
                
            elif command == "cancel":
                _log.info("Canceling mower")
                self.moebot.cancel()
                self._publish_stat("state", self.moebot.state)
                
            elif command == "dock":
                _log.info("Docking mower")
                self.moebot.dock()
                self._publish_stat("state", self.moebot.state)
                
            elif command == "mow_time":
                try:
                    hours = int(payload)
                    if 1 <= hours <= 99:
                        _log.info(f"Setting mow time to {hours} hours")
                        self.moebot.mow_time = hours
                        self._publish_stat("mow_time", hours)
                    else:
                        _log.warning(f"Mow time must be between 1-99, got {hours}")
                except ValueError:
                    _log.error(f"Invalid mow_time value: {payload}")
                
            elif command == "mow_in_rain":
                if payload in ("true", "1", "on", "yes"):
                    _log.info("Enabling mow in rain")
                    self.moebot.mow_in_rain = True
                    self._publish_stat("mow_in_rain", "true")
                elif payload in ("false", "0", "off", "no"):
                    _log.info("Disabling mow in rain")
                    self.moebot.mow_in_rain = False
                    self._publish_stat("mow_in_rain", "false")
                else:
                    _log.warning(f"Invalid mow_in_rain value: {payload}")
                    
            elif command == "poll":
                _log.info("Polling device status")
                self.moebot.poll()
                self._publish_all_stats()
                
            elif command == "get_errors":
                _log.info("Fetching machine errors")
                errors = self.moebot.machine_errors
                self._publish_stat("machine_errors", ",".join(errors) if errors else "None")
                
            elif command == "get_password":
                _log.info("Fetching device password")
                password_data = self.moebot.password
                if password_data["numeric"]:
                    # Publish both numeric and letter format
                    password_str = f"{password_data['letter']}"
                    self._publish_stat("device_password", password_str)
                else:
                    self._publish_stat("device_password", "Unknown")
                
            else:
                _log.warning(f"Unknown command: {command}")
                
        except Exception as e:
            _log.error(f"Error handling command '{command}': {e}")
    
    def _on_moebot_update(self, data):
        """Handle MoeBot status updates"""
        try:
            _log.debug(f"MoeBot update received: {data}")
            self._publish_all_stats()
        except Exception as e:
            _log.error(f"Error handling MoeBot update: {e}")
    
    def _publish_stat(self, stat_name: str, value):
        """Publish a single stat to MQTT - only if value changed"""
        if not self.mqtt_client:
            return
            
        payload = str(value).lower() if isinstance(value, bool) else str(value)
        
        # Only publish if value has changed
        if self.last_stats.get(stat_name) == payload:
            _log.debug(f"Skipped {stat_name} (unchanged: {payload})")
            return
        
        topic = f"{self.stats_topic}/{stat_name}"
        self.mqtt_client.publish(topic, payload, retain=True)
        self.last_stats[stat_name] = payload
        _log.debug(f"Published {topic} = {payload}")
    
    def _publish_all_stats(self):
        """Publish all MoeBot stats to MQTT"""
        try:
            # Publish all properties
            self._publish_stat("battery", self.moebot.battery)
            self._publish_stat("state", self.moebot.state)
            
            # Only publish emergency_state if machine is in EMERGENCY state
            if self.moebot.state == "EMERGENCY" and self.moebot.emergency_state:
                self._publish_stat("emergency_state", self.moebot.emergency_state)
            else:
                # Clear emergency_state if not in emergency
                self._publish_stat("emergency_state", "")
            
            self._publish_stat("mow_in_rain", self.moebot.mow_in_rain)
            self._publish_stat("mow_time", self.moebot.mow_time)
            self._publish_stat("work_mode", self.moebot.work_mode)
            self._publish_stat("online", self.moebot.online)
            
            # Publish zone information
            zones = self.moebot.zones
            if zones:
                for i in range(1, 6):
                    zone = getattr(zones, f"zone{i}")
                    distance, ratio = zone
                    self._publish_stat(f"zone{i}_distance", distance)
                    self._publish_stat(f"zone{i}_ratio", ratio)
            
            # Publish machine errors
            errors = self.moebot.machine_errors
            self._publish_stat("machine_errors", ",".join(errors) if errors else "None")
            
            # Publish device password
            password_data = self.moebot.password
            if password_data["numeric"]:
                password_str = f"{password_data['letter']}"
                self._publish_stat("device_password", password_str)
            
            _log.debug("Published all stats to MQTT")
            
        except Exception as e:
            _log.error(f"Error publishing stats: {e}")
    
    def start(self):
        """Start MQTT bridge - connect and listen"""
        try:
            _log.info("Starting MoeBot MQTT bridge")
            
            # Suppress stderr for the entire initialization process
            save_stderr = sys.stderr
            sys.stderr = open(os.devnull, 'w')
            
            try:
                # Initialize MoeBot Client
                self.moebot = MoeBotClient(self.device_id, self.device_ip, self.local_key)
                self.moebot.add_listener(self._on_moebot_update)
                
                # Initialize MQTT client
                self.mqtt_client = mqtt.Client()
                self.mqtt_client.on_connect = self._on_mqtt_connect
                self.mqtt_client.on_message = self._on_mqtt_message
                
                # Set credentials if provided
                if self.mqtt_username and self.mqtt_password:
                    self.mqtt_client.username_pw_set(self.mqtt_username, self.mqtt_password)
                
                # Connect to MQTT broker
                _log.info(f"Connecting to MQTT broker at {self.mqtt_host}:{self.mqtt_port}")
                self.mqtt_client.connect(self.mqtt_host, self.mqtt_port, keepalive=120)
                
                # Start MQTT client loop in background
                self.mqtt_client.loop_start()
                
                # Start MoeBot listener
                _log.info("Starting MoeBot listener")
                self.moebot.listen()
                
            finally:
                # Restore stderr
                sys.stderr.close()
                sys.stderr = save_stderr
            
            # Publish initial status
            self.moebot.poll()
            self._publish_all_stats()
            
            self.running = True
            _log.info("MoeBot MQTT bridge started successfully")
            
        except Exception as e:
            _log.error(f"Error starting MQTT bridge: {e}")
            raise
    
    def stop(self):
        """Stop MQTT bridge"""
        try:
            _log.info("Stopping MoeBot MQTT bridge")
            self.running = False
            
            if self.moebot:
                self.moebot.unlisten()
            
            if self.mqtt_client:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
            
            _log.info("MoeBot MQTT bridge stopped")
            
        except Exception as e:
            _log.error(f"Error stopping MQTT bridge: {e}")


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(
        format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
        level=logging.INFO
    )
    
    # Configuration
    # REPLACE WITH YOUR DEVICE DETAILS
    DEVICE_ID = "YOUR_DEVICE_ID"
    DEVICE_IP = "YOUR_DEVICE_IP"
    LOCAL_KEY = "YOUR_LOCAL_KEY"
    
    # REPLACE WITH YOUR MQTT BROKER DETAILS
    MQTT_HOST = "YOUR_MQTT_BROKER_IP"
    MQTT_PORT = 1883
    MQTT_USERNAME = "YOUR_MQTT_USERNAME"  # Leave empty if not required
    MQTT_PASSWORD = "YOUR_MQTT_PASSWORD"  # Leave empty if not required
    MQTT_TOPIC = "moebot"
    
    # Create and start bridge
    bridge = MoeBotMQTT(
        device_id=DEVICE_ID,
        device_ip=DEVICE_IP,
        local_key=LOCAL_KEY,
        mqtt_host=MQTT_HOST,
        mqtt_port=MQTT_PORT,
        mqtt_username=MQTT_USERNAME,
        mqtt_password=MQTT_PASSWORD,
        mqtt_topic=MQTT_TOPIC
    )
    
    try:
        bridge.start()
        print("MQTT bridge running. Press Ctrl+C to stop.")
        # Keep the script running
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        bridge.stop()
