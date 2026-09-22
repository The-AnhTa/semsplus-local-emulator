export type DeviceState = "RUNNING" | "STANDBY" | "STOPPING" | "OFFLINE" | "STARTING" | "FAULT" | "RAPID_SHUTDOWN";

export interface Station {
  id: string;
  name: string;
  capacityKw: number;
  address: string;
  email: string;
  status: DeviceState;
  todayGenerationKwh: number;
  cumulativeGenerationKwh: number;
  specificYieldKwhKwp: number;
  pvPowerKw: number;
  note: string;
}

export interface Device {
  id: string;
  name: string;
  serialNumber: string;
  stationId: string;
  stationName: string;
  status: DeviceState;
  deviceType: string;
  activePowerKw: number;
  dailyGenerationKwh: number;
  rapidShutdown: boolean;
}

export interface Telemetry {
  timestamp: string;
  activePowerKw: number;
  reactivePowerKvar: number;
  powerFactor: number;
  acFrequencyHz: number;
  dailyEnergyKwh: number;
  cumulativeEnergyKwh: number;
  pvPowerKw: number;
  phaseAVoltage: number;
  phaseBVoltage: number;
  phaseCVoltage: number;
  phaseACurrent: number;
  phaseBCurrent: number;
  phaseCCurrent: number;
  temperatureC: number;
}

export interface HistoryPoint {
  timestamp: string;
  activePowerKw: number;
  pvPowerKw: number;
}

export interface MpptPoint {
  voltage: number;
  current: number;
  powerKw: number;
}

export interface Alarm {
  id: number;
  alarmType: string;
  alarmName: string;
  deviceId: string;
  deviceName: string;
  stationName: string;
  status: "OCCURRING" | "RECOVERED";
  level: string;
  alarmTime: string;
  recoveredTime: string | null;
}

