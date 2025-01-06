from datetime import datetime
from omviva_comms import OmronBLE
import asyncio
import logging
import json
from pathlib import Path
from custom_logging import setupLogging
from persistence import VivaPersistence
from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.assigned_numbers import AdvertisementDataType
from bleak.backends.bluezdbus.advertisement_monitor import OrPattern
from bleak.backends.bluezdbus.scanner import BlueZScannerArgs
from bleak.backends.scanner import AdvertisementData

logger = None
config = None
isReading = False
scanner = None


def getConfig():
    configFile = Path(__file__).with_name("config.json")
    with configFile.open("r") as jsonfile:
        config = json.load(jsonfile)
        return config


async def sync():
    global isReading
    isReading = True
    viva = OmronBLE(logger=logger, bleAddr=config["VIVA_MAC"])
    persistence = VivaPersistence(db_name="viva_measurements.db")

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
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        persistence.close()

    isReading = False


async def pair():
    user = 2
    viva = OmronBLE(logger=logger, bleAddr=config["VIVA_MAC"])

    try:
        await viva.connect()
        await viva.register_user(user)
        await viva.disconnect()
    except Exception as e:
        logger.error(f"Error: {e}")


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
    logger = logging.getLogger("omviva")
    setupLogging(logger, config)
    logger.info("Omron VIVA Sync Tool started")
    if config["TRIGGER_MODE"] == "mqtt":
        logger.info("MQTT trigger mode not implemented yet")
    else:
        asyncio.run(bl_passive_scan())
