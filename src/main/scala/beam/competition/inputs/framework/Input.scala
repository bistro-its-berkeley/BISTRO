package beam.competition.inputs.framework

import beam.competition.run.CompetitionServices
import com.github.martincooper.datatable.DataTable
import com.typesafe.scalalogging.LazyLogging
import com.wix.accord._
import com.wix.accord.dsl._
import com.wix.accord.transform.ValidationTransform

import scala.reflect.ClassTag

trait Input {
  val id: String
}

trait InputDataHelper[T <: Input] extends LazyLogging {
  type Fields = Map[String, Object]

  val fields: Fields

  implicit val inputValidator: ValidationTransform.TransformedValidator[T]

  implicit val inputSeqValidator
    : ValidationTransform.TransformedValidator[Seq[T]] = validator[Seq[T]] {
    inputSeq =>
      inputSeq.map {
        _.id
      } is notNull
  }

  implicit val competitionServices: CompetitionServices

  def name(implicit tag: ClassTag[T]): String = tag.runtimeClass.getSimpleName

  def cost(input: Seq[T]): BigDecimal = 0.0

  def convertDataTable(dataTable: DataTable): Seq[T]

  def validateEach(inputs: Seq[T]): Result = {

    val failures = inputs
      .map { input: T =>
        {
          validate(input)
        }
      }
      .flatMap { x =>
        if (x.isFailure) x.toFailure.get.violations else Set[Violation]()
      }
      .toSet

    if (failures.isEmpty) {
      Success
    } else {
      Failure(failures)
    }
  }

  def validateInputs(inputs: Seq[T]): Result = {
    validateEach(inputs) and validate(inputs)
  }

}

object InputDataHelper {
  private[this] def areUnique[A](seq: Seq[A], errorMessage: String): Result = {
    if (seq.size == seq.distinct.size) Success
    else Failure(Set(RuleViolation(seq, errorMessage)))
  }

  def elementsAreUnique[A](
      errorMessage: String = "Elements must be unique."): Validator[Seq[A]] = {
    seq: Seq[A] =>
      areUnique(seq, errorMessage)
  }
}
