package beam.competition.inputs.impl

import beam.competition.inputs.framework.{Age, Input, InputDataHelper, StringCol}
import beam.competition.run.CompetitionServices
import beam.sim.common.{Range => CensusRange}
import com.github.martincooper.datatable.DataTable
import com.typesafe.scalalogging.LazyLogging
import com.wix.accord.dsl._
import com.wix.accord.transform.ValidationTransform

import scala.collection.JavaConverters._
import scala.util.Try

case class MassTransitFaresInput(agencyId: String,
                                 routeId: String,
                                 age: CensusRange,
                                 amount: BigDecimal) extends Input {

  override val id: String = s"$agencyId-$routeId"
  val hasRouteId: Boolean = routeId.nonEmpty
}

object MassTransitFaresInput extends LazyLogging {
  /**
    * Constructor for a single raw massTransitFare data from a single csv row record.
    *
    * The amount is preferably a [[Double double]]; however,
    * if it is an [[Int int]], then it will still be processed correctly. At least one of {age,agencyId} must be present
    * for a massTransitFare to be applied (i.e., we won't apply an incentive to the entire population by default, but
    * you don't have to specify both values for this to be valid.
    *
    * @param agencyId The optionally applicable agency [[String agencyId]]
    * @param routeId  The optionally applicable route [[String routeId]] of specified agency (if present then agency should be specified)
    * @param age      The applicable age [[CensusRange range]] (between 0 and 120, exclusive) for the massTransitFare.
    * @param amount   The value of the massTransitFare itself.
    * @return Fully populated massTransitFare object.
    */
  def apply(agencyId: String,
            routeId: String,
            age: String,
            amount: String): MassTransitFaresInput = {
    if (age.contains('(') || age.contains(')') || age.contains(',')) {
      logger.error("Improperly formatted census range inputs ('age'). We no longer use inclusive '(',')' brackets. Also, make sure you are using ':' not ',' to separate endpoints!")
      System.exit(1)
      throw new RuntimeException()
    }
    new MassTransitFaresInput(agencyId,
      routeId,
      CensusRange(age),
      (Try(amount.toDouble) match {
        case scala.util.Success(value) => Try(BigDecimal(value))
        case scala.util.Failure(_) => Try(BigDecimal(amount.toInt))
      }).getOrElse(BigDecimal(0.0)))
  }
}

case class MassTransitFaresInputDataHelper()(implicit val competitionServices: CompetitionServices)
  extends InputDataHelper[MassTransitFaresInput] {

  override val fields: Fields = Map(
    "agencyId" -> StringCol,
    "routeId" -> StringCol,
    "age" -> StringCol,
    "amount" -> StringCol
  )

  override def convertDataTable(dataTable: DataTable): Seq[MassTransitFaresInput] = {
    dataTable.map(
      row =>
        MassTransitFaresInput(
          row(0).toString,
          row(1).toString,
          row(2).toString,
          row(3).toString))
  }

  implicit val inputValidator
  : ValidationTransform.TransformedValidator[MassTransitFaresInput] =
    validator[MassTransitFaresInput] { p =>
      p.amount as "the mass transit fare ('amount)" should be > BigDecimal(0.0)
      p.amount as "the mass transit fare ('amount')" should be <= BigDecimal(10.0)
      p.age.lowerBound as "age field ('age') lower endpoint" is in((Age.minValue until (Age.maxValue,Age.minInterval)).toSet)
      p.age.upperBound as "age field ('age') upper endpoint" is in((Age.minInterval to (Age.maxValue,Age.minInterval)).toSet)
      p.age.lowerBound < p.age.upperBound as "age field  ('age') lower endpoint should be less than upper endpoint" is true
      p.agencyId as "the agency id ('agency_id')" is in(competitionServices.gtfsFeeds.flatMap { feed => feed.agency.asScala.keys }.toSet)
    }
}
