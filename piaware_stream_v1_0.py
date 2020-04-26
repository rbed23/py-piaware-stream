'''piaware flight data downloader to IoT'''
# !/usr/bin/env python

# requires: AWSIoTPythonSDK, config.json file

from __future__ import print_function
from datetime import datetime as dt
import json
import ssl
import sys
import time

import requests
from AWSIoTPythonSDK.core.protocol.paho import client as mqtt

swv = 'v1.0'


def setup_iot_device():
    '''
    Sets up the IoT device configuration

    <<type device>> dict
    <<desc device>> specific device details
    '''
    try:
        with open('piaware_stream_config.json', 'r') as f:
            cfg = json.load(f)
            device = {
                "endpoint_url": cfg['aws_vars']['awsendpoint'],
                "endpoint_port": int(cfg['aws_vars']['awsendpoint_port']),
                "client_id": cfg['aws_vars']['clientId'],
                "ca_file": cfg['aws_vars']['caPath'],
                "key_file": cfg['aws_vars']['keyPath'],
                "cert_file": cfg['aws_vars']['certPath'],
                "channels": cfg['aws_vars']['topics'],
                "poll_delay": int(cfg['piaware_script']['pollDelay']),
                "send_method": int(cfg['piaware_script']['deliveryMethod']),
                # 0: IoT publish only
                # 1: HTTP POST only
                # 2: both IoT publish and HTTP POST
                "dump1090_url": cfg['piaware_script']['dump1090dataUrl']
                # as specified in the piaware service documentation
            }

            # optional: a HTTP service to POST results
            if cfg['piaware_script']['piawarePostUrl']:
                device['post_url'] = cfg['piaware_script']['piawarePostUrl']

            if device['send_method'] == 1 or device['send_method'] == 2 \
                    and not device['post_url']:
                print(f"HTTP POST URL not configured... publishing IoT only")
                device['send_method'] = 0

    except Exception as err:
        print(f"Exception Error: Unable to open config.json file\n{err}")
    else:
        return device


def setup_client(device):
    '''
    Sets up IoT client object configuration

    <type device> dict
    <desc device> valid device configuration

    <<type client>> Client object (from AWSIoTPythonSDK MQTT PAHO library)
    <<desc client>> with set flags, callbacks, and TLS credentials
    '''
    try:
        client = mqtt.Client(device['client_id'])
        print('MQTT Client initialized; setting flags...')
    except Exception as err:
        print(f"Exception Error: Unable to initialize client object\n{err}")

    # set flags
    client.bad_connection_flag = False
    client.bad_auth_flag = False
    client.connected_flag = False
    client.disconnected_flag = False

    print('binding callbacks...')
    try:
        client.on_connect = onConnect
        client.on_disconnect = onDisconnect
        '''
        client.on_message = onMessage
        client.on_publish = onPublish
        client.on_subscribe = onSubscribe
        client.on_unsubscribe = onUnsubscribe
        client.on_log = onLog
        '''
        print('callbacks bound.')
    except Exception as err:
        print(f"Exception Error: error binding callbacks to client\n{err}")

    print('setting TLS credentials...')
    try:
        client.tls_set(
            ca_certs=device['ca_file'],
            certfile=device['cert_file'],
            keyfile=device['key_file'],
            cert_reqs=ssl.CERT_REQUIRED,
            tls_version=ssl.PROTOCOL_SSLv23,
            ciphers=None)
        print('TLS credentials set successfully')
    except Exception as err:
        print(f"Exception Error: error setting tls credentials\n{err}")

    return client


# Initialize the MQTT on_connect callback function
def onConnect(client, userdata, flags, rc):
    '''
    Successful connection callback handler

    <type client> Client object
    <desc client> object connected to broker

    <type userdata> str
    <desc userdata> n/a
        see AWSIoTPythonSDK.core.protocol.paho.client L340

    <type flags> dict
    <desc flags> contains response flags from the broker
        see AWSIoTPythonSDK.core.protocol.paho.client L347

    <type rc> int
    <desc rc> value of rc determines success or not
        see AWSIoTPythonSDK.core.protocol.paho.client L353
    '''
    print('[in onConnect callback]')
    if rc == 0:
        client.connected_flag = True
        client.disconnected_flag = False
        print(f"{dt.utcnow().strftime('%Y-%m-%d_%H:%M:%S')}: "
              f"MQTT Connected OK; return code = {rc}")
        print(f"ClientId Connected : {client._client_id}")
    else:
        client.bad_connection_flag = True
        print(f"{dt.utcnow().strftime('%Y-%m-%d_%H:%M:%S')}: "
              f"MQTT Connection Error; return code = {rc}")
        print(f"MQTT RC Error: {mqtt.error_string(rc)}")
        print(f"Lookup RC designation << {rc} >> in "
              f"AWSIoTPythonSDK.core.protocol.paho.client "
              f"documentation (L353) for more information")


def onDisconnect(client, userdata, rc):
    '''
    Disconnection callback handler, purposeful or otherwise

    <type client> mqtt paho Client object
    <desc client> disconnected object

    <type userdata> str
    <desc userdata> see AWSIoTPythonSDK.core.protocol.paho.client L340

    <type rc> int
    <desc rc> value of rc determines success or not
        see AWSIoTPythonSDK.core.protocol.paho.client L353
    '''
    print('[in onDisconnect callback]')
    print(f"{dt.utcnow().strftime('%Y-%m-%d_%H:%M:%S')} "
          f"(dt.utc): MQTT Disconnection; return code = {rc}")
    print(f"Lookup RC designation << {rc} >> in "
          f"AWSIoTPythonSDK.core.protocol.paho.client documentation (L353)")

    client.connected_flag = False
    client.disconnected_flag = True
    if rc == 1:
        print('Check if the certificate is active\n'
              'Check if the policy rules for this device are setup correctly')


def onMessage(client, userdata, message):
    print('[in onMessage callback]')
    mssg = json.loads(message.payload)
    print(f"{dt.utcnow().strftime('%Y-%m-%d_%H:%M:%S')} "
          f"(dt.utc): Received message from {mssg['_client_id']}")


def refresh(dump_curl):
    '''
    Refreshes the piaware payload

    <type dump_curl> str
    <desc dump_curl> local dump1090 url

    <<type myflights>> dict
    <<desc myflights>> polled flights information from piaware device
    '''
    # sets up JSON variable with header and flight list info
    myflights = {
        "_fName": "local_stream_" +
        str(dt.now().strftime('%Y-%m-%d_%H:%M:%S')),
        "polled_flights_list": []
    }

    # open the data url
    try:
        req = requests.get(dump_curl)
        req.raise_for_status()
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTPS Error: {http_err} at: "
              f"{dt.now().strftime('%Y-%m-%d_%H-%M-%S')} "
              f"when requesting GET from: {dump_curl}")
    except requests.exceptions.RequestException as req_err:
        print(f"Request Exception: {req_err} at: "
              f"{dt.now().strftime('%Y-%m-%d_%H-%M-%S')} "
              f"when requesting GET from: {dump_curl}")
    except Exception as err:
        print(f"Unspecified Error: {err} at: "
              f"{dt.now().strftime('%Y-%m-%d_%H-%M-%S')} "
              f"when requesting GET from: {dump_curl}")
    # execute iff successful GET
    else:
        # load as JSON
        json_payload = req.json()

        # appdend data from dump1090-fa GET to the polled flights list
        myflights["polled_flights_list"].append(json_payload)

    # return myflights data, independent of successful 'get' try
    finally:
        return myflights


def exit_script(client):
    # stop loop and disconnect the device client from broker
    client.loop_stop()
    client.disconnect()
    # exit script and depend on autorestart service
    sys.exit()


def main():
    try:
        device = setup_iot_device()
    except Exception as err:
        print(f"Error: Unable to setup IoT device\n{err}")

    try:
        pi_client = setup_client(device)
    except Exception as err:
        print(f"Error: unable to setup MQTT client\n{err}")

    script_info = {
        "_sw_version": swv,
        "_client_id":  device['client_id'],
        }
    header_data = {"content-type": "application/json"}

    print("---------------------------------------------------------------")
    print("STARTING LOCAL PIAWARE SCRIPT")
    print(f"Date: {dt.now().strftime('%Y %m %d')}")
    print(f"Time: {dt.now().strftime('%H : %M : %S')}")
    print(f"Timestamp: {dt.now().strftime('%Y-%m-%d_%H:%M:%S')}")

    print(f"Connecting to broker: {device['endPtUrl']}")
    try:
        pi_client.connect(device['endpoint_url'], device['endpoint_port'])
    except Exception as err:
        print(f"Error: connection attempt to broker unsuccessful\n{err}")

    pi_client.loop_start()

    while not pi_client.connected_flag and not pi_client.bad_auth_flag:
        print('waiting for connection...')
        time.sleep(2)
        if pi_client.bad_auth_flag:
            exit_script(pi_client)

    print('connection established')

    # continuously poll, publish and / or POST
    while True:
        # counters for outputting successes / errors
        err_cnt = 0
        suc_cnt = 0

        # create new FlightData object from refresh module
        myflights_send = refresh(device['dump1090_url'])
        myflights_send.update(script_info)

        # if the device send method is 0 (publish) or 2 (both)...
        if device['send_method'] == 0 or device['send_method'] == 2:
            # publish to all channels
            for each_topic in device['channels']:
                if "<clientId>" in each_topic:
                    each_topic = each_topic.replace("<clientId>",
                                                    device['client_id'])
                try:
                    rc = pi_client.publish(each_topic, myflights_send, 1)
                except Exception as err:
                    print(f"Error: general exception in MQTT << {rc} >>: "
                          f"{mqtt.error_string(rc)}\n{err}")

        # if the device send method is 1 (post) or 2 (both)...
        if device['send_method'] == 1 or device['send_method'] == 2:
            # post to listening server
            try:
                res = requests.post(
                    device['post_url'],
                    data=myflights_send,
                    headers=header_data
                    )
                res.raise_for_status()
                suc_cnt += 1    # increment successful POST counter
                err_cnt = 0     # reset error counter
                if suc_cnt == 1000:
                    print(f"{dt.now().strftime('%Y-%m-%d_%H:%M:%S')}: "
                          f"{suc_cnt} successful POST attempts")
                    suc_cnt = 0
            except requests.exceptions.HTTPError as http_err:
                err_cnt += 1
                if err_cnt == 100 or err_cnt == 1000 or err_cnt == 10000:
                    print(f"HTTPS Error: {http_err} at: "
                          f"{dt.now().strftime('%Y-%m-%d_%H:%M:%S')} "
                          f"connecting to: {device['post_url']}\n"
                          f"unavailable after {err_cnt} attempts")
                if err_cnt == 10000:
                    print('resetting...')
                    err_cnt = 0
            except requests.exceptions.RequestException as req_err:
                err_cnt += 1
                if err_cnt == 100 or err_cnt == 1000 or err_cnt == 10000:
                    print(f"Request Error: {req_err} at: "
                          f"{dt.now().strftime('%Y-%m-%d_%H:%M:%S')} "
                          f"connecting to: {device['post_url']}\n"
                          f"unavailable after {err_cnt} attempts")
                if err_cnt == 10000:
                    print('resetting...')
                    err_cnt = 0
            except Exception as err:
                print(f"Unspecified Error: {err} at: "
                      f"{dt.now().strftime('%Y-%m-%d_%H-%M-%S')} "
                      f"when requesting POST to: {device['post_url']}")
                err_cnt += 1

        time.sleep(device['poll_delay'])

    # failure handling if the infinite script loop were to be exited
    reset_mssg = device['client_id'] + ": DEVICE SCRIPT EXPERIENCED FAILURE"
    print(reset_mssg)
    for each_topic in device['channels']:
        if "<clientId>" in each_topic:
            each_topic = each_topic.replace("<clientId>", device['client_id'])
        try:
            rc = pi_client.publish(each_topic, reset_mssg, 1)
        except Exception as err:
            print(f"Error: general exception in MQTT << {rc} >>: "
                  f"{mqtt.error_string(rc)}\n{err}")
    if device['post_url'] is not None:
        try:
            res = requests.post(
                device['post_url'],
                data=reset_mssg,
                headers='{"content-type":"application/text"}'
                )
        except Exception as err:
            print(f"Error: {err}\n"
                  f"when exiting script...")
    exit_script(pi_client)


if __name__ == "__main__":
    main()
