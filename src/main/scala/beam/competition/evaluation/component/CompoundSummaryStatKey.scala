package beam.competition.evaluation.component

import enumeratum.{Enum, EnumEntry}

import scala.collection.immutable


/**
  * Enumerated type that defines which compound scoring functions are available.
  *
  * These identifiers refer to entries spanning multiple column names found in the
  * header of summaryStats.csv. Each identifier must have a prefix that specifies the general
  * stat category and
  */
sealed trait CompoundSummaryStatKey extends EnumEntry {
  val columnPrefix: String

  def withColumnPrefix(input: String): String = {
    s"${columnPrefix}_$input"
  }
}

object CompoundSummaryStatKey extends Enum[CompoundSummaryStatKey] {

  val values: immutable.IndexedSeq[CompoundSummaryStatKey] = findValues

  case object FuelConsumedInMJ extends CompoundSummaryStatKey {
    override val columnPrefix: String = "fuelConsumedInMJ"
  }

  case object TotalIncentive extends CompoundSummaryStatKey {
    override val columnPrefix: String = "totalIncentive"
  }

  case object VehicleHoursTraveled extends CompoundSummaryStatKey {
    override val columnPrefix: String = "vehicleHoursTraveled"
  }

  case object AgencyRevenue extends CompoundSummaryStatKey {
    override val columnPrefix: String = "agencyRevenue"
  }

  case object PersonTravelTime extends CompoundSummaryStatKey {
    override val columnPrefix: String = "personTravelTime"
  }

  case object MotorizedVehicleMilesTraveled extends CompoundSummaryStatKey {
    override val columnPrefix: String = "vehicleMilesTraveled"
  }

}

