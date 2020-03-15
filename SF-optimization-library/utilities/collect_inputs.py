from navigate_data import *
##### The next few function all take a folder as input and extract input info
filepath_network = "./fixed_data/network.csv"


#Load weights from working directory
def load_weights():
	dict_name = "scoringWeights.csv"
	dic = {}
	with open(dict_name) as csvfile:
		df = pd.read_csv(csvfile)
		kpi_names = list(df.columns)
		for name in kpi_names:
			dic[name] = list(df[name])[0]
	return dic

def singleKPI_weights(KPI):
	weights = load_weights()
	for w in weights:
		if w != KPI:
			weights[w] = 0.0
		else:
			weights[w] = 1.0
	return weights


#Loads the dicationnary of {KPI: mean, std} from working directory
def load_standards(file):
	dict_name = file
	params = {}
	with open(dict_name) as csvfile:
		reader = csv.reader(csvfile)
		for row in reader:
			params[row[0]] = (float(row[1]), float(row[2]))
	return params


#Reads transit fare inputs
def getTransitFareInputs(tpe_dir):
	path = os.path.join(getInputsDir(tpe_dir), "MassTransitFares.csv")	
	dic = {}
	with open(path) as csvfile:
		df = pd.read_csv(csvfile, index_col=2)

		if df.empty:
			return dic

		dic["AdultFare"] = df["amount"][0]
		dic["ChildrenFare"] = df["amount"][1]
	
	return dic

#
def load_network():
    with open(filepath_network, "rt") as csvfile:
        datareader = csv.reader(csvfile)
        yield next(datareader)
        for row in datareader:
        	if row[0].isdigit():
        		yield row
        return


#Reads road pricing information inputs
def getRoadPricing(tpe_dir):
	path = os.path.join(getInputsDir(tpe_dir), "RoadPricing.csv")
	dic = {}

	if not os.path.exists(path):
		return dic

	with open(path) as csvfile:
		reader = csv.reader(csvfile)
		for row in reader:
			if row[0][0].isdigit():
				dic[row[0]] = float(row[1])

	return dic

def reconstructRoadPrincingArea(tpe_dir):
	x = 0
	y = 0
	p = 0

	i = 0

	dic = getRoadPricing(tpe_dir)

	for row in load_network():
		linkId = row[0]

		if linkId in dic:
			linkLength,fromLocationX,fromLocationY,toLocationX,toLocationY = float(row[1]),float(row[-4]),float(row[-3]),float(row[-2]),float(row[-1])

			if dic[linkId] != 3.0:
				i += 1
				p += dic[linkId] * 1600 / linkLength

				if fromLocationX >= x and toLocationX >= x:
					x = max(fromLocationX, toLocationX)

				if fromLocationY >= y and toLocationY >= y:
					y = max(fromLocationY, toLocationY)

	if i==0:
		print(tpe_dir)
		return {"x":None, "y":None, "p":None}

	p /= i
	p = round(p, 2)
	x = int(x)
	y = int(y)

	return {"x":x, "y":y, "p":p}


def collect_circle_fares_parameters(tpe_dir):
	file = open(tpe_dir + "/circle_params.txt",'r')
	params = file.readline().split(',')

	dic = {}
	for p in params:
		k,v = p.split(":")
		dic[k] = round(float(v), 2)

	return dic

