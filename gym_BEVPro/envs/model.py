import pandas as pd
import numpy as np
from datetime import datetime


class dataFromCSV():

    def __init__(self, csv_file, stepLenth, simulationYear):
        '''Input csv file needs to be hourly load 
        '''
        self.csv_file = csv_file
        self.load = pd.read_csv(self.csv_file, index_col=0)
        ## Check the input load
        assert self.load.shape[0] == 8760, "Input building load file needs to be hourly."
        if self.load.shape[1] > 1:
            print('Input building load file have more than 1 column, only the first column will be used.')
        self.stepLenth = stepLenth  #unit: s
        self.setTimeStep(simulationYear)

    def setTimeStep(self, simulationYear):
        start_time = datetime(year = simulationYear, month = 1, day =1)
        self.load.index = pd.date_range(start_time, periods = self.load.shape[0], freq = 'H')
        self.load = self.load.resample('{}T'.format(self.stepLenth/60)).interpolate()


class Building(dataFromCSV):

    def __init__(self, csv_file, stepLenth, simulationYear):
        super().__init__(csv_file, stepLenth, simulationYear)

    def getLoad(self, timeStep):
        '''Time step start with 0
        '''
        return self.load.iloc[timeStep, 0]
    
    def getLoadFullYear(self):
        return self.load


class RE(dataFromCSV):

    def __init__(self, csv_file, stepLenth, simulationYear):
        super().__init__(csv_file, stepLenth, simulationYear)

    def getPower(self, timeStep):
        '''Time step start with 0
        '''
        return self.load.iloc[timeStep, 0]

    def getPowerFullYear(self):
        return self.load

class Vehicle:

    def __init__(self, csv_file, schd_file, stepLenth):
        '''Class of vehicle, equiped with a battery
        Consume electricity for daily communiting
        Can be charged through power plants connected to the grid
        Can be discharged to power the grid, but not considered in this version
        ------------------------------------
        Args
            -- csv_file, key parameters of the vehicle
            -- schd_file, parking schedule of the vehicle
            -- stepLenth, lenth of each time step, unit: h
        ------------------------------------
        State
            -- batterySOC: current state of charge of the vehicle battery.
        '''
        self.vehicle_info = pd.read_csv(csv_file)
        self.vehicle_schd = pd.read_csv(schd_file)
        self.cruiseEff = float(self.vehicle_info.loc[0,'cruiseEff'])  # unit: kWh/km
        self.dist_mu_wd = float(self.vehicle_info.loc[0,'dist_mean_wd'])
        self.dist_sigma_wd = float(self.vehicle_info.loc[0,'dist_std_wd'])
        self.dist_mu_nwd = float(self.vehicle_info.loc[0,'dist_mean_nwd'])
        self.dist_sigma_nwd = float(self.vehicle_info.loc[0,'dist_std_nwd'])
        self.maxChargingCapacity = float(self.vehicle_info.loc[0,'maxChargingCapacity']) # unit: kW
        self.maxDischargingCapacity = float(self.vehicle_info.loc[0,'maxDischargingCapacity']) # unit: kW
        self.charEff = float(self.vehicle_info.loc[0,'charEff'])
        self.discEff = float(self.vehicle_info.loc[0,'discEff']) 
        self.batteryCapacity = float(self.vehicle_info.loc[0,'batteryCapacity']) # unit: kWh
        self.parkSchd_wd = self.vehicle_schd[self.vehicle_info.loc[0,'parkSchd_wd']]
        self.parkSchd_nwd = self.vehicle_schd[self.vehicle_info.loc[0,'parkSchd_nwd']]
        self.stepLenth = stepLenth/3600                # unit: h
        # Initialize electricity storage in the vehicle battery
        self.batteryVol = self.batteryCapacity/2    # unit: kWh
        self.batterySOC = self.batteryVol/self.batteryCapacity
    
    def vehicleCharge(self, chargeRate):
        '''
        ------------------------------------
        Args
            -- chargeRate, control signal for charging vehicles, unit: kW
        ------------------------------------
        Output
            -- realChargeRate, real charge rate, unit: kW
        '''
        assert chargeRate>=0, "Charge rate must be positive value"
        realChargeRate = min(min(chargeRate, self.maxChargingCapacity), (self.batteryCapacity-self.batteryVol)/self.stepLenth/self.charEff)
        
        chargeElectricity = realChargeRate * self.stepLenth 
        self.batteryVol += chargeElectricity * self.charEff
        self.batterySOC += chargeElectricity * self.charEff/self.batteryCapacity
        return realChargeRate
    
    def eleToGrid(self, dischargeRate):
        '''
        ------------------------------------
        Args
            -- dischargeRate, control signal for discharging vehicles, unit: kW
        ------------------------------------
        Output
            -- realDischargeRate, real discharge power, unit: kW
        '''
        assert dischargeRate>=0, "Discharge rate must be positive value"
        realDischargeRate = min(min(dischargeRate, self.maxDischargingCapacity), self.batteryVol/self.stepLenth*self.discEff)
        dischargeElectricity = realDischargeRate * self.stepLenth
        self.batteryVol -= dischargeElectricity / self.discEff
        self.batterySOC -= dischargeElectricity / self.discEff/self.batteryCapacity
        return realDischargeRate

    def cruise(self, workingDay):
        eleConsumption = self._getEleConsumption(workingDay)
        self.batteryVol -= eleConsumption
        self.batterySOC -= eleConsumption/self.batteryCapacity

    def _getEleConsumption(self, workingDay):
        distance = self._getDistance(workingDay)
        eleConsumption = self.cruiseEff*distance         # unit: kWh
        return eleConsumption
    
    def _getDistance(self, workingDay):
        if workingDay:
            self.distance = np.random.normal(self.dist_mu_wd, self.dist_sigma_wd, 1)[0]
        else:
            self.distance = np.random.normal(self.dist_mu_nwd, self.dist_sigma_nwd, 1)[0]
        return self.distance

    def getParkSchd(self, workingDay):
        self.parkSchd = self.parkSchd_wd if workingDay else self.parkSchd_nwd
        return self.parkSchd

class BatteryOnsite:

    def __init__(self, csv_file, stepLenth):
        '''Class of onsite battery
        Can store electricity
        ------------------------------------
        Args
            -- csv_file, key parameters of the onsite battery
            -- stepLenth, lenth of each time step, unit: h
        ------------------------------------
        '''
        
        self.battery_info = pd.read_csv(csv_file)
        self.charEff = float(self.battery_info.loc[0,'charEff'])  
        self.charCap = float(self.battery_info.loc[0,'charCap'])  # unit: kW
        self.discEff = float(self.battery_info.loc[0,'discEff'])  
        self.discCap = float(self.battery_info.loc[0,'discCap'])  # unit: kW
        self.capacityMax = float(self.battery_info.loc[0,'batteryCapacity'])  # unit: kWh
        self.stepLenth = stepLenth           # unit: h
        # Initialize electricity storage in the battery
        self.batteryVol = 0
                 

    def batteryCharge(self, chargeRate):
        '''
        ------------------------------------
        Args
            -- chargeRate, unit: kW
        ------------------------------------
        Output
            -- realChargeRate, unit: kW
            -- chargeElectricity, unit: kWh
        '''
        assert chargeRate>=0, "Charge power must be a positive value"
        
        realChargeRate = min(min(chargeRate, self.charCap), (self.capacityMax-self.batteryVol)/self.stepLenth/self.charEff)
        
        chargeElectricity = realChargeRate * self.stepLenth 
        self.batteryVol += chargeElectricity * self.charEff
        return realChargeRate, chargeElectricity

    def batteryDischarge(self, dischargeRate):
        '''
        ------------------------------------
        Args
            -- dischargeRate, unit: kW
        ------------------------------------
        Output
            -- realdischargeRate, unit: kW
            -- dischargeElectricity, unit: kWh
        '''
        assert dischargeRate>=0, "Discharge power must be a postitive value"
        realDischargeRate = min(min(dischargeRate, self.discCap), self.batteryVol/self.stepLenth*self.discEff)
        dischargeElectricity = realDischargeRate * self.stepLenth
        self.batteryVol -= dischargeElectricity / self.discEff
        return realDischargeRate, dischargeElectricity








