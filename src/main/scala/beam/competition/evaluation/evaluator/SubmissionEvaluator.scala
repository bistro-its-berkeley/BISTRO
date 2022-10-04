package beam.competition.evaluation.evaluator

import java.nio.file.{Path, Paths}

import beam.competition.evaluation.component.ScoreComponent.ScoreComponentWeightIdentifier
import beam.competition.evaluation.component.ScoreComponent.ScoreComponentWeightIdentifier.{CostBenefitAnalysis, Sustainability_GHG, Sustainability_PM, TollRevenue, MotorizedVehicleMilesTraveled_total}
import beam.competition.evaluation.component.{AccessibilityScoreComputation, CompoundScoreComponent, NormalizedScoreComponent}
import beam.competition.inputs.framework.InputReader.loadDblDataTable
import beam.competition.run.CompetitionServices
import beam.competition.utils.SummaryTable
import beam.utils.BeamConfigUtils
import com.github.martincooper.datatable.{DataColumn, DataTable}
import com.google.inject.Inject
import com.typesafe.scalalogging
import com.typesafe.scalalogging.LazyLogging

import scala.collection.mutable.ListBuffer
import scala.io.Source
import scala.collection.concurrent.TrieMap
import org.matsim.api.core.v01.Id
import scala.util.{Try,Success,Failure}
import beam.agentsim.agents.vehicles.BeamVehicleType
import beam.agentsim.agents.vehicles.{BeamVehicleType, FuelType}
import beam.competition.evaluation.component.CompoundSummaryStatKey._



case class SubmissionEvaluator @Inject()(simpleStatFields: Set[ScoreComponentWeightIdentifier],
                                         compoundStatFields: Map[ScoreComponentWeightIdentifier, CompoundScoreComponent],
                                         currentIteration: Int)
                                        (implicit val competitionServices: CompetitionServices) extends LazyLogging {

  implicit val myLogger: scalalogging.Logger = this.logger

  //TODO[saf]: Create these using a factory with score components and names specified in csv
  private val simpleScoringFunctions: Set[_ <: NormalizedScoreComponent] = simpleStatFields.map { sn => new NormalizedScoreComponent(ScoreComponentWeightIdentifier.withName(sn.entryName)) }

  private val summaryTable = SummaryTable()

  val submissionScoreMSAOverNumberOfIters: Int = if (Paths.get(competitionServices.SUBMISSION_OUTPUT_ROOT_NAME + "/beam.conf").toFile.exists()) { BeamConfigUtils.parseFileSubstitutingInputDirectory(  competitionServices.SUBMISSION_OUTPUT_ROOT_NAME + "/beam.conf").getInt("beam.competition.submissionScoreMSAOverNumberOfIters")
  }  else { 1}
  // val submissionScoreMSAOverNumberOfIters: Int = BeamConfigUtils.parseFileSubstitutingInputDirectory(  competitionServices.SUBMISSION_OUTPUT_ROOT_NAME + "/beam.conf").getInt("beam.competition.submissionScoreMSAOverNumberOfIters")

  private lazy val bauDataTable: DataTable = SubmissionEvaluator.loadBAUDataTable("bauDf", competitionServices.BAU_STATS_PATH, submissionScoreMSAOverNumberOfIters)

  private lazy val submissionDataTable: DataTable = SubmissionEvaluator.loadSubmissionDataTable("submissionDf", competitionServices.SUBMISSION_STATS_PATH, submissionScoreMSAOverNumberOfIters, competitionServices.SUBMISSION_VEHICLE_STATS_PATH, competitionServices.vehicleTypes)

  private def getAccessibilityScoreComponent(modeType: String, poiType: String): NormalizedScoreComponent = {
    val accessibilityType = ScoreComponentWeightIdentifier.withName(s"$modeType${poiType.capitalize}Accessibility")
    new NormalizedScoreComponent(accessibilityType)
  }

  def accessibilityScores: BigDecimal = {

    val accessibilityScoreMap: ListBuffer[Map[String, Map[String, Double]]]
    = ListBuffer(Map(
        "secondary" ->
          Map("drive" -> 0.0, "transit" -> 0.0),
        "commute" ->
          Map("drive" -> 0.0, "transit" -> 0.0)
      ),Map(
        "secondary" ->
          Map("drive" -> 0.0, "transit" -> 0.0),
        "commute" ->
          Map("drive" -> 0.0, "transit" -> 0.0)
      ))
//    = if (currentIteration == 1 || currentIteration == competitionServices.lastIteration) {
//      new AccessibilityScoreComputation(currentIteration,competitionServices.lastIteration).runAccessibilityComputation()
//    } else {
//      ListBuffer(Map(
//        "secondary" ->
//          Map("drive" -> 0.0, "transit" -> 0.0),
//        "commute" ->
//          Map("drive" -> 0.0, "transit" -> 0.0)
//      ),Map(
//        "secondary" ->
//          Map("drive" -> 0.0, "transit" -> 0.0),
//        "commute" ->
//          Map("drive" -> 0.0, "transit" -> 0.0)
//      ))
//    }
    val driveWorkValues = Seq(accessibilityScoreMap.head("commute")("drive"),accessibilityScoreMap(1)("commute")("drive"))
    val transitWorkValues= Seq(accessibilityScoreMap.head("commute")("transit"),accessibilityScoreMap(1)("commute")("transit"))
    val driveSecondaryValues = Seq(accessibilityScoreMap.head("secondary")("drive"),accessibilityScoreMap(1)("secondary")("drive"))
    val transitSecondaryValues = Seq(accessibilityScoreMap.head("secondary")("transit"),accessibilityScoreMap(1)("secondary")("transit"))

    val driveWorkAccess = getAccessibilityScoreComponent("drive","commute")
    val transitWorkAccess = getAccessibilityScoreComponent("transit","commute")
    val driveSecondaryAccess = getAccessibilityScoreComponent("drive","secondary")
    val transitSecondaryAccess = getAccessibilityScoreComponent("transit","secondary")

    driveWorkAccess.evaluate(driveWorkValues.tail.head,driveWorkValues.head)
    transitWorkAccess.evaluate(transitWorkValues.tail.head,transitWorkValues.head)
    driveSecondaryAccess.evaluate(driveSecondaryValues.tail.head,driveSecondaryValues.head)
    transitSecondaryAccess.evaluate(transitSecondaryValues.tail.head,transitSecondaryValues.head)
    summaryTable.addRow(driveWorkAccess)+summaryTable.addRow(transitWorkAccess)+summaryTable.addRow(driveSecondaryAccess)+summaryTable.addRow(transitSecondaryAccess)
  }

  def scoreSubmission(): BigDecimal = {
    println("SCORE SUBMISSION")
    val allScoringFunctions = simpleScoringFunctions ++: Set(compoundStatFields(CostBenefitAnalysis), compoundStatFields(Sustainability_GHG), compoundStatFields(Sustainability_PM), compoundStatFields(MotorizedVehicleMilesTraveled_total))
    println("CALC RESULT")
    val result = allScoringFunctions
      .foldLeft(accessibilityScores)((a, fn) => {
        fn.evaluate(bauDataTable, submissionDataTable)
        a + summaryTable.addRow(fn)
      }) / (allScoringFunctions.size+4)
    println("DONE")
    summaryTable.addRow("Submission Score", "", "", "", "", result.toString)
    result
  }


  def getRawScoreSummaryMap: Map[String, java.lang.Double] = {
    summaryTable.getScoreSummaryMap
  }

  def outputSummary(): Unit = {
    summaryTable.outputSummaryTable(Paths
      .get(competitionServices.SUBMISSION_OUTPUT_ROOT_NAME,
        CompetitionServices.COMPETITION_ROOT,
        "submissionScores.csv")
      .toString)
  }
}

object SubmissionEvaluator {

  /**
    * Perform MSA over a summary stats datatable for given number of BEAM
    * iterations.
    *
    * Averages values from of summary stats from previous iterations.
    *
    * @param dataTableName                       Name of data table used (e.g., "BAU DF")
    * @param summaryStats                        Summary statistics collected thus far for simulation run
    * @param submissionScoreMSAOverNumberOfIters Score of submission
    * @return
    */
  def summaryStatsMSA(dataTableName: String, summaryStats: DataTable, submissionScoreMSAOverNumberOfIters: Int): DataTable = {

    if (submissionScoreMSAOverNumberOfIters > 0) {
      val msaIters = Math.min(submissionScoreMSAOverNumberOfIters, summaryStats.rowCount)
      val columns = scala.collection.mutable.ArrayBuffer.empty[DataColumn[Double]]

      summaryStats.columns.foreach { col =>
        val average: Double = summaryStats.takeRight(msaIters).map(x => x.get(col.name).get).reduce(_.toString.toDouble + _.toString.toDouble).toString.toDouble / msaIters
        val doubleCol = new DataColumn[Double](col.name, List(average))
        columns += doubleCol
      }

      val dataTable = DataTable(dataTableName, columns)
      dataTable.get
    } else {
      summaryStats
    }
  }

  private def loadBAUDataTable(dataTableName: String, statsPath: Path, submissionScoreMSAOverNumberOfIters: Int): DataTable = {
    val fields: Map[String, Double.type] = Source.fromFile(statsPath.toString).getLines().next().split(",").map { x => x -> Double }.toMap
    val summaryStats = loadDblDataTable(fields, statsPath, dataTableName)
    SubmissionEvaluator.summaryStatsMSA(dataTableName, summaryStats, submissionScoreMSAOverNumberOfIters)
  }

  private def loadSubmissionDataTable(dataTableName: String, statsPath: Path, submissionScoreMSAOverNumberOfIters: Int, vehStatsPath: Path, vehicleTypes: TrieMap[Id[BeamVehicleType], BeamVehicleType]): DataTable = {
    val fields: Map[String, Double.type] = Source.fromFile(statsPath.toString).getLines().next().split(",").map { x => x -> Double }.toMap
    val vehFields: Map[String, Double.type] = Source.fromFile(vehStatsPath.toString).getLines().next().split(",").map { x => x-> Double }.toMap
    val summaryVehicleStats = loadDblDataTable(vehFields, vehStatsPath, "vehicleStatsDf")
    val summaryStats = processVehicleSummaryStats(loadDblDataTable(fields, statsPath, dataTableName), summaryVehicleStats, vehicleTypes)
    SubmissionEvaluator.summaryStatsMSA(dataTableName, summaryStats, submissionScoreMSAOverNumberOfIters)
  }

  private def processVehicleSummaryStats(summaryStats: DataTable, summaryVehicleStats: DataTable, vehicleTypes: TrieMap[Id[BeamVehicleType], BeamVehicleType]): DataTable = {
    /** add columns to summaryStats dataTable for VMT by fuelType & mode
    **/
    val vmtGas = new DataColumn[Double] (MotorizedVehicleMilesTraveled.withColumnPrefix("Gasoline"),
      (0 to summaryStats.length-1).map{i => sumVMTByFuel(summaryVehicleStats, i, FuelType.Gasoline ,getMapFuelTypeStrings(vehicleTypes))})
    val vmtDiesel = new DataColumn[Double] (MotorizedVehicleMilesTraveled.withColumnPrefix("Diesel"),
      (0 to summaryStats.length-1).map(i => sumVMTByFuel(summaryVehicleStats, i, FuelType.Diesel ,getMapFuelTypeStrings(vehicleTypes))))
    val vmtCar = new DataColumn[Double] (MotorizedVehicleMilesTraveled.withColumnPrefix("Car"),
      (0 to summaryStats.length-1).map(i => sumVMTByMode(summaryVehicleStats, i, "CAR")))
    val vmtBus = new DataColumn[Double] (MotorizedVehicleMilesTraveled.withColumnPrefix("BUS"),
      (0 to summaryStats.length-1).map(i => sumVMTByMode(summaryVehicleStats, i, "BUS")))
    val vmtBike = new DataColumn[Double] (MotorizedVehicleMilesTraveled.withColumnPrefix("BIKE"),
      (0 to summaryStats.length-1).map(i => sumVMTByMode(summaryVehicleStats, i, "BIKE")))

    val newStatsDf = addColumn(summaryStats, vmtGas)
    val newStatsDf_2 = addColumn(newStatsDf, vmtDiesel)
    val newStatsDf_3 = addColumn(newStatsDf_2, vmtCar)
    val newStatsDf_4 = addColumn(newStatsDf_3, vmtBus)
    val newStatsDf_5 = addColumn(newStatsDf_4, vmtBike)

  newStatsDf_5
  }

  private def addColumn(dT: DataTable, column: DataColumn[Double]): DataTable = {
    val updatedTable = dT.columns.add(column)

    updatedTable.get
  }


  private def sumVMTByMode(df: DataTable, iter: Integer, modeType: String): Double = {
    modeType match {
      case mt if mt.equals("CAR") => df.filter(row => 
        {(row.as[String]("vehicleType").toString.startsWith("Car") || row.as[String]("vehicleType").toString.endsWith("Car") ||
       row.as[String]("vehicleType").toString=="BEV" || row.as[String]("vehicleType").toString=="PHEV") && row.as[Double]("iteration")== iter}
      ).toDataTable.columns.get("vehicleMilesTraveled").map{x=> x.toDataColumn[Double].get.data.sum}.getOrElse(0.0)
      case mt if mt.equals("BUS")  => df.filter(row =>{row.as[String]("vehicleType").toString.contains(modeType) && row.as[Double]("iteration")== iter}).toDataTable.columns.get("vehicleMilesTraveled").map{x=> x.toDataColumn[Double].get.data.sum}.getOrElse(0.0)
      case mt if mt.equals("BIKE")  => df.filter(row =>{row.as[String]("vehicleType").toString.contains(modeType) && row.as[Double]("iteration")== iter}).toDataTable.columns.get("vehicleMilesTraveled").map{x=> x.toDataColumn[Double].get.data.sum}.getOrElse(0.0)
      case _=> 0.0
    }
  }

  private def sumVMTByFuel[T](df: DataTable, iter: Integer, fuelType: T, vehicleFuelTypes: Map[String, String]): Double = {    
      vehicleFuelTypes.map{x => if(x._2 == fuelType.toString){
      df.filter(row =>{row.as[Double]("iteration") == iter && row.as[String]("vehicleType").toString == x._1}).toDataTable.columns.get("vehicleMilesTraveled").map{x=> x.toDataColumn[Double].get.data.sum}.getOrElse(0.0)
      } else {0.0}
    }.sum
    
    
  }

  private def getMapFuelTypeStrings(mapTypes: TrieMap[Id[BeamVehicleType], BeamVehicleType]): Map[String, String]  = {
    mapTypes.map{ case(k,v) => (k.toString , v.primaryFuelType.toString)}.toMap
  }

}
