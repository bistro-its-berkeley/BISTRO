package beam.competition.inputs.impl

import beam.competition.inputs.InputSpecHelper
import com.wix.accord.transform.ValidationTransform
import org.scalacheck.Gen

class VehicleFleetMixInputSpec extends InputSpecHelper[VehicleFleetMixInput] {

  import com.wix.accord._

  implicit val singleValidator: ValidationTransform.TransformedValidator[VehicleFleetMixInput] = VehicleFleetMixInputDataHelper().inputValidator

  import beam.competition.inputs.impl.SiouxFauxConstants._

  "Vehicle fleet mix input" should {

    "pass property check for random data" in {
      val vfmGen: Gen[VehicleFleetMixInput] = for {
        routeId <- Gen.oneOf(ROUTE_NUMBER)
        vehicleTypeId <- Gen.oneOf(services.vehicleTypes.keySet.toList.filterNot(_.toString.contains("CAR")))
      } yield VehicleFleetMixInput("217", routeId.toString, vehicleTypeId)

      forAll(vfmGen) {
        input => validate(input) shouldBe aSuccess
      }
    }
  }

}
