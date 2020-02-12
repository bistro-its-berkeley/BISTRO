package beam.competition.inputs

import beam.agentsim.agents.vehicles.FuelType.FuelType
import beam.competition.CompetitionTestUtils
import beam.competition.inputs.framework.Input
import beam.competition.run.CompetitionServices
import beam.utils.BeamVehicleUtils.{readBeamVehicleTypeFile, readFuelTypeFile}
import com.conveyal.gtfs.GTFSFeed
import com.wix.accord.scalatest.ResultMatchers
import com.wix.accord.transform.ValidationTransform
import org.mockito.Mockito._
import org.scalatest.mockito.MockitoSugar
import org.scalatest.prop.PropertyChecks
import org.scalatest.{Matchers, WordSpec}

import scala.collection.concurrent.TrieMap


trait InputSpecHelper[T <: Input] extends WordSpec with CompetitionTestUtils with MockitoSugar with PropertyChecks with Matchers with ResultMatchers {

  // Set up mock services for testing
  private val gtfsFeeds = CompetitionServices.getAllGTFSFiles("fixed-data/sioux_faux/r5").map(file => GTFSFeed.fromFile(file.toString))
  private val fuelTypes: TrieMap[FuelType, Double] =
    TrieMap(readFuelTypeFile("fixed-data/sioux_faux/beamFuelTypes.csv").toSeq: _*)


  implicit val services: CompetitionServices = mock[CompetitionServices](withSettings().stubOnly())
  when(services.gtfsFeeds).thenReturn(gtfsFeeds)
  when(services.vehicleTypes).thenReturn(TrieMap(
    readBeamVehicleTypeFile("fixed-data/sioux_faux/sample/15k/vehicleTypes.csv").toSeq: _*
  ))


  when(services.gtfsAgenciesAndRoutes).thenReturn(gtfsFeeds.map { feed: GTFSFeed =>
    (feed.agency.values.iterator().next().agency_id, feed.routes)
  }.toMap)

  implicit val singleValidator: ValidationTransform.TransformedValidator[T]

}
