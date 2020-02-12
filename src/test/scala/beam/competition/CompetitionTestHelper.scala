package beam.competition

import java.nio.file.{Path, Paths}

import beam.competition.run.CompetitionServices
import beam.sim.{BeamHelper, BeamServices}
import beam.utils.BeamConfigUtils

trait CompetitionTestHelper extends BeamHelper {
  val resourcesDirectory: Path = Paths.get("src/test/resources/")
  val testConfig: String = "test/sioux_faux/sioux_faux-1k.conf"
}
