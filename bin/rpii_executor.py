from threading import Thread
from time import sleep

import laser_alignment_listener
import read_serial_temp_scanner
from paho.mqtt import client as mqtt_client

KillAll = False
UnreportedExceptions = []
ScriptList = {laser_alignment_listener, read_serial_temp_scanner}

MQTT_SERVER = "localhost"  # specify the broker address, it can be IP of raspberry pi or simply localhost
MQTT_PATH = "rpii_executor"  # this is the name of topic, like temp
MQTT_PORT = 1883


def connect_mqtt():
    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            print("Connected to MQTT Broker!")
        else:
            print("Failed to connect, return code %d\n", rc)

    client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION1)
    # client.username_pw_set(username, password)
    client.on_connect = on_connect
    client.connect(MQTT_SERVER)
    return client


# also the MQTT broker
def publish_msg(client, msg):
    try:
        client.loop_start()
        result = client.publish(MQTT_PATH, msg)

        # result: [0, 1]
        status = result[0]
        if status == 0:
            print(f"Send `{msg}` to topic `{MQTT_PATH}`")
        else:
            print(f"Failed to send message to topic {MQTT_PATH}")
        client.loop_stop()
    except Exception as e:
        print(f"MQTT excepted trying to send: {msg}: {e}")


# thread function that runs function in while 1 loop and reports exceptions
def execute_script_indefinitely(script):
    while True:
        try:
            script.main()
        except Exception as e:
            UnreportedExceptions.append(f"Script: {str(script)} excepted: {e}")
            sleep(30)


if __name__ == "__main__":
    client = connect_mqtt()
    client.connect(MQTT_SERVER)

    # kick off function threads
    for script in ScriptList:
        thread = Thread(target=execute_script_indefinitely, args=(script,))
        thread.start()

    client.loop_start()

    while True:
        # check for status/exception updates
        if len(UnreportedExceptions):
            # pop exception off the list
            msg = UnreportedExceptions.pop()
            # report those exception updates thru MQTT
            publish_msg(client, msg)

        sleep(5)

    client.loop_stop()
