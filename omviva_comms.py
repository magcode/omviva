import asyncio
from omviva_measurement import OmronMeasurementWS
from bleak.exc import BleakDeviceNotFoundError
import bleak


class OmronBLE:
    RECORD_ACCESS_CONTROL_POINT = "00002a52-0000-1000-8000-00805f9b34fb"
    USER_CONTROL_POINT = "00002a9f-0000-1000-8000-00805f9b34fb"
    OMRON_MEASUREMENT_WS = "8ff2ddfb-4a52-4ce5-85a4-d2f97917792a"

    DEVICE_RX_CHANNEL_UUIDS = [
        # "00002a2b-0000-1000-8000-00805f9b34fb",  # Current Time Handle: 1296  510
        USER_CONTROL_POINT,  # User Control Point Handle: 1840  730
        # "00002a99-0000-1000-8000-00805f9b34fb",  # Database Change Increment Handle: 1808  710
        RECORD_ACCESS_CONTROL_POINT,  # Record Access Control Point Handle: 1552  610
        OMRON_MEASUREMENT_WS,  # OmronMeasurementWS Handle: 1568 620
    ]

    # DEVICE_DATA_RX_CHANNEL_INT_HANDLES = [0x510, 0x730, 0x710, 0x610, 0x620]
    DEVICE_DATA_RX_CHANNEL_INT_HANDLES = [0x730, 0x610, 0x620]

    def __init__(self, bleAddr, logger, pairing=False):
        self.rx_raw_channel_buffer = [None] * 5  # a buffer for each channel
        self.bleAddr = bleAddr
        self.logger = logger
        self.current_rx_notify_state_flag = False
        self.ble_client = None

    async def connect(self):
        self.ble_client = bleak.BleakClient(self.bleAddr, timeout=10)
        try:
            self.logger.info(f"Attempt connecting to {self.bleAddr}.")
            await self.ble_client.connect()
            await asyncio.sleep(1)
            await self.ble_client.pair(protection_level=2)
            self.logger.info("pair done")
        except BleakDeviceNotFoundError as e:
            # self.logger.error(f"Device not found. {e}")
            raise e
        except Exception as e:
            # self.logger.error(f"Something else {e}")
            raise e

    async def disconnect(self):
        if self.ble_client.is_connected:
            await self.ble_client.unpair()
            try:
                await self.ble_client.disconnect()
            except AssertionError as e:
                self.logger.warn(f"Bleak AssertionError during disconnect. {e}")

    async def _enable_rx_channel_notify_and_callback(self):
        await asyncio.sleep(5)
        if not self.current_rx_notify_state_flag:
            for rx_channel_uuid in self.DEVICE_RX_CHANNEL_UUIDS:
                self.logger.debug(f"start_notify for {rx_channel_uuid}")
                await self.ble_client.start_notify(rx_channel_uuid, self._callback_for_rx_channels)
            self.current_rx_notify_state_flag = True

    async def _disable_rx_channel_notify_and_callback(self):
        if self.current_rx_notify_state_flag:
            for rx_channel_uuid in self.DEVICE_RX_CHANNEL_UUIDS:
                await self.ble_client.stop_notify(rx_channel_uuid)
            self.current_rx_notify_state_flag = False

    def _callback_for_rx_channels(self, bleak_gatt_char, rx_bytes):
        if isinstance(bleak_gatt_char, int):
            rx_channel_id = self.DEVICE_DATA_RX_CHANNEL_INT_HANDLES.index(bleak_gatt_char)
        else:
            rx_channel_id = self.DEVICE_DATA_RX_CHANNEL_INT_HANDLES.index(bleak_gatt_char.handle)

        self.logger.debug(f"rx ch{rx_channel_id} {bleak_gatt_char} < {convert_byte_array_to_hex_string(rx_bytes)}")
        if self.rx_raw_channel_buffer[rx_channel_id] is None:
            self.rx_raw_channel_buffer[rx_channel_id] = rx_bytes
        else:
            self.rx_raw_channel_buffer[rx_channel_id] += rx_bytes

        if bleak_gatt_char.uuid == self.RECORD_ACCESS_CONTROL_POINT:
            if rx_bytes[0] == 0x05:
                raw_value = int.from_bytes(rx_bytes[2:3], byteorder="little")
                self.logger.info(f"NumberOfStoredRecordsResponse: {raw_value}")

    async def register_user(self, user_index):
        await asyncio.sleep(10)
        await self._enable_rx_channel_notify_and_callback()

        self.logger.info("Step 1")
        packet = get_register_new_user(user_index)
        await self.ble_client.write_gatt_char("00002a9f-0000-1000-8000-00805f9b34fb", packet)

        await asyncio.sleep(3)
        self.logger.info("Step 2 Consent")
        packet = get_consent(user_index)
        await self.ble_client.write_gatt_char("00002a9f-0000-1000-8000-00805f9b34fb", packet)
        await asyncio.sleep(3)

        self.logger.info("Step 7")
        await self.ble_client.write_gatt_char("00002a52-0000-1000-8000-00805f9b34fb", bytearray.fromhex("0401")[:16])
        await asyncio.sleep(3)

        self.logger.info("Step 8")
        await self.ble_client.write_gatt_char("00002a52-0000-1000-8000-00805f9b34fb", bytearray.fromhex("0101")[:16])
        await asyncio.sleep(3)

        self.logger.info("Step 9")
        await self.ble_client.write_gatt_char("00002a52-0000-1000-8000-00805f9b34fb", bytearray.fromhex("1000")[:16])
        await asyncio.sleep(3)

        await self._disable_rx_channel_notify_and_callback()

    async def register_user2(self, user_index):
        self.logger.info(f"Register user started for user #{user_index}")
        await self._enable_rx_channel_notify_and_callback()

        self.logger.info("Step 1")
        packet = get_register_new_user(user_index)
        await self.send("00002a9f-0000-1000-8000-00805f9b34fb", convert_byte_array_to_hex_string(packet))

        self.logger.info("Step 2 Consent")
        packet = get_consent(user_index)
        await self.send("00002a9f-0000-1000-8000-00805f9b34fb", convert_byte_array_to_hex_string(packet))
        await asyncio.sleep(3)

        self.logger.info("Step 3 Request count")
        await self.send("00002a52-0000-1000-8000-00805f9b34fb", "0401")

        self.logger.info("Step 4 Request data")
        await self.send("00002a52-0000-1000-8000-00805f9b34fb", "0101")

        self.logger.info("Step 5 Finish")
        await self.send("00002a52-0000-1000-8000-00805f9b34fb", "1000")

        await self._disable_rx_channel_notify_and_callback()

    async def get_records(self, user_index, last_sequence):
        await self._enable_rx_channel_notify_and_callback()

        packet = get_consent(user_index)
        await self.send(self.USER_CONTROL_POINT, convert_byte_array_to_hex_string(packet))

        packet = get_filter(last_sequence, reportCountOnly=True)
        await self.send(self.RECORD_ACCESS_CONTROL_POINT, convert_byte_array_to_hex_string(packet))

        packet = get_filter(last_sequence, reportCountOnly=False)
        await self.send(self.RECORD_ACCESS_CONTROL_POINT, convert_byte_array_to_hex_string(packet))
        await self.send(self.RECORD_ACCESS_CONTROL_POINT, "1000")

        measurements = []
        if self.rx_raw_channel_buffer[2]:
            data = self.rx_raw_channel_buffer[2]

            for i in range(0, len(data), 35):
                bcm = OmronMeasurementWS(data1=data[i : i + 19], data2=data[i + 19 : i + 35])
                measurements.append(bcm)
                self.logger.info(f"Got measurement index {bcm.mSequenceNumber} with weight {bcm.mWeight}")

        await self._disable_rx_channel_notify_and_callback()
        return measurements

    async def send(self, char, data):
        self.logger.debug(f"tx > {char} {data}")
        await self.ble_client.write_gatt_char(char, bytearray.fromhex(data)[:16])
        await asyncio.sleep(3)


def get_consent(userIndex):
    DEFAULT_CONSENT_CODE = 0x020E
    packet = bytearray(4)
    packet[0] = 0x02
    packet[1] = userIndex
    packet[2] = DEFAULT_CONSENT_CODE & 0x000000FF
    packet[3] = (DEFAULT_CONSENT_CODE >> 8) & 0x000000FF
    return packet


def get_register_new_user(userIndex):
    DEFAULT_CONSENT_CODE = 0x020E
    packet = bytearray(3)
    packet[0] = 0x01
    packet[1] = DEFAULT_CONSENT_CODE & 0x000000FF
    packet[2] = (DEFAULT_CONSENT_CODE >> 8) & 0x000000FF
    return packet


def get_filter(sequenceNumber, reportCountOnly=False):
    packet = bytearray(5)
    if reportCountOnly:
        packet[0] = 0x04  # ReportNumberOfStoredRecords
    else:
        packet[0] = 0x01  # ReportStoredRecords
    packet[1] = 0x03  # GreaterThanOrEqualTo
    packet[2] = 0x01  # FilterType.SequenceNumber
    packet[3] = sequenceNumber & 0x000000FF
    packet[4] = (sequenceNumber >> 8) & 0x000000FF
    return packet


def convert_byte_array_to_hex_string(array):
    return bytes(array).hex()
