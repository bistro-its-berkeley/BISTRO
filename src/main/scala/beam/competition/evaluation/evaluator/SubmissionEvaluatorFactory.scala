package beam.competition.evaluation.evaluator

import beam.competition.evaluation.component.CompoundScoreComponent
import beam.competition.evaluation.component.ScoreComponent.ScoreComponentWeightIdentifier
import beam.competition.run.CompetitionServices
import com.google.inject.Inject

class SubmissionEvaluatorFactory @Inject()(simpleStatFields: Set[ScoreComponentWeightIdentifier],compoundStatFields: Map[ScoreComponentWeightIdentifier, CompoundScoreComponent]) {

  def getEvaluatorForIteration(iteration: Int)(implicit competitionServices: CompetitionServices): SubmissionEvaluator = {
    SubmissionEvaluator(simpleStatFields, compoundStatFields, iteration)
  }
}
