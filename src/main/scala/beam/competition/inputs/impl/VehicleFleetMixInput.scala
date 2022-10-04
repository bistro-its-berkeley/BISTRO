package beam.competition.inputs.impl

import beam.agentsim.agents.vehicles.BeamVehicleType
import beam.competition.inputs.framework.{Input, InputDataHelper, InputReader, StringCol}
import beam.competition.run.CompetitionServices
import com.github.martincooper.datatable.DataTable
import com.github.tototoshi.csv.CSVReader
import com.wix.accord.dsl._
import com.wix.accord.transform.ValidationTransform
import org.matsim.api.core.v01.Id

import scala.collection.JavaConverters

import java.nio.file.{Paths, Files}

case class VehicleFleetMixInput(agencyId: String, routeId: String, vehicleTypeId: Id[BeamVehicleType]) extends Input {
  override val id: String = s"$agencyId-$routeId"
}

case class VehicleFleetMixInputDataHelper()(implicit val competitionServices: CompetitionServices) extends InputDataHelper[VehicleFleetMixInput] {

  override val fields: Fields = Map("agencyId" -> StringCol, "routeId" -> StringCol, "vehicleTypeId" -> StringCol)


  override def convertDataTable(dataTable: DataTable): Seq[VehicleFleetMixInput] = {
    dataTable.map(row => VehicleFleetMixInput(row(0).toString, row(1).toString, Id.create(row(2).toString, classOf[BeamVehicleType])))
  }

  override implicit val inputValidator: ValidationTransform.TransformedValidator[VehicleFleetMixInput] = validator[VehicleFleetMixInput] {
    p => {
      p.vehicleTypeId as "Vehicle Type" is in(competitionServices.vehicleTypes.keys.toSet.filterNot(id=>id.toString.contains("CAR")))
      p.agencyId as "Transit 'agency_id'" is in(competitionServices.gtfsAgenciesAndRoutes.keySet)
      if (competitionServices.gtfsAgenciesAndRoutes.keySet.contains(p.agencyId)) {
        p.routeId as s"Valid 'route_id' for agency ${p.agencyId}" is in(JavaConverters.asScalaSet(competitionServices.gtfsAgenciesAndRoutes(p.agencyId).keySet()).toSet)
      }
    }
  }
}

case class VehicleCostData(vehicleTypeId: Id[BeamVehicleType], purchasingCost: Int, operationsMaintenanceCost: Double)

object VehicleCostData {


  val fields: Map[String, Object] = Map("vehicleTypeId" -> StringCol, "purchaseCost" -> Int, "opAndMaintCost" -> Double)

  def readBeamVehicleCostsFile(costLoc: String): Map[Id[BeamVehicleType], VehicleCostData] = {
    val reader = CSVReader.open(costLoc)
    val df = InputReader.readDataTableForFields(fields, reader, "VehicleCosts")
    df.map(row => {
      val tid = Id.create(row(0).asInstanceOf[String], classOf[BeamVehicleType])

      tid -> VehicleCostData(tid, row(1).asInstanceOf[Int], row(2).asInstanceOf[Double])
    }
    ).toMap

  }
}

