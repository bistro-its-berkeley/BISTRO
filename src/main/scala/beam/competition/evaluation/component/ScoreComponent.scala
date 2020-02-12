package beam.competition.evaluation.component

import beam.competition.evaluation.component
import beam.competition.evaluation.component.ScoreComponent.ScoreComponentWeightIdentifier
import com.github.martincooper.datatable.{DataColumn, DataTable, GenericColumn}
import enumeratum.EnumEntry.Uncapitalised
import enumeratum._

import scala.collection.immutable
import scala.reflect.runtime.universe._

/**
  * Basic marker trait for functions that compute scoring components.
  */
trait ScoreComponent {
  val scoreComponentWeightIdentifier: ScoreComponentWeightIdentifier
  val weight: Double

  import ScoreComponent._

  var rawScore: Double = Double.NaN
  var ans: Double = Double.NaN

  /**
    * Convenience method to evaluate the [[component]] when it is associated
    * with appropriate business as usual (BAU) and
    *
    * @param bauDf        The BAU [[DataTable]] representing summary stats for the status quo simulation scenario case.
    * @param submissionDf The Submission [[DataTable]] representing the summary stats for the policy simulation scenario case.
    * @return the evaluated score
    */
  def evaluate(bauDf: DataTable, submissionDf: DataTable): ScoreComponent = {
    val bauScore: Double = prepData(bauDf)
    val submissionScore: Double = prepData(submissionDf)
    evaluate(bauScore, submissionScore)
    this
  }

  def evaluate(bauScore: Double, submissionScore: Double): ScoreComponent

  def prepData(source: DataTable): Double = {
    (source |@|[Double] scoreComponentWeightIdentifier).last
  }
}


object ScoreComponent {

  def heavyside(metric: Double): Int = {
    if (metric >= 0) 1 else 0
  }

  /**
    * Parametric utility syntax to simplify getting data out of a type-parametric
    * column
    *
    * @param df a [[DataTable]]
    */
  implicit class DataVectorForName(df: DataTable) {
    /**
      * Single function method for data retrieval from [[DataColumn[T]].
      *
      * @param scoreComponentWeightIdentifier The identifier indexing into the [[DataTable]] using its
      *                                       shortName
      * @tparam T The type to parametrize on
      * @return
      */
    def |@|[T: TypeTag](scoreComponentWeightIdentifier: ScoreComponentWeightIdentifier): Vector[T] = {

      (for {
        dfCol: GenericColumn <- df.columns.get(scoreComponentWeightIdentifier.shortName)
        dfDbl: DataColumn[T] <- dfCol.toDataColumn[T]
      } yield dfDbl.data) match {
        case scala.util.Success(value) => value
        case scala.util.Failure(exception) => throw exception
      }
    }
  }


  //TODO: Implement below to reduce complicated Map traversals
  trait ScoreComponentIdentifier {
    val shortName: String
    val longName: String
    val tau = 1
  }

  /**
    * Subclasses of this [[EnumEntry]] comprise individual scoring components.
    *
    * That is, these identifiers refer to single columns names found in the header of summaryStats.csv and
    * are not part of a composite scoring component, which are instead identified using
    * [[CompoundSummaryStatKey]].
    */
  sealed trait ScoreComponentWeightIdentifier extends EnumEntry with Uncapitalised with ScoreComponentIdentifier {
    override val shortName: String = entryName

  }

  object ScoreComponentWeightIdentifier extends Enum[ScoreComponentWeightIdentifier] {

    val values: immutable.IndexedSeq[ScoreComponentWeightIdentifier] = findValues

    case object CostBenefitAnalysis extends ScoreComponentWeightIdentifier {
      override val longName: String = "Level of service: costs and benefits"
    }

    case object AverageVehicleDelayPerPassengerTrip extends ScoreComponentWeightIdentifier {
      override val longName: String = "Congestion: average vehicle delay per passenger trip"
    }

    case object DriveWorkAccessibility extends ScoreComponentWeightIdentifier {
      override val longName: String =  "Accessibility: number of work locations accessible by car within 15 minutes"
    }

    case object DriveCommuteAccessibility extends ScoreComponentWeightIdentifier {
      override val longName: String =  "Accessibility: number of commute locations accessible by car within 15 minutes"
    }

    case object DriveSecondaryAccessibility extends ScoreComponentWeightIdentifier {
      override val longName: String = "Accessibility: number of secondary locations accessible by car within 15 minutes"
    }

    case object TransitWorkAccessibility extends ScoreComponentWeightIdentifier {
      override val longName: String = "Accessibility: number of work locations accessible by transit within 15 minutes"
    }

    case object TransitCommuteAccessibility extends ScoreComponentWeightIdentifier {
      override val longName: String = "Accessibility: number of commute locations accessible by transit within 15 minutes"
    }

    case object TransitSecondaryAccessibility extends ScoreComponentWeightIdentifier {
      override val longName: String = "Accessibility: number of secondary locations accessible by transit within 15 minutes"
    }

    case object MotorizedVehicleMilesTraveled_total extends ScoreComponentWeightIdentifier {
      override val longName: String = "Congestion: total vehicle miles traveled"
    }

    case object BusCrowding extends ScoreComponentWeightIdentifier{
      override val longName: String = "Level of service: average bus crowding experienced"
    }

    case object AverageTravelCostBurden_Work extends ScoreComponentWeightIdentifier{
      override val shortName: String = "averageTripExpenditure_Work"
      override val longName = "Equity: average travel cost burden - work"
    }

    case object AverageTravelCostBurden_Secondary extends ScoreComponentWeightIdentifier{
      override val shortName: String = "averageTripExpenditure_Secondary"
      override val longName: String = "Equity: average travel cost burden -  secondary"
    }

    case object Sustainability_GHG extends ScoreComponentWeightIdentifier {
      override val longName: String = "Sustainability: Total grams GHGe Emissions"
    }

    case object Sustainability_PM extends ScoreComponentWeightIdentifier {
      override val longName: String = "Sustainability: Total grams PM 2.5 Emitted"
    }

  }

}
