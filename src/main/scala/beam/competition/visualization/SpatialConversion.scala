package beam.competition.visualization

import beam.competition.run.CompetitionServices
import com.fasterxml.jackson.databind.ObjectMapper
import org.geojson.FeatureCollection
import org.matsim.api.core.v01.Coord
import org.matsim.core.utils.io.IOUtils

trait SpatialConversion {

  val competitionServices: CompetitionServices

  def runConversion(): Unit

  def writeFeaturesToFile(features: FeatureCollection, outputFileLoc: String): Unit = {
    val writer = IOUtils.getBufferedWriter(outputFileLoc)
    val json = new ObjectMapper().writeValueAsString(features)
    writer.write(json)
    writer.flush()
    writer.close()
  }

}

object SpatialConversion {
  case class CoordPair(first: Coord, second: Coord){
    override def toString: String = s"${first.getX},${first.getY},${second.getX},${second.getY}"
  }
}
