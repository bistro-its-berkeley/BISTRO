package beam.competition.evaluation.component

import java.nio.file.Paths

import beam.competition.CompetitionTestUtils
import beam.competition.run.CompetitionServices
import org.mockito.Answers
import org.mockito.Mockito.when
import org.scalatest.mockito.MockitoSugar
import org.scalatest.{Matchers, WordSpecLike}

class AccessibilityScoreComputationSpec extends WordSpecLike with CompetitionTestUtils with MockitoSugar with Matchers {

  val currentIteration = 1

  // Set up mock services for testing
  implicit val services: CompetitionServices = mock[CompetitionServices](Answers.RETURNS_DEEP_STUBS)
  when(services.SAMPLE_NAME).thenReturn("15k")
  when(services.SUBMISSION_OUTPUT_ROOT_NAME).thenReturn(s"$testResourcesDirectory/accessibilitySpec/output/sioux_faux/sioux_faux-15k-acessibility_test")
  when(services.SIMULATION_NAME).thenReturn("sioux_faux")
  when(services.BAU_ROOT_PATH).thenReturn(Paths.get("fixed-data/sioux_faux/bau"))

  "AccessibilityScoreComputation" should {

    "runAccessibilityComputation to completion" in {
      val accessibilityScoreComputation = new AccessibilityScoreComputation(currentIteration,1)
      Option(accessibilityScoreComputation.runAccessibilityComputation()).get shouldNot be(None)
    }

  }
}
