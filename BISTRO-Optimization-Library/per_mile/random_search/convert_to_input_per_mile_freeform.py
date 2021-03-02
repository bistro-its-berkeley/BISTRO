import pandas as pd
import csv
import sys
import os
import yaml
import logging

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
hyperopt_path = os.path.abspath(os.path.dirname(__file__));
sys.path.append(os.path.abspath("../"))
sys.path.append(os.path.abspath("../../"))
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
try:
    from optimization_utils import *
except:
    from utilities.optimization_utils import *

CONFIG = {}
with open(os.path.join(hyperopt_path,"settings.yaml")) as stream:
    CONFIG = yaml.safe_load(stream)

#from shapely.geometry import Point
#from shapely.geometry.polygon import Polygon

vehicle_fleet_columns = ["agencyId", "routeId", "vehicleTypeId"]
frequency_adjustment_columns = ['route_id', 'start_time', 'end_time', 'headway_secs', 'exact_times']
mode_incentive_columns = ['mode', 'age', 'income', 'amount']
mass_fare_columns = ['agencyId', 'routeId', 'age', 'amount']
road_pricing_columns = ['linkId','toll','timeRange']


#Circle fare limits
# centerx = None
# centery = None
# cradius = None
# ctoll = None
# centerx=[ None for _ in range(5) ]
# centery=[ None for _ in range(5) ]
# ctoll=[ None for _ in range(5) ]
# cradius=[ None for _ in range(5) ]

centerx=[ None for _ in range(20) ]
centery=[ None for _ in range(20) ]
ctoll=[ None for _ in range(20) ]
cradius=[ None for _ in range(20) ]


def convert_to_input(sample, input_dir, network_path=CONFIG["NETWORK_PATH"]):
    # print(CONFIG["NETWORK_PATH"])
    vehicle_fleet = []
    frequency_adjustment = []
    mode_incentive = []
    mass_fare = []
    # [[linkId,price,timeRange],[]]
    road_pricing = {}
    for key in sample:
        value = sample[key]
        # print("key type is "+str(type(key)))
        # print("value type is "+str(type(value)))
        # logger.info("value type is "+str(type(value)))
        if key.startswith('c'):
            link_price=processC(key, value, network_path)
            for item in link_price:
                if item[0] not in road_pricing:
                    road_pricing[item[0]]=item[1:]
                else:
                    road_pricing[item[0]][0]=float(road_pricing[item[0]][0])+float(item[1])
            #logger.info("processC end\n")
        else:
            print("EROOR: UNKWOWN KEY; EXITING")
            exit(0);
    road_pricing_list=[]
    for item in road_pricing.items() :
        road_pricing_list.append([item[0]]+item[1])

    # road_pricing = []
    # for key in sample:
    #     value = sample[key]
    #     print("key type is "+str(type(key)))
    #     print("value type is "+str(type(value)))
    #     logger.info("value type is "+str(type(value)))
    
    #     if key.startswith('c'):
    #         road_pricing = road_pricing + processC(key, value, network_path)
    #         #logger.info("processC end\n")
    #     else:
    #         print("EROOR: UNKWOWN KEY; EXITING")
    #         exit(0);




    vehicle_fleet_d = pd.DataFrame(vehicle_fleet, columns=vehicle_fleet_columns)
    frequency_adjustment_d = pd.DataFrame(frequency_adjustment, columns=frequency_adjustment_columns)
    mode_incentive_d = pd.DataFrame(mode_incentive, columns=mode_incentive_columns)
    mass_fare_d = pd.DataFrame(mass_fare, columns=mass_fare_columns)
    road_pricing_d = pd.DataFrame(road_pricing_list, columns=road_pricing_columns)

    road_pricing_d.to_csv(input_dir + '/RoadPricing.csv', sep=',', index=False)
    vehicle_fleet_d.to_csv(input_dir+'/VehicleFleetMix.csv', sep=',', index=False)
    frequency_adjustment_d.to_csv(input_dir + '/FrequencyAdjustment.csv', sep=',', index=False)
    mode_incentive_d.to_csv(input_dir + '/ModeIncentives.csv', sep=',', index=False)
    mass_fare_d.to_csv(input_dir + '/MassTransitFares.csv', sep=',', index=False)
    

def processC(key, value, network_path):
    #logger.info("processC start "+str(value))
    global centerx, centery, ctoll, cradius
    if key.startswith('centerx'):
        centerx[int(key[-1])] = value
    if key.startswith('centery'):
        centery[int(key[-1])] = value
    if key.startswith('cradius'):
        cradius[int(key[-1])] = value
    if key.startswith('ctoll'):
        ctoll[int(key[-1])] = value

    if centerx[int(key[-1])] == None or centery[int(key[-1])] == None or ctoll[int(key[-1])] == None or cradius[int(key[-1])] == None:
        # logger.info(str(centerx)+" "+str(centerx)+" "+str(centerx)+" "+str(centerx))
        return []

    else:
        #print(key[-1]+"th Parameters for this run: \nCenterX"+key[-1]+": " + str(centerx[int(key[-1])]) + "\nCenterY"+key[-1]+": " + str(centery[int(key[-1])]) + "\nPrice"+key[-1]+": " + str(ctoll[int(key[-1])]) + "\nRadius"+key[-1]+": " + str(cradius[int(key[-1])]))
        #logger.info("get_circle_links should start\n")
        links = get_circle_links(centerx[int(key[-1])], centery[int(key[-1])], cradius[int(key[-1])], ctoll[int(key[-1])], network_path,int(key[-1]))
        #logger.info("get_circle_links ends\n")
        return links


def load_network(filepath_network):
    with open(filepath_network, "rt") as csvfile:
        datareader = csv.reader(csvfile)
        yield next(datareader)
        for row in datareader:
            yield row
        return


def get_circle_links(x, y, r, p, filepath_network,number):
    timeRange = '[:]'
    #logger.info("get_circle_links start\n")

    #Save parameters
    file = open("circle_params.txt","a")
    print('writing to circle_params')
    file.write("x"+str(number)+":" + str(x) + ",y"+str(number)+":" + str(y) + ",r"+str(number)+":"+str(r) + ",p"+str(number)+":" + str(p)+",")
    file.close()
    logger.info("written circle params to file")

    changes = []
    for row in load_network(filepath_network):
        if row[0].isdigit():
            linkId,linkLength,fromLocationX,fromLocationY,toLocationX,toLocationY = row[0],row[1],row[-4],row[-3],row[-2],row[-1]
            fromLocationX = float(fromLocationX)
            toLocationX = float(toLocationX)
            fromLocationY = float(fromLocationY)
            toLocationY = float(toLocationY)
            dfrom = ((x - fromLocationX)**2 + (y - fromLocationY)**2)**0.5
            dto = ((x - toLocationX)**2 + (y - toLocationY)**2)**0.5
            price = str(round(float(linkLength)*float(p)/1600, 2))

            
            if dfrom < r or dto < r: 
                changes.append([linkId,price,timeRange])

    return changes