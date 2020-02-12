package beam.competition.visualization

import java.nio.file._

import beam.competition.run.CompetitionServices
import beam.competition.utils.MiscUtils._
import beam.competition.visualization.LinkStatSpatialConversion.{Link, LinkStat}
import com.conveyal.r5.transit.TransportNetwork
import org.apache.commons.io.FilenameUtils.getName
import org.geojson.{Feature, FeatureCollection}
import org.joda.time.DateTime
import org.joda.time.format.{DateTimeFormat, DateTimeFormatter}
import org.matsim.core.utils.io.IOUtils

import scala.collection.JavaConverters._
import scala.collection.mutable
import scala.compat.java8.StreamConverters._

case class LinkStatSpatialConversion(override val competitionServices: CompetitionServices) extends SpatialConversion {

  val itersBase: String = getITERSPath(competitionServices.SUBMISSION_OUTPUT_ROOT_NAME).get
  val lastIteration: Int = competitionServices.beamConfig.matsim.modules.controler.lastIteration
  val linkStatsPath: Path = Paths.get(itersBase, s"it.$lastIteration", s"$lastIteration.linkstats.csv.gz")

  private def getITERSPath(runPath: String): Option[String] = {
    Files.walk(Paths.get(runPath)).toScala[Stream]
      .map(_.toString)
      .find(p => "ITERS".equals(getName(p)))
  }


  override def runConversion(): Unit = {
    Files.createDirectory(competitionServices.VIZ_OUTPUT_ROOT)
    val features = convertLinkStats()
    writeFeaturesToFile(features.head, Paths.get(competitionServices.VIZ_OUTPUT_ROOT.toString, "links.geojson").toString)
    writeFeaturesToFile(features(1), Paths.get(competitionServices.VIZ_OUTPUT_ROOT.toString, "link_stats.geojson").toString)
  }


  private def convertLinkStats(): Seq[FeatureCollection] = {
    val staticFeatures: FeatureCollection = new FeatureCollection
    val dynamicFeatures: FeatureCollection = new FeatureCollection
    var linksFound: Seq[Int] = Seq[Int]()

    implicit val transportNetwork: TransportNetwork = competitionServices.networkCoordinator.transportNetwork

    val linkStatsOutputLoc = Paths.get(competitionServices.VIZ_OUTPUT_ROOT.toString, "linkstats.csv").toString

    beam.utils.UnzipUtility.unGunzipFile(linkStatsPath.toString, linkStatsOutputLoc, true)

    val lines = IOUtils.getBufferedReader(linkStatsOutputLoc)
    lines.skip(1)
    val rows = lines.lines().toArray().map(x => x.asInstanceOf[String]).map(x => x.split(","))
    for {row <- rows if !row(3).equals("0.0 - 30.0") && row(7).equals("AVG")} yield {
      {
        val linkId = row(0).toInt
        if (!linksFound.contains(linkId)) {
          val freespeed = row(5).toDouble
          val capacity = row(6).toDouble
          val link = Link(linkId, freespeed, capacity).lineFeature
          staticFeatures.add(link)
          linksFound :+= linkId
        }
        val hour = row(3).toDouble.toInt
        val volume = row(8).toDouble
        val travelTime = row(9).toDouble
        val linkStat = LinkStat(linkId, hour, volume, travelTime)
        dynamicFeatures.add(linkStat.lineFeature)

      }
    }
    Seq(staticFeatures, dynamicFeatures)

  }
}

object LinkStatSpatialConversion {


  trait LinearGeojson {
    val id: Int

    implicit val transportNetwork: TransportNetwork

    def lineFeature: Feature = {
      val lineFeature = new Feature()
      val linkLineString = getCoordsAsLineString(getR5EdgeCoords(id))
      lineFeature.setGeometry(linkLineString)
      lineFeature.setProperties(getPropertyMap)
      lineFeature
    }

    def getPropertyMap: java.util.Map[String, AnyRef]
  }

  case class Link(override val id: Int, freespeed: Double, capacity: Double)
                 (implicit val transportNetwork: TransportNetwork) extends LinearGeojson {

    def getPropertyMap: java.util.Map[String, AnyRef] = {
      mutable.Map(
        "linkId" -> id,
        "freespeed" -> freespeed,
        "capacity" -> capacity,
      ).asJava.asInstanceOf[java.util.Map[String, AnyRef]]
    }
  }

  case class LinkStat(override val id: Int, hour: Int, volume: Double, travelTime: Double)
                     (implicit val transportNetwork: TransportNetwork) extends LinearGeojson {

    val fmt: DateTimeFormatter = DateTimeFormat.forPattern("yyyy-MM-dd HH:mm:ss +Z")

    def getPropertyMap: java.util.Map[String, AnyRef] = {
      val now = DateTime.now()
      mutable.Map(
        "linkId" -> id,
        "hour" -> fmt.print(if (hour > 23) {
          now.withHourOfDay(hour - 23).withDayOfYear(now.dayOfYear.get() + 1)
        } else {
          now.withHourOfDay(hour)
        }),
        "volume" -> volume,
        "travelTime" -> travelTime
      ).asJava.asInstanceOf[java.util.Map[String, AnyRef]]
    }
  }


}
