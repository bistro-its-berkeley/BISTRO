package beam.competition.evaluation.component

import java.io.File
import java.lang.Math.min
import java.nio.file
import java.nio.file.{Files, Paths, StandardCopyOption}

import beam.competition.run.CompetitionServices
import beam.utils.BeamConfigUtils
import com.typesafe.scalalogging.LazyLogging
import org.apache.commons.io.FileUtils
import org.matsim.core.utils.io.IOUtils

import scala.collection.mutable.ListBuffer
import scala.sys.process._


class AccessibilityScoreComputation(currentIteration: Int, lastIteration: Int)(implicit competitionServices: CompetitionServices) extends LazyLogging {

  private val numOfIters = min(BeamConfigUtils
    .parseFileSubstitutingInputDirectory(competitionServices.SUBMISSION_OUTPUT_ROOT_NAME + "/beam.conf")
    .getInt("beam.competition.submissionScoreMSAOverNumberOfIters"), currentIteration)

  private val linkStat = ".linkstats.csv.gz"
  private val submissionTravelTimeName = s"$currentIteration$linkStat"

  private val bauTravelTimeName = s"linkstats_bau-${competitionServices.SAMPLE_NAME}.csv.gz"

  val dataPath: file.Path = Paths.get("tmp-data").toAbsolutePath
  var bauAccessibilityScores: Map[String, Map[String, Double]] = Map.empty
  val bauTransitNetRootName = "bau_transit_net.h5"
  val osmWalkLinksRootName = "bau_osm_walk_data"
  val bauTransitFile: File = Paths.get("accessibility/data", bauTransitNetRootName).toFile
  val osmWalkLinks: File = Paths.get("accessibility/data", osmWalkLinksRootName).toFile
  val r5SubDirectory: String = competitionServices.beamConfig.beam.routing.r5.directory.split("/").last

  prepareAccessibilityComputation()

  private def computeAccessibilityForTravelTimes(travelTimeFile: String, numOfIters: Int = 1): Map[String, Map[String, Double]] = {
    val prefix = if (travelTimeFile contains "bau") "bau" else "sub"
    s"python3 accessibility/accessibility_analysis.py tmp-data/$travelTimeFile " +
      s"$numOfIters $r5SubDirectory" ! ProcessLogger(stderr append _)
    val dataOutput: Map[String, Map[String, Double]] = readAccessibilityOutputFile(prefix)
    dataOutput
  }

  private def readAccessibilityOutputFile(prefix: String): Map[String, Map[String, Double]] = {
    val reader = IOUtils.getBufferedReader(dataPath + "/" + prefix + "_accessibility_output.csv")
    val lines = reader.lines().iterator()
    val header = ListBuffer() ++ lines.next().split(",").tail.toSeq
    val index = ListBuffer[String]()
    val data = ListBuffer[Array[Double]]()

    while (lines.hasNext) {
      val line = lines.next()
      val lineData = line.split(",")
      data.append(lineData.tail.map(_.toDouble))
      index.append(lineData.head)
    }

    index.zip(data.map { d => header.zip(d).toMap }).toMap
  }

  private def updateGtfsData(): Unit = {
    s"python3  accessibility/modify_gtfs_for_submission.py $r5SubDirectory" ! ProcessLogger(stderr append _)
  }

  private def prepareAccessibilityComputation(): Unit = {
    if (currentIteration == 1) {
      FileUtils.deleteDirectory(dataPath.toFile)
    }
    Files.createDirectories(dataPath)
    (0 until numOfIters).foreach(n => {
      val prefixIter = currentIteration - n
      val linkStatFile = Paths.get(s"${competitionServices.SUBMISSION_OUTPUT_ROOT_NAME}", "ITERS",
        s"it.$prefixIter", s"$prefixIter$linkStat")
      Files.copy(linkStatFile, dataPath.resolve(s"$prefixIter$linkStat"), StandardCopyOption.REPLACE_EXISTING)
    })

    updateGtfsData()

    if (bauTransitFile.exists()) { // Will be recomputed for bau if absent and put in appropriate directory by script
      FileUtils.copyDirectory(bauTransitFile, dataPath.resolve(bauTransitNetRootName).toFile)
    }
    if (osmWalkLinks.exists()) {
      FileUtils.copyDirectory(osmWalkLinks, dataPath.resolve(osmWalkLinksRootName).toFile)
    }

    val inputPlansPath = Paths.get(competitionServices.beamConfig.beam.agentsim.agents.plans.inputPlansFilePath)

    Files.copy(inputPlansPath, dataPath.resolve(inputPlansPath.getFileName), StandardCopyOption.REPLACE_EXISTING)
    Files.copy(Paths.get(competitionServices.beamConfig.beam.routing.r5.directory, "physsim-network.xml"),
      dataPath.resolve("physsim-network.xml"), StandardCopyOption.REPLACE_EXISTING)
    Files.copy(Paths.get(competitionServices.BAU_ROOT_PATH.toString, "linkstats", bauTravelTimeName),
      dataPath.resolve(bauTravelTimeName), StandardCopyOption.REPLACE_EXISTING)
  }

  /**
    * Runs full accessiblity computation pipeline using pandana
    *
    * @return a [[Map]] containing the name of each accessibility metric suffixed with a "bau" or "sub"
    *         for the business as usual or submission cases, respectively.
    */
  def runAccessibilityComputation(): ListBuffer[Map[String, Map[String, Double]]] = {

    if (currentIteration == 1) {
      bauAccessibilityScores = computeAccessibilityForTravelTimes(bauTravelTimeName)
    } else {
      bauAccessibilityScores = readAccessibilityOutputFile("bau")
    }

    val submissionAccessibilityScores = computeAccessibilityForTravelTimes(submissionTravelTimeName, numOfIters)

    ListBuffer(bauAccessibilityScores, submissionAccessibilityScores)

  }

}

