package beam.competition.run

import java.io.File
import java.nio.file._
import java.nio.file.attribute.BasicFileAttributes
import java.util

import beam.agentsim.agents.vehicles.FuelType.FuelType
import beam.agentsim.agents.vehicles.{BeamVehicleType, FuelType}
import beam.competition.evaluation.component.NormalizedScoreComponent.StandardizationParams
import beam.competition.evaluation.component.ScoreComponent.ScoreComponentWeightIdentifier
import beam.competition.inputs.impl.VehicleCostData
import beam.competition.inputs.impl.VehicleCostData.readBeamVehicleCostsFile
import beam.router.r5.NetworkCoordinator
import beam.sim.BeamServices
import beam.sim.config.BeamConfig
import beam.utils.BeamVehicleUtils.{readBeamVehicleTypeFile, readCsvFileByLine}
import beam.utils.FileUtils
import com.conveyal.gtfs.GTFSFeed
import com.conveyal.gtfs.model.Route
import com.typesafe.scalalogging.LazyLogging
import org.matsim.api.core.v01.Id
import org.matsim.api.core.v01.population.Activity

import scala.collection.JavaConverters._
import scala.collection.concurrent.TrieMap
import scala.collection.immutable
import scala.collection.mutable.ArrayBuffer
import scala.io.Source

case class CompetitionServices(beamServices: BeamServices, networkCoordinator: NetworkCoordinator) extends LazyLogging {


  import CompetitionServices._

  final val beamConfig: BeamConfig = beamServices.beamConfig

  final val lastIteration = beamConfig.beam.agentsim.lastIteration

  final val simNameParts = beamConfig.beam.agentsim.simulationName.split("-",2)

  final val SIMULATION_NAME: String = simNameParts(0)

  final val SAMPLE_NAME: String = simNameParts(1)

  final val SUBMISSION_OUTPUT_ROOT_NAME: String = s"${
    FileUtils.getConfigOutputFile(
      beamConfig.beam.outputs.baseOutputDirectory,
      beamConfig.beam.agentsim.simulationName,
      beamConfig.beam.outputs.addTimestampToOutputDirectory,
    )
  }"

  final val SCORING_WEIGHTS_PATH = Paths.get(FIXED_DATA_ROOT_NAME, SIMULATION_NAME, "scoringWeights.csv")

  final val STANDARDIZATION_PARAMETER_FILENAME = Paths.get(FIXED_DATA_ROOT_NAME, SIMULATION_NAME, "standardizationParameters.csv")

  final val BAU_ROOT_PATH: Path = Paths.get(FIXED_DATA_ROOT_NAME, SIMULATION_NAME, BAU_ROOT_NAME)

  final val INPUT_DEST: Path = Paths.get(SUBMISSION_OUTPUT_ROOT_NAME, COMPETITION_ROOT, INPUT_ROOT)

  final val BAU_STATS_PATH: Path = Paths.get(BAU_ROOT_PATH.toString, "stats", s"$SUMMARY_STATS_NAME-$SAMPLE_NAME.csv")

  final val SUBMISSION_STATS_PATH: Path = Paths.get(SUBMISSION_OUTPUT_ROOT_NAME, s"$SUMMARY_STATS_NAME.csv")

  final val SUBMISSION_STATS_Vehicle_PATH: Path = Paths.get(SUBMISSION_OUTPUT_ROOT_NAME, s"$SUMMARY_STATS_Vehicle_NAME.csv")

  final val VIZ_OUTPUT_ROOT = Paths.get(SUBMISSION_OUTPUT_ROOT_NAME, "competition", "viz")

  lazy val fuelTypes: TrieMap[FuelType, BeamFuelData] =
    TrieMap(CompetitionServices.readFuelTypeFile(beamConfig.beam.agentsim.agents.vehicles.fuelTypesFilePath).toSeq: _*)

  lazy val vehicleTypes: TrieMap[Id[BeamVehicleType], BeamVehicleType] =
    TrieMap(
      readBeamVehicleTypeFile(beamConfig.beam.agentsim.agents.vehicles.vehicleTypesFilePath).toSeq: _*
    )

  final val VEHICLE_COSTS: Map[Id[BeamVehicleType], VehicleCostData] = readBeamVehicleCostsFile(Paths.get(FIXED_DATA_ROOT_NAME, SIMULATION_NAME, "vehicleCosts.csv").toString)

  final val OUTPUT_DIRECTORY: String = Paths.get(SUBMISSION_OUTPUT_ROOT_NAME, CompetitionServices.COMPETITION_ROOT).toString

  val gtfsFeeds: ArrayBuffer[GTFSFeed] = getAllGTFSFiles(beamConfig.beam.routing.r5.directory).map(file => GTFSFeed.fromFile(file.toString))
  val gtfsAgenciesAndRoutes: Map[String, util.Map[String, Route]] = gtfsFeeds.map { feed: GTFSFeed =>
    (feed.agency.values.iterator().next().agency_id, feed.routes)
  }.toMap

  final lazy val activityTypes: Set[String] = beamServices.matsimServices.getScenario.getPopulation.getPersons.asScala.values.flatMap { person =>
    person.getSelectedPlan.getPlanElements.asScala.filter(_.isInstanceOf[Activity]).map { pe =>
      pe.asInstanceOf[Activity].getType
    }
  }.toSet


  final lazy val weights: Map[ScoreComponentWeightIdentifier, Double] = {
    val lines = Source.fromFile(SCORING_WEIGHTS_PATH.toFile).getLines().toSeq
    val weightIndicators = lines.head.split(",").map(ScoreComponentWeightIdentifier.withName)
    val values = lines(1).split(",").map(_.toDouble)
    weightIndicators.zip(values).toMap
  }

  final val standardizationParams: Map[ScoreComponentWeightIdentifier, StandardizationParams] = {
    val lines: immutable.Seq[Array[String]] = Source.fromFile(STANDARDIZATION_PARAMETER_FILENAME.toFile).getLines().toVector.map(l => l.split(","))

    (for {line <- lines}
      yield {
        ScoreComponentWeightIdentifier.withName(line(0).toString) -> StandardizationParams(line(1).toDouble, line(2).toDouble)
      }).toMap

  }

}

object CompetitionServices {

  final val MAX_HEADWAY_SECS: Int = 60 * 60 * 2 // 2 Hours

  final val MIN_HEADWAY_SECS: Int = 60 * 3 // 3 Minutes

  final val BUS_COST_SCALING_FACTOR = Math.pow(100000.0, -1)

  final val COMPETITION_ROOT: String = "competition"

  final val INPUT_ROOT: String = "submission-inputs/"

  final val BAU_ROOT_NAME: String = "bau"

  final val SUMMARY_STATS_NAME: String = "summaryStats"

  final val SUMMARY_STATS_Vehicle_NAME: String = "summaryVehicleStats"

  final val FIXED_DATA_ROOT_NAME: String = "fixed-data"

  final val POSSIBLE_INCENTIVE_MODES: Set[String] = Set("onDemandRide", "drive_transit", "walk_transit", "onDemandRide_transit", "walk")

  final val INPUT_ROOT_PATH: Path = new File(INPUT_ROOT).toPath.toAbsolutePath

  case class BeamFuelData(cost: Double, gramsGHGePerGallon: Double, pm25PerVMT: Double)

  def getAllGTFSFiles(pathToR5Dir: String): ArrayBuffer[Path] = {
    val files = ArrayBuffer.empty[Path]
    val r5Path = Paths.get(s"$pathToR5Dir")
    Files.walkFileTree(r5Path, new SimpleFileVisitor[Path] {
      override def visitFile(file: Path, attrs: BasicFileAttributes): FileVisitResult = {
        if (file.getFileName.toString.endsWith(".zip")) {
          files += file
        }
        FileVisitResult.CONTINUE
      }
    })
    files
  }

  def readFuelTypeFile(filePath: String): scala.collection.Map[FuelType, BeamFuelData] = {
    readCsvFileByLine(filePath, scala.collection.mutable.HashMap[FuelType, BeamFuelData]()) {
      case (line, z) =>
        val fuelType = FuelType.fromString(line.get("fuelTypeId"))
        val priceInDollarsPerMJoule = line.get("priceInDollarsPerMJoule").toDouble
        val pm25PerVMT = line.get("pm25PerVMT").toDouble
        val gramsCO2EquivPerGallon = line.get("gCO2ePerGal").toDouble
        z += ((fuelType, BeamFuelData(priceInDollarsPerMJoule, gramsCO2EquivPerGallon, pm25PerVMT)))
    }
  }


}
