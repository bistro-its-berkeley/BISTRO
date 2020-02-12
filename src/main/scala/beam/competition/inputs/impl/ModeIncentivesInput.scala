package beam.competition.inputs.impl

import beam.agentsim.agents.choice.mode.ModeIncentive
import beam.competition.inputs.framework._
import beam.competition.run.CompetitionServices
import beam.router.Modes.BeamMode
import beam.router.Modes.BeamMode.{DRIVE_TRANSIT, RIDE_HAIL, WALK_TRANSIT}
import beam.sim.common.{Range => CensusRange}
import com.github.martincooper.datatable.DataTable
import com.typesafe.scalalogging.LazyLogging
import com.wix.accord.dsl._
import com.wix.accord.transform.ValidationTransform

import scala.util.Try

case class ModeIncentivesInput(mode: BeamMode,
                               age: CensusRange,
                               income: CensusRange,
                               amount: BigDecimal)
  extends Input {
  override val id: String = ""
}

object ModeIncentivesInput extends LazyLogging {
  /**
    * Constructor for a single raw [[ModeIncentive]] data from a single csv row record.
    *
    * The amount is preferably a [[Double double]]; however,
    * if it is an [[Int int]], then it will still be processed correctly. At least one of {age,income} must be present
    * for a incentive to be applied (i.e., we won't apply a incentive to the entire population by default, but
    * you don't have to specify both values for this to be valid.
    *
    * @param mode   The [[BeamMode mode]] selected for the [[ModeIncentive incentive]]
    * @param age    The applicable age [[CensusRange range]] (between 0 and 120, exclusive) for the [[ModeIncentive incentive]].
    * @param income The applicable income [[CensusRange range]] (greater than 0) for the incentive.
    * @param amount The value of the [[ModeIncentive incentive]] itself.
    * @return Fully populated [[ModeIncentive incentive]] object.
    */
  def apply(mode: String,
            age: String,
            income: String,
            amount: String): ModeIncentivesInput = {
    if (age.contains('(') || age.contains(')') || income.contains('(') || income.contains(')') || income.contains(',') || age.contains(',')) {
      logger.error("Improperly formatted census range inputs. We no longer use inclusive '(',')' brackets.")
      System.exit(1)
      throw new RuntimeException()
    }
    new ModeIncentivesInput(
      if (mode.equals("OnDemand_ride")) {
        BeamMode.RIDE_HAIL
      }
      else if (BeamMode.withValueOpt(mode).isEmpty) {
        logger.error("Error in ModeIncentivesInput.csv: Mode %s is not a supported BEAM mode!".format(mode))
        System.exit(1)
        throw new RuntimeException()
      }
      else {
        BeamMode.fromString(mode).get
      },
      CensusRange(age),
      CensusRange(income),
      (Try(amount.toDouble) match {
        case scala.util.Success(value) => Try(BigDecimal(value))
        case scala.util.Failure(_) => Try(BigDecimal(amount.toInt))
      }).getOrElse(BigDecimal(0.0))
    )
  }
}

case class ModeIncentivesInputDataHelper()(
  implicit val competitionServices: CompetitionServices)
  extends InputDataHelper[ModeIncentivesInput] {

  override val fields: Fields = Map(
    "mode" -> StringCol,
    "age" -> StringCol,
    "income" -> StringCol,
    "amount" -> StringCol
  )

  override def convertDataTable(
                                 dataTable: DataTable): Seq[ModeIncentivesInput] = {
    dataTable.map(
      row =>
        ModeIncentivesInput(row(0).toString,
          row(1).toString,
          row(2).toString,
          row(3).toString))
  }

  implicit val inputValidator
  : ValidationTransform.TransformedValidator[ModeIncentivesInput] =
    validator[ModeIncentivesInput] { p =>
      p.mode as "incentivized mode ('mode')" is in(WALK_TRANSIT, DRIVE_TRANSIT, RIDE_HAIL)
      p.amount as "incentive amount ('amount')" should be > BigDecimal(0.0)
      p.amount as "incentive amount ('amount')" should be <= BigDecimal(50.0)
      p.age.lowerBound as "age field ('age') lower endpoint" is in((Age.minValue until (Age.maxValue,Age.minInterval)).toSet)
      p.age.upperBound as "age field ('age') upper endpoint" is in((Age.minInterval to (Age.maxValue,Age.minInterval)).toSet)
      p.income.lowerBound as "income field ('income') lower endpoint" is in((Income.minValue until (Income.maxValue, Income.minInterval)).toSet)
      (p.income.upperBound as "income field ('income') upper endpoint" is in((Income.minInterval-1 until (Income.maxValue-Income.minInterval,Income.minInterval)).toSet)) or (p.income.upperBound is equalTo(Income.maxValue))
    }

}
