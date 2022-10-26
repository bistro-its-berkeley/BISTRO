import pandas as pd
import csv
import sys
import os
import yaml
import logging
import shapely 
from shapely.geometry import LineString, Point

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
hyperopt_path = os.path.abspath(os.path.dirname(__file__));
sys.path.append(os.path.abspath("../"))
sys.path.append(os.path.abspath("../../"))
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
# try:
#     from optimization_utils import *
# except:
#     from utilities.optimization_utils import *

# PUT IN SEARCH OBJECT:
# CONFIG = {}
# with open(os.path.join(hyperopt_path,"settings.yaml")) as stream:
#     CONFIG = yaml.safe_load(stream)

#from shapely.geometry import Point
#from shapely.geometry.polygon import Polygon

mode_incentive_columns = ['mode', 'age', 'income', 'amount']
mass_fare_columns = ['agencyId', 'routeId', 'age', 'amount']
road_pricing_columns = ['linkId','toll','timeRange']


# Circle fare limits
# centerx = None
# centery = None
# cradius = None
# ctoll = None
# centerx=[ None for _ in range(5) ]
# centery=[ None for _ in range(5) ]
# ctoll=[ None for _ in range(5) ]
# cradius=[ None for _ in range(5) ]

# INITIALIZE PARAM LISTS
num = 20
centerx = [None for _ in range(num)]
centery = [None for _ in range(num)]
ctoll = [None for _ in range(num)]
cradius = [None for _ in range(num)]

incomeThresh = [None for _ in range(num)]
modes = [None for _ in range(num)]
subsidies = [None for _ in range(num)]


def convert_to_input(sample, input_dir, network_path):
    print(network_path)

    mode_incentive = []
    mass_fare = []
    road_pricing = {}

    print(sample)
    for key in sample:
        value = sample[key]
        # logger.info("key, value : {}, {}".format(key,value))
        # logger.info("value type is "+str(type(value)))
        if key.startswith('c'):
            ## process cordons:
            link_price = processC(key, value, network_path)
            for item in link_price:
                ## TODO: speed up - simply check for duplicates and then add?
                if item[0] not in road_pricing:
                    road_pricing[item[0]]=item[1:]
                else:
                    # IF LINK IS ALREADY PART OF A CORDON
                    # both tolls apply:
                    #road_pricing[item[0]][0]=float(road_pricing[item[0]][0])+float(item[1])
                    # min toll applies:
                    road_pricing[item[0]][0] = min(float(road_pricing[item[0]][0]), float(item[1]))
            #logger.info("processC end\n")
        elif key.startswith('subsidyModes'):
        ## process subsidies
            subs = processSubsidy(value,key[-1],sample)
            # print(subs)
            for s in subs:
                mode_incentive.append(s)


    # convert road pricing dict to list:
    # TODO: make it a list from the beginning..
    road_pricing_list=[]
    for item in road_pricing.items() :
        road_pricing_list.append([item[0]] + item[1])

    mode_incentive_d = pd.DataFrame(mode_incentive, columns=mode_incentive_columns)
    mass_fare_d = pd.DataFrame(mass_fare, columns=mass_fare_columns)
    road_pricing_d = pd.DataFrame(road_pricing_list, columns=road_pricing_columns)

    # print(mode_incentive_d.head())
    # print(mass_fare_d.head())
    # print(road_pricing_d.head(30))

    mode_incentive_d.to_csv(input_dir + '/ModeIncentives.csv', sep=',', index=False)
    mass_fare_d.to_csv(input_dir + '/MassTransitFares.csv', sep=',', index=False)
    road_pricing_d.to_csv(input_dir + '/RoadPricing.csv', sep=',', index=False)

def processSubsidy(subMode, subNum, this_sample):
    ## TODO: generalize to allow age groups:
    mode_dict = {'RIDE_HAIL_POOLED':'ride_hail_pooled','WALK_TRANSIT':'walk_transit','BIKE_TRANSIT':'bike_transit','RIDE_HAIL_TRANIST':'ride_hail_transit','DRIVE_TRANSIT':'drive_transit'}
    ageGroup = '[0:120]'

    subsidy_list = []
    found = True
    threshNum = 0
    lb=0
    while found:
        if "incomeThresh{}".format(threshNum) in this_sample.keys():
            incomeGroup = '[{}:{}]'.format(lb,this_sample["incomeThresh{}".format(threshNum)])
            lb = this_sample["incomeThresh{}".format(threshNum)]+1
            for m in subMode:
                if float(this_sample["subsidyVal_mode{}_level{}".format(subNum,threshNum)])>0:
                    subsidy_list.append([mode_dict[m], ageGroup, incomeGroup,float(this_sample["subsidyVal_mode{}_level{}".format(subNum,threshNum)])])
            threshNum += 1
        else:
            found = False
    return subsidy_list


def processC(key, value, network_path):
    logger.info("processC start {}: {}".format(key,str(value)))
    global centerx, centery, ctoll, cradius
    if key.startswith('centerx'):
        centerx[int(key[-1])] = value # centerx1, centerx2
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
        print(key[-1]+"th Parameters for this run: \nCenterX"+key[-1]+": " + str(centerx[int(key[-1])]) + "\nCenterY"+key[-1]+": " + str(centery[int(key[-1])]) + "\nPrice"+key[-1]+": " + str(ctoll[int(key[-1])]) + "\nRadius"+key[-1]+": " + str(cradius[int(key[-1])]))
        logger.info("get_circle_links should start\n")
        links = get_circle_links(centerx[int(key[-1])], centery[int(key[-1])], cradius[int(key[-1])], ctoll[int(key[-1])], network_path,int(key[-1]))
        logger.info("get_circle_links ends\n")
        return links


def load_network(filepath_network):
    with open(filepath_network, "rt") as csvfile:
        datareader = csv.reader(csvfile)
        yield next(datareader)
        for row in datareader:
            yield row
        return


def get_circle_links(x, y, r, p, filepath_network,number):
    timeRange = '[0:35]'

    #Save parameters
    file = open("circle_params.txt","a")
    print('writing to circle_params')
    file.write("x"+str(number)+":" + str(x) + ",y"+str(number)+":" + str(y) + ",r"+str(number)+":"+str(r) + ",p"+str(number)+":" + str(p)+",")
    file.close()
    logger.info("written circle params to file")

    changes = []
    for row in load_network(filepath_network):
        if row[0].isdigit():
            linkId,linkLength,fromLocationX,fromLocationY,toLocationX,toLocationY = row[1],row[2],row[-5],row[-4],row[-3],row[-2]
            fromLocationX = float(fromLocationX)
            toLocationX = float(toLocationX)
            fromLocationY = float(fromLocationY)
            toLocationY = float(toLocationY)
            dfrom = ((x - fromLocationX)**2 + (y - fromLocationY)**2)**0.5
            dto = ((x - toLocationX)**2 + (y - toLocationY)**2)**0.5
            # print('x {}, y {}; link from ({},{}) to ({},{}))  ; {} to {}; r {}'.format(x,y,fromLocationX,fromLocationY,toLocationX,toLocationY,dfrom, dto, r))
            if dfrom < r and dto < r: 
                price = str(float(linkLength)*float(p)/1609.344)
                changes.append([linkId,price,timeRange])
            elif dfrom < r or dto < r:
                int_x,int_y=get_intersection(x,y,r,fromLocationX,fromLocationY,toLocationX,toLocationY)
                if int_x != False:
                    if dfrom < r:
                        dist = ((int_x - fromLocationX)**2 + (int_y - fromLocationY)**2)**0.5
                    else: 
                        dist = ((int_x - toLocationX)**2 + (int_y - toLocationY)**2)**0.5
                    price = str(float(dist)*float(p)/1609.344)
                    changes.append([linkId,price,timeRange])
                else:
                    price = str(float(linkLength)*float(p)/1609.344)
                    changes.append([linkId,price,timeRange])
    return changes

def get_intersection(x,y,r,x1,y1,x2,y2):
    p = Point(x,y)
    c = p.buffer(r).boundary
    l = LineString([(x1,y1),(x2,y2)])
    if c.intersects(l):
        i = c.intersection(l)
        try: 
            return i[0].x,i[0].y
        except:
            return i.x,i.y
    else:
        return False, False
