import gym
from gym import error, spaces, utils
from gym.utils import seeding

import pandas as pd
import numpy as np

from model import *

'''
In this version:
1. The time step is fixed at 1 hour
2. Vehicle-to-grid interaction is not supported
'''
class BEVCommunity(gym.Env):
    """ BEVPro is a custom Gym Environment to simulate a community equiped with on-site renewables, electric vehicles, and smart grid
    ------------------------------------------------------------------------------------------------------
    Args:
        - stepLenth: length of time step, unit: s
        - building_list: a list of buildings, each element in the list is a tuple of (buildingLoad.csv, number of buildings)
            example: [('inputs/building1.csv', 10), ('inputs/building2.csv', 10), ('inputs/building3.csv', 10)]
        - re_list: a list of on-site renewable sources, each element in the list is a tuple of (reGeneration.csv, number of sources)
            example: [('inputs/renewable1.csv', 10), ('inputs/renewable2.csv', 10), ('inputs/renewable3.csv', 10)]
        - vehicle_list: a list of electric vehicles, 
            first element is parkSchedule.csv, 
            the remaining elements in the list are tuples of 
                (vehicleParameter.csv, number of vehicles)
            example: ['inputs/vehicle_atHomeSchd.csv', ('inputs/vehicle1.csv', 10), ('inputs/vehicle2.csv', 10), ('inputs/vehicle3.csv', 10)]
        - battery_info: an onsite battery for enhancing energy flexibility. In this version, the distributed batteries are simplified as one large battery
    ------------------------------------------------------------------------------------------------------
    States:
        - buildingLoad: total building load of the community, [kW]
        - reGeneration: total on-site renewable generation, [kW]
        - battery_left: total electricity stored in the onsite battery, [kWh]
        - battery_spare: rest battery space for storing electricity, [kWh] 
        - vehicle_park: binary variable, whether the vechile is parked at home or not
        - vehicle_max_dist: predicted maximum travel distance of today, dist_mu_wd+5*dist_sigma_wd [km]
        - vehicle_SOC: the state of charge of vehicle battery
    ------------------------------------------------------------------------------------------------------
    Actions:
        - vehicle_charge: array, each element is charge/discharge rate of each vehicle,
            positive means charging vehicles, negative means dischargingg to grid/buildings, [kW]
    """

    def __init__(self, building_list, re_list, vehicle_list, battery_info, powerplant_num):
        '''
        In this version: 
            -- The step length is fixed at 1 hour
            
        '''
        super().__init__()
        self.episode_idx = 0
        self.time_step_idx = 0

        self.stepLenth =3600          # To be revised when the step length is not 1 hour
        self.simulationYear = 2019    # Fixed in this version
        start_time = datetime(year = self.simulationYear, month = 1, day =1)
        self.n_steps = 8760*3600//self.stepLenth   # Simulate a whole year
        freq = '{}H'.format(self.stepLenth/3600)
        self.timeIndex = pd.date_range(start_time, periods=self.n_steps, freq=freq)
        
        # power plant quantity for charging vehicles
        self.plantNum = powerplant_num

        # Calculate the load for each time step
        self.buildingLoad = self._calculateBuildingLoad(building_list, self.stepLenth, self.simulationYear)
        self.reGeneration = self._calculateReGeneration(re_list, self.stepLenth, self.simulationYear)

        # Initialize the onsite battery
        self.batteryOnsite = BatteryOnsite(battery_info, self.stepLenth/3600) 

        # Initialize the vehicles
        self.vehicles = []
        self.vehicle_schl_file = vehicle_list[0]
        for vehicle_tuple in vehicle_list[1:]:
            for _ in range(vehicle_tuple[1]):
                vehicle = Vehicle(vehicle_tuple[0], self.vehicle_schl_file, self.stepLenth)
                self.vehicles.append(vehicle)

        # define the state and action space
        vehicle_n = len(self.vehicles)           # Only control the vehicles
        self.action_names = ['vehicle_{}'.format(vehicle_i) for vehicle_i in range(vehicle_n)]
        self.actions_low = np.array([-100 for _ in range(vehicle_n)])    # Maximum discharging power -100 kW
        self.actions_high = np.array([100 for _ in range(vehicle_n)])    # Maximum charging power 100 kW
        self.action_space = spaces.Box(low=self.actions_low,
                                       high=self.actions_high,
                                       dtype=np.float32)  

        self.obs_names = ['buildingLoad', 'reGeneration', 'battery_left','battery_spare'] + \
            ['vehicle_park_{}'.format(vehicle_i) for vehicle_i in range(vehicle_n)] + \
            ['vehicle_max_dist_{}'.format(vehicle_i) for vehicle_i in range(vehicle_n)] + \
            ['vehicle_SOC_{}'.format(vehicle_i) for vehicle_i in range(vehicle_n)] #+ \
    
        self.obs_low  = np.array([0, 0, 0, 0] + [0 for _ in range(vehicle_n)] + \
            [0 for _ in range(vehicle_n)] + [0 for _ in range(vehicle_n)]) #+ \
            
        self.obs_high = np.array([10000, 10000, 10000, 10000] + [1 for _ in range(vehicle_n)] + \
            [1000 for _ in range(vehicle_n)] + [1000 for _ in range(vehicle_n)]) #+ \

        self.observation_space = spaces.Box(low=self.obs_low, 
                                            high=self.obs_high, 
                                            dtype=np.float32)

    def reset(self):
        self.episode_idx += 1
        self.time_step_idx = 0
        load = self._getLoad(self.time_step_idx)
        batteryVol = [0]
        batterySpare = [self.batteryOnsite.capacityMax]
        vehicles_park = []
        vehicles_max_dist = []
        vehicles_SOC = []
        
        for vehicle in self.vehicles:
            vehicle_park, vehicle_max_dist, _ = self._getVehicleStateStatic(vehicle)
            vehicles_park.append(vehicle_park)
            vehicles_max_dist.append(vehicle_max_dist)           
            vehicles_SOC.append(vehicle.batterySOC)
        obs = load + batteryVol + batterySpare + vehicles_park + vehicles_max_dist + vehicles_SOC

        return obs

    def step(self, actions):
        load = self._getLoad(self.time_step_idx)
        vehicles_park = []
        vehicles_max_dist = []
        vehicles_SOC = []
        usedPlants = 0
        totalVehicleCharge = 0
        totalVehicletoGrid = 0
        
        for action, vehicle in zip(actions, self.vehicles):
            vehicle_park, vehicle_max_dist, cruiseBackHour = self._getVehicleStateStatic(vehicle)
            if action > 0:   # Charge the vehicle battery
                if usedPlants < self.plantNum:
                    realChargeRate = vehicle.vehicleCharge(action)
                    totalVehicleCharge += realChargeRate
                    if realChargeRate != 0:
                        usedPlants += 1
                else:
                    realChargeRate = 0
            else: # discharge the vehicle battery for powering the grid
                realDischargePower = vehicle.eleToGrid(-action)
                totalVehicletoGrid += realDischargePower
            # Vehicle-stored electricity is reduced at the hour when the vehicle is back 
            if cruiseBackHour:
                workingDay = self.timeIndex[self.time_step_idx].weekday()
                vehicle.cruise(workingDay)

            vehicles_park.append(vehicle_park)
            vehicles_max_dist.append(vehicle_max_dist)
            vehicles_SOC.append(vehicle.batterySOC)


        renewableSurlpus =  max(0.95*load[1] - load[0] - totalVehicleCharge, 0)
        demandShoratge = max(load[0] - 0.95*load[1] + totalVehicleCharge, 0)
        # Charge/discharge the onsite battery
        if renewableSurlpus >= 0: 
            power_batteryCharge, ele_batteryCharge = self.batteryOnsite.batteryCharge(renewableSurlpus)
            power_batteryDischarge = 0
            ele_batteryDischarge = 0
        if demandShoratge > 0: 
            power_batteryDischarge, ele_batteryDischarge = self.batteryOnsite.batteryDischarge(demandShoratge)
            power_batteryCharge = 0
            ele_batteryCharge = 0

        batteryVol = self.batteryOnsite.batteryVol
        batterySpare = self.batteryOnsite.capacityMax - self.batteryOnsite.batteryVol
        
        totalGridLoad = load[0] - 0.95*load[1] + power_batteryCharge - power_batteryDischarge + totalVehicleCharge - totalVehicletoGrid

        reward = totalGridLoad
        done = self.time_step_idx == len(self.timeIndex)-1
        comments = (power_batteryCharge, power_batteryDischarge, totalVehicleCharge, totalVehicletoGrid)

        self.time_step_idx += 1
        if done:
            load = self._getLoad(self.time_step_idx-1)
        else:
            load = self._getLoad(self.time_step_idx)
        obs = load + [batteryVol] + [batterySpare] + vehicles_park + vehicles_max_dist + vehicles_SOC
        return obs, reward, done, comments

    def _calculateBuildingLoad(self, building_list, stepLenth, simulationYear):
        '''Calculate the total building load from the building list
        '''
        
        buildings = pd.DataFrame()
        for building_tuple in building_list:
            building_csv = building_tuple[0]
            building_numbers = building_tuple[1]
            building_obj = Building(building_csv, stepLenth, simulationYear)
            building = building_obj.getLoadFullYear()*building_numbers
            buildings = pd.concat([buildings,building], axis=1)
        totalLoad = buildings.sum(axis=1).values
        return totalLoad

    def _calculateReGeneration(self, re_list, stepLenth, simulationYear):
        '''Calculate the total renewable generation from the renewable list
        '''
        res = pd.DataFrame()
        for re_tuple in re_list:
            re_csv = re_tuple[0]
            re_numbers = re_tuple[1]
            re_obj = RE(re_csv, stepLenth, simulationYear)
            re = re_obj.getPowerFullYear()*re_numbers
            res = pd.concat([res,re], axis=1)
        totalGeneration = res.sum(axis=1).values
        return totalGeneration
    
    def _getLoad(self, time_step_idx):
        '''Get the building load and renewable generation for the given time step
        Return a list
        '''
        load = [self.buildingLoad[time_step_idx], self.reGeneration[time_step_idx]]
        return load
    
    def _getVehicleStateStatic(self, vehicle):
        '''Get the park state and maximum traveling distance of the vehicle
        Return: park state (1 for at home, 0 for not at home)
                predicted maximum travel distance
                cruiseBackHour: Boolean, Whether it is the hour vehicle returns to home, the vehicle battery is discharged at this hour
        '''
        weekday = self.timeIndex[self.time_step_idx].weekday()
        hour = self.timeIndex[self.time_step_idx].hour
        if weekday:
            vehicle_park = vehicle.parkSchd_wd[hour]
            cruiseHour = vehicle.parkSchd_wd.index[vehicle.parkSchd_wd==0].max()+1
            vehicle_max_dist = vehicle.dist_mu_wd+5*vehicle.dist_sigma_wd
        else:
            vehicle_park = vehicle.parkSchd_nwd[hour]
            cruiseHour = vehicle.parkSchd_wd.index[vehicle.parkSchd_wd==0].max()+1
            vehicle_max_dist = vehicle.dist_mu_nwd+5*vehicle.dist_sigma_nwd
        cruiseBackHour = hour == cruiseHour
        return vehicle_park, vehicle_max_dist, cruiseBackHour
