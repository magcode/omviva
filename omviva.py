from malog import setupLogging
from datetime import datetime

from aiomqtt import Client
from omviva_comms import OmronBLE
import asyncio
import json
from pathlib import Path
from omviva_persistence import VivaPersistence
from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.assigned_numbers import AdvertisementDataType
from bleak.backends.bluezdbus.advertisement_monitor import OrPattern
from bleak.backends.bluezdbus.scanner import BlueZScannerArgs
from bleak.backends.scanner import AdvertisementData
from scp import SCPClient
import paramiko
from signal import SIGINT, SIGTERM
import sys
import argparse


logger = None
config = None
isReading = False
scanner = None

DATABASE_NAME = "viva_measurements.db"


def signal_handler():
    logger.info("Exiting")
    sys.exit(0)


async def mqtt_listener():
    # this assumes that "something" is informing us that the Omron VIVA is ready to be read
    # this something can be a bluetooth passive scanning script on a shelly bluetooth device
    loop = asyncio.get_running_loop()
    loop.add_signal_handler(SIGINT, signal_handler)
    loop.add_signal_handler(SIGTERM, signal_handler)
    async with Client(config["MQTT_HOST"]) as client:
        await client.subscribe(config["MQTT_TOPIC"])
        try:
            async for message in client.messages:
                logger.info(f"Got sync command via MQTT on {message.topic} with {message.payload.decode()}")                    
                if isReading is False:
                    logger.info("Starting sync")
                    await sync()
                    logger.info("Sync done")
                else:
                    logger.info("Sync already in progress, ignoring MQTT command")
        except asyncio.CancelledError:
            logger.info("MQTT listener cancelled")


def scp_transfer(local_file, remote_file, hostname, username, password):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname, username=username, password=password)

    with SCPClient(client.get_transport()) as scp:
        scp.put(local_file, remote_file)

    client.close()


def getConfig():
    configFile = Path(__file__).with_name("config.json")
    with configFile.open("r") as jsonfile:
        config = json.load(jsonfile)
        return config


async def sync():
    global isReading
    isReading = True
    success = False
    attempts = 0
    while not success:
        attempts += 1
        viva = OmronBLE(logger=logger, bleAddr=config["VIVA_MAC"])
        persistence = VivaPersistence(db_name=DATABASE_NAME)

        # we don't know for which user the transmission should be started
        # also we cannot read all users in one connect cycle
        # so the idea is to cycle between users
        noOfUsers = config["NO_OF_USERS"]
        last_user = persistence.get_last_sync_user()
        if last_user[0]:
            last_sync_time = datetime.fromtimestamp(last_user[0]).strftime("%Y-%m-%d %H:%M:%S")
            user = last_user[1] + 1
            if user > noOfUsers:
                user = 1
            logger.info(f"Last user was #{last_user[1]} on {last_sync_time}. Next user is #{user}")
        else:
            user = 1
            logger.info(f"First sync, starting with user #{user}")

        lastSeq = persistence.get_highest_sequence_number_for_user(user)
        if lastSeq is None:
            lastSeq = 0
        logger.info(f"Last sequence for user #{user} was {lastSeq}")

        try:
            await asyncio.sleep(2)
            await viva.connect()
            logger.info(f"Syncing user #{user}")
            allRecs = await viva.get_records(user, lastSeq + 1)
            for rec in allRecs:
                persistence.persist_measurement(rec)

            logger.info(f"Syncing done for user #{user}")
            persistence.store_success(user)
            await viva.disconnect()
            success = True
            persistence.close()
            if config["SCP_HOST"]:
                scp_transfer(
                    DATABASE_NAME,
                    config["SCP_PATH"] + DATABASE_NAME,
                    config["SCP_HOST"],
                    config["SCP_USER"],
                    config["SCP_PASSWORD"],
                )
                logger.info("Database transferred to remote host")
            break
        except Exception as e:
            logger.error(f"Error syncing (attempt {attempts}): {e}")
        finally:
            persistence.close()

        if attempts > 3:
            logger.error("Max attempts reached, aborting sync")
            break
    isReading = False
    await mqtt_listener()

async def pair(user):
    viva = OmronBLE(logger=logger, bleAddr=config["VIVA_MAC"])

    try:
        await viva.connect()
        await viva.register_user(user)
        await viva.disconnect()
    except Exception as e:
        logger.error(f"Pair Error: {e}")


async def bl_passive_scan_callback(device: BLEDevice, advertisement_data: AdvertisementData):
    if device.address == config["VIVA_MAC"] and isReading is False:
        logger.info(f"I found {device.name} via passive scan")
        await scanner.stop()
        await sync()


async def bl_passive_scan():
    # this requires BLE passive scanning. See https://github.com/hbldh/bleak/pull/884
    # flag --experimental is needed
    # BlueZ >= 5.56
    # Linux kernel >= 5.10.

    global scanner
    scanner = BleakScanner(
        bl_passive_scan_callback,
        None,
        scanning_mode="passive",
        bluez=BlueZScannerArgs(
            or_patterns=[
                OrPattern(0, AdvertisementDataType.FLAGS, b"\x06"),
            ]
        ),
    )

    while True:
        if isReading is False:
            await scanner.start()
            await asyncio.sleep(10.0)
            await scanner.stop()
        else:
            logger.info("Waiting for sync to finish before scanning again")
            await asyncio.sleep(60.0)


if __name__ == "__main__":
    config = getConfig()

    logger = setupLogging(config)
    logger.info("Omron VIVA Sync Tool started")

    parser = argparse.ArgumentParser(description="Omron VIVA Sync Tool")
    parser.add_argument("-pair", type=int, help="Pair with a new user")
    args = parser.parse_args()

    if args.pair:
        logger.info(f"Pairing with user #{args.pair}")
        asyncio.run(pair(args.pair))
        sys.exit(0)

    if config["TRIGGER_MODE"] == "mqtt":
        logger.info("Using MQTT trigger mode")
        asyncio.run(mqtt_listener())
    else:
        logger.info("Using BL passive scan trigger mode")
        asyncio.run(bl_passive_scan())
