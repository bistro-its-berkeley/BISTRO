package beam.competition.run

import java.io.File
import java.nio.file.Paths
import java.text.NumberFormat
import java.util.concurrent.TimeUnit

import awscala.Region
import awscala.s3.S3
import beam.competition.aicrowd._
import beam.competition.evaluation.IterationScoreComponentPlottingListener
import beam.competition.evaluation.evaluator.{SubmissionEvaluatorFactory, SubmissionEvaluatorModule}
import beam.competition.inputs.framework.InputProcessor
import beam.competition.run.statsreporter.SimStateReportingEventsListener
import beam.competition.utils.MiscUtils
import beam.competition.visualization.{LinkStatCsvSpatialConversion, PopulationCsvSpatialConversion}
import beam.router.r5.NetworkCoordinator
import beam.sim.config.BeamConfig
import beam.sim.{BeamHelper, BeamScenario, BeamServices, BeamWarmStart}
import beam.utils.BeamConfigUtils
import cats.implicits._
import com.google.inject
import com.typesafe.config.{ConfigFactory, Config => TypesafeConfig}
import net.codingwell.scalaguice.InjectorExtensions._
import org.apache.commons.io.FileUtils
import org.matsim.core.api.experimental.events.EventsManager
import org.matsim.core.config.{Config => MatsimConfig}
import org.matsim.core.controler.ControlerListenerManagerImpl
import org.matsim.core.scenario.MutableScenario

import scala.collection.JavaConverters._
import scala.language.higherKinds

case class Arguments(
                      scenario: Option[String] = None,
                      subScenario: Option[String] = None,
                      config: Option[TypesafeConfig] = None,
                      configLocation: Option[String] = None,
                      sampleSize: Option[String] = None,
                      iterations: Option[String] = None,
                      withoutWarmStart: Boolean = true,
                      s3Location: Option[String] = None,
                      processEvents: Boolean = false
                    )

trait CompetitionHelper extends BeamHelper {

  val numberFormatter: NumberFormat = java.text.NumberFormat.getInstance

  var runStateMonitor: RunStateMonitor = _

  var processEvents: Boolean = false

  private val argsParser = new scopt.OptionParser[Arguments]("beam") {
    opt[String]("config")
      .action(
        (value, args) =>
          args.copy(
            config = Some(BeamConfigUtils.parseFileSubstitutingInputDirectory(value)),
            configLocation = Option(value)
          )
      )
      .validate(
        value =>
          if (value.trim.isEmpty) failure("config location cannot be empty")
          else success
      )
      .text("Location of the beam config file")
    opt[String]("scenario")
      .action(
        (value, args) => {
          if (value.contains("/")) {
            val tmp: Array[String] = value.split("/")
            val (sf, sc) = (tmp.head, tmp.reverse.head)
            args.copy(scenario = Some(sf.trim.toLowerCase), subScenario = Some(sc))
          } else {
            args.copy(scenario = Some(value.trim.toLowerCase), subScenario = None)
          }
        }
      )
      .validate(
        value =>
          if (value.contains("sioux_faux") || value.contains("sf_light"))
            success
          else failure("Wrong scenario name"))
      .text("Scenario name")
    opt[String]("sample-size")
      .action((value, args) => args.copy(sampleSize = Option(value)))
      .validate(
        value =>
          if (Seq("1k", "15k", "157k").contains(value.toLowerCase.trim))
            success
          else failure("sample-size cannot be empty"))
      .text("Sample size [\"1k\", \"15k\", \"157k\"]")
    opt[String]("iters")
      .action((value, args) => args.copy(iterations = Option(value)))
      .validate(value =>
        if (value.toInt > 0)
          success
        else
          failure("When specifying scenario parameters via command line, please specify a number of BEAM iterations > 0.")
      )
      .text("Number of BEAM iterations to run (1,N).")
    opt[Unit]("without-warm-start")
      .action((_, args) => args.copy(withoutWarmStart = true))
      .text("Flag to run without warm start")
    opt[String](name = "s3-input-loc")
      .action((value, args) => args.copy(s3Location = Option(value)))
      .validate(_ =>
        if (System.getenv("AWS_ACCESS_KEY_ID") != null &&
          System.getenv("AWS_BUCKET_NAME") != null &&
          System.getenv("AWS_FILE_KEY_TEMPLATE") != null &&
          System.getenv("RANDOM_SEARCH_ID") != null)
          success
        else
          failure("Environment not configured for AWS"))
      .text("Location of input files on s3 (to be downloaded and used for this run)")
    opt[Unit]("processEvents")
      .action((_, args) => args.copy(processEvents = false))
      .text("Flag to execute event processor after run (posts digested events to s3 as csvs).")
    checkConfig(
      args =>
        if (args.config.isEmpty && (args.scenario.isEmpty || args.sampleSize.isEmpty))
          failure(
            "You have to specify scenario name, number of iterations, and size or config location")
        else success
    )
  }

  def downloadInputsFromS3(s3Location: String): String = {
    implicit val s3: S3 = S3().at(Region.US_WEST_2)
    val AWS_BUCKET_NAME: String = scala.util.Properties.envOrElse("AWS_BUCKET_NAME", "false")
    val AWS_FILE_KEY_TEMPLATE: String = scala.util.Properties.envOrElse("AWS_FILE_KEY_TEMPLATE", "false")
    val RANDOM_SEARCH_ID: String = scala.util.Properties.envOrElse("RANDOM_SEARCH_ID", "false")
    val bucket = s3.bucket(AWS_BUCKET_NAME)

    val s3InputKeyPrefix = Paths.get(AWS_FILE_KEY_TEMPLATE, if (RANDOM_SEARCH_ID.equals("-1")) {
      ""
    } else {
      s"Exploration_$RANDOM_SEARCH_ID"
    }, s"$s3Location").toString

    InputProcessor.listFiles(CompetitionServices.INPUT_ROOT).map(x => x.map(_.stripSuffix(".csv"))) match {
      case Right(inputStrings) =>
        // Ensure inputs specified in config match available inputs in inputFileList
        inputStrings.foreach {
          inputType =>
            bucket.flatMap { b =>
              b.getObject(Paths.get(s"$s3InputKeyPrefix", s"$inputType.csv").toString)
            }.map(io => {
              val targetFile = new File(s"${CompetitionServices.INPUT_ROOT}$inputType.csv")
              FileUtils.copyInputStreamToFile(io.content, targetFile)
            })
        }
        "Successfully loaded input data from S3!"
      case Left(failure) => failure

    }

  }

  private def uploadCompetitionResultsToS3(competitionServices: CompetitionServices): Unit = {
    runStateMonitor.uploadOutputDump(Paths.get(competitionServices.SUBMISSION_OUTPUT_ROOT_NAME).toString)
    runStateMonitor.uploadOutputDump(Paths.get(competitionServices.SUBMISSION_OUTPUT_ROOT_NAME, CompetitionServices.COMPETITION_ROOT, "submissionScores.csv").toString)
    runStateMonitor.uploadOutputDump(Paths.get(competitionServices.SUBMISSION_OUTPUT_ROOT_NAME, CompetitionServices.COMPETITION_ROOT, "rawScores.csv").toString)
    runStateMonitor.uploadOutputDump(Paths.get(competitionServices.SUBMISSION_OUTPUT_ROOT_NAME, "summaryStats.csv").toString)
    val lastIter = competitionServices.lastIteration
    val lastIterEvents = Paths.get(s"${competitionServices.SUBMISSION_OUTPUT_ROOT_NAME}", "ITERS", s"it.$lastIter", s"$lastIter.events.xml.gz")
    runStateMonitor.uploadOutputDump(lastIterEvents.toString)
  }

  private def parseArgs(args: Array[String]): TypesafeConfig = {
    val parsedArgs = argsParser.parse(args, init = Arguments()) match {
      case Some(pArgs) => pArgs
      case Some(pArgs) => pArgs
      case None =>
        throw new IllegalArgumentException(
          "Arguments provided were unable to be parsed. See above for reasoning."
        )
    }

    processEvents = parsedArgs.processEvents


    val altConfigPath: Option[String] =

      (parsedArgs.scenario, parsedArgs.sampleSize, parsedArgs.subScenario.map(x => s"-$x").orElse(Some(""))).mapN({ case (sc: String, s: String, subSc: String) => Paths
        .get(CompetitionServices.FIXED_DATA_ROOT_NAME, sc, s"$sc-$s$subSc.conf").toString.replace("\\", "/")
      })


    val tempConfig: TypesafeConfig = parsedArgs.config.orElse(
      (altConfigPath, parsedArgs.iterations).mapN { case (pth: String, itrs: String) =>
        ConfigFactory.parseMap(
          Map("beam.agentsim.lastIteration" -> itrs).asJava)
          .withFallback(BeamConfigUtils.parseFileSubstitutingInputDirectory(pth))
      }
    ).get

    val config: TypesafeConfig = ConfigFactory.parseMap(
      Map("beam.warmStart.enabled" -> !parsedArgs.withoutWarmStart).asJava)
      .withFallback(tempConfig).withFallback(
      ConfigFactory.parseString("config=" + parsedArgs.configLocation.getOrElse(altConfigPath.get))
    )

    runStateMonitor = parsedArgs.s3Location match {
      case Some(s3Loc) =>
        logger.info(downloadInputsFromS3(s3Loc))
        RunStateMonitor(Some(s3Loc))
      case None =>
        RunStateMonitor()
    }
    config
  }

  private def warmStart(beamConfig: BeamConfig, matsimConfig: MatsimConfig): Unit = {
    val maxHour = TimeUnit.SECONDS.toHours(matsimConfig.travelTimeCalculator().getMaxTime).toInt
    val beamWarmStart = BeamWarmStart(beamConfig)

  }


  def runCompetition(args: Array[String]): Unit = {

    val config = parseArgs(args).withFallback(ConfigFactory.parseMap(
      Map(
        "beam.agentsim.toll.file" -> "submission-inputs/RoadPricing.csv",
        "beam.agentsim.agents.vehicles.transitVehicleTypesByRouteFile" -> "submission-inputs/VehicleFleetMix.csv",
        "beam.agentsim.agents.modeIncentive.file" -> "submission-inputs/ModeIncentives.csv",
        "beam.agentsim.agents.ptFare.file" -> "submission-inputs/MassTransitFares.csv"
      ).asJava
    )).resolve()

    runCompetitionWithConfig(config)
  }


  def runCompetitionWithConfig(config: TypesafeConfig): Unit = {

    // Can initialize only when config is fully loaded
    runStateMonitor.init(config)

    val beamExecutionConfig = setupBeamWithConfig(config)
    val networkCoordinator: NetworkCoordinator = buildNetworkCoordinator(beamExecutionConfig.beamConfig)
    val (scenario, beamScenario): (MutableScenario, BeamScenario) = buildBeamServicesAndScenario(beamExecutionConfig.beamConfig, beamExecutionConfig.matsimConfig)
    val injector: inject.Injector = buildInjector(config,beamExecutionConfig.beamConfig,scenario,beamScenario)
    val logStart = {
      val populationSize = scenario.getPopulation.getPersons.size()
      val vehiclesSize = scenario.getVehicles.getVehicles.size()
      val lanesSize = scenario.getLanes.getLanesToLinkAssignments.size()

      val logHHsize = scenario.getHouseholds.getHouseholds.size()
      val logBeamPrivateVehiclesSize = beamScenario.privateVehicles.size
      val logVehicleTypeSize = beamScenario.vehicleTypes.size
      val modIncentivesSize = beamScenario.modeIncentives.modeIncentives.size
      s"""
         |Scenario population size: $populationSize
         |Scenario vehicles size: $vehiclesSize
         |Scenario lanes size: $lanesSize
         |BeamScenario households size: $logHHsize
         |BeamScenario privateVehicles size: $logBeamPrivateVehiclesSize
         |BeamScenario vehicleTypes size: $logVehicleTypeSize
         |BeamScenario modIncentives size $modIncentivesSize
         |""".stripMargin
    }
    logger.warn(logStart)

    val beamServices = injector.getInstance(classOf[BeamServices])

    implicit val competitionServices: CompetitionServices = CompetitionServices(beamServices, networkCoordinator)

//    warmStart(beamExecutionConfig.beamConfig, beamExecutionConfig.matsimConfig)

    val eventsManager = injector.getInstance(classOf[EventsManager])
    eventsManager.addHandler(new SimStateReportingEventsListener(beamServices, runStateMonitor))

    val childInjector = injector.createChildInjector(new SubmissionEvaluatorModule(CompetitionServices))

    val mainEvaluator = childInjector.instance[SubmissionEvaluatorFactory].getEvaluatorForIteration(competitionServices.lastIteration)

    val controlerListenerManager = childInjector.getInstance(classOf[ControlerListenerManagerImpl])

    controlerListenerManager.addControlerListener(childInjector.instance[IterationScoreComponentPlottingListener])

    // Move input data to destination w/in submission output directory
    MiscUtils.moveInputs(Paths.get(CompetitionServices.INPUT_ROOT),
      competitionServices.INPUT_DEST)

    InputProcessor().processInputs()

    scenario.setNetwork(networkCoordinator.network)

    runBeam(beamServices, scenario, beamScenario, beamExecutionConfig.outputDirectory)

    // Score submission
    val submissionScore: BigDecimal = mainEvaluator.scoreSubmission()

    // BEGIN Post-processing here...

    // Visualization conversion to csv
    val linkStatConverter = LinkStatCsvSpatialConversion(competitionServices)
    linkStatConverter.runConversion()
    val populationConverter = PopulationCsvSpatialConversion(competitionServices)
    populationConverter.runConversion()

    //Mark the last iteration in runState as COMPLETE
    runStateMonitor.setIterationState(runStateMonitor.numberOfIterations - 1, IterationStateTemplates.SUCCESS)

    // Register Score in the runState, and update the state of the whole run
    runStateMonitor.setScore(submissionScore.doubleValue())
    runStateMonitor.setProgress(1)

    // Register Final Score here
    mainEvaluator.outputSummary()
    submissionScore.setScale(2, BigDecimal.RoundingMode.HALF_UP)

    // Upload data to S3
//    OutputProcessor.runPostProcessing(Paths.get(competitionServices.SUBMISSION_OUTPUT_ROOT_NAME).toString, runStateMonitor.numberOfIterations - 1, runStateMonitor.s3OutputLoc, competitionServices.SAMPLE_NAME)

    // Only uploads the output dump if the relevant S3 coordinates are provided
    // uploadCompetitionResultsToS3(competitionServices)

    runStateMonitor.setState(RunStateTemplates.SUCCESS)
//    runStateMonitor.syncStateWithRedis(forceUpdate = true)
    Console.println(runStateMonitor.serializeState())
    Console.err.print("\n")

    Console.err.print(
      s"\n\n -------- Submission score: ${numberFormatter.format(submissionScore)} -------------- \n")

    Console.flush()
  }


}
