from navigate_data import *
import xmltodict
import gzip

trans_dict = {

	'Iteration':'Iteration',

	'Accessibility: number of secondary locations accessible by car within 15 minutes':'driveSecondaryAccessibility',
	'Accessibility: number of secondary locations accessible by transit within 15 minutes':'transitSecondaryAccessibility',
	'Accessibility: number of work locations accessible by car within 15 minutes':'driveWorkAccessibility',
	'Accessibility: number of work locations accessible by transit within 15 minutes':'transitWorkAccessibility',

	'Congestion: average vehicle delay per passenger trip':'averageVehicleDelayPerPassengerTrip',
	'Congestion: total vehicle miles traveled':'motorizedVehicleMilesTraveled_total',
	'Equity: average travel cost burden -  secondary':'averageTravelCostBurden_Secondary',
	'Equity: average travel cost burden - work':'averageTravelCostBurden_Work',
	'Level of service: average bus crowding experienced':'busCrowding',
	'Level of service: costs and benefits':'costBenefitAnalysis',

	'Sustainability: Total grams GHGe Emissions':'sustainability_GHG',
	'Sustainability: Total grams PM 2.5 Emitted':'sustainability_PM',

	'TollRevenue': 'TollRevenue'
	'VMT':'VMT'
}


#Load an old standardization file
def loadStandardization(file = "standardizationParameters.csv"):
	dict_name = file
	means = {}
	sigma = {}
	with open(dict_name) as csvfile:
		reader = csv.reader(csvfile)
		for row in reader:

			means[row[0]] = float(row[1])
			sigma[row[0]] = float(row[2])

	return (means, sigma)


def read_toll_revenue(tpe_dir):
	output_dir = os.path.join(tpe_dir, 'output')
	output_dir = os.path.join(output_dir, only_subdir(output_dir))
	output_dir = os.path.join(output_dir, only_subdir(output_dir))
	output_dir = os.path.join(output_dir, only_subdir(output_dir))
	f = gzip.open(os.path.join(output_dir,'outputEvents.xml.gz'), 'rb')
	doc = xmltodict.parse(f.read())
	totalTolls = 0
	for event in doc['events']['event']:
		if '@tollPaid' in event.keys():
			totalTolls += float(event['@tollPaid'])

	print("		Tolls paid : " + str(totalTolls))
	return totalTolls


def load_raw(tpe_dir):
	path = os.path.join(get_results_dir(tpe_dir), "rawScores.csv")
	dic = {}

	if not check_file_existence(tpe_dir):
		return

	with open(path) as csvfile:
		df = pd.read_csv(csvfile)
		kpi_names = list(df.columns)
		for name in kpi_names:
			dic[trans_dict[name]] = list(df[name])[-1]

	if 'TollRevenue' not in dic.keys():
		dic['TollRevenue'] = read_toll_revenue(tpe_dir)
	return dic

def standardize():
	dirs = getTimeSortedDirs()
	print("Found ",len(dirs), " samples")
	i = 0

	(means, sigma) = loadStandardization("old_standards.csv")

	scores = {}
	for key in means:
		scores[key] = []
	scores['TollRevenue'] = []


	for d in dirs:
		i += 1
		print("Loading score " + str(i) + " / " + str(len(dirs)))
		score = load_raw(d)
		for s,v in score.items():
			if s!="Iteration" and s!="TollRevenue":
				scores[s].append(v)
			if s=="TollRevenue" and v > -1.0:
				scores[s].append(v)


	print("Computing means and stds")
	for s,v in scores.items():
		mean, std = np.mean(v), np.std(v)
		means[s] = mean
		sigma[s] = std

	print("Saving to file")
	save_standards(means, sigma)


def save_standards(means, sigma):

	path = "standardizationParameters.csv"

	with open(path, mode='w') as csvfile:
		writer = csv.writer(csvfile, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
		for k in means.keys():
			writer.writerow([k, means[k], sigma[k]])
		csvfile.close()

if __name__=="__main__":
	standardize()
