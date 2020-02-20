#Defined frequently used KPIS

congestion_KPI = {
	"averageVehicleDelayPerPassengerTrip":0.333,
	"sustainability_GHG":0.333,
	"VMT":0.333
}

social_KPI = {
	"averageTravelCostBurden_Work":0.33,
	"busCrowding":0.33,
	"averageTravelCostBurden_Secondary":0.33
}

cost_burden_KPI = {
	"averageTravelCostBurden_Work":0.50,
	"averageTravelCostBurden_Secondary":0.50
}


VMT_KPI = {
	"VMT":1.0
}

Aggregate_optim_KPI = {
	"averageVehicleDelayPerPassengerTrip":1*0.333/4,
	"sustainability_GHG":1*0.333/4,
	"VMT":1*0.333/4,
	"averageTravelCostBurden_Work":1*0.5/4,
	"averageTravelCostBurden_Secondary":1*0.5/4,
	"TollRevenue":-1.0/2
}

Aggregate_0_KPI = {
	"averageVehicleDelayPerPassengerTrip":1*0.333/4,
	"sustainability_GHG":1*0.333/4,
	"VMT":1*0.333/4,
	"averageTravelCostBurden_Work":1*0.5/4,
	"averageTravelCostBurden_Secondary":1*0.5/4,
	"TollRevenue":-1.0/2
}

Aggregate_1_KPI = {
	"averageVehicleDelayPerPassengerTrip":1*0.333/4,
	"sustainability_GHG":1*0.333/4,
	"VMT":1*0.333/4,
	"averageTravelCostBurden_Work":1*0.5/4,
	"averageTravelCostBurden_Secondary":1*0.5/4,
	"TollRevenue":-1.0/2
}

Aggregate_2_KPI = {
	"averageVehicleDelayPerPassengerTrip":1*0.333/3,
	"sustainability_GHG":1*0.333/3,
	"VMT":1*0.333/3,
	"averageTravelCostBurden_Work":1*0.5/3,
	"averageTravelCostBurden_Secondary":1*0.5/3,
	"TollRevenue":-1.0/3
}

Aggregate_3_KPI = {
	"averageVehicleDelayPerPassengerTrip":3*0.333/8,
	"sustainability_GHG":3*0.333/8,
	"VMT":3*0.333/8,
	"averageTravelCostBurden_Work":3*0.5/8,
	"averageTravelCostBurden_Secondary":3*0.5/8,
	"TollRevenue":-1.0/4
}

Aggregate_4_KPI = {
	"averageVehicleDelayPerPassengerTrip":2*0.333/5,
	"sustainability_GHG":2*0.333/5,
	"VMT":2*0.333/5,
	"averageTravelCostBurden_Work":2*0.5/5,
	"averageTravelCostBurden_Secondary":2*0.5/5,
	"TollRevenue":-1.0/5
}

Aggregate_5_KPI = {
	"averageVehicleDelayPerPassengerTrip":5*0.333/12,
	"sustainability_GHG":5*0.333/12,
	"VMT":5*0.333/12,
	"averageTravelCostBurden_Work":5*0.5/12,
	"averageTravelCostBurden_Secondary":5*0.5/12,
	"TollRevenue":-1.0/6
}

Aggregate_6_KPI = {
	"averageVehicleDelayPerPassengerTrip":2*0.333/10,
	"sustainability_GHG":2*0.333/10,
	"VMT":2*0.333/10,
	"averageTravelCostBurden_Work":4*0.5/10,
	"averageTravelCostBurden_Secondary":4*0.5/10,
	"TollRevenue":-4.0/10
}

Aggregate_7_KPI = {
	"averageVehicleDelayPerPassengerTrip":2*0.333/10,
	"sustainability_GHG":2*0.333/10,
	"VMT":2*0.333/10,
	"averageTravelCostBurden_Work":5*0.5/10,
	"averageTravelCostBurden_Secondary":5*0.5/10,
	"TollRevenue":-3.0/10
}

Aggregate_8_KPI = {
	"averageVehicleDelayPerPassengerTrip":2*0.333/10,
	"sustainability_GHG":2*0.333/10,
	"VMT":2*0.333/10,
	"averageTravelCostBurden_Work":3*0.5/10,
	"averageTravelCostBurden_Secondary":3*0.5/10,
	"TollRevenue":-5.0/10
}


Toll_Revenue_KPI = {
	"TollRevenue":-1.0
}

Avg_vehicule_delay_KPI = {
	"averageVehicleDelayPerPassengerTrip":1
}

Avg_cost_burden_work_KPI = {
	"averageTravelCostBurden_Work":1
}

Avg_cost_burden_secondary_KPI = {
	"averageTravelCostBurden_Secondary":1
}

Bus_crowding_KPI = {
	"busCrowding":1
}

ALL_KPIS = [Aggregate_0_KPI, Aggregate_1_KPI, Aggregate_2_KPI, Aggregate_3_KPI, Aggregate_4_KPI, Aggregate_5_KPI,Aggregate_6_KPI,Aggregate_7_KPI,Aggregate_8_KPI, VMT_KPI, cost_burden_KPI, congestion_KPI, social_KPI, Toll_Revenue_KPI, Avg_vehicule_delay_KPI]
ALL_KPIS += [Avg_cost_burden_work_KPI, Avg_cost_burden_secondary_KPI, Bus_crowding_KPI]

ALL_NAMES = ["Agg0", "Agg1", "Agg2", "Agg3", "Agg4", "Agg5", "Agg6", "Agg7", "Agg8", "VMT", "Cost Burden", "Congestion", "Social", "TR", "VHD"]
ALL_NAMES += ["CB_work", "CB_2ndary", "BC"]



"""
aggregate_KPI = {
	"averageVehicleDelayPerPassengerTrip":2*0.333/5,
	"sustainability_GHG":2*0.333/5,
	"VMT":2*0.333/5,
	"averageTravelCostBurden_Work":2*0.333/5,
	"busCrowding":2*0.333/5,
	"averageTravelCostBurden_Secondary":2*0.333/5,
	"TollRevenue":1.0/5
}

aggregate_KPI_2 = {
	"averageVehicleDelayPerPassengerTrip":2*0.333/5,
	"sustainability_GHG":2*0.333/5,
	"VMT":2*0.333/5,
	"averageTravelCostBurden_Work":2*0.5/5,
	"averageTravelCostBurden_Secondary":2*0.5/5,
	"TollRevenue":1.0/5
}

TollRevenue_KPI = {
	"TollRevenue":1.0
}
"""