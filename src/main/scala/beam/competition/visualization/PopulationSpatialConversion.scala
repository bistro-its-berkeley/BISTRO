package beam.competition.visualization

import java.nio.file.Paths

import beam.competition.run.CompetitionServices
import beam.sim.common.{GeoUtils, GeoUtilsImpl}
import org.geojson.{Feature, FeatureCollection, LngLatAlt, Point}
import org.matsim.api.core.v01.Coord
import org.matsim.api.core.v01.population.{Activity, Person, Population}

import scala.collection.JavaConverters._
import scala.collection.mutable

case class PopulationSpatialConversion(override val competitionServices: CompetitionServices) extends SpatialConversion {

  override def runConversion(): Unit = {
    val scenario = competitionServices.beamServices.matsimServices.getScenario
    writeFeaturesToFile(populationToGeoJson(scenario.getPopulation),
      Paths.get(competitionServices.VIZ_OUTPUT_ROOT.toString, "activity_locs.csv").toString)
  }

  def populationToGeoJson(population: Population): FeatureCollection = {
    val populationFeatures = new FeatureCollection
    population.getPersons.asScala.values.foreach { person =>
      populationFeatures.addAll(personToGeoJson(person).getFeatures)
    }
    populationFeatures
  }

  def personToGeoJson(person: Person): FeatureCollection = {
    val personLocations = new FeatureCollection
    val plan = person.getSelectedPlan
    val feature: mutable.Seq[Feature] = plan.getPlanElements.asScala.filter(p =>
      p.isInstanceOf[Activity]).map(act =>
      createActivityFeature(person.getId.toString, act.asInstanceOf[Activity]))
    personLocations.addAll(feature.asJava)
    personLocations
  }


  private def createActivityFeature(personId: String, activity: Activity): Feature = {
    val geo = new GeoUtilsImpl(competitionServices.beamConfig)
    val coord: Coord = geo.utm2Wgs(activity.getCoord)
    val feature = new Feature()
    feature.setProperty("personId", personId)
    feature.setProperty("type", "activity")
    feature.setProperty("activityType", activity.getType)
    feature.setGeometry(new Point(new LngLatAlt(coord.getX, coord.getY)))
    feature
  }
}
