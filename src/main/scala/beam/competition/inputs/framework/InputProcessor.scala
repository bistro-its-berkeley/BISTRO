package beam.competition.inputs.framework


import java.io.File
import java.text.NumberFormat

import beam.competition.inputs.impl._
import beam.competition.run.CompetitionServices
import com.wix.accord.{Failure, Result, Success}

import scala.reflect.ClassTag

case class InputProcessor()(implicit val competitionServices: CompetitionServices) extends InputValidationUtils {

  import InputProcessor._

  private val currencyFormatter: NumberFormat = java.text.NumberFormat.getCurrencyInstance

  private val inputDirectory: String = competitionServices.INPUT_DEST.toString

  private val inputReader: InputReader = InputReader(inputDirectory)

  var inputCostsMap: Map[String, BigDecimal] = Map.empty

  private var invalidInputLogged: Boolean = false



  /////////////////////////////
  // Public Method
  ////////////////////////////

  def processInputs(): Unit = {
    listFiles(inputDirectory).map(x => x.map(_.stripSuffix(".csv"))) match {
      case Right(inputStrings) =>
        // Ensure inputs specified in config match available inputs in inputFileList
        inputStrings.foreach {
          resolveAndProcessInput
        }
        if (invalidInputLogged) {
          logger.error(s"Invalid inputs. Please see ${competitionServices.SUBMISSION_OUTPUT_ROOT_NAME}/${CompetitionServices.COMPETITION_ROOT}/validation-errors.log and fix listed errors prior to resubmitting.")
          System.exit(1)
        }
      case Left(msg) =>
        logger.error(msg)
        System.exit(1)
    }
  }

  lazy val inputCosts: Map[String, BigDecimal] = {
    if (inputCostsMap.isEmpty) {
      processInputs()
    }
    inputCostsMap
  }

  /////////////////////////////
  // Private Methods
  ////////////////////////////


  def logInputsCosts(): Unit = {
    var totalValue = 0.0
    inputCostsMap.foreach { case (inpName, value) =>
      totalValue += value.toDouble
      logger.info(s"\n\nCost of $inpName: ${currencyFormatter.format(value)}\n")
    }
    logger.info(s"\n\n -------- Total Cost of Policies: ${currencyFormatter.format(totalValue)} --------------  \n")
  }

  private def resolveAndProcessInput(inputString: String): Unit = {
    inputString match {
      case "ModeIncentives" => processInput(ModeIncentivesInputDataHelper())
      case "MassTransitFares" => processInput(MassTransitFaresInputDataHelper())
      case "FrequencyAdjustment" => processInput(FrequencyAdjustmentInputDataHelper())
      // RoadPricing not permitted yet
      case "RoadPricing" => processInput(RoadPricingInputDataHelper(competitionServices))
      case "VehicleFleetMix" => processInput(VehicleFleetMixInputDataHelper())
      case ".DS_Store" => logger.debug(".DS_Store found in submission-input directory, ignoring.")
      case anyOtherName: String => logger.error(s"Invalid file, $anyOtherName found in input directory!")
    }
  }

  private def processInput[T <: Input : ClassTag](inputDataHelper: InputDataHelper[T]): Unit = {
    val inputSet: Seq[T] = inputReader.readInput(inputDataHelper)
    if (inputSet.nonEmpty) {
      val result: Result = inputDataHelper.validateInputs(inputSet)
      result match {
        case Success => inputCostsMap += inputDataHelper.name -> inputDataHelper.cost(inputSet)
        case Failure(violations) => logViolations(inputDataHelper.name, violations)
          invalidInputLogged = true
      }
    }
  }

}

object InputProcessor {
  def listFiles(inputDirectory: String): Either[String, Set[String]] = {
    val file = new File(inputDirectory).toPath
      .toFile
    if (file.isDirectory)
      Right(file.listFiles.map(f => {
        f.getName
      }).toSet)
    else
      Left("Invalid input directory!")
  }
}
