# py-piaware-stream
Streams Piaware dump1090-fa flight data to AWS IoT endpoint and/or HTTP POST URL

*Requires:*
1. Raspberry Pi Model B
1. Piaware RF Adapter
1. Piaware RF Antenna
1. Piaware software installed on RasPi 
    [(instructions)](https://flightaware.com/adsb/piaware/install)

1. AWSIoTPythonSDK package installed 
    [(inscructions)](https://pypi.org/project/AWSIoTPythonSDK/)

1. AWS Account created
1. AWS IoT gateway configured
1. Registered AWS IoT 'Thing' with downloaded security credentials
1. the following files installed under the ~/opt/ directory
    - piaware_stream_v1_0.py
    - piaware_stream_config.json
1. piaware_streamd.service file installed correctly 
    [(instructions)](https://www.raspberrypi.org/documentation/linux/usage/systemd.md)

## Piaware Stream Configuration file Options

__AWS Variables__

`"awsendpoint": "[AWS-IOT-ENDPOINT-DESIGNATOR-STR].iot.[AWS-REGION].amazonaws.com"`
- the correct AWS IoT endpoint URL designated for your AWS IoT Service environment 

`"awsendpoint_port": 8883`
- AWS IoT MQTT Protocol port mapping

`"clientId": "[DEVICE-CLIENT-ID]"`
- the unique client identifier for the specific piaware device

`"caPath": "PATH/TO/root-CA.crt"`
`"keyPath": "PATH/TO/private.pem.key"`
`"certPath": "PATH/TO/certificate.pem.crt"`
- x.509 client certificate file paths

`"topics": [LIST]`
- list of AWS IoT topics to publish the dump1090-fa data
    - note: subscribers to these topics must be setup to listen for this incoming data

__Script Variables__

`"deliveryMethod": [INT]`
- determines how the dump1090-fa data will be sent
    - **0** : publish to the AWS IoT endpoint
    - **1** : HTTP POST method to a listening URL
    - **2** : publish and POST together

`"dump1090dataUrl": "http://127.0.0.1/dump1090-fa/data/aircraft.json"`
- local URL where Piaware dump1090-fa data is being delivered

`"piawarePostUrl": "[URL-TO-POST-DATA]"`
- URL setup to receive incoming HTTP POST requests (via delivery methods 1,2)

`"pollDelay": 2`
- designates delay (in seconds) before polling the dump1090dataUrl link for refreshed fligth results

## Workflow

1. Raspberry Pi Piaware device is booted
1. Raspberry Pi Piaware device establishes an online network connection
1. Raspberry Pi Piaware device starts running Piaware software application
1. Raspberry Pi Piaware device starts running piaware_stream script
1. piaware_stream establishes secure connection with AWS IoT endpoint
1. piaware_stream polls Piaware application for fresh aircraft data (via dump1090-fa GET call)
1. piaware_stream gets, packages, and sends data
1. continues...
