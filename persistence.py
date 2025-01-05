from omviva_measurement import OmronMeasurementWS
import sqlite3
import decimal
import time

D = decimal.Decimal


class VivaPersistence:
    def __init__(self, db_name="viva_measurements.db"):
        self.db_name = db_name
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()
        self.create_database()

    def create_database(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS measurements (
                SequenceNumber INTEGER,
                TimeStamp INTEGER,
                UserID INTEGER,
                Weight REAL,
                BMI REAL,
                Height REAL,
                BodyFatPercentage REAL,
                BasalMetabolism INTEGER,
                SkeletalMusclePercentage REAL,
                VisceralFatLevel REAL,
                BodyAge INTEGER
            )
        """)

        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS syncs (
            TimeStamp INTEGER,
            UserID INTEGER
            )
        """)
        self.conn.commit()

    def get_last_sync_user(self):
        self.cursor.execute(
            """
            SELECT MAX(TimeStamp), UserID FROM syncs
        """
        )
        result = self.cursor.fetchone()
        return result

    def store_success(self, user_id):
        self.cursor.execute(
            """
            INSERT INTO syncs (TimeStamp, UserID) VALUES (?, ?)
        """,
            (int(time.time()), user_id),
        )
        self.conn.commit()

    def get_highest_sequence_number_for_user(self, user_id):
        self.cursor.execute(
            """
            SELECT MAX(SequenceNumber) FROM measurements WHERE UserID = ?
        """,
            (user_id,),
        )
        result = self.cursor.fetchone()[0]
        return result

    def persist_measurement(self, measurement):
        sqlite3.register_adapter(D, adapt_decimal)
        sqlite3.register_converter("decimal", convert_decimal)
        self.cursor.execute(
            """
            SELECT COUNT(*) FROM measurements WHERE SequenceNumber = ? AND UserID = ?
        """,
            (int(measurement.mSequenceNumber), int(measurement.mUserID)),
        )
        if self.cursor.fetchone()[0] > 0:
            print(f"{measurement.mSequenceNumber} already exists")
            return

        self.cursor.execute(
            """
            INSERT INTO measurements (SequenceNumber, TimeStamp, UserID, Weight, BMI, Height, BodyFatPercentage, BasalMetabolism, SkeletalMusclePercentage, VisceralFatLevel, BodyAge)
            VALUES (?, ?, ?, ?, ?, ?,?,?,?,?,?)
        """,
            (
                int(measurement.mSequenceNumber),
                int(measurement.mTimeStamp),
                int(measurement.mUserID),
                measurement.mWeight,
                measurement.mBMI,
                measurement.mHeight,
                measurement.mBodyFatPercentage,
                int(measurement.mBasalMetabolism),
                measurement.mSkeletalMusclePercentage,
                measurement.mVisceralFatLevel,
                int(measurement.mBodyAge),
            ),
        )
        self.conn.commit()

    def close(self):
        self.conn.close()


def adapt_decimal(d):
    return str(d)


def convert_decimal(s):
    return D(s)


# test usage
if __name__ == "__main__":
    persistence = VivaPersistence(db_name="viva_measurements.db")

    data = bytearray.fromhex(
        "3e00100100903de8070c010a173801fe00e006c2c01f0100e9009a1b600108340906063e00100200903de8070c010a2b1701fe00e006c2c01f0200ec00471b570108370906063e00100300cc3de8070c1e101c2d01ff00e006c2c01f0300dd00bb1c7e01082b090606"
    )
    for i in range(0, len(data), 35):
        bcm = OmronMeasurementWS(data1=data[i : i + 19], data2=data[i + 19 : i + 35])
        persistence.persist_measurement(bcm)
