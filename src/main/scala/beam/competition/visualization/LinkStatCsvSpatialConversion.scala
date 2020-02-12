package beam.competition.visualization

import java.io.PrintStream
import java.nio.file._

import beam.competition.run.CompetitionServices
import beam.competition.utils.MiscUtils._
import com.conveyal.r5.transit.TransportNetwork
import org.apache.commons.io.FilenameUtils.getName
import org.matsim.core.utils.io.IOUtils

import scala.collection.mutable
import scala.collection.mutable.ListBuffer
import scala.compat.java8.StreamConverters._

case class LinkStatCsvSpatialConversion(competitionServices: CompetitionServices) {

  val itersBase = getITERSPath(competitionServices.SUBMISSION_OUTPUT_ROOT_NAME).get
  val lastIteration = competitionServices.beamConfig.matsim.modules.controler.lastIteration
  val linkStatsPath = Paths.get(itersBase, s"it.$lastIteration", s"$lastIteration.linkstats.csv.gz") //Paths.get(itersBase, s"it.0", s"0.linkstats.csv.gz")

  private def getITERSPath(runPath: String): Option[String] = {
    Files.walk(Paths.get(runPath)).toScala[Stream]
      .map(_.toString)
      .find(p => "ITERS".equals(getName(p)))
  }

  def writeFeaturesToFile(spatialData: ListBuffer[String], outputFile: String): Unit = {
    val fileStream: PrintStream = IOUtils.getPrintStream(outputFile)

    spatialData foreach fileStream.println

    fileStream.flush()

    fileStream.close()
  }

  def runConversion(): Unit = {
    Files.createDirectory(competitionServices.VIZ_OUTPUT_ROOT)
    val features = convertLinkStats()
    writeFeaturesToFile(features.head, Paths.get(competitionServices.VIZ_OUTPUT_ROOT.toString, "links.csv").toString)
    writeFeaturesToFile(features(1), Paths.get(competitionServices.VIZ_OUTPUT_ROOT.toString, "link_stats.csv").toString)
  }


  private def convertLinkStats(): Seq[ListBuffer[String]] = {
    val staticFeatures: mutable.ListBuffer[String] = ListBuffer[String]()
    val dynamicFeatures: mutable.ListBuffer[String] = ListBuffer[String]()
    var linksFound: Seq[Int] = Seq[Int]()
    implicit val transportNetwork: TransportNetwork = competitionServices.networkCoordinator.transportNetwork

    val linkStatsOutputLoc = Paths.get(competitionServices.VIZ_OUTPUT_ROOT.toString, "links.csv").toString

    beam.utils.UnzipUtility.unGunzipFile(linkStatsPath.toString, linkStatsOutputLoc, true)

    val lines = IOUtils.getBufferedReader(linkStatsOutputLoc)
    lines.skip(1)


    val staticHeader = "fromX,fromY,toX,toY,freespeed,capacity"
    staticFeatures += staticHeader

    val dynamicHeader = "fromX,fromY,toX,toY,hour,volume,travelTime"
    dynamicFeatures += dynamicHeader

    val rows = lines.lines().toArray().map(x => x.asInstanceOf[String]).map(x => x.split(","))

    for {row <- rows if !row(3).equals("0.0 - 30.0") && row(7).equals("AVG")} yield {
      val linkId = row(0).toInt
      val coords = getR5EdgeCoords(linkId)
      if (!linksFound.contains(linkId)) {
        val freespeed = row(5).toDouble
        val capacity = row(6).toDouble
        val coords = getR5EdgeCoords(linkId)
        val link = s"${coords.toString},$freespeed,$capacity"
        staticFeatures += link
        linksFound :+= linkId
      }
      val hour = row(3).toDouble.toInt
      val volume = row(8).toDouble
      val travelTime = row(9).toDouble
      val linkStat = s"${coords.toString},$hour,$volume,$travelTime"
      dynamicFeatures += linkStat
    }
    Seq(staticFeatures, dynamicFeatures)
  }
}


