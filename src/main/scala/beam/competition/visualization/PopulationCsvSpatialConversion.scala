package beam.competition.visualization

import java.io.PrintStream
import java.nio.file.Paths

import beam.competition.run.CompetitionServices
import beam.sim.common.{GeoUtils, GeoUtilsImpl}
import org.matsim.api.core.v01.Coord
import org.matsim.api.core.v01.population.{Activity, Person, Population}
import org.matsim.core.utils.io.IOUtils

import scala.collection.JavaConverters._
import scala.collection.mutable
import scala.collection.mutable.ListBuffer

case class PopulationCsvSpatialConversion(competitionServices: CompetitionServices) {

  def runConversion(): Unit = {
    val scenario = competitionServices.beamServices.matsimServices.getScenario
    writeFeaturesToFile(populationToCsv(scenario.getPopulation),
      Paths.get(competitionServices.VIZ_OUTPUT_ROOT.toString, "activity_locs.csv").toString)
  }

  def writeFeaturesToFile(spatialData: ListBuffer[String], outputFile: String): Unit = {
    val fileStream: PrintStream = IOUtils.getPrintStream(outputFile)
    spatialData foreach fileStream.println
    fileStream.flush()
    fileStream.close()
  }

  def populationToCsv(population: Population): ListBuffer[String] = {
    val populationFeatures = new ListBuffer[String]
    populationFeatures += "personId,x,y,actType"
    population.getPersons.asScala.values.foreach { person =>
      populationFeatures ++= personToCsvRows(person)
    }
    populationFeatures
  }

  def personToCsvRows(person: Person): mutable.Seq[String] = {
    val plan = person.getSelectedPlan
    plan.getPlanElements.asScala.filter(p =>
      p.isInstanceOf[Activity]).map(act =>
      createActivityRow(person.getId.toString, act.asInstanceOf[Activity]))
  }


  private def createActivityRow(personId: String, activity: Activity): String = {
    val geo = new GeoUtilsImpl(competitionServices.beamConfig)
    val coord: Coord = geo.utm2Wgs(activity.getCoord)
    s"$personId,${coord.getX},${coord.getY},${activity.getType}"
  }
}
