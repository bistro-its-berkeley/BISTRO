package beam.competition.run

import beam.competition.CompetitionTestUtils
import beam.competition.aicrowd.OutputProcessor
import org.scalatest.{Matchers, WordSpec}

class OutputProcessorSpec extends WordSpec with CompetitionTestUtils with Matchers {
  //TODO: Fix this test
  "OutputProcessorTest" should {

    val testData = testResourcesDirectory / "outputProcessorSpec"/ "test-output"

    "compress and upload output data folder to s3" in  {
        val s3OutPath: String = OutputProcessor.compressAndUploadToS3((testData/"competition").toString,Some("upload-test"))

      s3OutPath should (endWith ("zip") and startWith ("unit-test-data"))
    }

    "compress and upload data to s3" ignore  {
      val s3OutPath: String = OutputProcessor.compressAndUploadToS3((testData/"summaryStats.csv").toString,Some("upload-test"))

      s3OutPath should (endWith ("zip") and startWith ("unit-test-data"))
    }
  }
}
