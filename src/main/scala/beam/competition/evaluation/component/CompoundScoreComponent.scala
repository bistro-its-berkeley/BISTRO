package beam.competition.evaluation.component

import beam.competition.evaluation.component.ScoreComponent.ScoreComponentWeightIdentifier
import beam.competition.run.CompetitionServices
import com.github.martincooper.datatable.DataTable

abstract class CompoundScoreComponent(override val scoreComponentWeightIdentifier: ScoreComponentWeightIdentifier, statFields: Set[String])(override implicit val competitionServices: CompetitionServices) extends NormalizedScoreComponent(scoreComponentWeightIdentifier) {

  def transformation(input: String, source: DataTable): Double

  override def prepData(source: DataTable): Double = {
    {
      statFields.map {
        transformation(_, source)
      }.sum
    }
  }

}
