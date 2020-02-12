package beam.competition.run

import java.io.File
import java.nio.file._

import beam.utils.BeamConfigUtils

import scala.collection.JavaConverters._


object RunAnalysis extends App with CompetitionHelper {

  val ANALYSIS_OPT = "analysis"

  val argsMap = parseArgs(args)

  if (argsMap.get(ANALYSIS_OPT).isEmpty) {
    throw new IllegalArgumentException(s"$ANALYSIS_OPT param is missing")
  }

  val analysisPath: Path = new File(argsMap(ANALYSIS_OPT)).toPath.toAbsolutePath

  if (!Files.exists(analysisPath)) {
    throw new IllegalArgumentException(s"$ANALYSIS_OPT file is missing: $analysisPath")
  }

  // Run analysis
  runAnalysis(analysisPath)

  System.exit(0)

  def parseArgs(args: Array[String]) = {
    args
      .sliding(2, 1)
      .toList
      .collect {
        case Array("--analysis", filePath: String) if filePath.trim.nonEmpty =>
          (ANALYSIS_OPT, filePath)
        case arg@_ =>
          throw new IllegalArgumentException(arg.mkString(" "))
      }
      .toMap
  }

  def runAnalysis(analysisPath: Path) = {
    val analysisConfig = BeamConfigUtils.parseFileSubstitutingInputDirectory(analysisPath.toFile).resolve()

    val baseConfPath = analysisConfig.getString("analysis.baseConfig")
    val baseConf = BeamConfigUtils.parseFileSubstitutingInputDirectory(baseConfPath)

    val plans = analysisConfig.getConfigList("analysis.plans")

    for (plan <- plans.asScala) {
      val conf = plan.withFallback(baseConf).resolve()

      val rootSubmissionInputsFolder = conf.getString("beam.agentsim.agents.ptFare.file").replace("MassTransitFares.csv", "")

      runCompetitionWithConfig(conf)
    }
  }


  /*

    val files = getListOfFiles("plan")
    val MassTransitFaresPath = Paths.get("fixed-data", "sioux_faux", "MassTransitFares.csv")

    files.foreach(file => {
      Files.copy(file.toPath, MassTransitFaresPath, StandardCopyOption.REPLACE_EXISTING)

      println(s"Starting analyses for ${file.toString}")
      //RunCompetition.main(args)
    }
    )

    def getListOfFiles(dir: String):List[File] = {
      val d = new File(dir)
      if (d.exists && d.isDirectory) {
        d.listFiles.filter(_.isFile).toList
      } else {
        List[File]()
      }
    }*/
}
