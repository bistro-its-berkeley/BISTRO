
TABLES = {}
COLUMNS = {}
INSERT = {}

# because of the foreign relation, tables cannot be created in random order
# the partial order below addresses the dependency between foreign key relations.
TABLES_LIST = [
    'scenario', 'simulationrun', 'simulationtag', 'node', 'link', 'household',
    'person', 'activity', 'vehicletype', 'vehiclecost', 'agency',
    'transitroute', 'transittrip', 'fleetmix', 'transitfare', 'incentive',
    'roadpricing', 'tollcircle', 'vehicle', 'trip', 'leg', 'leg_link',
    'pathtraversal', 'pathtraversal_link', 'leg_pathtraversal', 'modechoice',
    'realizedmodechoice', 'hourlymodechoice', 'traveltime', 'score'
    ]


TABLES['scenario'] = """
`scenario` VARCHAR(50) PRIMARY KEY NOT NULL,
`fixed_data_stored` BOOL
"""
COLUMNS['scenario'] = '`scenario`, `fixed_data_stored`'
INSERT['scenario'] = '%s, %s'


TABLES['simulationrun'] = """
`run_id` BINARY(16) PRIMARY KEY,
`datetime` DATETIME NOT NULL,
`scenario` VARCHAR(50) NOT NULL,
`name` VARCHAR(50)
"""
COLUMNS['simulationrun'] = '`run_id`, `datetime`, `scenario`, `name`'
INSERT['simulationrun'] = 'UUID_TO_BIN(%s), %s, %s, %s'


TABLES['simulationtag'] = """
`tag` VARCHAR(100),
`name` VARCHAR(50)
"""
COLUMNS['simulationtag'] = '`tag`, `name`'
INSERT['simulationtag'] = '%s, %s'


TABLES['node'] = """
`node_id` INT,
`x` DOUBLE,
`y` DOUBLE,
`scenario` VARCHAR(50) NOT NULL,
PRIMARY KEY (`node_id`, `scenario`)
"""
COLUMNS['node'] = '`node_id`, `x`, `y`, `scenario`'
INSERT['node'] = ', '.join(['%s']*4)


TABLES['link'] = """
`link_id` INT,
`original_node_id` INT,
`destination_node_id` INT,
`length` DOUBLE,
`freespeed` DOUBLE,
`capacity` DOUBLE,
`modes` VARCHAR(50),
`osm_id` INT,
`link_type` VARCHAR(50),
`scenario` VARCHAR(50) NOT NULL,
PRIMARY KEY (`link_id`, `scenario`),
FOREIGN KEY (`original_node_id`, `scenario`)
REFERENCES `node` (`node_id`, `scenario`) ON DELETE CASCADE,
FOREIGN KEY (`destination_node_id`, `scenario`)
REFERENCES `node` (`node_id`, `scenario`) ON DELETE CASCADE
"""
COLUMNS['link'] = ('`link_id`,`original_node_id`,`destination_node_id`,'
    '`length`,`freespeed`,`capacity`,`modes`,`osm_id`,`link_type`,`scenario`') 
INSERT['link'] = ', '.join(['%s']*10)


TABLES['household'] = """
`household_id` VARCHAR(100),
`household_income` INT,
`num_vehicles` SMALLINT,
`x` DOUBLE,
`y` DOUBLE,
`scenario` VARCHAR(50) NOT NULL,
PRIMARY KEY (`household_id`, `scenario`)
"""
COLUMNS['household'] = ('`household_id`,`household_income`,`num_vehicles`,`x`,'
    '`y`,`scenario`')
INSERT['household'] = ', '.join(['%s']*6)


TABLES['person'] = """
`person_id` VARCHAR(100),
`household_id` VARCHAR(100) NOT NULL,
`age` SMALLINT,
`sex` VARCHAR(10),
`income` INT,
`excluded_modes` VARCHAR(50),
`rank` SMALLINT,
`value_of_time` SMALLINT,
`scenario` VARCHAR(50) NOT NULL,
PRIMARY KEY (`person_id`, `scenario`),
FOREIGN KEY (`household_id`, `scenario`)
REFERENCES `household` (`household_id`, `scenario`) ON DELETE CASCADE
"""
COLUMNS['person'] = ('`person_id`,`household_id`,`age`,`sex`,`income`,'
    '`excluded_modes`,`rank`,`value_of_time`,`scenario`')
INSERT['person'] = ', '.join(['%s']*9)


TABLES['activity'] = """
`person_id` VARCHAR(100) NOT NULL,
`activity_num` SMALLINT NOT NULL,
`activity_type` VARCHAR(20),
`link_id` INT,
`desired_start` TIME,
`desired_end` TIME,
`scenario` VARCHAR(50) NOT NULL,
PRIMARY KEY (`person_id`, `activity_num`, `scenario`),
FOREIGN KEY (`person_id`, `scenario`)
REFERENCES `person` (`person_id`, `scenario`) ON DELETE CASCADE,
FOREIGN KEY (`link_id`, `scenario`)
REFERENCES `link` (`link_id`, `scenario`) ON DELETE CASCADE
"""
COLUMNS['activity'] = ('`person_id`, `activity_num`, `activity_type`, `link_id`,'
    ' `desired_start`, `desired_end`,`scenario`')
INSERT['activity'] = ', '.join(['%s']*7)


TABLES['vehicletype'] = """
`vehicle_type` VARCHAR(50),
`fuel` VARCHAR(20),
`fuel_consumption` FLOAT,
`fuel_capacity` FLOAT,
`seating_capacity` SMALLINT,
`standing_capacity` SMALLINT,
`scenario` VARCHAR(50) NOT NULL,
KEY `fuel` (`fuel`),
PRIMARY KEY (`vehicle_type`, `scenario`)
"""
COLUMNS['vehicletype'] = ('`vehicle_type`, `fuel`, `fuel_consumption`, '
    '`fuel_capacity`, `seating_capacity`, `standing_capacity`,`scenario`')
INSERT['vehicletype'] = ', '.join(['%s']*7)


TABLES['vehiclecost'] = """
`vehicle_type` VARCHAR(50),
`purchase_cost` INT,
`operation_cost` DOUBLE,
`scenario` VARCHAR(50),
FOREIGN KEY (`vehicle_type`, `scenario`)
REFERENCES `vehicletype` (`vehicle_type`, `scenario`) ON DELETE CASCADE
"""
COLUMNS['vehiclecost'] = ('`vehicle_type`,`purchase_cost`,`operation_cost`,'
    '`scenario`')
INSERT['vehiclecost'] = ', '.join(['%s']*4)


TABLES['agency'] = """
`agency_id` VARCHAR(20),
`scenario` VARCHAR(50)
"""
COLUMNS['agency'] = '`agency_id`, `scenario`'
INSERT['agency'] = ', '.join(['%s']*2)


TABLES['transitroute'] = """
`route_id` INT,
`agency_id` VARCHAR(20),
`scenario` VARCHAR(50)
"""
COLUMNS['transitroute'] = '`route_id`,`agency_id`,`scenario`'
INSERT['transitroute'] = ', '.join(['%s']*3)


TABLES['transittrip'] = """
`route_id` INT,
`service_id` VARCHAR(50),
`trip_id` VARCHAR(50),
`scenario` VARCHAR(50)
"""
COLUMNS['transittrip'] = '`route_id`,`service_id`,`trip_id`,`scenario`'
INSERT['transittrip'] = ', '.join(['%s']*4)


TABLES['vehicle'] = """
`vehicle_id` VARCHAR(100),
`type` VARCHAR(50),
`scenario` VARCHAR(50) NOT NULL,
KEY `type` (`type`),
PRIMARY KEY (`vehicle_id`, `scenario`),
FOREIGN KEY (`type`, `scenario`)
REFERENCES `vehicletype` (`vehicle_type`, `scenario`) ON DELETE CASCADE
"""
COLUMNS['vehicle'] = '`vehicle_id`, `type`, `scenario`'
INSERT['vehicle'] = ', '.join(['%s']*3)

TABLES['fuel'] = """
`fuel_id` VARCHAR(20) PRIMARY KEY
"""


TABLES['trip'] = """
`run_id` BINARY(16) NOT NULL,
`person_id` VARCHAR(100) NOT NULL,
`trip_num` SMALLINT NOT NULL,
`orig_act` SMALLINT,
`dest_act` SMALLINT,
`trip_start` INT,
`trip_end` INT,
`distance` DOUBLE,
`planned_mode` VARCHAR(20),
`realized_mode` VARCHAR(20),
`fare` DOUBLE,
`fuel_cost` DOUBLE,
`toll` DOUBLE,
`incentives` DOUBLE,
PRIMARY KEY (`run_id`, `person_id`, `trip_num`),
FOREIGN KEY (`run_id`) REFERENCES `simulationrun` (`run_id`) ON DELETE CASCADE,
FOREIGN KEY (`person_id`) REFERENCES `person` (`person_id`) ON DELETE CASCADE
"""
COLUMNS['trip'] = (
    '`run_id`, `person_id`, `trip_num`, `orig_act`, `dest_act`, `trip_start`, '
    '`trip_end`, `distance`, `planned_mode`, `realized_mode`, `fare`, '
    '`fuel_cost`, `toll`, `incentives`')
INSERT['trip'] = 'UUID_TO_BIN(%s), ' + ', '.join(['%s']*13)


TABLES['leg'] = """
`run_id` BINARY(16) NOT NULL,
`person_id` VARCHAR(100) NOT NULL,
`trip_num` SMALLINT NOT NULL,
`leg_num` SMALLINT NOT NULL,
`orig_link` INT,
`dest_link` INT,
`leg_start` INT,
`leg_end` INT,
`distance` DOUBLE,
`leg_mode` VARCHAR(20),
`vehicle` VARCHAR(100),
`fuel_cost` DOUBLE, 
`fare` DOUBLE,
`toll` DOUBLE,
PRIMARY KEY (`run_id`, `person_id`, `trip_num`, `leg_num`),
FOREIGN KEY (`run_id`) REFERENCES `simulationrun` (`run_id`) ON DELETE CASCADE,
FOREIGN KEY (`person_id`) REFERENCES `person` (`person_id`) ON DELETE CASCADE
"""
COLUMNS['leg'] = (
    '`run_id`, `person_id`, `trip_num`, `leg_num`, `orig_link`, `dest_link`, '
    '`leg_start`, `leg_end`, `distance`, `leg_mode`, `vehicle`, `fuel_cost`, '
    '`fare`, `toll`')
INSERT['leg'] = 'UUID_TO_BIN(%s), ' + ', '.join(['%s']*13)


TABLES['leg_link'] = """
`run_id` BINARY(16),
`person_id` VARCHAR(100),
`trip_num` SMALLINT,
`leg_num` SMALLINT,
`link_id` INT,
`scenario` VARCHAR(50),
PRIMARY KEY (`run_id`, `person_id`, `trip_num`, `leg_num`, `link_id`,
             `scenario`),
FOREIGN KEY (`run_id`, `person_id`, `trip_num`, `leg_num`)
REFERENCES `leg` (`run_id`, `person_id`, `trip_num`, `leg_num`),
FOREIGN KEY (`link_id`, `scenario`) REFERENCES `link` (`link_id`, `scenario`)
"""
COLUMNS['leg_link'] = ('`run_id`, `person_id`, `trip_num`, `leg_num`, '
    '`link_id`, `scenario`')
INSERT['leg_link'] = 'UUID_TO_BIN(%s), ' + ', '.join(['%s']*5)


TABLES['leg_pathtraversal'] = """
`run_id` BINARY(16),
`person_id` VARCHAR(100),
`trip_num` SMALLINT,
`leg_num` SMALLINT,
`vehicle_id` VARCHAR(100),
`path_num` SMALLINT,
PRIMARY KEY (`run_id`, `person_id`, `trip_num`, `leg_num`, `vehicle_id`,
             `path_num`),
FOREIGN KEY (`run_id`, `person_id`, `trip_num`, `leg_num`)
REFERENCES `leg` (`run_id`, `person_id`, `trip_num`, `leg_num`),
FOREIGN KEY (`run_id`, `vehicle_id`, `path_num`)
REFERENCES `pathtraversal` (`run_id`, `vehicle_id`, `path_num`)
"""
COLUMNS['leg_pathtraversal'] = ('`run_id`, `person_id`, `trip_num`, `leg_num`, '
    '`vehicle_id`, `path_num`')
INSERT['leg_pathtraversal'] = 'UUID_TO_BIN(%s), ' + ', '.join(['%s']*5)


TABLES['pathtraversal'] = """
`run_id` BINARY(16) NOT NULL,
`vehicle_id` VARCHAR(100) NOT NULL,
`path_num` SMALLINT NOT NULL,
`driver_id` VARCHAR(100),
`mode` VARCHAR(20),
`distance` DOUBLE,
`start_time` INT,
`end_time` INT,
`num_passengers` SMALLINT,
`fuel_consumed` DOUBLE,
`fuel_level` DOUBLE,
`fuel_type` VARCHAR(20),
`fuel_cost` DOUBLE,
`start_x` DOUBLE,
`start_y` DOUBLE,
`end_x` DOUBLE,
`end_y` DOUBLE,
KEY `driver_id` (`driver_id`),
PRIMARY KEY (`run_id`, `vehicle_id`, `path_num`),
FOREIGN KEY (`run_id`) REFERENCES `simulationrun` (`run_id`) ON DELETE CASCADE,
FOREIGN KEY (`vehicle_id`) REFERENCES `vehicle` (`vehicle_id`) ON DELETE CASCADE
"""
COLUMNS['pathtraversal'] = (
    '`run_id`, `vehicle_id`, `path_num`, `driver_id`, `mode`, `distance`, '
    '`start_time`, `end_time`, `num_passengers`, `fuel_consumed`, `fuel_level`,'
    '`fuel_type`, `fuel_cost`, `start_x`, `start_y`, `end_x`, `end_y`')
INSERT['pathtraversal'] = 'UUID_TO_BIN(%s), ' + ', '.join(['%s']*16)


TABLES['pathtraversal_link'] = """
`run_id` BINARY(16),
`vehicle_id` VARCHAR(100),
`path_num` SMALLINT,
`link_id` INT,
`scenario` VARCHAR(50),
PRIMARY KEY (`run_id`, `vehicle_id`, `path_num`, `link_id`, `scenario`),
FOREIGN KEY (`run_id`, `vehicle_id`, `path_num`)
REFERENCES `pathtraversal` (`run_id`, `vehicle_id`, `path_num`),
FOREIGN KEY (`link_id`, `scenario`) REFERENCES `link` (`link_id`, `scenario`)
"""
COLUMNS['pathtraversal_link'] = ('`run_id`, `vehicle_id`, `path_num`,'
    ' `link_id`, `scenario`')
INSERT['pathtraversal_link'] = 'UUID_TO_BIN(%s), ' + ', '.join(['%s']*4)


TABLES['incentive'] = """
`run_id` BINARY(16),
`trip_mode` VARCHAR(50),
`age_min` SMALLINT,
`age_max` SMALLINT,
`income_min` INT,
`income_max` INT,
`amount` FLOAT,
PRIMARY KEY (`trip_mode`, `age_min`, `age_max`, `income_min`, `income_max`),
FOREIGN KEY (`run_id`) REFERENCES `simulationrun` (`run_id`) ON DELETE CASCADE
"""
COLUMNS['incentive'] = ('`run_id`,`trip_mode`,`age_min`,`age_max`,`income_min`,'
    '`income_max`,`amount`')
INSERT['incentive'] = 'UUID_TO_BIN(%s), ' + ', '.join(['%s']*6)


TABLES['fleetmix'] = """
`run_id` BINARY(16),
`agency_id` VARCHAR(20),
`route_id` INT,
`service_start` INT,
`service_end` INT,
`frequency` INT,
`vehicle_type` VARCHAR(50),
PRIMARY KEY (`agency_id`, `route_id`, `service_start`, `service_end`),
FOREIGN KEY (`run_id`) REFERENCES `simulationrun` (`run_id`) ON DELETE CASCADE
"""
COLUMNS['fleetmix'] = ('`run_id`, `agency_id`, `route_id`, `service_start`,'
    '`service_end`, `frequency`, `vehicle_type`')
INSERT['fleetmix'] = 'UUID_TO_BIN(%s), ' + ', '.join(['%s']*6)


TABLES['transitfare'] = """
`run_id` BINARY(16),
`route_id` INT,
`age_min` SMALLINT,
`age_max` SMALLINT,
`amount` FLOAT,
PRIMARY KEY (`route_id`, `age_min`, `age_max`),
FOREIGN KEY (`run_id`) REFERENCES `simulationrun` (`run_id`) ON DELETE CASCADE
"""
COLUMNS['transitfare'] = '`run_id`,`route_id`,`age_min`,`age_max`,`amount`'
INSERT['transitfare'] = 'UUID_TO_BIN(%s), ' + ', '.join(['%s']*4)


TABLES['roadpricing'] = """
`run_id` BINARY(16),
`link_id` INT,
`toll` FLOAT,
`start_time` INT,
`end_time` INT,
FOREIGN KEY (`run_id`) REFERENCES `simulationrun` (`run_id`) ON DELETE CASCADE,
FOREIGN KEY (`link_id`) REFERENCES `link` (`link_id`) ON DELETE CASCADE
"""
COLUMNS['roadpricing'] = '`run_id`, `link_id`, `toll`, `start_time`, `end_time`'
INSERT['roadpricing'] = 'UUID_TO_BIN(%s), ' + ', '.join(['%s']*4)


TABLES['tollcircle'] = """
`run_id` BINARY(16),
`scenario` VARCHAR(50),
`type` VARCHAR(20),
`toll` FLOAT,
`center_lat` DOUBLE,
`center_lon` DOUBLE,
`border_lat` DOUBLE,
`border_lon` DOUBLE,
FOREIGN KEY (`run_id`) REFERENCES `simulationrun` (`run_id`) ON DELETE CASCADE
"""
COLUMNS['tollcircle'] = ('`run_id`, `scenario`, `type`, `toll`, `center_lat`, '
    '`center_lon`, `border_lat`, `border_lon`')
INSERT['tollcircle'] = 'UUID_TO_BIN(%s), ' + ', '.join(['%s']*7)

TABLES['modechoice'] = """
`run_id` BINARY(16),
`iterations` SMALLINT,
`mode` VARCHAR(20),
`count` INT,
FOREIGN KEY (`run_id`) REFERENCES `simulationrun` (`run_id`) ON DELETE CASCADE
"""
COLUMNS['modechoice'] = '`run_id`,`iterations`,`mode`,`count`'
INSERT['modechoice'] = 'UUID_TO_BIN(%s), ' + ', '.join(['%s']*3)


TABLES['realizedmodechoice'] = """
`run_id` BINARY(16),
`iterations` SMALLINT,
`mode` VARCHAR(20),
`count` INT,
FOREIGN KEY (`run_id`) REFERENCES `simulationrun` (`run_id`) ON DELETE CASCADE
"""
COLUMNS['realizedmodechoice'] = '`run_id`,`iterations`,`mode`,`count`'
INSERT['realizedmodechoice'] = 'UUID_TO_BIN(%s), ' + ', '.join(['%s']*3)


TABLES['hourlymodechoice'] = """
`run_id` BINARY(16),
`mode` VARCHAR(20),
`hour` SMALLINT,
`count` INT,
FOREIGN KEY (`run_id`) REFERENCES `simulationrun` (`run_id`) ON DELETE CASCADE
"""
COLUMNS['hourlymodechoice'] = '`run_id`,`mode`,`hour`,`count`'
INSERT['hourlymodechoice'] = 'UUID_TO_BIN(%s), ' + ', '.join(['%s']*3)


TABLES['traveltime'] = """
`run_id` BINARY(16),
`mode` VARCHAR(20),
`hour` SMALLINT,
`averagetime` DOUBLE,
FOREIGN KEY (`run_id`) REFERENCES `simulationrun` (`run_id`) ON DELETE CASCADE
"""
COLUMNS['traveltime'] = '`run_id`,`mode`,`hour`,`averagetime`'
INSERT['traveltime'] = 'UUID_TO_BIN(%s), ' + ', '.join(['%s']*3)


TABLES['score'] = """
`run_id` BINARY(16),
`component` VARCHAR(200),
`weight` DOUBLE,
`z_mean` DOUBLE,
`z_stddev` DOUBLE,
`raw_score` DOUBLE,
`submission_score` DOUBLE,
FOREIGN KEY (`run_id`) REFERENCES `simulationrun` (`run_id`) ON DELETE CASCADE
"""
COLUMNS['score'] = ('`run_id`, `component`, `weight`, `z_mean`, `z_stddev`, '
    '`raw_score`, `submission_score`')
INSERT['score'] = 'UUID_TO_BIN(%s), ' + ', '.join(['%s']*6)


"""

TABLES['facility'] = 
`facility_id` VARCHAR(50) PRIMARY KEY,
`node_id` INT,
`type` VARCHAR(20),
KEY `node_id` (`node_id`),
FOREIGN KEY (`node_id`) REFERENCES `node` (`node_id`) ON DELETE CASCADE



TABLES['geography'] =


TABLES['tripmode'] = 



TABLES['mode'] =


TABLES['transitagency'] = 
`agency_id` VARCHAR(10),
`mode` VARCHAR(20),
`scenario` VARCHAR(50) NOT NULL,
KEY `mode` (`mode`),
PRIMARY KEY (`agency_id`, `scenario`),
"""
