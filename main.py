from moebot_client import MoeBotClient as MoeBot

import logging

# Suppress pymoebot and tinytuya debug/info logging during startup
logging.getLogger("pymoebot").setLevel(logging.CRITICAL)
logging.getLogger("tinytuya").setLevel(logging.CRITICAL)
logging.getLogger("moebot_client").setLevel(logging.INFO)

# Configure logging
logging.basicConfig(
    format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
    level=logging.INFO
)

# MoeBot Configuration
# REPLACE THESE WITH YOUR DEVICE DETAILS
DEVICE_ID = "YOUR_DEVICE_ID"          # e.g., "bf9744..."
DEVICE_IP = "YOUR_DEVICE_IP"          # e.g., "192.168.1.100"
LOCAL_KEY = "YOUR_LOCAL_KEY"          # e.g., "e2_y!..."

# MQTT Configuration
# REPLACE THESE WITH YOUR MQTT BROKER DETAILS
MQTT_HOST = "YOUR_MQTT_BROKER_IP"     # e.g., "192.168.1.50" or "openhab.local"
MQTT_PORT = 1883                      # Default MQTT port
MQTT_USERNAME = "YOUR_MQTT_USERNAME"  # Leave as None or "" if not required
MQTT_PASSWORD = "YOUR_MQTT_PASSWORD"  # Leave as None or "" if not required
MQTT_TOPIC = "moebot"                 # Base topic for MQTT messages

def query_status():
    """Query the MoeBot's current status (polling method)"""
    try:
        moebot = MoeBot(DEVICE_ID, DEVICE_IP, LOCAL_KEY)
        moebot.poll()
        
        print("=" * 50)
        print("MoeBot Status (Polling)")
        print("=" * 50)
        print(f"Device Online: {moebot.online}")
        print(f"Battery level: {moebot.battery}%")
        print(f"Machine state: {moebot.state}")
        print(f"Emergency State: {moebot.emergency_state}")
        print(f"Mow In Rain: {moebot.mow_in_rain}")
        print(f"Mow Time: {moebot.mow_time} hours")
        print(f"Work Mode: {moebot.work_mode}")
        print(f"Last update: {moebot.last_update}")
        
        # New Extended Features
        print("-" * 50)
        print(f"Device Password: {moebot.password}")
        print(f"Active Errors: {moebot.machine_errors}")
        print("-" * 50)
        
        # Decode and print zone information
        print("\nZone Configuration:")
        zones = moebot.zones
        if zones:
            distance1, ratio1 = zones.zone1
            distance2, ratio2 = zones.zone2
            distance3, ratio3 = zones.zone3
            distance4, ratio4 = zones.zone4
            distance5, ratio5 = zones.zone5
            
            print(f"  Zone 1: Distance={distance1}, Ratio={ratio1}%")
            print(f"  Zone 2: Distance={distance2}, Ratio={ratio2}%")
            print(f"  Zone 3: Distance={distance3}, Ratio={ratio3}%")
            print(f"  Zone 4: Distance={distance4}, Ratio={ratio4}%")
            print(f"  Zone 5: Distance={distance5}, Ratio={ratio5}%")
        else:
            print("  No zone configuration available")
        
        print("=" * 50)
        
    except Exception as e:
        print(f"Error querying device: {e}")

def listener(msg):
    """Listener callback for receiving device status updates"""
    print(f"Device update: {msg}")

def listen_for_updates():
    """Listen for real-time updates from the MoeBot"""
    try:
        moebot = MoeBot(DEVICE_ID, DEVICE_IP, LOCAL_KEY)
        moebot.add_listener(listener)
        
        print("=" * 50)
        print("Listening for MoeBot updates...")
        print("Press Ctrl+C to stop listening")
        print("=" * 50)
        
        moebot.listen()
        
    except KeyboardInterrupt:
        print("\nStopping listener...")
        moebot.unlisten()
    except Exception as e:
        print(f"Error listening to device: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        
        if mode == "listen":
            listen_for_updates()
        elif mode == "mqtt":
            # Start MQTT bridge
            from mqtt_handler import MoeBotMQTT
            mqtt_bridge = MoeBotMQTT(
                device_id=DEVICE_ID,
                device_ip=DEVICE_IP,
                local_key=LOCAL_KEY,
                mqtt_host=MQTT_HOST,
                mqtt_port=MQTT_PORT,
                mqtt_username=MQTT_USERNAME if MQTT_USERNAME else None,
                mqtt_password=MQTT_PASSWORD if MQTT_PASSWORD else None,
                mqtt_topic=MQTT_TOPIC
            )
            
            try:
                mqtt_bridge.start()
                print("\n" + "=" * 50)
                print("MQTT Bridge Active")
                print("=" * 50)
                
                # Keep running
                import time
                while True:
                    time.sleep(1)
                    
            except KeyboardInterrupt:
                print("\nShutting down MQTT bridge...")
                mqtt_bridge.stop()
        else:
            print(f"Unknown mode: {mode}")
            print("Usage: python main.py [listen|mqtt]")
            print("  - No argument: Query device status once")
            print("  - listen: Listen for real-time updates")
            print("  - mqtt: Start MQTT bridge")
    else:
        query_status()
