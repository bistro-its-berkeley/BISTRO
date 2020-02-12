import csv
import sys

TIME_RANGES = {'morning_peak': range(7, 10), "midday": range(10, 17), "evening peak": range(17, 20)}

def load_network(filepath):
	"""
	Genertator for reading the csv file
	"""
	with open(filepath, "rt") as csvfile:
		datareader = csv.reader(csvfile)
		yield next(datareader)
		for row in datareader:
			yield row
		return

def getdata(filepath,x,y):
	"""
	x: west, string
	y: south, string
	p: price mile/$
	"""
	for row in load_network(filepath):
		if row[0].isdigit():
			linkId,linkLength,fromLocationX,fromLocationY,toLocationX,toLocationY = row[0],row[1],row[-4],row[-3],row[-2],row[-1]
			#if row[0] < '10050':
			if toLocationX < x and toLocationY < y:
				yield row


def get_output_attr(filepath,x,y,p,time_range):
	for row in getdata(filepath,x,y): #'690000','4836000','[:]'
		linkId,linkLength,fromLocationX,fromLocationY,toLocationX,toLocationY = row[0],row[1],row[-4],row[-3],row[-2],row[-1]
		price = 3
		if fromLocationX < x and fromLocationY < y:
			price = str(float(linkLength)*float(p))
		yield [linkId,price,time_range]

def write_to_road_price(filepath,x,y,p,time_range,output):
	with open(output,'a') as f:
		writer = csv.writer(f)
		writer.writerow(['linkId','toll','timeRange'])
		for row in get_output_attr(filepath,x,y,p,time_range):
			writer.writerow(row)


if __name__ == '__main__':
	write_to_road_price('/Users/ruubyan/Desktop/UCB/BISTRO/BeamCompetitions/output/sf_light/sf_light_bau/network.csv',
		'551200','4175000','0.4','[:]','/Users/ruubyan/Desktop/UCB/BISTRO/BeamCompetitions/submission-inputs/RoadPricing.csv')









