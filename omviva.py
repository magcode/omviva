from datetime import datetime
from omviva_comms import OmronBLE
import asyncio
import logging
import json
from pathlib import Path
from custom_logging import setupLogging
from persistence import VivaPersistence

logger = None
config = None


def getConfig():
    configFile = Path(__file__).with_name("config.json")
    with configFile.open("r") as jsonfile:
        config = json.load(jsonfile)
        return config


async def sync():
    viva = OmronBLE(logger=logger, bleAddr=config["VIVA_MAC"])
    persistence = VivaPersistence(db_name="viva_measurements.db")

    # idea is to cycle between users
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
        await viva.connect()
        allRecs = await viva.get_records(user, lastSeq + 1)
        for rec in allRecs:
            persistence.persist_measurement(rec)
        persistence.store_success(user)
        await viva.disconnect()
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        persistence.close()


async def pair():
    user = 2
    viva = OmronBLE(logger=logger, bleAddr=config["VIVA_MAC"])

    try:
        await viva.connect()
        await viva.register_user(user)
        await viva.disconnect()
    except Exception as e:
        logger.error(f"Error: {e}")


async def main():
    global config
    global logger
    config = getConfig()
    logger = logging.getLogger("omviva")
    setupLogging(logger, config)
    logger.info("Started")

    await sync()
    # await pair()


asyncio.run(main())
