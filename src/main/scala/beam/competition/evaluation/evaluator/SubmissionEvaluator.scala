package beam.competition.evaluation.evaluator

import java.nio.file.{Path, Paths}

import beam.competition.evaluation.component.ScoreComponent.ScoreComponentWeightIdentifier
import beam.competition.evaluation.component.ScoreComponent.ScoreComponentWeightIdentifier.{CostBenefitAnalysis, Sustainability_GHG, Sustainability_PM}
import beam.competition.evaluation.component.ScoreComponent.ScoreComponentWeightIdentifier.{MotorizedVehicleMilesTraveled_total}
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

case class SubmissionEvaluator @Inject()(simpleStatFields: Set[ScoreComponentWeightIdentifier],
                                         compoundStatFields: Map[ScoreComponentWeightIdentifier, CompoundScoreComponent],
                                         currentIteration: Int)
                                        (implicit val competitionServices: CompetitionServices) extends LazyLogging {

  implicit val myLogger: scalalogging.Logger = this.logger

  //TODO[saf]: Create these using a factory with score components and names specified in csv
  private val simpleScoringFunctions: Set[_ <: NormalizedScoreComponent] = simpleStatFields.map { sn => new NormalizedScoreComponent(ScoreComponentWeightIdentifier.withName(sn.entryName)) }

  private val summaryTable = SummaryTable()

  val submissionScoreMSAOverNumberOfIters: Int = BeamConfigUtils.parseFileSubstitutingInputDirectory(  competitionServices.SUBMISSION_OUTPUT_ROOT_NAME + "/beam.conf").getInt("beam.competition.submissionScoreMSAOverNumberOfIters")

  private lazy val bauDataTable: DataTable = SubmissionEvaluator.loadDataTable("bauDf", competitionServices.BAU_STATS_PATH, submissionScoreMSAOverNumberOfIters)

  private lazy val submissionDataTable: DataTable = SubmissionEvaluator.loadDataTable("submissionDf", competitionServices.SUBMISSION_STATS_PATH, submissionScoreMSAOverNumberOfIters)

  private lazy val submissionVehicleDataTable: DataTable = SubmissionEvaluator.loadVehicleDataTable("submissionVehicleDf", competitionServices.SUBMISSION_STATS_Vehicle_PATH, submissionScoreMSAOverNumberOfIters)


  private def getAccessibilityScoreComponent(modeType: String, poiType: String): NormalizedScoreComponent = {
    val accessibilityType = ScoreComponentWeightIdentifier.withName(s"$modeType${poiType.capitalize}Accessibility")
    new NormalizedScoreComponent(accessibilityType)
  }

  def accessibilityScores: BigDecimal = {

    val accessibilityScoreMap: ListBuffer[Map[String, Map[String, Double]]]
    = if (currentIteration == 1 || currentIteration == competitionServices.lastIteration) {
      new AccessibilityScoreComputation(currentIteration,competitionServices.lastIteration).runAccessibilityComputation()
    } else {
      ListBuffer(Map(
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
    }
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
    val allScoringFunctions = simpleScoringFunctions ++: Set(compoundStatFields(CostBenefitAnalysis), compoundStatFields(Sustainability_GHG), compoundStatFields(Sustainability_PM))
    val result = allScoringFunctions
      .foldLeft(accessibilityScores)((a, fn) => {
        fn.evaluate(bauDataTable, submissionDataTable)
        a + summaryTable.addRow(fn)
      }) / (allScoringFunctions.size+4)

    summaryTable.addRow("Submission Score", "", "", "", "", result.toString)
    result
  }

  def scoreVehicleSubmission(): BigDecimal = {
    val allScoringFunctions = compoundStatFields(MotorizedVehicleMilesTraveled_total)
    val result = allScoringFunctions
      .foldLeft(Option.empty[X])((a, fn) => {
        fn.evaluate(bauDataTable,submissionVehicleDataTable)
        a + summaryTable.addRow(fn)
      }) / (allScoringFunctions.size+4)

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

  def summaryVehicleStatsMSA(dataTableName: String, summaryStats: DataTable, submissionScoreMSAOverNumberOfIters: Int): DataTable = {

    if (submissionScoreMSAOverNumberOfIters > 0) {
      //*20 is for VMT as we have 20 values in 1 iter for
      val msaIters = Math.min(submissionScoreMSAOverNumberOfIters, summaryStats.rowCount)*20
      val columns = scala.collection.mutable.ArrayBuffer.empty[DataColumn[Double]]

      summaryStats.columns.foreach { col =>
        val average: Double = summaryStats.takeRight(msaIters).map(x => x.get(col.name).get).reduce(_.toString.toDouble + _.toString.toDouble).toString.toDouble / (msaIters/20)
        val doubleCol = new DataColumn[Double](col.name, List(average))
        columns += doubleCol
      }

      val dataTable = DataTable(dataTableName, columns)
      dataTable.get
    } else {
      summaryStats
    }
  }




  private def loadDataTable(dataTableName: String, statsPath: Path, submissionScoreMSAOverNumberOfIters: Int): DataTable = {
    val fields: Map[String, Double.type] = Source.fromFile(statsPath.toString).getLines().next().split(",").map { x => x -> Double }.toMap
    val summaryStats = loadDblDataTable(fields, statsPath, dataTableName)
    SubmissionEvaluator.summaryStatsMSA(dataTableName, summaryStats, submissionScoreMSAOverNumberOfIters)
  }

  private def loadVehicleDataTable(dataTableName: String, statsPath: Path, submissionScoreMSAOverNumberOfIters: Int): DataTable = {
    val fields: Map[String, Double.type] = Source.fromFile(statsPath.toString).getLines().next().split(",").map { x => x -> Double }.toMap
    val summaryStats = loadDblDataTable(fields, statsPath, dataTableName)
    SubmissionEvaluator.summaryVehicleStatsMSA(dataTableName, summaryStats, submissionScoreMSAOverNumberOfIters)
  }


}
