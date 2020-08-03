package beam.competition.evaluation.component

import beam.competition.evaluation.component.ScoreComponent.ScoreComponentWeightIdentifier
import beam.competition.run.CompetitionServices

class NormalizedScoreComponent(val scoreComponentWeightIdentifier: ScoreComponentWeightIdentifier)(implicit val competitionServices: CompetitionServices) extends ScoreComponent {

  import NormalizedScoreComponent._

  override val weight: Double = competitionServices.weights(scoreComponentWeightIdentifier)
  val standardizationParams: StandardizationParams = competitionServices.standardizationParams(scoreComponentWeightIdentifier)

  override def evaluate(bauScore: Double, submissionScore: Double): ScoreComponent = {
    // Catch problem-cases here:
    println(s"SCORE ID: ${scoreComponentWeightIdentifier.shortName}")
    println("BAU SCORE")
    println(bauScore)
    println("SUB SCORE")
    println(submissionScore)
    // 1. Possible divide by 0
    if (bauScore == 0.0) {
      // 2. 0/0: 0(bau)->0(sub) => No change, then rawScore = 1.0
      if (submissionScore == 0.0) {
        rawScore = 1.0
      } else {
        println(s"Zero BAU score for ${scoreComponentWeightIdentifier.shortName}!")
        //throw new ArithmeticException(s"Zero BAU score for ${scoreComponentWeightIdentifier.shortName}!")
        rawScore = submissionScore
      }
    } else {
      rawScore = scoreComponentWeightIdentifier.tau * submissionScore / bauScore
    }
    ans = weight * zscore(rawScore, standardizationParams)
    try {
      ans = ans
      this
    }
    catch {
      case e: NumberFormatException =>
        ans=0.0
        this
    }
  }
}

object NormalizedScoreComponent {

  case class StandardizationParams(mu: Double, sigma: Double)

  def zscore(x: Double, standardizationParams: StandardizationParams): Double = {
    assert(standardizationParams.sigma != 0)
    (x - standardizationParams.mu) / standardizationParams.sigma
  }

}
