package beam.competition.inputs.impl

import beam.competition.inputs.InputSpecHelper
import beam.competition.inputs.framework.InputReader
import com.wix.accord.transform.ValidationTransform
import org.scalacheck.Gen
import org.scalatest.Assertion

import scala.reflect.io.Path


class ModeIncentivesInputSpec extends InputSpecHelper[ModeIncentivesInput] {

  import com.wix.accord._

  implicit val singleValidator: ValidationTransform.TransformedValidator[ModeIncentivesInput] = ModeIncentivesInputDataHelper().inputValidator

  implicit val seqValidator: ValidationTransform.TransformedValidator[Seq[ModeIncentivesInput]] = ModeIncentivesInputDataHelper().inputSeqValidator

  import beam.competition.inputs.impl.SiouxFauxConstants._

  "Mode incentives input" should {

    "pass property check for random data" in {
      val miGen: Gen[ModeIncentivesInput] = for {
        incentivizedMode <- Gen.oneOf(INCENTIVIZED_MODE)

        ageStart <- Gen.oneOf(AGE_START)
        ageEnd <- Gen.oneOf(AGE_END)

        incomeStart <- Gen.oneOf(INCOME_START)
        incomeEnd <- Gen.oneOf(INCOME_END)

        amount <- Gen.choose(0.01, 50.0)

      } yield ModeIncentivesInput(incentivizedMode, s"[$ageStart:$ageEnd]", s"[$incomeStart:$incomeEnd]", amount.toString)

      forAll(miGen) {
        input => validate(input) shouldBe aSuccess
      }
    }

    "fail on invalid age range" in {
      val invalidAgeRange: ModeIncentivesInput = ModeIncentivesInput("OnDemand_ride", "[0:4]", "[0:4999]", "20.0")
      validate(invalidAgeRange) shouldBe aFailure
    }

    "succeed on correct income range" in {
      val invalidIncomeRange: ModeIncentivesInput = ModeIncentivesInput("OnDemand_ride", "[1:5]", "[0:4999]", "20.0")
      validate(invalidIncomeRange) shouldBe aSuccess
    }

    "fail on amount greater than 50" in {
      val invalidAmount: ModeIncentivesInput = ModeIncentivesInput("OnDemand_ride", "[1:5]", "[0:4999]", "51.0")
      validate(invalidAmount) shouldBe aFailure
    }

    "fail on bad income input" in {
      val implicitIncomeGap = ModeIncentivesInput("OnDemand_ride", "[1:5]", "[0:5003]", "20.0")
      // Must succeed on their own
      validate(implicitIncomeGap) shouldBe aFailure
    }

    "succeed on correct income range overlap" in {
      val implicitIncomeGap = Seq[ModeIncentivesInput](ModeIncentivesInput("OnDemand_ride", "[1:5]", "[0:4999]", "20.0"), ModeIncentivesInput("OnDemand_ride", "[16:20]", "[0:4999]", "20.0"))
      // Must each at least succeed on their own
      implicitIncomeGap.map(incentive => validate(incentive)).map(res => res shouldBe aSuccess)
    }

    // some further interesting examples that need to pass
    "succeed on many examples" in {
      val testFileRoot: Path = testResourcesDirectory / "incentiveInputSpec" / "ModeIncentives"
      ('A' to 'C').flatMap { l =>

        val data = InputReader((testFileRoot / l.toString).toAbsolute.toString).readInput(ModeIncentivesInputDataHelper())
        val x: List[Assertion] = data.map {
          validate(_) shouldBe aSuccess
        }.toList ::: List(validate(data) shouldBe aSuccess)
        x
      }
    }
  }


}
