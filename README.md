# Omron Viva Interface
This tool allows you to extract data from Omron Viva scale devices.
The data will be persisted into a simple local SQLite database.

# Install
```
git clone git@github.com:magcode/omviva.git
cd omviva
pip3 install -r requirements.txt
```

# Pair
For every user (1-4) you need to "pair" the scale with your Linux server.

Turn on the scale
Select the user by pressing the "arrow right" button
Long press the Bluetooth button

```
python3 omviva.py -pair 3
```
You should eventually see "OK" and hear two beeps.

# Trigger the sync
You can either trigger the sync/download of data using a Bluetooth Agent Service running on the same machine. This uses passive scanning and recognized the Omviva device. The second option is to use any other device to detect the Omviva and publish this information using MQTT.

## Using Bluetooth Agent Service
In the configuration set `"TRIGGER_MODE": "BT"`
You need to run a bluetooth agent.

```
curuser=`whoami`
__service="
[Unit]
Description=Bluetooth Agent Service
After=network.target

[Service]
ExecStart=/usr/bin/bt-agent
Restart=always
User=$curuser

[Install]
WantedBy=multi-user.target
"


echo "$__service" | sudo tee /etc/systemd/system/btagent.service
sudo systemctl daemon-reload
sudo service btagent start
```

## Using MQTT
In the configuration set 

```
"TRIGGER_MODE": "MQTT"
"MQTT_HOST": "mybroker",
"MQTT_PORT": 1883,
"MQTT_TOPIC": "home/blegateway/omviva",
```

Any message on this topic will trigger a sync.
Here is an example how to use a shelly device script for this purpose:

```
let CONFIG = {
  scan_duration: BLE.Scanner.INFINITE_SCAN,
  topic: "home/blegateway/omviva"
};



function scanCB(ev, res) {
  //console.log(res);
  
  if (ev !== BLE.Scanner.SCAN_RESULT) return;
   if (res.addr.toString().toUpperCase() == "<OMVIVA MAC HERE>") {
     if(MQTT.isConnected()) {
            MQTT.publish(CONFIG.topic, btoh(res.advData), 0, false);
      }
   }  

}

// retry several times to start the scanner if script was started before
// BLE infrastructure was up in the Shelly
function startBLEScan() {
  let bleScanSuccess = BLE.Scanner.Start({ duration_ms:  CONFIG.scan_duration, active: false }, scanCB);
  if( bleScanSuccess === false ) {
    Timer.set(1000, false, startBLEScan);
  } else {
    console.log('Success: BLE passive scanner running');
  }
}

//Check for BLE config and print a message if BLE is not enabled on the device
let BLEConfig = Shelly.getComponentConfig('ble');
if(BLEConfig.enable === false) {
  console.log('Error: BLE not enabled');
} else {
  Timer.set(1000, false, startBLEScan);
}
```


# install as a service

```
curuser=`whoami`
__service="
[Unit]
Description=Omron Viva Sync Service

[Service]
WorkingDirectory=/home/marko/omviva
ExecStart=/home/marko/pythonenv/bin/python3 /home/marko/omviva/omviva.py
User=$curuser
Environment=

[Install]
WantedBy=multi-user.target
"

echo "$__service" | sudo tee /etc/systemd/system/omviva.service
sudo systemctl daemon-reload
sudo systemctl enable omviva.service
sudo service omviva start

```

# Auto-Transfer the database
You can transfer the `viva_measurements.db` file to a remote server.
Use the following settings in `config.json`:

```
    "SCP_HOST": "myserver",
    "SCP_USER": "myuser",
    "SCP_PASSWORD": "mypassword",
    "SCP_PATH": "/opt/omviva/"
```