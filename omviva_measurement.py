# translated from https://github.com/huraypositive/omron-android-sdk/blob/master/omronsdk/src/main/java/net/huray/omronsdk/ble/entity/internal/OmronMeasurementWS.java

from enum import Enum, IntFlag, auto
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List
from BodyCompositionFeature import BodyCompositionFeature
import time
import calendar

class OmronMeasurementWS:
    WEIGHT_UNIT_KILOGRAM = "kg"
    WEIGHT_UNIT_POUND = "lb"
    HEIGHT_UNIT_METER = "m"
    HEIGHT_UNIT_INCH = "in"

    SCALE = 3
    WEIGHT_RESOLUTION_KG_DEFAULT = 0.005
    WEIGHT_RESOLUTION_LB_DEFAULT = 0.01
    HEIGHT_RESOLUTION_M_DEFAULT = 0.001
    HEIGHT_RESOLUTION_IN_DEFAULT = 0.1

    def __init__(self, data1: bytes, data2: Optional[bytes] = None, feature: Optional['BodyCompositionFeature'] = None):
        self.mWeightUnit = ""
        self.mHeightUnit = ""
        self.mSequenceNumber = None
        self.mWeight = None
        self.mTimeStamp = None
        self.mUserID = None
        self.mBMI = None
        self.mHeight = None
        self.mBodyFatPercentage = None
        self.mBasalMetabolism = None
        self.mMusclePercentage = None
        self.mMuscleMass = None
        self.mFatFreeMass = None
        self.mSoftLeanMass = None
        self.mBodyWaterMass = None
        self.mImpedance = None
        self.mSkeletalMusclePercentage = None
        self.mVisceralFatLevel = None
        self.mBodyAge = None
        self.mBodyFatPercentageStageEvaluation = None
        self.mSkeletalMusclePercentageStageEvaluation = None
        self.mVisceralFatLevelStageEvaluation = None

        self._parse(data1, feature)
        if data2:
            self._parse(data2, feature)

    def _parse(self, data: bytes, feature: Optional['BodyCompositionFeature']):
        offset = 0
        flags = Flag.parse(int.from_bytes(data[offset:offset + 3], byteorder='little') & 0x00ffffff)
        offset += 3

        if Flag.ImperialUnit in flags:
            weight_measurement_resolution = feature.get_weight_measurement_resolution_lb() if feature else self.WEIGHT_RESOLUTION_LB_DEFAULT
            height_measurement_resolution = feature.get_height_measurement_resolution_in() if feature else self.HEIGHT_RESOLUTION_IN_DEFAULT
            self.mWeightUnit = self.WEIGHT_UNIT_POUND
            self.mHeightUnit = self.HEIGHT_UNIT_INCH
        else:
            weight_measurement_resolution = feature.get_weight_measurement_resolution_kg() if feature else self.WEIGHT_RESOLUTION_KG_DEFAULT
            height_measurement_resolution = feature.get_height_measurement_resolution_m() if feature else self.HEIGHT_RESOLUTION_M_DEFAULT
            self.mWeightUnit = self.WEIGHT_UNIT_KILOGRAM
            self.mHeightUnit = self.HEIGHT_UNIT_METER

        if Flag.SequenceNumberPresent in flags:
            self.mSequenceNumber = Decimal(int.from_bytes(data[offset:offset + 2], byteorder='little'))
            offset += 2

        if Flag.WeightPresent in flags:
            raw_value = int.from_bytes(data[offset:offset + 2], byteorder='little')
            self.mWeight = Decimal(raw_value * weight_measurement_resolution).quantize(Decimal('1.000'), rounding=ROUND_HALF_UP)
            offset += 2

        if Flag.TimeStampPresent in flags:
            self.mTimeStamp = self._parse_timestamp(data[offset:offset + 7])
            offset += 7

        if Flag.UserIDPresent in flags:
            self.mUserID = Decimal(data[offset])
            offset += 1

        if Flag.BMIAndHeightPresent in flags:
            raw_value = int.from_bytes(data[offset:offset + 2], byteorder='little')
            self.mBMI = Decimal(raw_value * 0.1).quantize(Decimal('1.000'), rounding=ROUND_HALF_UP)
            offset += 2

            raw_value = int.from_bytes(data[offset:offset + 2], byteorder='little')
            self.mHeight = Decimal(raw_value * height_measurement_resolution).quantize(Decimal('1.0'), rounding=ROUND_HALF_UP)
            offset += 2

        if Flag.BodyFatPercentagePresent in flags:
            raw_value = int.from_bytes(data[offset:offset + 2], byteorder='little')
            self.mBodyFatPercentage = Decimal(raw_value * 0.1 * 0.01).quantize(Decimal('1.000'), rounding=ROUND_HALF_UP)
            offset += 2

        if Flag.BasalMetabolismPresent in flags:
            self.mBasalMetabolism = Decimal(int.from_bytes(data[offset:offset + 2], byteorder='little'))
            offset += 2

        if Flag.MusclePercentagePresent in flags:
            raw_value = int.from_bytes(data[offset:offset + 2], byteorder='little')
            self.mMusclePercentage = Decimal(raw_value * 0.1 * 0.01).quantize(Decimal('1.000'), rounding=ROUND_HALF_UP)
            offset += 2

        if Flag.MuscleMassPresent in flags:
            raw_value = int.from_bytes(data[offset:offset + 2], byteorder='little')
            self.mMuscleMass = Decimal(raw_value * weight_measurement_resolution).quantize(Decimal('1.000'), rounding=ROUND_HALF_UP)
            offset += 2

        if Flag.FatFreeMassPresent in flags:
            raw_value = int.from_bytes(data[offset:offset + 2], byteorder='little')
            self.mFatFreeMass = Decimal(raw_value * weight_measurement_resolution).quantize(Decimal('1.000'), rounding=ROUND_HALF_UP)
            offset += 2

        if Flag.SoftLeanMassPresent in flags:
            raw_value = int.from_bytes(data[offset:offset + 2], byteorder='little')
            self.mSoftLeanMass = Decimal(raw_value * weight_measurement_resolution).quantize(Decimal('1.000'), rounding=ROUND_HALF_UP)
            offset += 2

        if Flag.BodyWaterMassPresent in flags:
            raw_value = int.from_bytes(data[offset:offset + 2], byteorder='little')
            self.mBodyWaterMass = Decimal(raw_value * weight_measurement_resolution).quantize(Decimal('1.000'), rounding=ROUND_HALF_UP)
            offset += 2

        if Flag.ImpedancePresent in flags:
            raw_value = int.from_bytes(data[offset:offset + 2], byteorder='little')
            self.mImpedance = Decimal(raw_value * 0.1).quantize(Decimal('1.000'), rounding=ROUND_HALF_UP)
            offset += 2

        if Flag.SkeletalMusclePercentagePresent in flags:
            raw_value = int.from_bytes(data[offset:offset + 2], byteorder='little')
            self.mSkeletalMusclePercentage = Decimal(raw_value * 0.1 * 0.01).quantize(Decimal('1.000'), rounding=ROUND_HALF_UP)
            offset += 2

        if Flag.VisceralFatLevelPresent in flags:
            raw_value = data[offset]
            self.mVisceralFatLevel = Decimal(raw_value * 0.5).quantize(Decimal('1.000'), rounding=ROUND_HALF_UP)
            offset += 1

        if Flag.BodyAgePresent in flags:
            self.mBodyAge = Decimal(data[offset])
            offset += 1

        if Flag.BodyFatPercentageStageEvaluationPresent in flags:
            self.mBodyFatPercentageStageEvaluation = Decimal(data[offset])
            offset += 1

        if Flag.SkeletalMusclePercentageStageEvaluationPresent in flags:
            self.mSkeletalMusclePercentageStageEvaluation = Decimal(data[offset])
            offset += 1

        if Flag.VisceralFatLevelStageEvaluationPresent in flags:
            self.mVisceralFatLevelStageEvaluation = Decimal(data[offset])
            offset += 1

    def _parse_timestamp(self, data: bytes) -> int:
        year = int.from_bytes(data[0:2], byteorder='little')
        month = data[2]
        day = data[3]
        hour = data[4]
        minute = data[5]
        second = data[6]
        dt = f"{year:04}-{month:02}-{day:02} {hour:02}:{minute:02}:{second:02}"
        struct_time = time.strptime(dt, "%Y-%m-%d %H:%M:%S")
        return calendar.timegm(struct_time)
        
        
    def __str__(self):
        return (f"OmronMeasurementWS(mWeightUnit='{self.mWeightUnit}', mHeightUnit='{self.mHeightUnit}', "
                f"mSequenceNumber={self.mSequenceNumber}, mWeight={self.mWeight}, mTimeStamp='{self.mTimeStamp}', "
                f"mUserID={self.mUserID}, mBMI={self.mBMI}, mHeight={self.mHeight}, mBodyFatPercentage={self.mBodyFatPercentage}, "
                f"mBasalMetabolism={self.mBasalMetabolism}, mMusclePercentage={self.mMusclePercentage}, mMuscleMass={self.mMuscleMass}, "
                f"mFatFreeMass={self.mFatFreeMass}, mSoftLeanMass={self.mSoftLeanMass}, mBodyWaterMass={self.mBodyWaterMass}, "
                f"mImpedance={self.mImpedance}, mSkeletalMusclePercentage={self.mSkeletalMusclePercentage}, mVisceralFatLevel={self.mVisceralFatLevel}, "
                f"mBodyAge={self.mBodyAge}, mBodyFatPercentageStageEvaluation={self.mBodyFatPercentageStageEvaluation}, "
                f"mSkeletalMusclePercentageStageEvaluation={self.mSkeletalMusclePercentageStageEvaluation}, "
                f"mVisceralFatLevelStageEvaluation={self.mVisceralFatLevelStageEvaluation})")

class Flag(IntFlag):
    ImperialUnit = 1
    SequenceNumberPresent = 1 << 1
    WeightPresent = 1 << 2
    TimeStampPresent = 1 << 3
    UserIDPresent = 1 << 4
    BMIAndHeightPresent = 1 << 5
    BodyFatPercentagePresent = 1 << 6
    BasalMetabolismPresent = 1 << 7
    MusclePercentagePresent = 1 << 8
    MuscleMassPresent = 1 << 9
    FatFreeMassPresent = 1 << 10
    SoftLeanMassPresent = 1 << 11
    BodyWaterMassPresent = 1 << 12
    ImpedancePresent = 1 << 13
    SkeletalMusclePercentagePresent = 1 << 14
    VisceralFatLevelPresent = 1 << 15
    BodyAgePresent = 1 << 16
    BodyFatPercentageStageEvaluationPresent = 1 << 17
    SkeletalMusclePercentageStageEvaluationPresent = 1 << 18
    VisceralFatLevelStageEvaluationPresent = 1 << 19
    MultiplePacketMeasurement = 1 << 20

    @staticmethod
    def parse(bits: int) -> List['Flag']:
        return [flag for flag in Flag if flag & bits]
