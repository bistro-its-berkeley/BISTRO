package beam.competition.inputs.impl

import beam.competition.inputs.InputSpecHelper
import com.wix.accord.transform.ValidationTransform
import org.scalacheck.Gen

class FrequencyAdjustmentInputSpec extends InputSpecHelper[FrequencyAdjustmentInput] {

  override implicit val singleValidator: ValidationTransform.TransformedValidator[FrequencyAdjustmentInput] = FrequencyAdjustmentInputDataHelper().inputValidator

  import com.wix.accord._
  import beam.competition.inputs.impl.SiouxFauxConstants._

  "Frequency adjustment input" should {

    "pass property check for random data" in {
      val faGen: Gen[FrequencyAdjustmentInput] = for {

        routeId <- Gen.oneOf(ROUTE_NUMBER)

        endTime <- Gen.oneOf(BUS_SCHEDULE_START_TIMES)
        startTime <- Gen.oneOf(BUS_SCHEDULE_END_TIMES) suchThat (_ < endTime)

        headway <- Gen.oneOf(AVAILABLE_HEADWAY)

      } yield FrequencyAdjustmentInput(routeId.toString, startTime, endTime, headway)

      forAll(faGen) {
        input => validate(input) shouldBe aSuccess
      }
    }

  }
}
