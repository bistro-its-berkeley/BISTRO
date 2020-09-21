package beam.competition.evaluation.evaluator

import beam.agentsim.agents.vehicles.{BeamVehicleType, FuelType}
import beam.competition.evaluation.IterationScoreComponentPlottingListener
import beam.competition.evaluation.component.CompoundScoreComponent
import beam.competition.evaluation.component.CompoundSummaryStatKey._
import beam.competition.evaluation.component.ScoreComponent.ScoreComponentWeightIdentifier
import beam.competition.evaluation.component.ScoreComponent.ScoreComponentWeightIdentifier._
import beam.competition.run.CompetitionServices
import com.github.martincooper.datatable.DataTable
import com.google.inject.AbstractModule
import net.codingwell.scalaguice.{ScalaMapBinder, ScalaModule, ScalaMultibinder}
import org.matsim.api.core.v01.Id

import scala.collection.concurrent.TrieMap

case class SubmissionEvaluatorModule(implicit competitionServices: CompetitionServices) extends AbstractModule with ScalaModule {

  import SubmissionEvaluatorModule.getMapTypeStrings

  private val cbaTypeStrings: Set[String] = getMapTypeStrings(competitionServices.vehicleTypes) ++ CompetitionServices.POSSIBLE_INCENTIVE_MODES ++ competitionServices.gtfsAgenciesAndRoutes.keySet ++ competitionServices.fuelTypes.keySet.map(_.toString)

  val ghgEmissionsSustainabilityComponent: CompoundScoreComponent = new CompoundScoreComponent(Sustainability_GHG, getMapTypeStrings(competitionServices.vehicleTypes))(competitionServices) {

    override def transformation(vehicleType: String, source: DataTable): Double = {
      vehicleType match {
        case vt if vt.contains("BUS") => source.columns.get(FuelConsumedInMJ.withColumnPrefix("Diesel")).map { x => x.toDataColumn[Double].get.data.last * competitionServices.fuelTypes(FuelType.Diesel).gramsGHGePerGallon }.getOrElse(0.0)
        case vt if vt.equals("Car") => source.columns.get(FuelConsumedInMJ.withColumnPrefix("Gasoline")).map { x => x.toDataColumn[Double].get.data.last * competitionServices.fuelTypes(FuelType.Gasoline).gramsGHGePerGallon }.getOrElse(0.0)
        //        case vt if vt.contains("CAR") => source.columns.get(FuelConsumedInMJ.withColumnPrefix("Gasoline")).map { x => x.toDataColumn[Double].get.data.last * competitionServices.fuelTypes(FuelType.Gasoline).gramsGHGePerGallon }.getOrElse(0.0)
        case _=> 0.0
      }
    }
  }

  val pmEmissionsSustainabilityComponent: CompoundScoreComponent = new CompoundScoreComponent(Sustainability_PM, getMapTypeStrings(competitionServices.vehicleTypes))(competitionServices) {

    override def transformation(vehicleType: String, source: DataTable): Double = {
      vehicleType match {
        case vt if vt.contains("BUS") => source.columns.get(MotorizedVehicleMilesTraveled.withColumnPrefix(vt)).map { x => x.toDataColumn[Double].get.data.last * competitionServices.fuelTypes(FuelType.Diesel).pm25PerVMT  }.getOrElse(0.0)
        case vt if vt.equals("Car") => source.columns.get(MotorizedVehicleMilesTraveled.withColumnPrefix(vt)).map { x => x.toDataColumn[Double].get.data.last * competitionServices.fuelTypes(FuelType.Gasoline).pm25PerVMT  }.getOrElse(0.0)
        case _=> 0.0
      }
    }
  }

  val costBenefitAnalysisComponent: CompoundScoreComponent = new CompoundScoreComponent(CostBenefitAnalysis, cbaTypeStrings)(competitionServices) {

    override def transformation(input: String, dataTable: DataTable): Double = {
      if (!FuelType.fromString(input).equals(FuelType.Undefined)) {
        input match {
          case ft if !(FuelType.fromString(input) == FuelType.Gasoline) =>
            dataTable.columns.get(FuelConsumedInMJ.withColumnPrefix(ft.capitalize)).map { x =>
              - x.toDataColumn[Double].get.data.last * competitionServices.fuelTypes(FuelType.fromString(ft)).cost
            }.getOrElse(0.0)
          case _ => 0.0
        }
      }
      else if (competitionServices.gtfsAgenciesAndRoutes.keySet.contains(input)) {
        dataTable.columns.get(AgencyRevenue.withColumnPrefix(input)).map { x =>
          x.toDataColumn[Double].get.data.last * 1.0
        }.getOrElse(0.0)
      }
      else if (CompetitionServices.POSSIBLE_INCENTIVE_MODES.contains(input)) {
        dataTable.columns.get(TotalIncentive.withColumnPrefix(input)).map {
          x =>
            - x.toDataColumn[Double].get.data.last
        }.getOrElse(0.0)
      } else if (competitionServices.vehicleTypes.values.toVector.map(_.id.toString).filter(_.contains("BUS")).toSet.contains(input)) {
        val vtId = Id.create(input, classOf[BeamVehicleType])
        dataTable.columns.get(VehicleHoursTraveled.withColumnPrefix(input)).map { x =>
          - x.toDataColumn[Double].get.data.last *
            competitionServices.VEHICLE_COSTS(vtId).operationsMaintenanceCost
        }.getOrElse(0.0)
      }
      else {
        0.0
      }
    }
  }

  val motorizedVehicleMilesTraveledComponent: CompoundScoreComponent = new CompoundScoreComponent(MotorizedVehicleMilesTraveled_total,getMapTypeStrings(competitionServices.vehicleTypes))(competitionServices) {
    override def transformation(vehicleType: String, source: DataTable): Double = {
      vehicleType match {
        case vt if vt.equals("Car") => source.columns.get(MotorizedVehicleMilesTraveled.withColumnPrefix(vt)).map { x => x.toDataColumn[Double].get.data.last * competitionServices.fuelTypes(FuelType.Gasoline).pm25PerVMT  }.getOrElse(0.0)
        case _=> 0.0
      }
    }
  }

  override def configure(): Unit = {

    // Bind simple score components here
    val simpleScoreComponentSetBinder = ScalaMultibinder.newSetBinder[ScoreComponentWeightIdentifier](binder)
    simpleScoreComponentSetBinder.addBinding.toInstance(AverageTravelCostBurden_Work)
    //simpleScoreComponentSetBinder.addBinding.toInstance(AverageTravelCostBurden_Secondary)
    simpleScoreComponentSetBinder.addBinding.toInstance(BusCrowding)
    // FIXME: fix motorized vehicle miles traveled SAF 9/19
    // simpleScoreComponentSetBinder.addBinding.toInstance(MotorizedVehicleMilesTraveled_total)
    simpleScoreComponentSetBinder.addBinding.toInstance(AverageVehicleDelayPerPassengerTrip)

    // Bind compound score components here
    val compoundScoreComponentMapBinder = ScalaMapBinder.newMapBinder[ScoreComponentWeightIdentifier, CompoundScoreComponent](binder)
    compoundScoreComponentMapBinder.permitDuplicates()

    compoundScoreComponentMapBinder.addBinding(Sustainability_GHG).toInstance(ghgEmissionsSustainabilityComponent)

    compoundScoreComponentMapBinder.addBinding(Sustainability_PM).toInstance(pmEmissionsSustainabilityComponent)

    compoundScoreComponentMapBinder.addBinding(CostBenefitAnalysis).toInstance(costBenefitAnalysisComponent)

    compoundScoreComponentMapBinder.addBinding(MotorizedVehicleMilesTraveled_total).toInstance(motorizedVehicleMilesTraveledComponent)

    bind[CompetitionServices].toInstance(competitionServices)

    bind[SubmissionEvaluatorFactory].asEagerSingleton()

    bind[IterationScoreComponentPlottingListener].asEagerSingleton()
  }

}

object SubmissionEvaluatorModule {
  def getMapTypeStrings[T](mapTypes: TrieMap[Id[T], T]): Set[String] = mapTypes.keys.map {
    _.toString
  }.toSet
}
