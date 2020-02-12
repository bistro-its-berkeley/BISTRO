package beam.competition.inputs.impl

import beam.sim.common.{Range=>CensusRange}
import beam.competition.inputs.framework.{Input, InputDataHelper, StringCol}
import beam.competition.run.CompetitionServices
import beam.sim.BeamServicesImpl
import com.github.martincooper.datatable.DataTable
import com.wix.accord.dsl._
import com.wix.accord.transform.ValidationTransform
import org.matsim.api.core.v01.Id
import org.matsim.api.core.v01.network.{Link, Network}

import scala.collection.{JavaConverters, mutable}

case class RoadPricingInput(linkId: Id[Link], toll: Double, timeRange: CensusRange) extends Input {
  override val id: String = s"${linkId.toString}"
}

// If there are overlapping times on the same link, then add amounts during those times.
case class RoadPricingInputDataHelper(implicit val competitionServices: CompetitionServices) extends InputDataHelper[RoadPricingInput] {

  val networkLinks: mutable.Map[Id[Link], _ <: Link] = JavaConverters.mapAsScalaMap(competitionServices.beamServices.asInstanceOf[BeamServicesImpl].injector.getInstance(classOf[Network]).getLinks)


  override val fields: Fields = Map(
    "linkId" -> StringCol,
    "toll" -> Double,
    "timeRange" -> StringCol)

  override def convertDataTable(dataTable: DataTable): Seq[RoadPricingInput] = {
    dataTable.map(
      row =>
        RoadPricingInput(Id.createLinkId(row(0).toString), Option(row(1)).fold(0.0D)(x => x.toString.toDouble), CensusRange(row(2).toString))
    )
  }

  override implicit val inputValidator: ValidationTransform.TransformedValidator[RoadPricingInput] = validator[RoadPricingInput] {
    rpi =>
      rpi.linkId is in(networkLinks.keys.toSet) // Make sure link is network
      rpi.toll should be >= 0.0D // Ensure only positive tolls
      rpi.timeRange.lowerBound is within(0 to 23)
      rpi.timeRange.upperBound is within(1 to 24) // must be at some hour during day
  }
}
