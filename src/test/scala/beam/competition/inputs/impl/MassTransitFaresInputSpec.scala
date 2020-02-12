package beam.competition.inputs.impl

import beam.competition.inputs.InputSpecHelper
import com.wix.accord.transform.ValidationTransform
import org.scalacheck.Gen

class MassTransitFaresInputSpec extends InputSpecHelper[MassTransitFaresInput] {

  import com.wix.accord._
  import beam.competition.inputs.impl.SiouxFauxConstants._

  override implicit val singleValidator: ValidationTransform.TransformedValidator[MassTransitFaresInput] = MassTransitFaresInputDataHelper().inputValidator

  "Mass Transit Fares input" should {

    "pass property check for random data" in {
      val mtGen: Gen[MassTransitFaresInput] = for {
        routeId <- Gen.oneOf(ROUTE_NUMBER)

        ageEnd <- Gen.oneOf(AGE_END)
        ageStart <- Gen.oneOf(AGE_START) suchThat (_< ageEnd)

        amount <- Gen.choose(0.01, 10.0)
      } yield MassTransitFaresInput("217", routeId.toString, s"[$ageStart:$ageEnd]", amount.toString)


      forAll(mtGen) {
        input => validate(input) shouldBe aSuccess
      }
    }
  }


}
