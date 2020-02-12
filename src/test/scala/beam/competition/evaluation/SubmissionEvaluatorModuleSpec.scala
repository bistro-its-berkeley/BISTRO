package beam.competition.evaluation

import java.nio.file.{Path, Paths}

import beam.competition.CompetitionTestHelper
import beam.competition.evaluation.component.NormalizedScoreComponent.StandardizationParams
import beam.competition.evaluation.component.ScoreComponent.ScoreComponentWeightIdentifier
import beam.competition.evaluation.evaluator.SubmissionEvaluatorModule
import beam.competition.inputs.framework.InputReader.loadDblDataTable
import beam.competition.inputs.impl.VehicleCostData.readBeamVehicleCostsFile
import beam.competition.run.CompetitionServices
import beam.utils.BeamVehicleUtils.readBeamVehicleTypeFile
import com.conveyal.gtfs.GTFSFeed
import com.github.martincooper.datatable.{DataColumn, DataTable}
import org.mockito.Mockito.when
import org.scalactic.TolerantNumerics
import org.scalatest.mockito.MockitoSugar
import org.scalatest.prop.TableDrivenPropertyChecks
import org.scalatest.{Matchers, WordSpecLike}

import scala.collection.concurrent.TrieMap
import scala.collection.immutable
import scala.io.Source

class SubmissionEvaluatorModuleSpec extends WordSpecLike with TableDrivenPropertyChecks with MockitoSugar with Matchers with CompetitionTestHelper {

  val epsilon = 1e-2f

  implicit val doubleEq = TolerantNumerics.tolerantDoubleEquality(epsilon)

  private val vehicleCosts = readBeamVehicleCostsFile(Paths.get("fixed-data/sioux_faux/vehicleCosts.csv").toString)
  private val gtfsFeeds = CompetitionServices.getAllGTFSFiles("fixed-data/sioux_faux/r5").map(file => GTFSFeed.fromFile(file.toString))

  private final val weights = {
    val lines = Source.fromFile("fixed-data/sioux_faux/scoringWeights.csv").getLines().toSeq
    val weightIndicators = lines.head.split(",").map(ScoreComponentWeightIdentifier.withName)
    val values = lines(1).split(",").map(_.toDouble)
    weightIndicators.zip(values).toMap
  }

  private final val standardizationParams = {
    val lines: immutable.Seq[Array[String]] = Source.fromFile("fixed-data/sioux_faux/standardizationParameters.csv").getLines().toVector.map(l => l.split(","))

    (for {line <- lines}
      yield {
        ScoreComponentWeightIdentifier.withName(line(0).toString) -> StandardizationParams(line(1).toDouble, line(2).toDouble)
      }).toMap

  }

  private val fuelTypes =
    TrieMap(CompetitionServices.readFuelTypeFile("fixed-data/sioux_faux/beamFuelTypes.csv").toSeq: _*)

  // Set up mock services for testing
  implicit val services: CompetitionServices = mock[CompetitionServices]

  when(services.gtfsFeeds).thenReturn(gtfsFeeds)
//
//  when(services.vehicleTypes).thenReturn(TrieMap(
//    readBeamVehicleTypeFile("fixed-data/sioux_faux/sample/15k/vehicleTypes.csv", fuelTypes.map { case (k, v) => k -> v.cost }.toMap).toSeq: _*
//  ))

  when(services.gtfsAgenciesAndRoutes).thenReturn(gtfsFeeds.map { feed: GTFSFeed =>
    (feed.agency.values.iterator().next().agency_id, feed.routes)
  }.toMap)

  when(services.weights).thenReturn(weights)

  when(services.standardizationParams).thenReturn(standardizationParams)

  when(services.fuelTypes).thenReturn(fuelTypes)

  when(services.VEHICLE_COSTS).thenReturn(vehicleCosts)

  def loadDataTable(statsPath: Path, dataTableName: String): DataTable = {
    val fields: Map[String, Double.type] = Source.fromFile(statsPath.toString).getLines().next().split(",").map { x => x -> Double }.toMap
    loadDblDataTable(fields, statsPath, dataTableName)
  }

  "Submission evaluator" should {

    "evaluate dummy data" in {
      val inputRootBau: Path = resourcesDirectory.resolve("test/submissionEvaluatorModuleSpec/bau/summaryStats/summaryStats-1k.csv")
      val inputRootSub: Path = resourcesDirectory.resolve("test/submissionEvaluatorModuleSpec/sub/summaryStats/summaryStats-1k.csv")
      val bauDfData: DataTable = loadDataTable(inputRootBau, "bauTest")
      val subDfData: DataTable = loadDataTable(inputRootSub, "subTest")

      (0 until bauDfData.rowCount).map { idx =>
        val bauData = DataTable(s"$idx", bauDfData(idx).valueMap.map { x => new DataColumn[Double](x._1, Iterable[Double](x._2.asInstanceOf[Double])) }).get
        val subData = DataTable(s"$idx", subDfData(idx).valueMap.map { x => new DataColumn[Double](x._1, Iterable[Double](x._2.asInstanceOf[Double])) }).get
        assert(new SubmissionEvaluatorModule().costBenefitAnalysisComponent.evaluate(bauData, subData).rawScore === subData(0).get("financialSustainability_rawScore").get.asInstanceOf[Double])
      }

    }
  }
}
